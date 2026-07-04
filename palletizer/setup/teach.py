"""Captura de pontos por freedrive.

Fluxo por ponto:
1. Habilita o freedrive (operador move o robô à mão).
2. Ao confirmar, lê a pose TCP atual (offset realtime 252:300) e grava no config.
3. Encerra o freedrive — SEMPRE antes de qualquer movimento automático (segurança).

A dependência de comunicação é injetada (:class:`~palletizer.comm.ur_socket.URConnection`
ou um duplo de teste), então esta lógica é testável sem robô.
"""

from __future__ import annotations

from typing import List, Protocol

from ..config.models import PalletizationConfig, TaughtPoint


class PoseSource(Protocol):
    """Interface mínima de comunicação usada pelo teach (facilita mock nos testes)."""

    def start_freedrive(self) -> None: ...
    def end_freedrive(self) -> None: ...
    def read_tcp_pose(self) -> List[float]: ...


class TeachSession:
    """Sessão de ensino de pontos para uma configuração."""

    def __init__(self, config: PalletizationConfig, comm: PoseSource) -> None:
        self.config = config
        self.comm = comm
        self._freedrive_active = False

    def begin(self) -> None:
        """Libera as juntas para posicionamento manual."""
        self.comm.start_freedrive()
        self._freedrive_active = True

    def capture(self, point_name: str) -> TaughtPoint:
        """Lê a pose atual e grava como ``point_name`` no config."""
        pose = self.comm.read_tcp_pose()
        point = TaughtPoint(name=point_name, pose=list(pose))
        self.config.points[point_name] = point
        return point

    def end(self) -> None:
        """Encerra o freedrive. Idempotente e seguro para chamar sempre antes de mover."""
        self.comm.end_freedrive()
        self._freedrive_active = False

    @property
    def freedrive_active(self) -> bool:
        return self._freedrive_active

    def __enter__(self) -> "TeachSession":
        self.begin()
        return self

    def __exit__(self, *exc) -> None:
        # Garante que o robô nunca fique em freedrive ao sair do bloco.
        self.end()
