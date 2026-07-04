"""Ponto de entrada do software de paletização.

Sem argumentos: abre a GUI (requer PyQt6). Comandos sem GUI (úteis para o URSim):
  --list                 lista as configs salvas
  --gen NOME             gera o URScript da config NOME (arquivo, sem enviar)
  --read-pose            conecta e imprime a pose TCP atual (para montar pontos alcançáveis)
  --send NOME            gera e ENVIA o URScript da config NOME ao robô/URSim (o robô se move!)
  --ip IP                sobrescreve o IP da config (ex.: 192.168.2.102 do URSim)
"""

from __future__ import annotations

import argparse
import sys

from palletizer.app.controller import PalletizerController
from palletizer.comm.ur_socket import URConnection
from palletizer.config.store import ConfigStore


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Paletizador UR10")
    parser.add_argument("--configs", default="configs", help="diretório de configs")
    parser.add_argument("--list", action="store_true", help="lista as configs salvas")
    parser.add_argument("--gen", metavar="NOME", help="gera o URScript da config NOME")
    parser.add_argument("--out", default="scripts/palletizer_core.script",
                        help="arquivo de saída do --gen")
    parser.add_argument("--send", metavar="NOME", help="gera e ENVIA o URScript ao robô/URSim")
    parser.add_argument("--read-pose", action="store_true",
                        help="imprime a pose TCP atual do robô/URSim")
    parser.add_argument("--ip", help="sobrescreve o IP (ex.: 192.168.2.102 do URSim)")
    parser.add_argument("--port", type=int, default=30003, help="porta (default 30003)")
    args = parser.parse_args(argv)

    store = ConfigStore(args.configs)

    if args.list:
        for name in store.list_names():
            print(name)
        return 0

    if args.read_pose:
        ip = args.ip or "192.168.2.102"
        print(f"Conectando em {ip}:{args.port} ...")
        with URConnection(ip, args.port) as conn:
            pose = conn.read_tcp_pose()
        print("Pose TCP atual [x, y, z, rx, ry, rz] (m, rad):")
        print("  [%s]" % ", ".join("%.4f" % v for v in pose))
        return 0

    if args.gen:
        cfg = store.load(args.gen)
        path = PalletizerController(cfg).save_urscript(args.out)
        print(f"URScript gerado: {path}")
        return 0

    if args.send:
        cfg = store.load(args.send)
        if args.ip:
            cfg.robot.ip = args.ip
        cfg.robot.port = args.port
        ctrl = PalletizerController(cfg)
        # salva uma cópia do que será enviado (rastreabilidade)
        ctrl.save_urscript(args.out)
        print(f"Enviando '{args.send}' para {cfg.robot.ip}:{cfg.robot.port} ... (o robô vai se mover)")
        with URConnection(cfg.robot.ip, cfg.robot.port) as conn:
            ctrl.send_to_robot(conn)
        print("URScript enviado. Acompanhe a execução no PolyScope do URSim.")
        return 0

    # sem args → GUI
    from palletizer.gui import run_app
    try:
        return run_app(args.configs)
    except ImportError as exc:
        print(exc, file=sys.stderr)
        print("Dica: use --gen/--send NOME para operar sem GUI.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
