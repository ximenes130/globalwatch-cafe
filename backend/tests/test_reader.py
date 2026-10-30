"""Leitura do GeoTIFF: conversão única, NoData, ordem das bandas e data (T2.1)."""

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from app.processing.errors import ProcessingError
from app.processing.reader import read_image

KIT_IMAGE = Path(__file__).resolve().parents[2] / "data" / "exemplo" / "imagem_multiespectral.tif"

# DN do pixel conhecido: B02, B03, B04, B08.
KNOWN_DN = (1500, 1800, 1100, 4100)


def make_tiff(
    dn: np.ndarray,
    *,
    scales: tuple[float, ...] | None = (0.0001,) * 4,
    offsets: tuple[float, ...] | None = (-0.1,) * 4,
    descriptions: tuple[str, ...] | None = ("B02_blue", "B03_green", "B04_red", "B08_nir"),
    tags: dict[str, str] | None = None,
    nodata: float | None = 0,
) -> bytes:
    """GeoTIFF uint16 em memória no mesmo formato do kit (EPSG:32723, 10 m)."""
    count, height, width = dn.shape
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": count,
        "height": height,
        "width": width,
        "crs": "EPSG:32723",
        "transform": from_origin(323200, 7642980, 10, 10),
        "nodata": nodata,
    }
    with MemoryFile() as memfile:
        with memfile.open(**profile) as dst:
            dst.write(dn.astype(np.uint16))
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


def known_pixel_stack(height: int = 2, width: int = 2) -> np.ndarray:
    return np.stack([np.full((height, width), v) for v in KNOWN_DN])


def ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    return (nir - red) / (nir + red)


def test_known_pixel_converted_once():
    image = read_image(make_tiff(known_pixel_stack()))

    assert image.red[0, 0] == pytest.approx(0.01, abs=1e-6)
    assert image.nir[0, 0] == pytest.approx(0.31, abs=1e-6)
    # Com conversão dupla o NDVI daria outro valor; com nenhuma, 0,5769.
    assert ndvi(image.red, image.nir)[0, 0] == pytest.approx(0.9375, abs=1e-4)
    assert image.radiometry.source == "file_tags"
    assert image.red.dtype == np.float32


def test_scale_and_offset_come_from_file():
    image = read_image(make_tiff(known_pixel_stack(), scales=(0.0002,) * 4, offsets=(0.0,) * 4))

    assert image.red[0, 0] == pytest.approx(0.22, abs=1e-6)
    assert image.radiometry.scale == (0.0002,) * 4
    assert image.radiometry.source == "file_tags"


def test_missing_scale_and_offset_fall_back_to_kit():
    image = read_image(make_tiff(known_pixel_stack(), scales=None, offsets=None))

    assert image.radiometry.source == "kit_default"
    assert image.radiometry.scale == (0.0001,) * 4
    assert image.radiometry.offset == (-0.1,) * 4
    assert ndvi(image.red, image.nir)[0, 0] == pytest.approx(0.9375, abs=1e-4)


def test_dn_zero_is_nodata_in_every_band():
    dn = known_pixel_stack()
    dn[2, 0, 1] = 0  # só o vermelho é NoData neste pixel

    image = read_image(make_tiff(dn))

    assert not image.valid[0, 1]
    assert image.valid.sum() == 3
    for band in (image.blue, image.green, image.red, image.nir):
        assert np.isnan(band[0, 1])
        assert not np.isnan(band[0, 0])


def test_file_nodata_other_than_zero_is_also_excluded():
    dn = known_pixel_stack()
    dn[:, 1, 1] = 65535

    image = read_image(make_tiff(dn, nodata=65535))

    assert not image.valid[1, 1]
    assert image.valid.sum() == 3


def test_bands_reordered_by_description():
    # Arquivo gravado como NIR, vermelho, verde, azul.
    dn = known_pixel_stack()[::-1]
    descriptions = ("nir", "Red", "B3", "B02 (blue)")

    image = read_image(make_tiff(dn, descriptions=descriptions))

    assert image.bands.source == "descriptions"
    assert image.bands.indexes == (4, 3, 2, 1)
    assert ndvi(image.red, image.nir)[0, 0] == pytest.approx(0.9375, abs=1e-4)


def test_without_descriptions_assumes_kit_order():
    image = read_image(make_tiff(known_pixel_stack(), descriptions=None))

    assert image.bands.source == "default"
    assert image.bands.indexes == (1, 2, 3, 4)


@pytest.mark.parametrize(
    "descriptions",
    [
        ("B02", "B03", "B04", "B8A"),  # B8A não é a B08
        ("B02", "B03", "B04", "B04"),  # vermelho duplicado
        ("red_nir", "B03", "B04", "B08"),  # banda com dois papéis
    ],
)
def test_ambiguous_descriptions_fall_back_to_default(descriptions):
    image = read_image(make_tiff(known_pixel_stack(), descriptions=descriptions))

    assert image.bands.source == "default"
    assert image.bands.indexes == (1, 2, 3, 4)


def test_extra_bands_are_found_by_description():
    dn = np.concatenate([np.full((1, 2, 2), 3000), known_pixel_stack()])
    descriptions = ("B01", "B02", "B03", "B04", "B08")

    image = read_image(make_tiff(dn, scales=None, offsets=None, descriptions=descriptions))

    assert image.bands.indexes == (2, 3, 4, 5)
    assert ndvi(image.red, image.nir)[0, 0] == pytest.approx(0.9375, abs=1e-4)


def test_acquisition_date_from_tag():
    tags = {"ACQUISITION_UTC": "2025-08-16T13:28:10.823000Z"}

    image = read_image(make_tiff(known_pixel_stack(), tags=tags))

    assert image.acquired_at == datetime(2025, 8, 16, 13, 28, 10, 823000, tzinfo=UTC)


@pytest.mark.parametrize("tags", [None, {"ACQUISITION_UTC": "16 de agosto"}])
def test_missing_or_unreadable_acquisition_date_is_none(tags):
    image = read_image(make_tiff(known_pixel_stack(), tags=tags))

    assert image.acquired_at is None


def test_fewer_than_four_bands_is_a_processing_error():
    dn = known_pixel_stack()[:3]

    with pytest.raises(ProcessingError, match="3 banda"):
        read_image(make_tiff(dn, scales=None, offsets=None, descriptions=None))


def test_kit_image():
    image = read_image(KIT_IMAGE.read_bytes())

    assert image.shape == (512, 512)
    assert image.crs.to_epsg() == 32723
    assert image.transform.a == 10
    assert image.acquired_at == datetime(2025, 8, 16, 13, 28, 10, 823000, tzinfo=UTC)
    assert image.radiometry.source == "file_tags"
    assert image.bands.source == "descriptions"
    assert image.bands.indexes == (1, 2, 3, 4)
    # Pixel (0, 0) do azul: DN 2012 → 2012 * 0,0001 − 0,1.
    assert image.blue[0, 0] == pytest.approx(0.1012, abs=1e-6)
