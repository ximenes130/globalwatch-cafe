"""Configuração lida de variáveis de ambiente (segredos nunca no código)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Pooler do Supabase (Supavisor); ver specs/001-fundacao-auth-deploy/design.md.
    database_url: str | None = None
    # https://<ref>.supabase.co; deriva o issuer e o JWKS do JWT.
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    # Lista separada por vírgula. Restrição final ao domínio do front: T6.5.
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
