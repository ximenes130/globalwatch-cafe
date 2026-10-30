"""Validação do upload antes de aceitar a análise (R6.6, R6.7).

Roda na rota, antes de contar a cota e de criar a linha: arquivo errado responde na
hora (415 ou 422), em vez de virar uma análise `failed`. Só o cabeçalho do raster é
lido; os pixels ficam para o worker. O tamanho (413) é conferido antes, na leitura.
"""

from dataclasses import dataclass
from pathlib import PurePath

from fastapi import HTTPException, status
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile

# Little-endian e big-endian, TIFF clássico (42) e BigTIFF (43).
TIFF_SIGNATURES = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")
TIFF_EXTENSIONS = (".tif", ".tiff")
# R6.7: acima disso, o processamento arrisca os 512 MB do Render free.
MAX_SIDE_PX = 2048


@dataclass(frozen=True)
class Expected:
    """O que cada campo do formulário precisa ter."""

    label: str
    min_bands: int
    dtype: str | None  # `None`: o tipo não é conferido aqui


IMAGE = Expected("Imagem", min_bands=4, dtype="uint16")
SCL = Expected("Camada SCL", min_bands=1, dtype=None)
SECOND_IMAGE = Expected("Segunda imagem", min_bands=4, dtype="uint16")
SECOND_SCL = Expected("SCL da segunda imagem", min_bands=1, dtype=None)


def validate_raster(data: bytes, filename: str | None, expected: Expected) -> None:
    """415 se não for TIFF; 422 com o motivo se o raster não servir."""
    name = PurePath(filename or "").name
    if not name.lower().endswith(TIFF_EXTENSIONS) or not data.startswith(TIFF_SIGNATURES):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"{expected.label}: o arquivo precisa ser um GeoTIFF (.tif).",
        )
    try:
        with MemoryFile(data) as memfile, memfile.open() as ds:
            count, dtypes, crs = ds.count, ds.dtypes, ds.crs
            width, height = ds.width, ds.height
    except RasterioError as exc:
        raise _unprocessable(expected, "não foi possível abrir o arquivo como GeoTIFF.") from exc

    if crs is None:
        raise _unprocessable(expected, "o arquivo não tem sistema de coordenadas (CRS).")
    if count < expected.min_bands:
        raise _unprocessable(
            expected,
            f"o arquivo tem {count} banda(s); são necessárias 4 (azul, verde, vermelho e "
            "infravermelho próximo).",
        )
    if expected.dtype and any(dtype != expected.dtype for dtype in dtypes[:4]):
        raise _unprocessable(
            expected,
            f"as bandas estão em {dtypes[0]}; o esperado é {expected.dtype}, os números "
            "digitais do Sentinel-2 L2A.",
        )
    if width > MAX_SIDE_PX or height > MAX_SIDE_PX:
        raise _unprocessable(
            expected,
            f"o arquivo tem {width} x {height} px; o limite é {MAX_SIDE_PX} x {MAX_SIDE_PX}.",
        )


def _unprocessable(expected: Expected, problem: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{expected.label}: {problem}")
