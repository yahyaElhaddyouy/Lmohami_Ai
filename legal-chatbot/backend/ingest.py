import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import chromadb
import requests
from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = os.getenv("CHROMA_PATH", str(BASE_DIR / "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "legal_sources")

OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://localhost:11434/api/embeddings")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

SUPPORTED_TYPES = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".md": "md",
}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "darija_dataset",
    "evaluation",
    "node_modules",
    "real_cases",
    "synthetic",
    "training",
    "venv",
}

MIN_CHUNK_CHARS = 800
TARGET_CHUNK_CHARS = 1000
MAX_CHUNK_CHARS = 1200
OVERLAP_CHARS = 180
MIN_INDEX_CHARS = 100
BATCH_SIZE = 32

ARTICLE_START_RE = re.compile(
    r"(?im)(?:^|\n)\s*(?:article|art\.)\s+\d+\b|"
    r"(?:^|\n)\s*\u0627\u0644\u0645\u0627\u062f\u0629\s+\d+\b"
)


@dataclass(frozen=True)
class DocumentPage:
    page: int
    text: str


@dataclass
class IngestStats:
    files_found: int = 0
    chunks_indexed: int = 0
    chunks_existing: int = 0
    chunks_too_small: int = 0
    categories_found: set[str] | None = None
    skipped_files: list[str] | None = None
    skipped_dirs: list[str] | None = None
    errors: list[str] | None = None

    def __post_init__(self):
        self.categories_found = set()
        self.skipped_files = []
        self.skipped_dirs = []
        self.errors = []


def get_embedding(text: str):
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"-\s*\n\s*", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_article_sections(text: str) -> list[str]:
    matches = list(ARTICLE_START_RE.finditer(text))
    if not matches:
        return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]

    sections: list[str] = []
    first_start = matches[0].start()
    if first_start > 0:
        intro = text[:first_start].strip()
        if intro:
            sections.append(intro)

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.start() : end].strip()
        if section:
            sections.append(section)

    return sections


def split_long_text(text: str) -> list[str]:
    chunks: list[str] = []
    start = 0

    while start < len(text):
        hard_end = min(start + TARGET_CHUNK_CHARS, len(text))
        if hard_end == len(text):
            chunks.append(text[start:].strip())
            break

        min_end = min(start + MIN_CHUNK_CHARS, hard_end)
        window = text[min_end:hard_end]
        boundary = max(
            window.rfind("\n\n"),
            window.rfind("\n"),
            window.rfind(". "),
            window.rfind("; "),
            window.rfind(": "),
        )

        end = hard_end if boundary == -1 else min_end + boundary + 1
        if end <= start:
            end = hard_end

        chunks.append(text[start:end].strip())
        start = end

    return [chunk for chunk in chunks if chunk]


def tail_overlap(text: str) -> str:
    text = text.strip()
    if len(text) <= OVERLAP_CHARS:
        return text
    return text[-OVERLAP_CHARS:].lstrip()


def add_overlap(chunks: list[str]) -> list[str]:
    if not chunks:
        return []

    overlapped = [chunks[0]]
    for previous, chunk in zip(chunks, chunks[1:]):
        prefix = tail_overlap(previous)
        if prefix and len(prefix) + 2 + len(chunk) <= MAX_CHUNK_CHARS:
            overlapped.append(f"{prefix}\n\n{chunk}")
        else:
            overlapped.append(chunk)
    return overlapped


def split_text(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    base_chunks: list[str] = []
    current = ""

    for section in split_article_sections(text):
        if len(section) > TARGET_CHUNK_CHARS:
            if current:
                base_chunks.append(current.strip())
                current = ""
            base_chunks.extend(split_long_text(section))
            continue

        candidate = section if not current else f"{current}\n\n{section}"
        if len(candidate) <= TARGET_CHUNK_CHARS:
            current = candidate
            continue

        if current:
            base_chunks.append(current.strip())
        current = section

    if current:
        base_chunks.append(current.strip())

    return add_overlap([chunk for chunk in base_chunks if chunk.strip()])


def read_pdf(path: Path) -> list[DocumentPage]:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        reader.decrypt("")

    pages: list[DocumentPage] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if text:
            pages.append(DocumentPage(page=page_number, text=text))
    return pages


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1256", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def read_document(path: Path, source_type: str) -> list[DocumentPage]:
    if source_type == "pdf":
        return read_pdf(path)

    text = clean_text(read_text_file(path))
    return [DocumentPage(page=1, text=text)] if text else []


def resolve_data_dir(data_dir: str) -> Path:
    raw_path = Path(data_dir)
    if raw_path.is_absolute():
        return raw_path

    cwd_path = (Path.cwd() / raw_path).resolve()
    if cwd_path.exists():
        return cwd_path

    backend_path = (BASE_DIR / raw_path).resolve()
    if backend_path.exists():
        return backend_path

    project_path = (BASE_DIR.parent / raw_path).resolve()
    if project_path.exists():
        return project_path

    return cwd_path


def category_for(path: Path, data_dir: Path) -> str:
    relative = path.relative_to(data_dir)
    return relative.parts[0] if len(relative.parts) > 1 else "uncategorized"


def scan_source_files(data_dir: Path, stats: IngestStats) -> list[Path]:
    files: list[Path] = []

    for root, dirnames, filenames in os.walk(data_dir):
        root_path = Path(root)
        kept_dirs = []
        for dirname in dirnames:
            if dirname in EXCLUDED_DIRS or dirname.startswith("."):
                stats.skipped_dirs.append(str((root_path / dirname).relative_to(data_dir)))
            else:
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in filenames:
            path = root_path / filename
            suffix = path.suffix.lower()
            if suffix in SUPPORTED_TYPES:
                files.append(path)
            else:
                stats.skipped_files.append(
                    f"{path.relative_to(data_dir)} (unsupported type)"
                )

    files.sort(key=lambda item: str(item.relative_to(data_dir)).lower())
    stats.files_found = len(files)
    return files


def stable_chunk_id(category: str, filename: str, page: int, chunk_index: int) -> str:
    raw = f"{category}:{filename}:page-{page}:chunk-{chunk_index}"
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", raw)


def get_existing_ids(collection) -> set[str]:
    try:
        return set(collection.get(include=[])["ids"])
    except Exception:
        return set(collection.get()["ids"])


def flush_batch(collection, batch: dict[str, list]):
    if not batch["ids"]:
        return

    collection.upsert(
        ids=batch["ids"],
        embeddings=batch["embeddings"],
        documents=batch["documents"],
        metadatas=batch["metadatas"],
    )

    for values in batch.values():
        values.clear()


def print_limited(title: str, values: list[str], limit: int = 12):
    print(f"{title}: {len(values)}")
    for value in values[:limit]:
        print(f"  - {value}")
    if len(values) > limit:
        print(f"  ... {len(values) - limit} more")


def ingest(data_dir: Path, reset: bool) -> IngestStats:
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    stats = IngestStats()
    files = scan_source_files(data_dir, stats)

    print(f"Data directory: {data_dir}")
    print(f"Chroma path: {CHROMA_PATH}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Files found: {stats.files_found}")

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
            print(f"Reset: deleted existing collection '{COLLECTION_NAME}'")
        except Exception:
            print(f"Reset: no existing collection named '{COLLECTION_NAME}'")

    collection = client.get_or_create_collection(COLLECTION_NAME)
    existing_ids = set() if reset else get_existing_ids(collection)
    seen_ids: set[str] = set()
    batch = {
        "ids": [],
        "embeddings": [],
        "documents": [],
        "metadatas": [],
    }

    for path in files:
        source_type = SUPPORTED_TYPES[path.suffix.lower()]
        category = category_for(path, data_dir)
        relative_path = path.relative_to(data_dir)
        stats.categories_found.add(category)

        try:
            pages = read_document(path, source_type)
        except Exception as exc:
            stats.errors.append(f"{relative_path}: {exc}")
            continue

        if not pages:
            stats.skipped_files.append(f"{relative_path} (no extractable text)")
            continue

        for page in pages:
            chunks = split_text(page.text)
            for chunk_index, chunk in enumerate(chunks):
                clean_chunk = chunk.strip()
                if len(clean_chunk) < MIN_INDEX_CHARS:
                    stats.chunks_too_small += 1
                    continue

                chunk_id = stable_chunk_id(category, path.name, page.page, chunk_index)
                if chunk_id in existing_ids or chunk_id in seen_ids:
                    stats.chunks_existing += 1
                    continue

                try:
                    embedding = get_embedding(clean_chunk)
                except requests.RequestException as exc:
                    flush_batch(collection, batch)
                    raise RuntimeError(
                        f"Embedding failed for {relative_path} page {page.page}: {exc}"
                    ) from exc

                batch["ids"].append(chunk_id)
                batch["embeddings"].append(embedding)
                batch["documents"].append(clean_chunk)
                batch["metadatas"].append(
                    {
                        "source": path.name,
                        "category": category,
                        "page": page.page,
                        "source_type": source_type,
                        "source_path": str(relative_path).replace("\\", "/"),
                    }
                )

                seen_ids.add(chunk_id)
                stats.chunks_indexed += 1

                if len(batch["ids"]) >= BATCH_SIZE:
                    flush_batch(collection, batch)

    flush_batch(collection, batch)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Index Moroccan legal sources into a local ChromaDB collection."
    )
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild the collection.")
    parser.add_argument("--data-dir", default="data", help="Directory containing legal sources.")
    args = parser.parse_args()

    data_dir = resolve_data_dir(args.data_dir)

    try:
        stats = ingest(data_dir=data_dir, reset=args.reset)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    print("\nIngestion summary")
    print(f"Files found: {stats.files_found}")
    print(f"Chunks indexed: {stats.chunks_indexed}")
    print(f"Existing chunks skipped: {stats.chunks_existing}")
    print(f"Small chunks skipped: {stats.chunks_too_small}")
    print(
        "Categories indexed: "
        + (", ".join(sorted(stats.categories_found)) if stats.categories_found else "none")
    )
    print_limited("Skipped files", stats.skipped_files)
    print_limited("Skipped directories", stats.skipped_dirs)
    print_limited("Errors", stats.errors)

    return 1 if stats.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
