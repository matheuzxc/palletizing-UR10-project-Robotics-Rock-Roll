from palletizer.config.models import BoxSpec, PalletizationConfig, PatternType
from palletizer.planner.plan import build_plan
from palletizer.robodk.adapter import RoboDKAdapter


class FakeItem:
    def __init__(self, name):
        self.name = name
        self.movej = 0
        self.movel = 0
        self.detached = 0
        self.frame_set = False
        self.tool_set = False

    def setPoseFrame(self, frame):
        self.frame_set = True

    def setPoseTool(self, tool):
        self.tool_set = True

    def MoveJ(self, target):
        self.movej += 1

    def MoveL(self, target):
        self.movel += 1

    def DetachAll(self):
        self.detached += 1


class FakeRDK:
    def __init__(self):
        self.items = {}

    def Item(self, name):
        return self.items.setdefault(name, FakeItem(name))


def _config():
    cfg = PalletizationConfig(name="t")
    cfg.box = BoxSpec(100, 100, 100)
    cfg.pallet.corners = [[0.0, 0.0, 0.0], [0.2, 0.0, 0.0], [0.2, 0.2, 0.0], [0.0, 0.2, 0.0]]
    cfg.pallet.layers = 2  # 200 x 200 mm → nx=2, ny=2
    cfg.pattern = PatternType.GRID
    return cfg


def _trivial_factory(x, y, z, rot):
    return (x, y, z, rot)


def test_run_plan_places_all_boxes():
    cfg = _config()
    plan = build_plan(cfg)
    rdk = FakeRDK()
    adapter = RoboDKAdapter(rdk, pose_factory=_trivial_factory)
    placed = adapter.run_plan(cfg, plan)
    assert placed == plan.total_boxes == 8


def test_run_plan_uses_movej_movel_and_detaches():
    cfg = _config()
    plan = build_plan(cfg)
    rdk = FakeRDK()
    adapter = RoboDKAdapter(rdk, pose_factory=_trivial_factory)
    adapter.run_plan(cfg, plan)
    robot = rdk.Item("UR10 B")
    tool = rdk.Item("GripperB")
    assert robot.frame_set is True
    assert robot.movel == plan.total_boxes * 2  # descida + recuo por caixa
    assert robot.movej >= plan.total_boxes      # ao menos um MoveJ por caixa
    assert tool.detached == plan.total_boxes
