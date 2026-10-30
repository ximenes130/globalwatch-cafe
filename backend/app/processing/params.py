"""Parâmetros versionados do método (R2.17).

Os limiares aqui são valores de partida; os finais saem da calibração (T2.5)
e precisam ser espelhados em `frontend/src/lib/method.ts`.
"""

from pydantic import BaseModel, ConfigDict, Field

METHOD_VERSION = "spectral-rules-1.0"

# Radiometria do kit (LEIA-ME e metadados.json), usada quando o arquivo não
# traz scale/offset: reflectância = DN * KIT_SCALE + KIT_OFFSET.
KIT_SCALE = 0.0001
KIT_OFFSET = -0.1

# Classes da SCL excluídas: sem dado, saturado, sombra de nuvem, água, nuvem
# (média e alta probabilidade), cirrus e neve (R2.6).
SCL_EXCLUDE = (0, 1, 3, 6, 8, 9, 10, 11)


class Params(BaseModel):
    """Escolhas do método; salvas com cada análise junto de `method_version`."""

    model_config = ConfigDict(frozen=True)

    scl_exclude: tuple[int, ...] = SCL_EXCLUDE
    ndwi_water_min: float = 0.0
    ndvi_min: float = 0.55
    ndvi_max: float = 0.72
    gndvi_min: float | None = None
    morphology_iterations: int = Field(default=1, ge=0)
    min_area_ha: float = Field(default=0.5, ge=0)
    simplify_tolerance_px: float = Field(default=0.5, ge=0)
