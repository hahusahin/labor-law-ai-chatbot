"""
Offline ingest: PDF legislation → article chunks → Gemini embeddings → Pinecone.

Run from the backend/ directory:
    python scripts/ingest.py <path-to-pdf>
    python scripts/ingest.py <path-to-pdf> --clear   # deletes all vectors first
"""

import re
import sys
import time
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import settings
from repositories.vector_repository import PineconeRepository
from services.embedding_service import GeminiEmbeddingService

LAW_NAME = "İş Kanunu"
LAW_NUMBER = "4857"
BATCH_SIZE = 5

# Captures optional "Geçici " or "Ek " prefix before "Madde X -"
# \s+ matches the newline between "Geçici" and "Madde" as pdfplumber may split them
ARTICLE_PATTERN = re.compile(r"(Geçici\s+|Ek\s+)?Madde\s+(\d+)\s*[–\-]")


def _article_id(prefix: str, number: int) -> str:
    p = prefix.strip()
    if p.startswith("Geçici") or p.startswith("geçici"):
        return f"is-kanunu-gecici-madde-{number}"
    if p.startswith("Ek"):
        return f"is-kanunu-ek-madde-{number}"
    return f"is-kanunu-madde-{number}"


def _article_type(prefix: str) -> str:
    p = prefix.strip()
    if p.startswith("Geçici") or p.startswith("geçici"):
        return "Geçici Madde"
    if p.startswith("Ek"):
        return "Ek Madde"
    return "Madde"


def extract_text(pdf_path: str) -> str:
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)
    return "\n".join(parts)


def split_into_articles(text: str) -> list[dict]:
    matches = list(ARTICLE_PATTERN.finditer(text))

    if not matches:
        raise ValueError("No articles found — check the PDF text extraction.")

    articles = []
    for i, match in enumerate(matches):
        prefix = match.group(1) or ""
        number = int(match.group(2))
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        pre_lines = [ln.strip() for ln in text[:start].strip().split("\n") if ln.strip()]
        title = pre_lines[-1] if pre_lines and len(pre_lines[-1]) < 80 else ""

        articles.append({
            "vector_id": _article_id(prefix, number),
            "article_number": number,
            "article_type": _article_type(prefix),
            "title": title,
            "text": f"{title}\n{body}".strip() if title else body,
        })

    return articles


def build_vectors(articles: list[dict], embeddings: list[list[float]]) -> list[dict]:
    return [
        {
            "id": a["vector_id"],
            "values": emb,
            "metadata": {
                "law": LAW_NAME,
                "law_number": LAW_NUMBER,
                "article_number": a["article_number"],
                "article_type": a["article_type"],
                "title": a["title"],
                "text": a["text"],
            },
        }
        for a, emb in zip(articles, embeddings)
    ]


def ingest(pdf_path: str, clear: bool = False) -> None:
    print(f"[1/4] Extracting text from: {pdf_path}")
    text = extract_text(pdf_path)

    print("[2/4] Splitting into articles...")
    articles = split_into_articles(text)
    total = len(articles)
    regular = sum(1 for a in articles if a["article_type"] == "Madde")
    gecici = sum(1 for a in articles if a["article_type"] == "Geçici Madde")
    ek = sum(1 for a in articles if a["article_type"] == "Ek Madde")
    print(f"      Found {total} articles: {regular} regular, {gecici} Geçici, {ek} Ek.")

    embedding_service = GeminiEmbeddingService(api_key=settings.gemini_api_key)
    repo = PineconeRepository(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
    )

    if clear:
        print("      Clearing existing vectors from index...")
        repo.clear()
        print("      Done.")

    print(f"[3/4] Embedding and uploading in batches of {BATCH_SIZE}...")

    for i in range(0, total, BATCH_SIZE):
        batch_articles = articles[i : i + BATCH_SIZE]
        batch_texts = [a["text"] for a in batch_articles]
        label = f"articles {i + 1}–{min(i + BATCH_SIZE, total)}"

        embeddings = embedding_service.embed_batch(batch_texts)
        vectors = build_vectors(batch_articles, embeddings)
        repo.upsert(vectors)
        print(f"      Embedded + upserted {label}")

        if i + BATCH_SIZE < total:
            time.sleep(10)

    print(f"\nDone! {total} articles indexed in Pinecone.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest.py <path-to-pdf> [--clear]")
        sys.exit(1)
    ingest(sys.argv[1], clear="--clear" in sys.argv)
