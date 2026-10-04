@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0.."
if not exist "%~dp0..\.venv\Scripts\python.exe" goto missing
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\main.py" stop
set "STOP_RESULT=%ERRORLEVEL%"
timeout /t 3 /nobreak >nul 2>nul
exit /b %STOP_RESULT%
:missing
echo [CXH FP] Окружение Python не найдено. Сначала запустите Setup.bat.
pause
exit /b 1
