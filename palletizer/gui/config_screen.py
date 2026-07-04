"""Tela de configuração: escolher/editar/salvar paletizações (modelo v2).

Estilo PolyScope: posições em **mm**, orientações como **vetor de rotação** em **rad**. A
conversão mm→m acontece na borda (o modelo guarda metros). O pallet é definido por 4 cantos;
``nx``/``ny`` são derivados e exibidos como leitura.
"""

from __future__ import annotations

from PyQt6 import QtWidgets

from ..config.models import PalletizationConfig, PatternType
from ..config.store import ConfigStore
from ..planner.geometry import build_grid
from ..planner.patterns import selectable_patterns
from ..setup.calibration import ensure_default_points

_M = 1000.0  # mm ↔ m


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
        self.pattern_combo.addItems([p.value for p in selectable_patterns()])
        layout.addRow("Formato", self.pattern_combo)

        self.layers = self._spin(1, 20, 2)
        layout.addRow("Camadas", self.layers)

        # --- caixa (mm) ---
        self.box_l = self._dspin(1, 2000, 100)
        self.box_w = self._dspin(1, 2000, 100)
        self.box_h = self._dspin(1, 2000, 100)
        layout.addRow("Caixa L (mm)", self.box_l)
        layout.addRow("Caixa W (mm)", self.box_w)
        layout.addRow("Caixa H (mm)", self.box_h)

        # --- 4 cantos do pallet (mm, chão) ---
        self.corners = []
        defaults = PalletizationConfig(name="_").pallet.corners
        for idx, label in enumerate(["c0 (origem)", "c1 (compr. X)", "c2 (diagonal)", "c3 (larg. Y)"]):
            cx = self._dspin(-5000, 5000, defaults[idx][0] * _M)
            cy = self._dspin(-5000, 5000, defaults[idx][1] * _M)
            cz = self._dspin(-5000, 5000, defaults[idx][2] * _M)
            for w in (cx, cy, cz):
                w.valueChanged.connect(self._update_derived)
            self.corners.append((cx, cy, cz))
            layout.addRow(f"Canto {label} X/Y/Z (mm)", self._triple_row(cx, cy, cz))
        for w in (self.box_l, self.box_w):
            w.valueChanged.connect(self._update_derived)

        self.derived_label = QtWidgets.QLabel("—")
        layout.addRow("Grade derivada (nx × ny)", self.derived_label)

        # --- pose de pick (mm; rotação em rad) ---
        self.pick_x = self._dspin(-5000, 5000, 0)
        self.pick_y = self._dspin(-5000, 5000, 0)
        self.pick_z = self._dspin(-5000, 5000, 0)
        self.pick_rx = self._dspin(-6.2832, 6.2832, 0, decimals=4, step=0.01)
        self.pick_ry = self._dspin(-6.2832, 6.2832, 0, decimals=4, step=0.01)
        self.pick_rz = self._dspin(-6.2832, 6.2832, 0, decimals=4, step=0.01)
        layout.addRow("Pick X/Y/Z (mm)", self._triple_row(self.pick_x, self.pick_y, self.pick_z))
        layout.addRow("Pick Rx/Ry/Rz (rad)", self._triple_row(self.pick_rx, self.pick_ry, self.pick_rz))

        # --- offsets (mm) ---
        self.off_pick_z = self._dspin(0, 2000, 150)
        self.off_pallet_xy = self._dspin(0, 2000, 100)
        self.off_pallet_z = self._dspin(0, 2000, 50)
        layout.addRow("Offset approachPick Z (mm)", self.off_pick_z)
        layout.addRow("Offset approach pallet XY (mm)", self.off_pallet_xy)
        layout.addRow("Offset approach pallet Z (mm)", self.off_pallet_z)

        # --- atuador (ventosas) ---
        self.gripper_do = self._spin(0, 7, 0)
        self.gripper_hold = self._dspin(0, 30, 5, decimals=1, step=0.5)
        layout.addRow("Atuador D (saída digital)", self.gripper_do)
        layout.addRow("Retenção do atuador (s)", self.gripper_hold)

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

        self._update_derived()

    # -- helpers de widget ---------------------------------------------------------
    def _spin(self, lo, hi, val):
        s = QtWidgets.QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _dspin(self, lo, hi, val, decimals=1, step=1.0):
        s = QtWidgets.QDoubleSpinBox()
        s.setDecimals(decimals)
        s.setSingleStep(step)
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    def _triple_row(self, a, b, c):
        w = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        for widget in (a, b, c):
            row.addWidget(widget)
        return w

    def _corners_m(self):
        return [[cx.value() / _M, cy.value() / _M, cz.value() / _M] for (cx, cy, cz) in self.corners]

    def _update_derived(self, *_):
        """Recalcula nx × ny a partir dos 4 cantos + caixa; mostra o motivo se inválido."""
        try:
            cfg = PalletizationConfig(name="_")
            cfg.pallet.corners = self._corners_m()
            cfg.box.length = self.box_l.value()
            cfg.box.width = self.box_w.value()
            cfg.box.height = self.box_h.value()
            grid = build_grid(cfg.pallet, cfg.box)
            self.derived_label.setText(f"{grid.nx} × {grid.ny} = {grid.nx * grid.ny} caixas/camada")
        except ValueError as exc:
            self.derived_label.setText(f"inválido: {exc}")

    # -- construção / carregamento -------------------------------------------------
    def current_config(self) -> PalletizationConfig:
        """Constrói a config a partir dos campos da tela (mm→m na borda)."""
        name = self.name_combo.currentText().strip() or "nova_paletizacao"
        cfg = self.config or PalletizationConfig(name=name)
        cfg.name = name
        cfg.pattern = PatternType(self.pattern_combo.currentText())
        cfg.pallet.layers = self.layers.value()
        cfg.pallet.corners = self._corners_m()
        cfg.box.length = self.box_l.value()
        cfg.box.width = self.box_w.value()
        cfg.box.height = self.box_h.value()
        cfg.motion.approach_pick_offset_z = self.off_pick_z.value() / _M
        cfg.motion.pallet_approach_offset_xy = self.off_pallet_xy.value() / _M
        cfg.motion.pallet_approach_offset_z = self.off_pallet_z.value() / _M
        cfg.motion.gripper_do = self.gripper_do.value()
        cfg.motion.gripper_hold_s = self.gripper_hold.value()
        cfg.robot.ip = self.ip.text().strip()
        ensure_default_points(cfg)
        cfg.points["pick"].pose = [
            self.pick_x.value() / _M, self.pick_y.value() / _M, self.pick_z.value() / _M,
            self.pick_rx.value(), self.pick_ry.value(), self.pick_rz.value(),
        ]
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
        if cfg.pattern in selectable_patterns():
            self.pattern_combo.setCurrentText(cfg.pattern.value)
        self.layers.setValue(cfg.pallet.layers)
        self.box_l.setValue(cfg.box.length)
        self.box_w.setValue(cfg.box.width)
        self.box_h.setValue(cfg.box.height)
        for (cx, cy, cz), corner in zip(self.corners, cfg.pallet.corners):
            cx.setValue(corner[0] * _M)
            cy.setValue(corner[1] * _M)
            cz.setValue(corner[2] * _M)
        self.off_pick_z.setValue(cfg.motion.approach_pick_offset_z * _M)
        self.off_pallet_xy.setValue(cfg.motion.pallet_approach_offset_xy * _M)
        self.off_pallet_z.setValue(cfg.motion.pallet_approach_offset_z * _M)
        self.gripper_do.setValue(cfg.motion.gripper_do)
        self.gripper_hold.setValue(cfg.motion.gripper_hold_s)
        self.ip.setText(cfg.robot.ip)
        pick = cfg.points.get("pick")
        if pick is not None:
            self.pick_x.setValue(pick.pose[0] * _M)
            self.pick_y.setValue(pick.pose[1] * _M)
            self.pick_z.setValue(pick.pose[2] * _M)
            self.pick_rx.setValue(pick.pose[3])
            self.pick_ry.setValue(pick.pose[4])
            self.pick_rz.setValue(pick.pose[5])
        self._update_derived()

    def on_save(self) -> None:
        cfg = self.current_config()
        self.store.save(cfg)
        if self.name_combo.findText(cfg.name) < 0:
            self.name_combo.addItem(cfg.name)
        QtWidgets.QMessageBox.information(self, "Config", f"'{cfg.name}' salva.")
