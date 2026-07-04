import pytest

from palletizer.config.models import PalletizationConfig
from palletizer.motion.urscript import generate_script
from palletizer.setup.calibration import ensure_default_points
from palletizer.setup.teach import set_point


def test_set_point_manual_stores_pose():
    cfg = PalletizationConfig(name="t")
    p = set_point(cfg, "pick", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    assert cfg.points["pick"].pose == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    assert p.name == "pick"


def test_set_point_rejects_wrong_length():
    cfg = PalletizationConfig(name="t")
    with pytest.raises(ValueError):
        set_point(cfg, "pick", [0.1, 0.2, 0.3])


def test_manual_points_feed_urscript():
    cfg = PalletizationConfig(name="t")
    ensure_default_points(cfg)
    for name in ("home", "pick", "pick_approach", "pallet_corner", "pallet_approach"):
        set_point(cfg, name, [0.4, -0.5, 0.2, 0.0, 3.14, 0.0])
    script = generate_script(cfg)
    assert "p_pick" in script and "movel(" in script
