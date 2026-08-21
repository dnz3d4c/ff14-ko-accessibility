@echo off
setlocal
call "%~dp0_env.cmd"

rem 배포 폴더를 만든다. 결과는 파일 두 개다 - 설치기 EXE와 플러그인 zip.
rem 설치기는 자기 옆의 zip을 먼저 보므로 그 폴더를 통째로 옮기면 어디서든
rem 돈다. 받는 쪽에 .NET 설치를 요구하지 않으려고 자체 포함으로 낸다.
rem
rem **플러그인을 여기서 다시 빌드한다.** bin에 있는 것을 그냥 담으면 안 된다 -
rem run\check.bat이 같은 소스를 KR(7.51)과 글로벌(7.55)로 두 번 빌드하고 둘 다
rem 같은 bin에 쓰는데, 마지막이 글로벌이다. 그대로 담으면 적재는 되고 첫
rem 장비세트 호출에서 죽는 물건이 나간다(2026-08-18 실제로 그렇게 나갔다).

set "INSTALLER=%REPO%\vendor\ff14-accessibility\Installer\FF14AccessibilityInstaller.csproj"
set "PUBLISH=%REPO%\vendor\ff14-accessibility\Installer\bin\Release\net8.0-windows\win-x64\publish"
set "PLUGINZIP=%REPO%\vendor\ff14-accessibility\FF14Accessibility\bin\Release\net10.0-windows\FF14Accessibility\latest.zip"
set "LAUNCHER=%REPO%\vendor\ff14-accessibility\Launcher\FF14AccessibilityPlay.csproj"
set "LAUNCHEREXE=%REPO%\vendor\ff14-accessibility\Launcher\bin\Release\net10.0-windows\win-x64\publish\FF14AccessibilityPlay.exe"
set "OUT=%REPO%\dist"

echo == 배포 폴더 만들기 ==
echo.

if not exist "%DOTNET%" (
  echo [실패] .NET SDK를 못 찾았다: %DOTNET%
  goto :fail
)
if not defined DALAMUD_HOME (
  echo [실패] Dalamud hook 폴더가 없다: %KR_PROFILE%\addon\Hooks
  goto :fail
)

set "DOTNET_CLI_UI_LANGUAGE=en"
echo 1/6  플러그인을 KR(7.51)로 다시 빌드한다.
set "PLUGINPROJ=%REPO%\vendor\ff14-accessibility\FF14Accessibility\FF14Accessibility.csproj"
"%DOTNET%" build -c Release "%PLUGINPROJ%" -v quiet --nologo
if errorlevel 1 (
  echo [실패] 플러그인 빌드가 깨졌다.
  goto :fail
)
if not exist "%PLUGINZIP%" (
  echo [실패] 산출물이 없다: %PLUGINZIP%
  goto :fail
)

echo.
echo 2/6  게임과 업데이터를 함께 띄우는 런처를 낸다.
rem **설치기보다 먼저다.** 설치기가 이 EXE를 리소스로 품고 나가므로, 순서가
rem 뒤바뀌면 옛 런처가 배포물에 실린다. 없으면 설치기 빌드가 아예 깨진다 -
rem csproj의 EmbeddedResource에 조건을 안 걸어 둔 것이 그래서다.
rem
rem 프레임워크 종속이다. 설치기가 .NET 10을 먼저 보장하므로 런타임을 한 벌
rem 더 싣지 않는다.
"%DOTNET%" publish -c Release "%LAUNCHER%" -v quiet --nologo
if errorlevel 1 (
  echo [실패] 런처 빌드가 깨졌다.
  goto :fail
)
if not exist "%LAUNCHEREXE%" (
  echo [실패] 런처 산출물이 없다: %LAUNCHEREXE%
  goto :fail
)

echo.
echo 3/6  설치기를 자체 포함 단일 EXE로 낸다. 몇 분 걸린다.
"%DOTNET%" publish -c Release "%INSTALLER%"
if errorlevel 1 (
  echo [실패] 설치기 빌드가 깨졌다.
  goto :fail
)

echo.
echo 4/6  배포 폴더에 모은다.
if not exist "%OUT%" mkdir "%OUT%"
copy /y "%PUBLISH%\FF14AccessibilityInstaller-KR.exe" "%OUT%\" >nul
if errorlevel 1 goto :fail
copy /y "%PLUGINZIP%" "%OUT%\FF14Accessibility.zip" >nul
if errorlevel 1 goto :fail

rem 안내 문서 둘도 같이 나간다. 설치의 첫 단계가 이걸 읽는 것인데, 저장소에만
rem 두면 받는 사람은 무엇부터 눌러야 하는지 알 길이 없다.
rem
rem **여기에 줄을 더하는 것만으로는 사용자에게 안 닿는다.** 받는 사람이 푸는
rem 아카이브는 tools\release-manifest 의 USER_FILES 가 담고, 거기 없으면
rem 파일이 dist 에만 남는다. 그 빠짐은 오류가 아니라 침묵이다.
copy /y "%REPO%\overlay\ko\README.ko.md" "%OUT%\사용 안내.md" >nul
if errorlevel 1 goto :fail
copy /y "%REPO%\overlay\ko\KEYS.ko.md" "%OUT%\단축키 목록.md" >nul
if errorlevel 1 goto :fail

echo.
echo 5/6  릴리스에 같이 올릴 매니페스트를 산출물에서 만든다.
rem 자기 갱신은 installer.json을, Dalamud 커스텀 저장소는 repo.json을 읽는다.
rem 릴리스에 이 둘이 안 올라가면 받는 쪽은 오류가 아니라 "새 판이 없다"로
rem 읽는다. 값은 손으로 안 적고 방금 낸 산출물에서 뽑는다.
uv run --no-project python "%REPO%\tools\release-manifest\release_manifest.py"
if errorlevel 1 (
  echo [실패] 릴리스 매니페스트를 못 만들었다. 위 이유를 본다.
  goto :fail
)

echo.
echo 6/6  낸 것을 다시 잰다. 압축 내용과 설치 결과를 규칙으로 대조한다.
uv run --no-project python "%REPO%\tools\pack-check\pack_check.py" --e2e --kr-dalamud "%DALAMUD_HOME%" --dotnet "%DOTNET%"
if errorlevel 1 (
  echo [실패] 배포 검사가 걸렸다. 위 목록을 본다.
  goto :fail
)

echo.
echo 끝: %OUT%
dir /b "%OUT%"
echo.
echo 확인 (설치는 안 하고 무엇을 찾았는지만 말한다):
echo   "%OUT%\FF14AccessibilityInstaller-KR.exe" --check
echo.
endlocal
exit /b 0

:fail
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 1
