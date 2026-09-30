@echo off
setlocal
set "PYTHONUTF8=1"
cd /d "%~dp0"
if defined COXERHUB_PYTHON goto custom
py -3.11 -c "import sys" >nul 2>&1
if errorlevel 1 goto fallback
py -3.11 "%~dp0setup.py" %*
goto finish
:fallback
python "%~dp0setup.py" %*
goto finish
:custom
"%COXERHUB_PYTHON%" "%~dp0setup.py" %*
:finish
set "SETUP_RESULT=%ERRORLEVEL%"
if not "%SETUP_RESULT%"=="0" echo Setup failed. Python 3.11 is required.
pause
exit /b %SETUP_RESULT%
