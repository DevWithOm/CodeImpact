from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CodeImpact API"
    app_env: str = "development"
    api_prefix: str = "/api"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    # Gemini / Gemma AI configuration
    gemini_api_key: str | None = None
    gemini_model: str = "gemma-4-31b-it"


settings = Settings()
