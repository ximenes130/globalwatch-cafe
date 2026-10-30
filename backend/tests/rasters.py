"""GeoTIFFs sintéticos em memória para os testes de processamento."""

from pathlib import Path

import numpy as np
from rasterio.io import MemoryFile
from rasterio.transform import Affine, from_origin

KIT_DIR = Path(__file__).resolve().parents[2] / "data" / "exemplo"
KIT_IMAGE = KIT_DIR / "imagem_multiespectral.tif"
KIT_SCL = KIT_DIR / "qualidade_scl.tif"
# Cena adicional da spec 003 (estação chuvosa), na mesma grade do kit.
ADDITIONAL_DIR = KIT_DIR.parent / "adicional" / "S2B_T23KLS_20260110T131730_L2A"
ADDITIONAL_IMAGE = ADDITIONAL_DIR / "imagem_multiespectral.tif"
ADDITIONAL_SCL = ADDITIONAL_DIR / "qualidade_scl.tif"

# Canto superior esquerdo do kit (EPSG:32723).
KIT_ORIGIN = (323200, 7642980)
KIT_DESCRIPTIONS = ("B02_blue", "B03_green", "B04_red", "B08_nir")


def make_tiff(
    data: np.ndarray,
    *,
    dtype: str = "uint16",
    crs: str | None = "EPSG:32723",
    transform: Affine | None = None,
    scales: tuple[float, ...] | None = (0.0001,) * 4,
    offsets: tuple[float, ...] | None = (-0.1,) * 4,
    descriptions: tuple[str, ...] | None = KIT_DESCRIPTIONS,
    tags: dict[str, str] | None = None,
    nodata: float | None = 0,
) -> bytes:
    """GeoTIFF em memória; por padrão no formato do kit (uint16, EPSG:32723, 10 m)."""
    if data.ndim == 2:
        data = data[np.newaxis]
    count, height, width = data.shape
    profile = {
        "driver": "GTiff",
        "dtype": dtype,
        "count": count,
        "height": height,
        "width": width,
        "crs": crs,
        "transform": transform or from_origin(*KIT_ORIGIN, 10, 10),
        "nodata": nodata,
    }
    with MemoryFile() as memfile:
        with memfile.open(**profile) as dst:
            dst.write(data.astype(dtype))
            if scales is not None:
                dst.scales = scales
            if offsets is not None:
                dst.offsets = offsets
            if descriptions is not None:
                for i, description in enumerate(descriptions, start=1):
                    dst.set_band_description(i, description)
            if tags:
                dst.update_tags(**tags)
        return memfile.read()


def make_scl(
    classes: np.ndarray,
    *,
    origin=KIT_ORIGIN,
    crs: str | None = "EPSG:32723",
    nodata: float | None = 0,
) -> bytes:
    """SCL uint8 de uma banda em 20 m, como a do kit."""
    return make_tiff(
        classes,
        dtype="uint8",
        crs=crs,
        transform=from_origin(*origin, 20, 20),
        scales=None,
        offsets=None,
        descriptions=None,
        nodata=nodata,
    )


def reflectance_to_dn(reflectance: float) -> int:
    """Inverso da radiometria do kit: DN = (reflectância + 0,1) / 0,0001."""
    return round((reflectance + 0.1) / 0.0001)
