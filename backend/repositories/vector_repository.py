from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class QueryMatch:
    id: str
    score: float
    metadata: dict = field(default_factory=dict)


class VectorRepository(ABC):
    """Abstract interface for any vector database backend."""

    @abstractmethod
    def upsert(self, vectors: list[dict]) -> None:
        """Store or overwrite vectors. Each dict must have 'id', 'values', 'metadata'."""

    @abstractmethod
    def query(self, vector: list[float], top_k: int) -> list[QueryMatch]:
        """Return the top_k most similar vectors to the given query vector."""

    @abstractmethod
    def clear(self) -> None:
        """Delete all vectors from the index."""


class PineconeRepository(VectorRepository):
    def __init__(self, api_key: str, index_name: str) -> None:
        from pinecone import Pinecone
        pc = Pinecone(api_key=api_key)
        self._index = pc.Index(index_name)

    def upsert(self, vectors: list[dict]) -> None:
        self._index.upsert(vectors=vectors)

    def query(self, vector: list[float], top_k: int) -> list[QueryMatch]:
        result = self._index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
        )
        return [
            QueryMatch(id=m.id, score=m.score, metadata=m.metadata or {})
            for m in result.matches
        ]

    def clear(self) -> None:
        self._index.delete(delete_all=True)
