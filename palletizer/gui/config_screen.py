"""Tela de configuração: escolher/editar/salvar paletizações."""

from __future__ import annotations

from PyQt6 import QtWidgets

from ..config.models import PalletizationConfig, PatternType
from ..config.store import ConfigStore
from ..setup.calibration import ensure_default_points


class ConfigScreen(QtWidgets.QWidget):
    def __init__(self, store: ConfigStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.config: PalletizationConfig | None = None

        layout = QtWidgets.QFormLayout(self)

        self.name_combo = QtWidgets.QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.addItems(self.store.list_names())
        layout.addRow("Paletização", self.name_combo)

        self.pattern_combo = QtWidgets.QComboBox()
        self.pattern_combo.addItems([p.value for p in PatternType])
        layout.addRow("Formato", self.pattern_combo)

        self.nx = self._spin(1, 50, 3)
        self.ny = self._spin(1, 50, 3)
        self.layers = self._spin(1, 20, 2)
        layout.addRow("Caixas em X", self.nx)
        layout.addRow("Caixas em Y", self.ny)
        layout.addRow("Camadas", self.layers)

        self.box_l = self._dspin(1, 2000, 100)
        self.box_w = self._dspin(1, 2000, 100)
        self.box_h = self._dspin(1, 2000, 100)
        layout.addRow("Caixa L (mm)", self.box_l)
        layout.addRow("Caixa W (mm)", self.box_w)
        layout.addRow("Caixa H (mm)", self.box_h)

        self.ip = QtWidgets.QLineEdit("192.168.0.10")
        layout.addRow("IP do robô", self.ip)

        btns = QtWidgets.QHBoxLayout()
        self.load_btn = QtWidgets.QPushButton("Carregar")
        self.save_btn = QtWidgets.QPushButton("Salvar")
        self.load_btn.clicked.connect(self.on_load)
        self.save_btn.clicked.connect(self.on_save)
        btns.addWidget(self.load_btn)
        btns.addWidget(self.save_btn)
        layout.addRow(btns)

    def _spin(self, lo, hi, val):
        s = QtWidgets.QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _dspin(self, lo, hi, val):
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def current_config(self) -> PalletizationConfig:
        """Constrói a config a partir dos campos da tela."""
        name = self.name_combo.currentText().strip() or "nova_paletizacao"
        cfg = self.config or PalletizationConfig(name=name)
        cfg.name = name
        cfg.pattern = PatternType(self.pattern_combo.currentText())
        cfg.pallet.nx = self.nx.value()
        cfg.pallet.ny = self.ny.value()
        cfg.pallet.layers = self.layers.value()
        cfg.box.length = self.box_l.value()
        cfg.box.width = self.box_w.value()
        cfg.box.height = self.box_h.value()
        cfg.robot.ip = self.ip.text().strip()
        ensure_default_points(cfg)
        self.config = cfg
        return cfg

    def on_load(self) -> None:
        name = self.name_combo.currentText().strip()
        try:
            cfg = self.store.load(name)
        except FileNotFoundError:
            QtWidgets.QMessageBox.warning(self, "Config", f"'{name}' não encontrada.")
            return
        self.config = cfg
        self.pattern_combo.setCurrentText(cfg.pattern.value)
        self.nx.setValue(cfg.pallet.nx)
        self.ny.setValue(cfg.pallet.ny)
        self.layers.setValue(cfg.pallet.layers)
        self.box_l.setValue(cfg.box.length)
        self.box_w.setValue(cfg.box.width)
        self.box_h.setValue(cfg.box.height)
        self.ip.setText(cfg.robot.ip)

    def on_save(self) -> None:
        cfg = self.current_config()
        self.store.save(cfg)
        if self.name_combo.findText(cfg.name) < 0:
            self.name_combo.addItem(cfg.name)
        QtWidgets.QMessageBox.information(self, "Config", f"'{cfg.name}' salva.")
