"""
ui/player_bar.py — Player bar for Mope (Qt port).

Contains:
  - Previous / Play-Pause / Next buttons
  - Shuffle toggle
  - Repeat toggle (cycles: off -> repeat-all -> repeat-one)
  - Track title + artist label
  - Seek slider + position label
  - Volume slider

Icons are Material Symbols / Material Icons SVGs bundled in ../icons/,
loaded via QIcon rather than QStyle.standardIcon() (which just draws
generic OS-default glyphs) or emoji text (which render at an inconsistent
size/weight compared to real icons).
"""

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QToolButton, QLabel, QSlider,
    QFrame, QSizePolicy
)

from ui.widgets import ElidedLabel
from ui.theme import BORDER, BG_HOVER, ORANGE, ORANGE_HOVER, TEXT_DIM

# Repeat mode constants (same values/semantics as the GTK version)
REPEAT_NONE = 0
REPEAT_ALL  = 1
REPEAT_ONE  = 2

_ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"
_ICON_SIZE = QSize(22, 22)
_BTN_SIZE  = QSize(32, 32)

# Every transport/mode button gets the same visible border at all times,
# so the bar reads as one consistent toolbar.
_BASE_STYLE = (
    f"QToolButton {{ background-color: transparent; "
    f"border: 1px solid {BORDER}; border-radius: 5px; }}"
    f"QToolButton:hover {{ background-color: {BG_HOVER}; border-color: {ORANGE}; }}"
)
_ACTIVE_STYLE = (
    f"QToolButton {{ background-color: rgba(255, 152, 0, 45); "
    f"border: 1px solid {ORANGE}; border-radius: 5px; }}"
    f"QToolButton:hover {{ background-color: rgba(255, 152, 0, 70); "
    f"border-color: {ORANGE_HOVER}; }}"
)


def _icon(name: str) -> QIcon:
    return QIcon(str(_ICONS_DIR / f"{name}.svg"))


class PlayerBar(QWidget):
    """
    Horizontal bar:
      [prev] [play] [next]  [shuffle] [repeat]   Title / Artist   0:00/3:45  ══●══  vol──●──
    """

    def __init__(self):
        super().__init__()

        # Callbacks wired by main window (same names as GTK version)
        self.on_play_pause = None
        self.on_previous   = None
        self.on_next       = None
        self.on_seek       = None    # called with (seconds: float)
        self.on_volume     = None    # called with (0.0-1.0)

        self._duration = 0.0
        self._seeking  = False

        # Playback mode state (read by main_window to decide what to do at track end)
        self.shuffle     = False
        self.repeat_mode = REPEAT_NONE

        self._build()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self._btn_prev = self._make_button(
            _icon("skip_previous"), self._on_prev_clicked, "Previous"
        )
        self._btn_play = self._make_button(
            _icon("play"), self._on_play_clicked, "Play / Pause"
        )
        self._btn_next = self._make_button(
            _icon("skip_next"), self._on_next_clicked, "Next"
        )
        layout.addWidget(self._btn_prev)
        layout.addWidget(self._btn_play)
        layout.addWidget(self._btn_next)

        # --- Shuffle button ---
        self._btn_shuffle = self._make_button(
            _icon("shuffle"), None, "Shuffle"
        )
        self._btn_shuffle.setCheckable(True)
        self._btn_shuffle.toggled.connect(self._on_shuffle_toggled)
        layout.addWidget(self._btn_shuffle)

        # --- Repeat button (cycles through modes on each click) ---
        self._btn_repeat = self._make_button(
            _icon("repeat"), self._on_repeat_clicked, "Repeat: Off"
        )
        layout.addWidget(self._btn_repeat)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

        # --- Track info ---
        info_box = QVBoxLayout()
        info_box.setSpacing(0)

        self._lbl_title = ElidedLabel("Not playing")
        f = self._lbl_title.font()
        f.setBold(True)
        self._lbl_title.setFont(f)

        self._lbl_artist = ElidedLabel("")
        self._lbl_artist.setStyleSheet(f"color: {TEXT_DIM};")

        info_box.addWidget(self._lbl_title)
        info_box.addWidget(self._lbl_artist)

        info_widget = QWidget()
        info_widget.setLayout(info_box)
        info_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(info_widget, 1)

        # --- Position label ---
        self._lbl_position = QLabel("0:00 / 0:00")
        self._lbl_position.setStyleSheet("font-family: monospace;")
        layout.addWidget(self._lbl_position)

        # --- Seek slider ---
        self._seek_bar = QSlider(Qt.Orientation.Horizontal)
        self._seek_bar.setRange(0, 100)
        self._seek_bar.setFixedWidth(200)
        self._seek_bar.sliderPressed.connect(self._on_seek_press)
        self._seek_bar.sliderReleased.connect(self._on_seek_release)
        self._seek_bar.valueChanged.connect(self._on_seek_changed)
        layout.addWidget(self._seek_bar)

        # --- Volume ---
        vol_lbl = QLabel()
        vol_lbl.setPixmap(_icon("volume").pixmap(_ICON_SIZE))
        layout.addWidget(vol_lbl)

        self._vol_bar = QSlider(Qt.Orientation.Horizontal)
        self._vol_bar.setRange(0, 100)
        self._vol_bar.setValue(100)
        self._vol_bar.setFixedWidth(90)
        self._vol_bar.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self._vol_bar)

    def _make_button(self, icon, handler, tooltip):
        btn = QToolButton()
        btn.setIcon(icon)
        btn.setIconSize(_ICON_SIZE)
        btn.setFixedSize(_BTN_SIZE)
        btn.setToolTip(tooltip)
        btn.setStyleSheet(_BASE_STYLE)
        if handler:
            btn.clicked.connect(handler)
        return btn

    # ------------------------------------------------------------------
    # Public API (same names/shapes as the GTK version)
    # ------------------------------------------------------------------

    def set_track(self, title: str, artist: str, duration: float):
        self._lbl_title.setText(title or "")
        self._lbl_artist.setText(artist or "")
        self._duration = duration or 0.0
        self._seek_bar.blockSignals(True)
        self._seek_bar.setRange(0, max(int(self._duration), 1))
        self._seek_bar.setValue(0)
        self._seek_bar.blockSignals(False)
        self._update_position_label(0.0)

    def update_position(self, pos: float, duration: float):
        self._duration = duration
        self._seek_bar.blockSignals(True)
        self._seek_bar.setRange(0, max(int(duration), 1))
        if not self._seeking:
            self._seek_bar.setValue(int(pos))
        self._seek_bar.blockSignals(False)
        self._update_position_label(pos)

    def set_playing(self, playing: bool):
        self._btn_play.setIcon(_icon("pause") if playing else _icon("play"))

    def _update_position_label(self, pos: float):
        self._lbl_position.setText(_fmt(pos) + " / " + _fmt(self._duration))

    # ------------------------------------------------------------------
    # Transport handlers
    # ------------------------------------------------------------------

    def _on_play_clicked(self):
        if self.on_play_pause:
            self.on_play_pause()

    def _on_prev_clicked(self):
        if self.on_previous:
            self.on_previous()

    def _on_next_clicked(self):
        if self.on_next:
            self.on_next()

    # ------------------------------------------------------------------
    # Shuffle handler
    # ------------------------------------------------------------------

    def _on_shuffle_toggled(self, checked: bool):
        self.shuffle = checked
        self._btn_shuffle.setStyleSheet(_ACTIVE_STYLE if checked else _BASE_STYLE)

    # ------------------------------------------------------------------
    # Repeat handler — cycles: Off -> Repeat All -> Repeat One -> Off
    # ------------------------------------------------------------------

    def _on_repeat_clicked(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3

        if self.repeat_mode == REPEAT_NONE:
            self._btn_repeat.setIcon(_icon("repeat"))
            self._btn_repeat.setToolTip("Repeat: Off")
            self._btn_repeat.setStyleSheet(_BASE_STYLE)
        elif self.repeat_mode == REPEAT_ALL:
            self._btn_repeat.setIcon(_icon("repeat"))
            self._btn_repeat.setToolTip("Repeat: All")
            self._btn_repeat.setStyleSheet(_ACTIVE_STYLE)
        elif self.repeat_mode == REPEAT_ONE:
            self._btn_repeat.setIcon(_icon("repeat_one"))
            self._btn_repeat.setToolTip("Repeat: One")
            self._btn_repeat.setStyleSheet(_ACTIVE_STYLE)

    # ------------------------------------------------------------------
    # Seek handlers
    # ------------------------------------------------------------------

    def _on_seek_press(self):
        self._seeking = True

    def _on_seek_release(self):
        self._seeking = False
        if self.on_seek:
            self.on_seek(float(self._seek_bar.value()))

    def _on_seek_changed(self, value):
        if self._seeking and self.on_seek:
            self.on_seek(float(value))
        self._update_position_label(float(value))

    # ------------------------------------------------------------------
    # Volume handler
    # ------------------------------------------------------------------

    def _on_volume_changed(self, value):
        if self.on_volume:
            self.on_volume(value / 100.0)


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------

def _fmt(seconds: float) -> str:
    s = int(seconds)
    return str(s // 60) + ":" + str(s % 60).zfill(2)
