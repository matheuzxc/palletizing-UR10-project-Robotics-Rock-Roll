import pytest

from palletizer.config.models import BoxSpec, PalletizationConfig, PalletSpec, PatternType
from palletizer.motion.urscript import generate_script
from palletizer.planner.plan import build_plan
from palletizer.setup.calibration import ensure_default_points


def _config():
    cfg = PalletizationConfig(name="t")
    cfg.box = BoxSpec(100, 100, 100)
    cfg.pallet = PalletSpec(nx=2, ny=2, layers=2)
    cfg.pattern = PatternType.GRID
    ensure_default_points(cfg)
    return cfg


def test_params_emitted_at_top():
    script = generate_script(_config())
    head = script[: script.index("def palletize")]
    for token in ("v_nominal", "a_nominal", "v_joint", "a_joint", "blend_r"):
        assert token in head


def test_has_movej_movel_and_safety_guard():
    script = generate_script(_config())
    assert "movej(" in script
    assert "movel(" in script
    assert "is_within_safety_limits(p_place)" in script
    assert "pose_trans(p_pallet" in script


def test_one_place_per_box():
    cfg = _config()
    plan = build_plan(cfg)
    script = generate_script(cfg, plan)
    # cada caixa gera exatamente uma pose de place (p_place = pose_trans ...)
    assert script.count("p_place     = pose_trans") == plan.total_boxes


def test_missing_taught_point_raises():
    cfg = _config()
    del cfg.points["pick"]
    with pytest.raises(KeyError):
        generate_script(cfg)


def test_starts_and_ends_at_home():
    script = generate_script(_config())
    assert "movej(p_home" in script
    assert script.rstrip().endswith("palletize()")
