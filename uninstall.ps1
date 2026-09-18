# Mope - Windows Start Menu uninstaller
# Removes the Start Menu shortcut created by install.ps1. Does not touch
# your Python packages, project files, or your music library database
# (which lives under %USERPROFILE%\.local\share\mope).

$ShortcutPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Mope.lnk"

if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Removed 'Mope' from the Start Menu." -ForegroundColor Green
} else {
    Write-Host "No Start Menu shortcut found (already removed?)." -ForegroundColor Yellow
}
