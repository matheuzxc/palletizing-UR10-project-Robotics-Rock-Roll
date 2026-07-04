"""Conexão com o RoboDK, tolerante às duas formas de importar a API.

- Pacote pip moderno: ``from robodk.robolink import Robolink``.
- Instalação embutida/legada do RoboDK: ``from robolink import Robolink``.

Requer o RoboDK **aberto** com a estação em foco.
"""

from __future__ import annotations


def _import_robolink():
    try:
        from robodk.robolink import Robolink  # pacote pip moderno
        return Robolink
    except ImportError:
        from robolink import Robolink  # instalação embutida/legada
        return Robolink


def new_robolink():
    """Cria uma conexão Robolink com o RoboDK aberto (levanta erro claro se ausente)."""
    try:
        Robolink = _import_robolink()
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise ImportError(
            "Pacote 'robodk' não encontrado. Rode 'pip install robodk' no seu Python, "
            "ou execute com o Python embutido do RoboDK "
            "(C:/RoboDK/Python-Embedded/python.exe)."
        ) from exc
    return Robolink()
