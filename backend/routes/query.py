import json
from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from core.config import settings
from core.errors import NonRetryableError, RetryableError
from models.schemas import QueryRequest, QueryResponse, SourceChunk
from repositories.vector_repository import PineconeRepository
from services.embedding_service import GeminiEmbeddingService
from services.llm_service import GeminiLLMService

router = APIRouter()

TOP_K = 5

OUT_OF_SCOPE_MESSAGE = (
    "Bu konuya dair mevzuatımda yeterli bilgi bulunmamaktadır. "
    "Lütfen sorunuzu Türk iş hukuku kapsamında ifade edin."
)

# User-facing message streamed when generation fails mid-request (Turkish UX).
STREAM_ERROR_MESSAGE = "Şu anda yanıt oluşturulamıyor. Lütfen birazdan tekrar deneyin."

_embedding_service = GeminiEmbeddingService(api_key=settings.gemini_api_key)
_llm_service = GeminiLLMService(api_key=settings.gemini_api_key)
_repo = PineconeRepository(
    api_key=settings.pinecone_api_key,
    index_name=settings.pinecone_index_name,
)


def _build_context(matches) -> str:
    parts = []
    for m in matches:
        meta = m.metadata
        label = f"{meta.get('article_type', 'Madde')} {meta.get('article_number', '?')}"
        parts.append(f"[{label}]\n{meta.get('text', '')}")
    return "\n\n---\n\n".join(parts)


def _build_prompt(question: str, context: str) -> str:
    return (
        "Sen, vatandaşlara yardımcı olan bir Türk iş hukuku asistanısın. "
        "Aşağıdaki kanun maddelerine dayanarak soruyu Türkçe yanıtla. Kurallara uy:\n"
        "- Yalnızca verilen maddelere dayan; bu maddelerde soruyu yanıtlayacak "
        "yeterli bilgi yoksa 'Bu konuya dair mevzuatımda yeterli bilgi "
        "bulunmamaktadır.' de ve dur; başka tavsiye ekleme.\n"
        "- Cevabı, hukuk bilmeyen bir vatandaşın kolayca anlayacağı sade ve "
        "gündelik bir Türkçeyle yaz; ağır hukuki terimlerden kaçın, kullanman "
        "gerekiyorsa parantez içinde kısaca açıkla.\n"
        "- Doğruluktan ödün verme: maddedeki sayı, süre ve oranları (gün, hafta, "
        "yüzde vb.) aynen ve eksiksiz aktar.\n"
        "- Cevabının sonunda dayandığın maddeyi belirt (örneğin: 'Dayanak: Madde 53').\n\n"
        f"KANUN MADDELERİ:\n{context}\n\n"
        f"SORU: {question}\n\n"
        "CEVAP:"
    )


def _build_sources(matches) -> list[SourceChunk]:
    return [
        SourceChunk(
            law=m.metadata.get("law", "İş Kanunu"),
            article_number=str(int(m.metadata.get("article_number", 0))),
            article_type=m.metadata.get("article_type", "Madde"),
            article_title=m.metadata.get("title") or None,
            text=m.metadata.get("text", ""),
        )
        for m in matches
    ]


@dataclass
class PreparedQuery:
    """Outcome of retrieval + relevance gating, shared by both query paths.

    prompt is None when the question is out of scope — the caller should abstain
    (return / stream OUT_OF_SCOPE_MESSAGE) with the empty sources list.
    """
    sources: list[SourceChunk]
    prompt: str | None


def _prepare(question: str) -> PreparedQuery:
    """Embed, retrieve, and apply the relevance gate. Identical for streaming and
    non-streaming so both honour the same abstention behaviour eval measures."""
    question_vector = _embedding_service.embed(question)
    matches = _repo.query(vector=question_vector, top_k=TOP_K)

    # Relevance gate: if even the best match is below the threshold, the question
    # is out of scope — abstain with zero sources (no junk context, no junk chips).
    if not matches or matches[0].score < settings.relevance_min_score:
        return PreparedQuery(sources=[], prompt=None)

    prompt = _build_prompt(question, _build_context(matches))
    return PreparedQuery(sources=_build_sources(matches), prompt=prompt)


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    prepared = _prepare(request.question)
    if prepared.prompt is None:
        return QueryResponse(answer=OUT_OF_SCOPE_MESSAGE, sources=[])

    try:
        answer = _llm_service.generate(prepared.prompt)
    except NonRetryableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RetryableError:
        raise HTTPException(status_code=503, detail="The AI service is temporarily unavailable. Please try again in a moment.")
    except Exception:
        raise HTTPException(status_code=503, detail="LLM service temporarily unavailable.")

    return QueryResponse(answer=answer, sources=prepared.sources)


def _sse(payload: dict) -> str:
    """Format one SSE frame: a single `data:` line plus the blank-line delimiter.
    ensure_ascii=False keeps Turkish characters intact instead of \\uXXXX escapes."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/query/stream")
def query_stream(request: QueryRequest) -> StreamingResponse:
    def event_stream() -> Iterator[str]:
        # Retrieval + gating happen before any frame is sent, so a failure here
        # can still surface as a clean error frame with nothing half-streamed.
        try:
            prepared = _prepare(request.question)
        except Exception:
            yield _sse({"type": "error", "message": STREAM_ERROR_MESSAGE})
            return

        # Sources first (empty list when out of scope) — chips can render while
        # the answer is still typing.
        yield _sse({"type": "sources", "sources": [s.model_dump() for s in prepared.sources]})

        try:
            if prepared.prompt is None:
                # Out of scope: stream the fixed abstention text as the answer.
                yield _sse({"type": "token", "text": OUT_OF_SCOPE_MESSAGE})
            else:
                for piece in _llm_service.generate_stream(prepared.prompt):
                    yield _sse({"type": "token", "text": piece})
        except Exception:
            yield _sse({"type": "error", "message": STREAM_ERROR_MESSAGE})
            return

        yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        # Defensive against proxy buffering (nginx/Render): without these a proxy
        # may hold the whole response, killing the stream. See 10.5 gateway note.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
