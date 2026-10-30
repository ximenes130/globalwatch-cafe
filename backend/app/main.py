"""Aplicação FastAPI."""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.auth import CurrentUser, current_user
from app.config import get_settings
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


app = FastAPI(title="Global Watch API", lifespan=lifespan)

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
