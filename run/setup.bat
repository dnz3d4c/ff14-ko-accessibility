@echo off
setlocal
call "%~dp0_env.cmd"

rem 최초 1회. 프로필의 빠진 조각을 만들고 dev 플러그인 두 개를 설정에 심는다.
rem docs/kr-runtime-setup.md 3절, 7절, 8절.
rem
rem **게임을 끈 상태에서 돌린다.** Dalamud는 종료할 때 설정을 저장하므로
rem 켜져 있으면 여기서 쓴 것이 덮인다.

echo == KR 프로필 최초 설정 ==
echo.
echo 게임과 업데이터를 모두 끈 상태여야 한다.
echo 켜져 있으면 지금 끄고, 끝났으면 엔터.
pause
echo.

if not exist "%KR_PROFILE%" (
  echo [실패] KR 프로필이 없다: %KR_PROFILE%
  echo   업데이터를 한 번 실행해 Check Update를 돌린다.
  goto :fail
)

echo 1/4  빠진 폴더를 만든다.
if not exist "%KR_PROFILE%\installedPlugins" mkdir "%KR_PROFILE%\installedPlugins"
if not exist "%KR_DEVPLUGINS%" mkdir "%KR_DEVPLUGINS%"

echo 2/4  DALAMUD_RUNTIME 환경변수를 건다.
if not defined DALAMUD_RUNTIME (
  setx DALAMUD_RUNTIME "%ProgramFiles%\dotnet" >nul
  echo      걸었다. 게임을 새로 켜야 반영된다.
) else (
  echo      이미 있다: %DALAMUD_RUNTIME%
)

echo 3/4  접근성 모드를 설정에 심는다.
if not exist "%KR_DEVPLUGINS%\FF14Accessibility\FF14Accessibility.dll" (
  echo [실패] 먼저 run\build.bat으로 빌드·배포한다.
  goto :fail
)
uv run --no-project python "%REPO%\tools\kr-setup\seed_devplugin.py" "%KR_CONFIG%" "%KR_DEVPLUGINS%\FF14Accessibility\FF14Accessibility.dll" FF14Accessibility
if errorlevel 1 goto :fail

echo 4/4  vnavmesh를 설정에 심는다.
if not exist "%KR_DEVPLUGINS%\vnavmesh\vnavmesh.dll" (
  echo      vnavmesh가 없다 - 자동 이동만 빠진 채로 끝낸다.
  echo      받는 절차는 docs/kr-runtime-setup.md 8절.
) else (
  uv run --no-project python "%REPO%\tools\kr-setup\seed_devplugin.py" "%KR_CONFIG%" "%KR_DEVPLUGINS%\vnavmesh\vnavmesh.dll" vnavmesh
  if errorlevel 1 goto :fail
)

echo.
echo 끝. 이제 run\play.bat으로 켠다.
echo.
pause
endlocal
exit /b 0

:fail
echo.
pause
endlocal
exit /b 1
