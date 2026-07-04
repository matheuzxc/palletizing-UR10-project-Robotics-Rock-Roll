from palletizer.config.models import BoxSpec, PalletizationConfig, PatternType
from palletizer.planner.plan import (
    approach_height_mm,
    build_plan,
    pallet_approach_pose_mm,
)


def _corners(nx, ny, box=100.0, z=0.0):
    L = nx * box / 1000.0
    W = ny * box / 1000.0
    return [[0.0, 0.0, z], [L, 0.0, z], [L, W, z], [0.0, W, z]]


def _config(pattern=PatternType.GRID):
    cfg = PalletizationConfig(name="t")
    cfg.box = BoxSpec(100, 100, 100)
    cfg.pallet.corners = _corners(2, 2)  # 200 x 200 mm → nx=2, ny=2
    cfg.pallet.layers = 2
    cfg.pattern = pattern
    return cfg


def test_total_boxes_and_ordering():
    plan = build_plan(_config())
    assert plan.total_boxes == 2 * 2 * 2  # nx*ny*layers
    seqs = [s.seq for s in plan.slots]
    assert seqs == sorted(seqs)  # ordenado
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
    assert a0 == 100.0 + 150.0
    assert a1 == 200.0 + 150.0


def test_pinhole_plan_has_fewer_boxes():
    cfg = _config(PatternType.PINHOLE)
    cfg.pallet.corners = _corners(2, 2)
    plan = build_plan(cfg)
    # 2x2 sem centro = 3 por camada
    assert len(plan.slots_in_layer(0)) == 3


def test_pallet_approach_is_dynamic_toward_empty_side():
    """O approach de cada caixa é deslocado para o lado vazio (+x, +y) e elevado em Z."""
    cfg = _config()
    plan = build_plan(cfg)
    s = plan.slots[0]
    ax, ay, az = pallet_approach_pose_mm(s, plan.box, plan.grid, cfg.motion)
    # offset default 100 mm no plano (lado vazio = +x, +y), Z bem acima do topo
    assert ax == s.x + 100.0
    assert ay == s.y + 100.0
    assert az > s.z


def test_pallet_approach_differs_between_opposite_slots():
    cfg = _config()
    plan = build_plan(cfg)
    layer0 = plan.slots_in_layer(0)
    first = pallet_approach_pose_mm(layer0[0], plan.box, plan.grid, cfg.motion)
    last = pallet_approach_pose_mm(layer0[-1], plan.box, plan.grid, cfg.motion)
    assert first[:2] != last[:2]  # posições opostas → approaches distintos
