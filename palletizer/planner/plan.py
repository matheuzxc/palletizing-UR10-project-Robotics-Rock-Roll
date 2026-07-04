"""Plano de paletização — a FONTE DE VERDADE ÚNICA (DD1).

Uma lista ordenada de :class:`PlaceSlot` (pose relativa ao pallet + camada + Z acumulado)
que alimenta tanto o adaptador RoboDK (simulação) quanto o gerador de URScript (robô real).
Ambos renderizam a MESMA lista; divergência entre eles é bug.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..config.models import BoxSpec, PalletSpec, PalletizationConfig, PatternType
from .patterns import layer_positions


@dataclass(frozen=True)
class PlaceSlot:
    """Destino de uma caixa, relativo ao frame do pallet (mm/graus).

    - ``x, y`` : centro da caixa no plano do pallet.
    - ``z``    : centro da caixa em altura (topo acumulado das camadas abaixo + meia caixa).
    - ``rot_z``: orientação da caixa (0/90°).
    - ``layer``: índice da camada (0-based).
    - ``seq``  : ordem de colocação (0-based, de baixo para cima).
    """

    seq: int
    layer: int
    x: float
    y: float
    z: float
    rot_z: float


@dataclass
class PalletizationPlan:
    """Plano completo: todos os slots ordenados e a geometria de referência."""

    slots: List[PlaceSlot]
    box: BoxSpec
    pallet: PalletSpec
    pattern: PatternType

    def slots_in_layer(self, layer: int) -> List[PlaceSlot]:
        return [s for s in self.slots if s.layer == layer]

    @property
    def total_boxes(self) -> int:
        return len(self.slots)


def build_plan(config: PalletizationConfig) -> PalletizationPlan:
    """Constrói o plano ordenado (camada 0 primeiro) a partir da config."""
    box = config.box
    pallet = config.pallet
    slots: List[PlaceSlot] = []
    seq = 0
    for layer in range(pallet.layers):
        z_center = (layer + 0.5) * box.height  # topo acumulado + meia caixa (Z dinâmico)
        for (x, y, rot_z) in layer_positions(config.pattern, box, pallet, layer):
            slots.append(
                PlaceSlot(seq=seq, layer=layer, x=x, y=y, z=z_center, rot_z=rot_z)
            )
            seq += 1
    return PalletizationPlan(slots=slots, box=box, pallet=pallet, pattern=config.pattern)


def approach_height_mm(slot: PlaceSlot, box: BoxSpec, approach_height_m: float) -> float:
    """Altura de aproximação (mm) = topo da caixa nessa camada + folga de aproximação.

    Deriva do topo acumulado (``layer+1`` caixas de altura), nunca de um valor estático —
    atende à prevenção ativa de colisão exigida no trabalho.
    """
    top_of_layer = (slot.layer + 1) * box.height
    return top_of_layer + approach_height_m * 1000.0
