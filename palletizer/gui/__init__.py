"""GUI do operador (PyQt6).

O import do PyQt é opcional: a lógica de negócio não depende dele, então os testes e o core
rodam sem PyQt instalado. Use :func:`is_available` para checar antes de abrir a janela.
"""

from __future__ import annotations


def is_available() -> bool:
    try:
        import PyQt6.QtWidgets  # noqa: F401
        return True
    except Exception:
        return False


def run_app(configs_dir: str = "configs") -> int:
    """Ponto de entrada da GUI. Levanta ImportError amigável se PyQt faltar."""
    if not is_available():
        raise ImportError(
            "PyQt6 não instalado. Rode 'pip install PyQt6' ou use a CLI/geração de script."
        )
    from .main_window import launch
    return launch(configs_dir)


__all__ = ["is_available", "run_app"]
