from abc import ABC, abstractmethod

from google import genai
from google.genai import types
from openai import OpenAI

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 3072


class EmbeddingService(ABC):
    """Abstract interface for any embedding provider."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector size this model produces. Must match the Pinecone index dimension."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single query string. Used at query time."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple document strings. Used at ingest time.

        Default: loops over embed(). Override for provider-native batching.
        """
        return [self.embed(text) for text in texts]


# ---------------------------------------------------------------------------
# Gemini implementation
# ---------------------------------------------------------------------------

class GeminiEmbeddingService(EmbeddingService):
    """Gemini text embedding using gemini-embedding-001.

    Uses asymmetric retrieval: embed() applies RETRIEVAL_QUERY (for user
    questions at query time), embed_batch() applies RETRIEVAL_DOCUMENT (for
    legislation chunks at ingest time). This distinction improves RAG retrieval
    quality as the model optimises each vector for its intended use.

    Vectors are 3072-dimensional (the model default) and arrive pre-normalized.
    The Pinecone index must be created with dimension=3072.
    """

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIMENSION

    def embed(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=[text],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return result.embeddings[0].values

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        result = self._client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return [e.values for e in result.embeddings]


# ---------------------------------------------------------------------------
# OpenAI implementation
# ---------------------------------------------------------------------------

class OpenAIEmbeddingService(EmbeddingService):
    """OpenAI text embedding — same interface, different provider.

    Not used in production for this project (costs money / requires credit card).
    Included to illustrate how the abstraction makes the provider swappable.
    embed_batch() uses the base class loop default — no override needed.
    """

    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)

    @property
    def dimension(self) -> int:
        return 1536

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text,
        )
        return response.data[0].embedding
