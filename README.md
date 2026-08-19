# FF14 접근성 모드 — 한국 서버

파이널 판타지 14를 한국 서버에서 시각장애 플레이어가 스크린 리더로 플레이할 수 있게 합니다. [원본 접근성 모드](https://github.com/derbruedi/ff14-accessibility)에 한국 서버용 패치를 얹은 것입니다.

- **설치하고 쓰는 법** — [사용 안내](overlay/ko/README.ko.md)
- **남은 일과 알려진 결함** — [현황판](docs/status.md)
- **문서가 어디 있나** — [문서 지도](docs/README.md)

## 1. 무엇을 하나

모드가 만든 안내는 NVDA가 읽고, 같은 내용이 점자 정보 단말기로도 나갑니다. 게임이 주는 글(NPC 이름, 대사, 메뉴, 아이템 이름)은 원래부터 한국어이고 모드가 손대지 않습니다.

- **메뉴와 창** — 타이틀 화면, 캐릭터 선택, 캐릭터 생성, 시스템 메뉴, 퀘스트 목록, 선택 대화를 화살표로 넘길 때 줄마다 읽습니다. 설정 창의 조절바·선택 목록·스위치·탭을 읽고, [시스템(ESC) > 단축키 설정] 창은 기능 이름과 거기 지정된 키를 함께 읽습니다. NPC 대화에는 말하는 사람 이름이 먼저 붙습니다
- **로그와 대화** — 들어오는 줄을 채널별로 읽고 채널마다 따로 끌 수 있습니다. 입력란을 열면 지금 채널을 말하고 치는 글자를 하나씩 읽습니다. 아홉 채널로 나눈 기록을 개수 제한 없이 되읽을 수 있고, 되읽는 중에 Enter를 누르면 그 채널 그대로 답장이 열립니다
- **이동과 길찾기** — 가까운 대상을 키 하나로 넘기며 이름·분류·거리·방향을 읽고 게임 대상으로도 잡습니다. 목표 방향은 신호음으로 나갑니다. 좌우는 목표가 있는 쪽, 높낮이는 앞뒤(정면이 가장 높음), 크기는 남은 거리입니다. 장애물을 피해 걸을 방향을 안내하고, vnavmesh가 있으면 목표까지 자동으로 걸어갑니다. 길 정보에 없는 구간은 한 번 걸어서 기록해 두면 나중에 그 경로를 따라갑니다
- **전투** — 내 HP는 숫자로, 대상 HP는 백분율로 말합니다. HP와 MP는 소리로도 나타나서 가득 차 있으면 오른쪽, 다 떨어졌으면 왼쪽에서 나고, HP가 25퍼센트 아래로 내려가면 소리가 떨립니다. 적이 나를 겨냥해 기술을 쓰면 알리고, 예고된 범위 안에 서 있는 동안 반복해서 소리가 납니다. 전리품 입찰은 아이템 능력치까지 읽어 주고 숫자패드로 고를 수 있습니다
- **소지품과 장비** — 칸마다 이름·레벨·착용 가능 여부를 읽고, 못 쓰면 그 이유까지 붙입니다. 아이템 레벨과 방어력과 능력치가 안내에 들어가고, 장비세트에 들어 있는 물건은 팔기 전에 경고합니다
- **단축바** — 어느 키에 어떤 기술이 놓여 있는지 읽습니다. 배운 기술과 소지품의 포션·음식을 키보드만으로 10개 단축바 어디에나 올릴 수 있습니다
- **딥 던전** — 방을 대상으로 고를 수 있어서, 멀리 떨어져 게임이 화면에서 지운 곳까지 걸어갈 수 있습니다. 몇 층인지와 층 전체에 걸린 효과·위험을 알려 줍니다. 이 갈래는 아직 게임 안에서 검증되지 않았습니다
- **그 밖** — 감정 표현, 토벌수첩, 낚시터, 채집 지점, 탈것, 교환 창, 화폐 창, 업적, 카드 대결을 읽습니다. 마우스로만 되던 초대 수락을 키로 할 수 있고, 스크린 리더가 못 읽는 Dalamud 플러그인 목록을 모드가 대신 읽어 줍니다

### 한국 서버판이 원본과 다른 점

- **설치와 실행 방법이 완전히 다릅니다.** 한국에는 XIVLauncher가 없어서, 게임을 켠 뒤에 Dalamud를 따로 붙입니다
- 모드 안내가 한국어로 나오고, 기본 언어가 한국어로 고정되어 있습니다
- 한국 클라이언트에서 무엇이 어떻게 동작하는지 알려 주는 `/acc compat` 명령이 있습니다
- 한국 서버에만 있는 결함이 하나, 원본과 함께 겪는 결함이 둘 있습니다. [사용 안내](overlay/ko/README.ko.md)에 증상과 우회 방법이 있습니다

## 2. 단축키

기능 이름 옆 괄호는 설정 파일에 적는 이름입니다. 키를 바꾸는 방법과 설정 파일에 쓰는 독일어 키 이름 표는 [사용 안내](overlay/ko/README.ko.md)에 있습니다.

### 대상 찾기

- **Page Down** — 다음 대상 알려 주고 지정하기 (`KeyNextObject`)
- **Page Up** — 이전 대상 알려 주고 지정하기 (`KeyPrevObject`)
- **Ctrl+Page Down** — 다음 분류로 옮기기 (`KeyCategory`)
- **Ctrl+Page Up** — 이전 분류로 옮기기 (`KeyCategoryPrev`)

### 이동과 길안내

- **숫자패드 3** — 자동 이동 켜고 끄기. vnavmesh가 필요합니다 (`KeyAutoWalk`)
- **Ctrl+숫자패드 3** — 길안내 켜고 끄기 (`KeyWalkGuide`)
- **+** — 지정한 대상 따라가기 켜고 끄기. vnavmesh가 필요합니다 (`KeyFollowTarget`)
- **Ctrl+숫자패드 5** — 경로 미리 듣기 (`KeyRoutePreview`)
- **숫자패드 5** — 길안내가 가리키는 쪽으로 한 번 돌기 (`KeyFaceWaypoint`)
- **Ctrl+Shift+F1** — 클립보드에 복사해 둔 좌표로 이동하기 (`KeyGotoCoords`)
- **Ctrl+Shift+F2** — 지금 서 있는 자리의 좌표를 클립보드로 복사하기 (`KeyCopyCoords`)
- **Ctrl+Shift+F6** — 발자취 기록 켜고 끄기 (`KeyRecordTrail`)
- **N** — 방향 안내 켜고 끄기 (`KeyToggleHeading`)

`+`는 숫자패드가 아니라 일반 자판의 `+`입니다. **`N`은 한국 클라이언트에서 제작수첩과 겹칩니다.**

### 읽어 주기와 정보

- **Ctrl+F1** — 지금 쓸 수 있는 키와 명령 말해 주기 (`KeyHelp`)
- **Ctrl+F2** — 지금 초점이 있는 창 알려 주기 (`KeyWhereAmI`)
- **Ctrl+F10** — 지금 열려 있는 메뉴 읽기. 퀘스트 목록이 열려 있으면 퀘스트를 읽습니다 (`KeyReadUI`)
- **Ctrl+F11** — 말하기 즉시 멈추기 (`KeySilence`)
- **Ctrl+Delete** — 내 HP와 MP 말해 주기 (`KeyCombatStatus`)
- **Ctrl+End** — 채집가의 GP 말해 주기 (`KeySpStatus`)
- **Ctrl+L** — 레벨과 남은 경험치 말해 주기 (`KeyLevelExp`)
- **Shift+L** — 휴식 구역과 휴식 보너스 말해 주기 (`KeyRestedStatus`)
- **Ctrl+F** — 어느 딥 던전의 몇 층인지 말해 주기 (`KeyDeepFloor`)
- **Shift+F9** — 설정 메뉴 열고 닫기 (`KeyOptionsMenu`)
- **Ctrl+F3** — 소지품과 중요 아이템 읽기 (`KeyReadInventory`)
- **Shift+F3** — 소지금 말해 주기 (`KeyReadGil`)
- **Ctrl+F4** — 토벌수첩 읽기 (`KeyBestiary`)
- **Ctrl+F12** — 들어온 알림·초대 수락하기 (`KeyNotification`)

**`Ctrl+F`는 지금 동작하지 않습니다.** 원인과 되살리는 방법은 [사용 안내](overlay/ko/README.ko.md)에 있습니다.

### 전투

- **Ctrl+Shift+F3** — 범위 경고 켜고 끄기. **기본값은 꺼짐**입니다 (`KeyToggleAoeWarning`)
- **Shift+F7** — 열려 있는 전리품 입찰 읽기 (`KeyReadLootRolls`)
- **Shift+F8** — 전리품 입찰 창으로 초점 옮기기 (`KeyFocusLootRolls`)

### 장비

- **Ctrl+F6** — 착용 중인 장비 읽기 (`KeyReadEquipment`)
- **Ctrl+F7** — 가장 좋은 장비를 한 번에 착용하기 (`KeyEquipBest`)
- **Ctrl+F8** — 무작위 외모 고르기. 캐릭터 생성에서만 동작합니다 (`KeyRandomLook`)

### 기술 메뉴

- **Ctrl+F9** — 첫 단축바 읽기 (`KeyReadHotbar`)
- **Ctrl+숫자패드 0** — 기술 메뉴 열고 닫기 (`KeySkillMenu`)

기술 메뉴가 열려 있는 동안 숫자패드는 메뉴를 다루는 데만 쓰입니다. 숫자패드 8과 2로 목록을 넘기고, 4와 6으로 기술과 아이템 사이를 옮기고, 0으로 고르고, 마침표로 한 단계 뒤로 갑니다.

### 로그 되읽기

- **Alt+Page Up** — 이전 채널로 옮기기 (`KeyChatCatPrev`)
- **Alt+Page Down** — 다음 채널로 옮기기 (`KeyChatCatNext`)
- **Shift+Page Up** — 고른 채널에서 더 오래된 줄 읽기 (`KeyChatReadOlder`)
- **Shift+Page Down** — 고른 채널에서 더 새로운 줄 읽기 (`KeyChatReadNewer`)
- **Shift+Home** — 채널의 맨 처음으로 가기 (`KeyChatReadOldest`)
- **Shift+End** — 채널의 맨 끝으로 가기 (`KeyChatReadNewest`)
- **Alt+Home** — 이전 로그 탭으로 옮기기 (`KeyChatTabPrev`)
- **Alt+End** — 다음 로그 탭으로 옮기기 (`KeyChatTabNext`)
- **Enter** — 방금 읽은 줄에 같은 채널로 답장하기

**`Shift+Home`과 `Alt+Home`은 지금 동작하지 않습니다.** `Ctrl+F`와 같은 원인입니다.

### 감정 표현, 카드 대결, 플러그인 목록, 진단

- **Shift+F4** / **Shift+F5** — 이전 / 다음 감정 표현 알려 주기 (`KeyEmotePrev`, `KeyEmoteNext`)
- **Shift+F6** — 고른 감정 표현 실행하기 (`KeyEmoteDo`)
- **Ctrl+Shift+F4** / **Ctrl+Shift+F5** — 카드 대결의 판 / 내 패 읽기 (`KeyReadBoard`, `KeyReadHand`)
- **Shift+F1** / **Shift+F2** — 다음 / 이전 플러그인 알려 주기 (`KeyPluginsNext`, `KeyPluginsPrev`)
- **Shift+F12** — 고른 플러그인의 설정 열기 (`KeyPluginsConfig`)
- **Ctrl+F5** — 지금 열려 있는 창의 내부 구조를 바탕 화면에 글 파일로 저장하기 (`KeyDumpUI`)

### 게임 키와 겹치는 것

**Page Up**과 **Page Down**은 카메라 확대·축소를, **Ctrl+End**는 카메라 설정 저장을, **숫자패드 5**는 카메라를 대상 쪽으로 돌리는 기능을 겸합니다. 셋 다 화면에만 영향을 주므로 전맹 플레이에서는 겹쳐도 결과가 없고, 일부러 그렇게 두었습니다. 한국 클라이언트에서는 여기에 **`N`이 하나 더 겹칩니다.** 이것만은 실제로 창이 열립니다.

겹치는 개수는 접속할 때마다 음성으로 알려 줍니다.

## 3. 명령어

키 대신 명령어로도 쓸 수 있습니다. 대화 입력란에 그대로 칩니다.

- `/acc help` — 도움말 알려 주기
- `/acc nav` — 대상까지의 방향과 거리 말해 주기
- `/acc set` — 지금 지정한 대상을 계속 따라다니며 안내하기
- `/acc clear` — 추적 중인 대상 지우기
- `/acc near` — 가까이 있는 대상 나열하기
- `/acc status` — HP와 MP 말해 주기
- `/acc ui` — 지금 열려 있는 메뉴 읽기
- `/acc win` — 지금 초점이 있는 창 알려 주기
- `/acc keys` — 게임 단축키 설정을 바탕 화면에 저장하기
- `/acc stop` — 말하기 멈추기
- `/acc fish` — 이 지역의 낚시터 알려 주기
- `/acc fishhere` — 지금 서 있는 자리를 낚시터로 기억하기
- `/acc fishobj` — 50미터 안의 사물을 훑어 Dalamud 로그에 적기. 낚시터를 못 찾을 때 쓰는 진단용입니다
- `/acc gather` — 이 지역의 채집 지점 알려 주기
- `/acc gathergo` — 가장 가까운 채집 지점으로 이동하기
- `/acc trails` — 이 지역에 기록해 둔 발자취 나열하기
- `/acc cd` — 기술 준비됨 안내 켜고 끄기. `/acc cooldowns`도 같습니다
- `/acc soundtest` — 모드가 쓰는 소리를 차례로 들려주기
- `/acc compat` — 어느 방식으로 동작하는지 말해 주기. **한국 서버판에만 있습니다**
- `/acc lang ko` — 안내 언어 바꾸기. `ko`, `en`, `de`, `auto`를 쓸 수 있습니다
- `/acc dump <창 이름>` — 그 창의 구조를 바탕 화면에 저장하기

## 4. 무엇 위에 서 있나

이 모드는 혼자 서지 못합니다. 아래 넷이 밑에 깔려 있고, 그중 셋은 다른 사람이 만든 것입니다.

- **[원본 접근성 모드](https://github.com/derbruedi/ff14-accessibility)** (AGPL-3.0) — 기능의 대부분이 여기서 옵니다. **독일어로 개발되고 글로벌 클라이언트를 전제로 합니다.** 우리는 그 커밋 위에 한국 서버용 변경을 얹고, 한국과 무관한 수정은 원본으로 돌려보냅니다
- **[Dalamud / XIVLauncher](https://goatcorp.github.io/)** (AGPL-3.0) — 플러그인이 게임에 붙는 계층입니다. **스퀘어 에닉스의 공식 이용약관 밖에 있고, 사용에 따르는 책임은 사용하는 사람에게 있습니다**
- **[KR Dalamud 업데이터](https://github.com/MiqoKR/kr-dalamud-updater)** — 한국 서버에는 XIVLauncher가 없어서, 이 프로그램이 돌고 있는 게임에 Dalamud를 붙입니다. 이것이 없으면 모드를 설치해도 게임에 올라오지 않습니다
- **[vnavmesh](https://github.com/awgil/ffxiv_navmesh)** — 자동 이동, 따라가기, 경로 미리 듣기에 필요합니다. 없어도 나머지 기능은 그대로 동작합니다

**뒤의 둘은 재배포하지 않습니다.** 설치기가 각각의 원 저장소에서 사용자 대신 받아 옵니다.

## 5. 제안과 문제 신고

- **이 저장소의 이슈** — 한국 서버에서 겪은 것, 한국어 문장이 어색하거나 게임 표기와 다른 것, 설치기가 실패하는 것
- **[원본 저장소의 이슈](https://github.com/derbruedi/ff14-accessibility/issues)** — 한국 서버와 무관하게 모드 자체가 갖는 문제. 어느 쪽인지 모르겠으면 이쪽 저장소에 적으면 됩니다. 우리가 갈라서 올립니다

문제를 알릴 때 함께 보내면 원인을 훨씬 빨리 찾을 수 있는 것이 넷 있습니다. `Ctrl+F5`로 저장한 창 구조 파일, 바탕 화면의 `FFXIV_Keybinds.txt`, `/acc compat`이 말해 준 내용, 그리고 **무엇을 눌렀을 때 무엇이 들렸고 무엇이 들릴 것이라 생각했는지**입니다.

**한국어 표현 제안은 특히 환영합니다.** 모드가 하는 말은 게임 한국어판에 실제로 있는 낱말만 골라 쓰지만, 게임에 없는 말을 골라야 하는 자리가 남아 있습니다.

## 6. 라이선스와 고지

원본 모드가 **GNU Affero General Public License 버전 3**을 따르고, Dalamud와 goatcorp 공식 플러그인 서식도 같은 라이선스입니다. 배포하는 플러그인은 그 파생물이므로 AGPL-3.0을 따릅니다. 쓰고, 고치고, 남에게 줄 수 있습니다. 다만 **고친 판을 배포하거나 네트워크로 제공하면 그 소스 코드도 함께 공개해야 합니다.**

**이 저장소에는 아직 `LICENSE` 파일이 없습니다.** 소스를 담지 않고 원본 커밋을 가리키는 포인터와 우리 도구·문서만 담고 있어서 미뤄 둔 것인데, 공개 배포를 시작하면 필요합니다. [현황판](docs/status.md) §7에 판단 항목으로 올려 두었습니다.

배포물에 함께 들어가는 다른 사람의 소프트웨어는 **Tolk**(LGPL-3.0), **NVDA Controller Client**(LGPL-2.1), **NAudio**(MIT)이고 `THIRD-PARTY-NOTICES.md`에 적혀 있습니다. **이 파일은 남에게 전할 때 함께 있어야 합니다.**

## 7. 만든 사람들

모드 자체는 [derbruedi](https://github.com/derbruedi)가 만들고 있습니다.

큰 기능 여섯 가지는 [bladestorm360](https://github.com/bladestorm360)이 더했습니다. 적을 넘길 때 레벨과 HP를 함께 말하기와 내 HP를 숫자로 되돌리기(PR #1), 기술 설명에 효과 범위의 모양 넣기(PR #2), 대상 분류 아군과 임무(PR #3), 캐릭터 생성의 외모 단계(PR #4), 게임의 로그 탭과 필터를 따라가는 두 번째 로그 시스템(PR #5), 딥 던전 전체(PR #6)입니다.

## 8. 개발

### 저장소가 무엇을 담나

- `vendor/ff14-accessibility/` — 원본 클론의 **submodule.** 우리 변경의 원본은 거기 `kr-port` 브랜치의 커밋이고, 이 저장소는 그 팁을 가리키는 포인터 하나만 기록합니다. 이유는 [vendor.md](docs/upstream/vendor.md)에 있습니다
- `overlay/ko/` — **한국어의 원본.** `ko.json`이 `(독일어, 영어) → 한국어` 표, `terms.json`이 게임에서 뽑은 용어 대장, `guide-quotes.json`이 공식 가이드 인용 대장, `README.ko.md`가 사용자 문서입니다
- `overlay/patches/` — 한국 전용 변경의 명세
- `patches/` — **업스트림에 보낼 것**의 기준과 기록. 기각된 후보는 `rejected.md`에 남고 다시 만들지 않습니다
- `upstream.json` — 우리 커밋이 어느 업스트림 판 위에 얹혀 있는지
- `tools/` · `run/` · `docs/` — 검사기와 한국어화 도구, 실행 배치, 개발 문서

### 한국 서버라서 다른 것

여기 적은 것만 우리 몫입니다. 나머지는 원본과 같습니다.

- **FFXIVClientStructs가 7.51입니다** (글로벌은 7.55). 원본 소스를 KR로 빌드했을 때 오류는 53,971줄에서 정확히 1건이었고, 확장 메서드 shim으로 메웠습니다. **같은 소스를 글로벌로 빌드한 결과는 바뀌지 않습니다**
- **`DALAMUD_HOME`이 KR 업데이터가 만든 경로를 가리킵니다.** 업데이터가 hook 버전을 올릴 때마다 낡으므로, `run\_env.cmd`가 `Hooks` 아래에서 최신 버전을 직접 골라 이 함정을 없앱니다
- **프로필 루트가 `%APPDATA%\XIVLauncherKR`입니다.** 사용자가 업데이터에서 옮길 수 있는 값이라 박아 두지 않고 업데이터 설정에서 읽습니다
- **한국어 문장은 소스가 아니라 `overlay/ko/ko.json`에서 고칩니다.** 소스의 그 자리는 `tools/ko-apply`가 만드는 생성물이라 손대면 검사가 막습니다

### 클론 직후 한 번

git config core.hooksPath .githooks && git config commit.template .gitmessage && git submodule update --init && uv run --no-project --with pytest pytest tools -q

`vendor/`는 비공개 미러라 접근 권한이 있어야 받아집니다. 못 받은 상태에서는 vendor가 필요한 검사가 건너뛰어지고, 그것은 오류가 아닙니다. `kr-port` 브랜치를 세우는 일은 손으로 하지 않아도 됩니다. 처음 `run\build.bat`을 돌릴 때 자동으로 처리됩니다.

빌드 환경 구성은 [environment.md](docs/dev/environment.md)를 봅니다. .NET SDK 경로에 함정이 있습니다.

### 매일 쓰는 것

배치가 `run\`에 있고 **저장소 루트에서** 실행합니다. 자세한 것은 [run/README.md](run/README.md)에 있습니다.

- `play.bat` — 게임 켜고 로그인하고 Dalamud 붙이기
- `build.bat` — 소스를 고친 뒤 반영하기
- `log.bat` — 이번 판이 정상인지 기계로 판정하기
- `check.bat` — 커밋 전 검사. 전체 테스트 → vendor 기록 정합 → KR과 글로벌 양쪽 빌드
- `pack.bat` — 배포 폴더 만들기. 소스를 다시 빌드해서 담고 결과를 다시 잽니다
- `sync.bat` — 업스트림이 얼마나 앞서 갔는지 재고 올리기
- `terms.bat` · `guide.bat` — 게임 낱말과 공식 가이드에서 표기 찾기

검사만 따로 돌릴 때는 이렇게 합니다.

uv run --no-project --with pytest pytest tools -q

### 저장소가 스스로 지키는 것

- `commit-lint` — 커밋 메시지 규칙 C1~C11
- `patch-check` — 저장소가 기록한 vendor 포인터가 `kr-port` 팁이고 핀이 그 조상인지
- `docs-check` — **문서가 인용한 숫자를 산출물에서 다시 계산해 대조합니다.** 손으로 옮겨 적은 값이 낡으면 빨개집니다
- `ko-words` — 번역이 실제로 쓴 낱말을 모아 게임 덤프와 대조합니다. 용어 대장에 적는 것을 잊어도 잡힙니다
- `pack-check` — 배포 산출물이 바닐라인지, 설치 결과가 Dalamud가 읽는 모양인지. 설치기를 버리는 프로필에 대고 실제로 돌려 봅니다
- `asmref-check` · `sig-probe` · `cs-api-diff` · `asmstr` — 플러그인이 부르는 타입과 시그니처가 KR에 실제로 있는지

### 한국 서버와 무관한 것은 원본을 봅니다

**원본의 개발 문서는 대부분 독일어이고, 영어로 남아 있는 것은 FF14 문서가 아닙니다.** 원본 저장소가 범용 접근성 모드 템플릿에서 출발해서, 영어 `docs/`는 Unity·MelonLoader 시절의 잔재입니다. 걸 수 있는 것만 적습니다.

- [README.en.md](https://github.com/derbruedi/ff14-accessibility/blob/main/README.en.md) (영어) — **모드 전체의 기능·키·명령·설치.** 한국 서버 고유가 아닌 것은 여기가 기준입니다
- [docs/game-api.md](https://github.com/derbruedi/ff14-accessibility/blob/main/docs/game-api.md) (독일어) — 검증된 게임 내부 구조. FF14 문서 중 제일 중요하지만 독일어입니다
- [docs/ACCESSIBILITY_MODDING_GUIDE.md](https://github.com/derbruedi/ff14-accessibility/blob/main/docs/ACCESSIBILITY_MODDING_GUIDE.md) (영어) — 접근성 모드를 만드는 일반 원칙. **FF14 내용은 없습니다**

### 커맨드

배치가 한 가지 일을 한다면, 커맨드는 **그 일들을 어떤 순서로 엮고 어디서 멈출지**를 갖습니다.

- `/ff_help` — 목록
- `/ff_sync` — **위에서 오는 것.** 원본 모드 따라잡기
- `/ff_env` — **아래에서 오는 것.** KR Dalamud·vnavmesh·게임 패치

**아래가 위보다 먼저입니다.** 각 커맨드는 사람이 정할 것이 섞여 들어오면 커밋하지 않고 멈춥니다.
