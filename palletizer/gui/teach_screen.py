"""Tela de ensino de pontos por freedrive."""

from __future__ import annotations

from PyQt6 import QtWidgets

from ..comm.ur_socket import URConnection
from ..setup.calibration import DEFAULT_POINT_NAMES
from ..setup.teach import TeachSession


class TeachScreen(QtWidgets.QWidget):
    def __init__(self, get_config, parent=None) -> None:
        super().__init__(parent)
        self._get_config = get_config
        self._session: TeachSession | None = None
        self._conn: URConnection | None = None

        layout = QtWidgets.QVBoxLayout(self)
        self.freedrive_btn = QtWidgets.QPushButton("Ligar freedrive")
        self.freedrive_btn.setCheckable(True)
        self.freedrive_btn.clicked.connect(self.on_freedrive)
        layout.addWidget(self.freedrive_btn)

        self.point_combo = QtWidgets.QComboBox()
        self.point_combo.addItems(DEFAULT_POINT_NAMES)
        layout.addWidget(self.point_combo)

        self.capture_btn = QtWidgets.QPushButton("Capturar pose atual")
        self.capture_btn.clicked.connect(self.on_capture)
        layout.addWidget(self.capture_btn)

        self.status = QtWidgets.QPlainTextEdit()
        self.status.setReadOnly(True)
        layout.addWidget(self.status)

    def _ensure_session(self) -> TeachSession:
        cfg = self._get_config()
        if self._conn is None:
            self._conn = URConnection(cfg.robot.ip, cfg.robot.port).connect()
        if self._session is None:
            self._session = TeachSession(cfg, self._conn)
        return self._session

    def on_freedrive(self, checked: bool) -> None:
        try:
            session = self._ensure_session()
            if checked:
                session.begin()
                self.freedrive_btn.setText("Desligar freedrive")
                self.status.appendPlainText("Freedrive LIGADO — posicione o robô à mão.")
            else:
                session.end()
                self.freedrive_btn.setText("Ligar freedrive")
                self.status.appendPlainText("Freedrive DESLIGADO.")
        except Exception as exc:  # comunicação pode falhar sem robô
            self.freedrive_btn.setChecked(False)
            self.status.appendPlainText(f"Erro: {exc}")

    def on_capture(self) -> None:
        try:
            session = self._ensure_session()
            name = self.point_combo.currentText()
            point = session.capture(name)
            self.status.appendPlainText(f"'{name}' = {['%.3f' % v for v in point.pose]}")
        except Exception as exc:
            self.status.appendPlainText(f"Erro: {exc}")
