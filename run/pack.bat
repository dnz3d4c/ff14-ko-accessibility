@echo off
setlocal
call "%~dp0_env.cmd"

rem 배포 폴더를 만든다. 결과는 파일 두 개다 - 설치기 EXE와 플러그인 zip.
rem 설치기는 자기 옆의 zip을 먼저 보므로 그 폴더를 통째로 옮기면 어디서든
rem 돈다. 받는 쪽에 .NET 설치를 요구하지 않으려고 자체 포함으로 낸다.

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
if not exist "%PLUGINZIP%" (
  echo [실패] 플러그인이 아직 안 빌드됐다.
  echo   먼저 run\build.bat을 돌린다.
  goto :fail
)

set "DOTNET_CLI_UI_LANGUAGE=en"
echo 1/2  설치기를 자체 포함 단일 EXE로 낸다. 몇 분 걸린다.
"%DOTNET%" publish -c Release "%INSTALLER%"
if errorlevel 1 (
  echo [실패] 설치기 빌드가 깨졌다.
  goto :fail
)

echo.
echo 2/2  배포 폴더에 모은다.
if not exist "%OUT%" mkdir "%OUT%"
copy /y "%PUBLISH%\FF14AccessibilityInstaller-KR.exe" "%OUT%\" >nul
if errorlevel 1 goto :fail
copy /y "%PLUGINZIP%" "%OUT%\FF14Accessibility.zip" >nul
if errorlevel 1 goto :fail

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
