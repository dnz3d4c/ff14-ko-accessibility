# 프로젝트 지침 — ff14-ko-accessibility

전역 지침(`~/.claude/CLAUDE.md`)에 더해 이 저장소에만 적용된다.

## 사용자에게 실행을 시킬 때 [필수]

이 프로젝트는 게임·런처·인젝터를 다뤄서 사용자가 직접 GUI를 눌러야 하는 단계가 계속 나온다. 그때 지켜야 할 것.

- **"평소대로", "보통 하던 대로", "알아서", "필요하면" 금지.** 실행할 것은 **정확히 하나**를 제시한다. 선택지를 주는 건 사용자에게 조사를 떠넘기는 것이다.
- **제시 전에 실측한다.** 바로가기는 `WScript.Shell`로 Target·Arguments·WorkingDirectory를 열어 확인하고, 설치 경로는 레지스트리 언인스톨 항목과 시작 메뉴를 뒤진다. 확인 안 된 경로를 내놓지 않는다.
- **실행 가능한 것만 준다.** zip·폴더·빌드 산출물 경로를 실행하라고 주지 않는다. 실행 대상은 `.exe` 또는 `.lnk`다.
- **작업 디렉토리가 걸린 프로그램은 바로가기(`.lnk`)로 준다.** exe 직접 호출은 cwd가 달라진다.
- **붙여넣을 곳을 명시한다** — Win+R인지, 터미널인지, GUI 버튼 이름인지.
- 경로는 **윈도 표기**(백슬래시). 공백이 있으면 큰따옴표로 감싼다. 세션 셸이 bash라고 bash 표기로 주지 않는다.
- **순서와 선행 조건을 명시한다.** "게임이 떠 있는 상태에서" 같은 조건은 명령 옆에 붙인다.
- 명령을 준 뒤 **무엇을 보고 성공/실패를 판단하는지**와 **나에게 뭘 알려줘야 하는지**를 같이 적는다.

### 확정된 실행 대상

게임 실행 (Win+R):

"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\FINAL FANTASY XIV - KOREA\FINAL FANTASY XIV - KOREA.lnk"

KR Dalamud 업데이터 (Win+R, 게임이 떠 있는 상태에서):

C:\Users\USER\AppData\Local\KR-Dalamud-Updater\app\Dalamud.Updater.exe

새로 확정한 실행 대상은 여기에 즉시 추가한다.

## vendor 취급 [필수]

`vendor/ff14-accessibility/`는 업스트림 클론이고 **우리 저장소의 버전 관리 밖**이다.

- 거기서 직접 작업하지 않는다. `kr-port` 브랜치에 커밋하고 `git format-patch`로 떼어낸다.
- 한국 전용 패치는 `overlay/patches/`, 업스트림 기여 대기 변경은 `patches/`. 섞는 커밋은 훅이 거부한다.

## 나머지는 문서가 소유한다

여기에 베끼지 않는다. 어긋나면 문서가 맞다.

- 개발 환경·경로·빌드 명령: `docs/environment.md`
- 커밋 규칙: `docs/commit-rules.md`
- 포팅 판단 근거: `docs/ko-client-port-feasibility.md`
