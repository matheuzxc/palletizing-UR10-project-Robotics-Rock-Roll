"""Smoke test da GUI — pulado se PyQt6 não estiver instalado."""

import os

import pytest

pytest.importorskip("PyQt6", reason="PyQt6 não instalado")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from PyQt6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def test_main_window_builds(qapp, tmp_path):
    from palletizer.gui.main_window import MainWindow

    win = MainWindow(str(tmp_path))
    # as três telas existem e a config pode ser materializada
    cfg = win._current_config()
    assert cfg.name
    assert win.centralWidget().count() == 3
