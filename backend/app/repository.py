"""Acesso à tabela `analyses` (spec 002).

O backend conecta com um papel que ignora a RLS, então toda consulta filtra
por `user_id` explicitamente (C3.2). Análise de outro usuário e análise
inexistente dão o mesmo resultado (`None`/`False`), que a rota traduz em 404.
"""

from typing import Protocol
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.processing.pipeline import AnalysisResult

# Mensagem gravada quando a análise fica órfã (R2.24).
STALE_MESSAGE = "O processamento foi interrompido (o servidor reiniciou). Envie o arquivo de novo."

LIST_COLUMNS = """
    id, filename, created_at, status, acquired_at,
    (stats ->> 'potential_area_ha')::float8 as potential_area_ha
"""
DETAIL_COLUMNS = """
    id, user_id, status, filename, created_at, acquired_at, crs, bounds_wgs84,
    stats, params, method_version, rationale, error
"""


class Repository(Protocol):
    def create(self, user_id: UUID, filename: str) -> UUID: ...

    def complete(self, analysis_id: UUID, result: AnalysisResult) -> None: ...

    def fail(self, analysis_id: UUID, message: str) -> None: ...

    def expire_stale(self, user_id: UUID, minutes: int) -> int: ...

    def list(self, user_id: UUID) -> list[dict]: ...

    def get(self, user_id: UUID, analysis_id: UUID) -> dict | None: ...

    def delete(self, user_id: UUID, analysis_id: UUID) -> bool: ...


class AnalysisRepository:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def create(self, user_id: UUID, filename: str) -> UUID:
        with self.pool.connection() as conn:
            row = conn.execute(
                "insert into analyses (user_id, filename) values (%s, %s) returning id",
                (user_id, filename),
            ).fetchone()
        return row[0]

    def complete(self, analysis_id: UUID, result: AnalysisResult) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                """
                update analyses set
                    status = 'completed', acquired_at = %s, crs = %s, bounds_wgs84 = %s,
                    stats = %s, params = %s, method_version = %s, rationale = %s, error = null
                where id = %s and status = 'processing'
                """,
                (
                    result.acquired_at,
                    result.crs,
                    Jsonb(result.bounds_wgs84),
                    Jsonb(result.stats),
                    Jsonb(result.params),
                    result.method_version,
                    Jsonb(result.rationale),
                    analysis_id,
                ),
            )

    def fail(self, analysis_id: UUID, message: str) -> None:
        with self.pool.connection() as conn:
            conn.execute(
                "update analyses set status = 'failed', error = %s "
                "where id = %s and status = 'processing'",
                (message, analysis_id),
            )

    def expire_stale(self, user_id: UUID, minutes: int) -> int:
        """Marca como `failed` as análises do usuário presas em `processing` (R2.24)."""
        with self.pool.connection() as conn:
            cursor = conn.execute(
                """
                update analyses set status = 'failed', error = %s
                where user_id = %s and status = 'processing'
                  and created_at < now() - make_interval(mins => %s)
                """,
                (STALE_MESSAGE, user_id, minutes),
            )
            return cursor.rowcount

    def list(self, user_id: UUID) -> list[dict]:
        with self.pool.connection() as conn:
            cursor = conn.cursor(row_factory=dict_row)
            return cursor.execute(
                f"select {LIST_COLUMNS} from analyses where user_id = %s order by created_at desc",
                (user_id,),
            ).fetchall()

    def get(self, user_id: UUID, analysis_id: UUID) -> dict | None:
        with self.pool.connection() as conn:
            cursor = conn.cursor(row_factory=dict_row)
            return cursor.execute(
                f"select {DETAIL_COLUMNS} from analyses where id = %s and user_id = %s",
                (analysis_id, user_id),
            ).fetchone()

    def delete(self, user_id: UUID, analysis_id: UUID) -> bool:
        with self.pool.connection() as conn:
            cursor = conn.execute(
                "delete from analyses where id = %s and user_id = %s", (analysis_id, user_id)
            )
            return cursor.rowcount == 1


class ChatRepository(Protocol):
    def history(self, user_id: UUID, analysis_id: UUID) -> list[dict]: ...

    def append(self, user_id: UUID, analysis_id: UUID, messages: list[dict]) -> None: ...


class ChatMessageRepository:
    """Conversa de uma análise em `chat_messages` (T5.5, R5.9), sempre filtrada por `user_id`."""

    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def history(self, user_id: UUID, analysis_id: UUID) -> list[dict]:
        # Cursor próprio com `dict_row`: mudar a conexão afetaria quem a pegar depois no pool.
        with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cursor:
            return cursor.execute(
                """
                select id, role, content, cards, created_at from chat_messages
                where user_id = %s and analysis_id = %s
                order by created_at, id
                """,
                (user_id, analysis_id),
            ).fetchall()

    def append(self, user_id: UUID, analysis_id: UUID, messages: list[dict]) -> None:
        """Pergunta e resposta juntas: numa transação, nenhuma fica sem a outra."""
        with self.pool.connection() as conn, conn.transaction(), conn.cursor() as cursor:
            cursor.executemany(
                """
                insert into chat_messages (analysis_id, user_id, role, content, cards)
                values (%s, %s, %s, %s, %s)
                """,
                [
                    (analysis_id, user_id, m["role"], m["content"], Jsonb(m.get("cards", [])))
                    for m in messages
                ],
            )
