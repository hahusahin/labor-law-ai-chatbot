from abc import ABC, abstractmethod

import google.generativeai as genai
from openai import OpenAI

GEMINI_EMBEDDING_MODEL = "models/text-embedding-004"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


class EmbeddingService(ABC):
    """Abstract interface for any embedding provider."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector size this model produces. Must match the Pinecone index dimension."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single text string into a vector."""

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts. Override for provider-native batching."""
        return [self.embed(text) for text in texts]


# ---------------------------------------------------------------------------
# Gemini implementation
# ---------------------------------------------------------------------------

class GeminiEmbeddingService(EmbeddingService):
    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)

    @property
    def dimension(self) -> int:
        return 768

    def embed(self, text: str) -> list[float]:
        response = genai.embed_content(model=GEMINI_EMBEDDING_MODEL, content=text)
        return response["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = genai.embed_content(model=GEMINI_EMBEDDING_MODEL, content=texts)
        return response["embedding"]


# ---------------------------------------------------------------------------
# OpenAI implementation
# ---------------------------------------------------------------------------

class OpenAIEmbeddingService(EmbeddingService):
    """
    Not used in production for this project (costs money).
    Included to illustrate how frontier embedding APIs compare.
    Requires OPENAI_API_KEY in .env.
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

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]
