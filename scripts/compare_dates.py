"""Compara a data seca (kit) com a chuvosa (cena adicional) pelo pipeline da app (T3.3).

Gera em `docs/evidencias/comparacao-datas/`:
- `resumo.txt`: estatísticas das duas análises lado a lado (as mesmas que a app
  grava), a matriz de níveis da cascata seca × chuva em hectares, a transição
  da área potencial, a amplitude de NDVI por classe de transição e as classes
  do MapBiomas em cada uma;
- `comparacao.jpg`: RGB das duas datas, mapa de transição e histogramas de
  amplitude.

No fim, roda a análise de duas datas da app (seca classificada, chuva como
segunda imagem, regra de amplitude da T3.5) e registra o resultado.

As duas datas usam os mesmos `Params` da app (R3.7). Os arrays por pixel vêm
das mesmas funções que o `run_pipeline` chama, então os números batem com os da
análise em produção (T3.4 confere).

O MapBiomas entra como concordância com outro produto, nunca como acurácia
(C1.2): é um modelo de 30 m, de 2024, com erros próprios.

Uso (da raiz do repositório):
    backend/.venv/bin/python scripts/compare_dates.py
    backend/.venv/bin/python scripts/compare_dates.py --additional data/adicional/<item_id>
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.processing.classification import (  # noqa: E402
    CODES,
    EXCLUSION_LEVELS,
    POTENTIAL,
    Classification,
    classify,
)
from app.processing.indices import gndvi, ndvi  # noqa: E402
from app.processing.masking import quality_mask  # noqa: E402
from app.processing.params import Params  # noqa: E402
from app.processing.pipeline import run_pipeline  # noqa: E402
from app.processing.reader import ImageData, read_image  # noqa: E402
from calibrate_thresholds import (  # noqa: E402
    CHERRY,
    MAPBIOMAS_ATTRIBUTION,
    MAPBIOMAS_CLASSES,
    STRAW,
    overlay,
    read_mapbiomas,
    true_color,
)

KIT = ROOT / "data" / "exemplo"
ADDITIONAL = ROOT / "data" / "adicional" / "S2B_T23KLS_20260110T131730_L2A"
OUT = ROOT / "docs" / "evidencias" / "comparacao-datas"

SKY = (0x3E / 255, 0x7C / 255, 0xB1 / 255)  # só na chuva
TRANSITIONS = {
    "both": "candidato nas duas datas",
    "dry_only": "só na seca",
    "wet_only": "só na chuva",
    "neither": "em nenhuma",
}
TRANSITION_COLORS = {"both": CHERRY, "dry_only": STRAW, "wet_only": SKY, "neither": (0.6,) * 3}
# Nome curto de cada nível da cascata, na ordem dos códigos (0 = potencial).
LEVEL_NAMES = {POTENTIAL: "potencial", **{CODES[name]: name for name in EXCLUSION_LEVELS}}
UNUSABLE = (CODES["no_data"], CODES["quality_mask"])


@dataclass
class DateResult:
    label: str
    image: ImageData
    ndvi: np.ndarray
    classification: Classification
    stats: dict

    @property
    def usable(self) -> np.ndarray:
        return ~np.isin(self.classification.levels, UNUSABLE)


def analyse(folder: Path, label: str, params: Params) -> DateResult:
    image_bytes = (folder / "imagem_multiespectral.tif").read_bytes()
    scl_bytes = (folder / "qualidade_scl.tif").read_bytes()
    stats = run_pipeline(image_bytes, scl_bytes, params).stats
    image = read_image(image_bytes)
    quality = quality_mask(image, params, scl_bytes)
    nd = ndvi(image.red, image.nir, image.valid)
    classification = classify(
        image, quality, nd, params, gndvi=gndvi(image.green, image.nir, image.valid)
    )
    # Mesmo cálculo da app: se divergir, a comparação não estaria olhando o que a app vê.
    if round(classification.potential_area_ha, 2) != stats["potential_area_ha"]:
        raise RuntimeError(f"{label}: área potencial diverge do run_pipeline")
    return DateResult(label, image, nd, classification, stats)


def transitions(dry: DateResult, wet: DateResult) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Base comum (utilizável nas duas datas) e a classe de transição de cada pixel."""
    common = dry.usable & wet.usable
    in_dry, in_wet = dry.classification.potential, wet.classification.potential
    classes = {
        "both": common & in_dry & in_wet,
        "dry_only": common & in_dry & ~in_wet,
        "wet_only": common & ~in_dry & in_wet,
        "neither": common & ~in_dry & ~in_wet,
    }
    return common, classes


def stats_table(dry: DateResult, wet: DateResult) -> list[str]:
    rows = [
        ("área total (ha)", "total_area_ha"),
        ("área válida (ha)", "valid_area_ha"),
        ("máscara de qualidade (ha)", "masked_area_ha"),
        ("área potencial (ha)", "potential_area_ha"),
        ("polígonos", "polygon_count"),
    ]
    lines = [f"  {'':34} {dry.label:>14} {wet.label:>14}"]
    for title, key in rows:
        lines.append(f"  {title:34} {dry.stats[key]:>14} {wet.stats[key]:>14}")
    for name in EXCLUSION_LEVELS:
        a, b = dry.stats["excluded_area_ha"][name], wet.stats["excluded_area_ha"][name]
        lines.append(f"  {'excluído em ' + name + ' (ha)':34} {a:>14} {b:>14}")
    for key in ("p5", "median", "p95"):
        a, b = dry.stats["ndvi"][key], wet.stats["ndvi"][key]
        lines.append(f"  {'NDVI ' + key:34} {a:>14} {b:>14}")
    return lines


def level_matrix(dry: DateResult, wet: DateResult, pixel_ha: float) -> list[str]:
    """Hectares por nível da cascata: linha = seca, coluna = chuva."""
    codes = sorted(LEVEL_NAMES)
    width = 17
    corner = "seca \\ chuva"
    lines = [f"  {corner:16}" + "".join(f"{LEVEL_NAMES[c]:>{width}}" for c in codes)]
    for row in codes:
        in_row = dry.classification.levels == row
        cells = [
            np.count_nonzero(in_row & (wet.classification.levels == col)) * pixel_ha
            for col in codes
        ]
        lines.append(f"  {LEVEL_NAMES[row]:16}" + "".join(f"{v:>{width}.2f}" for v in cells))
    return lines


def amplitude_lines(amplitude: np.ndarray, classes: dict, pixel_ha: float) -> list[str]:
    lines = [f"  {'classe':26} {'área (ha)':>10}   amplitude p25 / mediana / p75 / p90"]
    for key, mask in classes.items():
        if not mask.any():
            lines.append(f"  {TRANSITIONS[key]:26} {0:>10.2f}   -")
            continue
        p25, p50, p75, p90 = np.percentile(amplitude[mask], [25, 50, 75, 90])
        lines.append(
            f"  {TRANSITIONS[key]:26} {mask.sum() * pixel_ha:>10.2f}"
            f"   {p25:.3f} / {p50:.3f} / {p75:.3f} / {p90:.3f}"
        )
    return lines


def mapbiomas_lines(
    classes_mb: np.ndarray, classes: dict, common: np.ndarray, amplitude: np.ndarray, pixel_ha
) -> list[str]:
    codes = [c for c in np.unique(classes_mb[common]) if c != 0]
    codes = sorted(codes, key=lambda c: -np.count_nonzero(common & (classes_mb == c)))
    head = "".join(f"{TRANSITIONS[k]:>26}" for k in classes)
    lines = [f"  {'classe MapBiomas (ha)':28}{head}   amplitude mediana"]
    for code in codes:
        in_class = classes_mb == code
        cells = "".join(
            f"{np.count_nonzero(mask & in_class) * pixel_ha:>26.2f}" for mask in classes.values()
        )
        median = np.median(amplitude[common & in_class])
        name = MAPBIOMAS_CLASSES.get(int(code), f"classe {code}")
        lines.append(f"  {name:28}{cells}   {median:.3f}")
    lines.append(f"  fonte: {MAPBIOMAS_ATTRIBUTION}")
    return lines


def figure(dry: DateResult, wet: DateResult, classes: dict, amplitude: np.ndarray) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14, 14), constrained_layout=True)
    rgb_dry, rgb_wet = true_color(dry.image), true_color(wet.image)
    axes[0, 0].imshow(rgb_dry)
    axes[0, 0].set_title(f"Seca: {dry.label}")
    axes[0, 1].imshow(rgb_wet)
    axes[0, 1].set_title(f"Chuva: {wet.label}")

    layers = [(classes[k], TRANSITION_COLORS[k], 0.75) for k in ("both", "dry_only", "wet_only")]
    grey = np.repeat(rgb_dry.mean(axis=2, keepdims=True), 3, axis=2) * 0.8
    axes[1, 0].imshow(overlay(grey, layers))
    axes[1, 0].set_title(
        "Área potencial: nas duas datas (cereja), só na seca (palha), só na chuva (azul)"
    )
    for ax in (axes[0, 0], axes[0, 1], axes[1, 0]):
        ax.set_xticks([])
        ax.set_yticks([])

    bins = np.linspace(0, 0.6, 61)
    for key, mask in classes.items():
        if mask.any():
            axes[1, 1].hist(
                amplitude[mask],
                bins=bins,
                density=True,
                histtype="step",
                lw=2,
                color=TRANSITION_COLORS[key],
                label=TRANSITIONS[key],
            )
    axes[1, 1].set_xlabel("|NDVI chuva − NDVI seca|")
    axes[1, 1].set_ylabel("densidade")
    axes[1, 1].set_title("Amplitude de NDVI entre as datas, por classe de transição")
    axes[1, 1].legend()
    fig.text(
        0.01,
        0.003,
        "Contains modified Copernicus Sentinel data (2025, 2026). Área potencial, não café "
        "confirmado.",
        fontsize=8,
        color="#555",
    )
    fig.savefig(OUT / "comparacao.jpg", dpi=80, pil_kwargs={"quality": 85})
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--additional", type=Path, default=ADDITIONAL)
    args = parser.parse_args()

    params = Params()
    dry = analyse(KIT, "16/08/2025", params)
    wet = analyse(args.additional, "10/01/2026", params)
    if dry.image.transform != wet.image.transform or dry.image.crs != wet.image.crs:
        raise SystemExit("erro: as duas imagens não estão na mesma grade")
    if wet.image.acquired_at:
        wet.label = wet.image.acquired_at.strftime("%d/%m/%Y")

    pixel_ha = dry.image.pixel_area_ha
    common, classes = transitions(dry, wet)
    total = sum(np.count_nonzero(mask) for mask in classes.values())
    if total != np.count_nonzero(common):
        raise RuntimeError("as classes de transição não somam a base comum")
    amplitude = np.abs(wet.ndvi - dry.ndvi)

    OUT.mkdir(parents=True, exist_ok=True)
    lines = [
        "Comparação entre datas (spec 003, T3.3)",
        f"Seca: kit, {dry.label}. Chuva: {args.additional.name}, {wet.label}.",
        f"Mesmos parâmetros da app: {params.model_dump(mode='json')}",
        "",
        "Estatísticas das duas análises (as que a app grava):",
        *stats_table(dry, wet),
        "",
        "Nível da cascata por pixel, seca (linha) × chuva (coluna), em hectares:",
        *level_matrix(dry, wet, pixel_ha),
        "",
        f"Base comum (utilizável nas duas datas): {np.count_nonzero(common) * pixel_ha:.2f} ha.",
        "Transição da área potencial e amplitude |NDVI chuva − NDVI seca|:",
        *amplitude_lines(amplitude, classes, pixel_ha),
        "",
        "MapBiomas 2024 em cada classe de transição (concordância, não acurácia):",
        *mapbiomas_lines(read_mapbiomas(dry.image), classes, common, amplitude, pixel_ha),
    ]
    two_dates = run_pipeline(
        (KIT / "imagem_multiespectral.tif").read_bytes(),
        (KIT / "qualidade_scl.tif").read_bytes(),
        params,
        (args.additional / "imagem_multiespectral.tif").read_bytes(),
        (args.additional / "qualidade_scl.tif").read_bytes(),
    ).stats
    lines += [
        "",
        f"Análise de duas datas da app (seca + chuva, |ΔNDVI| < {params.ndvi_amplitude_max}):",
        f"  área potencial: {two_dates['potential_area_ha']} ha em "
        f"{two_dates['polygon_count']} polígonos (só a seca: {dry.stats['potential_area_ha']} ha)",
        f"  excluído por amplitude: {two_dates['excluded_area_ha']['high_amplitude']} ha",
    ]
    figure(dry, wet, classes, amplitude)
    report = "\n".join(lines)
    (OUT / "resumo.txt").write_text(report + "\n")
    print(report)
    print(f"arquivos em {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
