"""Retenção de 7 dias (R6.15, T6.7).

Rodada uma vez por dia pelo GitHub Actions (`.github/workflows/retention.yml`):

    cd backend && python -m app.retention

Para cada análise com mais de 7 dias, de qualquer usuário: arquivos no Storage
primeiro, depois a linha (as mensagens do chat saem por `on delete cascade`). Se o
Storage falhar, a linha fica para a próxima execução, e o código de saída 1 deixa o job
vermelho.
"""

import logging
import sys

from app import db
from app.config import get_settings
from app.repository import AnalysisRepository
from app.routes.analyses import ALL_FILES
from app.storage import Storage, StorageError, SupabaseStorage, object_prefix

log = logging.getLogger(__name__)

RETENTION_DAYS = 7


def purge_expired(
    repository: AnalysisRepository, storage: Storage, days: int = RETENTION_DAYS
) -> tuple[int, int]:
    """Apaga as análises vencidas; devolve `(apagadas, falhas)`."""
    removed = failures = 0
    for analysis_id, user_id in repository.list_expired(days):
        prefix = object_prefix(user_id, analysis_id)
        try:
            storage.remove([f"{prefix}/{name}" for name in ALL_FILES])
        except StorageError:
            log.exception(
                "Retenção: arquivos da análise %s não saíram; fica para amanhã", analysis_id
            )
            failures += 1
            continue
        repository.delete(user_id, analysis_id)
        removed += 1
    return removed, failures


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")
    settings = get_settings()
    if not (settings.database_url and settings.supabase_url and settings.supabase_service_role_key):
        log.error("Retenção: faltam DATABASE_URL, SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY")
        return 2
    db.open_pool(settings.database_url)
    try:
        storage = SupabaseStorage(
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.storage_bucket,
            settings.signed_url_ttl_seconds,
        )
        removed, failures = purge_expired(AnalysisRepository(db.get_pool()), storage)
    finally:
        db.close_pool()
    log.info("Retenção: %d análise(s) apagada(s), %d falha(s)", removed, failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
