"""
ui/info_panel.py — Right panel: album art + metadata for Mope (Qt port).

Displays:
  - Album cover art (from embedded tags or Cover Art Archive cache)
  - Album / Artist / Year / Label / Track count
  - A "Fetch Tags" button that triggers MusicBrainz lookup
"""

import threading
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

from ui.qt_utils import invoke_later
from ui.theme import TEXT_DIM


class InfoPanel(QWidget):
    """Right sidebar: art + metadata + tagging trigger."""

    def __init__(self):
        super().__init__()
        self.setFixedWidth(180)

        # Callback: called when user clicks "Fetch Tags" for a folder
        self.on_fetch_tags = None   # function(folder_path, artist, album)

        self._current_folder = None

        self._build()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._art = QLabel()
        self._art.setFixedSize(160, 160)
        self._art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._art.setStyleSheet("background: rgba(128,128,128,40); border-radius: 4px;")
        self._art.setText("\U0001F4BF")
        layout.addWidget(self._art, 0, Qt.AlignmentFlag.AlignHCenter)

        self._lbl_album  = self._make_label("", bold=True)
        self._lbl_artist = self._make_label("")
        self._lbl_year   = self._make_label("", dim=True)
        self._lbl_label  = self._make_label("", dim=True)
        self._lbl_tracks = self._make_label("", dim=True)

        for lbl in [self._lbl_album, self._lbl_artist,
                    self._lbl_year, self._lbl_label, self._lbl_tracks]:
            layout.addWidget(lbl)

        layout.addStretch(1)

        self._fetch_btn = QPushButton("🔍 Fetch Tags")
        self._fetch_btn.setEnabled(False)
        self._fetch_btn.clicked.connect(self._on_fetch_clicked)
        layout.addWidget(self._fetch_btn)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {TEXT_DIM};")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._status_lbl)

    def _make_label(self, text, bold=False, dim=False):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        if bold:
            f = lbl.font()
            f.setBold(True)
            lbl.setFont(f)
        if dim:
            lbl.setStyleSheet(f"color: {TEXT_DIM};")
        return lbl

    # ------------------------------------------------------------------
    # Public API (same names/shapes as GTK version)
    # ------------------------------------------------------------------

    def load_folder(self, folder_path: str, tracks: list):
        """Update the panel from the currently selected folder."""
        self._current_folder = folder_path
        self._status_lbl.setText("")

        if not tracks:
            self._clear()
            return

        first = tracks[0]
        album      = first["album"]       or Path(folder_path).name
        artist     = first["albumartist"] or first["artist"] or ""
        year       = first["year"]        or ""
        num_tracks = len(tracks)

        self._lbl_album.setText(album)
        self._lbl_artist.setText(artist)
        self._lbl_year.setText(year)
        self._lbl_label.setText("")
        self._lbl_tracks.setText(f"{num_tracks} track{'s' if num_tracks != 1 else ''}")

        self._fetch_btn.setEnabled(True)

        self._load_art_from_file(first["filepath"])

    def set_art_bytes(self, data: bytes):
        """Display album art from raw bytes (called after MB fetch).
        Safe to call from any thread."""
        if data:
            invoke_later(lambda: self._show_art_bytes(data))

    def set_status(self, text: str):
        """Safe to call from any thread."""
        invoke_later(lambda: self._status_lbl.setText(text))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear(self):
        self._lbl_album.setText("")
        self._lbl_artist.setText("")
        self._lbl_year.setText("")
        self._lbl_label.setText("")
        self._lbl_tracks.setText("")
        self._clear_art()
        self._fetch_btn.setEnabled(False)

    def _clear_art(self):
        self._art.setPixmap(QPixmap())
        self._art.setText("\U0001F4BF")

    def _load_art_from_file(self, filepath: str):
        """Try to extract embedded cover art from an audio file."""
        def _worker():
            data = _extract_embedded_art(filepath)
            if data:
                invoke_later(lambda: self._show_art_bytes(data))
            else:
                invoke_later(self._clear_art)

        threading.Thread(target=_worker, daemon=True).start()

    def _show_art_bytes(self, data: bytes):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            scaled = pixmap.scaled(
                160, 160, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._art.setText("")
            self._art.setPixmap(scaled)
        else:
            self._clear_art()

    def _on_fetch_clicked(self):
        if not self._current_folder or not self.on_fetch_tags:
            return
        album  = self._lbl_album.text()
        artist = self._lbl_artist.text()
        self._status_lbl.setText("Searching MusicBrainz…")
        self._fetch_btn.setEnabled(False)
        self.on_fetch_tags(self._current_folder, artist, album)


# ------------------------------------------------------------------
# Embedded art extraction (identical logic to the GTK version)
# ------------------------------------------------------------------

def _extract_embedded_art(filepath: str):
    """Return raw bytes of cover art embedded in the audio file, or None."""
    try:
        from mutagen.id3 import ID3
        tags = ID3(filepath)
        for key in tags:
            if key.startswith("APIC"):
                return tags[key].data
    except Exception:
        pass

    try:
        from mutagen.flac import FLAC
        audio = FLAC(filepath)
        if audio.pictures:
            return audio.pictures[0].data
    except Exception:
        pass

    try:
        from mutagen.mp4 import MP4
        audio = MP4(filepath)
        covr = audio.tags.get("covr")
        if covr:
            return bytes(covr[0])
    except Exception:
        pass

    return None
