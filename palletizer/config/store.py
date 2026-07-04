"""Persistência local de configurações de paletização (uma por arquivo JSON).

Permite ao operador salvar vários ambientes e escolher qual carregar — objetivo central do
software. O nome do arquivo deriva do nome da config (saneado).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from .models import PalletizationConfig


def _safe_filename(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    return (slug or "config") + ".json"


class ConfigStore:
    """CRUD de configs num diretório (default ``configs/``)."""

    def __init__(self, directory: str | Path = "configs") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.directory / _safe_filename(name)

    def save(self, config: PalletizationConfig) -> Path:
        path = self._path(config.name)
        with path.open("w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
        return path

    def load(self, name: str) -> PalletizationConfig:
        path = self._path(name)
        if not path.is_file():
            raise FileNotFoundError(f"Config '{name}' não encontrada em {path}")
        with path.open("r", encoding="utf-8") as f:
            return PalletizationConfig.from_dict(json.load(f))

    def list_names(self) -> List[str]:
        names = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as f:
                    names.append(json.load(f).get("name", path.stem))
            except (json.JSONDecodeError, OSError):
                continue
        return names

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if path.is_file():
            path.unlink()
            return True
        return False
