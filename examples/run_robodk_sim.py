"""Testa o adaptador RoboDK contra a estação ABERTA no RoboDK.

Pré-requisitos:
1. RoboDK aberto com a estação em foco (a mesma espelhada em ``robodk_sync/``).
2. Pacote ``robodk`` disponível no Python que roda este script
   (``pip install robodk``  OU  o Python embutido ``C:/RoboDK/Python-Embedded/python.exe``).

Uso:
    python examples/run_robodk_sim.py            # robô B, grid 3x3, 2 camadas
    python examples/run_robodk_sim.py --robot A --pattern brick --nx 3 --ny 3 --layers 2

Ele NÃO precisa de robô real nem de pontos ensinados por freedrive: usa o ``frame_pallet``
da estação e move via API (MoveJ/MoveL), como o ``RobotB_StoreParts.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# garante que o pacote 'palletizer' seja importável ao rodar de qualquer lugar
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from palletizer.config.models import PalletizationConfig, PatternType
from palletizer.planner.plan import build_plan
from palletizer.robodk.adapter import RoboDKAdapter
from palletizer.robodk.link import new_robolink
from palletizer.robodk.station import StationItems


def build_config(args) -> PalletizationConfig:
    cfg = PalletizationConfig(name="sim_robodk")
    cfg.pattern = PatternType(args.pattern)
    cfg.pallet.nx = args.nx
    cfg.pallet.ny = args.ny
    cfg.pallet.layers = args.layers
    cfg.box.length = args.box
    cfg.box.width = args.box
    cfg.box.height = args.box
    return cfg


def verify_station(rdk, items: StationItems) -> bool:
    """Confere que os itens esperados existem na estação; imprime o que faltar."""
    ok = True
    for label, name in [
        ("robô", items.robot),
        ("garra", items.tool),
        ("frame do pallet", items.frame_pallet),
        ("target seguro", items.target_pallet_safe),
    ]:
        item = rdk.Item(name)
        if not item.Valid():
            print(f"  [FALTA] {label}: item '{name}' não encontrado na estação.")
            ok = False
        else:
            print(f"  [OK]    {label}: '{name}'")
    return ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Simula uma paletização no RoboDK")
    parser.add_argument("--robot", choices=["A", "B"], default="B")
    parser.add_argument("--pattern", default="grid",
                        choices=[p.value for p in PatternType])
    parser.add_argument("--nx", type=int, default=3)
    parser.add_argument("--ny", type=int, default=3)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--box", type=float, default=100.0, help="lado da caixa (mm)")
    args = parser.parse_args(argv)

    items = StationItems.robot_a() if args.robot == "A" else StationItems()

    print("Conectando ao RoboDK...")
    rdk = new_robolink()
    station = rdk.ActiveStation()
    if not station.Valid():
        print("ERRO: nenhuma estação aberta no RoboDK.")
        return 1
    print(f"Estação ativa: {station.Name()}")

    print("Verificando itens da estação:")
    if not verify_station(rdk, items):
        print("\nAjuste os nomes em palletizer/robodk/station.py para casar com a sua estação.")
        return 2

    cfg = build_config(args)
    plan = build_plan(cfg)
    print(f"\nPlano: formato={cfg.pattern.value} | camadas={cfg.pallet.layers} "
          f"| caixas={plan.total_boxes}")

    adapter = RoboDKAdapter(rdk, items=items)
    try:
        placed = adapter.run_plan(cfg, plan)
    except Exception as exc:
        print(f"\nERRO durante a simulação (pose inalcançável/colisão?): {exc}")
        print("Dica: reduza --nx/--ny ou ajuste o tamanho da caixa ao seu pallet.")
        return 3

    print(f"\nOK: {placed} caixas percorridas na simulação.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
