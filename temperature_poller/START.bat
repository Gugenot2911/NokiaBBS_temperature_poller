@echo off
chcp 65001 >nul
title Temperature Poller API

echo ==========================================
echo Temperature Poller API Server
echo ==========================================
echo.

cd /d %%~dp0

REM Настройки по умолчанию
set HOST=0.0.0.0
set PORT=8000
set LOG_LEVEL=info

REM Передача параметров командной строки
python run_api.py %%*

echo.
echo ==========================================
echo Сервер остановлен
echo Нажмите любую клавишу для выхода...
pause >nul
