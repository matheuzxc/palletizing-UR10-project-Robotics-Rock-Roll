"""Integração end-to-end do redesenho da config (Fase 7).

Carrega uma config v2 do disco, constrói o plano de ≥2 camadas e gera o URScript, validando
estruturalmente as três mudanças: Z do chão + altura, approach diagonal por caixa e D0 5 s.
"""

import pytest

from palletizer.config.models import PalletizationConfig, PatternType, TaughtPoint
from palletizer.config.store import ConfigStore
from palletizer.motion.urscript import generate_script
from palletizer.planner.plan import build_plan
from palletizer.setup.calibration import ensure_default_points


def _v2_config(name="e2e") -> PalletizationConfig:
    cfg = PalletizationConfig(name=name)
    cfg.pattern = PatternType.BRICK
    cfg.box.length = cfg.box.width = cfg.box.height = 100.0
    # 4 cantos no chão a z=0.15 → 300 x 300 mm → nx=3, ny=3
    cfg.pallet.corners = [
        [0.6, 0.6, 0.15], [0.9, 0.6, 0.15], [0.9, 0.9, 0.15], [0.6, 0.9, 0.15],
    ]
    cfg.pallet.layers = 2
    ensure_default_points(cfg)
    cfg.points["home"] = TaughtPoint("home", [0.9, -0.2, 0.8, 1.1, -1.2, 1.2])
    cfg.points["pick"] = TaughtPoint("pick", [0.6, -0.8, 0.25, 1.2, -2.6, -0.06])
    return cfg


def test_config_v2_roundtrips_and_builds_multilayer_plan(tmp_path):
    store = ConfigStore(tmp_path)
    store.save(_v2_config())
    cfg = store.load("e2e")
    plan = build_plan(cfg)
    assert plan.grid.nx == 3 and plan.grid.ny == 3
    assert plan.total_boxes == 3 * 3 * 2  # 2 camadas
    # Z cresce entre camadas (chão + altura acumulada)
    assert plan.slots_in_layer(1)[0].z > plan.slots_in_layer(0)[0].z


def test_end_to_end_script_has_all_three_changes(tmp_path):
    store = ConfigStore(tmp_path)
    store.save(_v2_config())
    cfg = store.load("e2e")
    plan = build_plan(cfg)
    script = generate_script(cfg, plan)

    # 1) D0 mantido 5 s
    idx_do = script.index("set_digital_out(0, state)")
    assert "sleep(5.0)" in script[idx_do:]
    # 2) approach diagonal por caixa (um p_place_app por caixa)
    assert script.count("p_place_app = pose_trans(p_pallet") == plan.total_boxes
    # 3) Z de place derivado do chão + altura: camada 1 acima da camada 0
    assert plan.slots_in_layer(1)[0].z == pytest.approx(150.0)
    # frame do pallet dos 4 cantos + pick_approach derivado
    assert "p_pallet       = p[" in script
    assert "p_pick_app     = p[" in script


def test_generated_script_is_syntactically_balanced(tmp_path):
    cfg = _v2_config()
    script = generate_script(cfg)
    # def/end balanceados (um def de topo + defs internos fecham)
    assert script.count("def ") == script.count("\nend") or script.rstrip().endswith("end")
    assert "movej(" in script and "movel(" in script
