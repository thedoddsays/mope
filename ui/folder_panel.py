"""
ui/folder_panel.py — Left panel: browsable folder tree for Mope (Qt port).

Shows the filesystem rooted at the user's chosen music folder.
Selecting a folder fires self.on_folder_selected(path).

Uses QFileSystemModel, which lazy-loads directory contents from disk
automatically — no manual placeholder-row tree-building needed here,
unlike the GTK version.
"""

from pathlib import Path

from PySide6.QtCore import QDir, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeView, QFileSystemModel, QFileDialog
)

_ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"


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

        self._root_path = None
        self._model = QFileSystemModel()
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
