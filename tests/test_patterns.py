import itertools

import pytest

from palletizer.config.models import BoxSpec, PatternType
from palletizer.planner.geometry import PalletFrame, PalletGrid
from palletizer.planner.patterns import (
    footprints_overlap,
    layer_positions,
    selectable_patterns,
)

BOX = BoxSpec(100, 100, 100)  # cúbica


def _grid(nx, ny):
    frame = PalletFrame(
        origin=(0.0, 0.0, 0.0), ex=(1.0, 0.0, 0.0), ey=(0.0, 1.0, 0.0), ez=(0.0, 0.0, 1.0),
        length_mm=nx * 100.0, width_mm=ny * 100.0, floor_z=0.0,
    )
    return PalletGrid(nx=nx, ny=ny, frame=frame)


GRID = _grid(3, 3)
LAYERS = 2


def _no_overlap(positions):
    return all(
        not footprints_overlap(a, b, BOX)
        for a, b in itertools.combinations(positions, 2)
    )


@pytest.mark.parametrize("pattern", list(PatternType))
def test_layer_has_no_internal_overlap(pattern):
    for layer in range(LAYERS):
        positions = layer_positions(pattern, BOX, GRID, layer)
        assert _no_overlap(positions), f"{pattern} camada {layer} tem sobreposição"


def test_selectable_patterns_are_the_three_interlocks():
    assert set(selectable_patterns()) == {
        PatternType.BRICK, PatternType.PINHOLE, PatternType.SPLIT_BLOCK
    }


def test_all_patterns_share_the_same_signature():
    """Contrato uniforme: toda função de padrão aceita (box, grid, layer)."""
    for pattern in PatternType:
        positions = layer_positions(pattern, BOX, GRID, 0)
        assert isinstance(positions, list) and positions


def test_grid_count_is_nx_times_ny():
    positions = layer_positions(PatternType.GRID, BOX, GRID, 0)
    assert len(positions) == GRID.nx * GRID.ny


def test_pinhole_removes_center():
    positions = layer_positions(PatternType.PINHOLE, BOX, GRID, 0)
    assert len(positions) == GRID.nx * GRID.ny - 1


def test_grid_layers_are_identical():
    l0 = layer_positions(PatternType.GRID, BOX, GRID, 0)
    l1 = layer_positions(PatternType.GRID, BOX, GRID, 1)
    assert l0 == l1


@pytest.mark.parametrize("pattern", [PatternType.BRICK, PatternType.PINHOLE, PatternType.SPLIT_BLOCK])
def test_interlock_layers_differ(pattern):
    """A amarração exige que camadas consecutivas NÃO sejam idênticas."""
    l0 = layer_positions(pattern, BOX, GRID, 0)
    l1 = layer_positions(pattern, BOX, GRID, 1)
    assert l0 != l1, f"{pattern} não alterna entre camadas"


def test_overlap_detects_true_overlap():
    a = (0.0, 0.0, 0.0)
    b = (50.0, 0.0, 0.0)  # meio box de distância → sobrepõe
    assert footprints_overlap(a, b, BOX) is True


def test_touching_boxes_do_not_overlap():
    a = (0.0, 0.0, 0.0)
    b = (100.0, 0.0, 0.0)  # exatamente encostadas
    assert footprints_overlap(a, b, BOX) is False
