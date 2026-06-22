from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str
    frontend_url: str = "http://localhost:3000"
    internal_api_key: str

    # Retrieval relevance gate: if the top match scores below this, treat the
    # question as out of scope and abstain with zero sources. Tuned from the eval
    # score distribution (off-topic top-1 <= 0.690 < 0.695 <= in-scope top-1),
    # NOT a guessed number. The 0.011 gap is thin, so this is env-tunable and
    # should be revisited with more data / a reranker (Phase 2).
    relevance_min_score: float = 0.695

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
