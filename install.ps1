# Mope - Windows Start Menu installer
# Creates a Start Menu shortcut that launches the app without a console
# window (via pythonw.exe) and uses mope.ico as its icon.

$ErrorActionPreference = "Stop"

$ProjectDir = $PSScriptRoot
$IconPath   = Join-Path $ProjectDir "mope.ico"
$MainScript = Join-Path $ProjectDir "main.py"

Write-Host ""
Write-Host "  Installing Mope to your Start Menu..."
Write-Host ""

# Find pythonw.exe - it ships alongside python.exe in the same install,
# and runs the app without a console window staying open behind it.
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "  ERROR: 'python' was not found on PATH." -ForegroundColor Red
    Write-Host "  Install Python from python.org first (see README.md), then try again." -ForegroundColor Red
    exit 1
}

$PythonDir  = Split-Path $pythonCmd.Source -Parent
$PythonwExe = Join-Path $PythonDir "pythonw.exe"

if (-not (Test-Path $PythonwExe)) {
    Write-Host "  WARNING: pythonw.exe not found next to python.exe." -ForegroundColor Yellow
    Write-Host "  Falling back to python.exe - a console window will stay open behind the app." -ForegroundColor Yellow
    $PythonwExe = $pythonCmd.Source
}

if (-not (Test-Path $MainScript)) {
    Write-Host "  ERROR: main.py not found in $ProjectDir" -ForegroundColor Red
    exit 1
}

$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$ShortcutPath = Join-Path $StartMenuDir "Mope.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath       = $PythonwExe
$Shortcut.Arguments        = "`"$MainScript`""
$Shortcut.WorkingDirectory = $ProjectDir
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}
$Shortcut.Description = "Mope - Music Organizer Player Etc."
$Shortcut.Save()

Write-Host "  Done! 'Mope' is now in your Start Menu." -ForegroundColor Green
Write-Host "  You can search for it by name, or find it under Start > All apps." -ForegroundColor Green
Write-Host ""
