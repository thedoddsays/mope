"""
playlist_manager.py — M3U8 playlist storage and management for Mope.

Playlists are stored as UTF-8 M3U8 files in ~/.local/share/mope/playlists/.
Each file is a standard extended M3U that any other player can read.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict


PLAYLIST_DIR = Path.home() / ".local" / "share" / "mope" / "playlists"
PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------
# Data class
# ------------------------------------------------------------------

class Playlist:
    """In-memory representation of a playlist."""

    def __init__(self, name: str, path: Path, tracks: List[Dict]):
        self.name   = name          # display name (filename without extension)
        self.path   = path          # Path to the .m3u8 file
        self.tracks = tracks        # list of dicts: {filepath, title, artist, duration}

    def __repr__(self):
        return f"<Playlist {self.name!r} ({len(self.tracks)} tracks)>"


# ------------------------------------------------------------------
# Core functions
# ------------------------------------------------------------------

def list_playlists() -> List[Playlist]:
    """Return all playlists in the Mope playlist directory, sorted by name."""
    playlists = []
    for f in sorted(PLAYLIST_DIR.glob("*.m3u8")):
        tracks = _parse_m3u(f)
        playlists.append(Playlist(name=f.stem, path=f, tracks=tracks))
    return playlists


def create_playlist(name: str) -> Playlist:
    """Create a new empty playlist and save it to disk."""
    path = _unique_path(name)
    _write_m3u(path, [])
    return Playlist(name=path.stem, path=path, tracks=[])


def delete_playlist(playlist: Playlist):
    """Delete a playlist file from disk."""
    if playlist.path.exists():
        playlist.path.unlink()


def rename_playlist(playlist: Playlist, new_name: str) -> Playlist:
    """Rename a playlist (moves the file). Returns updated Playlist."""
    new_path = _unique_path(new_name, exclude=playlist.path)
    playlist.path.rename(new_path)
    return Playlist(name=new_path.stem, path=new_path, tracks=playlist.tracks)


def add_track(playlist: Playlist, filepath: str,
              title: str = "", artist: str = "",
              duration: float = 0.0) -> Playlist:
    """Add a track to a playlist and save. Returns updated Playlist."""
    # Avoid duplicates
    existing = [t["filepath"] for t in playlist.tracks]
    if filepath in existing:
        return playlist

    track = {"filepath": filepath, "title": title,
             "artist": artist, "duration": duration}
    new_tracks = playlist.tracks + [track]
    _write_m3u(playlist.path, new_tracks)
    return Playlist(name=playlist.name, path=playlist.path, tracks=new_tracks)


def remove_track(playlist: Playlist, filepath: str) -> Playlist:
    """Remove a track from a playlist by filepath and save."""
    new_tracks = [t for t in playlist.tracks if t["filepath"] != filepath]
    _write_m3u(playlist.path, new_tracks)
    return Playlist(name=playlist.name, path=playlist.path, tracks=new_tracks)


def reorder_tracks(playlist: Playlist, new_order: List[Dict]) -> Playlist:
    """Save playlist with tracks in a new order."""
    _write_m3u(playlist.path, new_order)
    return Playlist(name=playlist.name, path=playlist.path, tracks=new_order)


# ------------------------------------------------------------------
# Import / Export
# ------------------------------------------------------------------

def import_playlist(source_path: str) -> Optional[Playlist]:
    """
    Import an .m3u or .m3u8 file from anywhere on disk.
    Copies it into the Mope playlist directory.
    Returns the new Playlist, or None on failure.
    """
    src = Path(source_path)
    if not src.exists():
        return None

    tracks = _parse_m3u(src)
    dest   = _unique_path(src.stem)
    _write_m3u(dest, tracks)   # re-write so paths are resolved consistently
    return Playlist(name=dest.stem, path=dest, tracks=tracks)


def export_playlist(playlist: Playlist, dest_path: str):
    """
    Export a playlist to an arbitrary location as a standard M3U8 file.
    """
    dest = Path(dest_path)
    shutil.copy2(playlist.path, dest)


# ------------------------------------------------------------------
# M3U parsing and writing
# ------------------------------------------------------------------

def _parse_m3u(path: Path) -> List[Dict]:
    """
    Parse an extended M3U/M3U8 file.
    Returns a list of track dicts: {filepath, title, artist, duration}
    Missing files are silently skipped.
    """
    tracks  = []
    pending = {"title": "", "artist": "", "duration": 0.0}

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []

    for line in lines:
        line = line.strip()
        if not line or line == "#EXTM3U":
            continue

        if line.startswith("#EXTINF:"):
            # Format: #EXTINF:<duration>,<artist> - <title>
            # or just: #EXTINF:<duration>,<title>
            rest = line[8:]  # after "#EXTINF:"
            comma = rest.find(",")
            if comma != -1:
                try:
                    pending["duration"] = float(rest[:comma])
                except ValueError:
                    pending["duration"] = 0.0
                info = rest[comma + 1:].strip()
                if " - " in info:
                    artist, title = info.split(" - ", 1)
                    pending["artist"] = artist.strip()
                    pending["title"]  = title.strip()
                else:
                    pending["title"]  = info
                    pending["artist"] = ""
            continue

        if line.startswith("#"):
            continue  # other comment, skip

        # This line is a filepath or URL
        filepath = line
        # Resolve relative paths relative to the playlist file's directory
        if not os.path.isabs(filepath):
            filepath = str(path.parent / filepath)

        tracks.append({
            "filepath": filepath,
            "title":    pending["title"]    or Path(filepath).stem,
            "artist":   pending["artist"]   or "",
            "duration": pending["duration"] or 0.0,
        })
        pending = {"title": "", "artist": "", "duration": 0.0}

    return tracks


def _write_m3u(path: Path, tracks: List[Dict]):
    """Write tracks to an extended M3U8 file."""
    lines = ["#EXTM3U", ""]
    for t in tracks:
        dur    = int(t.get("duration") or 0)
        artist = t.get("artist", "")
        title  = t.get("title", "") or Path(t["filepath"]).stem
        info   = f"{artist} - {title}" if artist else title
        lines.append(f"#EXTINF:{dur},{info}")
        lines.append(t["filepath"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _unique_path(name: str, exclude: Optional[Path] = None) -> Path:
    """Return a unique .m3u8 path in PLAYLIST_DIR for the given name."""
    safe = _safe_filename(name)
    candidate = PLAYLIST_DIR / f"{safe}.m3u8"
    if candidate == exclude or not candidate.exists():
        return candidate
    i = 2
    while True:
        candidate = PLAYLIST_DIR / f"{safe}_{i}.m3u8"
        if candidate == exclude or not candidate.exists():
            return candidate
        i += 1


def _safe_filename(name: str) -> str:
    """Strip characters that are unsafe in filenames."""
    bad = r'\/:*?"<>|'
    return "".join(c if c not in bad else "_" for c in name).strip() or "playlist"
