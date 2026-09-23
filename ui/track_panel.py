"""
ui/track_panel.py — Centre panel: track list for the selected folder (Qt port).

Shows all audio files in the currently selected folder as a sortable table.
Clicking a column header sorts ascending; clicking again sorts descending.
Double-clicking a track fires self.on_track_activated(filepath).

The header is a clickable breadcrumb trail (e.g. Music › Bad Religion ›
Recipe for Hate) rather than a plain label — clicking any segment jumps
back up to that folder.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView, QFrame
)

from ui.widgets import NumericTableWidgetItem
from ui.breadcrumb_bar import BreadcrumbBar

COL_NUM      = 0
COL_TITLE    = 1
COL_ARTIST   = 2
COL_DURATION = 3

# Filepath is stashed as item data rather than a visible column
FILEPATH_ROLE = Qt.ItemDataRole.UserRole


class TrackPanel(QWidget):
    """
    Vertical panel containing:
      - A clickable breadcrumb trail showing the current folder path
      - A scrollable, sortable table of tracks
    """

    def __init__(self):
        super().__init__()

        # Callbacks (same names as GTK version, plus breadcrumb navigation)
        self.on_track_activated   = None   # function(filepath: str)
        self.on_track_right_click = None   # function(filepath, global_x, global_y)
        self.on_breadcrumb_clicked = None  # function(path: str)

        self._build()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._breadcrumb = BreadcrumbBar()
        self._breadcrumb.on_segment_clicked = self._on_breadcrumb_segment_clicked
        self._breadcrumb.set_plain_text("No folder selected")
        layout.addWidget(self._breadcrumb)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["#", "Title", "Artist", "Duration"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(COL_NUM, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_ARTIST, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_DURATION, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_TITLE, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(COL_NUM, 40)
        self._table.setColumnWidth(COL_ARTIST, 160)
        self._table.setColumnWidth(COL_DURATION, 70)

        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self._table.customContextMenuRequested.connect(self._on_right_click)

        layout.addWidget(self._table, 1)

    # ------------------------------------------------------------------
    # Loading tracks
    # ------------------------------------------------------------------

    def load_folder(self, root: str, folder_path: str, tracks: list):
        """Populate the table with tracks from a real filesystem folder,
        showing a clickable breadcrumb trail from root down to folder_path."""
        self._breadcrumb.set_path(root, folder_path)
        self._populate_table(tracks)

    def load_playlist(self, name: str, tracks: list):
        """Populate the table with a playlist's tracks. Playlists aren't
        real folder paths, so the header is plain text with no clickable
        breadcrumb segments."""
        self._breadcrumb.set_plain_text(name)
        self._populate_table(tracks)

    def _populate_table(self, tracks: list):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        self._table.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            num      = track["tracknumber"] or 0
            title    = track["title"]  or Path(track["filepath"]).stem
            artist   = track["artist"] or ""
            dur_raw  = float(track["duration"] or 0.0)
            duration = _format_duration(dur_raw)
            filepath = track["filepath"]

            num_item = NumericTableWidgetItem(str(num) if num else "", num)
            title_item  = QTableWidgetItem(title)
            artist_item = QTableWidgetItem(artist)
            dur_item    = NumericTableWidgetItem(duration, dur_raw)

            # Filepath is stashed on the title item (any column would do)
            title_item.setData(FILEPATH_ROLE, filepath)

            self._table.setItem(row, COL_NUM, num_item)
            self._table.setItem(row, COL_TITLE, title_item)
            self._table.setItem(row, COL_ARTIST, artist_item)
            self._table.setItem(row, COL_DURATION, dur_item)

        self._table.setSortingEnabled(True)
        self._table.sortItems(COL_NUM, Qt.SortOrder.AscendingOrder)

    def clear(self):
        self._table.setRowCount(0)
        self._breadcrumb.set_plain_text("No folder selected")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_breadcrumb_segment_clicked(self, path: str):
        if self.on_breadcrumb_clicked:
            self.on_breadcrumb_clicked(path)

    def _filepath_at_row(self, row: int):
        item = self._table.item(row, COL_TITLE)
        return item.data(FILEPATH_ROLE) if item else None

    def _on_cell_double_clicked(self, row, column):
        filepath = self._filepath_at_row(row)
        if filepath and self.on_track_activated:
            self.on_track_activated(filepath)

    def _on_right_click(self, pos):
        item = self._table.itemAt(pos)
        if not item:
            return
        filepath = self._filepath_at_row(item.row())
        if filepath and self.on_track_right_click:
            global_pos = self._table.viewport().mapToGlobal(pos)
            self.on_track_right_click(filepath, global_pos.x(), global_pos.y())

    def get_all_filepaths(self) -> list:
        """Return filepaths in current (visual/sorted) row order."""
        paths = []
        for row in range(self._table.rowCount()):
            fp = self._filepath_at_row(row)
            if fp:
                paths.append(fp)
        return paths

    def highlight_track(self, filepath: str):
        """Scroll to and select the row matching filepath."""
        for row in range(self._table.rowCount()):
            if self._filepath_at_row(row) == filepath:
                self._table.selectRow(row)
                self._table.scrollToItem(self._table.item(row, COL_TITLE))
                return


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _format_duration(seconds) -> str:
    if not seconds:
        return ""
    try:
        s = int(float(seconds))
        return str(s // 60) + ":" + str(s % 60).zfill(2)
    except (ValueError, TypeError):
        return ""
