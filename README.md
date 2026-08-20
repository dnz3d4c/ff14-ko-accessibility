# FF14 접근성 모드 (한국 서버)

파이널 판타지 14를 한국 서버에서 시각장애인이 스크린 리더로 플레이할 수 있게 합니다. [원본 접근성 모드](https://github.com/derbruedi/ff14-accessibility)에 한국 서버용 패치를 얹은 것입니다.

- **받는 곳** — [최신 릴리스](https://github.com/dnz3d4c/ff14-ko-accessibility/releases/latest)
- **설치 및 사용방법** — [사용 안내](overlay/ko/README.ko.md)
- **프로젝트 현황** — [현황판](docs/status.md)
- **프로젝트 문서 읽는법** — [문서 지도](docs/README.md)

## 1. 이 모드가 하는 일

모드가 만든 안내 메시지는 NVDA가 음성 및 점자로 처리합니다. 메뉴와 창, 로그와 대화, 이동과 길안내, 전투, 소지품과 장비, 단축바를 음성 출력합니다. 인게임 내 메시지(NPC 이름, 대사, 메뉴, 아이템 이름)은 한국어로 출력되며, 모드가 손대지 않습니다.

모드 기능과 단축키, 명령어는 [사용 안내](overlay/ko/README.ko.md) 4장과 5장에 있습니다.

## 2. 한국 서버 모드가 원본 모드와 다른 것

원본 모드는 독일어로 개발되고 글로벌 클라이언트를 전제로 합니다. 한국 서버 모드와 다른 점은 셋입니다.

- **모드 안내 메시지가 한국어로 출력됩니다.** 언어는 `/acc lang`으로 변경할 수 있습니다. 기본값이 한국어입니다
- **공식 파이널 판타지 14 런처와 한국 서버용으로 포팅된 Dalamud를 사용합니다**
- **방향 안내를 켜고 끄는 `N`이 한국 클라이언트에서는 제작수첩을 여는 키와 같습니다.** 한국 서버에만 있는 결함이고, 원본과 함께 겪는 결함이 둘 더 있습니다. 증상과 우회 방법은 [사용 안내](overlay/ko/README.ko.md) 6장에 있습니다

이 외 동작은 원본 모드와 같습니다.

## 3. 함께 필요한 것

**KR Dalamud 업데이터와 vnavmesh는 설치 프로그램이 해당 프로그램의 저장소에서 직접 내려받으며**, 내려받을지 묻는 대화상자가 표시됩니다. 이 저장소에서 재배포하지 않습니다.

- **[KR Dalamud 업데이터](https://github.com/MiqoKR/kr-dalamud-updater)** — 게임에 Dalamud를 사용할 수 있게 해주는 프로그램입니다. 프로그램이 없으면 모드가 실행되지 않습니다
- **[vnavmesh](https://github.com/awgil/ffxiv_navmesh)** — 자동 이동, 따라가기, 경로 미리 듣기에 필요합니다. 설치하지 않아도 나머지 모드 기능은 그대로 동작합니다

## 4. 제안과 문제 신고

- 한국어 번역, 설치 프로그램 **한국 서버와 관련된 내용**은 [이 저장소의 이슈](https://github.com/dnz3d4c/ff14-ko-accessibility/issues)에 남길 수 있습니다
- 모드의 새 기능 제안, 원본 모드에서 나타나는 문제는 [원본 저장소의 이슈](https://github.com/derbruedi/ff14-accessibility/issues)에 올려주세요. 어느 쪽에 올릴지 모르겠다면 이 저장소에 올려주세요.

문제를 남길 때 다음이 함께 있으면 원인을 찾는 데 도움이 됩니다.

- 인게임에서 `Ctrl+F5`로 바탕 화면에 저장한 창 구조 파일
- 바탕 화면의 `FFXIV_Keybinds.txt`
- 어떤 음성이 들렸고 무엇을 기대했는지

**모드의 한국어 표현 제안은 특히 환영합니다.**

## 5. 라이선스

이 모드는 **GNU Affero General Public License, Version 3**을 따릅니다. 원본 모드와 Dalamud, goatcorp의 공식 플러그인 서식도 모두 같은 라이선스입니다. 전문은 저장소의 [LICENSE](LICENSE)에 있습니다.

배포물에 함께 포함된 제3자 소프트웨어는 **Tolk**(LGPL-3.0), **NVDA Controller Client**(LGPL-2.1), **NAudio**(MIT)입니다. 각각의 라이선스는 `FF14Accessibility.zip` 안의 `THIRD-PARTY-NOTICES.md`에 있고, **재배포할 때 이 파일이 함께 있어야 합니다.**

## 6. 만든 사람들

- **원본 접근성 모드** — [derbruedi](https://github.com/derbruedi)가 만들고 있습니다. 기여자 목록은 [원본 저장소](https://github.com/derbruedi/ff14-accessibility)에 있습니다
- **한국 서버 모드** — [dnz3d4c](https://github.com/dnz3d4c)

## 7. 개발

### 저장소가 무엇을 담나

- `vendor/ff14-accessibility/` — 원본 클론의 **submodule입니다.** 한국 서버용 변경은 그 안 `kr-port` 브랜치의 커밋으로 있고, 이 저장소는 그 브랜치의 마지막 커밋을 가리키는 포인터 하나만 기록합니다. 이유는 [vendor.md](docs/upstream/vendor.md)에 있습니다
- `overlay/ko/` — **한국어의 원본입니다.** `ko.json`이 `(독일어, 영어) → 한국어` 표, `terms.json`이 게임에서 뽑은 용어 대장, `guide-quotes.json`이 공식 가이드 인용 대장, `README.ko.md`가 사용자 문서입니다
- `overlay/patches/` — 한국 전용 변경의 명세입니다
- `patches/` — **원본 저장소에 보낼 것**의 기준과 기록입니다. 기각된 후보는 `rejected.md`에 남고 다시 만들지 않습니다
- `upstream.json` — 한국 서버용 변경이 원본의 어느 버전을 기준으로 하는지 적습니다
- `tools/ko-apply` · [`ko-terms`](tools/ko-terms/README.md) · [`ko-words`](tools/ko-words/README.md) · `strings-golden` — 한국어화 도구입니다. 카탈로그를 소스에 써 넣고, 게임을 켜지 않고 낱말을 뽑고, 옮기기 전 원본을 지킵니다
- `run/` · `docs/` — 실행 배치와 개발 문서입니다

### 한국 서버라서 다른 것

여기 적은 넷이 한국 서버용 변경의 전부입니다. 나머지는 원본과 같습니다.

- **KR이 깔아 주는 FFXIVClientStructs가 글로벌과 판이 다릅니다.** 원본 소스를 KR로 빌드했을 때 없는 함수는 정확히 하나였고 확장 메서드 shim으로 메웠습니다. **같은 소스를 글로벌로 빌드한 결과는 바뀌지 않습니다.** 두 판의 실제 번호와 실측 값은 [environment.md](docs/dev/environment.md)가 갖습니다
- **`DALAMUD_HOME`이 KR 업데이터가 만든 경로를 가리킵니다.** 업데이터가 hook 버전을 올릴 때마다 낡으므로 `run\_env.cmd`가 `Hooks` 아래에서 최신 버전을 직접 골라 이 문제를 없앱니다
- **프로필 루트가 `%APPDATA%\XIVLauncherKR`입니다.** 사용자가 업데이터에서 옮길 수 있는 값이라 박아 두지 않고 업데이터 설정에서 읽습니다
- **한국어 문장은 소스가 아니라 `overlay/ko/ko.json`에서 고칩니다.** 소스의 그 자리는 `tools/ko-apply`가 만드는 생성물이라 손대면 검사가 막습니다

### 클론 직후 한 번

git config core.hooksPath .githooks && git config commit.template .gitmessage && git submodule update --init && uv run --no-project --with pytest pytest tools -q

`vendor/`는 비공개 미러라 접근 권한이 있어야 받아집니다. 못 받은 상태에서는 vendor가 필요한 검사를 건너뜁니다. 오류가 아닙니다. `kr-port` 브랜치를 세우는 일은 손으로 하지 않아도 됩니다. 처음 `run\build.bat`을 돌릴 때 자동으로 처리됩니다.

### 빌드에 더 필요한 셋

셋 중 하나라도 없으면 `run\build.bat`이 그 자리에서 멈추고 무엇이 없는지 말합니다.

- **scoop으로 설치한 .NET SDK 10** — PATH의 `dotnet`은 런타임만 있어서 쓰지 않습니다
- **7z** — `scoop install 7zip`
- **KR Dalamud의 hook 폴더** — 업데이터에서 [업데이트 확인]을 한 번 돌려야 생깁니다

경로와 함정은 [environment.md](docs/dev/environment.md)가 갖습니다. .NET SDK 경로에서 자주 막힙니다.

### 자동으로 도는 검사

- `commit-lint` — 커밋 메시지가 규칙 C1~C13을 지키는지 검사합니다
- `patch-check` — 저장소가 기록한 vendor 포인터가 `kr-port`의 마지막 커밋이고, 핀이 그 이력의 조상인지 대조합니다
- `docs-check` — **문서가 인용한 숫자를 산출물에서 다시 계산해 대조합니다.** 손으로 옮겨 적은 값이 낡으면 검사가 실패합니다. 단축키 목록이 사용 안내와 소스에서 갈라지는 것도 여기서 잡습니다
- [`ko-words`](tools/ko-words/README.md) — 번역이 실제로 쓴 낱말을 모아 게임 덤프와 대조합니다. 용어 대장에 적는 것을 잊어도 잡힙니다
- [`ko-style`](tools/ko-style/README.md) — 문서의 말투가 한 문서 안에서 갈리는 것과, 사용자가 걷어낸 표현이 되살아나는 것을 잡습니다. 인용은 실물을 옮긴 것이라 보지 않습니다
- [`ko-speech`](tools/ko-speech/README.md) — 번역 표를 안 거치고 소스에 맨몸으로 박힌 외국어 문장을 잡습니다. 그런 자리는 한국어가 없어도 조용히 지나가므로, 목록 자체를 고정해 늘어나면 실패시킵니다
- [`pack-check`](tools/pack-check/README.md) — 배포 산출물이 바닐라인지, 설치 결과가 Dalamud가 읽는 모양인지 봅니다. 설치 프로그램을 임시 프로필에 실제로 돌려 확인합니다
- [`asmref-check`](tools/asmref-check/README.md) · `sig-probe` · [`asmstr`](tools/asmstr/README.md) — 플러그인이 부르는 타입과 시그니처가 KR에 실제로 있는지 확인합니다

검사만 따로 돌릴 때는 이렇게 합니다.

uv run --no-project --with pytest pytest tools -q

### 원본 모드 전체를 다루는 문서

한국 서버 고유가 아닌 내용은 원본 저장소의 문서가 기준입니다.

- [README.en.md](https://github.com/derbruedi/ff14-accessibility/blob/main/README.en.md) (영어) — **모드 전체의 기능·키·명령·설치를 다룹니다**
- [docs/game-api.md](https://github.com/derbruedi/ff14-accessibility/blob/main/docs/game-api.md) (독일어) — 검증된 게임 내부 구조입니다. FF14 문서 중 제일 중요하지만 독일어입니다
- [docs/ACCESSIBILITY_MODDING_GUIDE.md](https://github.com/derbruedi/ff14-accessibility/blob/main/docs/ACCESSIBILITY_MODDING_GUIDE.md) (영어) — 접근성 모드를 만드는 일반 원칙입니다. **FF14 내용은 없습니다**

### 커맨드

- `/ff_help` — 목록
- `/ff_sync` — 원본 모드가 앞서 간 만큼 따라잡기
- `/ff_env` — KR Dalamud·vnavmesh·게임 클라이언트 패치가 바뀌었는지 재기

**`/ff_env`를 `/ff_sync`보다 먼저 돌립니다.** 이유는 [sync.md](docs/upstream/sync.md) §9에 있습니다. 각 커맨드는 `## 멈추는 조건`을 갖고, 사람이 판단해야 하는 상황을 만나면 커밋하지 않고 멈춥니다.

### 매일 쓰는 배치

`run\`에 있고 **저장소 루트에서** 실행합니다. 무엇이 있고 무엇을 하는지는 [run/README.md](run/README.md)가 표로 갖습니다.
