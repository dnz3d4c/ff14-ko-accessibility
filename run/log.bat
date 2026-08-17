@echo off
setlocal
call "%~dp0_env.cmd"

rem 마지막 세션이 정상인지 판정한다. 25만 자를 눈으로 훑지 않기 위한 것이라
rem 로그를 그대로 뱉지 않고 판정만 낸다. 원문이 필요하면 아래 경로를 연다.

if not exist "%KR_LOG%" (
  echo [실패] 로그가 없다: %KR_LOG%
  echo   게임에 Dalamud를 한 번도 안 붙였다는 뜻이다. run\play.bat
  goto :end
)

uv run --no-project python "%REPO%\tools\kr-setup\check_log.py" "%KR_LOG%"

echo.
echo 로그 원문: %KR_LOG%

:end
echo.
if not defined FF14_NOPAUSE pause
endlocal
