@echo off
setlocal
call "%~dp0_env.cmd"

rem 릴리스를 낸다. pack.bat이 낸 dist를 그대로 GitHub 릴리스에 올린다.
rem
rem 사용자가 새 판을 받는 길은 둘이고, 둘 다 이 릴리스의 자산을 가리킨다.
rem   - 설치 프로그램 자기 갱신: installer.json (버전과 SHA-256)
rem   - Dalamud 커스텀 저장소:   repo.json     (플러그인 zip 주소)
rem 그래서 자산 다섯이 한 릴리스에 같이 올라가야 한다. 하나라도 빠지면
rem 받는 쪽은 오류가 아니라 "새 판이 없다"로 읽는다.
rem
rem 태그는 플러그인 버전이다. 설치 프로그램이 태그에서 v를 떼어 설치된
rem 버전과 비교하기 때문이다(InstallerService.ChoosePluginSourceAsync).

set "OUT=%REPO%\dist"
set "GHREPO=dnz3d4c/ff14-ko-accessibility"

echo == 릴리스 ==
echo.

for %%F in (
  "FF14AccessibilityInstaller-KR.exe"
  "FF14Accessibility.zip"
  "사용 안내.md"
  "repo.json"
  "installer.json"
) do (
  if not exist "%OUT%\%%~F" (
    echo [실패] 자산이 없다: %OUT%\%%~F
    echo   run\pack.bat 을 먼저 돌린다.
    goto :fail
  )
)

rem 릴리스 노트는 사람이 쓴다. 판마다 내용이 달라서 만들어 낼 수 없고,
rem 받는 사람이 "이번에 뭐가 바뀌었나"를 읽는 유일한 자리다.
if not exist "%OUT%\release-notes.md" (
  echo [실패] 릴리스 노트가 없다: %OUT%\release-notes.md
  echo   이번 판에서 바뀐 것을 한국어로 적고 다시 돌린다.
  goto :fail
)

for /f "delims=" %%V in ('uv run --no-project python "%REPO%\tools\release-manifest\release_manifest.py" --print-version') do set "VER=%%V"
if not defined VER (
  echo [실패] repo.json 에서 버전을 못 읽었다.
  goto :fail
)
set "TAG=v%VER%"

echo 태그: %TAG%
echo 저장소: %GHREPO%
echo.

rem gh가 윈도에서 한글 파일 이름을 못 다룬다. 첫 릴리스에서 `사용 안내.md`가
rem `default.md`로 올라갔고 오류도 안 났다 - 받는 사람 화면에서만 이름이
rem 틀린다. 그래서 올릴 때만 ASCII 이름의 사본을 쓴다. 폴더에 나가는
rem 이름은 그대로다.
set "TMPGUIDE=%TEMP%\README.ko.md"
copy /y "%OUT%\사용 안내.md" "%TMPGUIDE%" > NUL
if errorlevel 1 (
  echo [실패] 안내 문서 사본을 못 만들었다.
  goto :fail
)

gh release view "%TAG%" --repo "%GHREPO%" > NUL 2>&1
if errorlevel 1 (
  echo 새 릴리스를 만든다.
  gh release create "%TAG%" --repo "%GHREPO%" --title "%TAG%" --notes-file "%OUT%\release-notes.md" ^
    "%OUT%\FF14AccessibilityInstaller-KR.exe" ^
    "%OUT%\FF14Accessibility.zip" ^
    "%OUT%\repo.json" ^
    "%OUT%\installer.json" ^
    "%TMPGUIDE%"
  if errorlevel 1 goto :fail
) else (
  echo 같은 태그가 이미 있다. 자산만 덮어쓴다.
  gh release upload "%TAG%" --repo "%GHREPO%" --clobber ^
    "%OUT%\FF14AccessibilityInstaller-KR.exe" ^
    "%OUT%\FF14Accessibility.zip" ^
    "%OUT%\repo.json" ^
    "%OUT%\installer.json" ^
    "%TMPGUIDE%"
  if errorlevel 1 goto :fail
)

echo.
echo 냈다. 받는 쪽이 보는 주소:
echo   https://github.com/%GHREPO%/releases/latest/download/FF14AccessibilityInstaller-KR.exe
echo   https://github.com/%GHREPO%/releases/latest/download/repo.json
echo.
endlocal
exit /b 0

:fail
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 1
