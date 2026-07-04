"""Geometria do pallet a partir dos 4 cantos (v2).

Constrói o frame do pallet (origem + eixos X/Y + eixo Z) a partir dos 4 cantos ensinados no
CHÃO, deriva a grade útil ``nx``/``ny`` pelas dimensões da caixa, ancora o Z de place no chão
+ altura acumulada, e calcula o offset de approach diagonal pelo lado ainda VAZIO (oposto ao
avanço do preenchimento).

Convenção de unidades: cantos e origem em **metros**; extensões e offsets expostos em **mm**
(mesma unidade do motor de padrões e do :class:`~palletizer.planner.plan.PlaceSlot`). Poses de
saída (``frame_to_ur_pose``) em ``[x, y, z, rx, ry, rz]`` (m, rad, vetor de rotação).

Matemática vetorial em Python puro (sem numpy) para manter os testes sem dependências.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from ..config.models import BoxSpec, PalletSpec

Vec3 = Tuple[float, float, float]
_MM = 1000.0

# Tolerâncias de consistência dos 4 cantos ensinados (folga de teach realista).
_CLOSURE_TOL_M = 0.02      # |c2 - (c0 + vx + vy)| < 20 mm  → retângulo fecha
_PERP_TOL = 0.10           # |cos(ângulo entre eixos)| < 0.10 (~6°) → cantos quase perpendiculares
_COPLANAR_TOL_M = 0.02     # desvio dos cantos ao plano médio < 20 mm


def _sub(a: Sequence[float], b: Sequence[float]) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a: Sequence[float], b: Sequence[float]) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a: Sequence[float], k: float) -> Vec3:
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Sequence[float], b: Sequence[float]) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _norm(a: Sequence[float]) -> float:
    return math.sqrt(_dot(a, a))


def _unit(a: Sequence[float]) -> Vec3:
    n = _norm(a)
    if n == 0.0:
        raise ValueError("Vetor nulo: cantos do pallet coincidentes.")
    return _scale(a, 1.0 / n)


@dataclass(frozen=True)
class PalletFrame:
    """Frame do pallet no mundo (metros). Eixos unitários; extensões em mm."""

    origin: Vec3       # c0 (m)
    ex: Vec3           # eixo X (comprimento) unitário
    ey: Vec3           # eixo Y (largura) unitário
    ez: Vec3           # eixo Z (normal ao plano do pallet) unitário
    length_mm: float   # |c0→c1| em mm
    width_mm: float    # |c0→c3| em mm
    floor_z: float     # z médio dos cantos (m)


@dataclass(frozen=True)
class PalletGrid:
    """Grade derivada: quantas caixas cabem por eixo + o frame do pallet."""

    nx: int
    ny: int
    frame: PalletFrame


def build_frame(corners: Sequence[Sequence[float]]) -> PalletFrame:
    """Constrói o frame do pallet a partir dos 4 cantos (chão), validando a consistência.

    ``corners`` = ``[c0, c1, c2, c3]`` (m): origem, fim do comprimento, diagonal oposta, fim
    da largura. Suporta pallet girado no plano. Levanta ``ValueError`` se os cantos não
    formarem um retângulo aproximadamente coplanar (erro de teach).
    """
    if len(corners) != 4:
        raise ValueError(f"São necessários 4 cantos do pallet; recebido {len(corners)}.")
    c0, c1, c2, c3 = (tuple(float(v) for v in c) for c in corners)

    vx = _sub(c1, c0)
    vy = _sub(c3, c0)
    length = _norm(vx)
    if length == 0.0 or _norm(vy) == 0.0:
        raise ValueError("Cantos degenerados: comprimento ou largura nulos.")

    ex = _unit(vx)
    ey_raw = _unit(vy)

    # Perpendicularidade (retângulo, não paralelogramo arbitrário).
    if abs(_dot(ex, ey_raw)) > _PERP_TOL:
        raise ValueError(
            "Cantos do pallet não são perpendiculares o suficiente "
            f"(|cos|={abs(_dot(ex, ey_raw)):.3f} > {_PERP_TOL}); verifique o teach dos cantos."
        )

    # Fechamento do retângulo: c2 ≈ c0 + vx + vy.
    expected_c2 = _add(_add(c0, vx), vy)
    if _norm(_sub(c2, expected_c2)) > _CLOSURE_TOL_M:
        raise ValueError(
            "Os 4 cantos não fecham um retângulo "
            f"(erro {_norm(_sub(c2, expected_c2)) * _MM:.1f} mm > {_CLOSURE_TOL_M * _MM:.0f} mm)."
        )

    # Base ORTONORMAL (Gram-Schmidt): o teach real nunca é perfeitamente perpendicular; sem
    # ortonormalizar, [ex, ey, ez] não é uma matriz de rotação válida e o vetor de rotação de
    # ``frame_to_ur_pose`` sai errado. ez normal ao plano; ey = ez × ex (destro, unitário).
    ez = _unit(_cross(ex, ey_raw))
    ey = _cross(ez, ex)

    # Coplanaridade: desvio dos cantos ao plano que passa por c0 com normal ez.
    for c in (c1, c2, c3):
        if abs(_dot(_sub(c, c0), ez)) > _COPLANAR_TOL_M:
            raise ValueError(
                "Cantos do pallet não são coplanares o suficiente "
                f"(desvio {abs(_dot(_sub(c, c0), ez)) * _MM:.1f} mm); pallet inclinado não suportado."
            )

    # Extensão da largura projetada no eixo ortonormal ey (≈ |vy|; casa com nx/ny estáveis).
    width = _dot(vy, ey)
    floor_z = sum(c[2] for c in (c0, c1, c2, c3)) / 4.0
    return PalletFrame(
        origin=c0, ex=ex, ey=ey, ez=ez,
        length_mm=length * _MM, width_mm=width * _MM, floor_z=floor_z,
    )


def derive_grid_counts(frame: PalletFrame, box: BoxSpec) -> Tuple[int, int]:
    """Quantas caixas cabem por eixo. Levanta ``ValueError`` se a caixa não couber."""
    nx = int(frame.length_mm // box.length)
    ny = int(frame.width_mm // box.width)
    if nx < 1 or ny < 1:
        raise ValueError(
            f"Caixa ({box.length}x{box.width} mm) não cabe no pallet "
            f"({frame.length_mm:.0f}x{frame.width_mm:.0f} mm): nx={nx}, ny={ny}."
        )
    return nx, ny


def build_grid(pallet: PalletSpec, box: BoxSpec) -> PalletGrid:
    """Frame + contagens derivadas, a partir da config do pallet e da caixa."""
    frame = build_frame(pallet.corners)
    nx, ny = derive_grid_counts(frame, box)
    return PalletGrid(nx=nx, ny=ny, frame=frame)


def place_z(layer: int, box: BoxSpec, floor_z: float) -> float:
    """Z ABSOLUTO (m) do centro da caixa: chão + topo acumulado + meia caixa.

    ``floor_z`` em metros; ``box.height`` em mm. Z dinâmico (colisão ativa), nunca estático.
    """
    return floor_z + (layer + 0.5) * (box.height / _MM)


def empty_side_direction(i: int, j: int, nx: int, ny: int) -> Tuple[float, float]:
    """Sentido (no frame do pallet) do lado ainda VAZIO para o approach diagonal.

    O preenchimento avança em ordem raster (``i`` interno, ``j`` externo, ambos crescentes):
    ao colocar ``(i, j)`` já estão no lugar as caixas com índice menor (lados ``-x``/``-y``).
    O lado vazio é, portanto, o de índices crescentes (``+x``, ``+y``) — inclusive na borda,
    onde apontar para fora do pallet ainda cai em espaço livre. Assim a descida diagonal nunca
    varre caixas já empilhadas. Determinístico pela ordem de colocação.
    """
    return (1.0, 1.0)


def empty_side_offset_mm(
    direction: Tuple[float, float], offset_xy_m: float, offset_z_m: float
) -> Vec3:
    """Offset de approach (mm, no frame do pallet) a somar à pose-alvo da caixa.

    ``direction`` = saída de :func:`empty_side_direction`; ``offset_xy_m``/``offset_z_m`` em
    metros (config). O offset é aplicado no frame do pallet; a rotação para o mundo é feita
    por ``pose_trans`` (URScript) ou pelo ``frame_pallet`` da estação (RoboDK).
    """
    sx, sy = direction
    return (sx * offset_xy_m * _MM, sy * offset_xy_m * _MM, offset_z_m * _MM)


def frame_to_ur_pose(frame: PalletFrame) -> List[float]:
    """Frame do pallet como pose UR ``[x, y, z, rx, ry, rz]`` (m, rad, vetor de rotação).

    Frame NATURAL do pallet com **Z para cima**: ``R = [ex, ey, ez]``. O empilhamento usa
    ``+dz`` (sobe) neste frame. A orientação "garra para baixo" NÃO é embutida aqui — é aplicada
    por caixa no offset de place (:func:`tool_down_offset_rotvec`, ``rotx(pi)*rotz``), espelhando
    exatamente o ``transl*rotx(pi)*rotz`` do adapter RoboDK (fonte única, DD1).
    """
    ex, ey, ez = frame.ex, frame.ey, frame.ez
    r = [
        [ex[0], ey[0], ez[0]],
        [ex[1], ey[1], ez[1]],
        [ex[2], ey[2], ez[2]],
    ]
    rx, ry, rz = _rotation_vector(r)
    ox, oy, oz = frame.origin
    return [ox, oy, oz, rx, ry, rz]


def tool_down_offset_rotvec(rot_z_deg: float) -> Vec3:
    """Vetor de rotação do offset de place: ``rotx(pi) * rotz(rot_z)`` (garra para baixo).

    Emitido no ``pose_trans(p_pallet, p[dx, dy, dz, rx, ry, rz])`` para a garra apontar para
    baixo com o yaw ``rot_z`` da caixa — igual ao ``rotx(pi)*rotz`` aplicado por caixa no adapter.
    """
    rz = math.radians(rot_z_deg)
    cz, sz = math.cos(rz), math.sin(rz)
    r_z = [[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]]
    r_x = [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]]  # rotx(pi)
    r = _matmul3(r_x, r_z)
    return _rotation_vector(r)


def _matmul3(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    return [
        [sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)]
        for i in range(3)
    ]


def _rotation_vector(r: List[List[float]]) -> Vec3:
    """Converte matriz de rotação 3x3 (row-major) para vetor de rotação (eixo * ângulo)."""
    trace = r[0][0] + r[1][1] + r[2][2]
    cos_theta = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
    theta = math.acos(cos_theta)

    if theta < 1e-8:
        return (0.0, 0.0, 0.0)

    if math.pi - theta < 1e-6:
        # Ângulo ~ pi: eixo pelo maior elemento diagonal de (R + I)/2.
        xx = (r[0][0] + 1.0) / 2.0
        yy = (r[1][1] + 1.0) / 2.0
        zz = (r[2][2] + 1.0) / 2.0
        if xx >= yy and xx >= zz:
            ax = math.sqrt(max(xx, 0.0))
            ay = (r[0][1] + r[1][0]) / (4.0 * ax) if ax else 0.0
            az = (r[0][2] + r[2][0]) / (4.0 * ax) if ax else 0.0
        elif yy >= zz:
            ay = math.sqrt(max(yy, 0.0))
            ax = (r[0][1] + r[1][0]) / (4.0 * ay) if ay else 0.0
            az = (r[1][2] + r[2][1]) / (4.0 * ay) if ay else 0.0
        else:
            az = math.sqrt(max(zz, 0.0))
            ax = (r[0][2] + r[2][0]) / (4.0 * az) if az else 0.0
            ay = (r[1][2] + r[2][1]) / (4.0 * az) if az else 0.0
        return (ax * theta, ay * theta, az * theta)

    s = 2.0 * math.sin(theta)
    ax = (r[2][1] - r[1][2]) / s
    ay = (r[0][2] - r[2][0]) / s
    az = (r[1][0] - r[0][1]) / s
    return (ax * theta, ay * theta, az * theta)
