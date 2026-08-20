# 개발 안내

이 저장소를 클론해서 빌드하고 검사를 돌리는 데 필요한 것. **남은 일은 [현황판](../status.md)이 갖는다.**

## 저장소가 무엇을 담나

- `vendor/ff14-accessibility/` — 원본 클론의 **submodule이다.** 한국 서버용 변경은 그 안 `kr-port` 브랜치의 커밋으로 있고, 이 저장소는 그 브랜치의 마지막 커밋을 가리키는 포인터 하나만 기록한다. 이유는 [vendor.md](../upstream/vendor.md)에 있다
- `overlay/ko/` — **한국어의 원본이다.** `ko.json`이 `(독일어, 영어) → 한국어` 표, `terms.json`이 게임에서 뽑은 용어 대장, `guide-quotes.json`이 공식 가이드 인용 대장, `README.ko.md`가 사용자 문서다
- `overlay/patches/` — 한국 전용 변경의 명세다
- `patches/` — **원본 저장소에 보낼 것**의 기준과 기록이다. 기각된 후보는 `rejected.md`에 남고 다시 만들지 않는다
- `upstream.json` — 한국 서버용 변경이 원본의 어느 버전을 기준으로 하는지 적는다
- `tools/ko-apply` · [`ko-terms`](../../tools/ko-terms/README.md) · [`ko-words`](../../tools/ko-words/README.md) · `strings-golden` — 한국어화 도구다. 카탈로그를 소스에 써 넣고, 게임을 켜지 않고 낱말을 뽑고, 옮기기 전 원본을 지킨다
- `run/` · `docs/` — 실행 배치와 개발 문서다

## 한국 서버라서 다른 것

여기 적은 넷이 한국 서버용 변경의 전부다. 나머지는 원본과 같다.

- **KR이 깔아 주는 FFXIVClientStructs가 글로벌과 판이 다르다.** 원본 소스를 KR로 빌드했을 때 없는 함수는 정확히 하나였고 확장 메서드 shim으로 메웠다. **같은 소스를 글로벌로 빌드한 결과는 바뀌지 않는다.** 두 판의 실제 번호와 실측 값은 [environment.md](environment.md)가 갖는다
- **`DALAMUD_HOME`이 KR 업데이터가 만든 경로를 가리킨다.** 업데이터가 hook 버전을 올릴 때마다 낡으므로 `run\_env.cmd`가 `Hooks` 아래에서 최신 버전을 직접 골라 이 문제를 없앤다
- **프로필 루트가 `%APPDATA%\XIVLauncherKR`이다.** 사용자가 업데이터에서 옮길 수 있는 값이라 박아 두지 않고 업데이터 설정에서 읽는다
- **한국어 문장은 소스가 아니라 `overlay/ko/ko.json`에서 고친다.** 소스의 그 자리는 `tools/ko-apply`가 만드는 생성물이라 손대면 검사가 막는다

## 클론 직후 한 번

git config core.hooksPath .githooks && git config commit.template .gitmessage && git submodule update --init && uv run --no-project --with pytest pytest tools -q

`vendor/`는 비공개 미러라 접근 권한이 있어야 받아진다. 못 받은 상태에서는 vendor가 필요한 검사를 건너뛴다. 오류가 아니다. `kr-port` 브랜치를 세우는 일은 손으로 하지 않아도 된다. 처음 `run\build.bat`을 돌릴 때 자동으로 처리된다.

## 빌드에 더 필요한 셋

셋 중 하나라도 없으면 `run\build.bat`이 그 자리에서 멈추고 무엇이 없는지 말한다.

- **scoop으로 설치한 .NET SDK 10** — PATH의 `dotnet`은 런타임만 있어서 쓰지 않는다
- **7z** — `scoop install 7zip`
- **KR Dalamud의 hook 폴더** — 업데이터에서 [업데이트 확인]을 한 번 돌려야 생긴다

경로와 함정은 [environment.md](environment.md)가 갖는다. .NET SDK 경로에서 자주 막힌다.

## 자동으로 도는 검사

- `commit-lint` — 커밋 메시지가 규칙 C1~C13을 지키는지 검사한다
- `patch-check` — 저장소가 기록한 vendor 포인터가 `kr-port`의 마지막 커밋이고, 핀이 그 이력의 조상인지 대조한다
- `docs-check` — **문서가 인용한 숫자를 산출물에서 다시 계산해 대조한다.** 손으로 옮겨 적은 값이 낡으면 검사가 실패한다. 단축키 목록이 사용 안내와 소스에서 갈라지는 것도 여기서 잡는다
- [`ko-words`](../../tools/ko-words/README.md) — 번역이 실제로 쓴 낱말을 모아 게임 덤프와 대조한다. 용어 대장에 적는 것을 잊어도 잡힌다
- [`ko-style`](../../tools/ko-style/README.md) — 문서의 말투가 한 문서 안에서 갈리는 것과, 사용자가 걷어낸 표현이 되살아나는 것을 잡는다. 인용은 실물을 옮긴 것이라 보지 않는다
- [`ko-speech`](../../tools/ko-speech/README.md) — 번역 표를 안 거치고 소스에 맨몸으로 박힌 외국어 문장을 잡는다. 그런 자리는 한국어가 없어도 조용히 지나가므로, 목록 자체를 고정해 늘어나면 실패시킨다
- [`pack-check`](../../tools/pack-check/README.md) — 배포 산출물이 바닐라인지, 설치 결과가 Dalamud가 읽는 모양인지 본다. 설치 프로그램을 임시 프로필에 실제로 돌려 확인한다
- [`asmref-check`](../../tools/asmref-check/README.md) · `sig-probe` · [`asmstr`](../../tools/asmstr/README.md) — 플러그인이 부르는 타입과 시그니처가 KR에 실제로 있는지 확인한다

검사만 따로 돌릴 때는 이렇게 한다.

uv run --no-project --with pytest pytest tools -q

## 원본 모드 전체를 다루는 문서

한국 서버 고유가 아닌 내용은 원본 저장소의 문서가 기준이다.

- [README.en.md](https://github.com/derbruedi/ff14-accessibility/blob/main/README.en.md) (영어) — **모드 전체의 기능·키·명령·설치를 다룬다**
- [docs/game-api.md](https://github.com/derbruedi/ff14-accessibility/blob/main/docs/game-api.md) (독일어) — 검증된 게임 내부 구조다. FF14 문서 중 제일 중요하지만 독일어다
- [docs/ACCESSIBILITY_MODDING_GUIDE.md](https://github.com/derbruedi/ff14-accessibility/blob/main/docs/ACCESSIBILITY_MODDING_GUIDE.md) (영어) — 접근성 모드를 만드는 일반 원칙이다. **FF14 내용은 없다**

## 커맨드

- `/ff_help` — 목록
- `/ff_sync` — 원본 모드가 앞서 간 만큼 따라잡기
- `/ff_env` — KR Dalamud·vnavmesh·게임 클라이언트 패치가 바뀌었는지 재기

**`/ff_env`를 `/ff_sync`보다 먼저 돌린다.** 이유는 [sync.md](../upstream/sync.md) §9에 있다. 각 커맨드는 `## 멈추는 조건`을 갖고, 사람이 판단해야 하는 상황을 만나면 커밋하지 않고 멈춘다.

## 매일 쓰는 배치

`run\`에 있고 **저장소 루트에서** 실행한다. 무엇이 있고 무엇을 하는지는 [run/README.md](../../run/README.md)가 표로 갖는다.
