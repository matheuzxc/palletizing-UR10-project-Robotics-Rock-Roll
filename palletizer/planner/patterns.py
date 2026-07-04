"""Motor de padrões de amarração.

Estende a lógica do ``box_calc`` (estação RoboDK ``RobotB_StoreParts.py``): posições dos
CENTROS das caixas, em mm, relativas ao frame do pallet. Cada padrão define como o arranjo
de uma camada muda em relação à anterior — é isso que caracteriza a "amarração" que impede
que as juntas verticais se alinhem entre camadas.

Cada posição é ``(x, y, rot_z_graus)``. ``rot_z`` é a orientação da caixa em torno de Z
(0 ou 90); só afeta a pegada quando a caixa não é quadrada.

Convenção da grade: célula ``i`` centrada em ``(i + 0.5) * box``. Camadas indexadas por
``layer`` (0-based); padrões alternam por paridade de ``layer``.
"""

from __future__ import annotations

from typing import List, Tuple

from ..config.models import BoxSpec, PalletSpec, PatternType

Position = Tuple[float, float, float]  # (x, y, rot_z_graus)


def _base_grid(box: BoxSpec, pallet: PalletSpec) -> List[Position]:
    """Grade retangular padrão nx x ny, sem rotação."""
    positions: List[Position] = []
    for j in range(pallet.ny):
        for i in range(pallet.nx):
            x = (i + 0.5) * box.length
            y = (j + 0.5) * box.width
            positions.append((x, y, 0.0))
    return positions


def _brick(box: BoxSpec, pallet: PalletSpec, layer: int) -> List[Position]:
    """Camadas ímpares deslocadas meia-caixa em X → juntas defasadas entre camadas."""
    positions = _base_grid(box, pallet)
    if layer % 2 == 1:
        dx = box.length / 2.0
        positions = [(x + dx, y, rot) for (x, y, rot) in positions]
    return positions


def _pinhole(box: BoxSpec, pallet: PalletSpec, layer: int) -> List[Position]:
    """Grade sem a caixa central (o 'furo') e girada 90° em camadas ímpares.

    O furo alterna de camada junto com a rotação, criando o encaixe característico.
    """
    positions = _base_grid(box, pallet)
    # índice central (mais próximo do centro da grade)
    ci = (pallet.nx - 1) / 2.0
    cj = (pallet.ny - 1) / 2.0
    center_idx = round(cj) * pallet.nx + round(ci)
    positions = [p for k, p in enumerate(positions) if k != center_idx]
    if layer % 2 == 1:
        positions = [(x, y, (rot + 90.0) % 180.0) for (x, y, rot) in positions]
    return positions


def _split_block(box: BoxSpec, pallet: PalletSpec, layer: int) -> List[Position]:
    """Pallet dividido em metade esquerda/direita com orientações opostas, alternando por camada."""
    positions = _base_grid(box, pallet)
    mid = pallet.nx / 2.0
    out: List[Position] = []
    for k, (x, y, rot) in enumerate(positions):
        i = k % pallet.nx
        left = i < mid
        # camadas pares: esquerda=0°, direita=90°; ímpares invertem
        rotated = (left == (layer % 2 == 1))
        out.append((x, y, 90.0 if rotated else 0.0))
    return out


_DISPATCH = {
    PatternType.GRID: lambda box, pallet, layer: _base_grid(box, pallet),
    PatternType.BRICK: _brick,
    PatternType.PINHOLE: _pinhole,
    PatternType.SPLIT_BLOCK: _split_block,
}


def layer_positions(
    pattern: PatternType, box: BoxSpec, pallet: PalletSpec, layer: int
) -> List[Position]:
    """Posições ``(x, y, rot_z)`` dos centros das caixas de uma camada."""
    return _DISPATCH[pattern](box, pallet, layer)


def _extents(box: BoxSpec, rot_z: float) -> Tuple[float, float]:
    """Meia-pegada (ex, ey) considerando rotação de 0/90°."""
    if round(rot_z) % 180 == 90:
        return box.width / 2.0, box.length / 2.0
    return box.length / 2.0, box.width / 2.0


def footprints_overlap(
    a: Position, b: Position, box: BoxSpec, eps: float = 1e-6
) -> bool:
    """True se as pegadas AABB de duas caixas se sobrepõem (encostar não conta)."""
    ax, ay, arot = a
    bx, by, brot = b
    aex, aey = _extents(box, arot)
    bex, bey = _extents(box, brot)
    overlap_x = abs(ax - bx) < (aex + bex) - eps
    overlap_y = abs(ay - by) < (aey + bey) - eps
    return overlap_x and overlap_y
