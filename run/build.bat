@echo off
setlocal
call "%~dp0_env.cmd"

rem KR 패치가 적용된 vendor 클론을 빌드하고 devPlugins에 배포한다.
rem AutomaticReloading이 켜져 있어서 게임이 떠 있어도 덮어쓰면 반영된다
rem (docs/dev/kr-runtime.md 7절).
rem
rem 여기는 **개발 상태**를 만든다. 사용자에게 나가는 정식 설치는 설치기가
rem installedPlugins에 넣는다. 둘은 상호 배타적이다 - 같이 있으면 Dalamud가
rem 같은 모드를 두 번 적재하고, 명령과 단축키가 겹친다. 그래서 이 배치는
rem 정식 설치본을 먼저 걷어낸다.

set "PROJ=%REPO%\vendor\ff14-accessibility\FF14Accessibility\FF14Accessibility.csproj"
set "OUTZIP=%REPO%\vendor\ff14-accessibility\FF14Accessibility\bin\Release\net10.0-windows\FF14Accessibility\latest.zip"
set "TARGET=%KR_DEVPLUGINS%\FF14Accessibility"

echo == 접근성 모드 빌드와 배포 ==
echo.

if not exist "%DOTNET%" (
  echo [실패] .NET SDK를 못 찾았다: %DOTNET%
  echo   PATH의 dotnet은 런타임만 있어서 못 쓴다. docs/dev/environment.md 2절.
  goto :fail
)
if not defined DALAMUD_HOME (
  echo [실패] Dalamud hook 폴더가 없다: %KR_PROFILE%\addon\Hooks
  echo   업데이터에서 Check Update를 먼저 돌린다. docs/dev/kr-runtime.md 5절.
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

rem kr-port 아닌 소스를 조용히 빌드하면 KR에서 안 뜨는 물건이 나온다.
rem 갓 클론은 vendor가 브랜치 없이 떠 있다 - 세우기까지 도구가 한다.
rem kr-port 밖의 다른 브랜치면 여기서 거부된다.
uv run --no-project python "%REPO%\tools\kr-setup\vendor_setup.py"
if errorlevel 1 (
  echo [실패] vendor가 빌드할 상태가 아니다. 위 안내대로 정리하고 다시.
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
set "INSTALLED=%KR_INSTALLEDPLUGINS%\FF14Accessibility"
if exist "%INSTALLED%" (
  echo 정식 설치본을 걷어낸다: %INSTALLED%
  echo   되돌리려면 dist\FF14AccessibilityInstaller-KR.exe를 다시 실행한다.
  rd /s /q "%INSTALLED%"
)

echo 배포: %TARGET%
if not exist "%TARGET%" mkdir "%TARGET%"
7z x -y -o"%TARGET%" "%OUTZIP%" >nul
if errorlevel 1 (
  echo [실패] 압축을 못 풀었다. 게임이 DLL을 잠갔을 수 있다.
  goto :fail
)

rem 설치기가 정식 경로로 옮기면서 dev 항목을 지웠을 수 있다. 없으면 심고,
rem 이미 있으면 손대지 않는다 - 게임이 떠 있는 동안 설정을 쓰면 Dalamud가
rem 종료할 때 자기 상태로 덮어써서 우리 것이 사라진다.
uv run --no-project python "%REPO%\tools\kr-setup\seed_devplugin.py" "%KR_CONFIG%" "%TARGET%\FF14Accessibility.dll" FF14Accessibility
if errorlevel 1 (
  echo [실패] dev 플러그인 설정을 심지 못했다.
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
