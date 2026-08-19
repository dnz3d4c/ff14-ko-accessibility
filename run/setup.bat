@echo off
setlocal
call "%~dp0_env.cmd"

rem 최초 1회. 프로필의 빠진 조각을 만들고 접근성 모드를 설정에 심는다.
rem docs/dev/kr-runtime.md 3절, 7절.
rem
rem **여기가 심는 것은 개발 경로다**(devPlugins). 사용자에게 나가는 정식
rem 설치는 설치기가 installedPlugins에 넣는다. 둘은 동시에 있으면 안 된다 -
rem 자세한 것은 kr-runtime-setup.md 7절.
rem
rem **vnavmesh는 여기서 다루지 않는다.** 그건 설치기가 갖는다 - 업스트림이
rem puni.sh 매니페스트에서 최신을 받아 버전을 비교하는 방식이고, 우리도 그걸
rem 그대로 따른다. 손으로 받아 심으면 그 버전에 묶여 갱신이 멈춘다.
rem
rem **게임을 끈 상태에서 돌린다.** Dalamud는 종료할 때 설정을 저장하므로
rem 켜져 있으면 여기서 쓴 것이 덮인다.

echo == KR 프로필 최초 설정 ==
echo.
echo 게임과 업데이터를 모두 끈 상태여야 한다.
echo 켜져 있으면 지금 끄고, 끝났으면 엔터.
if not defined FF14_NOPAUSE pause
echo.

if not exist "%KR_PROFILE%" (
  echo [실패] KR 프로필이 없다: %KR_PROFILE%
  echo   업데이터를 한 번 실행해 Check Update를 돌린다.
  goto :fail
)

echo 1/3  빠진 폴더를 만든다.
if not exist "%KR_PROFILE%\installedPlugins" mkdir "%KR_PROFILE%\installedPlugins"
if not exist "%KR_DEVPLUGINS%" mkdir "%KR_DEVPLUGINS%"

echo 2/3  DALAMUD_RUNTIME 환경변수를 건다.
if not defined DALAMUD_RUNTIME (
  setx DALAMUD_RUNTIME "%ProgramFiles%\dotnet" >nul
  echo      걸었다. 게임을 새로 켜야 반영된다.
) else (
  echo      이미 있다: %DALAMUD_RUNTIME%
)

echo 3/3  접근성 모드를 설정에 심는다.
if not exist "%KR_DEVPLUGINS%\FF14Accessibility\FF14Accessibility.dll" (
  echo [실패] 먼저 run\build.bat으로 빌드·배포한다.
  goto :fail
)
uv run --no-project python "%REPO%\tools\kr-setup\seed_devplugin.py" "%KR_CONFIG%" "%KR_DEVPLUGINS%\FF14Accessibility\FF14Accessibility.dll" FF14Accessibility
if errorlevel 1 goto :fail

echo.
if exist "%KR_DEVPLUGINS%\vnavmesh\vnavmesh.dll" (
  echo vnavmesh는 이미 있다. 갱신은 설치기가 맡는다 - run\pack.bat
) else (
  echo 자동 이동을 쓰려면 vnavmesh가 필요하다. 설치기가 받아 준다 - run\pack.bat
)
echo.
echo 끝. 이제 run\play.bat으로 켠다.
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 0

:fail
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 1
