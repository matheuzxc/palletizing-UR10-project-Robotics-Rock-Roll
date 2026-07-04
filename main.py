"""Ponto de entrada do software de paletização.

- Sem argumentos: abre a GUI (requer PyQt6).
- ``--gen NOME``: gera o URScript da config NOME e imprime/salva (sem GUI, sem robô).
- ``--list``: lista as configs salvas.
"""

from __future__ import annotations

import argparse
import sys

from palletizer.config.store import ConfigStore
from palletizer.app.controller import PalletizerController


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Paletizador UR10")
    parser.add_argument("--configs", default="configs", help="diretório de configs")
    parser.add_argument("--list", action="store_true", help="lista as configs salvas")
    parser.add_argument("--gen", metavar="NOME", help="gera o URScript da config NOME")
    parser.add_argument("--out", default="scripts/palletizer_core.script",
                        help="arquivo de saída do --gen")
    args = parser.parse_args(argv)

    store = ConfigStore(args.configs)

    if args.list:
        for name in store.list_names():
            print(name)
        return 0

    if args.gen:
        cfg = store.load(args.gen)
        path = PalletizerController(cfg).save_urscript(args.out)
        print(f"URScript gerado: {path}")
        return 0

    # sem args → GUI
    from palletizer.gui import run_app
    try:
        return run_app(args.configs)
    except ImportError as exc:
        print(exc, file=sys.stderr)
        print("Dica: use --gen NOME para gerar o script sem GUI.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
