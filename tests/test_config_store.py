import pytest

from palletizer.config.models import (
    PalletizationConfig,
    PatternType,
    TaughtPoint,
    SCHEMA_VERSION,
)
from palletizer.config.store import ConfigStore


def _sample() -> PalletizationConfig:
    cfg = PalletizationConfig(name="Linha A")
    cfg.pattern = PatternType.BRICK
    cfg.pallet.nx = 4
    cfg.points["pick"] = TaughtPoint(name="pick", pose=[0.4, -0.9, 0.6, 0.8, -2.9, 0.1])
    return cfg


def test_roundtrip_preserves_data(tmp_path):
    store = ConfigStore(tmp_path)
    store.save(_sample())
    loaded = store.load("Linha A")
    assert loaded.name == "Linha A"
    assert loaded.pattern is PatternType.BRICK
    assert loaded.pallet.nx == 4
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
