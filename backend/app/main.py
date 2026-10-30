"""Aplicação FastAPI."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.auth import CurrentUser, current_user
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.open_pool(settings.database_url)
    yield
    db.close_pool()


app = FastAPI(title="Global Watch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Público. Sempre 200 (health check do Render); o estado do banco vai em `db`."""
    return {"status": "ok", "db": db.check()}


@app.get("/me")
def me(user: Annotated[CurrentUser, Depends(current_user)]) -> dict[str, str | None]:
    """Protegido. Prova ponta a ponta que o backend valida o JWT."""
    return {"user_id": str(user.id), "email": user.email}
