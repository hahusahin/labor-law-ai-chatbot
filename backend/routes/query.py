from fastapi import APIRouter, HTTPException

from core.config import settings
from core.errors import NonRetryableError, RetryableError
from models.schemas import QueryRequest, QueryResponse, SourceChunk
from repositories.vector_repository import PineconeRepository
from services.embedding_service import GeminiEmbeddingService
from services.llm_service import GeminiLLMService

router = APIRouter()

TOP_K = 5

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
        "Sen bir Türk iş hukuku asistanısın. "
        "Yalnızca Türk iş hukuku ve İş Kanunu ile ilgili sorulara cevap ver. "
        "Soru iş hukuku ile ilgili değilse, bunu kibarca belirt ve yalnızca iş hukuku konularında yardımcı olabileceğini söyle. "
        "Aşağıdaki kanun maddelerine dayanarak soruyu Türkçe olarak yanıtla. "
        "Yalnızca verilen maddelere dayan; eğer cevap bu maddelerde yoksa bunu açıkça belirt. "
        "Cevabında hangi maddeye dayandığını mutlaka belirt (örneğin: 'Madde 53 uyarınca...').\n\n"
        f"KANUN MADDELERİ:\n{context}\n\n"
        f"SORU: {question}\n\n"
        "CEVAP:"
    )


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    question_vector = _embedding_service.embed(request.question)
    matches = _repo.query(vector=question_vector, top_k=TOP_K)

    if not matches:
        return QueryResponse(
            answer="Bu soruyla ilgili kanun maddesi bulunamadı. Lütfen sorunuzu iş kanunu kapsamında yeniden ifade edin.",
            sources=[],
        )

    context = _build_context(matches)

    try:
        answer = _llm_service.generate(_build_prompt(request.question, context))
    except NonRetryableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RetryableError:
        raise HTTPException(status_code=503, detail="The AI service is temporarily unavailable. Please try again in a moment.")
    except Exception:
        raise HTTPException(status_code=503, detail="LLM service temporarily unavailable.")

    sources = [
        SourceChunk(
            law=m.metadata.get("law", "İş Kanunu"),
            article_number=str(int(m.metadata.get("article_number", 0))),
            article_type=m.metadata.get("article_type", "Madde"),
            article_title=m.metadata.get("title") or None,
            text=m.metadata.get("text", ""),
        )
        for m in matches
    ]

    return QueryResponse(answer=answer, sources=sources)
