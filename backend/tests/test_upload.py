"""Validação do upload na rota (T6.1, R6.5, R6.6, R6.7).

Arquivo recusado não cria análise nem conta na cota diária.
"""

from types import SimpleNamespace
from uuid import UUID

import numpy as np
import pytest
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from app.auth import CurrentUser, current_user
from app.config import get_settings
from app.main import app
from app.ratelimit import get_usage
from app.routes import analyses
from app.routes.analyses import get_repository, get_storage
from tests.fakes import FakeRepository, FakeStorage, FakeUsage
from tests.rasters import KIT_IMAGE, KIT_ORIGIN, KIT_SCL, make_tiff

OWNER = CurrentUser(id=UUID("11111111-1111-1111-1111-111111111111"), email="dono@test")
PIXELS = np.full((4, 8, 8), 1000)


@pytest.fixture
def api(monkeypatch):
    # A validação é da rota; o pipeline não precisa rodar.
    monkeypatch.setattr(analyses, "run_analysis", lambda *args, **kwargs: None)
    repository, usage = FakeRepository(), FakeUsage()
    app.dependency_overrides[current_user] = lambda: OWNER
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_storage] = FakeStorage
    app.dependency_overrides[get_usage] = lambda: usage
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, repository=repository, usage=usage)
    app.dependency_overrides.clear()


def post(api, image: bytes, name: str = "imagem.tif", **others):
    files = {"image": (name, image, "image/tiff")}
    for field, (other_name, data) in others.items():
        files[field] = (other_name, data, "image/tiff")
    return api.client.post("/analyses", files=files)


def assert_rejected(api, response, status: int, detail: str):
    assert response.status_code == status
    assert response.json()["detail"] == detail
    assert api.repository.rows == {}
    assert api.usage.counts == {}


def test_kit_is_accepted(api):
    response = post(api, KIT_IMAGE.read_bytes(), scl=("qualidade_scl.tif", KIT_SCL.read_bytes()))

    assert response.status_code == 202


def test_bigtiff_is_accepted(api):
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": 4,
        "height": 8,
        "width": 8,
        "crs": "EPSG:32723",
        "transform": from_origin(*KIT_ORIGIN, 10, 10),
        "BIGTIFF": "YES",
    }
    with MemoryFile() as memfile:
        with memfile.open(**profile) as dst:
            dst.write(PIXELS.astype("uint16"))
        data = memfile.read()
    assert data.startswith(b"II+\x00")

    assert post(api, data).status_code == 202


def test_over_the_size_limit_is_413(api, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")  # o kit tem ~1,4 MB
    get_settings.cache_clear()

    response = post(api, KIT_IMAGE.read_bytes())

    assert_rejected(api, response, 413, "O arquivo passa do limite de 1 MB.")


@pytest.mark.parametrize(
    ("name", "data"),
    [
        # PNG renomeado para .tif: a extensão engana, a assinatura não.
        ("foto.tif", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64),
        # TIFF de verdade com extensão errada.
        ("imagem.png", make_tiff(PIXELS)),
        ("imagem", make_tiff(PIXELS)),
    ],
)
def test_not_a_tiff_is_415(api, name, data):
    response = post(api, data, name=name)

    assert_rejected(api, response, 415, "Imagem: o arquivo precisa ser um GeoTIFF (.tif).")


def test_tiff_extension_is_case_insensitive(api):
    assert post(api, make_tiff(PIXELS), name="IMAGEM.TIFF").status_code == 202


@pytest.mark.parametrize(
    ("data", "detail"),
    [
        (
            b"II*\x00" + b"\x00" * 64,
            "Imagem: não foi possível abrir o arquivo como GeoTIFF.",
        ),
        (
            make_tiff(PIXELS, crs=None),
            "Imagem: o arquivo não tem sistema de coordenadas (CRS).",
        ),
        (
            make_tiff(PIXELS[:3], descriptions=None, scales=None, offsets=None),
            "Imagem: o arquivo tem 3 banda(s); são necessárias 4 (azul, verde, vermelho e "
            "infravermelho próximo).",
        ),
        (
            make_tiff(PIXELS, dtype="float32"),
            "Imagem: as bandas estão em float32; o esperado é uint16, os números digitais "
            "do Sentinel-2 L2A.",
        ),
        (
            # 4096 px num lado só: o cabeçalho basta, e o arquivo fica pequeno.
            make_tiff(np.full((4, 1, 4096), 1000)),
            "Imagem: o arquivo tem 4096 x 1 px; o limite é 2048 x 2048.",
        ),
    ],
)
def test_unusable_raster_is_422_with_the_reason(api, data, detail):
    assert_rejected(api, post(api, data), 422, detail)


def test_problem_in_the_second_image_names_the_field(api):
    response = post(
        api,
        KIT_IMAGE.read_bytes(),
        image_2=("segunda.tif", KIT_SCL.read_bytes()),
    )

    assert_rejected(
        api,
        response,
        422,
        "Segunda imagem: o arquivo tem 1 banda(s); são necessárias 4 (azul, verde, vermelho e "
        "infravermelho próximo).",
    )


def test_scl_that_is_not_a_tiff_is_415(api):
    response = post(api, KIT_IMAGE.read_bytes(), scl=("scl.jp2", b"\x00\x00\x00\x0cjP  "))

    assert_rejected(api, response, 415, "Camada SCL: o arquivo precisa ser um GeoTIFF (.tif).")
