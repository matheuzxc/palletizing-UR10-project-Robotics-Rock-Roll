"""Adaptador RoboDK — dirige a estação via API a partir do plano de paletização (DD2).

Renderiza o mesmo :class:`~palletizer.planner.plan.PalletizationPlan` que o gerador de
URScript, reaproveitando o padrão de ``RobotB_StoreParts.py``: poses relativas ao
``frame_pallet``, ``MoveJ`` na aproximação/transição e ``MoveL`` na descida/recuo.

Dependências injetadas para permitir teste sem o RoboDK instalado:
- ``rdk``           : objeto tipo ``Robolink`` (``.Item(name)`` retorna itens da estação).
- ``pose_factory``  : constrói a pose a ser passada para ``MoveJ``/``MoveL`` a partir de
  ``(x_mm, y_mm, z_mm, rot_z_deg)``. O default usa ``robodk.robomath`` (import tardio);
  os testes injetam uma fábrica trivial.
"""

from __future__ import annotations

from typing import Callable, Optional

from ..config.models import MotionParams, PalletizationConfig
from ..planner.plan import PalletizationPlan, approach_height_mm, build_plan
from .station import StationItems

PoseFactory = Callable[[float, float, float, float], object]


def _robomath_pose_factory() -> PoseFactory:
    """Fábrica de poses baseada em ``robomath`` (usada em execução real)."""
    try:
        from robodk import robomath  # pacote pip moderno
    except ImportError:  # pragma: no cover - instalação embutida/legada
        import robomath  # type: ignore

    def factory(x_mm: float, y_mm: float, z_mm: float, rot_z_deg: float):
        # transl usa mm na estação; rotx(pi) aponta a garra para baixo (como no box_calc);
        # rotz aplica a orientação da caixa do padrão.
        return (
            robomath.transl(x_mm, y_mm, z_mm)
            * robomath.rotx(robomath.pi)
            * robomath.rotz(robomath.pi * rot_z_deg / 180.0)
        )

    return factory


class RoboDKAdapter:
    def __init__(
        self,
        rdk,
        items: Optional[StationItems] = None,
        pose_factory: Optional[PoseFactory] = None,
    ) -> None:
        self.rdk = rdk
        self.items = items or StationItems()
        self._pose_factory = pose_factory
        self.placed = 0

    def _factory(self) -> PoseFactory:
        if self._pose_factory is None:
            self._pose_factory = _robomath_pose_factory()
        return self._pose_factory

    def run_plan(self, config: PalletizationConfig, plan: Optional[PalletizationPlan] = None) -> int:
        """Executa o plano na estação. Retorna o número de caixas colocadas."""
        if plan is None:
            plan = build_plan(config)

        motion: MotionParams = config.motion
        robot = self.rdk.Item(self.items.robot)
        tool = self.rdk.Item(self.items.tool)
        frame = self.rdk.Item(self.items.frame_pallet)
        safe = self.rdk.Item(self.items.target_pallet_safe)

        robot.setPoseFrame(frame)
        if tool is not None:
            robot.setPoseTool(tool)

        make = self._factory()
        self.placed = 0
        for slot in plan.slots:
            app_z = approach_height_mm(slot, plan.box, motion.approach_height)
            target = make(slot.x, slot.y, slot.z, slot.rot_z)
            approach = make(slot.x, slot.y, app_z, slot.rot_z)

            robot.MoveJ(safe)          # transição aérea segura
            robot.MoveJ(approach)      # desce até a aproximação (espaço de juntas)
            robot.MoveL(target)        # descida linear até o ponto de place
            self._detach(tool)         # solta a caixa (place)
            robot.MoveL(approach)      # recuo linear
            self.placed += 1

        robot.MoveJ(safe)
        return self.placed

    @staticmethod
    def _detach(tool) -> None:
        # Em RoboDK real: DetachAll deposita a peça. Protegido para o duplo de teste.
        detach = getattr(tool, "DetachAll", None)
        if callable(detach):
            detach()
