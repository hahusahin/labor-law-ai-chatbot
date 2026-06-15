from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    law: str
    article_number: str
    article_title: str | None = None
    text: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
