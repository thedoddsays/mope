#!/bin/bash
# ============================================================
#  Mope - Music Organizer Player Etc. (Qt/PySide6 version)
#  Installer for Linux Mint 21/22 (Ubuntu 22.04/24.04 base)
#
#  Installs to ~/.local - no root required for the app itself.
#  sudo is only used for apt (system Qt/media packages).
#
#  App code lives at ~/.local/share/mope-qt internally, kept separate
#  from your music library database/playlists at ~/.local/share/mope/
#  (hardcoded in library.py/playlist_manager.py) so this install script's
#  rsync --delete step can never touch your actual library data.
# ============================================================

set -e

MOPE_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOPE_INSTALL="$HOME/.local/share/mope-qt"
MOPE_BIN="$HOME/.local/bin"
MOPE_APPS="$HOME/.local/share/applications"
MOPE_ICONS="$HOME/.local/share/icons/hicolor/256x256/apps"

echo ""
echo "  Installing Mope - Music Organizer Player Etc."
echo "  ========================================================"
echo ""

# -- 1. System packages --------------------------------------------------
echo "-> Installing system dependencies (requires sudo for apt)..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3 \
    python3-full \
    python3-venv \
    python3-pip \
    libxcb-cursor0 \
    libxkbcommon-x11-0

# -- 2. Copy app files ----------------------------------------------------
echo ""
echo "-> Installing Mope to $MOPE_INSTALL ..."
mkdir -p "$MOPE_INSTALL"
rsync -a --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='install.sh' \
    --exclude='uninstall.sh' \
    "$MOPE_SRC/" "$MOPE_INSTALL/"

# -- 3. Virtual environment -----------------------------------------------
echo ""
echo "-> Creating Python virtual environment..."
python3 -m venv "$MOPE_INSTALL/venv"

echo ""
echo "-> Installing Python packages..."
"$MOPE_INSTALL/venv/bin/pip" install --upgrade pip --quiet
"$MOPE_INSTALL/venv/bin/pip" install -r "$MOPE_INSTALL/requirements.txt"

# -- 4. Launcher script -----------------------------------------------------
echo ""
echo "-> Creating launcher at $MOPE_BIN/mope ..."
mkdir -p "$MOPE_BIN"
cat > "$MOPE_BIN/mope" << LAUNCHER
#!/bin/bash
exec "$MOPE_INSTALL/venv/bin/python3" "$MOPE_INSTALL/main.py" "\$@"
LAUNCHER
chmod +x "$MOPE_BIN/mope"

if ! echo "$PATH" | grep -q "$MOPE_BIN"; then
    echo ""
    echo "  WARNING: $MOPE_BIN is not in your PATH."
    echo "      Add this line to your ~/.bashrc or ~/.profile:"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# -- 5. Icon ----------------------------------------------------------------
echo ""
echo "-> Installing icon..."
mkdir -p "$MOPE_ICONS"
cp "$MOPE_SRC/mope.png" "$MOPE_ICONS/mope.png"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# -- 6. Desktop entry ---------------------------------------------------------
echo ""
echo "-> Installing Mint menu entry..."
mkdir -p "$MOPE_APPS"
cat > "$MOPE_APPS/mope.desktop" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Mope
GenericName=Music Player
Comment=Music Organizer Player Etc. - browse by folder, play and tag your music
Exec=$MOPE_BIN/mope
Icon=mope
Terminal=false
Categories=AudioVideo;Audio;Player;
Keywords=music;player;organizer;audio;flac;mp3;playlist;
StartupNotify=true
StartupWMClass=mope
DESKTOP
chmod +x "$MOPE_APPS/mope.desktop"

update-desktop-database "$MOPE_APPS" 2>/dev/null || true

# -- Done ---------------------------------------------------------------------
echo ""
echo "  Mope installed successfully!"
echo ""
echo "  Launch from the Mint menu (Sound & Video -> Mope)"
echo "  or from a terminal:"
echo "      mope"
echo ""
