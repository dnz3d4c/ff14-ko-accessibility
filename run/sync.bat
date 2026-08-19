@echo off
setlocal
call "%~dp0_env.cmd"

rem 업스트림이 얼마나 앞서 갔는지 본다. 받아오기만 하고 아무것도 안 옮긴다.
rem
rem 실제로 올리는 것은 인자가 필요하다 - 태그를 명시하게 해서, 손이 미끄러져
rem 최신으로 끌려가는 일이 없게 한다.
rem
rem   run\sync.bat            점검만
rem   run\sync.bat v5.87      v5.87로 올린다 (패치가 깨끗이 붙을 때만)
rem
rem 절차와 판단 기준: docs/upstream/sync.md

set "TOOL=%REPO%\tools\upstream-sync\upstream_sync.py"

if "%~1"=="" (
  uv run --no-project python "%TOOL%"
) else (
  uv run --no-project python "%TOOL%" --to %1
)
set "CODE=%ERRORLEVEL%"

echo.
if not defined FF14_NOPAUSE pause
endlocal & exit /b %CODE%
