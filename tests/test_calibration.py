import pytest

from palletizer.config.models import PalletizationConfig
from palletizer.setup.calibration import (
    DEFAULT_POINT_NAMES,
    ensure_default_points,
    pick_approach_pose,
)


def test_only_home_and_pick_are_taught():
    assert set(DEFAULT_POINT_NAMES) == {"home", "pick"}
    assert "pick_approach" not in DEFAULT_POINT_NAMES
    assert "pallet_approach" not in DEFAULT_POINT_NAMES


def test_ensure_default_points_creates_home_and_pick():
    cfg = PalletizationConfig(name="t")
    ensure_default_points(cfg)
    assert set(cfg.points) == {"home", "pick"}


def test_pick_approach_is_derived_from_pick_plus_vertical_offset():
    cfg = PalletizationConfig(name="t")
    ensure_default_points(cfg)
    cfg.points["pick"].pose = [0.4, -0.5, 0.2, 1.0, 2.0, 3.0]
    cfg.motion.approach_pick_offset_z = 0.15
    app = pick_approach_pose(cfg)
    assert app[0] == pytest.approx(0.4)
    assert app[1] == pytest.approx(-0.5)
    assert app[2] == pytest.approx(0.35)          # z do pick + 0.15
    assert app[3:] == pytest.approx([1.0, 2.0, 3.0])  # mesma orientação do pick
