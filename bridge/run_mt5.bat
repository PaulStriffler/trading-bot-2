@echo off
REM Windows launcher for the FTMO/MT5 live bridge.
REM Place this file next to mt5_sync.py and double-click to start.

cd /d "%~dp0\.."
echo Installing dependencies (first run only)...
pip install -q MetaTrader5 pyyaml

echo.
echo Starting MT5 live bridge...
echo Press Ctrl+C to stop.
echo.
python -m bridge.mt5_sync
pause
