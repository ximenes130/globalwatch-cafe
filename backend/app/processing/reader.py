"""Leitura do GeoTIFF enviado: bandas, reflectância, NoData e data (R2.2–R2.5).

A conversão DN → reflectância acontece **só aqui**, uma única vez. O resto do
pipeline recebe reflectância e nunca reaplica scale/offset (aviso do LEIA-ME).
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from rasterio.transform import Affine

from app.processing.errors import ProcessingError
from app.processing.params import KIT_OFFSET, KIT_SCALE

log = logging.getLogger(__name__)

ROLES = ("blue", "green", "red", "nir")

# Tokens que identificam cada banda na descrição (ex.: "B02_blue"). "B8A" não
# está na lista: é a borda do NIR em 20 m, não a B08.
ROLE_TOKENS = {
    "blue": {"b02", "b2", "blue"},
    "green": {"b03", "b3", "green"},
    "red": {"b04", "b4", "red"},
    "nir": {"b08", "b8", "nir"},
}

ACQUISITION_TAG = "ACQUISITION_UTC"
ATTRIBUTION_TAG = "ATTRIBUTION"

# Web Mercator é métrico, mas a área cresce com a latitude (cerca de +15% a 21°S).
WEB_MERCATOR = {3857, 900913}


@dataclass(frozen=True)
class Radiometry:
    """Scale/offset efetivamente aplicados, na ordem azul, verde, vermelho, NIR."""

    scale: tuple[float, ...]
    offset: tuple[float, ...]
    source: Literal["file_tags", "kit_default"]


@dataclass(frozen=True)
class BandOrder:
    """Índices (1-based, como no rasterio) das bandas azul, verde, vermelho, NIR."""

    indexes: tuple[int, ...]
    source: Literal["descriptions", "default"]


@dataclass(frozen=True, eq=False)
class ImageData:
    """Reflectância em float32, com `NaN` fora de `valid`."""

    blue: np.ndarray
    green: np.ndarray
    red: np.ndarray
    nir: np.ndarray
    valid: np.ndarray
    crs: CRS
    transform: Affine
    acquired_at: datetime | None
    radiometry: Radiometry
    bands: BandOrder
    # Texto de atribuição gravado no arquivo (o kit traz o da Copernicus).
    attribution: str | None = None

    @property
    def shape(self) -> tuple[int, int]:
        return self.valid.shape

    @property
    def pixel_area_ha(self) -> float:
        """Área de um pixel; o CRS é projetado em metros (conferido na leitura)."""
        return abs(self.transform.determinant) / 10_000


def read_image(data: bytes) -> ImageData:
    """Lê o GeoTIFF em memória e devolve as quatro bandas em reflectância."""
    with MemoryFile(data) as memfile, memfile.open() as ds:
        if ds.count < 4:
            raise ProcessingError(
                f"A imagem tem {ds.count} banda(s); são necessárias 4 (azul, verde, "
                "vermelho e infravermelho próximo)."
            )
        bands = _band_order(ds.descriptions)
        radiometry = _radiometry(ds, bands.indexes)
        dn = ds.read(indexes=list(bands.indexes))
        nodata = ds.nodata
        crs, transform = ds.crs, ds.transform
        _check_crs(crs)
        tags = ds.tags()
        acquired_at = _acquired_at(tags.get(ACQUISITION_TAG))
        attribution = tags.get(ATTRIBUTION_TAG) or None

    # Pixel inválido se qualquer banda for NoData: sem as quatro, não há índice.
    invalid = np.any(dn == 0, axis=0)
    if nodata is not None and nodata != 0:
        invalid |= np.any(dn == nodata, axis=0)
    valid = ~invalid

    reflectance = []
    for i in range(4):
        band = dn[i].astype(np.float32) * np.float32(radiometry.scale[i]) + np.float32(
            radiometry.offset[i]
        )
        band[invalid] = np.nan
        reflectance.append(band)

    return ImageData(
        *reflectance,
        valid=valid,
        crs=crs,
        transform=transform,
        acquired_at=acquired_at,
        radiometry=radiometry,
        bands=bands,
        attribution=attribution,
    )


def _check_crs(crs: CRS | None) -> None:
    """A área (R2.12) é medida no CRS da imagem, que precisa ser projetado em metros."""
    if crs is None:
        raise ProcessingError("A imagem não tem sistema de coordenadas.")
    if not crs.is_projected or crs.linear_units != "metre" or crs.to_epsg() in WEB_MERCATOR:
        raise ProcessingError(
            "A imagem precisa estar num sistema de coordenadas projetado em metros que "
            "preserve a área, como UTM (o Sentinel-2 já vem assim)."
        )


def _band_order(descriptions: tuple[str | None, ...]) -> BandOrder:
    """Usa as descrições quando identificam as quatro bandas sem ambiguidade."""
    matches = []
    for description in descriptions:
        tokens = set(re.split(r"[^a-z0-9]+", (description or "").lower()))
        matches.append({role for role, known in ROLE_TOKENS.items() if tokens & known})

    indexes = []
    for role in ROLES:
        # Banda que casa com mais de um papel (ex.: "red_nir") não serve.
        candidates = [i + 1 for i, found in enumerate(matches) if found == {role}]
        if len(candidates) != 1:
            return BandOrder(indexes=(1, 2, 3, 4), source="default")
        indexes.append(candidates[0])
    return BandOrder(indexes=tuple(indexes), source="descriptions")


def _radiometry(ds: rasterio.DatasetReader, indexes: tuple[int, ...]) -> Radiometry:
    """Scale/offset do arquivo; sem eles em alguma banda, os valores do kit nas quatro."""
    scales = ds.scales or (1.0,) * ds.count
    offsets = ds.offsets or (0.0,) * ds.count
    scale = tuple(float(scales[i - 1]) for i in indexes)
    offset = tuple(float(offsets[i - 1]) for i in indexes)
    # O rasterio devolve 1.0/0.0 quando a banda não tem a tag: lido como ausente.
    if any(s == 1.0 and o == 0.0 for s, o in zip(scale, offset, strict=True)):
        return Radiometry(scale=(KIT_SCALE,) * 4, offset=(KIT_OFFSET,) * 4, source="kit_default")
    return Radiometry(scale=scale, offset=offset, source="file_tags")


def _acquired_at(value: str | None) -> datetime | None:
    """Data da tag `ACQUISITION_UTC`; ausente ou ilegível vira `None` (R2.5)."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        log.warning("Tag %s ilegível: %r", ACQUISITION_TAG, value)
        return None
    # A tag é UTC por definição; sem fuso explícito, assume UTC.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
