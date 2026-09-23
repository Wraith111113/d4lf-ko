@echo off
setlocal
cd /d "%~dp0"

echo [D4LF koKR] Preparing the Korean build...

where uv >nul 2>nul
if errorlevel 1 (
  echo Installing the required runtime with Windows Package Manager...
  winget install --id astral-sh.uv -e --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo Failed to install uv. Install it manually and run this file again.
    echo https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
  )
  set "PATH=%USERPROFILE%\.local\bin;%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
)

set "CONFIG_DIR=%USERPROFILE%\.d4lf"
set "CONFIG_FILE=%CONFIG_DIR%\params.ini"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
if not exist "%CONFIG_FILE%" type nul > "%CONFIG_FILE%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p=$env:CONFIG_FILE; $c=[IO.File]::ReadAllText($p);" ^
  "if ($c -match '(?im)^\s*language\s*=') {" ^
  "  $c=[regex]::Replace($c,'(?im)^\s*language\s*=.*$','language = koKR');" ^
  "} elseif ($c -match '(?im)^\[general\]\s*$') {" ^
  "  $c=[regex]::Replace($c,'(?im)^\[general\]\s*$','$0'+[Environment]::NewLine+'language = koKR',1);" ^
  "} else {" ^
  "  if ($c.Length -gt 0 -and -not $c.EndsWith([Environment]::NewLine)) { $c += [Environment]::NewLine };" ^
  "  $c += '[general]'+[Environment]::NewLine+'language = koKR'+[Environment]::NewLine;" ^
  "};" ^
  "[IO.File]::WriteAllText($p,$c,(New-Object Text.UTF8Encoding($false)))"
if errorlevel 1 (
  echo Failed to enable Korean mode.
  pause
  exit /b 1
)

echo Installing or updating D4LF dependencies...
uv sync
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

echo Starting D4LF v10.0.4 in Korean mode...
uv run python -m src.main
if errorlevel 1 pause
