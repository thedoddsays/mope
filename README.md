# Mope

**A music player that respects your folders.**

Most music players build their library from metadata tags, so one artist turns into a dozen near-duplicates: `2Pac`, `2pac feat. Dr. Dre`, `2Pac & Outlawz`, `2pac ft. Someone Else`... Mope lets you browse your collection the way you already organized it on disk. If your music lives in `Music/2Pac/`, that's what you see: one folder, not 37 artist entries.

Mope is a music library, player, and tagger in one small app. It runs on Linux, Windows, and macOS.

<!-- Add a screenshot here: save it to the repo as screenshot.png -->
![Mope screenshot](screenshot.png)

## Features

- **Folder-based browsing.** Navigate your collection by your own directory structure, not by messy or inconsistent tags.
- **Music library.** Scans your folders into a local SQLite database, so your library loads quickly.
- **Playback.** Play, pause, seek, skip, shuffle, repeat, repeat-one, and volume control.
- **Playlists.** Create, rename, and delete playlists, with import and export as standard `.m3u8` files.
- **Tagging.** Look up track info on MusicBrainz and write tags to your files, for when you *do* want to fix them.
- **Remembers your layout.** Window size, position, and panel sizes are restored between sessions.
- **Dark theme.** A dark gray and orange theme, applied consistently across the app.

## Installation

Mope needs **Python 3.10 or newer**.

### Linux (Mint / Ubuntu, with app-menu entry)

```bash
git clone https://github.com/thedoddsays/mope.git
cd mope
chmod +x install.sh uninstall.sh
./install.sh
```

This installs Mope to `~/.local/share/mope-qt`, adds a `mope-qt` command, and puts a **Mope (Qt)** entry in your app menu under Sound & Video. It asks for your sudo password once to install a couple of required system packages, including `libxcb-cursor0`, which Qt 6.5+ needs on Linux but many systems don't have by default.

To remove it, run `./uninstall.sh`. Your music database and playlists are never touched.

### Windows

1. Install Python 3.10+ from [python.org](https://www.python.org/). During install, check **"Add python.exe to PATH"**.
2. Get the code, either with `git clone https://github.com/thedoddsays/mope.git` or by clicking **Code → Download ZIP** on this page and extracting it somewhere convenient.
3. Open Command Prompt or PowerShell in that folder and install the dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run it:
   ```
   python main.py
   ```

There's no separate GTK or GStreamer install needed. PySide6 bundles its own Qt, and playback uses Windows' built-in media framework.

**Start Menu shortcut (optional):** once `python main.py` works, double-click `install.bat`. It creates a **Mope (Qt)** Start Menu shortcut that launches without leaving a console window open. The shortcut points at wherever you put the folder, so don't move or delete the folder afterward without re-running `install.bat`. Use `uninstall.bat` to remove the shortcut.

Windows may show a SmartScreen warning the first time, because the script is unsigned. Click **More info → Run anyway**. If **Smart App Control** is on, it may block the `.bat` outright. In that case, paste the contents of `install.ps1` into a PowerShell window instead.

### macOS, or Linux without the installer

```bash
git clone https://github.com/thedoddsays/mope.git
cd mope
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## Where your data lives

Your library database (`library.db`), playlists, and cached album art are stored in `~/.local/share/mope/` on every OS. Uninstalling the app never deletes them.

## Testing status

**Confirmed working on Linux Mint (Cinnamon, X11):** playback, seeking, shuffle, track advancement, folder scanning, library persistence, and window and panel layout persistence.

**Confirmed working on Windows 11:** installation, Start Menu shortcut, playback, next track, shuffle, seeking, library persistence, and window layout persistence.

**Not yet tested by hand:** playlists (create, rename, delete, import, export), the track right-click menu, and MusicBrainz tag fetching. These use the same backend code as the confirmed features, so problems aren't expected, but they haven't been verified yet. **macOS** hasn't been tested at all.

**Known limitation:** on Wayland, window *position* can't be restored (Wayland doesn't allow apps to place their own windows), so Mope falls back to default placement. Window size still works.

Bug reports are welcome. Please open an issue.

## Built with

- [PySide6](https://doc.qt.io/qtforpython-6/) (Qt for Python) for the interface and playback
- [mutagen](https://mutagen.readthedocs.io/) for reading and writing tags
- [MusicBrainz](https://musicbrainz.org/) for track metadata lookups
- [Material Symbols and Material Icons](https://fonts.google.com/icons) by Google (Apache 2.0)

## License

Released under the MIT License. See [LICENSE](LICENSE).
