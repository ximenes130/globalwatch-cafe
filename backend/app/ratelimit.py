"""Limites diários por usuário em `usage_daily` (R6.8, R6.9).

Contador no Postgres, e não em memória: sobrevive a reinício e à hibernação do Render.
O incremento é uma única instrução (`insert … on conflict do update … where`): duas
requisições ao mesmo tempo não passam juntas do limite. O dia é o `current_date` do
banco (UTC no Supabase).
"""

from typing import Annotated, Literal, Protocol
from uuid import UUID

from fastapi import Depends, HTTPException, status
from psycopg import sql
from psycopg_pool import ConnectionPool

from app import db

Kind = Literal["uploads", "messages"]

LIMIT_MESSAGES: dict[Kind, str] = {
    "uploads": "Você chegou ao limite de {limit} envios de imagem por dia. Tente de novo amanhã.",
    "messages": "Você chegou ao limite de {limit} mensagens no chat por dia. Tente de novo amanhã.",
}


class UsageCounter(Protocol):
    def consume(self, user_id: UUID, kind: Kind, limit: int) -> bool:
        """Conta um uso se o usuário ainda estiver abaixo do limite de hoje."""
        ...

    def today(self, user_id: UUID) -> dict:
        """Uso de hoje sem contar nada: `uploads`, `messages` e `resets_at` (R6.16)."""
        ...


class UsageRepository:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    def consume(self, user_id: UUID, kind: Kind, limit: int) -> bool:
        # `kind` vira nome de coluna: só os dois valores conhecidos passam.
        if kind not in LIMIT_MESSAGES:
            raise ValueError(f"tipo de uso desconhecido: {kind}")
        column = sql.Identifier(kind)
        query = sql.SQL(
            """
            insert into usage_daily (user_id, day, {column}) values (%s, current_date, 1)
            on conflict (user_id, day) do update
                set {column} = usage_daily.{column} + 1
                where usage_daily.{column} < %s
            returning {column}
            """
        ).format(column=column)
        with self.pool.connection() as conn:
            # Sem linha de volta: o `where` barrou o incremento, o limite já foi atingido.
            return conn.execute(query, (user_id, limit)).fetchone() is not None

    def today(self, user_id: UUID) -> dict:
        # A renovação sai do banco: a mesma meia-noite do `current_date` usado no limite.
        with self.pool.connection() as conn:
            uploads, messages, resets_at = conn.execute(
                """
                select coalesce(u.uploads, 0), coalesce(u.messages, 0),
                       (current_date + 1)::timestamptz
                from (select 1) as one
                left join usage_daily u on u.user_id = %s and u.day = current_date
                """,
                (user_id,),
            ).fetchone()
        return {"uploads": uploads, "messages": messages, "resets_at": resets_at}


def get_usage() -> UsageCounter:
    pool = db.get_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponível.")
    return UsageRepository(pool)


Usage = Annotated[UsageCounter, Depends(get_usage)]


def consume_or_429(usage: UsageCounter, user_id: UUID, kind: Kind, limit: int) -> None:
    if not usage.consume(user_id, kind, limit):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, LIMIT_MESSAGES[kind].format(limit=limit)
        )
