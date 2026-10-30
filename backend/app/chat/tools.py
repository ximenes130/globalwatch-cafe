"""Ferramentas do chat: o único caminho dos números até o modelo (R5.2, C2.1).

Cada ferramenta devolve um `ToolOutput`, e o mesmo `data` vai para o modelo como
`tool_result` e para o front como card (R5.10, R5.11): um único objeto, com o
arredondamento que o processamento já gravou, para o número citado no texto ser o
mesmo do card.

As ferramentas ficam presas à análise da rota (R5.5): `AnalysisTools` recebe a linha
já conferida contra o dono e a pasta do usuário no Storage, e nenhuma ferramenta
aceita `analysis_id`. O que o modelo escreve não troca de análise nem de usuário.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from shapely.geometry import shape

from app.storage import Storage, StorageError

# Ordem da cascata (backend/app/processing/classification.py), a mesma do painel.
EXCLUSION_LEVELS = (
    "no_data",
    "quality_mask",
    "low_vegetation",
    "dense_canopy",
    "low_chlorophyll",
    "high_amplitude",
    "small_patch",
)

# Centróide com 6 casas: ~0,1 m, bem abaixo do pixel de 10 m.
CENTROID_DECIMALS = 6


@dataclass(frozen=True)
class ToolOutput:
    kind: str
    data: dict[str, Any]


class ToolError(Exception):
    """Falha prevista (ex.: polígono inexistente): vai ao modelo com `is_error` e sem card."""


# Definições enviadas à API. `strict` garante que `id` chega como inteiro.
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_analysis_summary",
        "description": (
            "Resumo da análise aberta: data da imagem (e da segunda data, se houver), "
            "área total, válida, mascarada e potencial em hectares, número de polígonos, "
            "área excluída em cada nível da cascata e os limiares usados. Use para "
            "qualquer pergunta sobre totais, datas, regras ou por que uma área ficou de fora."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "get_polygon",
        "description": (
            "Dados de um polígono de área potencial pelo número (o mesmo do popup do mapa): "
            "área em hectares, NDVI e GNDVI médios e centróide (lon, lat). Os números vão "
            "de 1 até o número de polígonos do resumo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "description": "Número do polígono, a partir de 1."}
            },
            "required": ["id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "get_limitations",
        "description": (
            "Limitações do método e referências usadas. Use quando perguntarem sobre "
            "confiança, acurácia, erros possíveis ou se a área é mesmo café."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        "strict": True,
    },
]


class AnalysisTools:
    """Ferramentas de uma análise concluída, já conferida contra o dono pela rota."""

    def __init__(self, analysis: dict, storage: Storage, prefix: str):
        self.analysis = analysis
        self.storage = storage
        self.prefix = prefix
        self._features: list[dict] | None = None

    def run(self, name: str, arguments: dict) -> ToolOutput:
        if name == "get_analysis_summary":
            return self.summary()
        if name == "get_polygon":
            polygon_id = arguments.get("id")
            # bool é subclasse de int em Python; `true` não é um número de polígono.
            if not isinstance(polygon_id, int) or isinstance(polygon_id, bool):
                raise ToolError("Informe o número do polígono (inteiro a partir de 1).")
            return self.polygon(polygon_id)
        if name == "get_limitations":
            return self.limitations()
        raise ToolError(f"Ferramenta desconhecida: {name}.")

    def summary(self) -> ToolOutput:
        row = self.analysis
        stats = row["stats"]
        params = row["params"] or {}
        second = stats.get("second_acquired_at")
        thresholds = {
            "ndvi_min": params.get("ndvi_min"),
            "ndvi_max": params.get("ndvi_max"),
            "min_area_ha": params.get("min_area_ha"),
        }
        # A regra de amplitude só existe com segunda data (R3.10).
        if second:
            thresholds["ndvi_amplitude_max"] = params.get("ndvi_amplitude_max")
        excluded = stats["excluded_area_ha"]
        return ToolOutput(
            "summary",
            {
                "filename": row["filename"],
                "acquired_at": _iso(row["acquired_at"]),
                "second_acquired_at": second,
                "total_area_ha": stats["total_area_ha"],
                "valid_area_ha": stats["valid_area_ha"],
                "masked_area_ha": stats["masked_area_ha"],
                "potential_area_ha": stats["potential_area_ha"],
                "polygon_count": stats["polygon_count"],
                "excluded_area_ha": {
                    level: excluded[level] for level in EXCLUSION_LEVELS if level in excluded
                },
                "thresholds": thresholds,
                "method_version": row["method_version"],
            },
        )

    def polygon(self, polygon_id: int) -> ToolOutput:
        features = self._load_features()
        for feature in features:
            props = feature["properties"]
            if props["id"] == polygon_id:
                centroid = shape(feature["geometry"]).centroid
                return ToolOutput(
                    "polygon",
                    {
                        "id": props["id"],
                        "area_ha": props["area_ha"],
                        "ndvi_mean": props["ndvi_mean"],
                        "gndvi_mean": props.get("gndvi_mean"),
                        "centroid": [
                            round(centroid.x, CENTROID_DECIMALS),
                            round(centroid.y, CENTROID_DECIMALS),
                        ],
                    },
                )
        if not features:
            raise ToolError("A análise não tem polígonos de área potencial.")
        raise ToolError(
            f"Polígono {polygon_id} não existe; a análise tem {len(features)} polígonos "
            f"(de 1 a {len(features)})."
        )

    def limitations(self) -> ToolOutput:
        rationale = self.analysis["rationale"]
        return ToolOutput(
            "limitations",
            {
                "items": list(rationale["limitations"]),
                "references": [
                    {"citation": ref["citation"], "doi": ref["doi"]}
                    for ref in rationale["references"]
                ],
            },
        )

    def _load_features(self) -> list[dict]:
        # Baixado uma vez por requisição, mesmo com várias chamadas a `get_polygon`.
        if self._features is None:
            try:
                raw = self.storage.download(f"{self.prefix}/result.geojson")
            except StorageError as exc:
                raise ToolError("Não foi possível ler os polígonos agora.") from exc
            self._features = json.loads(raw)["features"]
        return self._features


def _iso(value: datetime | str | None) -> str | None:
    # Do banco vem `datetime`; dos dublês e do JSON, já texto.
    return value.isoformat() if isinstance(value, datetime) else value
