@echo off
setlocal
call "%~dp0_env.cmd"

rem 업데이터와 게임을 함께 띄운다. 붙이는 것은 업데이터가 알아서 한다 -
rem 설정의 AutoApply가 참이고 게임 프로세스를 1초 간격으로 감시한다.
rem 근거와 실측은 docs/dev/kr-runtime.md §9.
rem
rem **개발용이다.** 사용자에게 나가는 것은 설치 프로그램이 놓는
rem `FF14 접근성 모드로 플레이` 바로가기다(vendor/.../Launcher/Play.cs).

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
  echo   설치 절차는 docs/dev/kr-runtime.md 2절.
  goto :fail
)

rem 업데이터를 먼저 띄운다. 순서가 필수는 아니고 - 게임이 먼저 떠 있어도
rem 감시가 찾아 붙는다 - 그쪽이 자기 갱신을 확인하는 시간을 벌기 위한 것이다.
rem
rem **--no-elevate를 붙이지 않는다.** KR 클라이언트가 관리자 권한으로 뜨므로
rem 일반 권한에 고정된 업데이터의 OpenProcess는 구조적으로 실패한다
rem (인젝터 로그의 Win32Exception 5). docs/status.md §5-8.
echo 1/2  업데이터를 켠다.
start "" "%UPDATER%"
echo.
echo 2/2  게임을 켠다. 런처에서 로그인하면 모드가 알아서 붙는다.
start "" "%GAME_LNK%"
echo.
echo 붙었는지 확인하려면: run\log.bat
echo.
endlocal
exit /b 0

:fail
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 1
