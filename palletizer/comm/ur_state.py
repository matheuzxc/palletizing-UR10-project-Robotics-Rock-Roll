"""Leitura de estado do robô pela interface realtime (porta 30003).

O ``base.py`` validou que a pose TCP atual está no offset ``252:300`` (6 doubles big-endian)
do pacote realtime. Aqui isso é feito corretamente, corrigindo o bug B1 do base.py (que dava
``recv`` antes de qualquer sincronização de pacote): lemos primeiro o inteiro de 4 bytes com
o tamanho total da mensagem e então o pacote completo, antes de fatiar.
"""

from __future__ import annotations

import socket
import struct
from typing import List, Tuple

# Offset validado em base.py: 6 doubles com a pose TCP atual [x, y, z, rx, ry, rz].
RT_TCP_POSE_SLICE: Tuple[int, int] = (252, 300)

# A interface realtime começa cada mensagem com um int32 big-endian = tamanho total.
_HEADER = struct.Struct("!i")
_POSE = struct.Struct("!dddddd")


def read_realtime_packet(sock: socket.socket) -> bytes:
    """Lê um pacote realtime completo (header de tamanho + corpo)."""
    header = _recv_exactly(sock, _HEADER.size)
    total = _HEADER.unpack(header)[0]
    body_len = total - _HEADER.size
    if body_len <= 0:
        raise ValueError(f"Tamanho de pacote realtime inválido: {total}")
    body = _recv_exactly(sock, body_len)
    return header + body


def parse_tcp_pose(packet: bytes) -> List[float]:
    """Extrai a pose TCP [x, y, z, rx, ry, rz] do pacote realtime."""
    start, end = RT_TCP_POSE_SLICE
    if len(packet) < end:
        raise ValueError(
            f"Pacote curto demais ({len(packet)} bytes) para o offset {RT_TCP_POSE_SLICE}"
        )
    return list(_POSE.unpack(packet[start:end]))


def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    chunks = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("Conexão fechada durante a leitura do pacote realtime")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
