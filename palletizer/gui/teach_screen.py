"""Tela de ensino de pontos: entrada manual OU captura por freedrive."""

from __future__ import annotations

from PyQt6 import QtWidgets

from ..comm.ur_socket import URConnection
from ..setup.calibration import DEFAULT_POINT_NAMES
from ..setup.teach import TeachSession, set_point


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
        layout.addWidget(QtWidgets.QLabel("Ponto:"))
        layout.addWidget(self.point_combo)

        # --- entrada MANUAL (principal para URSim) ---
        layout.addWidget(QtWidgets.QLabel("Manual — pose [x, y, z, rx, ry, rz] em m/rad:"))
        manual_row = QtWidgets.QHBoxLayout()
        self.manual_edit = QtWidgets.QLineEdit()
        self.manual_edit.setPlaceholderText("0.438, -0.975, 0.65, 0.881, -2.986, 0.051")
        self.manual_btn = QtWidgets.QPushButton("Definir manualmente")
        self.manual_btn.clicked.connect(self.on_manual)
        manual_row.addWidget(self.manual_edit)
        manual_row.addWidget(self.manual_btn)
        layout.addLayout(manual_row)

        # --- captura por FREEDRIVE (robô real) ---
        self.capture_btn = QtWidgets.QPushButton("Capturar pose atual (freedrive)")
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

    def on_manual(self) -> None:
        cfg = self._get_config()
        name = self.point_combo.currentText()
        raw = self.manual_edit.text().replace(";", ",")
        try:
            values = [float(v) for v in raw.split(",") if v.strip() != ""]
            point = set_point(cfg, name, values)
            self.status.appendPlainText(
                f"[manual] '{name}' = {['%.3f' % v for v in point.pose]}"
            )
        except (ValueError, TypeError) as exc:
            self.status.appendPlainText(f"Erro (manual): {exc}")

    def on_capture(self) -> None:
        try:
            session = self._ensure_session()
            name = self.point_combo.currentText()
            point = session.capture(name)
            self.status.appendPlainText(f"'{name}' = {['%.3f' % v for v in point.pose]}")
        except Exception as exc:
            self.status.appendPlainText(f"Erro: {exc}")
