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
    cfg.box.length = 100.0
    cfg.box.width = 100.0
    cfg.box.height = 100.0
    cfg.pallet.layers = 2
    # v2: pallet por 4 cantos no CHÃO (m). TODO: troque pelos 4 cantos reais do seu pallet.
    # Ordem: c0 origem, c1 fim do comprimento (X), c2 diagonal oposta, c3 fim da largura (Y).
    cfg.pallet.corners = [
        [0.60, 0.60, 0.15],
        [0.90, 0.60, 0.15],
        [0.90, 0.90, 0.15],
        [0.60, 0.90, 0.15],
    ]

    # Calibração (ajuste conforme necessário)
    cfg.motion.v_nominal = 0.25
    cfg.motion.approach_height = 0.15

    ensure_default_points(cfg)  # cria as entradas dos pontos ensinados (home, pick)

    # --- PONTOS MANUAIS (TODO: troque por poses alcançáveis no seu URSim) ---
    # v2: só home e pick são ensinados; pick_approach é derivado e o pallet vem dos 4 cantos.
    # pose = [x, y, z, rx, ry, rz] em metros e radianos (vetor de rotação).
    set_point(cfg, "home",  [0.9721, -0.2561, 0.8624, 1.1778, -1.2569, 1.2569])
    set_point(cfg, "pick",  [0.6315, -0.7938, 0.2515, 1.2192, -2.6377, -0.0658])
    store = ConfigStore(str(ROOT / "configs"))
    path = store.save(cfg)
    print(f"Config salva em: {path}")

    script_path = PalletizerController(cfg).save_urscript(ROOT / "scripts" / "palletizer_core.script")
    print(f"URScript gerado: {script_path}")
    print("Edite os pontos (TODO) com valores reais do seu URSim e rode de novo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
