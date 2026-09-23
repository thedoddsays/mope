"""
library.py — Music library scanner and SQLite database for Mope.

Responsibilities:
  - Recursively scan a root folder for audio files
  - Read metadata tags (via mutagen) from each file
  - Store everything in a local SQLite database (~/.local/share/mope/library.db)
  - Provide fast queries: list folders, list tracks in a folder, search
"""

import os
import sqlite3
import threading
from pathlib import Path
from typing import Callable, List, Dict, Optional

# mutagen reads audio metadata (tags) from MP3, FLAC, OGG, M4A, etc.
try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3NoHeaderError
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

# Where we store the database — always resolve the real home directory
DB_DIR  = Path(os.path.expanduser("~")) / ".local" / "share" / "mope"
DB_PATH = DB_DIR / "library.db"

# Audio file extensions we care about
AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac",
    ".wav", ".wv", ".ape", ".mpc", ".wma", ".aiff", ".aif"
}


class Library:
    """Manages the Mope music library database."""

    def __init__(self):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row   # rows behave like dicts
        # WAL mode: much safer for concurrent writes, survives app crashes
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=10000")
        self._lock = threading.Lock()
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self):
        with self._conn:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    filepath    TEXT UNIQUE NOT NULL,
                    folder      TEXT NOT NULL,
                    filename    TEXT NOT NULL,
                    title       TEXT,
                    artist      TEXT,
                    album       TEXT,
                    albumartist TEXT,
                    tracknumber INTEGER,
                    discnumber  INTEGER,
                    year        TEXT,
                    genre       TEXT,
                    duration    REAL,
                    bitrate     INTEGER,
                    last_scanned INTEGER
                );

                CREATE INDEX IF NOT EXISTS idx_folder   ON tracks(folder);
                CREATE INDEX IF NOT EXISTS idx_artist   ON tracks(artist);
                CREATE INDEX IF NOT EXISTS idx_album    ON tracks(album);

                CREATE TABLE IF NOT EXISTS library_roots (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    path    TEXT UNIQUE NOT NULL
                );
            """)

    # ------------------------------------------------------------------
    # Root folder management
    # ------------------------------------------------------------------

    def add_root(self, path: str):
        """Register a root music folder."""
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO library_roots (path) VALUES (?)", (path,)
            )

    def get_roots(self) -> List[str]:
        cur = self._conn.execute("SELECT path FROM library_roots")
        return [row["path"] for row in cur.fetchall()]

    def remove_folder(self, path: str):
        """Remove a folder (and everything nested under it) from the
        library: purges its indexed tracks and any registered root entries
        for it, without touching the actual files on disk. Used when a
        folder has been deleted/moved outside of Mope and the user wants
        the library to forget about it without a full rescan."""
        like_pattern = path.rstrip("/") + "/%"
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM tracks WHERE folder = ? OR folder LIKE ?",
                (path, like_pattern)
            )
            self._conn.execute(
                "DELETE FROM library_roots WHERE path = ? OR path LIKE ?",
                (path, like_pattern)
            )

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan_async(self, root: str,
                   on_progress: Optional[Callable[[str], None]] = None,
                   on_done: Optional[Callable[[int], None]] = None):
        """
        Scan *root* for audio files in a background thread.
        on_progress(filepath) is called for each file found.
        on_done(total_count) is called when the scan finishes.
        """
        self.add_root(root)
        thread = threading.Thread(
            target=self._scan_worker,
            args=(root, on_progress, on_done),
            daemon=True
        )
        thread.start()

    def _scan_worker(self, root, on_progress, on_done):
        count = 0
        import time
        now = int(time.time())

        for dirpath, _, filenames in os.walk(root):
            for filename in sorted(filenames):
                ext = Path(filename).suffix.lower()
                if ext not in AUDIO_EXTENSIONS:
                    continue

                filepath = os.path.join(dirpath, filename)
                meta = self._read_tags(filepath)
                meta["filepath"]     = filepath
                meta["folder"]       = dirpath
                meta["filename"]     = filename
                meta["last_scanned"] = now

                with self._lock:
                    self._conn.execute("""
                        INSERT INTO tracks
                            (filepath, folder, filename, title, artist, album,
                             albumartist, tracknumber, discnumber, year, genre,
                             duration, bitrate, last_scanned)
                        VALUES
                            (:filepath, :folder, :filename, :title, :artist, :album,
                             :albumartist, :tracknumber, :discnumber, :year, :genre,
                             :duration, :bitrate, :last_scanned)
                        ON CONFLICT(filepath) DO UPDATE SET
                            title        = excluded.title,
                            artist       = excluded.artist,
                            album        = excluded.album,
                            albumartist  = excluded.albumartist,
                            tracknumber  = excluded.tracknumber,
                            discnumber   = excluded.discnumber,
                            year         = excluded.year,
                            genre        = excluded.genre,
                            duration     = excluded.duration,
                            bitrate      = excluded.bitrate,
                            last_scanned = excluded.last_scanned
                    """, meta)
                    self._conn.commit()

                count += 1
                if on_progress:
                    on_progress(filepath)

        if on_done:
            on_done(count)

    def _read_tags(self, filepath: str) -> Dict:
        """Extract metadata from an audio file using mutagen."""
        defaults = {
            "title": None, "artist": None, "album": None,
            "albumartist": None, "tracknumber": None, "discnumber": None,
            "year": None, "genre": None, "duration": None, "bitrate": None
        }

        if not HAS_MUTAGEN:
            return defaults

        try:
            audio = MutagenFile(filepath, easy=True)
            if audio is None:
                return defaults

            def get(key):
                val = audio.get(key)
                return val[0] if val else None

            def get_int(key):
                val = get(key)
                if val is None:
                    return None
                # tracknumber can be "3/12" — take just the first part
                try:
                    return int(str(val).split("/")[0])
                except (ValueError, TypeError):
                    return None

            duration = None
            bitrate  = None
            if hasattr(audio, "info") and audio.info:
                duration = getattr(audio.info, "length",  None)
                bitrate  = getattr(audio.info, "bitrate", None)

            return {
                "title":       get("title"),
                "artist":      get("artist"),
                "album":       get("album"),
                "albumartist": get("albumartist"),
                "tracknumber": get_int("tracknumber"),
                "discnumber":  get_int("discnumber"),
                "year":        get("date"),
                "genre":       get("genre"),
                "duration":    duration,
                "bitrate":     bitrate,
            }
        except Exception:
            return defaults

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_folders(self, root: str) -> List[str]:
        """
        Return all unique folder paths under *root* that contain audio files,
        sorted alphabetically.
        """
        cur = self._conn.execute(
            "SELECT DISTINCT folder FROM tracks WHERE folder LIKE ? ORDER BY folder",
            (root + "%",)
        )
        return [row["folder"] for row in cur.fetchall()]

    def get_tracks_in_folder(self, folder: str) -> List[sqlite3.Row]:
        """Return all tracks inside *folder*, including any nested
        subfolders (e.g. clicking an artist folder returns every track
        across all of that artist's album subfolders, not just files
        sitting directly in the artist folder itself — which is normally
        none, since albums are one level deeper). Sorted by disc/track
        number then filename within each folder, then by folder so
        albums stay grouped together rather than interleaved."""
        like_pattern = folder.rstrip("/") + "/%"
        cur = self._conn.execute("""
            SELECT * FROM tracks
            WHERE folder = ? OR folder LIKE ?
            ORDER BY
                folder,
                COALESCE(discnumber, 0),
                COALESCE(tracknumber, 9999),
                filename
        """, (folder, like_pattern))
        return cur.fetchall()

    def get_track_by_path(self, filepath: str) -> Optional[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT * FROM tracks WHERE filepath = ?", (filepath,)
        )
        return cur.fetchone()

    def search(self, query: str) -> List[sqlite3.Row]:
        """Full-text search across title, artist, album, filename."""
        like = f"%{query}%"
        cur = self._conn.execute("""
            SELECT * FROM tracks
            WHERE title LIKE ?
               OR artist LIKE ?
               OR album LIKE ?
               OR filename LIKE ?
            ORDER BY artist, album, tracknumber, filename
            LIMIT 500
        """, (like, like, like, like))
        return cur.fetchall()

    def close(self):
        self._conn.close()
