"""Justificativa técnica estruturada da análise (R2.18).

Montada só com `params`, `stats`, a data da imagem e textos fixos do método.
A UI e o chat leem daqui: nenhum número ou referência é inventado por eles.
"""

from datetime import datetime

from app.processing.params import METHOD_REFERENCES, METHOD_VERSION, Params

# Estação seca no Sudeste: a calibração usou uma imagem de agosto.
DRY_SEASON_MONTHS = range(5, 10)

FIXED_LIMITATIONS = (
    "Uma única data: não distingue café de outras culturas perenes ou de lavouras com o mesmo "
    "vigor na imagem; o café varia pouco entre seca e chuva, e uma segunda data ajudaria a "
    "separá-lo de pasto e lavoura anual.",
    "Sem banda SWIR: mata e eucalipto são separados do café só pelo teto de NDVI; café "
    "adensado ou sombreado pode ser cortado junto.",
    "Café jovem, esqueletado ou recepado expõe solo e tende a ficar abaixo do piso de NDVI.",
    "Borda de mata, capoeira e lavoura irrigada com vigor parecido podem entrar como área "
    "potencial.",
    "Limiares calibrados no recorte do kit (Guaxupé/MG, agosto de 2025); em outra região ou "
    "época podem precisar de ajuste.",
    "Sem verdade de campo: o resultado não foi validado e não tem acurácia medida.",
)
# Referências citadas pelas limitações fixas (a primeira e a terceira).
LIMITATION_REFERENCES = ("souza2019", "maskell2021")


def build_rationale(
    params: Params,
    stats: dict,
    quality_source: str,
    acquired_at: datetime | None,
) -> dict:
    steps = _steps(params, stats, quality_source)
    cited = [key for step in steps for key in step["references"]] + list(LIMITATION_REFERENCES)
    keys = list(dict.fromkeys(cited))  # ordem da primeira citação, sem repetir
    return {
        "method_version": METHOD_VERSION,
        "summary": _summary(stats),
        "steps": steps,
        "masks": {
            "source": quality_source,
            "classes_excluded": list(params.scl_exclude) if quality_source == "scl" else None,
            "ndwi_water_min": params.ndwi_water_min if quality_source == "ndwi" else None,
        },
        "limitations": _limitations(quality_source, acquired_at),
        "references": [{"key": key, **METHOD_REFERENCES[key]} for key in keys],
    }


def _summary(stats: dict) -> str:
    total = br(stats["total_area_ha"])
    count = stats["polygon_count"]
    if count == 0:
        found = f"nenhuma área dos {total} ha do recorte passou nas regras de área potencial"
    else:
        noun = "polígono" if count == 1 else "polígonos"
        found = (
            f"{br(stats['potential_area_ha'])} ha de área potencial de café em {count} {noun}, "
            f"de {total} ha do recorte"
        )
    return f"Regras espectrais sobre uma única imagem: {found}. Resultado não validado em campo."


def _steps(params: Params, stats: dict, quality_source: str) -> list[dict]:
    excluded = stats["excluded_area_ha"]

    def step(level, name, rule, threshold, why, references=()):
        return {
            "level": level,
            "name": name,
            "rule": rule,
            "threshold": threshold,
            "excluded_ha": excluded[name],
            "why": why,
            "references": list(references),
        }

    if quality_source == "scl":
        classes = ", ".join(str(c) for c in params.scl_exclude)
        quality = step(
            "N1",
            "quality_mask",
            f"SCL nas classes {classes}",
            None,
            "Sem dado, saturação, sombra de nuvem, água, nuvem, cirrus e neve na SCL impedem "
            "ler a vegetação.",
        )
    else:
        quality = step(
            "N1",
            "quality_mask",
            f"NDWI > {br(params.ndwi_water_min)}",
            params.ndwi_water_min,
            "Sem a SCL, só a água é mascarada, pelo NDWI (água tem NDWI positivo).",
            ["mcfeeters1996"],
        )

    steps = [
        step(
            "N0",
            "no_data",
            "DN = 0 em alguma banda",
            0,
            "Pixel sem dado em alguma banda não tem índice.",
        ),
        quality,
        step(
            "N2",
            "low_vegetation",
            f"NDVI < {br(params.ndvi_min)}",
            params.ndvi_min,
            "Remove solo exposto, pasto seco e lavoura colhida, que têm NDVI baixo na estação "
            "seca; o café, perene, mantém folhas.",
            ["parreiras2025", "maskell2021"],
        ),
        step(
            "N3",
            "dense_canopy",
            f"NDVI > {br(params.ndvi_max)}",
            params.ndvi_max,
            "Remove dossel fechado (mata, eucalipto), que tem NDVI acima do café em produção, "
            "em que o solo aparece entre as linhas.",
            ["parreiras2025"],
        ),
    ]
    if params.gndvi_min is not None:
        steps.append(
            step(
                "N3b",
                "low_chlorophyll",
                f"GNDVI < {br(params.gndvi_min)}",
                params.gndvi_min,
                "Remove vegetação que passou no NDVI mas tem pouca clorofila; a banda verde é "
                "mais sensível à clorofila que a vermelha.",
                ["gitelson1996", "parreiras2025"],
            )
        )
    iterations = params.morphology_iterations
    steps.append(
        step(
            "N4",
            "small_patch",
            f"mancha menor que {br(params.min_area_ha)} ha após abertura e fechamento "
            f"({iterations} {'iteração' if iterations == 1 else 'iterações'})",
            params.min_area_ha,
            "Remove pixels isolados e bordas finas de pixels mistos e preenche falhas pequenas "
            "dentro do talhão.",
        )
    )
    return steps


def _limitations(quality_source: str, acquired_at: datetime | None) -> list[str]:
    limitations = list(FIXED_LIMITATIONS)
    if quality_source == "ndwi":
        limitations.append(
            "Sem a SCL, só a água foi mascarada: nuvem e sombra de nuvem podem ter entrado "
            "na análise."
        )
    if acquired_at is None:
        limitations.append(
            "Data da imagem não informada: os limiares foram calibrados para a estação seca."
        )
    elif acquired_at.month not in DRY_SEASON_MONTHS:
        limitations.append(
            f"Imagem de {acquired_at:%m/%Y}, fora da estação seca (maio a setembro): os "
            "limiares foram calibrados com uma imagem de agosto."
        )
    return limitations


def br(value: float) -> str:
    """Número com vírgula decimal e ponto de milhar (2621.44 → "2.621,44")."""
    text = f"{value:,.2f}".rstrip("0").rstrip(".") if value % 1 else f"{value:,.0f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")
