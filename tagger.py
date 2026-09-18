"""
tagger.py — MusicBrainz lookup and tag-writing for Mope.

Responsibilities:
  - Search MusicBrainz for a release by artist + album (or track title)
  - Return structured results the UI can display for the user to confirm
  - Write chosen tags back to the file via mutagen
  - Fetch and save album art from the Cover Art Archive
"""

import os
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional

try:
    import musicbrainzngs as mb
    mb.set_useragent("Mope", "0.1", "https://github.com/mope-player/mope")
    HAS_MB = True
except ImportError:
    HAS_MB = False

try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import (
        ID3, TIT2, TPE1, TALB, TPE2, TRCK, TDRC, TCON, APIC
    )
    from mutagen.flac import FLAC, Picture
    from mutagen.mp4  import MP4, MP4Cover
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# Where we cache downloaded artwork
ART_CACHE_DIR = Path.home() / ".local" / "share" / "mope" / "art_cache"
ART_CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------------
# Search
# ------------------------------------------------------------------

def search_release(artist: str = "", album: str = "",
                   title: str = "") -> List[Dict]:
    """
    Search MusicBrainz for releases matching artist+album or track title.
    Returns a list of result dicts (up to 10).
    """
    if not HAS_MB:
        return []

    results = []
    try:
        if album:
            resp = mb.search_releases(artist=artist, release=album, limit=10)
            for r in resp.get("release-list", []):
                results.append(_parse_release(r))
        elif title:
            resp = mb.search_recordings(artist=artist, recording=title, limit=10)
            for r in resp.get("recording-list", []):
                results.append(_parse_recording(r))
    except Exception as e:
        print(f"[tagger] MusicBrainz search error: {e}")

    return results


def _parse_release(r: dict) -> Dict:
    artist_credit = r.get("artist-credit-phrase", "")
    return {
        "type":      "release",
        "mbid":      r.get("id", ""),
        "title":     r.get("title", ""),
        "artist":    artist_credit,
        "year":      r.get("date", "")[:4] if r.get("date") else "",
        "tracks":    r.get("medium-track-count", ""),
        "country":   r.get("country", ""),
        "label":     _first_label(r),
    }


def _parse_recording(r: dict) -> Dict:
    artist_credit = r.get("artist-credit-phrase", "")
    release = (r.get("release-list") or [{}])[0]
    return {
        "type":   "recording",
        "mbid":   r.get("id", ""),
        "title":  r.get("title", ""),
        "artist": artist_credit,
        "album":  release.get("title", ""),
        "year":   release.get("date", "")[:4] if release.get("date") else "",
    }


def _first_label(r: dict) -> str:
    try:
        return r["label-info-list"][0]["label"]["name"]
    except (KeyError, IndexError, TypeError):
        return ""


# ------------------------------------------------------------------
# Full release detail (for writing tags to a whole album folder)
# ------------------------------------------------------------------

def get_release_detail(mbid: str) -> Optional[Dict]:
    """
    Fetch full release info including per-track details.
    Returns a dict with 'tracks' as a list of per-track dicts.
    """
    if not HAS_MB:
        return None
    try:
        r = mb.get_release_by_id(
            mbid,
            includes=["recordings", "artists", "labels", "release-groups"]
        )["release"]

        tracks = []
        for medium in r.get("medium-list", []):
            disc = medium.get("position", 1)
            for t in medium.get("track-list", []):
                rec = t.get("recording", {})
                tracks.append({
                    "tracknumber": t.get("position"),
                    "discnumber":  disc,
                    "title":       rec.get("title", t.get("title", "")),
                    "duration":    rec.get("length"),  # milliseconds or None
                })

        return {
            "mbid":       mbid,
            "album":      r.get("title", ""),
            "albumartist": _first_artist(r),
            "year":       r.get("date", "")[:4] if r.get("date") else "",
            "label":      _first_label(r),
            "tracks":     tracks,
        }
    except Exception as e:
        print(f"[tagger] release detail error: {e}")
        return None


def _first_artist(r: dict) -> str:
    try:
        return r["artist-credit"][0]["artist"]["name"]
    except (KeyError, IndexError, TypeError):
        return ""


# ------------------------------------------------------------------
# Album art
# ------------------------------------------------------------------

def fetch_album_art(mbid: str,
                    on_done: Optional[Callable[[Optional[bytes]], None]] = None
                    ) -> Optional[bytes]:
    """
    Download front cover art from the Cover Art Archive for a release MBID.
    Result is raw image bytes (JPEG/PNG).  Caches to disk.
    Calls on_done(bytes_or_None) when finished (always in calling thread if
    on_done is None; in background thread if provided).
    """
    cache_path = ART_CACHE_DIR / f"{mbid}.jpg"

    def _fetch():
        # Return from cache if available
        if cache_path.exists():
            data = cache_path.read_bytes()
            return data

        if not HAS_REQUESTS:
            return None

        url = f"https://coverartarchive.org/release/{mbid}/front-500"
        try:
            resp = requests.get(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                cache_path.write_bytes(resp.content)
                return resp.content
        except Exception as e:
            print(f"[tagger] art fetch error: {e}")
        return None

    if on_done:
        def worker():
            data = _fetch()
            on_done(data)
        threading.Thread(target=worker, daemon=True).start()
        return None
    else:
        return _fetch()


# ------------------------------------------------------------------
# Tag writing
# ------------------------------------------------------------------

def write_tags(filepath: str, tags: Dict, art_bytes: Optional[bytes] = None) -> bool:
    """
    Write *tags* dict to the audio file at *filepath*.
    Supported keys: title, artist, album, albumartist,
                    tracknumber, discnumber, year, genre
    Optionally embeds *art_bytes* as cover art.
    Returns True on success.
    """
    if not HAS_MUTAGEN:
        print("[tagger] mutagen not installed — cannot write tags")
        return False

    ext = Path(filepath).suffix.lower()

    try:
        if ext == ".mp3":
            return _write_mp3(filepath, tags, art_bytes)
        elif ext == ".flac":
            return _write_flac(filepath, tags, art_bytes)
        elif ext in (".m4a", ".aac", ".mp4"):
            return _write_mp4(filepath, tags, art_bytes)
        else:
            # Generic easy-tag fallback (ogg, opus, wv, etc.)
            return _write_easy(filepath, tags)
    except Exception as e:
        print(f"[tagger] write_tags error for {filepath}: {e}")
        return False


def _write_mp3(filepath, tags, art_bytes):
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TPE2, TRCK, TPOS, TDRC, TCON, APIC
    try:
        audio = ID3(filepath)
    except Exception:
        audio = ID3()

    def set_tag(frame_cls, key):
        val = tags.get(key)
        if val is not None:
            audio[frame_cls.__name__] = frame_cls(encoding=3, text=str(val))

    set_tag(TIT2, "title")
    set_tag(TPE1, "artist")
    set_tag(TALB, "album")
    set_tag(TPE2, "albumartist")
    set_tag(TDRC, "year")
    set_tag(TCON, "genre")

    tn = tags.get("tracknumber")
    if tn is not None:
        audio["TRCK"] = TRCK(encoding=3, text=str(tn))
    dn = tags.get("discnumber")
    if dn is not None:
        audio["TPOS"] = TPOS(encoding=3, text=str(dn))

    if art_bytes:
        audio["APIC"] = APIC(
            encoding=3, mime="image/jpeg", type=3,
            desc="Cover", data=art_bytes
        )

    audio.save(filepath)
    return True


def _write_flac(filepath, tags, art_bytes):
    audio = FLAC(filepath)
    mapping = {
        "title": "title", "artist": "artist", "album": "album",
        "albumartist": "albumartist", "year": "date",
        "genre": "genre", "tracknumber": "tracknumber",
        "discnumber": "discnumber",
    }
    for key, tag in mapping.items():
        val = tags.get(key)
        if val is not None:
            audio[tag] = [str(val)]

    if art_bytes:
        pic = Picture()
        pic.type = 3  # Cover (front)
        pic.mime = "image/jpeg"
        pic.data = art_bytes
        audio.clear_pictures()
        audio.add_picture(pic)

    audio.save()
    return True


def _write_mp4(filepath, tags, art_bytes):
    audio = MP4(filepath)
    mapping = {
        "title":       "\xa9nam",
        "artist":      "\xa9ART",
        "album":       "\xa9alb",
        "albumartist": "aART",
        "year":        "\xa9day",
        "genre":       "\xa9gen",
    }
    for key, atom in mapping.items():
        val = tags.get(key)
        if val is not None:
            audio[atom] = [str(val)]

    tn = tags.get("tracknumber")
    if tn is not None:
        audio["trkn"] = [(int(tn), 0)]

    if art_bytes:
        audio["covr"] = [MP4Cover(art_bytes, imageformat=MP4Cover.FORMAT_JPEG)]

    audio.save()
    return True


def _write_easy(filepath, tags):
    audio = MutagenFile(filepath, easy=True)
    if audio is None:
        return False
    mapping = {
        "title": "title", "artist": "artist", "album": "album",
        "albumartist": "albumartist", "year": "date",
        "genre": "genre", "tracknumber": "tracknumber",
    }
    for key, tag in mapping.items():
        val = tags.get(key)
        if val is not None:
            audio[tag] = [str(val)]
    audio.save()
    return True
