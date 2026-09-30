@echo off
setlocal
set "PYTHONUTF8=1"
cd /d "%~dp0"
if not exist "%~dp0.venv\Scripts\python.exe" goto missing
"%~dp0.venv\Scripts\python.exe" "%~dp0start.py" %*
set "START_RESULT=%ERRORLEVEL%"
if "%START_RESULT%"=="0" exit /b 0
pause
exit /b %START_RESULT%
:missing
echo Run Setup.bat first to prepare Python 3.11 and dependencies.
pause
exit /b 1
