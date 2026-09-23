@echo off
setlocal
cd /d "%~dp0"

if not exist "%~dp0runtime\python.exe" (
  echo D4LF runtime was not found. Extract the complete ZIP before running this file.
  pause
  exit /b 1
)

if not exist "%~dp0src\main.py" (
  echo D4LF source files were not found. Extract the complete ZIP before running this file.
  pause
  exit /b 1
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

"%~dp0runtime\python.exe" -m src.main
if errorlevel 1 (
  echo.
  echo D4LF exited with an error. Please copy the message above when reporting the issue.
  pause
  exit /b 1
)
