"""Cascata de exclusões N0–N4 e morfologia (R2.10, R2.11, R2.14, R3.10).

Cada pixel termina com um código em `levels`: 0 é área potencial; os demais
dizem em que nível ele saiu. A contagem é exclusiva (o pixel conta só no
primeiro nível que o exclui), então as áreas somam a área total do recorte.
"""

import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from app.processing.masking import QualityMask
from app.processing.params import Params
from app.processing.reader import ImageData

POTENTIAL = 0
# Ordem da cascata.
EXCLUSION_LEVELS = (
    "no_data",
    "quality_mask",
    "low_vegetation",
    "dense_canopy",
    "low_chlorophyll",
    "high_amplitude",
    "small_patch",
)
# Códigos fixos: o nível da spec 003 (`high_amplitude`) ganhou o 7 para não
# renumerar os que já existiam.
CODES = {
    "no_data": 1,
    "quality_mask": 2,
    "low_vegetation": 3,
    "dense_canopy": 4,
    "low_chlorophyll": 5,
    "small_patch": 6,
    "high_amplitude": 7,
}

# Vizinhança 4 (cruz 3 x 3): a mesma do `rasterio.features.shapes`, para cada
# componente rotulado aqui virar um polígono na vetorização.
CROSS = ndimage.generate_binary_structure(2, 1)


@dataclass(frozen=True, eq=False)
class Classification:
    levels: np.ndarray
    pixel_area_ha: float

    @property
    def potential(self) -> np.ndarray:
        return self.levels == POTENTIAL

    @property
    def potential_area_ha(self) -> float:
        return int(np.count_nonzero(self.potential)) * self.pixel_area_ha

    @property
    def excluded_area_ha(self) -> dict[str, float]:
        counts = np.bincount(self.levels.ravel(), minlength=max(CODES.values()) + 1)
        return {name: int(counts[CODES[name]]) * self.pixel_area_ha for name in EXCLUSION_LEVELS}


def classify(
    image: ImageData,
    quality: QualityMask,
    ndvi: np.ndarray,
    params: Params,
    gndvi: np.ndarray | None = None,
    amplitude: np.ndarray | None = None,
) -> Classification:
    """`gndvi` só é usado com `params.gndvi_min` definido (nível N3b, R2.9).

    `amplitude` (|NDVI da segunda data − NDVI|) só existe com segunda imagem
    (nível N3c, R3.10); sem ela, o nível fica com 0 ha.
    """
    if params.gndvi_min is not None and gndvi is None:
        raise ValueError("gndvi_min definido sem o GNDVI calculado")
    usable = image.valid & ~quality.excluded
    # Com NaN fora de `valid`, as comparações já dão False; o `usable` deixa explícito.
    low = usable & (ndvi < params.ndvi_min)
    dense = usable & (ndvi > params.ndvi_max)
    low_chlorophyll = np.zeros_like(usable)
    if params.gndvi_min is not None:
        low_chlorophyll = usable & ~low & ~dense & (gndvi < params.gndvi_min)
    passed = usable & ~low & ~dense & ~low_chlorophyll
    high_amplitude = np.zeros_like(usable)
    if amplitude is not None:
        high_amplitude = passed & (amplitude >= params.ndvi_amplitude_max)
    within = passed & ~high_amplitude

    # O fechamento pode preencher NoData ou pixel mascarado; cortar antes de
    # medir as manchas, senão esses pixels ajudariam a mancha a passar do mínimo.
    potential = morphology(within, params.morphology_iterations) & usable
    potential = remove_small_patches(potential, min_pixels(params.min_area_ha, image))

    levels = np.full(image.shape, CODES["small_patch"], dtype=np.uint8)
    levels[potential] = POTENTIAL
    # Os níveis espectrais só existem dentro de utilizável e não se sobrepõem;
    # quem passou em todos e não ficou cai em `small_patch`.
    levels[~potential & high_amplitude] = CODES["high_amplitude"]
    levels[~potential & dense] = CODES["dense_canopy"]
    levels[~potential & low_chlorophyll] = CODES["low_chlorophyll"]
    levels[~potential & low] = CODES["low_vegetation"]
    levels[quality.excluded & image.valid] = CODES["quality_mask"]
    levels[~image.valid] = CODES["no_data"]
    return Classification(levels=levels, pixel_area_ha=image.pixel_area_ha)


def morphology(mask: np.ndarray, iterations: int) -> np.ndarray:
    """Abertura e depois fechamento, sem perder a borda do recorte.

    O scipy trata o lado de fora da imagem como False: o fechamento apagaria a
    borda de um talhão que encosta no limite. Estender a borda evita isso. A
    extensão é de 2 x `iterations`: abertura e fechamento juntos alcançam essa
    distância (com 1 x, a abertura come a faixa estendida antes do fechamento).
    """
    if iterations == 0:
        return mask.copy()
    pad = 2 * iterations
    padded = np.pad(mask, pad, mode="edge")
    padded = ndimage.binary_opening(padded, structure=CROSS, iterations=iterations)
    padded = ndimage.binary_closing(padded, structure=CROSS, iterations=iterations)
    return padded[pad:-pad, pad:-pad]


def min_pixels(min_area_ha: float, image: ImageData) -> int:
    # A tolerância evita que 0,5 / 0,01 = 50,000000001 vire 51 pixels.
    return math.ceil(min_area_ha / image.pixel_area_ha - 1e-9)


def remove_small_patches(mask: np.ndarray, min_size: int) -> np.ndarray:
    """Mantém só os componentes (vizinhança 4) com pelo menos `min_size` pixels."""
    if min_size <= 1:
        return mask.copy()
    labels, _ = ndimage.label(mask, structure=CROSS)
    sizes = np.bincount(labels.ravel())
    keep = sizes >= min_size
    keep[0] = False  # rótulo 0 é o fundo
    return keep[labels]
