@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
where py >nul 2>nul
if errorlevel 1 (
  python server.py
) else (
  py -3 server.py
)
if errorlevel 1 pause
