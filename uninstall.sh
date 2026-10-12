#!/bin/bash
# ============================================================
#  Mope - Uninstaller
#
#  Removes the app files, launcher, and menu entry. Your music library
#  database and playlists live at ~/.local/share/mope/ and are never
#  touched by this script.
# ============================================================

MOPE_INSTALL="$HOME/.local/share/mope-qt"
MOPE_BIN="$HOME/.local/bin/mope"
MOPE_DESKTOP="$HOME/.local/share/applications/mope.desktop"

echo ""
echo "  Uninstalling Mope..."
echo ""

echo "-> Removing app files..."
rm -rf "$MOPE_INSTALL"

echo "-> Removing launcher..."
rm -f "$MOPE_BIN"

echo "-> Removing menu entry..."
rm -f "$MOPE_DESKTOP"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "  Mope uninstalled."
echo ""
echo "  Your library database and playlists are untouched, at:"
echo "      $HOME/.local/share/mope"
echo ""
