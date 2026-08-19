@echo off
setlocal
call "%~dp0_env.cmd"

rem 게임 데이터에서 한국어 UI 낱말을 뽑는다. 게임을 켤 필요가 없다 - sqpack을
rem 직접 읽는다. 왜 필요한지는 ko-localization 스킬 3절.

if not exist "%DOTNET%" (
  echo [실패] .NET SDK를 못 찾았다: %DOTNET%
  goto :fail
)
if not defined DALAMUD_HOME (
  echo [실패] Dalamud hook 폴더가 없다: %KR_PROFILE%\addon\Hooks
  echo   Lumina.dll을 거기서 참조한다. docs/dev/kr-runtime.md 5절.
  goto :fail
)

set "DOTNET_CLI_UI_LANGUAGE=en"
"%DOTNET%" run --project "%REPO%\tools\ko-terms\koterms.csproj" -c Release -v quiet -- %*
if errorlevel 1 goto :fail

endlocal
exit /b 0

:fail
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 1
