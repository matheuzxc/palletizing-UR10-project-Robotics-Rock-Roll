"""Orquestração do software.

Une config → plano → (simulação RoboDK | envio real por URScript). Mantém uma máquina de
estados simples que impede iniciar um ciclo enquanto outro está em curso — reforçando o
canal serializado (DD5) na camada de aplicação, além do lock no socket.
"""

from __future__ import annotations

import enum
from pathlib import Path
from typing import Optional

from ..config.models import PalletizationConfig
from ..motion.urscript import generate_script
from ..planner.plan import PalletizationPlan, build_plan


class CycleState(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


class CycleBusyError(RuntimeError):
    """Levantado ao tentar iniciar um ciclo com outro em andamento."""


class PalletizerController:
    def __init__(self, config: PalletizationConfig) -> None:
        self.config = config
        self.state = CycleState.IDLE
        self._plan: Optional[PalletizationPlan] = None

    @property
    def plan(self) -> PalletizationPlan:
        if self._plan is None:
            self._plan = build_plan(self.config)
        return self._plan

    def invalidate_plan(self) -> None:
        """Chamar após alterar a config (formato, pallet, caixa)."""
        self._plan = None

    # -- simulação -----------------------------------------------------------------
    def run_simulation(self, adapter) -> int:
        """Roda o plano no RoboDK via adaptador. Retorna nº de caixas colocadas."""
        with self._running():
            return adapter.run_plan(self.config, self.plan)

    # -- robô real -----------------------------------------------------------------
    def build_urscript(self) -> str:
        """Gera o URScript sem enviar (para inspeção/salvar)."""
        return generate_script(self.config, self.plan)

    def save_urscript(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.build_urscript(), encoding="utf-8", newline="\n")
        return path

    def send_to_robot(self, connection) -> None:
        """Gera e envia o URScript pelo canal serializado."""
        script = self.build_urscript()
        with self._running():
            connection.send(script)

    # -- máquina de estados --------------------------------------------------------
    def _running(self):
        return _RunningGuard(self)


class _RunningGuard:
    def __init__(self, controller: PalletizerController) -> None:
        self.controller = controller

    def __enter__(self):
        if self.controller.state == CycleState.RUNNING:
            raise CycleBusyError("Já existe um ciclo em andamento; envio serializado.")
        self.controller.state = CycleState.RUNNING
        return self.controller

    def __exit__(self, exc_type, exc, tb):
        self.controller.state = CycleState.ERROR if exc_type else CycleState.IDLE
        return False
