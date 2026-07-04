"""Motor de padrões de amarração — módulos com contrato de entrada IDÊNTICO.

Cada padrão é uma função ``f(box, grid, layer) -> List[(x, y, rot_z)]`` (mesma assinatura),
registrada num dispatch. As posições são os CENTROS das caixas, em mm, relativas à origem do
frame do pallet. ``grid`` é a grade DERIVADA (``nx``/``ny`` calculados dos 4 cantos + caixa em
:mod:`palletizer.planner.geometry`) — nenhum padrão recomputa geometria.

Cada padrão define como o arranjo de uma camada muda em relação à anterior — é isso que
caracteriza a "amarração" que impede que as juntas verticais se alinhem entre camadas.

``rot_z`` é a orientação da caixa em torno de Z (0 ou 90); só afeta a pegada quando a caixa não
é quadrada. Convenção da grade: célula ``i`` centrada em ``(i + 0.5) * box``; ``i`` (eixo X) é o
índice interno e ``j`` (eixo Y) o externo — a mesma ordem raster do preenchimento.
"""

from __future__ import annotations

from typing import Callable, List, Protocol, Tuple

from ..config.models import BoxSpec, PatternType

Position = Tuple[float, float, float]  # (x, y, rot_z_graus)


class GridLike(Protocol):
    """Contrato mínimo que todo padrão consome (a grade derivada)."""

    nx: int
    ny: int


# Assinatura uniforme de TODO padrão (DD5).
PatternFn = Callable[[BoxSpec, GridLike, int], List[Position]]


def _base_grid(box: BoxSpec, grid: GridLike, layer: int) -> List[Position]:
    """Grade retangular padrão nx x ny, sem rotação (base reutilizada pelos demais)."""
    positions: List[Position] = []
    for j in range(grid.ny):
        for i in range(grid.nx):
            x = (i + 0.5) * box.length
            y = (j + 0.5) * box.width
            positions.append((x, y, 0.0))
    return positions


def _brick(box: BoxSpec, grid: GridLike, layer: int) -> List[Position]:
    """Camadas ímpares deslocadas meia-caixa em X → juntas defasadas entre camadas."""
    positions = _base_grid(box, grid, layer)
    if layer % 2 == 1:
        dx = box.length / 2.0
        positions = [(x + dx, y, rot) for (x, y, rot) in positions]
    return positions


def _pinhole(box: BoxSpec, grid: GridLike, layer: int) -> List[Position]:
    """Grade sem a caixa central (o 'furo') e girada 90° em camadas ímpares.

    O furo alterna de camada junto com a rotação, criando o encaixe característico.
    """
    positions = _base_grid(box, grid, layer)
    ci = (grid.nx - 1) / 2.0
    cj = (grid.ny - 1) / 2.0
    center_idx = round(cj) * grid.nx + round(ci)
    positions = [p for k, p in enumerate(positions) if k != center_idx]
    if layer % 2 == 1:
        positions = [(x, y, (rot + 90.0) % 180.0) for (x, y, rot) in positions]
    return positions


def _split_block(box: BoxSpec, grid: GridLike, layer: int) -> List[Position]:
    """Pallet dividido em metade esquerda/direita com orientações opostas, alternando por camada."""
    positions = _base_grid(box, grid, layer)
    mid = grid.nx / 2.0
    out: List[Position] = []
    for k, (x, y, rot) in enumerate(positions):
        i = k % grid.nx
        left = i < mid
        # camadas pares: esquerda=0°, direita=90°; ímpares invertem
        rotated = (left == (layer % 2 == 1))
        out.append((x, y, 90.0 if rotated else 0.0))
    return out


_DISPATCH: dict[PatternType, PatternFn] = {
    PatternType.GRID: _base_grid,
    PatternType.BRICK: _brick,
    PatternType.PINHOLE: _pinhole,
    PatternType.SPLIT_BLOCK: _split_block,
}

# Padrões de amarração oferecidos ao operador (o 'grid' fica como base interna, não selecionável).
_SELECTABLE = (PatternType.BRICK, PatternType.PINHOLE, PatternType.SPLIT_BLOCK)


def selectable_patterns() -> Tuple[PatternType, ...]:
    """Os padrões de amarração selecionáveis na GUI (Brick, Pinhole, Split Block)."""
    return _SELECTABLE


def layer_positions(
    pattern: PatternType, box: BoxSpec, grid: GridLike, layer: int
) -> List[Position]:
    """Posições ``(x, y, rot_z)`` dos centros das caixas de uma camada (contrato uniforme)."""
    return _DISPATCH[pattern](box, grid, layer)


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
