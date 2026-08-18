# 프로젝트 지침 — ff14-ko-accessibility

전역 지침(`~/.claude/CLAUDE.md`)에 더해 이 저장소에만 적용된다.

## 현황판이 먼저다 [필수]

기능 구현·수정·개선을 **시작하기 전에** [docs/status.md](docs/status.md)를 연다. 남은 일의 기준이고, 다른 문서는 근거만 갖는다.

- 하려는 일이 판에 없으면 `W-NN`을 새로 따고 시작한다. ID는 재사용하지 않는다.
- 끝나면 판의 상태를 옮긴다. **완료 선언 전에 한다** — 나중에 몰아서 하지 않는다.
- `[업스트림]`·`[한국전용]`·`[검증]`·`[도구]` 커밋은 판을 같이 건드리거나 `Status-Board:` 트레일러로 이유를 밝혀야 한다. 훅의 C8이 검사한다.

판단이 필요한 사안은 판의 `## 8. 판단이 필요한 것`에 모은다. 흩어 놓고 그때그때 묻지 않는다.

## 사용자에게 실행을 시킬 때 [필수]

이 프로젝트는 게임·런처·인젝터를 다뤄서 사용자가 직접 GUI를 눌러야 하는 단계가 계속 나온다. 그때 지켜야 할 것.

**먼저, 시킬 일인지부터 본다.** `run/`의 배치는 전부 내가 직접 돌린다 — 빌드·배포·검사·로그 판정은 사용자 일이 아니다. `FF14_NOPAUSE=1`을 걸면 `pause`가 안 걸려 그대로 돌아간다.

cmd //c "set FF14_NOPAUSE=1 && run\build.bat"

사용자에게 남기는 것은 **게임 안에서만 되는 것**뿐이다 — 로그인, 인게임 조작, 그리고 **귀로 하는 판정**. 소스를 고쳤으면 배포까지 내가 끝내 놓고, 사용자에게는 "게임에서 이걸 쳐 보고 어떻게 들리는지 알려 줘"만 남긴다. 빌드를 시키는 건 자동화된 일을 떠넘기는 것이다(2026-08-18 지적).

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
- **한국어 문장은 패치가 아니라 `overlay/ko/ko.json`에서 고친다.** 마지막 패치(`0008`)는 `tools/ko-apply`가 만드는 생성물이라 손대지 않는다 — 충돌하면 푸는 게 아니라 다시 만든다. 왜인지는 [overlay/patches/README.md](overlay/patches/README.md).
- **붙는 자리는 `upstream.json`의 핀이지 `main`이 아니다.** 핀을 손으로 고치지 않는다 — `run\sync.bat`이 옮긴다.
- **업스트림은 독일어로 개발된다.** 핀을 옮겼으면 [docs/upstream-changes.md](docs/upstream-changes.md)에 한국어로 남긴다. 안 남기면 훅 C10과 테스트가 막는다. 절차는 [docs/upstream-sync.md](docs/upstream-sync.md).

## 나머지는 문서가 소유한다

여기에 베끼지 않는다. 어긋나면 문서가 맞다.

- 개발 환경·경로·빌드 명령: `docs/environment.md`
- 커밋 규칙: `docs/commit-rules.md`
- 업스트림 동기화: `docs/upstream-sync.md`
- 포팅 판단 근거: `docs/ko-client-port-feasibility.md`
