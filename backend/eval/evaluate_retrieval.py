"""
Offline retrieval evaluation: measure how often the correct article is retrieved.

The test set has two kinds of questions:
  - in-scope  (expected_articles non-empty): answerable from the knowledge base.
                Measured with recall@k (any-match): HIT if at least one expected
                article appears in the top-k retrieved results.
  - off-topic (expected_articles empty): outside the knowledge base. Not part of
                recall. We report their top-1 similarity score so we can later
                pick a relevance threshold for abstention (task 9.4): an off-topic
                question should score clearly lower than an in-scope one.

Run from the backend/ directory:
    python eval/evaluate_retrieval.py
    python eval/evaluate_retrieval.py --top-k 5
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import settings
from repositories.vector_repository import PineconeRepository
from services.embedding_service import GeminiEmbeddingService

# Must mirror routes/query.py — eval is only honest if it uses the same top_k
# the production endpoint uses.
DEFAULT_TOP_K = 5

# Free-tier embedding has a per-minute request limit; pause between questions.
SLEEP_BETWEEN_QUESTIONS = 4.0

TEST_SET_PATH = Path(__file__).resolve().parent / "test_set.json"


def load_test_set() -> list[dict]:
    with open(TEST_SET_PATH, encoding="utf-8") as f:
        return json.load(f)["items"]


def _retrieved_articles(matches) -> list[tuple[str, str]]:
    """(law, article_number-as-str) for each retrieved match, in rank order."""
    result = []
    for m in matches:
        law = m.metadata.get("law", "")
        number = m.metadata.get("article_number")
        result.append((law, str(int(number)) if number is not None else "?"))
    return result


def _best_hit_rank(expected: list[dict], retrieved: list[tuple[str, str]]) -> int | None:
    """1-based rank of the first retrieved match that is an expected article,
    or None if none of the expected articles were retrieved."""
    expected_pairs = {(e["law"], e["article"]) for e in expected}
    for rank, pair in enumerate(retrieved, start=1):
        if pair in expected_pairs:
            return rank
    return None


def evaluate(top_k: int) -> None:
    items = load_test_set()
    embedding_service = GeminiEmbeddingService(api_key=settings.gemini_api_key)
    repo = PineconeRepository(
        api_key=settings.pinecone_api_key,
        index_name=settings.pinecone_index_name,
    )

    in_scope = [it for it in items if it["expected_articles"]]
    off_topic = [it for it in items if not it["expected_articles"]]
    print(f"Evaluating {len(items)} questions "
          f"({len(in_scope)} in-scope, {len(off_topic)} off-topic), top_k={top_k}\n")

    hits = 0
    rank_counts = {}          # rank -> how many in-scope questions hit first here
    in_scope_top_scores = []  # top-1 score per in-scope question (for threshold)
    off_topic_top_scores = []  # top-1 score per off-topic question
    misses = []

    print("--- In-scope (recall@k) ---")
    for item in in_scope:
        vector = embedding_service.embed(item["question"])
        matches = repo.query(vector=vector, top_k=top_k)
        retrieved = _retrieved_articles(matches)
        top_score = matches[0].score if matches else 0.0
        in_scope_top_scores.append(top_score)
        rank = _best_hit_rank(item["expected_articles"], retrieved)

        expected_str = ", ".join(f"{e['law']} m.{e['article']}" for e in item["expected_articles"])
        if rank is not None:
            hits += 1
            rank_counts[rank] = rank_counts.get(rank, 0) + 1
            print(f"  [HIT  @{rank}] (score {top_score:.3f}) id {item['id']}: expected {expected_str}")
        else:
            misses.append(item)
            retrieved_str = ", ".join(f"{law} m.{num}" for law, num in retrieved)
            print(f"  [MISS    ] (score {top_score:.3f}) id {item['id']}: expected {expected_str}")
            print(f"              retrieved: {retrieved_str}")
        time.sleep(SLEEP_BETWEEN_QUESTIONS)

    print("\n--- Off-topic (should score low; not part of recall) ---")
    for item in off_topic:
        vector = embedding_service.embed(item["question"])
        matches = repo.query(vector=vector, top_k=top_k)
        top_score = matches[0].score if matches else 0.0
        off_topic_top_scores.append(top_score)
        top_article = ""
        if matches:
            law, num = _retrieved_articles(matches)[0]
            top_article = f"{law} m.{num}"
        print(f"  (score {top_score:.3f}) id {item['id']}: top match {top_article} — {item['question']}")
        time.sleep(SLEEP_BETWEEN_QUESTIONS)

    # ----- Summary -----
    total_in = len(in_scope)
    print("\n" + "=" * 55)
    print(f"Recall@{top_k}: {hits}/{total_in} = {hits / total_in:.0%}  (in-scope only)")
    if rank_counts:
        breakdown = ", ".join(f"rank {r}: {rank_counts[r]}" for r in sorted(rank_counts))
        print(f"Hit rank breakdown: {breakdown}")
    if misses:
        print(f"\nMisses ({len(misses)}):")
        for m in misses:
            print(f"  - id {m['id']}: {m['question']}")

    print("\n--- Score distribution (raw material for task 9.4 threshold) ---")
    if in_scope_top_scores:
        print(f"  in-scope  top-1 scores: min {min(in_scope_top_scores):.3f}, "
              f"max {max(in_scope_top_scores):.3f}")
    if off_topic_top_scores:
        print(f"  off-topic top-1 scores: min {min(off_topic_top_scores):.3f}, "
              f"max {max(off_topic_top_scores):.3f}")
    if in_scope_top_scores and off_topic_top_scores:
        gap = min(in_scope_top_scores) - max(off_topic_top_scores)
        if gap > 0:
            print(f"  Clean separation: a threshold between "
                  f"{max(off_topic_top_scores):.3f} and {min(in_scope_top_scores):.3f} "
                  f"would gate all off-topic questions (gap {gap:.3f}).")
        else:
            print("  Overlap: some off-topic questions score as high as in-scope ones — "
                  "no single clean cutoff; will need a tuned threshold (task 9.4).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure retrieval recall@k.")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="How many matches to retrieve per question")
    args = parser.parse_args()
    evaluate(args.top_k)
