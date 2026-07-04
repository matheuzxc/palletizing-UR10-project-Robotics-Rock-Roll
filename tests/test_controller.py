import pytest

from palletizer.app.controller import CycleState, PalletizerController, CycleBusyError
from palletizer.config.models import PalletizationConfig
from palletizer.setup.calibration import ensure_default_points


class FakeConn:
    def __init__(self):
        self.sent = []

    def send(self, script):
        self.sent.append(script)


def _config():
    cfg = PalletizationConfig(name="t")
    ensure_default_points(cfg)
    return cfg


def test_save_urscript(tmp_path):
    ctrl = PalletizerController(_config())
    path = ctrl.save_urscript(tmp_path / "scripts" / "core.script")
    assert path.is_file()
    assert "palletize()" in path.read_text(encoding="utf-8")


def test_send_to_robot_serialized_and_returns_idle():
    ctrl = PalletizerController(_config())
    conn = FakeConn()
    ctrl.send_to_robot(conn)
    assert len(conn.sent) == 1
    assert ctrl.state is CycleState.IDLE


def test_cannot_start_while_running():
    ctrl = PalletizerController(_config())
    ctrl.state = CycleState.RUNNING
    with pytest.raises(CycleBusyError):
        ctrl.send_to_robot(FakeConn())


def test_invalidate_plan_rebuilds():
    ctrl = PalletizerController(_config())
    first = ctrl.plan
    ctrl.invalidate_plan()
    assert ctrl.plan is not first
