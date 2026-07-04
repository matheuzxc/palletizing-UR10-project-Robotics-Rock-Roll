import pytest

from palletizer.config.models import (
    PalletizationConfig,
    PatternType,
    TaughtPoint,
    SCHEMA_VERSION,
)
from palletizer.config.store import ConfigStore
from palletizer.planner.geometry import build_grid


def _corners(nx, ny, box=100.0, z=0.0):
    L = nx * box / 1000.0
    W = ny * box / 1000.0
    return [[0.0, 0.0, z], [L, 0.0, z], [L, W, z], [0.0, W, z]]


def _sample() -> PalletizationConfig:
    cfg = PalletizationConfig(name="Linha A")
    cfg.pattern = PatternType.BRICK
    cfg.pallet.corners = _corners(4, 3)   # 400 x 300 mm → nx=4, ny=3
    cfg.points["pick"] = TaughtPoint(name="pick", pose=[0.4, -0.9, 0.6, 0.8, -2.9, 0.1])
    return cfg


def test_roundtrip_preserves_data(tmp_path):
    store = ConfigStore(tmp_path)
    store.save(_sample())
    loaded = store.load("Linha A")
    assert loaded.name == "Linha A"
    assert loaded.pattern is PatternType.BRICK
    grid = build_grid(loaded.pallet, loaded.box)
    assert (grid.nx, grid.ny) == (4, 3)
    assert loaded.points["pick"].pose[0] == pytest.approx(0.4)


def test_to_dict_from_dict_identity():
    cfg = _sample()
    clone = PalletizationConfig.from_dict(cfg.to_dict())
    assert clone.to_dict() == cfg.to_dict()


def test_list_and_delete(tmp_path):
    store = ConfigStore(tmp_path)
    store.save(_sample())
    store.save(PalletizationConfig(name="Linha B"))
    assert set(store.list_names()) == {"Linha A", "Linha B"}
    assert store.delete("Linha B") is True
    assert store.list_names() == ["Linha A"]
    assert store.delete("inexistente") is False


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ConfigStore(tmp_path).load("nada")


def test_incompatible_schema_version_rejected():
    data = PalletizationConfig(name="x").to_dict()
    data["schema_version"] = SCHEMA_VERSION + 99
    with pytest.raises(ValueError):
        PalletizationConfig.from_dict(data)


def test_migrates_v1_config_to_v2():
    """Uma config v1 (canto único + nx/ny + length/width mm) migra sem quebrar."""
    v1 = {
        "name": "antiga",
        "schema_version": 1,
        "robot": {"ip": "10.0.0.2", "port": 30003},
        "motion": {"v_nominal": 0.3, "approach_height": 0.2},
        "box": {"length": 100.0, "width": 100.0, "height": 100.0},
        "pallet": {"nx": 3, "ny": 3, "layers": 2, "length": 800.0, "width": 600.0},
        "pattern": "brick",
        "points": {
            "home": {"name": "home", "pose": [0.1, 0.2, 0.3, 0.0, 0.0, 0.0]},
            "pick": {"name": "pick", "pose": [0.4, -0.5, 0.2, 0.0, 3.14, 0.0]},
            "pick_approach": {"name": "pick_approach", "pose": [0.4, -0.5, 0.5, 0, 3.14, 0]},
            "pallet_corner": {"name": "pallet_corner", "pose": [0.7, 0.9, 0.1, 0, 0, 0]},
        },
    }
    cfg = PalletizationConfig.from_dict(v1)
    assert cfg.schema_version == SCHEMA_VERSION
    assert cfg.pattern is PatternType.BRICK
    assert cfg.robot.ip == "10.0.0.2"
    assert cfg.motion.v_nominal == pytest.approx(0.3)
    # length/width físicos viram 4 cantos no chão (800 x 600 mm → 0.8 x 0.6 m)
    grid = build_grid(cfg.pallet, cfg.box)
    assert (grid.nx, grid.ny) == (8, 6)
    # pontos derivados são descartados; home/pick preservados
    assert set(cfg.points) == {"home", "pick"}
    assert cfg.points["pick"].pose[1] == pytest.approx(-0.5)
    # campos novos ganham default
    assert cfg.motion.gripper_hold_s == pytest.approx(5.0)
    assert cfg.motion.gripper_do == 0
