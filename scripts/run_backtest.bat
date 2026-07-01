@echo off
REM Wrapper for running the backtester on Windows. Activates the project's
REM virtual environment and passes through any arguments, e.g.:
REM   scripts\run_backtest.bat --start-date 2026-01-01 --end-date 2026-03-31
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python scripts\backtest.py %*
