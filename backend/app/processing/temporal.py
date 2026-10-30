"""Segunda data e amplitude de NDVI entre as datas (spec 003, R3.10, R3.11).

A imagem principal é a classificada; a segunda só serve para medir quanto o
NDVI muda entre as datas. Café é perene e muda pouco entre seca e chuva; pasto,
cana e lavoura anual mudam mais (Souza et al., 2019).
"""

from dataclasses import dataclass

import numpy as np

from app.processing.errors import ProcessingError
from app.processing.indices import ndvi
from app.processing.masking import QualityMask, quality_mask
from app.processing.params import Params
from app.processing.reader import ImageData, read_image

GRID_MISMATCH = (
    "A segunda imagem precisa ter a mesma grade da primeira (mesmo recorte, CRS e resolução)."
)


@dataclass(frozen=True, eq=False)
class SecondDate:
    image: ImageData
    quality: QualityMask
    ndvi: np.ndarray


def read_second_date(
    image_bytes: bytes, scl_bytes: bytes | None, params: Params, primary: ImageData
) -> SecondDate:
    try:
        image = read_image(image_bytes)
        same_grid = (
            image.crs == primary.crs
            and image.transform == primary.transform
            and image.shape == primary.shape
        )
        # Sem reamostrar: comparar pixel a pixel só vale na mesma grade (R3.11).
        if not same_grid:
            raise ProcessingError(GRID_MISMATCH)
        quality = quality_mask(image, params, scl_bytes)
    except ProcessingError as exc:
        # A mensagem do leitor não diz de qual arquivo se trata.
        message = str(exc)
        raise ProcessingError(
            message if message == GRID_MISMATCH else f"Segunda imagem: {message}"
        ) from exc
    return SecondDate(image=image, quality=quality, ndvi=ndvi(image.red, image.nir, image.valid))


def combined_quality(primary: ImageData, quality: QualityMask, second: SecondDate) -> QualityMask:
    """N1 das duas datas: sai o pixel sem leitura confiável em qualquer uma.

    Assim nenhum pixel passa pela regra de amplitude sem ter sido medido nas
    duas. NoData da principal continua em N0, por isso o `& primary.valid`.
    """
    unreliable_second = ~second.image.valid | second.quality.excluded
    excluded = (quality.excluded | unreliable_second) & primary.valid
    return QualityMask(
        excluded=excluded, source=quality.source, classes_excluded=quality.classes_excluded
    )


def ndvi_amplitude(ndvi_primary: np.ndarray, ndvi_second: np.ndarray) -> np.ndarray:
    """|NDVI da segunda data − NDVI da principal|; a ordem das datas não importa."""
    return np.abs(ndvi_second - ndvi_primary)
