"""
Offline answer-correctness evaluation (LLM-as-judge).

Retrieval eval (evaluate_retrieval.py) only checks whether the right article is
fetched. This script checks whether the *generated answer* is actually correct.

For each in-scope question:
  1. Generate an answer via the REAL production query path (routes.query.query),
     so the eval reflects exactly what users get: embed -> retrieve -> prompt -> LLM.
  2. LLM-as-judge: a Gemini model grades the generated answer against the
     question's reference_answer and returns {correct, reason}.
  3. Deterministic check: does the answer cite the expected article number?

For each off-topic question:
  The correct behavior is abstention. We check whether the answer contains an
  abstention marker instead of fabricating an answer.

The judge is question-scoped: an answer is correct if it answers what was ASKED,
consistent with the reference. Extra facts in the reference that the question did
not ask for do not need to appear in the answer.

Resumable: results are cached per question id to a local file after each call.
On a crash (e.g. Gemini 503), just run again — finished questions are skipped.
Use --fresh to ignore the cache and re-evaluate everything.

Run from the backend/ directory:
    python eval/evaluate_answers.py
    python eval/evaluate_answers.py --fresh
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import settings
from models.schemas import QueryRequest
from routes.query import query  # the real production endpoint function

# Judge model. gemini-3.5-flash would be a stronger, different model (less
# self-preference bias) but its Free-tier daily request quota is far too small
# (~20/day) for a 20-question eval. flash-lite has a much higher Free-tier quota,
# so we accept mild self-preference bias (same family as the generator) in
# exchange for being able to actually finish the run.
JUDGE_MODEL = "gemini-3.1-flash-lite"

# Each fresh question fires embed + generate + judge calls; pause to respect
# Free-tier RPM. Cached questions are not paused.
SLEEP_BETWEEN_QUESTIONS = 5.0

# Substrings that signal the assistant correctly declined (see the prompt in
# routes/query.py and the no-match fallback there).
ABSTENTION_MARKERS = ("yeterli bilgi", "bulunmamaktadır", "bulunamadı")

TEST_SET_PATH = Path(__file__).resolve().parent / "test_set.json"
CACHE_PATH = Path(__file__).resolve().parent / ".answer_eval_cache.json"

_judge_client = genai.Client(api_key=settings.gemini_api_key)


class JudgeVerdict(BaseModel):
    correct: bool
    reason: str


JUDGE_INSTRUCTION = (
    "Sen bir Türk iş hukuku değerlendirme hakemisin. Sana bir SORU, o sorunun "
    "doğru cevabını içeren bir REFERANS ve bir de değerlendirilecek ADAY CEVAP "
    "vereceğim.\n"
    "Görevin: aday cevap, SORULAN şeyi referansla tutarlı ve olgusal olarak doğru "
    "biçimde yanıtlıyorsa correct=true ver.\n"
    "Kurallar:\n"
    "- Referansta olup soruda sorulmayan ekstra bilgiler aday cevapta yer almasa "
    "da bu bir eksiklik sayılmaz.\n"
    "- Aday cevap referansla çelişiyorsa, yanlış bir sayı/süre/oran veriyorsa ya "
    "da soruyu yanıtlamıyorsa correct=false ver.\n"
    "- İfade biçimi (parafraz) değil, bilginin doğruluğu önemlidir.\n"
    "Kısa bir gerekçe yaz."
)


@retry(
    retry=retry_if_exception_type(errors.APIError),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def judge(question: str, reference: str, candidate: str) -> JudgeVerdict:
    prompt = (
        f"SORU:\n{question}\n\n"
        f"REFERANS (doğru cevap):\n{reference}\n\n"
        f"ADAY CEVAP:\n{candidate}"
    )
    response = _judge_client.models.generate_content(
        model=JUDGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=JUDGE_INSTRUCTION,
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=JudgeVerdict,
        ),
    )
    if response.parsed is not None:
        return response.parsed
    return JudgeVerdict.model_validate_json(response.text)


def cites_article(answer: str, expected_articles: list[dict]) -> bool:
    """True if the answer text mentions any expected article number near 'madde'."""
    for e in expected_articles:
        n = e["article"]
        if re.search(rf"madde\s*0*{n}\b", answer, re.IGNORECASE):
            return True
        if re.search(rf"\b{n}\s*\.?\s*(?:inci|nci|üncü|uncu)?\s*madde", answer, re.IGNORECASE):
            return True
    return False


def is_abstention(answer: str) -> bool:
    low = answer.lower()
    return any(m in low for m in ABSTENTION_MARKERS)


def load_cache(fresh: bool) -> dict:
    if fresh or not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate(fresh: bool) -> None:
    items = json.loads(TEST_SET_PATH.read_text(encoding="utf-8"))["items"]
    in_scope = [it for it in items if it["expected_articles"]]
    off_topic = [it for it in items if not it["expected_articles"]]
    cache = load_cache(fresh)
    print(f"Answer eval: {len(in_scope)} in-scope (LLM-judge) + "
          f"{len(off_topic)} off-topic (abstention). "
          f"Cached: {len(cache)}.\n")

    try:
        print("--- In-scope (answer correctness) ---")
        for item in in_scope:
            key = str(item["id"])
            if key not in cache:
                answer = query(QueryRequest(question=item["question"])).answer
                verdict = judge(item["question"], item["reference_answer"], answer)
                cache[key] = {
                    "answer": answer,
                    "correct": verdict.correct,
                    "reason": verdict.reason,
                    "cited": cites_article(answer, item["expected_articles"]),
                }
                save_cache(cache)
                time.sleep(SLEEP_BETWEEN_QUESTIONS)
            rec = cache[key]
            flag = "OK " if rec["correct"] else "BAD"
            cite_flag = "cite" if rec["cited"] else "no-cite"
            print(f"  [{flag}|{cite_flag}] id {item['id']}: {rec['reason']}")

        print("\n--- Off-topic (should abstain) ---")
        for item in off_topic:
            key = str(item["id"])
            if key not in cache:
                answer = query(QueryRequest(question=item["question"])).answer
                cache[key] = {"answer": answer, "abstained": is_abstention(answer)}
                save_cache(cache)
                time.sleep(SLEEP_BETWEEN_QUESTIONS)
            rec = cache[key]
            flag = "ABSTAIN" if rec["abstained"] else "ANSWERED"
            print(f"  [{flag}] id {item['id']}: {rec['answer'][:80]}")
    except errors.APIError as e:
        save_cache(cache)
        print(f"\n[interrupted by API error: {e}] Progress saved — re-run to resume.")
        return

    # ----- Summary (only reached when every question is done) -----
    n_in = len(in_scope)
    n_off = len(off_topic)
    correct = sum(1 for it in in_scope if cache[str(it["id"])]["correct"])
    cited = sum(1 for it in in_scope if cache[str(it["id"])]["cited"])
    abstained = sum(1 for it in off_topic if cache[str(it["id"])]["abstained"])
    print("\n" + "=" * 55)
    print(f"Answer correctness (LLM-judge): {correct}/{n_in} = {correct / n_in:.0%}")
    print(f"Article citation rate:          {cited}/{n_in} = {cited / n_in:.0%}")
    print(f"Off-topic abstention:           {abstained}/{n_off} = {abstained / n_off:.0%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM-as-judge answer correctness eval.")
    parser.add_argument("--fresh", action="store_true", help="Ignore cache and re-evaluate all questions")
    args = parser.parse_args()
    evaluate(args.fresh)
