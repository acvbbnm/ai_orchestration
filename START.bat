@echo off
chcp 65001 >nul
title AI DEV 엔진
set "PATH=%LOCALAPPDATA%\agy\bin;%PATH%"
set "DIRECTOR=C:\Users\user\ai-dev-director-inspect"

echo ============================================
echo   AI DEV DIRECTOR - 엔진 시작
echo ============================================
echo.

if not exist "%DIRECTOR%\start-companion.ps1" (
  echo [오류] 엔진 본체를 찾을 수 없습니다: %DIRECTOR%
  pause
  exit /b 1
)

cd /d "%DIRECTOR%"
powershell -ExecutionPolicy Bypass -File ".\start-companion.ps1"

timeout /t 3 >nul
start "" http://127.0.0.1:8081

echo.
echo   ✅ 엔진 가동 완료
echo   - TRINITY 콘솔: http://127.0.0.1:8081
echo   - 콘솔 입력창에 목표를 넣으면 세 AI가 일을 시작합니다.
echo   - 이 창은 닫아도 됩니다 (서버는 백그라운드로 계속 돕니다).
echo   - 끄려면 STOP.bat 을 실행하세요.
echo.
pause
