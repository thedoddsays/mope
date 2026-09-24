# MOPE (Music Organizer, Player, Etc.)

This is a music organizer and player that defaults to utilizing local file structure to organize the user's library instead of ID tags. ID tags are great, but I didn't want 37 instanced of "Artist feat. *someotherperson*", I just wanted the reality which is *Artist* solely. Sounds dumb, but so few music players and organizers do this natively I just built one. 

## Setup

### Linux Mint / Ubuntu (app-menu install)

```bash
chmod +x install.sh uninstall.sh   # zip extraction sometimes drops the executable bit
./install.sh
```

This installs Mope to `~/.local/share/mope-qt` (kept separate from
`~/.local/share/mope`, which is where your music database and playlists
live — so if you ever also have the original GTK version installed, both
would share the same library data), sets up a `mope` command, and adds a
"Mope" entry to your app menu (Sound & Video category) so you can launch
it without a terminal. It'll ask for your sudo password once, to install
a couple of required system packages (including `libxcb-cursor0`, which
Qt 6.5+ needs for its Linux display backend but many systems don't have
by default).

`./uninstall.sh` removes the app, launcher, and menu entry again — it
never touches your library database or playlists.

### Windows

1. Install Python 3.10+ from [python.org](https://www.python.org/) if you
   don't already have it — during install, check **"Add python.exe to PATH"**.
2. Extract this zip somewhere convenient, e.g. `C:\Users\you\Projects\mope`.
3. Open Command Prompt or PowerShell and `cd` into that folder:
   ```
   cd C:\Users\you\Projects\mope
   ```
4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
5. Run it:
   ```
   python main.py
   ```

No MSYS2, no separate GTK or GStreamer install needed — PySide6 ships its
own bundled Qt binaries, and QtMultimedia uses Windows Media Foundation as
its native playback backend.

#### Adding it to your Start Menu

Once the steps above are working (i.e. `python main.py` runs the app
successfully), double-click **`install.bat`** in the project folder. It:

- Creates a "Mope" shortcut in your Start Menu, using `mope.ico` as
  its icon
- Points that shortcut at `pythonw.exe` (not `python.exe`), so launching
  it doesn't leave a console window open behind the app
- Doesn't move, copy, or modify your project files — the shortcut just
  points at wherever you extracted the zip, so don't delete/move that
  folder afterward without re-running `install.bat`

Double-click **`uninstall.bat`** to remove the shortcut again. Windows
may show a security prompt the first time you run either `.bat` file
(SmartScreen warning for an unsigned script) — click "More info" then
"Run anyway"; this is expected for any unsigned script you download
rather than something specific to this one.

If Windows 11's **Smart App Control** is turned on, it can block the
`.bat` file outright with no "Run anyway" option at all (stricter than
the regular SmartScreen prompt above). If that happens, either turn Smart
App Control off (Windows Security → App & browser control → Smart App
Control), or skip the `.bat` file and paste the contents of `install.ps1`
directly into an open PowerShell window instead — typing/pasting commands
yourself isn't treated the same way as running a downloaded script file.

### Linux (manual/terminal) / macOS

If you'd rather not use `install.sh`, or you're on macOS:

1. Make sure you have Python 3.10+ (`python3 --version`).
2. Extract the zip and `cd` into it.
3. Install dependencies — either directly:
   ```bash
   pip3 install -r requirements.txt --break-system-packages
   ```
   or inside a virtual environment (recommended if you don't want this
   touching system-wide packages):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. Run it:
   ```bash
   python3 main.py
   ```

### First run

Confirmed working on **Linux Mint (Cinnamon, X11)**: playback, seeking,
shuffle, sequential track advancement, folder scanning, library
persistence, and window/panel size + position persistence.

Confirmed working on **Windows 11**: install via python.org's installer,
`install.bat` Start Menu shortcut, playback, next-track, shuffle,
seeking, library persistence, and window size + position persistence.

Not tested at all on macOS.
