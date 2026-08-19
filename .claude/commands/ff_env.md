---
description: 우리 밑에 깔린 계층 재기 - KR 달라무드, vnavmesh, 게임 클라 패치. 업스트림 동기화보다 이쪽이 먼저다
argument-hint: check | dalamud | vnavmesh | game
---

# /ff_env — 아래에서 오는 변화

받은 인자: `$ARGUMENTS` — 비었으면 `check`로 친다.

동기화는 위에서만 오지 않는다. **아래에서도 온다** — 업스트림과 무관하게 우리만 깨지는 계층이 셋 있고, 그 규칙은 [docs/upstream/sync.md](../../docs/upstream/sync.md) §9가, 사실(버전·경로·측정값)은 [docs/dev/environment.md](../../docs/dev/environment.md)가 갖는다. 여기 베끼지 않는다.

**순서가 정해져 있다.** 게임이 패치되면 업스트림 동기화보다 이쪽이 먼저다. 이 계층이 깨진 채로 위를 올리면 무엇 때문에 깨졌는지 구분이 안 된다.

## 이 커맨드가 못 하는 것

**갱신 자체는 내가 못 한다.** KR 달라무드는 GUI 업데이터고, 게임 패치는 런처가 한다. 내가 하는 것은 **재고와 판정과 문서 갱신**이고, 누르는 것은 사용자다. 그러니 "동기화했다"고 말하지 않는다 — 무엇이 어긋났고 무엇을 눌러야 하는지를 낸다.

## 멈추는 조건 — 먼저 읽는다

하나라도 나오면 **커밋하지 않고 멈춰서 보고한다.**

- 우리가 싣는 KR 시그니처가 **0건이거나 2건 이상** → `overlay/patches/0004`가 죽고 모드가 조용히 관리 구현으로 떨어진다. 새 시그니처를 찾는 건 판단이 필요한 일이다
- **FFXIVClientStructs 짝이 어긋난다** (KR 7.51 / 글로벌 7.55) → 적재는 되고 호출에서 던진다. 빌드가 먼저 죽는 게 정상이고, 안 죽었는데 어긋났으면 그게 더 나쁘다
- `Hooks` 폴더를 못 찾거나 **버전이 문서와 다르다** → 업데이터가 갱신한 것이다. `run\_env.cmd`가 최신을 자동으로 고르지만, 문서의 값은 손으로 옮긴다
- vnavmesh 참조에 **미해결이 생겼다** → 남의 플러그인 IPC 15종이 우리 자동이동 전부다
- `run\check.bat`이 빨갛다

## check (기본)

지금 계층이 성한지 한 번에 잰다. 갱신은 안 한다.

1. **런타임 경로.** `run\_env.cmd`가 고른 Dalamud `Hooks` 버전과 프로필 루트를 확인한다. 프로필 루트 규칙은 `tools/kr-setup/kr_profile.py` 하나가 갖는다 — 우리 탈출구(`FF14ACC_KR_PROFILE`) → 업데이터 설정 → 기본값 순이다.
2. **양쪽 빌드.** CS 7.51/7.55 짝이 성한지는 빌드가 판정한다.

       cmd //c "set FF14_NOPAUSE=1 && run\check.bat"

3. **배포물 참조.** `dist/`가 있으면 담긴 DLL이 KR 쪽 어셈블리에 실제로 붙는지 다시 잰다. `run\pack.bat` 4단계(`tools/pack-check`)가 `tools/asmref-check`를 부른다.
4. **마지막 세션 판정.** 로그가 있으면 본다 — 25만 자를 눈으로 훑지 않는다.

       cmd //c "set FF14_NOPAUSE=1 && run\log.bat"

   `pluginConfigs\vnavmesh.json` FileNotFound 오류 **1건은 정상**이다(현황판 §5-7, 안 고치기로 한 것). 그 수가 늘었으면 그때가 볼 시점이다.
5. 어긋난 것이 있으면 위 "멈추는 조건"대로 보고하고 멈춘다. 없으면 한 줄로 성하다고 말한다.

## dalamud

KR 달라무드(`MiqoKR/kr-dalamud-updater`) 갱신. **버스 팩터 1인 계층이고 우리가 통제하지 못한다.**

1. **먼저 지금 값을 적어 둔다** — `Hooks` 아래 버전 폴더, `docs/dev/environment.md` §3의 값. 갱신 뒤 무엇이 움직였는지 대조할 기준이다.
2. **사용자에게 실행을 넘긴다.** 게임이 떠 있는 상태에서 업데이터를 돌린다. 실행 대상은 [CLAUDE.md](../../CLAUDE.md) `## 확정된 실행 대상`에 있는 것 하나를 그대로 준다. 무엇을 보고 성공을 판단하는지와 나에게 알려줄 것을 같이 적는다.
3. **갱신됐다는 답을 받은 뒤에** 다시 잰다 — `Hooks` 버전이 바뀌었나, `run\check.bat`이 그대로 통과하나, `dist/`를 다시 내야 하나.
4. **버전이 움직였으면 `docs/dev/environment.md` §3을 옮긴다.** 그 문서가 "빌드가 갑자기 Dalamud 타입을 못 찾으면 여기부터 본다"고 적어 둔 자리다.
5. 필요하면 `run\pack.bat`으로 배포물을 다시 내고, `[도구]`나 `[문서]`로 커밋한다.

## vnavmesh

자동 걷기 플러그인(`awgil/ffxiv_navmesh`, puni.sh 매니페스트). **남의 것은 남이 관리하게 둔다** — 우리는 재기만 한다.

1. 설치돼 있나. 없으면 결함이 아니라 미설치다(넘패드3에서 `Auto-walk not available`).
2. 어셈블리 참조와 시그니처를 다시 잰다. 절차와 지난 실측(참조 659건 미해결 0, 시그니처 6건 전부 유일)은 `docs/dev/environment.md` §7.
3. **설정 파일을 만들어 주지 않는다.** 그쪽 스키마에 우리가 묶인다(현황판 §5-7). 기동마다 뜨는 FileNotFound 1건이 정상 상태다.
4. 설치 프로그램이 받아오므로, 판이 올라갔으면 `run\pack.bat`으로 배포물을 다시 낸다. **`--check`는 `pack.bat`의 인자가 아니라 낸 EXE의 인자다** — `pack.bat`은 인자를 안 받고, 끝에 이 줄을 안내한다.

dist\FF14AccessibilityInstaller-KR.exe --check

## game

KR 클라이언트가 패치된 뒤. **시그니처가 살아 있는지가 전부다.**

1. 우리가 싣는 시그니처가 여전히 **정확히 1건**인지 본다. 시그니처는 사본이 아니라 실제로 나가는 패치에서 읽는다.

       uv run --no-project --with pytest pytest tools/sig-probe/tests -q

   게임이 안 깔린 머신에서는 건너뛴다. 다른 경로면 `FFXIV_KR_GAME`으로 `game\ffxiv_dx11.exe`를 가리킨다.
2. **도구 자신이 믿을 만한지도 같이 본다.** Dalamud가 실제 프로세스에서 해석해 캐시해 둔 시그니처와 우리 해석이 일치하는지 대조하는 모드가 있다(`--verify-cache`, `cachedSigs\cs.json`). 지난 실측은 2,203건 불일치 0이다(`docs/dev/environment.md` §6).
3. 게임 버전이 KR Dalamud가 지원한다고 적어 둔 버전과 **같은지** 본다. 어긋나면 주입이 안 되고, 그건 우리 문제가 아니라 대기다.
4. 시그니처가 깨졌으면 **거기서 멈춘다.** 새로 찾는 것은 `docs/dev/environment.md` §6의 절차(위치 근거 + 본문 근거 두 갈래)를 따라야 하고, 짐작으로 넣을 자리가 아니다.
5. 성했으면 그다음이 `/ff_sync`다.
