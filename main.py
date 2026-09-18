#!/usr/bin/env python3
"""
Mope — Music Organizer Player Etc. (Windows / Qt port)
Entry point: initialises Qt and launches the main window.
"""

import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ui.main_window import MopeWindow
from ui.theme import STYLESHEET

ICON_PATH = Path(__file__).resolve().parent / "mope.png"


def _fix_windows_taskbar_icon():
    """On Windows, the taskbar groups windows by the launching executable
    (python.exe) rather than by window icon, so without this, Mope would
    show the Python icon in the taskbar instead of its own."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "mope.musicplayer"
            )
        except Exception:
            pass


def main():
    _fix_windows_taskbar_icon()

    app = QApplication(sys.argv)
    app.setApplicationName("Mope")
    app.setDesktopFileName("mope")
    app.setStyleSheet(STYLESHEET)

    if ICON_PATH.exists():
        icon = QIcon(str(ICON_PATH))
        app.setWindowIcon(icon)

    win = MopeWindow()
    if ICON_PATH.exists():
        win.setWindowIcon(icon)
    win.show()

    # By default, Qt's C++ event loop blocks Python from ever getting a
    # chance to notice Ctrl+C. This periodic no-op timer hands control back
    # to the Python interpreter often enough that SIGINT still works.
    _sigint_pump = QTimer()
    _sigint_pump.timeout.connect(lambda: None)
    _sigint_pump.start(200)

    try:
        ret = app.exec()
    except KeyboardInterrupt:
        ret = 0

    # Save window/panel state and last-loaded folder regardless of how we
    # got here (closed via window X, or Ctrl+C in the terminal).
    win.save_state()
    return ret


if __name__ == "__main__":
    sys.exit(main())
