from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    pinecone_api_key: str
    pinecone_index_name: str
    frontend_url: str = "http://localhost:3000"
    internal_api_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
