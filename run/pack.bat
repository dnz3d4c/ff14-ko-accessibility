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
echo 1/4  플러그인을 KR(7.51)로 다시 빌드한다.
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
echo 2/4  설치기를 자체 포함 단일 EXE로 낸다. 몇 분 걸린다.
"%DOTNET%" publish -c Release "%INSTALLER%"
if errorlevel 1 (
  echo [실패] 설치기 빌드가 깨졌다.
  goto :fail
)

echo.
echo 3/4  배포 폴더에 모은다.
if not exist "%OUT%" mkdir "%OUT%"
copy /y "%PUBLISH%\FF14AccessibilityInstaller-KR.exe" "%OUT%\" >nul
if errorlevel 1 goto :fail
copy /y "%PLUGINZIP%" "%OUT%\FF14Accessibility.zip" >nul
if errorlevel 1 goto :fail

rem 안내 문서도 같이 나간다. 설치의 첫 단계가 이걸 읽는 것인데, 저장소에만
rem 두면 받는 사람은 무엇부터 눌러야 하는지 알 길이 없다.
copy /y "%REPO%\overlay\ko\README.ko.md" "%OUT%\사용 안내.md" >nul
if errorlevel 1 goto :fail

echo.
echo 4/4  낸 것을 다시 잰다. 압축 내용과 설치 결과를 규칙으로 대조한다.
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
