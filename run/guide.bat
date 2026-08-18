@echo off
setlocal
call "%~dp0_env.cmd"

rem 공식 가이드(guide.ff14.co.kr)를 받아 두고 우리가 베낄 형식을 뽑는다.
rem 왜 필요한지는 .claude\skills\ko-user-guide\SKILL.md.
rem
rem   guide.bat fetch        인덱스와 문서를 받아 캐시에 넣는다 (74건, 1초 간격)
rem   guide.bat md           캐시를 마크다운으로 다시 옮긴다 (네트워크 없음)
rem   guide.bat scan         시각 의존 표현이 어디에 몇 건인가
rem   guide.bat find 단축바  코퍼스에서 낱말 찾기

uv run --no-project python "%REPO%\tools\ko-guide\guide.py" %*
if errorlevel 1 goto :fail

endlocal
exit /b 0

:fail
echo.
if not defined FF14_NOPAUSE pause
endlocal
exit /b 1
