"""Rotas `/analyses` (R2.21, R2.22, R2.24, R2.25, R3.10).

Todas exigem JWT (`current_user`) e só enxergam análises do próprio usuário:
análise alheia ou inexistente responde 404 (C3.2).
"""

from pathlib import PurePath
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app import db
from app.auth import CurrentUser, current_user
from app.config import Settings, get_settings
from app.ratelimit import Usage, consume_or_429
from app.repository import AnalysisRepository, Repository
from app.storage import Storage, StorageError, SupabaseStorage, object_prefix
from app.worker import run_analysis

router = APIRouter(prefix="/analyses", tags=["analyses"])

# Chave da resposta → arquivo no Storage.
RESULT_FILES = {
    "rgb_png": "rgb.png",
    "classification_png": "classification.png",
    "polygons_png": "polygons.png",
    "geojson": "result.geojson",
}
ALL_FILES = ["original.tif", "scl.tif", "original_2.tif", "scl_2.tif", *RESULT_FILES.values()]
NOT_FOUND = "Análise não encontrada."


def get_repository() -> Repository:
    pool = db.get_pool()
    if pool is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Banco de dados indisponível.")
    return AnalysisRepository(pool)


def get_storage(settings: Annotated[Settings, Depends(get_settings)]) -> Storage:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Armazenamento indisponível.")
    return SupabaseStorage(
        settings.supabase_url,
        settings.supabase_service_role_key,
        settings.storage_bucket,
        settings.signed_url_ttl_seconds,
    )


User = Annotated[CurrentUser, Depends(current_user)]
Repo = Annotated[Repository, Depends(get_repository)]
Store = Annotated[Storage, Depends(get_storage)]
Config = Annotated[Settings, Depends(get_settings)]


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_analysis(
    response: Response,
    background: BackgroundTasks,
    user: User,
    repository: Repo,
    storage: Store,
    settings: Config,
    usage: Usage,
    image: Annotated[UploadFile, File()],
    scl: Annotated[UploadFile | None, File()] = None,
    image_2: Annotated[UploadFile | None, File()] = None,
    scl_2: Annotated[UploadFile | None, File()] = None,
) -> dict:
    """Cria a análise em `processing` e responde na hora; o pipeline roda depois (R2.22).

    `image_2`/`scl_2`: segunda data opcional da mesma área (R3.10).
    """
    if scl_2 is not None and image_2 is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Envie a segunda imagem junto da SCL dela."
        )
    limit_mb = settings.max_upload_mb
    image_bytes, scl_bytes, image_2_bytes, scl_2_bytes = (
        _read_limited(upload, limit_mb) if upload else None
        for upload in (image, scl, image_2, scl_2)
    )

    # Conta quando o envio é aceito: uma análise que falha depois continua contando (R6.8).
    consume_or_429(usage, user.id, "uploads", settings.max_uploads_per_day)
    analysis_id = repository.create(user.id, _clean_filename(image.filename))
    background.add_task(
        run_analysis,
        analysis_id,
        user.id,
        image_bytes,
        scl_bytes,
        repository,
        storage,
        image_2=image_2_bytes,
        scl_2=scl_2_bytes,
    )
    response.headers["Location"] = f"/analyses/{analysis_id}"
    return {"id": str(analysis_id), "status": "processing"}


@router.get("")
def list_analyses(user: User, repository: Repo, settings: Config) -> list[dict]:
    repository.expire_stale(user.id, settings.stale_after_minutes)
    return repository.list(user.id)


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: UUID, user: User, repository: Repo, storage: Store, settings: Config
) -> dict:
    repository.expire_stale(user.id, settings.stale_after_minutes)
    row = repository.get(user.id, analysis_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)

    urls = None
    if row["status"] == "completed":
        prefix = object_prefix(user.id, analysis_id)
        paths = {key: f"{prefix}/{name}" for key, name in RESULT_FILES.items()}
        try:
            signed = storage.signed_urls(list(paths.values()))
        except StorageError as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Não foi possível gerar os links dos arquivos agora. Tente de novo.",
            ) from exc
        urls = {key: signed[path] for key, path in paths.items()}

    row.pop("user_id", None)
    return {**row, "urls": urls}


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: UUID, user: User, repository: Repo, storage: Store, settings: Config
) -> Response:
    repository.expire_stale(user.id, settings.stale_after_minutes)
    row = repository.get(user.id, analysis_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND)
    if row["status"] == "processing":
        # Apagar no meio deixaria o worker gravando arquivos de uma análise que sumiu.
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Aguarde o fim do processamento para apagar a análise."
        )

    prefix = object_prefix(user.id, analysis_id)
    try:
        # Arquivos antes da linha: se o Storage falhar, nada fica sem dono.
        storage.remove([f"{prefix}/{name}" for name in ALL_FILES])
    except StorageError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Não foi possível apagar os arquivos agora. Tente de novo.",
        ) from exc
    repository.delete(user.id, analysis_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _read_limited(upload: UploadFile, limit_mb: int) -> bytes:
    """Lê no máximo o limite + 1 byte: passou disso, 413 sem guardar o resto (R6.5)."""
    limit = limit_mb * 1024 * 1024
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"O arquivo passa do limite de {limit_mb} MB."
        )
    return data


def _clean_filename(name: str | None) -> str:
    # Só o nome, sem pastas enviadas pelo navegador, e com tamanho limitado.
    return PurePath(name or "").name[:200] or "imagem.tif"
