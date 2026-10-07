@echo off
setlocal
cd /d "%~dp0"
if not exist ".mcp-venv\Scripts\python.exe" (
    python -m venv .mcp-venv
    if errorlevel 1 goto failed
)
".mcp-venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-mcp.txt
if errorlevel 1 goto failed
echo MCP setup complete. See MCP.md for connection settings.
exit /b 0
:failed
echo MCP setup failed. Install Python 3.11 or later and check your internet connection.
exit /b 1
