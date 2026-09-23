"""
ui/playlist_panel.py — Playlist list panel for Mope (Qt port), shown in the
left nav when the user switches to "Playlists" mode.

Shows all saved playlists. Selecting one fires on_playlist_selected(playlist).
Right-clicking gives Rename / Delete / Export options.
Toolbar has New / Import buttons.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QListWidget,
    QListWidgetItem, QMenu, QInputDialog, QMessageBox, QFileDialog
)

import playlist_manager as pm
from ui.theme import BORDER, BG_HOVER, ORANGE

_ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"
_ICON_SIZE = QSize(20, 20)
_BTN_SIZE  = QSize(30, 30)
_BTN_STYLE = (
    f"QToolButton {{ background-color: transparent; "
    f"border: 1px solid {BORDER}; border-radius: 5px; }}"
    f"QToolButton:hover {{ background-color: {BG_HOVER}; border-color: {ORANGE}; }}"
)


def _icon(name: str) -> QIcon:
    return QIcon(str(_ICONS_DIR / f"{name}.svg"))


class PlaylistPanel(QWidget):
    """Vertical panel: toolbar + playlist list."""

    def __init__(self):
        super().__init__()

        # Callbacks wired by main window (same names as GTK version)
        self.on_playlist_selected = None   # function(Playlist)
        self.on_playlist_changed  = None   # function() — list was modified

        self._playlists = []   # current list of Playlist objects
        self._suppress_selection = False

        self._build()
        self.refresh()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        bar = QHBoxLayout()
        label = QLabel("Playlists")
        f = label.font()
        f.setBold(True)
        label.setFont(f)

        import_btn = QToolButton()
        import_btn.setIcon(_icon("download"))
        import_btn.setIconSize(_ICON_SIZE)
        import_btn.setFixedSize(_BTN_SIZE)
        import_btn.setToolTip("Import .m3u / .m3u8")
        import_btn.setStyleSheet(_BTN_STYLE)
        import_btn.clicked.connect(self._on_import_clicked)

        new_btn = QToolButton()
        new_btn.setIcon(_icon("add"))
        new_btn.setIconSize(_ICON_SIZE)
        new_btn.setFixedSize(_BTN_SIZE)
        new_btn.setToolTip("New playlist")
        new_btn.setStyleSheet(_BTN_STYLE)
        new_btn.clicked.connect(self._on_new_clicked)

        bar.addWidget(label, 1)
        bar.addWidget(import_btn)
        bar.addWidget(new_btn)
        layout.addLayout(bar)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selection_changed)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_right_click)
        layout.addWidget(self._list, 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self):
        """Reload playlists from disk and repopulate the list, preserving
        the current selection (by playlist path) if it still exists —
        without this, adding/removing a track while viewing a playlist
        would visually deselect it in the sidebar on every change."""
        previously_selected_path = None
        row = self._list.currentRow()
        if 0 <= row < len(self._playlists):
            previously_selected_path = self._playlists[row].path

        self._playlists = pm.list_playlists()
        self._suppress_selection = True
        self._list.clear()
        restore_row = -1
        for i, pl in enumerate(self._playlists):
            item = QListWidgetItem("🎵  " + pl.name)
            self._list.addItem(item)
            if previously_selected_path is not None and pl.path == previously_selected_path:
                restore_row = i

        if restore_row >= 0:
            self._list.setCurrentRow(restore_row)
        else:
            self._list.clearSelection()
            self._list.setCurrentRow(-1)
        self._suppress_selection = False

    def get_playlist_names(self):
        """Return list of (name, Playlist) tuples for use in submenus."""
        return [(pl.name, pl) for pl in self._playlists]

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_selection_changed(self, row: int):
        if self._suppress_selection:
            return
        if row < 0 or row >= len(self._playlists):
            return
        pl = self._playlists[row]
        if self.on_playlist_selected:
            self.on_playlist_selected(pl)

    # ------------------------------------------------------------------
    # Right-click context menu
    # ------------------------------------------------------------------

    def _on_right_click(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        row = self._list.row(item)
        pl = self._playlists[row]

        menu = QMenu(self)
        menu.addAction("✏️  Rename", lambda: self._rename(pl))
        menu.addAction("↑  Export",  lambda: self._export(pl))
        menu.addAction("🗑  Delete", lambda: self._delete(pl))
        menu.exec(self._list.mapToGlobal(pos))

    # ------------------------------------------------------------------
    # New / Import / Rename / Export / Delete
    # ------------------------------------------------------------------

    def _on_new_clicked(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Name:")
        if ok and name.strip():
            pm.create_playlist(name.strip())
            self.refresh()
            if self.on_playlist_changed:
                self.on_playlist_changed()

    def _rename(self, pl):
        name, ok = QInputDialog.getText(self, "Rename Playlist", "Name:", text=pl.name)
        if ok and name.strip():
            pm.rename_playlist(pl, name.strip())
            self.refresh()
            if self.on_playlist_changed:
                self.on_playlist_changed()

    def _delete(self, pl):
        reply = QMessageBox.question(
            self, "Confirm Delete", f"Delete playlist: {pl.name}?",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Ok:
            pm.delete_playlist(pl)
            self.refresh()
            if self.on_playlist_changed:
                self.on_playlist_changed()

    def _export(self, pl):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Playlist", f"{pl.name}.m3u8",
            "Playlist files (*.m3u8 *.m3u)"
        )
        if path:
            pm.export_playlist(pl, path)

    def _on_import_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Playlist", "", "Playlist files (*.m3u8 *.m3u)"
        )
        if path:
            pl = pm.import_playlist(path)
            if pl:
                self.refresh()
                if self.on_playlist_changed:
                    self.on_playlist_changed()
