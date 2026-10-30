"""Aplicação FastAPI."""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.auth import CurrentUser, current_user
from app.config import get_settings
from app.errors import NeutralErrors
from app.ratelimit import Usage
from app.retention import RETENTION_DAYS
from app.routes import analyses, chat

settings = get_settings()

# O uvicorn só configura os próprios loggers: sem handler no root, os `log.info` de `app.*`
# (como a duração de cada análise, lida no log do Render na T2.11) eram descartados.
# INFO só para `app`; as bibliotecas continuam em WARNING.
logging.basicConfig(level=logging.WARNING, format="%(levelname)s:     %(name)s - %(message)s")
logging.getLogger("app").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Lido na subida, não na importação: os testes trocam o ambiente antes de
    # subir o app, e assim nunca conectam no banco real do `.env`.
    db.open_pool(get_settings().database_url)
    yield
    db.close_pool()


# R6.1: só `/health` é público. A documentação da API fica desligada fora do
# desenvolvimento (`API_DOCS=true` liga).
docs = settings.api_docs
app = FastAPI(
    title="Global Watch API",
    lifespan=lifespan,
    docs_url="/docs" if docs else None,
    redoc_url="/redoc" if docs else None,
    openapi_url="/openapi.json" if docs else None,
)

# Antes do CORS: o último registrado fica por fora, e o 500 neutro precisa dos cabeçalhos
# de CORS (ver app/errors.py).
app.add_middleware(NeutralErrors)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    # O POST /analyses devolve a URL da análise criada (R2.22).
    expose_headers=["Location"],
)

app.include_router(analyses.router)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Público. Sempre 200 (health check do Render); o estado do banco vai em `db`."""
    return {"status": "ok", "db": db.check()}


@app.get("/me")
def me(user: Annotated[CurrentUser, Depends(current_user)]) -> dict[str, str | None]:
    """Protegido. Prova ponta a ponta que o backend valida o JWT."""
    return {"user_id": str(user.id), "email": user.email}


@app.get("/me/usage")
def my_usage(user: Annotated[CurrentUser, Depends(current_user)], usage: Usage) -> dict:
    """Cota de hoje e retenção, para a interface mostrar os limites (R6.16 a R6.19)."""
    settings = get_settings()
    today = usage.today(user.id)
    return {
        "uploads": {"used": today["uploads"], "limit": settings.max_uploads_per_day},
        "messages": {"used": today["messages"], "limit": settings.max_messages_per_day},
        "resets_at": today["resets_at"],
        "retention_days": RETENTION_DAYS,
    }
