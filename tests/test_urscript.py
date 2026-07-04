import pytest

from palletizer.config.models import BoxSpec, PalletizationConfig, PatternType
from palletizer.motion.urscript import generate_script
from palletizer.planner.plan import build_plan
from palletizer.setup.calibration import ensure_default_points


def _config():
    cfg = PalletizationConfig(name="t")
    cfg.box = BoxSpec(100, 100, 100)
    cfg.pallet.corners = [[0.0, 0.0, 0.0], [0.2, 0.0, 0.0], [0.2, 0.2, 0.0], [0.0, 0.2, 0.0]]
    cfg.pallet.layers = 2  # 200 x 200 mm → nx=2, ny=2
    cfg.pattern = PatternType.GRID
    ensure_default_points(cfg)
    return cfg


def test_params_emitted_at_top():
    script = generate_script(_config())
    # os parâmetros aparecem antes do primeiro movimento (calibração centralizada)
    head = script[: script.index("movej(p_home")]
    for token in ("v_nominal", "a_nominal", "v_joint", "a_joint", "blend_r"):
        assert token in head


def test_wrapped_in_single_top_level_def():
    script = generate_script(_config())
    # todo o programa fica num único def de topo executado automaticamente pelo
    # controlador — sem chamada global no fim (senão o robô não se move).
    assert "def palletizer_prog():" in script
    assert script.count("def palletizer_prog(") == 1
    assert script.rstrip().endswith("end")
    assert "\npalletize()" not in script


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
    # o programa termina retornando ao home e fechando o def de topo
    assert script.rstrip().endswith("movej(p_home, a=a_joint, v=v_joint)\nend")


def test_actuator_on_d0_held_5_seconds():
    """O atuador de ventosas fica em D0 e é mantido 5 s para prender a caixa."""
    script = generate_script(_config())
    assert "set_digital_out(0, state)" in script
    assert "sleep(5.0)" in script


def test_actuator_channel_and_hold_are_configurable():
    cfg = _config()
    cfg.motion.gripper_do = 3
    cfg.motion.gripper_hold_s = 2.5
    script = generate_script(cfg)
    assert "set_digital_out(3, state)" in script
    assert "sleep(2.5)" in script


def test_pallet_frame_and_pick_approach_are_derived():
    """p_pallet vem dos 4 cantos e p_pick_app é derivado (não ensinado)."""
    script = generate_script(_config())
    assert "p_pallet       = p[" in script
    assert "p_pick_app     = p[" in script


def test_place_approach_is_dynamic_per_box():
    """Cada caixa tem seu p_place_app (approach diagonal do lado vazio), não um único ponto."""
    cfg = _config()
    plan = build_plan(cfg)
    script = generate_script(cfg, plan)
    assert script.count("p_place_app = pose_trans(p_pallet") == plan.total_boxes
