from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="D2L_AI_", env_file=".env", extra="ignore")

    app_name: str = "d2l-ai-api"
    environment: str = Field(default="dev")
    log_level: str = Field(default="INFO")
    otel_enabled: bool = Field(default=False)


settings = Settings()
