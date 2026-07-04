"""Conexão TCP com o UR (endurecimento do ``base.py``).

Correções sobre o base.py:
- **B1**: conexão persistente reutilizada (não um socket novo por comando) e leitura de pose
  na ordem certa (sincroniza o pacote realtime antes de fatiar — ver :mod:`ur_state`).
- **B3**: sem código com indentação quebrada; API explícita.
- **Segurança**: um :class:`threading.Lock` serializa os envios — nunca dois URScript
  sobrepostos no mesmo canal (DD3/DD5, risco de concurrency/operability).

Todo comando é terminado com ``\\n`` (o interpretador URScript exige quebra de linha).
"""

from __future__ import annotations

import socket
import threading
from typing import List, Optional

from .ur_state import parse_tcp_pose, read_realtime_packet

DEFAULT_PORT = 30003


class URConnection:
    """Canal serializado para a interface realtime do UR (envio de URScript + estado)."""

    def __init__(self, ip: str, port: int = DEFAULT_PORT, timeout: float = 5.0) -> None:
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()

    # -- ciclo de vida -------------------------------------------------------------
    def connect(self) -> "URConnection":
        if self._sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.ip, self.port))
            self._sock = sock
        return self

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> "URConnection":
        return self.connect()

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    # -- envio ---------------------------------------------------------------------
    def send(self, script: str) -> None:
        """Envia um trecho de URScript. Serializado: bloqueia envios concorrentes."""
        if self._sock is None:
            raise ConnectionError("URConnection não conectada; chame connect() primeiro.")
        payload = script if script.endswith("\n") else script + "\n"
        with self._lock:
            self._sock.sendall(payload.encode("utf-8"))

    # -- estado --------------------------------------------------------------------
    def read_tcp_pose(self) -> List[float]:
        """Lê a pose TCP cartesiana atual do stream realtime (offset 444:492, Tool vector actual)."""
        if self._sock is None:
            raise ConnectionError("URConnection não conectada.")
        with self._lock:
            packet = read_realtime_packet(self._sock)
        return parse_tcp_pose(packet)

    # -- freedrive -----------------------------------------------------------------
    def start_freedrive(self) -> None:
        self.send("freedrive_mode()")

    def end_freedrive(self) -> None:
        # Encerrar o freedrive ANTES de qualquer movimento automático é requisito de segurança.
        self.send("end_freedrive_mode()")
