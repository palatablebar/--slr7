"""应用配置（环境变量驱动）。"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    compose_project_name: str = "datatrace"
    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "datatrace_db"
    db_user: str = "datatrace_user"
    db_password: str = "datatrace_pwd"
    redis_url: str = "redis://redis:6379/0"
    jwt_secret: str = "change_me_to_a_long_random_string"
    jwt_algorithm: str = "HS256"
    access_token_hours: int = 12
    refresh_token_days: int = 7

    artifact_dir: str = "/data/artifacts"
    max_sql_bytes: int = 204_800
    parse_timeout_ms: int = 8_000
    parse_timeout_seconds: int = 8

    seed_demo: bool = True
    app_name: str = "DataTrace"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
