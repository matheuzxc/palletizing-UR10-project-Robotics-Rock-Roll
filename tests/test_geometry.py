import math

import pytest

from palletizer.config.models import BoxSpec, PalletSpec
from palletizer.planner.geometry import (
    _dot,
    build_frame,
    build_grid,
    derive_grid_counts,
    empty_side_direction,
    empty_side_offset_mm,
    frame_to_ur_pose,
    place_z,
    tool_down_offset_rotvec,
)

BOX = BoxSpec(100, 100, 100)


def _rect(length_m, width_m, z=0.0):
    return [[0.0, 0.0, z], [length_m, 0.0, z], [length_m, width_m, z], [0.0, width_m, z]]


def test_grid_counts_from_axis_aligned_pallet():
    frame = build_frame(_rect(0.4, 0.3))
    assert derive_grid_counts(frame, BOX) == (4, 3)
    assert frame.length_mm == pytest.approx(400.0)
    assert frame.width_mm == pytest.approx(300.0)


def test_grid_counts_from_rotated_pallet():
    """Pallet girado 30° no plano: mesma área útil, nx/ny idênticos."""
    theta = math.radians(30.0)
    c = math.cos(theta)
    s = math.sin(theta)
    L, W = 0.4, 0.3
    c0 = (0.5, 0.5, 0.0)
    c1 = (c0[0] + L * c, c0[1] + L * s, 0.0)
    c3 = (c0[0] - W * s, c0[1] + W * c, 0.0)
    c2 = (c1[0] + (c3[0] - c0[0]), c1[1] + (c3[1] - c0[1]), 0.0)
    frame = build_frame([list(c0), list(c1), list(c2), list(c3)])
    assert derive_grid_counts(frame, BOX) == (4, 3)
    # eixo X aponta na direção girada
    assert frame.ex[0] == pytest.approx(c)
    assert frame.ex[1] == pytest.approx(s)


def test_non_rectangular_corners_rejected():
    bad = [[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.5, 0.3, 0.0], [0.0, 0.3, 0.0]]
    with pytest.raises(ValueError):
        build_frame(bad)


def test_non_coplanar_corners_rejected():
    bad = [[0.0, 0.0, 0.0], [0.4, 0.0, 0.0], [0.4, 0.3, 0.2], [0.0, 0.3, 0.0]]
    with pytest.raises(ValueError):
        build_frame(bad)


def test_box_larger_than_pallet_raises():
    frame = build_frame(_rect(0.05, 0.05))
    with pytest.raises(ValueError):
        derive_grid_counts(frame, BOX)


def test_place_z_anchored_to_floor_plus_accumulated_height():
    floor = 0.15
    assert place_z(0, BOX, floor) == pytest.approx(0.15 + 0.05)  # chão + meia caixa
    assert place_z(1, BOX, floor) == pytest.approx(0.15 + 0.15)  # sobe uma caixa
    assert place_z(1, BOX, floor) > place_z(0, BOX, floor)


def test_empty_side_offset_points_to_unfilled_side():
    direction = empty_side_direction(0, 0, 3, 3)
    dx, dy, dz = empty_side_offset_mm(direction, 0.1, 0.05)
    assert dx > 0 and dy > 0  # lado vazio = índices crescentes (+x, +y)
    assert dz == pytest.approx(50.0)
    assert dx == pytest.approx(100.0)


def test_build_grid_combines_frame_and_counts():
    grid = build_grid(PalletSpec(corners=_rect(0.4, 0.3)), BOX)
    assert (grid.nx, grid.ny) == (4, 3)
    assert grid.frame.floor_z == pytest.approx(0.0)


def test_frame_to_ur_pose_is_z_up_frame_with_floor_origin():
    frame = build_frame(_rect(0.4, 0.3, z=0.12))
    pose = frame_to_ur_pose(frame)
    assert len(pose) == 6
    assert pose[:3] == pytest.approx([0.0, 0.0, 0.12])  # origem = c0 (chão)
    # frame NATURAL (Z para cima) de um pallet nível e alinhado ⇒ rotação ~0
    rmag = math.sqrt(pose[3] ** 2 + pose[4] ** 2 + pose[5] ** 2)
    assert rmag == pytest.approx(0.0, abs=1e-6)


def test_real_imperfect_corners_yield_orthonormal_z_up_frame():
    """Regressão: cantos reais (não perfeitamente perpendiculares) geram base ORTONORMAL com
    Z para cima, não uma matriz inválida."""
    corners = [
        [0.9694, -0.5625, -0.4054],
        [0.5947, -0.2273, -0.4063],
        [0.2818, -0.5961, -0.4114],
        [0.6612, -0.9238, -0.4115],
    ]
    frame = build_frame(corners)
    assert _dot(frame.ex, frame.ey) == pytest.approx(0.0, abs=1e-9)
    assert _dot(frame.ex, frame.ez) == pytest.approx(0.0, abs=1e-9)
    assert _dot(frame.ey, frame.ez) == pytest.approx(0.0, abs=1e-9)
    assert frame.ez[2] > 0.99  # normal do pallet aponta para CIMA (empilhamento sobe)


def test_tool_down_offset_rotvec_points_gripper_down():
    """rotx(pi)*rotz(0) = rotx(pi): garra para baixo, módulo ~pi."""
    rvx, rvy, rvz = tool_down_offset_rotvec(0.0)
    mag = math.sqrt(rvx ** 2 + rvy ** 2 + rvz ** 2)
    assert mag == pytest.approx(math.pi, abs=1e-9)
    # rotx(pi) puro: eixo em X
    assert abs(rvx) == pytest.approx(math.pi, abs=1e-9)
    assert rvy == pytest.approx(0.0, abs=1e-9)
    assert rvz == pytest.approx(0.0, abs=1e-9)
