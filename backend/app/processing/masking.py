"""Máscara de qualidade, nível N1 da cascata (R2.6, R2.7).

Com a SCL enviada, exclui as classes de `params.scl_exclude`. Sem ela, exclui
água pelo NDWI. A SCL é classificação de cena, não de uso do solo: não entra
como classe de vegetação.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from rasterio.errors import RasterioError
from rasterio.io import MemoryFile
from rasterio.warp import Resampling, reproject

from app.processing.errors import ProcessingError
from app.processing.indices import ndwi
from app.processing.params import Params
from app.processing.reader import ImageData

# Classe 0 da SCL: sem dado. Também usada para pixel da imagem fora da SCL.
SCL_NO_DATA = 0


@dataclass(frozen=True, eq=False)
class QualityMask:
    """`excluded` marca só pixels de `valid` (o NoData já conta no nível N0)."""

    excluded: np.ndarray
    source: Literal["scl", "ndwi"]
    classes_excluded: tuple[int, ...] | None


def quality_mask(image: ImageData, params: Params, scl: bytes | None) -> QualityMask:
    if scl is None:
        water = ndwi(image.green, image.nir, image.valid) > params.ndwi_water_min
        return QualityMask(excluded=water & image.valid, source="ndwi", classes_excluded=None)

    classes = resample_scl(scl, image)
    excluded = np.isin(classes, params.scl_exclude) & image.valid
    return QualityMask(excluded=excluded, source="scl", classes_excluded=tuple(params.scl_exclude))


def resample_scl(scl: bytes, image: ImageData) -> np.ndarray:
    """Leva a SCL para a grade da imagem por vizinho mais próximo.

    A SCL é categórica: interpolar (bilinear) criaria classes que não existem.
    """
    try:
        with MemoryFile(scl) as memfile, memfile.open() as ds:
            if ds.crs is None:
                raise ProcessingError("A SCL enviada não tem sistema de coordenadas.")
            source = ds.read(1)
            src_transform, src_crs, src_nodata = ds.transform, ds.crs, ds.nodata
    except RasterioError as exc:
        raise ProcessingError("Não foi possível ler a SCL enviada.") from exc

    # O que a SCL não cobrir fica 0 ("sem dado") e é excluído. O reproject já
    # preenche o destino com `dst_nodata` (`init_dest_nodata`); o `full` deixa
    # isso explícito e independe do padrão do rasterio.
    classes = np.full(image.shape, SCL_NO_DATA, dtype=np.uint8)
    reproject(
        source,
        classes,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=src_nodata,
        dst_transform=image.transform,
        dst_crs=image.crs,
        dst_nodata=SCL_NO_DATA,
        init_dest_nodata=True,
        resampling=Resampling.nearest,
    )
    if not np.any(classes != SCL_NO_DATA):
        raise ProcessingError("A SCL enviada não cobre a imagem.")
    return classes
