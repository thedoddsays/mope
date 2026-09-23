"""
ui/main_window.py — Main application window for Mope (Qt port).

Layout:
  ┌────────────────────────────────────────────────────┐
  │  [⏮] [▶] [⏭]   Title — Artist   ═══●═══  🔊──●──  │  ← PlayerBar
  ├────────────┬──────────────────────┬────────────────┤
  │ LeftPanel  │    TrackPanel        │  InfoPanel     │
  │ Library /  │    (centre)          │  (right)       │
  │ Playlists  │                      │                │
  └────────────┴──────────────────────┴────────────────┘
  Status bar
"""

import json
import os
import random
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter, QMenu,
    QDialog, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QPushButton, QHBoxLayout, QInputDialog
)

from library import Library
from player import Player
import playlist_manager as pm
from ui.left_panel  import LeftPanel
from ui.track_panel import TrackPanel
from ui.player_bar  import PlayerBar, REPEAT_NONE, REPEAT_ALL, REPEAT_ONE
from ui.info_panel  import InfoPanel
from ui.qt_utils    import invoke_later

STATE_PATH = os.path.expanduser("~/.local/share/mope/window_state_qt.json")


class MopeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mope")
        self.resize(1100, 680)

        # Core services
        self._library = Library()
        self._player  = Player()

        # Playback queue
        self._queue       = []
        self._queue_index = -1

        # Track whether we're in playlist mode (affects right-click menu)
        self._current_playlist = None   # None = library mode
        self._last_folder      = None   # last folder actually loaded into the track panel

        self._build_ui()
        self._wire_player()
        self._restore_window_state()   # only reads/stores size, safe to run now

    # ------------------------------------------------------------------
    # UI layout
    # ------------------------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Player bar ---
        self._player_bar = PlayerBar()
        self._player_bar.on_play_pause = self._on_play_pause
        self._player_bar.on_previous   = self._on_previous
        self._player_bar.on_next       = self._on_next
        self._player_bar.on_seek       = self._on_seek
        self._player_bar.on_volume     = self._on_volume
        root.addWidget(self._player_bar)

        # --- Three-panel splitter ---
        self._paned_outer = QSplitter(Qt.Orientation.Horizontal)

        self._left_panel = LeftPanel()
        self._left_panel.on_folder_selected   = self._on_folder_selected
        self._left_panel.on_folder_removed    = self._on_folder_removed
        self._left_panel.on_playlist_selected = self._on_playlist_selected
        self._left_panel.on_playlist_changed  = self._on_playlist_changed
        self._left_panel.setMinimumWidth(160)
        self._paned_outer.addWidget(self._left_panel)

        self._paned_inner = QSplitter(Qt.Orientation.Horizontal)

        self._track_panel = TrackPanel()
        self._track_panel.on_track_activated   = self._on_track_activated
        self._track_panel.on_track_right_click = self._on_track_right_click
        self._track_panel.on_breadcrumb_clicked = self._on_folder_selected
        self._paned_inner.addWidget(self._track_panel)

        self._info_panel = InfoPanel()
        self._info_panel.on_fetch_tags = self._on_fetch_tags
        self._paned_inner.addWidget(self._info_panel)
        self._paned_inner.setSizes([700, 180])

        self._paned_outer.addWidget(self._paned_inner)
        self._paned_outer.setSizes([220, 880])

        root.addWidget(self._paned_outer, 1)

        self.setCentralWidget(central)
        self.statusBar().showMessage("Ready  —  Add a music folder to get started")

    # ------------------------------------------------------------------
    # Player wiring
    # ------------------------------------------------------------------

    def _wire_player(self):
        self._player.on_track_end = self._on_track_end
        self._player.on_error     = self._on_player_error
        self._player.on_position  = self._on_position_update

    # ------------------------------------------------------------------
    # Restore saved library roots / last folder on startup
    # ------------------------------------------------------------------

    def _restore_roots(self):
        """Re-populate the folder tree from saved library roots."""
        roots = self._library.get_roots()
        existing = [r for r in roots if os.path.exists(r)]
        if not existing:
            return
        # Browsing into an unscanned subfolder registers it as a "root" too
        # (scan_async() calls add_root() for whatever path it's given), so
        # library_roots often ends up with several nested entries — e.g.
        # /mnt/data/Music alongside /mnt/data/Music/SomeArtist. The
        # shortest path is always the most inclusive one, so restore that.
        best = min(existing, key=len)
        self._left_panel.set_root(best)

    def _restore_last_folder(self):
        """Re-load whichever folder's tracks were showing when the app last closed."""
        try:
            with open(STATE_PATH) as f:
                state = json.load(f)
            last_folder = state.get("last_folder")
            if last_folder and os.path.isdir(last_folder):
                self._on_folder_selected(last_folder)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Window state persistence
    # ------------------------------------------------------------------

    def _restore_window_state(self):
        """Restore saved window size, position, and splitter positions."""
        try:
            with open(STATE_PATH) as f:
                state = json.load(f)
        except Exception:
            state = {}

        w = state.get("width",  1100)
        h = state.get("height", 680)
        self.resize(w, h)

        pos_x = state.get("pos_x")
        pos_y = state.get("pos_y")
        if pos_x is not None and pos_y is not None:
            self._restore_position(pos_x, pos_y, w, h)

        # Splitters don't reliably honor setSizes() before the window has
        # actually been shown/laid out (the same class of bug we hit with
        # GTK's Paned.set_position() needing to wait for the "map" signal).
        # Stash the values and apply them in showEvent() instead.
        self._pending_outer_sizes = state.get("paned_outer_sizes")
        self._pending_inner_sizes = state.get("paned_inner_sizes")

    def _restore_position(self, x: int, y: int, w: int, h: int):
        """Move the window to (x, y), but only if that position would
        actually land at least partly on a currently-connected monitor —
        otherwise (e.g. a second display got unplugged since last run)
        leave it at the OS's default placement instead of opening
        off-screen and invisible."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QRect

        saved_rect = QRect(x, y, w, h)
        for screen in QApplication.screens():
            if screen.availableGeometry().intersects(saved_rect):
                self.move(x, y)
                return
        # No screen overlaps the saved position — leave window at default.

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_state_applied", False):
            return
        self._state_applied = True

        def _apply():
            if self._pending_outer_sizes:
                self._paned_outer.setSizes(self._pending_outer_sizes)
            if self._pending_inner_sizes:
                self._paned_inner.setSizes(self._pending_inner_sizes)

            # QFileSystemModel populates directories asynchronously and
            # needs a running Qt event loop to deliver the results — calling
            # this from __init__ (before app.exec() has started) left the
            # sidebar tree silently empty. Restoring here, after the window
            # is shown and the event loop is confirmed running, fixes that.
            self._restore_roots()
            self._restore_last_folder()

        # One extra deferred pass lets the initial layout settle first.
        QTimer.singleShot(0, _apply)

    def save_state(self):
        """Save window size/position, splitter positions, and last folder
        to disk. Called on normal close AND on app quit/Ctrl+C (see
        main.py), so state isn't lost just because the app wasn't closed
        via the window's close button."""
        try:
            os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
            with open(STATE_PATH, "w") as f:
                json.dump({
                    "width":             self.width(),
                    "height":            self.height(),
                    "pos_x":             self.x(),
                    "pos_y":             self.y(),
                    "paned_outer_sizes": self._paned_outer.sizes(),
                    "paned_inner_sizes": self._paned_inner.sizes(),
                    "last_folder":       self._last_folder,
                }, f)
        except Exception:
            pass

    def closeEvent(self, event):
        """Save state when the window is closed via its close button."""
        self.save_state()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Library: folder selection → scan → track list
    # ------------------------------------------------------------------

    def _on_folder_selected(self, folder_path: str):
        self._current_playlist = None
        tracks = self._library.get_tracks_in_folder(folder_path)

        if tracks:
            self._load_tracks(folder_path, tracks)
        else:
            self.statusBar().showMessage(f"Scanning {folder_path} …")
            self._library.scan_async(
                folder_path,
                on_progress=self._on_scan_progress,
                on_done=lambda count: invoke_later(
                    lambda: self._on_scan_done(folder_path, count)
                )
            )

    def _on_scan_progress(self, filepath: str):
        invoke_later(lambda: self.statusBar().showMessage(
            f"Scanning … {filepath[-60:]}"
        ))

    def _on_scan_done(self, folder_path: str, count: int):
        self.statusBar().showMessage(f"Found {count} tracks in {folder_path}")
        tracks = self._library.get_tracks_in_folder(folder_path)
        self._load_tracks(folder_path, tracks)

    def _load_tracks(self, folder_path: str, tracks: list):
        root = self._left_panel.get_root() or folder_path
        self._track_panel.load_folder(root, folder_path, tracks)
        self._info_panel.load_folder(folder_path, tracks)
        self._queue       = [t["filepath"] for t in tracks]
        self._queue_index = -1
        self._last_folder = folder_path

    def _on_folder_removed(self, folder_path: str):
        """Purge a folder (and anything nested under it) from the library
        index. Does not touch any actual files on disk — just means Mope
        won't need a full rescan to notice the folder is gone."""
        self._library.remove_folder(folder_path)

        # If the track panel is currently showing this folder (or something
        # nested under it), clear it rather than leave stale tracks displayed.
        if self._last_folder and (
            self._last_folder == folder_path
            or self._last_folder.startswith(folder_path.rstrip("/") + "/")
        ):
            self._track_panel.clear()
            self._info_panel.load_folder("", [])
            self._queue       = []
            self._queue_index = -1
            self._last_folder = None

        self.statusBar().showMessage(f"Removed from library: {folder_path}")

    # ------------------------------------------------------------------
    # Playlists: selection → track list
    # ------------------------------------------------------------------

    def _on_playlist_selected(self, playlist):
        self._current_playlist = playlist
        self._load_playlist_tracks(playlist)

    def _load_playlist_tracks(self, playlist):
        """Show a playlist's tracks in the centre panel."""
        enriched = []
        for t in playlist.tracks:
            db = self._library.get_track_by_path(t["filepath"])
            if db:
                enriched.append(db)
            else:
                enriched.append({
                    "filepath":    t["filepath"],
                    "folder":      "",
                    "filename":    Path(t["filepath"]).name,
                    "title":       t["title"],
                    "artist":      t["artist"],
                    "album":       "",
                    "albumartist": "",
                    "tracknumber": None,
                    "discnumber":  None,
                    "year":        None,
                    "genre":       None,
                    "duration":    t["duration"],
                    "bitrate":     None,
                })

        self._track_panel.load_playlist(playlist.name, enriched)
        self._queue       = [t["filepath"] for t in playlist.tracks]
        self._queue_index = -1

        # The info panel is folder/album-oriented and has no single
        # "album" to show for a playlist spanning many albums — clear it
        # here; _play_track() will populate it with whatever track is
        # actually playing once playback starts.
        self._info_panel.load_folder("", [])

        n = len(playlist.tracks)
        self.statusBar().showMessage(
            playlist.name + " -- " + str(n) + (" tracks" if n != 1 else " track")
        )

    def _on_playlist_changed(self):
        """Called when a playlist is created/renamed/deleted."""
        self._left_panel.refresh_playlists()

    # ------------------------------------------------------------------
    # Track activation (double-click)
    # ------------------------------------------------------------------

    def _on_track_activated(self, filepath: str):
        if filepath in self._queue:
            self._queue_index = self._queue.index(filepath)
        self._play_track(filepath)

    def _play_track(self, filepath: str):
        self._player.play_file(filepath)
        self._player_bar.set_playing(True)
        track = self._library.get_track_by_path(filepath)
        if track:
            title  = track["title"]  or Path(filepath).stem
            artist = track["artist"] or ""
            dur    = track["duration"] or 0.0
            self._player_bar.set_track(title, artist, dur)
            # While viewing a playlist, the info panel has no single folder
            # to show (a playlist can span many albums) — so instead show
            # whatever track is actually playing right now. In library mode
            # it stays folder-oriented (matches whatever's being browsed,
            # regardless of playback) since that's what "Fetch Tags" acts on.
            if self._current_playlist:
                self._info_panel.load_folder(track["folder"], [track])
        else:
            self._player_bar.set_track(Path(filepath).stem, "", 0.0)
            if self._current_playlist:
                self._info_panel.load_folder("", [])
        self._track_panel.highlight_track(filepath)
        self.statusBar().showMessage(f"Playing: {filepath}")

    # ------------------------------------------------------------------
    # Transport controls
    # ------------------------------------------------------------------

    def _on_play_pause(self):
        self._player.play_pause()
        self._player_bar.set_playing(self._player.is_playing)

    def _on_previous(self):
        if not self._queue:
            return
        if self._player_bar.shuffle:
            self._play_random()
            return
        self._queue_index = max(0, self._queue_index - 1)
        self._play_track(self._queue[self._queue_index])

    def _on_next(self, from_track_end=False):
        if not self._queue:
            return
        repeat  = self._player_bar.repeat_mode
        shuffle = self._player_bar.shuffle

        if from_track_end and repeat == REPEAT_ONE:
            self._play_track(self._queue[self._queue_index])
            return

        if shuffle:
            self._play_random()
            return

        if self._queue_index < len(self._queue) - 1:
            self._queue_index += 1
            self._play_track(self._queue[self._queue_index])
        elif from_track_end and repeat == REPEAT_ALL:
            self._queue_index = 0
            self._play_track(self._queue[0])

    def _play_random(self):
        if len(self._queue) > 1:
            choices = [i for i in range(len(self._queue)) if i != self._queue_index]
            self._queue_index = random.choice(choices)
        else:
            self._queue_index = 0
        self._play_track(self._queue[self._queue_index])

    def _on_track_end(self):
        invoke_later(lambda: self._on_next(True))

    def _on_seek(self, seconds: float):
        self._player.seek(seconds)

    def _on_volume(self, volume: float):
        self._player.set_volume(volume)

    def _on_position_update(self, pos: float, dur: float):
        invoke_later(lambda: self._player_bar.update_position(pos, dur))

    def _on_player_error(self, err: str):
        invoke_later(lambda: self.statusBar().showMessage(f"Error: {err}"))

    # ------------------------------------------------------------------
    # Right-click context menu on tracks
    # ------------------------------------------------------------------

    def _on_track_right_click(self, filepath: str, global_x: float, global_y: float):
        menu = QMenu(self)

        menu.addAction("▶  Play", lambda: self._on_track_activated(filepath))

        playlists = self._left_panel.get_playlist_panel().get_playlist_names()
        if playlists:
            add_menu = menu.addMenu("Add to playlist")
            for pl_name, pl in playlists:
                add_menu.addAction(pl_name, lambda p=pl: self._add_track_to_playlist(filepath, p))

        menu.addSeparator()
        menu.addAction("＋  New playlist from here",
                        lambda: self._new_playlist_from_track(filepath))

        if self._current_playlist:
            menu.addAction("✕  Remove from playlist",
                            lambda: self._remove_from_current_playlist(filepath))

        menu.addSeparator()
        menu.addAction("🔍  Fetch Tags", lambda: self._fetch_single_track(filepath))

        menu.exec(QPoint(int(global_x), int(global_y)))

    # ------------------------------------------------------------------
    # Playlist track management (from right-click)
    # ------------------------------------------------------------------

    def _add_track_to_playlist(self, filepath: str, playlist):
        track = self._library.get_track_by_path(filepath)
        title  = (track["title"]  if track else "") or Path(filepath).name
        artist = (track["artist"] if track else "") or ""
        dur    = (track["duration"] if track else 0.0) or 0.0

        updated = pm.add_track(playlist, filepath, title, artist, dur)
        self.statusBar().showMessage(f"Added {title} to playlist {updated.name}")
        # The sidebar's PlaylistPanel caches Playlist objects from its last
        # refresh() call, so without this, clicking into the playlist right
        # after adding a track would show the stale (pre-add) track list.
        self._left_panel.refresh_playlists()
        if (self._current_playlist and
                self._current_playlist.path == updated.path):
            self._current_playlist = updated
            self._load_playlist_tracks(updated)

    def _remove_from_current_playlist(self, filepath: str):
        if not self._current_playlist:
            return
        updated = pm.remove_track(self._current_playlist, filepath)
        self._current_playlist = updated
        self._load_playlist_tracks(updated)
        self._left_panel.refresh_playlists()
        self.statusBar().showMessage(f"Removed track from {updated.name}")

    def _new_playlist_from_track(self, filepath: str):
        """Ask for a name, create a new playlist, add the track."""
        name, ok = QInputDialog.getText(self, "New Playlist", "Name:")
        if not ok or not name.strip():
            return
        new_pl = pm.create_playlist(name.strip())
        track  = self._library.get_track_by_path(filepath)
        title  = (track["title"]  if track else "") or Path(filepath).name
        artist = (track["artist"] if track else "") or ""
        dur    = (track["duration"] if track else 0.0) or 0.0
        pm.add_track(new_pl, filepath, title, artist, dur)
        self._left_panel.refresh_playlists()
        self.statusBar().showMessage(f"Created playlist: {name.strip()}")

    # ------------------------------------------------------------------
    # MusicBrainz tagging
    # ------------------------------------------------------------------

    def _on_fetch_tags(self, folder_path: str, artist: str, album: str):
        import tagger

        def worker():
            results = tagger.search_release(artist=artist, album=album)
            invoke_later(lambda: self._show_tag_results(folder_path, results))

        threading.Thread(target=worker, daemon=True).start()

    def _show_tag_results(self, folder_path: str, results: list):
        if not results:
            self._info_panel.set_status("No results found on MusicBrainz.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("MusicBrainz Results")
        dialog.resize(560, 360)
        layout = QVBoxLayout(dialog)

        from PySide6.QtWidgets import QLabel
        lbl = QLabel("Select the correct release to apply tags:")
        layout.addWidget(lbl)

        table = QTableWidget(len(results), 3)
        table.setHorizontalHeaderLabels(["Album", "Artist", "Year"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        for row, r in enumerate(results):
            album_item = QTableWidgetItem(r["title"])
            album_item.setData(Qt.ItemDataRole.UserRole, r["mbid"])
            table.setItem(row, 0, album_item)
            table.setItem(row, 1, QTableWidgetItem(r["artist"]))
            table.setItem(row, 2, QTableWidgetItem(r.get("year", "")))
        table.horizontalHeader().setStretchLastSection(False)
        table.horizontalHeader().setSectionResizeMode(0, table.horizontalHeader().ResizeMode.Stretch)
        layout.addWidget(table, 1)

        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        apply_btn = QPushButton("Apply Tags")

        def on_apply():
            row = table.currentRow()
            if row < 0:
                return
            mbid = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            dialog.accept()
            self._apply_tags_from_mbid(folder_path, mbid)

        apply_btn.clicked.connect(on_apply)
        btn_box.addWidget(cancel_btn)
        btn_box.addWidget(apply_btn)
        layout.addLayout(btn_box)

        dialog.exec()

    def _apply_tags_from_mbid(self, folder_path: str, mbid: str):
        import tagger
        self._info_panel.set_status("Fetching release details…")

        def worker():
            detail = tagger.get_release_detail(mbid)
            if not detail:
                self._info_panel.set_status("Could not fetch release details.")
                return

            tracks    = self._library.get_tracks_in_folder(folder_path)
            mb_tracks = detail.get("tracks", [])
            written   = 0

            for i, db_track in enumerate(tracks):
                mb   = mb_tracks[i] if i < len(mb_tracks) else {}
                tags = {
                    "album":       detail.get("album"),
                    "albumartist": detail.get("albumartist"),
                    "year":        detail.get("year"),
                    "title":       mb.get("title"),
                    "tracknumber": mb.get("tracknumber"),
                    "discnumber":  mb.get("discnumber"),
                }
                if tagger.write_tags(db_track["filepath"], tags):
                    written += 1

            art = tagger.fetch_album_art(mbid)
            if art:
                for db_track in tracks:
                    tagger.write_tags(db_track["filepath"], {}, art_bytes=art)
                self._info_panel.set_art_bytes(art)

            self._library.scan_async(folder_path)
            self._info_panel.set_status(f"✓ Tags written to {written} files.")

        threading.Thread(target=worker, daemon=True).start()

    def _fetch_single_track(self, filepath: str):
        track = self._library.get_track_by_path(filepath)
        if track:
            artist = track["artist"] or ""
            title  = track["title"]  or ""
            import tagger

            def worker():
                results = tagger.search_release(artist=artist, title=title)
                folder  = track["folder"]
                invoke_later(lambda: self._show_tag_results(folder, results))

            threading.Thread(target=worker, daemon=True).start()
