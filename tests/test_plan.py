from palletizer.config.models import BoxSpec, PalletizationConfig, PalletSpec, PatternType
from palletizer.planner.plan import approach_height_mm, build_plan


def _config(pattern=PatternType.GRID):
    cfg = PalletizationConfig(name="t")
    cfg.box = BoxSpec(100, 100, 100)
    cfg.pallet = PalletSpec(nx=2, ny=2, layers=2)
    cfg.pattern = pattern
    return cfg


def test_total_boxes_and_ordering():
    plan = build_plan(_config())
    assert plan.total_boxes == 2 * 2 * 2  # nx*ny*layers
    seqs = [s.seq for s in plan.slots]
    assert seqs == sorted(seqs)  # ordenado
    # camada 0 vem antes da camada 1
    assert all(s.layer == 0 for s in plan.slots[:4])
    assert all(s.layer == 1 for s in plan.slots[4:])


def test_z_increases_per_layer():
    plan = build_plan(_config())
    z0 = plan.slots_in_layer(0)[0].z
    z1 = plan.slots_in_layer(1)[0].z
    assert z1 > z0
    assert z0 == 50.0 and z1 == 150.0  # (layer+0.5)*altura


def test_approach_height_uses_accumulated_top():
    cfg = _config()
    plan = build_plan(cfg)
    s0 = plan.slots_in_layer(0)[0]
    s1 = plan.slots_in_layer(1)[0]
    a0 = approach_height_mm(s0, plan.box, cfg.motion.approach_height)
    a1 = approach_height_mm(s1, plan.box, cfg.motion.approach_height)
    # topo da camada + folga (0.15 m = 150 mm)
    assert a0 == 100.0 + 150.0
    assert a1 == 200.0 + 150.0


def test_pinhole_plan_has_fewer_boxes():
    plan = build_plan(_config(PatternType.PINHOLE))
    # 2x2 sem centro = 3 por camada
    assert len(plan.slots_in_layer(0)) == 3
