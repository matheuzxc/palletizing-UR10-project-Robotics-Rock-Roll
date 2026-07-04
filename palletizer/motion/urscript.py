"""Gerador do ``palletizer_core.script`` (URScript nativo).

Renderiza o :class:`~palletizer.planner.plan.PalletizationPlan` (fonte de verdade única)
como URScript. Princípios do trabalho:

- Parâmetros de velocidade/aceleração/blend **centralizados no topo** do script (DD4).
- ``movej`` nas transições aéreas e no retorno ao home; ``movel`` nas
  aproximações/descidas/recuos verticais.
- ``blend_radius`` (r) nos movimentos aéreos para trajetória fluida.
- ``p_pallet`` derivado dos 4 cantos (frame do pallet); poses de place por ``pose_trans``
  relativo a esse frame, com Z do chão + topo acumulado da camada (colisão ativa).
- ``pick_approach`` DERIVADO (offset vertical sobre o pick), não ensinado.
- Approach do pallet DINÂMICO por caixa: offset diagonal pelo lado ainda vazio (DD4).
- Atuador nas ventosas em ``D<gripper_do>``, mantido ``gripper_hold_s`` segundos (default 5 s).

O gerador não move nada: devolve uma string. O envio é responsabilidade da camada ``comm``.
"""

from __future__ import annotations

from typing import Dict

from ..config.models import MotionParams, PalletizationConfig, TaughtPoint
from ..planner.geometry import frame_to_ur_pose, tool_down_offset_rotvec
from ..planner.plan import (
    PalletizationPlan,
    build_plan,
    pallet_approach_pose_mm,
)
from ..setup.calibration import pick_approach_pose

_MM = 1000.0  # o URScript trabalha em metros; o plano está em mm.


def _pose(p) -> str:
    return "p[%.6f, %.6f, %.6f, %.6f, %.6f, %.6f]" % tuple(p)


def _require_point(points: Dict[str, TaughtPoint], name: str) -> TaughtPoint:
    if name not in points:
        raise KeyError(f"Ponto ensinado ausente: '{name}'. Ensine-o por freedrive antes de gerar.")
    return points[name]


def generate_script(config: PalletizationConfig, plan: PalletizationPlan | None = None) -> str:
    """Gera o URScript completo de paletização para a config dada."""
    if plan is None:
        plan = build_plan(config)

    m: MotionParams = config.motion
    pts = config.points
    pick = _require_point(pts, "pick")
    home = _require_point(pts, "home")
    pick_app = pick_approach_pose(config)          # derivado (offset vertical sobre o pick)
    pallet_pose = frame_to_ur_pose(plan.grid.frame)  # frame do pallet dos 4 cantos

    lines = []
    a = lines.append

    a("# palletizer_core.script  — gerado por palletizer")
    a("# Formato: %s | camadas: %d | caixas: %d"
      % (config.pattern.value, config.pallet.layers, plan.total_boxes))
    a("#")
    a("# Todo o programa vive dentro de UM único def de topo: as interfaces cliente do UR")
    a("# (30001/30002/30003) executam automaticamente a função recebida. Por isso NÃO há")
    a("# chamada global no fim — enviar instruções soltas de escopo global não roda de")
    a("# forma confiável (o robô fica parado, sem falha nem movimento).")
    a("")
    a("def palletizer_prog():")
    a("  # --- calibração centralizada (ajuste rápido de conformidade) ---")
    a("  v_nominal   = %.4f   # velocidade linear (m/s)" % m.v_nominal)
    a("  a_nominal   = %.4f   # aceleração linear (m/s^2)" % m.a_nominal)
    a("  v_joint     = %.4f   # velocidade de junta (rad/s)" % m.v_joint)
    a("  a_joint     = %.4f   # aceleração de junta (rad/s^2)" % m.a_joint)
    a("  blend_r     = %.4f   # raio de concordância (m)" % m.blend_radius)
    a("")
    a("  # --- pontos: home e pick ensinados; pick_approach derivado; pallet dos 4 cantos ---")
    a("  p_home         = %s" % _pose(home.pose))
    a("  p_pick         = %s" % _pose(pick.pose))
    a("  p_pick_app     = %s" % _pose(pick_app))
    a("  p_pallet       = %s" % _pose(pallet_pose))
    a("")
    a("  def gripper(state):")
    a("    # atuador de ventosas em D%d, mantido %.1f s para prender a caixa"
      % (m.gripper_do, m.gripper_hold_s))
    a("    set_digital_out(%d, state)" % m.gripper_do)
    a("    if (state):")
    a("      sleep(%.1f)" % m.gripper_hold_s)
    a("    else:")
    a("      sleep(0.3)")
    a("    end")
    a("  end")
    a("")
    a("  movej(p_home, a=a_joint, v=v_joint)")

    for slot in plan.slots:
        dx = slot.x / _MM
        dy = slot.y / _MM
        dz = slot.z / _MM
        # orientação do offset = garra para baixo + yaw da caixa (rotx(pi)*rotz), como no adapter
        rvx, rvy, rvz = tool_down_offset_rotvec(slot.rot_z)
        ax_mm, ay_mm, az_mm = pallet_approach_pose_mm(slot, plan.box, plan.grid, m)
        adx = ax_mm / _MM
        ady = ay_mm / _MM
        adz = az_mm / _MM
        a("  # caixa %d (camada %d, celula i=%d j=%d)" % (slot.seq + 1, slot.layer, slot.i, slot.j))
        # --- pega ---
        a("  movej(p_pick_app, a=a_joint, v=v_joint, r=blend_r)")
        a("  movel(p_pick, a=a_nominal, v=v_nominal)")
        a("  gripper(True)")
        a("  movel(p_pick_app, a=a_nominal, v=v_nominal)")
        # --- transporte + place (frame Z-up do pallet; garra p/ baixo; approach do lado vazio) ---
        a("  p_place     = pose_trans(p_pallet, p[%.6f, %.6f, %.6f, %.6f, %.6f, %.6f])"
          % (dx, dy, dz, rvx, rvy, rvz))
        a("  p_place_app = pose_trans(p_pallet, p[%.6f, %.6f, %.6f, %.6f, %.6f, %.6f])"
          % (adx, ady, adz, rvx, rvy, rvz))
        a("  movej(p_place_app, a=a_joint, v=v_joint, r=blend_r)")
        a("  if (is_within_safety_limits(p_place)):")
        a("    movel(p_place, a=a_nominal, v=v_nominal)")
        a("    gripper(False)")
        a("    movel(p_place_app, a=a_nominal, v=v_nominal)")
        a("  end")

    a("  movej(p_home, a=a_joint, v=v_joint)")
    a("end")
    return "\n".join(lines) + "\n"
