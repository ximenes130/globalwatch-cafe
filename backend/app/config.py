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
    # Chave secreta (service role ou sb_secret_…): só o backend usa, para o Storage.
    supabase_service_role_key: str | None = None
    storage_bucket: str = "analyses"
    # R6.4: URL assinada de até 5 minutos.
    signed_url_ttl_seconds: int = 300
    # Análise em `processing` há mais que isso é órfã (R2.24); a T2.11 mede o tempo real.
    stale_after_minutes: int = 15
    # R6.5: limite do upload (a validação completa é da spec 006).
    max_upload_mb: int = 20
    # Chat (spec 005): sem a chave, a rota do chat responde 503.
    anthropic_api_key: str | None = None
    # Documentação da API (/docs, /redoc, /openapi.json): só no desenvolvimento (R6.1).
    api_docs: bool = False
    # Limites diários por usuário (R6.8, R6.9).
    max_uploads_per_day: int = 20
    max_messages_per_day: int = 50

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
