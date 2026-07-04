"""Gerador do ``palletizer_core.script`` (URScript nativo).

Renderiza o :class:`~palletizer.planner.plan.PalletizationPlan` (fonte de verdade única)
como URScript, relativo aos pontos ensinados por freedrive. Princípios do trabalho:

- Parâmetros de velocidade/aceleração/blend **centralizados no topo** do script (DD4).
- ``movej`` nas transições aéreas e no retorno ao home; ``movel`` nas
  aproximações/descidas/recuos verticais.
- ``blend_radius`` (r) nos movimentos aéreos para trajetória fluida.
- Poses de place derivadas do canto do pallet via ``pose_trans`` (frame do pallet), com Z de
  aproximação a partir do topo acumulado da camada (colisão ativa, nunca ponto estático).

O gerador não move nada: devolve uma string. O envio é responsabilidade da camada ``comm``.
"""

from __future__ import annotations

from math import radians
from typing import Dict

from ..config.models import MotionParams, PalletizationConfig, TaughtPoint
from ..planner.plan import PalletizationPlan, approach_height_mm, build_plan

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
    pick_app = _require_point(pts, "pick_approach")
    corner = _require_point(pts, "pallet_corner")
    pallet_app = _require_point(pts, "pallet_approach")
    home = _require_point(pts, "home")

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
    a("  # --- pontos ensinados (freedrive) ---")
    a("  p_home         = %s" % _pose(home.pose))
    a("  p_pick         = %s" % _pose(pick.pose))
    a("  p_pick_app     = %s" % _pose(pick_app.pose))
    a("  p_pallet       = %s" % _pose(corner.pose))
    a("  p_pallet_app   = %s" % _pose(pallet_app.pose))
    a("")
    a("  def gripper(state):")
    a("    # TODO: mapear para a saída digital real da garra da célula")
    a("    set_digital_out(0, state)")
    a("    sleep(0.3)")
    a("  end")
    a("")
    a("  movej(p_home, a=a_joint, v=v_joint)")

    for slot in plan.slots:
        dx = slot.x / _MM
        dy = slot.y / _MM
        dz = slot.z / _MM
        rz = radians(slot.rot_z)
        app_dz = approach_height_mm(slot, plan.box, m.approach_height) / _MM
        a("  # caixa %d (camada %d)" % (slot.seq + 1, slot.layer))
        # --- pega ---
        a("  movej(p_pick_app, a=a_joint, v=v_joint, r=blend_r)")
        a("  movel(p_pick, a=a_nominal, v=v_nominal)")
        a("  gripper(True)")
        a("  movel(p_pick_app, a=a_nominal, v=v_nominal)")
        # --- transporte + place (relativo ao frame do pallet) ---
        a("  p_place     = pose_trans(p_pallet, p[%.6f, %.6f, %.6f, 0, 0, %.6f])"
          % (dx, dy, dz, rz))
        a("  p_place_app = pose_trans(p_pallet, p[%.6f, %.6f, %.6f, 0, 0, %.6f])"
          % (dx, dy, app_dz, rz))
        a("  movej(p_pallet_app, a=a_joint, v=v_joint, r=blend_r)")
        a("  movel(p_place_app, a=a_nominal, v=v_nominal)")
        a("  if (is_within_safety_limits(p_place)):")
        a("    movel(p_place, a=a_nominal, v=v_nominal)")
        a("    gripper(False)")
        a("    movel(p_place_app, a=a_nominal, v=v_nominal)")
        a("  end")

    a("  movej(p_home, a=a_joint, v=v_joint)")
    a("end")
    return "\n".join(lines) + "\n"
