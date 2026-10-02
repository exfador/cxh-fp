@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
echo [CXH FP] Проверка и настройка из "%~dp0"
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
if "%SETUP_RESULT%"=="0" echo [CXH FP] Проверка или настройка завершена успешно. Для запуска бота откройте Start.bat.
if not "%SETUP_RESULT%"=="0" echo [CXH FP] Настройка завершилась с кодом %SETUP_RESULT%. Причина показана выше. Требуется Python 3.11.
pause
exit /b %SETUP_RESULT%
