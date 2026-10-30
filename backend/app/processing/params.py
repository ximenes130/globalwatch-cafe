"""Parâmetros versionados do método (R2.17).

Os limiares aqui são valores de partida; os finais saem da calibração (T2.5)
e precisam ser espelhados em `frontend/src/lib/method.ts`.
"""

from pydantic import BaseModel, ConfigDict, Field

# 1.1: nível N3c, amplitude de NDVI entre duas datas (spec 003).
METHOD_VERSION = "spectral-rules-1.1"

# Radiometria do kit (LEIA-ME e metadados.json), usada quando o arquivo não
# traz scale/offset: reflectância = DN * KIT_SCALE + KIT_OFFSET.
KIT_SCALE = 0.0001
KIT_OFFSET = -0.1

# Classes da SCL excluídas: sem dado, saturado, sombra de nuvem, água, nuvem
# (média e alta probabilidade), cirrus e neve (R2.6).
SCL_EXCLUDE = (0, 1, 3, 6, 8, 9, 10, 11)


# Lista fixa de referências que a justificativa pode citar (R2.18). Só entra o
# que foi aberto e conferido (C5.2; tabela "Referências" do design da spec 002).
METHOD_REFERENCES = {
    "parreiras2025": {
        "citation": (
            "Parreiras, T. C. et al. Dense time series of harmonized Landsat Sentinel-2 and "
            "ensemble machine learning to map coffee production stages. Remote Sensing, "
            "17(18), 3168, 2025."
        ),
        "doi": "10.3390/rs17183168",
        "used_for": (
            "estrutura hierárquica da regra; separação de perenes e pasto; confusão "
            "espectral entre café e eucalipto; importância do GNDVI"
        ),
    },
    "maskell2021": {
        "citation": (
            "Maskell, G. M. et al. Integration of Sentinel optical and radar data for mapping "
            "smallholder coffee production systems in Vietnam. Remote Sensing of Environment, "
            "266, 112709, 2021."
        ),
        "doi": "10.1016/j.rse.2021.112709",
        "used_for": "uso da estação seca; dificuldade com café jovem e consorciado",
    },
    "souza2019": {
        "citation": (
            "Souza, C. G. et al. Variáveis multitemporais para o mapeamento de áreas de "
            "cultivo de café. Pesquisa Agropecuária Brasileira, 54, 2019."
        ),
        "doi": "10.1590/S1678-3921.pab2019.v54.00017",
        "used_for": "variação sazonal estreita do NDVI do café (limitação de uma única data e "
        "limiar de amplitude entre duas datas)",
    },
    "gitelson1996": {
        "citation": (
            "Gitelson, A. A.; Kaufman, Y. J.; Merzlyak, M. N. Use of a green channel in remote "
            "sensing of global vegetation from EOS-MODIS. Remote Sensing of Environment, "
            "58(3), 289–298, 1996."
        ),
        "doi": "10.1016/S0034-4257(96)00072-7",
        "used_for": "GNDVI e sensibilidade da banda verde à clorofila",
    },
    "mcfeeters1996": {
        "citation": (
            "McFeeters, S. K. The use of the Normalized Difference Water Index (NDWI) in the "
            "delineation of open water features. International Journal of Remote Sensing, "
            "17(7), 1425–1432, 1996."
        ),
        "doi": "10.1080/01431169608948714",
        "used_for": "NDWI para mascarar água quando não há SCL",
    },
}


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
    # Só vale com segunda imagem (R3.10). 0,25 é a oscilação de pico a pico do
    # componente sazonal do NDVI do pasto em Souza et al. (2019); a do café é
    # 0,11. Sai o que oscila pelo menos tanto quanto o pasto.
    ndvi_amplitude_max: float = Field(default=0.25, gt=0)
