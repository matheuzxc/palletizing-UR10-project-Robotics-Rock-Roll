import itertools

import pytest

from palletizer.config.models import BoxSpec, PalletSpec, PatternType
from palletizer.planner.patterns import (
    footprints_overlap,
    layer_positions,
)

BOX = BoxSpec(100, 100, 100)  # cúbica, como o box100mm da estação
PALLET = PalletSpec(nx=3, ny=3, layers=2)


def _no_overlap(positions):
    return all(
        not footprints_overlap(a, b, BOX)
        for a, b in itertools.combinations(positions, 2)
    )


@pytest.mark.parametrize("pattern", list(PatternType))
def test_layer_has_no_internal_overlap(pattern):
    for layer in range(PALLET.layers):
        positions = layer_positions(pattern, BOX, PALLET, layer)
        assert _no_overlap(positions), f"{pattern} camada {layer} tem sobreposição"


def test_grid_count_is_nx_times_ny():
    positions = layer_positions(PatternType.GRID, BOX, PALLET, 0)
    assert len(positions) == PALLET.nx * PALLET.ny


def test_pinhole_removes_center():
    positions = layer_positions(PatternType.PINHOLE, BOX, PALLET, 0)
    assert len(positions) == PALLET.nx * PALLET.ny - 1


def test_grid_layers_are_identical():
    l0 = layer_positions(PatternType.GRID, BOX, PALLET, 0)
    l1 = layer_positions(PatternType.GRID, BOX, PALLET, 1)
    assert l0 == l1


@pytest.mark.parametrize("pattern", [PatternType.BRICK, PatternType.PINHOLE, PatternType.SPLIT_BLOCK])
def test_interlock_layers_differ(pattern):
    """A amarração exige que camadas consecutivas NÃO sejam idênticas."""
    l0 = layer_positions(pattern, BOX, PALLET, 0)
    l1 = layer_positions(pattern, BOX, PALLET, 1)
    assert l0 != l1, f"{pattern} não alterna entre camadas"


def test_overlap_detects_true_overlap():
    a = (0.0, 0.0, 0.0)
    b = (50.0, 0.0, 0.0)  # meio box de distância → sobrepõe
    assert footprints_overlap(a, b, BOX) is True


def test_touching_boxes_do_not_overlap():
    a = (0.0, 0.0, 0.0)
    b = (100.0, 0.0, 0.0)  # exatamente encostadas
    assert footprints_overlap(a, b, BOX) is False
