@echo off
chcp 65001 >nul
title AI DEV 엔진 중지
set "DIRECTOR=C:\Users\user\ai-dev-director-inspect"
cd /d "%DIRECTOR%"
powershell -ExecutionPolicy Bypass -File ".\stop-companion.ps1"
echo.
echo   엔진을 중지했습니다.
echo.
pause
