@echo off
setlocal
call "%~dp0_env.cmd"

rem 게임을 띄우고, 로그인이 끝나면 Dalamud를 붙인다.
rem 업데이터는 게임을 실행하지 않는다 - 돌고 있는 프로세스에 주입할 뿐이라
rem 순서가 고정이다. docs/kr-runtime-setup.md §9.

echo == FF14 한국 서버 + 접근성 모드 ==
echo.

if not exist "%GAME_LNK%" (
  echo [실패] 게임 바로가기를 못 찾았다:
  echo   %GAME_LNK%
  goto :fail
)
if not exist "%UPDATER%" (
  echo [실패] KR Dalamud 업데이터를 못 찾았다:
  echo   %UPDATER%
  echo   설치 절차는 docs/kr-runtime-setup.md 2절.
  goto :fail
)

echo 1/3  게임을 켠다.
start "" "%GAME_LNK%"
echo.
echo 2/3  런처에서 로그인하고, 게임에 캐릭터로 접속할 때까지 기다린다.
echo      접속이 끝나면 이 창으로 돌아와 엔터를 누른다.
echo.
if not defined FF14_NOPAUSE pause

echo.
echo 3/3  업데이터를 켠다. 창에서 "달라무드 적용"을 누른다.
start "" "%UPDATER%" --no-elevate
echo.
echo 적용한 뒤 확인하려면: run\log.bat
echo.
endlocal
exit /b 0

:fail
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 1
