# 개발 환경 실측과 설치 결과

- 작성: 2026-08-17
- 대상 머신: 윈도 11 (Dewey 개인 PC)
- 이 문서는 **직접 확인한 값만** 적는다. 추정은 그렇게 표기한다.

## 1. 한국 클라이언트

| 항목 | 값 |
|------|-----|
| 설치 경로 | `C:\Program Files (x86)\FINAL FANTASY XIV - KOREA` |
| 게임 버전 | `2026.08.05.0000.0000` (`game\ffxivgame.ver`) |
| 실행 파일 | `game\ffxiv_dx11.exe` |
| 게임 데이터 | `game\sqpack\` — `ffxiv`, `ex1`~`ex5` |
| 부트 | `boot\FFXIV_Boot.exe`, `boot\FFXIV_Launcher.exe` |

**게임 버전이 KR Dalamud가 지원하는 버전과 정확히 같다.** `DalamudKrCompatibilityPatch.SupportedGameVersion = "2026.08.05.0000.0000"`. 타당성 조사 §4 가설 3에서 예측한 대로다.

`sqpack`이 있다는 것은 **게임을 실행하지 않고 Lumina로 KR 시트를 읽을 수 있다**는 뜻이다. 조사 §7의 1순위 미확인 항목(Addon 시트 행 ID가 KR에서 같은가)이 오프라인으로 풀린다.

### 무관한 것

- `%APPDATA%\FFXIVInjector\` — 한국 커뮤니티의 폰트/텍스트 주입 도구다(`resources\font\*.fdt`, `rawexd\*.csv`). Dalamud와 무관하고 이 프로젝트와도 무관하다. 건드리지 않는다.
- `%APPDATA%\XIVLauncher\` — 글로벌 XIVLauncher를 2026-08-17 15:00에 설치했다가 15:19에 제거한 흔적(`%LOCALAPPDATA%\XIVLauncher\.dead`). 설정 파일 3개만 남아 있다. KR 경로는 `XIVLauncherKR`이라 충돌하지 않는다.

## 2. .NET SDK — 이미 있는데 PATH가 가리고 있다

조사 보고서 §14-4는 "이 머신에 SDK가 없다"고 적었다. **틀렸다.** 실측:

- scoop에 **.NET SDK 10.0.302**가 있다 — `C:\Users\USER\scoop\apps\dotnet-sdk\current`
- 그런데 PATH의 `dotnet`은 `C:\Program Files\dotnet\dotnet.exe`로 해석되고, 그쪽은 **런타임만 있고 SDK가 없다**. 시스템 PATH가 사용자 PATH보다 앞서기 때문이다.
- `DOTNET_ROOT`는 scoop을 가리키지만 `C:\Program Files\dotnet`의 호스트는 자기 루트에서만 SDK를 찾는다. 그래서 `dotnet --list-sdks`가 비어 있다.

**빌드할 때는 절대 경로로 부른다.** PATH 조회를 아예 안 하므로 이 함정을 반복하지 않는다.

C:\Users\USER\scoop\apps\dotnet-sdk\current\dotnet.exe build -c Release

설치된 런타임: `Microsoft.NETCore.App 10.0.11`, `Microsoft.WindowsDesktop.App 10.0.11` (시스템). 플러그인의 `net10.0-windows`와 KR Dalamud Updater의 .NET 10 Desktop Runtime 요구를 둘 다 만족한다.

## 3. KR Dalamud

### 설치한 것

| 항목 | 값 |
|------|-----|
| 업데이터 | `%LOCALAPPDATA%\KR-Dalamud-Updater\app\Dalamud.Updater.exe` |
| 출처 | `MiqoKR/kr-dalamud-updater` 릴리스 `updater-v0.5.0` (2026-08-17 게시) |
| 라이선스 | **없음** — 재배포하지 않는다. 사용자가 직접 받는 것만 안내한다 |
| 프로필 루트 | `%APPDATA%\XIVLauncherKR` |
| Hook 루트 | `%APPDATA%\XIVLauncherKR\addon\Hooks\15.0.3.2` |
| 에셋 | `%APPDATA%\XIVLauncherKR\dalamudAssets\437` (44개 파일) |

업데이터 GUI의 Check Update로 공식 Dalamud stable `15.0.3.2`와 에셋 `437`을 받고 KR 호환 패치까지 자동 적용했다.

적용 확인:

- `Dalamud.dll` 15.0.3.2 (IL 패치됨, 원본은 `kr-language-backup\Dalamud.dll.official`)
- `FFXIVClientStructs.dll` **7.51.0.8667** (공식 7.55.1.8875에서 다운그레이드됨)
- `Lumina.dll` 7.6.0.0 / `Lumina.Excel.dll` 7.5.1.0
- `version.json`의 `supportedGameVer`가 `2026.08.11` → `2026.08.05`로 재작성됨
- 마커 3종: `Dalamud.KR.Compatibility.Patch.json`, `Dalamud.KR.Language.Patch.json`, `Dalamud.KR.755.Signature.Patch.json`

### `Hooks\dev`는 남겨 둔다

Check Update 이전에 공식 stable을 손으로 받아 `Hooks\dev`에 넣고 `--patch-hook`으로 패치한 적이 있다(194MB). 그 구성에는 **에셋이 빠져 있었다** — 빌드 참조로는 충분하지만 실행에는 부족했다.

지우지 않는 이유는 업데이터가 이걸 롤백 대상으로 기록해 뒀기 때문이다.

`kr-dalamud-backups\last-successful-update.json`: `PreviousHookVersion: "dev"`, `InstalledHookVersion: "15.0.3.2"`

### `DALAMUD_HOME`

사용자 환경변수로 걸어 뒀다. Check Update로 hook 경로가 `dev`에서 버전 폴더로 바뀌었으므로 그에 맞춰 갱신했다.

DALAMUD_HOME=C:\Users\USER\AppData\Roaming\XIVLauncherKR\addon\Hooks\15.0.3.2

글로벌 클라이언트용으로 빌드하려면 그 쉘에서만 덮어쓴다. 사용자 환경변수는 KR로 둔다.

**업데이터가 hook 버전을 올릴 때마다 이 값이 낡는다.** 빌드가 갑자기 Dalamud 타입을 못 찾으면 여기부터 본다.

### 아직 안 한 것 — 게임 주입

Dalamud를 게임에 붙이는 마지막 단계는 GUI 조작이라 남아 있다. 프로필 초기화 CLI(`--initialize-first-install-profile`)는 안전장치가 걸려 있어 메인 프로필에 쓰지 못한다("테스트 전용 프로필만 허용").

절차(README-KR.txt 기준):

1. ~~게임을 종료한 상태에서 `Dalamud.Updater.exe` 실행 → Check Update~~ (2026-08-17 완료)
2. 게임 실행
3. "달라무드 적용" 누름

실행 명령(복사용):

C:\Users\USER\AppData\Local\KR-Dalamud-Updater\app\Dalamud.Updater.exe

관리자 권한으로 재실행하려 들면 `--no-elevate`를 붙여 막을 수 있다.

## 4. 빌드 검증 — 조사 §7-7 해소

조사 보고서 §7의 미확인 항목 7번 "플러그인을 CS 7.51로 컴파일했을 때 빌드가 통과하는가"를 실측했다. 업스트림 소스(`vendor/`, 무수정) 대상 A/B다.

| 참조 CS 버전 | 결과 |
|--------------|------|
| 7.55.1.8875 (공식/글로벌) | **성공** — 경고 0, 오류 0 |
| 7.51.0.8667 (KR 호환) | **실패 — 오류 정확히 1건** |

유일한 오류:

```
Services/InventoryService.cs(199,28): error CS1061:
'RaptureGearsetModule'에 'IsItemRegisteredToGearset' 정의가 없음
```

호출부는 `InventoryService.cs:180-206`이다. 아이템이 기어세트에 등록돼 있는지 묻는 자리이고, 이미 `try`/`catch`로 감싸 실패 시 `false`를 돌려주게 돼 있다(주석: "시그니처로 해석되는 외부 게임 호출이라 패치가 옮기면 던진다").

**함의**: 53,971줄에서 KR 호환 CS와의 API 간극이 1개다. 조사 §12의 위험 2("KR 클라이언트와 CS 버전의 결합")가 예상보다 훨씬 얕다. 남은 위험은 컴파일이 아니라 런타임 쪽이다 — 컴파일은 되지만 7.51 구조체 레이아웃이 KR 7.55 바이너리와 어긋나는 경우는 이 검증으로 잡히지 않는다.

### 해소됨 — 2026-08-17

두 어셈블리를 `MetadataLoadContext`로 덤프해 비교한 결과, 7.51에는 **이름이 바뀐 것도 대체 API도 없고 메서드 자체가 없다.** 7.55의 시그니처는 `IsItemRegisteredToGearset(InventoryItem* item, void* itemRow = null, int equipSlotIndex = 14)`이고, 7.51의 `RaptureGearsetModule` 41개 메서드 어디에도 대응물이 없다.

확장 메서드 shim으로 메웠다 — `overlay/patches/0001`. C#이 인스턴스 메서드를 우선하므로 **글로벌(7.55) 빌드는 게임 함수를 그대로 부르고 shim을 참조조차 하지 않는다.** 실증까지 마쳤다(`overlay/patches/README.md`).

결과:

| 참조 CS 버전 | shim 적용 후 |
|--------------|--------------|
| 7.55.1.8875 (공식/글로벌) | 성공 — 경고 0, 오류 0 (바인딩 변화 없음) |
| 7.51.0.8667 (KR 호환) | **성공 — 경고 0, 오류 0** |

`bin/Release/net10.0-windows/FF14Accessibility/latest.zip`이 나온다. smoke test S1(플러그인 로드)이 이제 가능하다.

Check Update로 정식 설치된 hook(`Hooks\15.0.3.2`)에서도 **같은 오류 1건**이다. 손으로 만든 hook와 정식 hook가 빌드상 동등하다는 뜻이라, 위 결과는 수동 구성의 부작용이 아니다.

재현 명령(복사용, 저장소 루트에서):

DALAMUD_HOME="C:\Users\USER\AppData\Roaming\XIVLauncherKR\addon\Hooks\15.0.3.2" C:\Users\USER\scoop\apps\dotnet-sdk\current\dotnet.exe build -c Release vendor/ff14-accessibility/FF14Accessibility/FF14Accessibility.csproj

### 글로벌(7.55) 참조를 다시 구하는 법 — 2026-08-17 23:47 확인

업데이터의 Check Update가 공식 어셈블리를 KR 호환본으로 덮어쓰기 때문에 이 머신에는 7.55가 남지 않는다. 다시 받는다(복사용 한 줄):

curl -sS -o "C:\Users\USER\AppData\Local\Temp\dalamud-official.zip" https://goatcorp.github.io/dalamud-distrib/latest.zip && 7z x -y -o"C:\Users\USER\AppData\Local\Temp\dalamud-official-15.0.3.2" "C:\Users\USER\AppData\Local\Temp\dalamud-official.zip"

**받은 게 맞는 물건인지 해시로 확인한다.** `Dalamud.KR.Compatibility.Patch.json`의 `OfficialClientStructsSha256`과 같아야 한다 — 2026-08-17 실측에서 `913FA3ED…8A8A43`으로 일치했다. `dalamud-distrib/version`도 `15.0.3.2`를 돌려주므로 KR 업데이터가 깐 것과 같은 판이다.

그 폴더를 `DALAMUD_HOME`으로 주면 글로벌 빌드가 된다. 결과(패치 0004 포함):

| 참조 CS | 결과 |
|---------|------|
| 7.55.1.8875 (공식) | 경고 0, 오류 0 |
| 7.51.0.8667 (KR) | 경고 0, 오류 0 |

**확장 메서드 바인딩 실증도 오늘 자 어셈블리로 다시 돌렸다.** shim에 `[Obsolete(error: true)]`를 붙이면 7.55 빌드는 그대로 성공하고(확장이 아예 후보에 안 들어간다 = 글로벌은 게임 함수를 부른다), 7.51 빌드만 `InventoryService.cs:199`에서 CS0619로 정확히 1건 실패한다.

## 5. 실기 검증 결과 (2026-08-17)

캐릭터 생성 완료까지 진행했다. 근거는 전부 `%APPDATA%\XIVLauncherKR\dalamud-kr-gui.log`와 `Ctrl+F5` 노드 덤프다.

### 조사 §7 미확인 12개의 현재 상태

| # | 항목 | 상태 | 근거 |
|---|------|------|------|
| 1 | Addon 시트 행 ID 동일 여부 | **미확인** | 깊은 던전 미진입. sqpack이 있어 오프라인 확인 가능 |
| 2 | 모드 단축키 반응 | **해소** | `Ctrl+F3`·`Ctrl+F9`·`Ctrl+F5` 등이 실제 발화. 조사 §4 가설 12 통과 |
| 3 | addon 이름 90종 동일 | **대체로 해소** | `_TitleMenu`, `_CharaSelectListMenu`, `_CharaMake*` 9종이 그대로 잡힘 |
| 4 | 플러그인 자체 오프셋 3곳 | **2/3 해소** | human.cmp 팔레트 46,688색 로드, LogFilter 278행·69채널 파싱(Broken 아님). 트리플 트라이어드는 미확인 |
| 5 | 툴팁 후킹 3개 | **해소** | `[Tooltip] Hooks aktiv (Attach/Detach/DetachByAddon)` |
| 6 | vnavmesh 동작 | **미확인** | 설치와 사전 검증은 끝났고 인게임 적재가 남았다. §7 |
| 7 | CS 7.51 컴파일 | **해소** | §4 참조 |
| 8 | KR에 영어 시트 존재 | **미확인** | |
| 9 | UI 노드 ID/휴리스틱 | **부분 해소, 결함 1건 발견** | 아래 참조 |
| 10 | 채팅 채널 ID | **미확인** | 인게임 대화 미시도 |
| 11 | 커스텀 저장소 로드 | **해당 없음** | devPlugins 경로를 쓴다 |
| 12 | Tolk→NVDA 한글 전달 | **해소** | 한국어 UI 텍스트가 NVDA로 발화됨 |

### 실기에서 새로 발견한 것

1. **`AtkResNode.IsVisible()` 시그니처가 KR에서 해석되지 않는다** — 조사 §6-12가 예측한 항목이 그대로 나왔다. 60개 호출부가 전부 예외. 타이틀 메뉴 이동·창 전체 읽기·노드 덤프가 죽었다. `overlay/patches/0002`로 우회했고, **함수 자체는 KR 바이너리에 있다는 걸 확인해 `0004`에서 게임 함수 호출로 되돌렸다**(§6)
2. **확인 버튼 라벨이 독일어 하드코딩** — 조사 §3 계층 3의 1번 항목. 캐릭터 생성을 빠져나갈 수 없었다. `overlay/patches/0003`으로 수정
3. **KR 프로필 부트스트랩 3종이 없다** — 업데이터가 기존 프로필을 전제한다. `docs/kr-runtime-setup.md`
4. **키 이름 파서가 `Pos1`(Home)과 `Strg+F`를 모른다** — 바인딩 3개가 죽어 있다. KR 무관, 업스트림 결함
5. **타이틀 메뉴 항목 수가 경로에 따라 다르다** — 메뉴 전체 안내는 "1 of 5", 화살표 이동은 "1 of 6"이라고 말한다. 2026-08-17 가시성 변경 **전후 로그가 똑같으므로 회귀가 아니다**(`dalamud-kr-gui.old.log`에도 5와 6이 같이 있다). KR 무관 추정, 미조사

### 알고 받아들인 차이 — 2026-08-17 처리 완료

둘 다 조용했다. `NodeVisibilityCompat`에는 아무도 읽지 않는 `FallbackInstalled` 플래그가 있었고, 기어세트 쪽은 플래그조차 없었다. 전맹 사용자는 대체된 답과 게임의 답을 구분할 수단이 없었다.

- **노드 가시성** — 우회를 걷어냈다. 함수는 KR 바이너리에 있고 업스트림이 매칭하는 **호출부 패턴만** 없다(§6). 이제 KR 전용 시그니처로 그 함수를 찾아 ClientStructs에 주소를 넘긴다 — 답이 게임의 답 그 자체다. 시그니처가 유일하게 안 잡히면 그때만 나름의 구현으로 내려가고, 그건 디스어셈블 전사(轉寫)라 예전의 부모 사슬 추론과 다르다
- **기어세트 마크** — 그대로 id 단위다(`overlay/patches/0001`). 마테리아·염색까지 비교해 좁히면 오차 방향이 뒤집혀 "팔지 마라" 경고가 빠지는데, 업스트림이 이미 그쪽이 더 비싸다고 판단해 뒀다. 대신 **말하게 했다**

보고 방식(`overlay/patches/0004`):

| 경로 | 로그 | 기동 시 음성 | `/acc compat` |
|------|------|--------------|---------------|
| 게임 함수 (글로벌) | 매번 남는다 | 없음 | 말한다 |
| 게임 함수 + KR 시그니처 | 매번 남는다 | 없음 — 답이 같다 | 말한다 |
| 모드 내 구현 (가시성) | 경고로 남는다 | **1회** | 말한다 |
| id 단위 (기어세트) | 경고로 남는다 | **1회** | 말한다 |

지금 KR에서는 기어세트 한 줄만 기동 때 들린다. 가시성 시그니처가 게임 패치로 깨지면 그때 두 줄이 되고, **사용자는 동작이 바뀐 시점을 귀로 안다.**

### 인게임 확인 (2026-08-17 23:32~23:35)

`dalamud-kr-gui.log` 한 판 전수다.

- `[Compat] AtkResNode::IsVisible resolved by the Korean signature at 0x7FF61438E7E0` — 모듈 베이스 `0x7FF613D30000` + `0x65E7E0`이므로 **오프라인에서 찾은 그 함수가 런타임에도 그대로 잡혔다**
- 기동 음성 두 줄이 순서대로 나갔다 — 버전 안내 다음에 `Compatibility note: Gearset marks go by item ID.` 하나. `Speak`가 큐에 넣으므로 인사말을 자르지 않는다
- **로그 전체에 `[ERR]` 0건, 예외 0건.** 패치 0002 이전에는 가시성 호출부 60곳이 전부 예외였다
- 가시성에 의존하는 기능이 살아 있다 — 타이틀 메뉴 화살표 이동(항목 이름 + 위치), 창 제목·초점 읽기(`소지품`, `시스템`, `트러스트`), 로그아웃 확인 대화상자
- 종료 시 `dalamud.crashhandler.log`에 남는 `error: 0x6d` + `Terminating target process`는 **이 변경 전 다섯 판에도 같이 있다.** 이 구성의 정상 종료 흔적이지 크래시가 아니다

### 고장 주입 결과 (2026-08-18 00:10~00:12)

시그니처를 일부러 깨서 폴백 분기를 밟았다. 로드 시점에 주소를 0으로 강제하는 한 줄을 임시로 넣어(재적재로는 주소가 남아 붙어서 안 밟힌다) 두 경우를 확인했다.

| 주입 | 로그 | 기동 음성 |
|------|------|-----------|
| 0건 매칭 (첫 바이트 변경) | `signature matched 0 times, expected 1 - refused` → `using the managed replica` → `node visibility: Emulated (0x7FFE90291A58)` | **두 줄** — `Element visibility is emulated. Gearset marks go by item ID.` |
| 39,573건 매칭 (`48 85 C9`만) | `matched 39573 times, expected 1 - refused` → 같은 폴백 | 두 줄 |

**여럿 중 첫 번째를 집지 않는다**는 게 이 두 번째 줄로 실증됐다.

여기서 버그 둘이 나왔고 `overlay/patches/0005`로 고쳤다. `AtkResNode.Addresses`가 ClientStructs 어셈블리의 정적이라 우리가 넣은 주소가 플러그인보다 오래 산다 — 모드 내 구현이 설치된 채 재적재되면 CS가 언로드된 어셈블리의 포인터를 계속 부른다. 반대로 게임 주소를 0으로 되돌리면 **Dalamud 자신의 `DtrBar.FixCollision`이 매 프레임 예외를 던진다**(0.5초 창에 9건). 그래서 폴백 포인터만 회수하고 게임 주소는 둔다. 상세는 `overlay/patches/README.md` 0005 항목.

### 인게임 확인된 나머지

- `/acc compat` → `Visibility: the game's own function via the Korean signature. Gearset marks: by item ID.` (00:05:10)
- Ctrl+F5 → `22 windows, 383 nodes` 바탕화면 저장 (00:01:45). 이 판정 자체가 노드 가시성을 쓰는 경로다
- 폴백이 설치된 상태로 게임을 종료해도 언로드가 깨끗했다 (00:13:59 `Tolk entladen` → `Finished unloading`)

### 남은 것 하나

`0005`가 들어간 빌드의 **첫 적재**를 아직 못 봤다. 확인하려고 재적재를 걸었을 때 클라이언트가 이미 종료돼 있었다(00:14:00 `Session has ended.`).

다음 실행 때 `dalamud-kr-gui.log`에서 두 줄만 본다. 게임 안에서 뭘 할 필요 없다 — 적재만 하면 찍힌다.

- `[Compat] AtkResNode::IsVisible resolved by the Korean signature at 0x…` (`already set`이 아니라 이쪽이어야 한다. 새 프로세스라 주소가 비어 있으므로)
- `DtrBar.FixCollision` 예외 0건

### 검증 도구에 대해 알아낸 것

**게임에 키를 주입하는 방식은 이 클라이언트에서 안 통한다.** `SendInput`으로 스캔코드를 넣고 창이 포그라운드인 것까지 확인했는데(`GetForegroundWindow`가 게임 핸들) `Ctrl+F2`가 로그에 아무 흔적을 남기지 않았다. 게임이 주입된 입력을 걸러내는 것으로 보인다(미확인 추정 — 확인 방법은 다른 주입 API로 같은 키를 넣어 비교). 그래서 **키가 필요한 검증은 사람이 눌러야 한다.** 반면 DLL을 덮어 재적재를 유발하는 경로는 입력이 필요 없어서 자동화된다.

Git Bash에서 `/acc compat` 같은 인자를 넘기면 MSYS 경로 변환이 `C:/Users/.../acc compat`으로 바꿔 버린다. 넘길 때는 `MSYS_NO_PATHCONV=1`을 붙인다.

## 6. KR 바이너리에서 IsVisible 찾기 (2026-08-17)

게임을 켜지 않고 `ffxiv_dx11.exe`를 직접 뒤져서 얻은 결과다. 도구는 `tools/sig-probe`이고, **그 도구가 믿을 만한지부터 확인했다** — Dalamud가 실제 게임 프로세스에서 해석해 캐시해 둔 시그니처 2,203건을 전부 같은 주소로 재현한다(`cachedSigs\cs.json`, 불일치 0건).

| 시그니처 | 결과 |
|----------|------|
| `E8 ?? ?? ?? ?? 3C 01 75 7F` (업스트림) | **0건** — ClientStructs가 왜 비는지 확정 |
| `E8 ?? ?? ?? ?? 3C 01 75 ??` (점프 거리만 완화) | 582건 / 서로 다른 대상 157개 — **못 쓴다** |

그래서 호출부가 아니라 함수를 찾았다. 두 가지 독립 근거가 같은 주소를 가리킨다.

- **위치** — `AtkResNode` 멤버 함수 83개 중 82개가 KR에서 해석된다(못 잡히는 하나가 `IsVisible`이다). `0x65E7E0`은 그 무리 안에서 **`SetPriority`(0x65E7C0)와 `ToggleVisibility`(0x65E810) 사이**에 끼어 있고, 어떤 CS 시그니처도 이 주소를 주장하지 않는다
- **본문** — 38바이트다. `NodeFlags.Visible`(0xAE의 0x10, CS 7.51 메타데이터로 확인)을 보고, `DrawFlags`(0xB0)의 0x40000 비트가 서 있으면 거부한다. **부모 사슬을 걷지 않는다** — 패치 0002의 부모 사슬은 게임 동작에 대한 오해였다

무리 안의 다른 후보 둘은 본문이 배제한다. `0x65E850`은 0x10이 아니라 0x20(`Enabled`) 비트를 보고, `0x68B170`은 접근자 모양이 아니다.

```
48 85 C9                        test rcx, rcx
74 1E                           je   false
F7 81 AC 00 00 00 00 00 10 00   test [rcx+0xAC], 0x100000   ; NodeFlags.Visible
74 12                           je   false
F7 81 B0 00 00 00 00 00 04 00   test [rcx+0xB0], 0x40000    ; DrawFlags
75 06                           jne  false
B8 01 00 00 00                  mov  eax, 1
C3                              ret
32 C0                           xor  al, al
C3                              ret
```

점프 거리 셋을 `??`로 둔 본문 전체가 **정확히 1건** 잡힌다. 앞부분(플래그 검사)만 쓰면 15건인데 호출자들이 같은 검사를 인라인하기 때문이다 — 그래서 시그니처가 `ret`까지 간다.

**재확인 명령**(게임 패치 후 이걸 먼저 돌린다. 이 검사는 테스트에도 들어 있다 — `tools/sig-probe/tests/test_shipped_signature.py`가 패치 파일에서 시그니처를 꺼내 대조한다):

uv run --no-project --with pytest pytest tools/sig-probe/tests -q

## 7. vnavmesh 사전 검증 (2026-08-18)

게임을 켜지 않고 할 수 있는 검증은 전부 통과했다. **인게임 적재와 실제 동작은 아직 미확인이다** — 키를 사람이 눌러야 하고 이 클라이언트에는 키 주입이 통하지 않는다(§5). 확인 방법은 `docs/kr-runtime-setup.md` §10.

받은 것은 vnavmesh **1.2.3.13**이고 `https://puni.sh/api/repository/veyn` 매니페스트를 거쳤다. DalamudApiLevel 15, ApplicableVersion any. 업스트림 인스톨러가 쓰는 것과 같은 출처다(`Installer/InstallerService.cs:36`). 설치 경로와 절차는 `docs/kr-runtime-setup.md` §8.

**재배포하지 않는다.** vnavmesh는 `awgil/ffxiv_navmesh`이고 **LICENSE 파일이 없다.** KR Dalamud 도구(§3)와 같은 취급이다.

### 어셈블리 참조

vnavmesh는 FFXIVClientStructs **7.51.0.8681**을 참조한다. KR이 깔아 둔 것은 **7.51.0.8667**이다(§3). 같은 7.51 라인의 리비전 차이다 — 7.55 기준으로 빌드된 물건이 아니다.

### 멤버 참조

`tools/asmref-check`로 검사했다. 이번에 새로 만든 도구다.

| 대상 | 검사 | missing-type | missing-member | arity | sig-diff |
|------|------|--------------|----------------|-------|----------|
| FF14Accessibility (교정용) | 906 | 0 | 0 | 0 | 0 |
| vnavmesh 1.2.3.13 | 659 | 0 | 0 | 0 | 0 |

FF14Accessibility를 같이 돌린 것은 도구를 교정하기 위해서다. 이쪽은 KR 실기에서 동작하는 것이 이미 증명돼 있다(§5).

독립 구현 하나를 따로 짜서 교차 확인했다. SRM으로 직접 색인하는 쪽인데 vnavmesh 550건 검사에 미해결 0이었다. 검사 대상 수가 다른 것은 서명 타입을 어디까지 포함하느냐가 달라서고, 결론은 같다.

### 시그니처

`tools/asmstr`(새 도구)로 시그니처 문자열을 뽑고 기존 `tools/sig-probe`로 해석했다. 대상 바이너리는 KR `C:\Program Files (x86)\FINAL FANTASY XIV - KOREA\game\ffxiv_dx11.exe`.

| 대상 | UNIQUE | NOT FOUND | AMBIGUOUS |
|------|--------|-----------|-----------|
| vnavmesh | 6 | 0 | 0 |
| FF14Accessibility (대조군) | 1 | 0 | 0 |
| `cachedSigs\cs.json` 표본 20건 (대조군) | 20 | 0 | 0 |

### 시그니처 문자열은 두 군데에 들어간다

Dalamud 플러그인에서 시그니처가 어셈블리에 박히는 자리가 둘이다.

- `ScanText("...")` 호출 → `#US` 힙에 UTF-16
- `[Signature("...")]` 특성 → `#Blob` 힙에 UTF-8. 특성 인자는 인터닝이 아니라 직렬화되기 때문이다

vnavmesh는 양쪽을 다 쓴다. `#US`만 읽었으면 절반만 보고 통과시킬 뻔했다.

### 한국 커뮤니티는 vnavmesh를 안 건드린다

`MiqoKR/kr-dalamud-patches`의 catalog에는 Customize+ 하나만 stable로 올라 있고, 패치 대상은 Glamourer·SimpleHeels·BossMod·GatherBuddy·Penumbra·Umbra다. **vnavmesh는 목록에 없다.**

그 패치들은 한국어 캐릭터명·월드 ID 같은 데이터 문제를 고치는 것이라 충돌 지오메트리만 다루는 vnavmesh와 결이 다르다. 다만 이것은 "패치가 필요 없다"는 증거가 아니라 **아무도 안 했다**는 사실일 뿐이다.
