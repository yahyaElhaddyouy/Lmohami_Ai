# -*- coding: utf-8 -*-
"""Download/load external Moroccan Darija datasets into an isolated raw area.

This script deliberately does not clean, train, or ingest into Chroma. External
Darija text is language material only; legal correctness must still come from
the legal RAG sources.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data" / "external_darija"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
REPORTS_DIR = DATA_DIR / "reports"
SOURCES_PATH = DATA_DIR / "sources.json"
DOWNLOAD_REPORT_JSON = REPORTS_DIR / "download_report.json"
DOWNLOAD_REPORT_MD = REPORTS_DIR / "download_report.md"

DEFAULT_SOURCES = {
    "sources": [
        {
            "name": "doda",
            "type": "github_raw",
            "urls": [],
            "github_repo": "darija-open-dataset/dataset",
            "ref": "main",
            "paths": [
                "sentences/sentences.csv",
                "x-tra/idioms.csv",
                "x-tra/proverbs.csv",
                "x-tra/shorts.csv",
                "semantic categories/food.csv",
                "semantic categories/family.csv",
                "semantic categories/emotions.csv",
                "semantic categories/health.csv",
                "syntactic categories/adjectives.csv",
                "syntactic categories/adverbs.csv",
                "syntactic categories/nouns.csv",
                "syntactic categories/verbs.csv",
            ],
        },
        {
            "name": "atlaset",
            "type": "huggingface",
            "dataset": "atlasia/Atlaset",
            "max_rows": 5000,
        },
        {
            "name": "manual_local",
            "type": "local_files",
            "paths": [],
        },
    ]
}

RAW_FILE_SUFFIXES = {".jsonl", ".json", ".csv", ".tsv", ".txt"}


@dataclass
class DownloadReport:
    name: str
    type: str
    status: str = "pending"
    raw_files: list[str] = field(default_factory=list)
    raw_rows: int = 0
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()


def safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe.strip("._") or "source"


def ensure_layout() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCES_PATH.exists():
        SOURCES_PATH.write_text(
            json.dumps(DEFAULT_SOURCES, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def load_sources() -> list[dict[str, Any]]:
    ensure_layout()
    payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("data/external_darija/sources.json must contain a sources list")
    return [source for source in sources if isinstance(source, dict)]


def file_suffix_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix in RAW_FILE_SUFFIXES else ".txt"


def count_jsonl_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return sum(1 for line in handle if line.strip())
    except UnicodeDecodeError:
        return 0


def count_text_rows(path: Path) -> int:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return count_jsonl_rows(path)
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return sum(1 for line in handle if line.strip())
    except UnicodeDecodeError:
        return 0


def download_url(url: str, destination: Path) -> None:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)


def import_github_raw(source: dict[str, Any]) -> DownloadReport:
    name = str(source.get("name", "github_raw"))
    report = DownloadReport(name=name, type="github_raw")
    source_dir = RAW_DIR / safe_name(name)
    source_dir.mkdir(parents=True, exist_ok=True)

    urls = source.get("urls", [])
    if not isinstance(urls, list):
        urls = []

    if urls:
        for index, url in enumerate(urls, start=1):
            if not isinstance(url, str) or not url.strip():
                report.errors.append(f"urls[{index}] is empty or not a string")
                continue
            raw_path = source_dir / f"{safe_name(name)}_{index:03d}{file_suffix_from_url(url)}"
            try:
                download_url(url, raw_path)
                report.raw_files.append(relative(raw_path))
                report.raw_rows += count_text_rows(raw_path)
            except Exception as exc:  # noqa: BLE001 - external source can fail.
                report.errors.append(f"{url}: {exc}")
        report.status = "ok" if report.raw_files else "failed"
        if report.raw_files and report.errors:
            report.status = "partial"
        return report

    archive_imported = import_github_archive(source, report, source_dir)
    if archive_imported:
        report.status = "ok" if report.raw_files else "failed"
        if report.raw_files and report.errors:
            report.status = "partial"
        return report

    report.status = "skipped"
    report.notes.append("No GitHub raw URLs or archive paths configured.")
    return report


def import_github_archive(source: dict[str, Any], report: DownloadReport, source_dir: Path) -> bool:
    repo = source.get("github_repo")
    ref = source.get("ref", "main")
    paths = source.get("paths", [])
    if not isinstance(repo, str) or "/" not in repo:
        return False
    if not isinstance(ref, str) or not ref.strip():
        ref = "main"
    if not isinstance(paths, list) or not paths:
        return False

    archive_path = RAW_DIR / f"{safe_name(str(source.get('name', 'github')))}_{safe_name(ref)}.zip"
    archive_url = f"https://github.com/{repo}/archive/refs/heads/{ref}.zip"
    try:
        download_url(archive_url, archive_path)
        report.raw_files.append(relative(archive_path))
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"{archive_url}: {exc}")
        return True

    wanted = {str(path).replace("\\", "/").strip("/") for path in paths if isinstance(path, str)}
    imported: set[str] = set()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                parts = Path(member.filename).parts[1:]
                if not parts:
                    continue
                inner_path = "/".join(parts)
                if inner_path not in wanted:
                    continue
                imported.add(inner_path)
                destination = source_dir / inner_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(member))
                report.raw_files.append(relative(destination))
                report.raw_rows += count_text_rows(destination)
    except Exception as exc:  # noqa: BLE001
        report.errors.append(f"{archive_path}: {exc}")

    missing = sorted(wanted - imported)
    if missing:
        report.notes.append(f"Configured archive paths not found: {', '.join(missing[:5])}")
    if imported:
        report.notes.append("Imported configured files from GitHub archive because raw URLs were empty.")
    return True


def iter_hf_splits(dataset: Any) -> Iterable[tuple[str, Any]]:
    if hasattr(dataset, "items"):
        yield from dataset.items()
        return
    yield "train", dataset


def import_huggingface(source: dict[str, Any]) -> DownloadReport:
    name = str(source.get("name", "huggingface"))
    report = DownloadReport(name=name, type="huggingface")
    dataset_name = source.get("dataset")
    if not isinstance(dataset_name, str) or not dataset_name.strip():
        report.status = "skipped"
        report.errors.append("Missing Hugging Face dataset name.")
        return report

    try:
        from datasets import load_dataset  # type: ignore
    except ImportError:
        print("pip install datasets")
        report.status = "skipped"
        report.notes.append("Optional Hugging Face dependency missing: pip install datasets")
        return report

    max_rows = source.get("max_rows")
    if not isinstance(max_rows, int) or max_rows <= 0:
        max_rows = 5000
    source_dir = RAW_DIR / safe_name(name)
    source_dir.mkdir(parents=True, exist_ok=True)

    try:
        dataset = load_dataset(dataset_name)
    except Exception as exc:  # noqa: BLE001
        report.status = "failed"
        report.errors.append(f"{dataset_name}: {exc}")
        return report

    for split_name, split_data in iter_hf_splits(dataset):
        raw_path = source_dir / f"{safe_name(name)}_{safe_name(str(split_name))}.raw.jsonl"
        try:
            with raw_path.open("w", encoding="utf-8", newline="\n") as handle:
                for row_index, row in enumerate(split_data, start=1):
                    if row_index > max_rows:
                        break
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    report.raw_rows += 1
            report.raw_files.append(relative(raw_path))
            report.notes.append(f"Loaded up to {max_rows} rows for split {split_name}.")
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"{dataset_name}/{split_name}: {exc}")

    report.status = "ok" if report.raw_files else "failed"
    if report.raw_files and report.errors:
        report.status = "partial"
    return report


def expand_local_paths(paths: list[Any]) -> list[Path]:
    expanded: list[Path] = []
    for raw_path in paths:
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = PROJECT_DIR / path
        if path.is_dir():
            for suffix in RAW_FILE_SUFFIXES:
                expanded.extend(sorted(path.rglob(f"*{suffix}")))
        else:
            expanded.append(path)
    return expanded


def import_local_files(source: dict[str, Any]) -> DownloadReport:
    name = str(source.get("name", "local_files"))
    report = DownloadReport(name=name, type="local_files")
    paths = source.get("paths", [])
    if not isinstance(paths, list) or not paths:
        report.status = "skipped"
        report.notes.append("No manual local files configured.")
        return report

    source_dir = RAW_DIR / safe_name(name)
    source_dir.mkdir(parents=True, exist_ok=True)
    for index, path in enumerate(expand_local_paths(paths), start=1):
        if not path.exists():
            report.errors.append(f"{path}: file does not exist")
            continue
        if path.suffix.lower() not in RAW_FILE_SUFFIXES:
            report.notes.append(f"Skipped unsupported file type: {path}")
            continue
        destination = source_dir / f"{index:03d}_{safe_name(path.name)}"
        try:
            shutil.copy2(path, destination)
            report.raw_files.append(relative(destination))
            report.raw_rows += count_text_rows(destination)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"{path}: {exc}")

    report.status = "ok" if report.raw_files else "failed"
    if report.raw_files and report.errors:
        report.status = "partial"
    return report


def write_reports(sources: list[dict[str, Any]], reports: list[DownloadReport]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "External Moroccan Darija raw import only; not mixed with legal RAG or training data.",
        "sources_config": relative(SOURCES_PATH),
        "raw_dir": relative(RAW_DIR),
        "clean_dir": relative(CLEAN_DIR),
        "total_sources_configured": len(sources),
        "total_raw_files": sum(len(report.raw_files) for report in reports),
        "total_raw_rows": sum(report.raw_rows for report in reports),
        "sources": [report.__dict__ for report in reports],
        "next_step": "Run python clean_external_darija.py to normalize, deduplicate, and filter noisy rows.",
    }
    DOWNLOAD_REPORT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# External Darija Download Report",
        "",
        "## Summary",
        "",
        f"- Total configured sources: {len(sources)}",
        f"- Raw files written: {payload['total_raw_files']}",
        f"- Raw rows observed: {payload['total_raw_rows']}",
        f"- Raw directory: `{relative(RAW_DIR)}`",
        "",
        "## Source Status",
        "",
    ]
    for report in reports:
        lines.append(f"- {report.name} ({report.type}): {report.status}")
        lines.append(f"  - raw files: {len(report.raw_files)}")
        lines.append(f"  - raw rows: {report.raw_rows}")
        if report.notes:
            lines.append(f"  - notes: {'; '.join(report.notes)}")
        if report.errors:
            lines.append(f"  - errors: {'; '.join(report.errors[:3])}")
    lines.extend(
        [
            "",
            "## Guardrail",
            "",
            "No legal source, Chroma collection, SFT split, or training process was modified.",
            "",
        ]
    )
    DOWNLOAD_REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def import_sources() -> tuple[list[dict[str, Any]], list[DownloadReport]]:
    sources = load_sources()
    reports: list[DownloadReport] = []
    for source in sources:
        source_type = source.get("type")
        if source_type == "github_raw":
            reports.append(import_github_raw(source))
        elif source_type == "huggingface":
            reports.append(import_huggingface(source))
        elif source_type == "local_files":
            reports.append(import_local_files(source))
        else:
            reports.append(
                DownloadReport(
                    name=str(source.get("name", "unknown")),
                    type=str(source_type or "unknown"),
                    status="skipped",
                    errors=[f"Unsupported source type: {source_type}"],
                )
            )
    return sources, reports


def main() -> int:
    configure_stdout()
    ensure_layout()
    sources, reports = import_sources()
    write_reports(sources, reports)

    print("External Darija raw import")
    print(f"- configured sources: {len(sources)}")
    print(f"- raw files: {sum(len(report.raw_files) for report in reports)}")
    print(f"- raw rows: {sum(report.raw_rows for report in reports)}")
    print(f"- report: {relative(DOWNLOAD_REPORT_MD)}")
    for report in reports:
        print(f"- {report.name}: {report.status}, raw_files={len(report.raw_files)}, raw_rows={report.raw_rows}")
    print("No legal RAG data was modified and no training was started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
