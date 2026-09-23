"""
ui/folder_panel.py — Left panel: browsable folder tree for Mope (Qt port).

Shows the filesystem rooted at the user's chosen music folder.
Selecting a folder fires self.on_folder_selected(path).

Uses QFileSystemModel, which lazy-loads directory contents from disk
automatically — no manual placeholder-row tree-building needed here,
unlike the GTK version.
"""

import os
from pathlib import Path

from PySide6.QtCore import QDir, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QFileSystemModel, QFileDialog, QMenu, QMessageBox
)

_ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"


class _NoEmptyExpandModel(QFileSystemModel):
    """QFileSystemModel always shows an expand arrow on every directory,
    even ones with zero subdirectories (album folders, say, containing
    only audio/image files) — it doesn't check until you actually try to
    expand it. This override does a quick real check first, so leaf
    folders correctly show no arrow at all."""

    def hasChildren(self, parent):
        if not parent.isValid():
            return super().hasChildren(parent)
        path = self.filePath(parent)
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                        return True
            return False
        except OSError:
            return super().hasChildren(parent)


class FolderPanel(QWidget):
    """
    Vertical panel containing:
      - A toolbar with an "Add Folder" button
      - A tree view showing the folder hierarchy, rooted at the chosen folder
    """

    def __init__(self):
        super().__init__()

        # Callback: set this to a function(path: str) in the parent
        self.on_folder_selected = None
        # Callback: set this to a function(path: str) in the parent —
        # called after the user confirms removing a folder from the
        # library (purging its indexed tracks; does not touch actual files)
        self.on_folder_removed = None

        self._root_path = None
        self._model = _NoEmptyExpandModel()
        self._model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        self._model.setRootPath("")   # allow browsing any root we're given

        self._build()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        bar = QHBoxLayout()
        label = QLabel("Library")
        f = label.font()
        f.setBold(True)
        label.setFont(f)

        add_btn = QPushButton(" Add Folder")
        add_btn.setIcon(QIcon(str(_ICONS_DIR / "add.svg")))
        add_btn.setIconSize(QSize(18, 18))
        add_btn.clicked.connect(self._on_add_folder_clicked)

        bar.addWidget(label, 1)
        bar.addWidget(add_btn)
        layout.addLayout(bar)

        self._tree = QTreeView()
        self._tree.setModel(self._model)
        self._tree.setHeaderHidden(True)
        # Only show the name column — hide size/type/date-modified
        for col in (1, 2, 3):
            self._tree.setColumnHidden(col, True)
        self._tree.selectionModel_ready = False
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_right_click)
        layout.addWidget(self._tree, 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_root(self, path: str):
        """Set (or replace) the root music folder and populate the tree."""
        self._root_path = path
        root_index = self._model.setRootPath(path)
        self._tree.setRootIndex(root_index)

        # Connect selection handling once the model/selection model exist
        if not self._tree.selectionModel_ready:
            self._tree.selectionModel().currentChanged.connect(self._on_current_changed)
            self._tree.selectionModel_ready = True

    def get_root(self) -> str:
        return self._root_path

    # ------------------------------------------------------------------
    # Add folder dialog
    # ------------------------------------------------------------------

    def _on_add_folder_clicked(self):
        path = QFileDialog.getExistingDirectory(
            self, "Choose Music Folder", self._root_path or ""
        )
        if path:
            self.set_root(path)
            if self.on_folder_selected:
                self.on_folder_selected(path)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_current_changed(self, current, previous):
        if not current.isValid():
            return
        path = self._model.filePath(current)
        if path and self.on_folder_selected:
            self.on_folder_selected(path)

    # ------------------------------------------------------------------
    # Right-click: remove from library
    # ------------------------------------------------------------------

    def _on_right_click(self, pos):
        index = self._tree.indexAt(pos)
        if not index.isValid():
            return
        path = self._model.filePath(index)
        if not path:
            return

        menu = QMenu(self)
        menu.addAction(
            "Remove from Library",
            lambda: self._confirm_remove_folder(path)
        )
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _confirm_remove_folder(self, path: str):
        name = Path(path).name or path
        reply = QMessageBox.question(
            self, "Remove from Library",
            f"Remove \"{name}\" from your library?\n\n"
            "This only removes it from Mope's index (so it won't need a "
            "full rescan to notice it's gone) — it does NOT delete any "
            "actual files from disk.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Ok and self.on_folder_removed:
            self.on_folder_removed(path)
