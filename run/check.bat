@echo off
setlocal enabledelayedexpansion
call "%~dp0_env.cmd"

rem 완료 선언 전에 한 번 돌린다. 문서 여기저기 흩어져 있던 검증을 한 줄로 묶은
rem 것이고, 커밋 훅이 못 하는 느린 검사가 여기 있다.
rem
rem 하나라도 빨간불이면 마지막에 모아서 보여준다 - 첫 실패에서 멈추면 나머지
rem 상태를 모른 채 고치게 된다.

set "FAILED="
set "DOTNET_CLI_UI_LANGUAGE=en"

echo == 완료 전 점검 ==
echo.

echo [1/3] 테스트
uv run --no-project --with pytest pytest "%REPO%\tools" -q
if errorlevel 1 set "FAILED=!FAILED! 테스트"
echo.

echo [2/3] vendor 기록 - 포인터가 kr-port 팁이고 핀이 그 조상인가
uv run --no-project python "%REPO%\tools\patch-check\patch_check.py"
if errorlevel 1 set "FAILED=!FAILED! vendor기록"
echo.


echo [3/3] 빌드 - KR(7.51)과 글로벌(7.55) 양쪽
rem **글로벌을 먼저, KR을 나중에 돌린다.** 둘이 같은 bin에 쓰기 때문에
rem 마지막 빌드가 산출물로 남는다. KR을 마지막에 두면 남는 것이 KR용이고,
rem 반대면 검사 직후 패킹이 글로벌 바인딩 DLL을 배포물로 낸다
rem (2026-08-18 실제로 그렇게 나갔다). run\pack.bat도 자기가 다시 빌드해서
rem 순서에 기대지 않지만, 여기서도 KR 상태로 두는 편이 맞다.

rem 글로벌 참조는 이 머신에 상주하지 않는다. 업데이터가 KR 호환본을 깔기
rem 때문이다(docs/dev/environment.md 4절). 없으면 건너뛰되 조용히 넘어가지 않는다.
set "GLOBAL=%LOCALAPPDATA%\Temp\dalamud-official-15.0.3.2"
if exist "%GLOBAL%\Dalamud.dll" (
  call :build "%GLOBAL%" "글로벌 7.55"
  if errorlevel 1 set "FAILED=!FAILED! 글로벌빌드"
) else (
  echo   [건너뜀] 글로벌 참조가 없다: %GLOBAL%
  echo            받는 법은 docs/dev/environment.md 4절. 글로벌 회귀는 확인 못 했다.
)

call :build "%DALAMUD_HOME%" "KR 7.51"
if errorlevel 1 set "FAILED=!FAILED! KR빌드"

echo.
if defined FAILED (
  echo == 실패:!FAILED! ==
  echo.
  if not defined FF14_NOPAUSE pause
  endlocal
  exit /b 1
)
echo == 전부 통과 ==
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 0

:build
setlocal
set "DALAMUD_HOME=%~1"
echo   %~2 ...
"%DOTNET%" build -c Release "%REPO%\vendor\ff14-accessibility\FF14Accessibility\FF14Accessibility.csproj" -v quiet --nologo
if errorlevel 1 (
  echo   [실패] %~2
  endlocal
  exit /b 1
)
echo   [통과] %~2
endlocal
exit /b 0
