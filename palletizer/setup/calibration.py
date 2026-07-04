"""Calibração centralizada: nomes de pontos e valores de movimento padrão.

Mantém num só lugar (a) os pontos-chave que o operador deve ensinar e (b) os parâmetros de
velocidade/aceleração/blend — atendendo ao requisito de "calibração centralizada de padrões".
"""

from __future__ import annotations

from ..config.models import MotionParams, PalletizationConfig, TaughtPoint

# Pontos que a célula precisa para um ciclo pick→place completo.
DEFAULT_POINT_NAMES = (
    "home",            # posição segura de repouso
    "pick",            # onde a caixa é pega
    "pick_approach",   # aproximação vertical sobre o pick
    "pallet_corner",   # origem do frame do pallet (canto de referência)
    "pallet_approach",  # aproximação segura sobre o pallet
)


def ensure_default_points(config: PalletizationConfig) -> None:
    """Garante que a config tenha uma entrada para cada ponto-chave (pose zerada se ausente)."""
    for name in DEFAULT_POINT_NAMES:
        config.points.setdefault(name, TaughtPoint(name=name))


def default_motion() -> MotionParams:
    """Parâmetros de movimento conservadores para o primeiro setup no robô real."""
    return MotionParams()
