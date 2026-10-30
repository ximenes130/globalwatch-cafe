"""Pipeline da análise: do arquivo enviado ao resultado completo (R2.1, R2.17).

Função pura: recebe bytes e parâmetros e devolve tudo o que a análise grava,
sem tocar em banco nem storage (isso é do worker, T2.10). Erros previstos
saem como `ProcessingError` com mensagem para o usuário (R2.19).
"""

from dataclasses import dataclass
from datetime import datetime

from app.processing import render
from app.processing.classification import classify
from app.processing.indices import gndvi, ndvi
from app.processing.masking import quality_mask
from app.processing.params import METHOD_VERSION, Params
from app.processing.rationale import build_rationale
from app.processing.reader import ImageData, read_image
from app.processing.vectorization import build_stats, corners_wgs84, patch_polygons, vectorize


@dataclass(frozen=True)
class AnalysisResult:
    acquired_at: datetime | None
    crs: str
    bounds_wgs84: list[list[float]]
    stats: dict
    params: dict
    method_version: str
    rationale: dict
    geojson: dict
    # Nome do arquivo no storage → conteúdo PNG.
    images: dict[str, bytes]


def run_pipeline(image_bytes: bytes, scl_bytes: bytes | None, params: Params) -> AnalysisResult:
    image = read_image(image_bytes)
    quality = quality_mask(image, params, scl_bytes)
    ndvi_values = ndvi(image.red, image.nir, image.valid)
    gndvi_values = gndvi(image.green, image.nir, image.valid)

    classification = classify(image, quality, ndvi_values, params, gndvi=gndvi_values)
    geojson = vectorize(image, classification, ndvi_values, params, gndvi=gndvi_values)
    stats = build_stats(
        image, classification, ndvi_values, len(geojson["features"]), gndvi=gndvi_values
    )
    patches = patch_polygons(image, classification, params)

    return AnalysisResult(
        acquired_at=image.acquired_at,
        crs=image.crs.to_string(),
        bounds_wgs84=corners_wgs84(image),
        stats=stats,
        params=params_record(params, image),
        method_version=METHOD_VERSION,
        rationale=build_rationale(params, stats, quality.source, image.acquired_at),
        geojson=geojson,
        images={
            "rgb.png": render.rgb_png(image),
            "classification.png": render.classification_png(classification),
            "polygons.png": render.polygons_png(image, patches),
        },
    )


def params_record(params: Params, image: ImageData) -> dict:
    """O que é salvo em `analyses.params`: escolhas do método e o que o leitor achou."""
    return {
        "method_version": METHOD_VERSION,
        "radiometry": {
            "scale": list(image.radiometry.scale),
            "offset": list(image.radiometry.offset),
            "source": image.radiometry.source,
        },
        "bands": {"indexes": list(image.bands.indexes), "source": image.bands.source},
        **params.model_dump(mode="json"),
    }
