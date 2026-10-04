@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
echo [CXH FP] Запуск из "%~dp0"
echo [CXH FP] Остановить: Ctrl+C в этом окне, tools\Stop.bat или «Инструменты → Выключить» в Telegram.
if not exist "%~dp0.venv\Scripts\python.exe" goto missing
"%~dp0.venv\Scripts\python.exe" "%~dp0start.py" %*
set "START_RESULT=%ERRORLEVEL%"
if "%START_RESULT%"=="0" exit /b 0
echo.
echo [CXH FP] Запуск завершился с кодом %START_RESULT%.
echo Причина показана выше. Если подробностей нет, запустите Setup.bat для проверки Python и зависимостей.
echo Журнал бота, если он создан: "%~dp0logs\log.log"
pause
exit /b %START_RESULT%
:missing
echo [CXH FP] Окружение Python не найдено. Сначала запустите Setup.bat.
pause
exit /b 1
