"""Conexão com o Postgres do Supabase."""

import logging

from psycopg_pool import ConnectionPool

log = logging.getLogger(__name__)

_pool: ConnectionPool | None = None


def open_pool(database_url: str | None) -> None:
    """Cria o pool sem conectar (min_size=0): a API sobe mesmo com o banco fora."""
    global _pool
    if not database_url:
        log.warning("DATABASE_URL ausente; rotas que usam o banco ficam indisponíveis")
        return
    _pool = ConnectionPool(
        database_url,
        min_size=0,
        max_size=4,
        open=True,
        # O pooler em modo transação não suporta prepared statements.
        kwargs={"prepare_threshold": None, "connect_timeout": 5},
    )


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def check() -> str:
    """Executa `select 1`. Devolve "ok", "error" ou "not_configured"."""
    if _pool is None:
        return "not_configured"
    try:
        with _pool.connection(timeout=5) as conn:
            conn.execute("select 1")
    except Exception:
        log.exception("Falha no select 1 do health check")
        return "error"
    return "ok"
