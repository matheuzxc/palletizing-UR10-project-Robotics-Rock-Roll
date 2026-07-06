"""Leitura de estado do robô pela interface realtime (porta 30003).

Correção sobre o protótipo original de laboratório: o offset ``252:300`` que ele usava é o campo **``q actual``**
(posições de junta em rad), NÃO a pose TCP. Emitir esses valores como ``p[x,y,z,rx,ry,rz]``
gera poses inalcançáveis (``movej is unable to find an inverse kinematics solution``). A pose
TCP cartesiana real ("Tool vector actual") está no offset ``444:492`` do pacote realtime.

Layout do pacote realtime (bytes a partir do início, incluindo o header de 4 bytes):
``0`` size · ``4`` time · ``12`` q target · ``60`` qd target · ``108`` qdd target ·
``156`` I target · ``204`` M target · ``252`` **q actual** · ``300`` qd actual ·
``348`` I actual · ``396`` I control · ``444`` **Tool vector actual (pose TCP)** ·
``492`` TCP speed actual · ...

Também corrige o bug B1 do protótipo original (que dava ``recv`` antes de sincronizar o pacote): lemos
primeiro o inteiro de 4 bytes com o tamanho total da mensagem e então o corpo, antes de fatiar.
"""

from __future__ import annotations

import socket
import struct
from typing import List, Tuple

# Offset da pose TCP cartesiana atual [x, y, z, rx, ry, rz] ("Tool vector actual").
# ATENÇÃO: 252:300 é q_actual (juntas), não a pose — ver docstring do módulo.
RT_TCP_POSE_SLICE: Tuple[int, int] = (444, 492)

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
