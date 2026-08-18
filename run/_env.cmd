@echo off
rem 공통 경로 해석. 다른 배치가 call 해서 쓴다. 직접 실행하는 파일이 아니다.
rem
rem 경로를 박아 넣지 않는다 - 전부 환경변수에서 끌어낸다. 특히 Dalamud hook
rem 폴더는 이름이 버전이라 업데이터가 갱신할 때마다 바뀐다. docs/environment.md
rem §3이 "빌드가 갑자기 Dalamud 타입을 못 찾으면 여기부터 본다"고 적어 둔
rem 함정이고, 그걸 손으로 고치지 않게 하려고 여기서 자동으로 최신을 고른다.

set "REPO=%~dp0.."

rem 프로필 루트는 여기서 정하지 않는다. 정하는 곳은 KR Dalamud 업데이터의
rem 설정(%APPDATA%\KrDalamudUpdater\settings.json 의 ProfileRoot)이고, 그건
rem 사용자가 바꿀 수 있는 값이다. 박아 두면 설치기와 갈리고, 갈려도 오류가
rem 안 난다 - 플러그인만 조용히 빠진다. 규칙의 단일 원천은 kr_profile.py다.
set "KR_PROFILE="
for /f "delims=" %%P in ('uv run --no-project python "%REPO%\tools\kr-setup\kr_profile.py" 2^>nul') do set "KR_PROFILE=%%P"
if not defined KR_PROFILE (
  echo [실패] 프로필 루트를 정하는 데 실패했다.
  echo   uv가 있고 tools\kr-setup\kr_profile.py가 있는지 본다.
  exit /b 1
)
set "KR_LOG=%KR_PROFILE%\dalamud-kr-gui.log"
set "KR_CONFIG=%KR_PROFILE%\dalamudConfig.json"
set "KR_DEVPLUGINS=%KR_PROFILE%\devPlugins"
set "KR_INSTALLEDPLUGINS=%KR_PROFILE%\installedPlugins"
set "UPDATER=%LOCALAPPDATA%\KR-Dalamud-Updater\app\Dalamud.Updater.exe"
set "GAME_LNK=%ProgramData%\Microsoft\Windows\Start Menu\Programs\FINAL FANTASY XIV - KOREA\FINAL FANTASY XIV - KOREA.lnk"

rem scoop 루트는 %SCOOP%가 있으면 그것, 없으면 기본 위치.
if not defined SCOOP set "SCOOP=%USERPROFILE%\scoop"
set "DOTNET=%SCOOP%\apps\dotnet-sdk\current\dotnet.exe"

rem Hooks 아래에서 가장 마지막 이름을 고른다. dir /b /o:n 은 이름 오름차순이라
rem 마지막이 최신 버전이다. 'dev'(수동 구성 잔재)는 건너뛴다.
set "DALAMUD_HOME="
for /f "delims=" %%D in ('dir /b /a:d /o:n "%KR_PROFILE%\addon\Hooks" 2^>nul') do (
  if /i not "%%D"=="dev" set "DALAMUD_HOME=%KR_PROFILE%\addon\Hooks\%%D"
)
exit /b 0
