import struct

import pytest

from palletizer.comm.ur_socket import URConnection
from palletizer.comm.ur_state import parse_tcp_pose, read_realtime_packet


def _packet_with_pose(pose):
    body = bytearray(400)
    struct.pack_into("!dddddd", body, 252 - 4, *pose)  # offset dentro do corpo (após header)
    total = 4 + len(body)
    return struct.pack("!i", total) + bytes(body)


class FakeSocket:
    """Socket falso que entrega bytes pré-carregados e captura envios."""

    def __init__(self, incoming=b""):
        self._buf = bytearray(incoming)
        self.sent = bytearray()

    def recv(self, n):
        chunk = bytes(self._buf[:n])
        del self._buf[:n]
        return chunk

    def sendall(self, data):
        self.sent.extend(data)

    def close(self):
        pass


def test_parse_tcp_pose_reads_offset_252_300():
    pose = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    body = bytearray(400)
    struct.pack_into("!dddddd", body, 252, *pose)
    assert parse_tcp_pose(bytes(body)) == pytest.approx(pose)


def test_read_realtime_packet_then_parse():
    pose = [1.0, -2.0, 3.0, 0.0, 0.5, -0.5]
    sock = FakeSocket(_packet_with_pose(pose))
    packet = read_realtime_packet(sock)
    assert parse_tcp_pose(packet) == pytest.approx(pose)


def test_send_requires_connection():
    conn = URConnection("127.0.0.1")
    with pytest.raises(ConnectionError):
        conn.send("movej(p_home)")


def test_send_appends_newline_and_encodes():
    conn = URConnection("127.0.0.1")
    conn._sock = FakeSocket()
    conn.send("freedrive_mode()")
    assert conn._sock.sent == b"freedrive_mode()\n"


def test_read_tcp_pose_via_connection():
    pose = [0.5, 0.6, 0.7, 0.1, 0.2, 0.3]
    conn = URConnection("127.0.0.1")
    conn._sock = FakeSocket(_packet_with_pose(pose))
    assert conn.read_tcp_pose() == pytest.approx(pose)


def test_short_packet_raises():
    with pytest.raises(ValueError):
        parse_tcp_pose(b"\x00" * 100)
