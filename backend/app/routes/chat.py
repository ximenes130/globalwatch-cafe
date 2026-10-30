"""Rota do chat de uma análise (spec 005).

A análise vem da rota e é conferida contra o dono antes de qualquer coisa (R5.5):
análise alheia ou inexistente responde 404, como em `/analyses`.
"""

import logging
from typing import Annotated, Literal
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from app import db
from app.chat.client import ChatUnavailable, converse, make_client
from app.chat.prompt import intro_content
from app.chat.tools import AnalysisTools
from app.config import Settings, get_settings
from app.repository import ChatMessageRepository, ChatRepository
from app.routes.analyses import NOT_FOUND, Config, Repo, Store, User
from app.storage import StorageError, object_prefix

log = logging.getLogger(__name__)

router = APIRouter(prefix="/analyses", tags=["chat"])

MAX_MESSAGE_CHARS = 1000
MAX_HISTORY_CHARS = 4000
# Só as últimas mensagens vão ao modelo (R5.6).
HISTORY_LIMIT = 10
# Quando o histórico cortado começa na vez do assistente, a API precisa de uma mensagem
# do usuário antes: o pedido original da conversa, sem a imagem.
HISTORY_OPENER = "Apresente esta análise."


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_HISTORY_CHARS)


class ChatRequest(BaseModel):
    # `None` só na apresentação, com o histórico vazio (R5.1).
    message: str | None = Field(default=None, max_length=MAX_MESSAGE_CHARS)
    history: list[HistoryItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def message_or_intro(self):
        if self.message is None and self.history:
            raise ValueError("Envie a mensagem; só a apresentação vai sem texto.")
        if self.message is not None and not self.message.strip():
            raise ValueError("A mensagem está vazia.")
        return self


def get_chat_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Assistente indisponível.")
    return make_client(settings.anthropic_api_key)


ChatClient = Annotated[anthropic.Anthropic, Depends(get_chat_client)]


def get_chat_repository() -> ChatRepository:
    pool = db.get_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponível.")
    return ChatMessageRepository(pool)


Messages = Annotated[ChatRepository, Depends(get_chat_repository)]


@router.get("/{analysis_id}/chat")
def chat_history(analysis_id: UUID, user: User, repository: Repo, messages: Messages) -> list:
    """Conversa gravada da análise, com os cards de cada resposta (R5.9)."""
    if repository.get(user.id, analysis_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    return messages.history(user.id, analysis_id)


@router.post("/{analysis_id}/chat")
def chat(
    analysis_id: UUID,
    body: ChatRequest,
    user: User,
    repository: Repo,
    storage: Store,
    settings: Config,
    client: ChatClient,
    stored: Messages,
) -> dict:
    repository.expire_stale(user.id, settings.stale_after_minutes)
    row = repository.get(user.id, analysis_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    if row["status"] != "completed":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "O chat abre quando a análise termina de processar."
        )

    prefix = object_prefix(user.id, analysis_id)
    tools = AnalysisTools(row, storage, prefix)

    if body.message is None:
        try:
            picture = storage.download(f"{prefix}/polygons.png")
        except StorageError as exc:
            log.warning("Chat: imagem da análise %s indisponível: %s", analysis_id, exc)
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Não foi possível ler a imagem da análise agora. Tente de novo.",
            ) from exc
        messages = [{"role": "user", "content": intro_content(picture)}]
    else:
        history = [item.model_dump() for item in body.history[-HISTORY_LIMIT:]]
        if history and history[0]["role"] == "assistant":
            history.insert(0, {"role": "user", "content": HISTORY_OPENER})
        messages = [*history, {"role": "user", "content": body.message.strip()}]

    try:
        result = converse(client, tools, messages, force_summary=body.message is None)
    except ChatUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    exchange = [{"role": "assistant", "content": result.reply, "cards": result.cards}]
    if body.message is not None:
        exchange.insert(0, {"role": "user", "content": body.message.strip()})
    try:
        stored.append(user.id, analysis_id, exchange)
    except Exception:
        # A resposta já existe e custou uma chamada ao modelo: entrega mesmo sem gravar.
        log.exception("Chat: não foi possível gravar a conversa da análise %s", analysis_id)
    return {"reply": result.reply, "cards": result.cards}
