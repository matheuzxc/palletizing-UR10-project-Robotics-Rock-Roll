"""Tela de execução: simular no RoboDK, gerar/salvar/enviar URScript."""

from __future__ import annotations

import time

from PyQt6 import QtWidgets

from ..app.controller import PalletizerController
from ..comm.ur_socket import URConnection


class RunScreen(QtWidgets.QWidget):
    def __init__(self, get_config, parent=None) -> None:
        super().__init__(parent)
        self._get_config = get_config

        layout = QtWidgets.QVBoxLayout(self)
        row = QtWidgets.QHBoxLayout()
        self.sim_btn = QtWidgets.QPushButton("Simular no RoboDK")
        self.gen_btn = QtWidgets.QPushButton("Gerar URScript")
        self.save_btn = QtWidgets.QPushButton("Salvar .script")
        self.send_btn = QtWidgets.QPushButton("Enviar ao robô")
        self.sim_btn.clicked.connect(self.on_sim)
        self.gen_btn.clicked.connect(self.on_generate)
        self.save_btn.clicked.connect(self.on_save)
        self.send_btn.clicked.connect(self.on_send)
        for b in (self.sim_btn, self.gen_btn, self.save_btn, self.send_btn):
            row.addWidget(b)
        layout.addLayout(row)

        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

    def _controller(self) -> PalletizerController:
        return PalletizerController(self._get_config())

    def on_sim(self) -> None:
        try:
            from ..robodk.link import new_robolink  # import tardio: só quando há RoboDK
            from ..robodk.adapter import RoboDKAdapter

            adapter = RoboDKAdapter(new_robolink())
            placed = self._controller().run_simulation(adapter)
            self.output.appendPlainText(f"Simulação: {placed} caixas colocadas.")
        except Exception as exc:
            self.output.appendPlainText(f"Erro na simulação: {exc}")

    def on_generate(self) -> None:
        try:
            script = self._controller().build_urscript()
            self.output.setPlainText(script)
        except Exception as exc:
            self.output.appendPlainText(f"Erro ao gerar: {exc}")

    def on_save(self) -> None:
        try:
            path = self._controller().save_urscript("scripts/palletizer_core.script")
            self.output.appendPlainText(f"Salvo em {path}")
        except Exception as exc:
            self.output.appendPlainText(f"Erro ao salvar: {exc}")

    def on_send(self) -> None:
        cfg = self._get_config()
        confirm = QtWidgets.QMessageBox.question(
            self, "Enviar ao robô",
            f"Enviar URScript para {cfg.robot.ip}:{cfg.robot.port}? O robô vai se mover.",
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            with URConnection(cfg.robot.ip, cfg.robot.port) as conn:
                self._controller().send_to_robot(conn)
                # Espera o controlador ingerir o programa antes de fechar o socket (FIN).
                time.sleep(0.5)
            self.output.appendPlainText("URScript enviado.")
        except Exception as exc:
            self.output.appendPlainText(f"Erro no envio: {exc}")
