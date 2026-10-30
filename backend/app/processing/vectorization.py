"""Polígonos da área potencial, GeoJSON e estatísticas (R2.12–R2.15).

Áreas vêm da contagem de pixels no CRS projetado da imagem, antes de qualquer
reprojeção. A simplificação só afeta o desenho do contorno.
"""

from dataclasses import dataclass

import numpy as np
import shapely
from pyproj import Transformer
from rasterio.features import shapes
from scipy import ndimage
from shapely.geometry import Polygon, mapping, shape
from shapely.geometry.polygon import orient

from app.processing.classification import CROSS, Classification
from app.processing.params import Params
from app.processing.reader import ImageData

FEATURE_CLASS = "potential_coffee_area"
# 6 casas decimais em graus ≈ 10 cm (RFC 7946, §11.2).
COORDINATE_PRECISION = 1e-6
AREA_DECIMALS = 2
INDEX_DECIMALS = 4


@dataclass(frozen=True)
class PatchPolygon:
    """Uma mancha da área potencial, ainda no CRS projetado da imagem."""

    label: int
    pixels: int
    polygon: Polygon


def patch_polygons(
    image: ImageData, classification: Classification, params: Params
) -> list[PatchPolygon]:
    """Um polígono simplificado por mancha, por área decrescente (empate: rótulo)."""
    # Vizinhança 4 aqui e no `shapes`: cada rótulo vira exatamente um polígono.
    labels, count = ndimage.label(classification.potential, structure=CROSS)
    if count == 0:
        return []
    pixels = np.bincount(labels.ravel(), minlength=count + 1)
    tolerance = params.simplify_tolerance_px * abs(image.transform.a)

    patches = []
    for geometry, value in shapes(
        labels.astype(np.int32), mask=labels > 0, connectivity=4, transform=image.transform
    ):
        label = int(value)
        polygon = shapely.simplify(shape(geometry), tolerance, preserve_topology=True)
        patches.append(PatchPolygon(label=label, pixels=int(pixels[label]), polygon=polygon))
    return sorted(patches, key=lambda p: (-p.pixels, p.label))


def vectorize(
    image: ImageData,
    classification: Classification,
    ndvi: np.ndarray,
    params: Params,
    gndvi: np.ndarray | None = None,
) -> dict:
    """FeatureCollection RFC 7946 (WGS84, lon/lat) com uma feição por mancha.

    Sem `gndvi`, `gndvi_mean` sai `null` (só se o GNDVI não for calculado).
    """
    patches = patch_polygons(image, classification, params)
    if not patches:
        return {"type": "FeatureCollection", "features": []}

    labels, _ = ndimage.label(classification.potential, structure=CROSS)
    patch_labels = [p.label for p in patches]
    ndvi_means = ndimage.mean(ndvi, labels, patch_labels)
    gndvi_means = (
        ndimage.mean(gndvi, labels, patch_labels) if gndvi is not None else [None] * len(patches)
    )
    to_wgs84 = Transformer.from_crs(image.crs, "EPSG:4326", always_xy=True)

    features = []
    rows = zip(patches, ndvi_means, gndvi_means, strict=True)
    for feature_id, (patch, ndvi_mean, gndvi_mean) in enumerate(rows, start=1):
        features.append(
            {
                "type": "Feature",
                "id": feature_id,
                "geometry": mapping(to_lonlat(patch.polygon, to_wgs84)),
                "properties": {
                    "id": feature_id,
                    "area_ha": round(patch.pixels * image.pixel_area_ha, AREA_DECIMALS),
                    "ndvi_mean": _round_index(ndvi_mean),
                    "gndvi_mean": _round_index(gndvi_mean),
                    "class": FEATURE_CLASS,
                    "validated": False,
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def to_lonlat(polygon: Polygon, to_wgs84: Transformer) -> Polygon:
    """Reprojeta, arredonda a 6 casas e orienta pela regra da mão direita."""

    def reproject(xy: np.ndarray) -> np.ndarray:
        return np.column_stack(to_wgs84.transform(xy[:, 0], xy[:, 1]))

    lonlat = shapely.transform(polygon, reproject)
    # `set_precision` arredonda mantendo a geometria válida.
    lonlat = shapely.set_precision(lonlat, COORDINATE_PRECISION)
    # Anel externo anti-horário, buracos horários (RFC 7946, §3.1.6).
    return orient(lonlat, sign=1.0)


def corners_wgs84(image: ImageData) -> list[list[float]]:
    """Cantos do raster na ordem do MapLibre: SE, SD, ID, IE (lon, lat)."""
    height, width = image.shape
    corners = [(0, 0), (width, 0), (width, height), (0, height)]
    xs, ys = zip(*(image.transform @ corner for corner in corners), strict=True)
    to_wgs84 = Transformer.from_crs(image.crs, "EPSG:4326", always_xy=True)
    lons, lats = to_wgs84.transform(xs, ys)
    return [[round(lon, 6), round(lat, 6)] for lon, lat in zip(lons, lats, strict=True)]


def build_stats(
    image: ImageData,
    classification: Classification,
    ndvi: np.ndarray,
    polygon_count: int,
    gndvi: np.ndarray | None = None,
) -> dict:
    """Números da análise; a soma potencial + excluídas fecha com o total (R2.14)."""
    excluded = classification.excluded_area_ha
    total = image.valid.size * image.pixel_area_ha
    return {
        "total_area_ha": round(total, AREA_DECIMALS),
        "valid_area_ha": round(total - excluded["no_data"], AREA_DECIMALS),
        "masked_area_ha": round(excluded["quality_mask"], AREA_DECIMALS),
        "potential_area_ha": round(classification.potential_area_ha, AREA_DECIMALS),
        "polygon_count": polygon_count,
        "ndvi": index_summary(ndvi, image.valid),
        "gndvi": index_summary(gndvi, image.valid) if gndvi is not None else None,
        "excluded_area_ha": {name: round(area, AREA_DECIMALS) for name, area in excluded.items()},
    }


def index_summary(index: np.ndarray, valid: np.ndarray) -> dict | None:
    """Mín., p5, mediana, p95 e máx. dos pixels válidos; `None` se não houver nenhum."""
    values = index[valid]
    if values.size == 0:
        return None
    p5, median, p95 = np.percentile(values, [5, 50, 95])
    summary = {
        "min": values.min(),
        "p5": p5,
        "median": median,
        "p95": p95,
        "max": values.max(),
    }
    return {key: _round_index(value) for key, value in summary.items()}


def _round_index(value) -> float | None:
    return None if value is None else round(float(value), INDEX_DECIMALS)
