@echo off
REM Wrapper for Windows Task Scheduler: activates the project's virtual
REM environment and runs the watchlist scanner. Point a scheduled task at
REM this file (see README "Automating the watchlist scan" section).
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python scripts\watchlist_scanner.py %*
