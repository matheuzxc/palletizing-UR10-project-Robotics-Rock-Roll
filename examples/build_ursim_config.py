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
    cfg = PalletizationConfig(name="pallet")
    cfg.robot.ip = "192.168.2.103"   # IP do URSim
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
    set_point(cfg, "home",            [0.9721, -0.2561, 0.8624, 1.1778, -1.2569, 1.2569])
    set_point(cfg, "pick",            [0.6315, -0.7938, 0.2515, 1.2192, -2.6377, -0.0658])
    set_point(cfg, "pick_approach",   [0.6315, -0.7938, 0.5455, 1.2192, -2.6377, -0.0658])
    set_point(cfg, "pallet_corner",   [0.7930, 0.9527, 0.1681, 2.9808, -0.8398, 0.3026])
    set_point(cfg, "pallet_approach", [0.6743, 0.7578, 0.4695, 2.8434, -0.7767, 0.2233])
    store = ConfigStore(str(ROOT / "configs"))
    path = store.save(cfg)
    print(f"Config salva em: {path}")

    script_path = PalletizerController(cfg).save_urscript(ROOT / "scripts" / "palletizer_core.script")
    print(f"URScript gerado: {script_path}")
    print("Edite os pontos (TODO) com valores reais do seu URSim e rode de novo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
