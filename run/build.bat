@echo off
setlocal
call "%~dp0_env.cmd"

rem KR 패치가 적용된 vendor 클론을 빌드하고 devPlugins에 배포한다.
rem AutomaticReloading이 켜져 있어서 게임이 떠 있어도 덮어쓰면 반영된다
rem (docs/kr-runtime-setup.md 7절).

set "PROJ=%REPO%\vendor\ff14-accessibility\FF14Accessibility\FF14Accessibility.csproj"
set "OUTZIP=%REPO%\vendor\ff14-accessibility\FF14Accessibility\bin\Release\net10.0-windows\FF14Accessibility\latest.zip"
set "TARGET=%KR_DEVPLUGINS%\FF14Accessibility"

echo == 접근성 모드 빌드와 배포 ==
echo.

if not exist "%DOTNET%" (
  echo [실패] .NET SDK를 못 찾았다: %DOTNET%
  echo   PATH의 dotnet은 런타임만 있어서 못 쓴다. docs/environment.md 2절.
  goto :fail
)
if not defined DALAMUD_HOME (
  echo [실패] Dalamud hook 폴더가 없다: %KR_PROFILE%\addon\Hooks
  echo   업데이터에서 Check Update를 먼저 돌린다. docs/kr-runtime-setup.md 5절.
  goto :fail
)
if not exist "%PROJ%" (
  echo [실패] 업스트림 클론이 없다: %PROJ%
  echo   클론과 패치 적용은 overlay/patches/README.md.
  goto :fail
)
rem 7z은 워크스페이스 표준 압축 도구다. PowerShell의 Expand-Archive는
rem -NoProfile에서 모듈 자동 로드에 실패한다(2026-08-18 실측).
where 7z >nul 2>&1
if errorlevel 1 (
  echo [실패] 7z이 PATH에 없다.
  echo   설치: scoop install 7zip
  goto :fail
)

rem 패치가 안 붙은 main을 조용히 빌드하면 KR에서 안 뜨는 물건이 나온다.
for /f "delims=" %%B in ('git -C "%REPO%\vendor\ff14-accessibility" rev-parse --abbrev-ref HEAD 2^>nul') do set "BRANCH=%%B"
if /i not "%BRANCH%"=="kr-port" (
  echo [실패] vendor 클론이 kr-port 브랜치가 아니다. 현재: %BRANCH%
  echo   KR 패치 없이 빌드하면 게임 안에서 안 뜬다. overlay/patches/README.md 참조.
  goto :fail
)

rem dotnet은 UTF-8로 출력하는데 콘솔은 cp949라 한국어 메시지가 깨진다.
rem 깨진 글자보다 영어가 낫다 - 스크린리더가 읽을 수 있다.
set "DOTNET_CLI_UI_LANGUAGE=en"
echo Dalamud: %DALAMUD_HOME%
echo.
set "DALAMUD_HOME=%DALAMUD_HOME%"
"%DOTNET%" build -c Release "%PROJ%"
if errorlevel 1 (
  echo.
  echo [실패] 빌드가 깨졌다. 위 오류를 본다.
  goto :fail
)

if not exist "%OUTZIP%" (
  echo [실패] 산출물이 없다: %OUTZIP%
  goto :fail
)

echo.
echo 배포: %TARGET%
if not exist "%TARGET%" mkdir "%TARGET%"
7z x -y -o"%TARGET%" "%OUTZIP%" >nul
if errorlevel 1 (
  echo [실패] 압축을 못 풀었다. 게임이 DLL을 잠갔을 수 있다.
  goto :fail
)

echo.
echo 끝. 게임이 떠 있으면 몇 초 안에 다시 적재된다.
echo 확인: run\log.bat
echo.
endlocal
exit /b 0

:fail
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 1
