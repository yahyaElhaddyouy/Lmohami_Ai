import os
import requests
import chromadb
from pypdf import PdfReader

PDF_PATH = "data/code_travail_maroc.pdf"
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "code_travail_maroc"

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"


def get_embedding(text: str):
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={"model": EMBED_MODEL, "prompt": text}
    )
    response.raise_for_status()
    return response.json()["embedding"]


def split_text(text, chunk_size=900, overlap=150):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


def read_pdf(path):
    reader = PdfReader(path)
    pages_text = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            pages_text.append((page_num, text))

    return pages_text


def main():
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(COLLECTION_NAME)

    pages = read_pdf(PDF_PATH)

    doc_id = 0

    for page_num, text in pages:
        chunks = split_text(text)

        for chunk in chunks:
            if len(chunk.strip()) < 100:
                continue

            embedding = get_embedding(chunk)

            collection.add(
                ids=[f"doc_{doc_id}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"page": page_num}]
            )

            doc_id += 1

    print(f"Done. Added {doc_id} chunks to ChromaDB.")


if __name__ == "__main__":
    main()