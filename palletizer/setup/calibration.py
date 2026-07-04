"""Calibração centralizada: pontos ensinados e valores de movimento padrão.

No modelo v2 o operador ensina por freedrive apenas ``home`` e ``pick``. O ``pick_approach`` é
DERIVADO (offset vertical sobre o pick, ver :func:`pick_approach_pose`) e o frame do pallet vem
dos 4 cantos (config), não de um ponto ensinado. Assim há um só lugar para (a) os pontos-chave
e (b) os parâmetros de velocidade/aceleração/blend/offsets/atuador.
"""

from __future__ import annotations

from typing import List

from ..config.models import MotionParams, PalletizationConfig, TaughtPoint

# Pontos que o operador ensina por freedrive para um ciclo pick→place (v2).
DEFAULT_POINT_NAMES = (
    "home",   # posição segura de repouso
    "pick",   # onde a caixa é pega
)


def ensure_default_points(config: PalletizationConfig) -> None:
    """Garante uma entrada para cada ponto-chave ensinado (pose zerada se ausente)."""
    for name in DEFAULT_POINT_NAMES:
        config.points.setdefault(name, TaughtPoint(name=name))


def pick_approach_pose(config: PalletizationConfig) -> List[float]:
    """Pose de aproximação do pick = pose de pick + offset vertical (m), sem ensinar.

    Deriva de ``motion.approach_pick_offset_z``; a orientação é a mesma do pick.
    """
    pick = config.points["pick"].pose
    dz = config.motion.approach_pick_offset_z
    return [pick[0], pick[1], pick[2] + dz, pick[3], pick[4], pick[5]]


def default_motion() -> MotionParams:
    """Parâmetros de movimento conservadores para o primeiro setup no robô real."""
    return MotionParams()
