"""
ui/left_panel.py — Combined left navigation panel for Mope (Qt port).

Contains:
  - A "Library | Playlists" toggle at the top
  - The FolderPanel (shown when Library is selected)
  - The PlaylistPanel (shown when Playlists is selected)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget,
    QButtonGroup, QFrame
)

from ui.folder_panel   import FolderPanel
from ui.playlist_panel import PlaylistPanel


class LeftPanel(QWidget):
    """
    Wraps the Library folder tree and the Playlist panel behind a
    two-button toggle at the top of the left nav.
    """

    def __init__(self):
        super().__init__()

        # Public callbacks — wire these from main_window
        self.on_folder_selected   = None   # function(path: str)
        self.on_playlist_selected = None   # function(Playlist)
        self.on_playlist_changed  = None   # function()

        self._build()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Toggle bar: [ Library ]  [ Playlists ] ---
        toggle_bar = QHBoxLayout()
        toggle_bar.setContentsMargins(6, 6, 6, 6)

        self._btn_library   = QPushButton("Library")
        self._btn_playlists = QPushButton("Playlists")
        for btn in (self._btn_library, self._btn_playlists):
            btn.setCheckable(True)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.addButton(self._btn_library, 0)
        self._group.addButton(self._btn_playlists, 1)
        self._btn_library.setChecked(True)   # Library is default
        self._group.idClicked.connect(self._on_toggle)

        toggle_bar.addWidget(self._btn_library)
        toggle_bar.addWidget(self._btn_playlists)
        layout.addLayout(toggle_bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # --- Stacked pages ---
        self._stack = QStackedWidget()

        self._folder_panel = FolderPanel()
        self._folder_panel.on_folder_selected = self._relay_folder_selected
        self._stack.addWidget(self._folder_panel)   # index 0

        self._playlist_panel = PlaylistPanel()
        self._playlist_panel.on_playlist_selected = self._relay_playlist_selected
        self._playlist_panel.on_playlist_changed  = self._relay_playlist_changed
        self._stack.addWidget(self._playlist_panel)  # index 1

        layout.addWidget(self._stack, 1)

    # ------------------------------------------------------------------
    # Toggle handler
    # ------------------------------------------------------------------

    def _on_toggle(self, button_id: int):
        self._stack.setCurrentIndex(button_id)

    # ------------------------------------------------------------------
    # Relay callbacks to whoever wired us
    # ------------------------------------------------------------------

    def _relay_folder_selected(self, path):
        if self.on_folder_selected:
            self.on_folder_selected(path)

    def _relay_playlist_selected(self, playlist):
        if self.on_playlist_selected:
            self.on_playlist_selected(playlist)

    def _relay_playlist_changed(self):
        if self.on_playlist_changed:
            self.on_playlist_changed()

    # ------------------------------------------------------------------
    # Public API (delegated to inner panels)
    # ------------------------------------------------------------------

    def set_root(self, path: str):
        """Pass a new music root folder down to the FolderPanel."""
        self._folder_panel.set_root(path)

    def refresh_playlists(self):
        """Tell the PlaylistPanel to reload from disk."""
        self._playlist_panel.refresh()

    def get_playlist_panel(self) -> PlaylistPanel:
        return self._playlist_panel
