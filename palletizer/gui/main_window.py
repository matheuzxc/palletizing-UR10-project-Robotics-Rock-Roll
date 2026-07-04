"""Janela principal: monta as três telas em abas."""

from __future__ import annotations

import sys

from PyQt6 import QtWidgets

from ..config.store import ConfigStore
from .config_screen import ConfigScreen
from .run_screen import RunScreen
from .teach_screen import TeachScreen


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, configs_dir: str = "configs") -> None:
        super().__init__()
        self.setWindowTitle("Paletizador UR10")
        self.store = ConfigStore(configs_dir)

        tabs = QtWidgets.QTabWidget()
        self.config_screen = ConfigScreen(self.store)
        self.teach_screen = TeachScreen(self._current_config)
        self.run_screen = RunScreen(self._current_config)
        tabs.addTab(self.config_screen, "1. Configuração")
        tabs.addTab(self.teach_screen, "2. Ensino (freedrive)")
        tabs.addTab(self.run_screen, "3. Simular / Executar")
        self.setCentralWidget(tabs)

    def _current_config(self):
        return self.config_screen.current_config()


def launch(configs_dir: str = "configs") -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    window = MainWindow(configs_dir)
    window.resize(700, 520)
    window.show()
    return app.exec()
