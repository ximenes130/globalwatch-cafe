"""Processamento em plano de fundo (R2.1, R2.19, R2.22, R2.23).

`run_analysis` roda depois da resposta 202, numa thread do threadpool do
Starlette (`BackgroundTasks`). Um semáforo deixa só um processamento por vez:
com 512 MB no Render free, dois rasters grandes juntos arriscam a memória.
"""

import json
import logging
import threading
import time
from uuid import UUID

from app.processing.errors import ProcessingError
from app.processing.params import Params
from app.processing.pipeline import run_pipeline
from app.repository import Repository
from app.storage import Storage, object_prefix

log = logging.getLogger(__name__)

PROCESSING_SLOT = threading.Semaphore(1)

# Mensagem para falhas inesperadas: o detalhe fica só no log do servidor (R2.19).
UNEXPECTED_ERROR = (
    "Não foi possível processar a imagem por um erro interno. Tente de novo mais tarde."
)

CONTENT_TYPES = {".tif": "image/tiff", ".png": "image/png", ".geojson": "application/geo+json"}


def run_analysis(
    analysis_id: UUID,
    user_id: UUID,
    image: bytes,
    scl: bytes | None,
    repository: Repository,
    storage: Storage,
    params: Params | None = None,
) -> None:
    """Processa, grava os arquivos e depois a linha; nunca deixa exceção escapar."""
    params = params or Params()
    with PROCESSING_SLOT:
        started = time.perf_counter()
        try:
            result = run_pipeline(image, scl, params)
            files = {
                "original.tif": image,
                **({"scl.tif": scl} if scl is not None else {}),
                **result.images,
                "result.geojson": json.dumps(result.geojson).encode(),
            }
            prefix = object_prefix(user_id, analysis_id)
            # Arquivos antes da linha: análise `completed` sempre tem os arquivos.
            for name, data in files.items():
                storage.upload(f"{prefix}/{name}", data, content_type(name))
            repository.complete(analysis_id, result)
            status = "completed"
        except ProcessingError as exc:
            status = "failed"
            _fail(repository, analysis_id, str(exc))
        except Exception:
            status = "failed"
            log.exception("Falha inesperada na análise %s", analysis_id)
            _fail(repository, analysis_id, UNEXPECTED_ERROR)
        log.info(
            "Análise %s terminou como %s em %.2f s",
            analysis_id,
            status,
            time.perf_counter() - started,
        )


def content_type(name: str) -> str:
    return CONTENT_TYPES[name[name.rindex(".") :]]


def _fail(repository: Repository, analysis_id: UUID, message: str) -> None:
    # Se nem gravar a falha der certo (banco fora), a linha fica em `processing`
    # e expira sozinha depois (R2.24).
    try:
        repository.fail(analysis_id, message)
    except Exception:
        log.exception("Não foi possível gravar a falha da análise %s", analysis_id)
