"""Cria uma configuração de paletização para o URSim, com pontos MANUAIS.

Editar os valores marcados com TODO com poses ALCANÇÁVEIS no seu URSim (em metros/radianos,
formato de get_actual_tcp_pose). Depois:

    python examples/build_ursim_config.py        # salva configs/ursim.json + gera o .script

Para enviar ao URSim, use a GUI ou o controller com o IP 192.168.2.102 (ver README).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from palletizer.app.controller import PalletizerController
from palletizer.config.models import PalletizationConfig, PatternType
from palletizer.config.store import ConfigStore
from palletizer.setup.calibration import ensure_default_points
from palletizer.setup.teach import set_point


def main() -> int:
    cfg = PalletizationConfig(name="ursim")
    cfg.robot.ip = "192.168.2.102"   # IP do URSim
    cfg.robot.port = 30003

    # Geometria da paletização
    cfg.pattern = PatternType.BRICK
    cfg.pallet.nx = 3
    cfg.pallet.ny = 3
    cfg.pallet.layers = 2
    cfg.box.length = 100.0
    cfg.box.width = 100.0
    cfg.box.height = 100.0

    # Calibração (ajuste conforme necessário)
    cfg.motion.v_nominal = 0.25
    cfg.motion.approach_height = 0.15

    ensure_default_points(cfg)  # cria as entradas dos pontos (zeradas)

    # --- PONTOS MANUAIS (TODO: troque por poses alcançáveis no seu URSim) ---
    # pose = [x, y, z, rx, ry, rz] em metros e radianos.
    set_point(cfg, "home",            [0.300,  0.000, 0.500, 0.0, 3.14, 0.0])
    set_point(cfg, "pick",            [0.438, -0.500, 0.200, 0.0, 3.14, 0.0])
    set_point(cfg, "pick_approach",   [0.438, -0.500, 0.400, 0.0, 3.14, 0.0])
    set_point(cfg, "pallet_corner",   [0.600,  0.200, 0.100, 0.0, 3.14, 0.0])
    set_point(cfg, "pallet_approach", [0.600,  0.200, 0.400, 0.0, 3.14, 0.0])

    store = ConfigStore(str(ROOT / "configs"))
    path = store.save(cfg)
    print(f"Config salva em: {path}")

    script_path = PalletizerController(cfg).save_urscript(ROOT / "scripts" / "palletizer_core.script")
    print(f"URScript gerado: {script_path}")
    print("Edite os pontos (TODO) com valores reais do seu URSim e rode de novo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
