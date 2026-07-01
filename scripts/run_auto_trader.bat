@echo off
REM Wrapper for Windows Task Scheduler: activates the project's virtual
REM environment and runs the automated screener + portfolio trading pipeline.
REM Point a scheduled task at this file (see README "Automated screener +
REM portfolio trading" section).
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python scripts\auto_trader.py %*
