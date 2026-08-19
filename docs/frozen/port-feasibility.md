# FFXIV 접근성 플러그인 한국 서버 포팅 타당성 조사

- 조사일: 2026-08-17
- 조사 대상 커밋: `30512023e7a69683c02655506b29a7c53d2d21d5` (upstream/main, 2026-08-17, 워킹트리 clean)
- 조사 범위: 소스 읽기 전용. 프로덕션 소스 수정·의존성 설치·빌드·게임 프로세스 조작 없음.
- 표기 규칙: **확인** = 직접 읽은 파일:라인 근거 있음 / **강한 추론** = 간접 증거 있으나 실행 검증 안 됨 / **미확인** = 근거 없음.

---

> **말 바뀜 안내 (2026-08-18)**: 이 문서는 조사 당시 표현을 그대로 둔다. 지금 쓰는 말로는 "상류"는 **업스트림에 보낼 것**, "오버레이"는 **우리만 쓰는 것**이다. 커밋 앞에 붙이는 말도 `[업스트림]`·`[한국전용]`으로 바뀌었다.

## 1. 결론

포팅은 **가능하다.** 단, 통념과 원인이 다르다.

세 줄 요약:

1. **플러그인 소스에는 리전 제한이 없다.** 저장소 전체에서 Korea/Korean/KR 문자열 0건. "글로벌 전용"은 코드가 막은 게 아니라 **업스트림이 독일 클라이언트로만 개발·테스트했기 때문**이다 (`README.md:475-478`).
2. **진짜 장벽은 플러그인이 아니라 그 아래 프레임워크 계층(Dalamud)이다.** 공식 Dalamud는 언어 열거형에 한국어가 아예 없고(JP/EN/DE/FR), 한국 클라이언트에서는 키보드 입력 시그니처와 로그인 상태 판정이 어긋난다. 그런데 **이 문제는 이미 제3자가 풀어놨다** — 한국 서버용 Dalamud 배포 파이프라인이 실존하고 활발히 유지되고 있다.
3. **따라서 이 작업의 성격은 "리전 해제"가 아니라 "로케일 일반화 + KR 데이터 어댑터"다.** 플러그인이 한국어를 못 하는 부분은 (a) 모드 자체 음성 출력이 독일어/영어 2개국어로만 하드코딩된 것, (b) 독일어 게임 UI 텍스트에 문자열 매칭하는 6곳, (c) 설치 프로그램의 런처 경로다. 전부 국지적이고 전부 업스트림에 되돌릴 수 있는 형태로 고칠 수 있다.

**권장 경로: 경로 2(얇은 호환 어댑터) + 경로 1 활성화(로케일 추상화를 업스트림에 기여).** 유지되는 fork(경로 3)는 명시적으로 반대한다 — 근거는 §8.

**아직 증거가 없어 이 결론을 뒤집을 수 있는 것**: 한국 클라이언트에서 Lumina Excel 시트의 행 ID가 글로벌과 같은지 여부(§7). 이게 다르면 작업량이 국지적 수정에서 데이터 매핑 계층으로 커진다. 실기 없이는 확인 불가.

---

## 2. 현재 확인된 프로젝트 구조

### 2.1 대상 식별

- 이름: **FF14 Accessibility** (`InternalName: FF14Accessibility`, `repo.json:5`)
- 역할: 시각장애인이 FFXIV를 플레이할 수 있게 하는 **Dalamud 플러그인**. NVDA/Tolk 음성 출력, 오디오 내비게이션, 전체 키보드 조작 (`FF14Accessibility.json:4-5`)
- upstream: `https://github.com/derbruedi/ff14-accessibility` (origin, fetch/push 동일)
- 현재 checkout: branch `main`, commit `30512023`, dirty 아님. 원격 브랜치는 `origin/main`, `origin/test/prs` 2개
- 버전: 5.85.0 (`FF14Accessibility.csproj:9-11`), 태그 v4.58.0 ~ v5.85 총 48개
- 저장소 나이: 최초 커밋 2026-05-30, 총 140커밋 — **2.5개월 된 프로젝트**

### 2.2 라이선스와 재배포 범위 [확인]

- 플러그인 본체: **AGPL-3.0** (`LICENSE:1-2`)
- **중요한 타이밍 사실**: LICENSE 파일은 **최신 커밋(30512023, 2026-08-17)에서 처음 추가**됐다. `git ls-tree v5.85`로 확인한 결과 v5.85 태그에는 LICENSE가 없다. 즉 **v5.85까지 48개 릴리스는 라이선스 없이(=모든 권리 유보) 배포됐다.**
- 동봉 제3자 구성요소 (`THIRD-PARTY-NOTICES.md`):
  - Tolk.dll — LGPL-3.0 (Davy Kager)
  - nvdaControllerClient64.dll — LGPL-2.1 (NV Access)
  - NAudio 2.2.1 (7개 DLL) — MIT
  - Installer 전용: Newtonsoft.Json 13.0.3 — MIT
- **재배포 가능 여부**:
  - (a) fork 후 수정본 재배포: **가능**. 의무 = 파생물 전체를 AGPL-3.0으로 유지, 바이너리 수령자 전원에게 완전한 대응 소스 공개, 저작권/라이선스 고지 보존, 변경 사실 명시, 아카이브에 LICENSE + THIRD-PARTY-NOTICES.md 동봉(`THIRD-PARTY-NOTICES.md:8`이 명시적으로 요구).
  - (b) 한국 시장용 빌드 배포: **가능**. AGPL에는 지역·용도 제한이 없다.
  - (c) 코드를 복사하지 않는 **독립 애드온**(IPC로만 통신)이라면 파생물이 아니므로 임의 라이선스 가능. 단 Dalamud 자체에 링크하는 순간 Dalamud의 AGPL-3.0이 적용된다.
- **잔여 리스크**: 라이선스 부여 이전에 병합된 외부 PR 7건에 대한 기여자 동의가 미수령 상태라고 업스트림이 스스로 기록해 뒀다(`STATUS.md:49-56`). → **fork를 뜬다면 이전 태그가 아니라 HEAD(30512023 이후)에서 떠야 한다.**
- 법률 의견이 아니라 문서에 적힌 내용의 보고다.

### 2.3 언어·구조·빌드

- 언어: C#. `net10.0-windows` (플러그인, `FF14Accessibility.csproj:3`), `net8.0-windows` (Installer)
- 규모: .cs 80개 / **53,971줄**. 최대 파일은 `Services/UIReaderService.cs` **10,338줄**
- 배포 단위 **3개 프로젝트**:
  1. `FF14Accessibility/` — **실제 배포물**. Dalamud 플러그인 DLL. DalamudPackager가 `latest.zip` 생성
  2. `Installer/` — 최종 사용자용 설치 EXE. self-contained win-x64. 별도 릴리스 자산
  3. `tools/charamake-dump/` — 오프라인 도구. 캐릭터 생성 시트를 Lumina로 덤프. 배포 안 됨
- 빌드 진입점: **`dotnet build` 직접 실행**. 빌드 스크립트 없음. `CLAUDE.md:47`이 언급하는 `scripts/Build-Mod.ps1`은 **존재하지 않는다** — 그 CLAUDE.md는 채워지지 않은 범용 모드 템플릿(MelonLoader 언급 포함)이다.
- 필수 환경변수: **`DALAMUD_HOME`**. 모든 Dalamud 참조 어셈블리가 `$(DALAMUD_HOME)/*.dll`로 해석된다(`FF14Accessibility.csproj:118-145`: Dalamud, ImGuiScene, FFXIVClientStructs, InteropGenerator.Runtime, Lumina, Lumina.Excel — 전부 `Private=false`, 즉 재배포 안 함). `setup_dalamud_home.bat:8,33`이 `%APPDATA%\XIVLauncher\addon\Hooks\dev`로 setx.
- NuGet: DalamudPackager 15.0.0, NAudio 2.2.1
- **CI 없음**. `.github/` 디렉토리 자체가 없다. 릴리스는 메인테이너 로컬 수동 빌드.
- Debug 빌드 시 `%APPDATA%\XIVLauncher\devPlugins\FF14Accessibility`로 자동 배포(`FF14Accessibility.csproj:68-116`)

### 2.4 지원 클라이언트/런처/프레임워크

- 플러그인 프레임워크: **Dalamud**, `DalamudApiLevel 15` (`FF14Accessibility.csproj:4`, `repo.json:10`)
- 런처: **XIVLauncher** 하드 요구 (`README.md:241`)
- 배포 경로 2가지:
  1. **설치 EXE(주 경로)** — Dalamud 자체 플러그인 설치 UI가 ImGui라서 스크린리더로 읽을 수 없기 때문에 우회한다(`Installer/InstallerService.cs:16-20`). XIVLauncher 미설치 시 goatcorp에서 받아 `--silent` 설치, 플러그인 zip을 devPlugins에 풀고, **`dalamudConfig.json`을 직접 패치**해 DevMode·DevPluginLoadLocations·DevPluginSettings를 심는다(`InstallerService.cs:402-576`). vnavmesh도 puni.sh 저장소에서 받아 설치(`:278-367`)
  2. **Dalamud 커스텀 저장소(보조)** — `repo.json`이 GitHub 릴리스의 `latest.zip`을 가리킴. README가 "사이트가 보이는 도우미용 선택 경로"라고 명시(`README.md:521-523`)

### 2.5 접근성 출력 방식 [확인]

- **스크린리더 연동: Tolk 단독.** `Native/TolkNative.cs:42-72`가 Tolk_Load/Speak/Output/Braille/Silence를 P/Invoke. 모드 코드에 직접적인 nvdaControllerClient 호출이나 SAPI 호출은 없다.
- **NVDA 도달 경로**: `nvdaControllerClient64.dll`을 플러그인 폴더에서 **전체 경로로 선로딩**해서, Tolk가 네이티브 코드에서 base name으로 LoadLibrary할 때 이미 로드된 모듈을 잡게 한다(`TolkNative.cs:19-24`). 게임 디렉토리에 DLL을 복사하는 방식은 재설치 때 지워져서 2026-07-16에 음성이 끊겼기 때문에 바꾼 것.
- **문자 인코딩**: `Tolk_Output/Speak/Braille` 전부 `CharSet = CharSet.Unicode` + `[MarshalAs(UnmanagedType.LPWStr)]` (`TolkNative.cs:55-68`). **UTF-16 종단 간 전달 — 한국어는 관리 코드 구간에서 손실 없이 통과한다.**
- 전처리: `TolkService.Sanitize`(`TolkService.cs:68-87`)가 SeString 페이로드(0x02..0x03), PUA 아이콘 글리프(U+E000-F8FF), U+FFFD, C0 제어문자를 제거하고 공백을 접는다. **한글 범위는 건드리지 않는다.**
- 중단 가능: `Tolk_Output(text, true)`로 인터럽트, 0.5초 동일문자열 디바운스. `Ctrl+F11` / `/acc stop`으로 `Tolk_Silence`.
- 비음성 오디오: NAudio로 **합성**(파일 없음). 비콘(방향=피치, 좌우=팬, 거리=음량), 웨이포인트/도착/스킬준비 큐, AoE 경고 660Hz, HP/MP 톤.
- **네이티브 DLL**: Tolk.dll, nvdaControllerClient64.dll 2개만. 자체 네이티브 코드 없음.
- **IPC**: 외부 플러그인 **vnavmesh** 1개에 의존. 게이트 15개(`NavmeshIpc.cs:47-62`, `RouteService.cs:41-46`). 길찾기·자동이동 전체가 여기 얹혀 있다.
- 로그/오버레이: `IPluginLog`만. **ImGui 창은 의도적으로 하나도 없다** — 설정 UI도 넘패드로 조작하는 음성 메뉴다(`OptionsMenu.cs`, Shift+F9).

### 2.6 실제로 사용하는 게임 접근 수단 [확인]

- **Lumina Excel 시트: 약 40종** 사용. 대표: Action, Item, Quest, Map, MapMarker(서브행), TerritoryType, ClassJob, LogFilter, DeepDungeon*, CharaMake*, ENpcBase/Resident, EObj/EObjName, FishingSpot, GatheringPoint, Mount, Emote, SpecialShop, MonsterNoteTarget 등. 이름 문자열로 접근하는 **원시 시트 2종**: `InstanceContentGuide`, `ArrayEventHandler` (`DungeonSide.cs:127-128`)
- **하드코딩 행 ID**: Addon 시트 UI 라벨 행 10440, 10420-10422, 10113, 10418-10419 / 전투로그 행위자명 1227-1232, 1276-1279, 1283 / Lobby 2127 / ClassJob 16,17
- **메모리 읽기**: `unsafe` 342회 / 29파일. 대부분은 FFXIVClientStructs가 선언한 필드 경유. **플러그인이 직접 선언한 오프셋은 3곳뿐**:
  - `GameChatFilters.cs:188` `FilterBlockOffset = 0x48`
  - `TripleTriadService.cs:30-32` `576 / 1416 / 2256`
  - `CharaMakePalette.cs:48-53` `human.cmp` 레이아웃 `0x4800 / 0x1400 / 0x400`
- **시그니처 스캔: 없음.** `ISigScanner`, `ScanText`, `GetStaticAddressFromSig`, `[Signature]`, 바이트 패턴 리터럴 — 전부 0건. **플러그인은 주소 해석을 전적으로 Dalamud와 FFXIVClientStructs에 위임한다.** (이게 포팅에 결정적으로 유리하다.)
- **함수 후킹: 3개뿐**. 전부 `TooltipService.cs:81-86`, 주소는 FFXIVClientStructs의 `AtkTooltipManager.Addresses.*`에서 온다. 실패 시 툴팁 없이 degrade.
- **네트워크 opcode/패킷 처리: 없음.** `opcode`, `packet`, `NetworkMessage` 등 0건. 채팅은 Dalamud `IChatGui`와 `RaptureLogModule`로만 받는다.
- **프로세스명/모듈명 하드코딩: 없음.** `ffxiv_dx11`, `GetModuleHandle` 0건.
- **하드코딩 addon(창) 이름**: 약 90종. 전부 게임 내부 식별자라 언어 독립적이다.

### 2.7 리전 제한이 구현된 위치

**없다.** 그리고 이것이 이 조사의 핵심 발견이다.

- 저장소 전체 grep (`korea|korean|KR|한국|actoz|china|CN`, .cs/.md/.json/.txt/.ps1): **플러그인 관련 히트 0건.** 유일한 히트 2건은 `STATUS.md:1558, 3419`인데 의존성 vnavmesh의 중국어 fork(`AtmoOmen/ffxiv_navmesh-cn`) 언급이다.
- 리전/데이터센터/월드 게이트: 없음. `IsKorean`/`IsGlobal` 류 없음.
- `ClientLanguage`는 **전체 소스에서 정확히 1회** 등장: `GearInfoService.cs:291`. 그나마 게이트가 아니라 영문 직업 약어를 얻으려는 용도다.
- `IClientState.ClientLanguage`, `IDataManager.Language` 사용: 0건.

---

## 3. 글로벌 전용 제약의 실제 원인

원인은 **3개 계층으로 분리**된다. 이걸 뭉뚱그리면 포팅 설계가 틀어진다.

### 계층 1 — 프레임워크(Dalamud): 실질적 장벽, 그러나 이미 해결됨 [확인]

공식 Dalamud는 한국 클라이언트를 지원하지 않는다. 근거는 추측이 아니라 소스다:

- **`ClientLanguage` 열거형에 한국어가 없다.** goatcorp/Dalamud `Dalamud/Game/ClientLanguage.cs` 원문 확인: `Japanese, English, German, French` 넷뿐.
- 반면 **Lumina(게임 데이터 판독기)에는 있다.** NotAdam/Lumina `src/Lumina/Data/Language.cs`: `Korean = 7`, 코드 `"ko"`. **즉 파일 포맷 계층은 한국어를 읽을 수 있는데, Dalamud API 계층이 그걸 표현할 수단이 없다.**

그런데 이 간극을 메우는 **제3자 배포 파이프라인이 실존하고 현재도 유지되고 있다**:

- `MiqoKR/kr-dalamud-updater` — "KR Dalamud updater and compatibility release pipeline", **2026-08-17 푸시(조사 당일)**
- `MiqoKR/kr-dalamud-patches` — 플러그인별 KR 호환 IL 패치 매니저, 2026-08-16 푸시
- 프로필 루트가 **`%APPDATA%\XIVLauncherKR`** (글로벌은 `%APPDATA%\XIVLauncher`)
- **`HookVersion: 15.0.3.2`** → Dalamud API level = 어셈블리 major = **15**. **업스트림 플러그인이 요구하는 `DalamudApiLevel 15`와 정확히 일치한다.**
- .NET 10 Desktop Runtime x64 요구 → 플러그인의 `net10.0-windows`와 일치

이 파이프라인이 **공식 Dalamud 바이너리에 Mono.Cecil로 IL 패치를 가한다.** 무엇을 고치는지가 곧 "한국 클라이언트에서 뭐가 깨지는가"의 답이다:

`DalamudKrLanguagePatch.cs`:
- `Dalamud.Game.ClientLanguage`에 **`Korean = 6` 필드를 추가**
- `ClientLanguageExtensions.ToLumina` / `ToClientLanguage` 재작성
- `DataManager` 생성자에서 언어를 **한국어로 강제**
- `GetExcelSheet` / `GetSubrowExcelSheet`가 `Nullable<ClientLanguage>` 대신 **`Lumina.Data.Language.Korean`(=7)을 강제**하도록 IL 재작성
- **`LuminaOptions.PanicOnSheetChecksumMismatch`를 끈다** ← 한국 클라이언트 시트가 Lumina의 글로벌 기준 스키마와 체크섬이 어긋난다는 뜻

`DalamudKrSignaturePatch.cs` — `ClientStateAddressResolver.Setup64Bit`의 시그니처를 교체:
- 키보드: 글로벌 `48 8D 0C 85 ?? ?? ?? ?? 8B 04 31 85 C2 0F 85` → KR 7.55 `48 8D 0C 85 ?? ?? ?? ?? 8B 04 39 85 C2 0F 85`
- 키보드 인덱스: 글로벌 `0F B6 94 33 ?? ?? ?? ?? 84 D2` → KR `0F B6 B4 3B ?? ?? ?? ?? 40 84 F6`
- **`ClientState.IsLoggedIn` 폴백 주입**: 소스 주석 원문 — "The Korean client can expose both AgentLobby login flags as false after zone entry." 패치 후 판정식은 `AgentLobby.IsLoggedIn || AgentLobby.IsLoggedIntoZone || ClientState.TerritoryType != 0`

`DalamudKrCompatibilityPatch.cs`:
- KR 지원 게임 버전 `2026.08.05.0000.0000` vs 공식(글로벌) `2026.08.11.0000.0000`
- **FFXIVClientStructs를 다운그레이드**: 공식 `7.55.1.8875` → KR 호환 `7.51.0.8667` (SHA-256 고정, 압축 리소스로 동봉)

**이 두 가지가 이 포팅의 핵심 위험이다.** 왜냐하면:

- 플러그인의 **입력 계층 전체가 Dalamud `IKeyState`**다(`Plugin.cs:26`, 폴링 `:759-779`, 디스패치 `:1359-1543`). 키보드 시그니처가 안 맞으면 **모드의 모든 단축키가 죽는다.** 전맹 사용자용 전체 키보드 조작 모드에서 이건 기능 저하가 아니라 완전 불능이다.
- **`IsLoggedIn`이 여러 서비스의 조기 반환 게이트**다(`CooldownService.cs:79`, `EmoteService.cs:85`, `FateService.cs:49`, `HotbarService.cs:365/381/416/450/1111` 등). false면 **조용히 아무것도 안 한다.** 업스트림 CLAUDE.md가 경고하는 바로 그 실패 모드 — "모드의 침묵은 '정상인데 할 말이 없음'과 구분되지 않는다".

### 계층 2 — 모드 자체 출력: 한국어가 아예 없음 [확인]

- `Loc.cs:7-13` `LanguageMode { Auto = 0, German = 1, English = 2 }` — **2개국어뿐**
- `Loc.cs:31-39` Auto는 **Windows UI 컬처**로 해석. `"de"`면 독일어, **그 외 전부 영어**. → 한국어 Windows는 영어로 떨어진다.
- `Loc.cs:42-48` `ParseArg`는 `de/en/auto`만 인식
- **문자열 저장 방식이 문제다**: 카탈로그가 없다. `Services/AccessibilityStrings.cs`(2,547줄) + `.Chat.cs`(236줄)에 **`IsGerman ? "독일어" : "English"` 삼항 연산자가 712곳** 인라인으로 박혀 있다(`AccessibilityStrings.cs:16-18` 형태).
- **3번째 언어를 이 구조에 끼워 넣을 수 없다.** 712곳을 전부 고쳐야 하는데, 이 파일은 churn 6위(2.5개월간 37회 변경)다.
- **단, 업스트림 자신의 템플릿은 다른 구조를 규정한다**: `templates/shared/Loc.cs.template`은 언어별 `Dictionary<string,string>` + `Loc.Get("key")` 방식이고 주석에 "Weitere Sprachen nach Bedarf hinzufügen"(필요에 따라 언어 추가)이라고 적혀 있다. 업스트림 CLAUDE.md도 "ALL ScreenReader strings through `Loc.Get()`. No exceptions."라고 못 박는다. **즉 카탈로그화는 업스트림이 원래 의도한 구조로 되돌리는 작업이지, 한국 전용 하드코딩이 아니다.** → 업스트림 수용 가능성이 높다.

### 계층 3 — 독일어 게임 텍스트 매칭: 국지적, 6곳 [확인]

모드가 **말하는** 문자열은 포팅에 무해하다. 문제는 모드가 **게임 UI 텍스트와 비교하는** 문자열이다. 전수 조사 결과 6곳:

1. `UIReaderService.cs:7153` — `ConfirmButtonLabels = ["Ok", "Bestätigen"]`, 주석에 "(German client)" 명시. 확인 버튼 클릭에 사용
2. `UIReaderService.cs:5684` — `TryClickButton(addon, "Schließen")`. **ContentsTutorial 팝업의 유일한 탈출구**(게임이 ESC를 무시, `:5609-5617`). 매칭 실패 시 **팝업에 갇힌다** — 가장 심각한 단일 결함
3. `UIReaderService.cs:7529-7533` — 퀘스트 창 헤더 9종("Zusammenfassung", "Belohnung" 등) 소음 억제용
4. `UIReaderService.cs:299-300` — `YesNoLabels = ["Ja","Nein","Yes","No","??","???","Oui","Non"]`. **한국어 항목 없음**
5. `UIReaderService.cs:4377-4378` — `"fps"` / `"Bilder/Sek"` FPS 표시 억제
6. `UIReaderService.cs:796-797` — 소셜 탭 폴백 4종. 게임 텍스트 노드가 비었을 때만 쓰는 폴백이라 영향 경미

추가로 **시트 이름 ↔ UI 텍스트 조인** 4곳(`GearInfoService.cs:165-169`, `InventoryService.cs:539-557`, `BestiaryService.cs:71-134`, `ObjectNameService.cs:267-273`)이 있다. 양쪽 다 클라이언트 언어에서 나오므로 **언어가 일관되면 동작한다.** 단 `ObjectNameService`의 독일어 격변화 마커 `[a]/[p]/[t]` 제거는 한국어에서 무의미한 no-op이 된다(무해).

**중요**: 나머지 문자열 매칭은 전부 `"CMF"`, `"_CharaMake"`, `"Config"`, `"ChatLog"` 같은 **addon 내부 이름**이다. 언어 독립적이라 그대로 동작한다.

### 계층 4 — 설치·배포 경로 [확인]

- `Installer/InstallerService.cs:44` — `%APPDATA%\XIVLauncher` **하드코딩**. KR은 `%APPDATA%\XIVLauncherKR`
- `InstallerService.cs:161` — goatcorp의 **글로벌 XIVLauncher** 설치본을 받아 설치
- `InstallerService.cs:46` — `dalamudConfig.json` 직접 패치
- `FF14Accessibility.csproj:58` — Debug 배포 대상도 `XIVLauncher`
- → **설치 프로그램은 한국 환경에서 그대로는 못 쓴다.** 반면 `repo.json` 커스텀 저장소 경로는 GitHub 릴리스라 지역 무관이고, KR Dalamud 설정이 `DisableCustomRepoPlugins: false`이므로 **커스텀 저장소 경로는 살아 있을 가능성이 높다**(강한 추론).

---

## 4. 가설별 판정

### 가설 1 — 단순 지역/언어 체크

- **판정: 기각**
- 근거: 저장소 전체 grep에서 Korea/KR 0건. 리전·DC·월드 게이트 없음. `ClientLanguage` 사용 1회(`GearInfoService.cs:291`)이며 게이트가 아님. `IClientState.ClientLanguage`/`IDataManager.Language` 사용 0건
- 위치: 해당 없음(부재가 근거)
- 한국판 실행 증거: 불필요
- 틀렸을 경우 다음: 없음. 이 가설은 확정적으로 닫혔다

### 가설 2 — 한국어 UI 문자열·게임 데이터 명칭 미지원

- **판정: 확인 (단, 성격이 둘로 갈린다)**
- 근거:
  - 모드 **출력**: 한국어 없음. `Loc.cs:7-13` DE/EN 2개국어, 712개 인라인 삼항. 한국어 Windows는 영어로 폴백(`Loc.cs:35-38`)
  - 게임 **텍스트 매칭**: 독일어 리터럴 6곳(§3 계층 3). 전부 **실패해도 예외가 아니라 무동작**으로 degrade
  - 반면 게임 **콘텐츠 낭독**은 언어 무관하게 동작한다 — 게임 텍스트는 Loc를 거치지 않고 그대로 읽는다(`Loc.cs:20-23`), Tolk 경로가 UTF-16(`TolkNative.cs:55-68`)
- 위치: `Loc.cs:7-48`, `AccessibilityStrings.cs` 전체, `UIReaderService.cs:299,796,4377,5684,7153,7529`
- 한국판 실행 증거: ContentsTutorial 팝업을 열고 모드의 Enter로 닫히는지 확인. 확인 버튼이 있는 창에서 `PressFocusedOk`가 동작하는지 확인
- 틀렸을 경우 다음: 가설 7(시트 계층에서 이미 어긋남)

### 가설 3 — 글로벌판/한국판 게임 빌드·패치 시점 차이

- **판정: 확인 (외부 증거)**
- 근거: KR 지원 게임 버전 `2026.08.05.0000.0000`, 공식(글로벌) `2026.08.11.0000.0000` (`DalamudKrCompatibilityPatch.cs:11-12`). 더 결정적으로 **FFXIVClientStructs를 공식 7.55.1.8875에서 KR 호환 7.51.0.8667로 다운그레이드**해야 한다(`:15-22`)
- 위치: 외부 저장소 `MiqoKR/kr-dalamud-updater`. 업스트림 플러그인 쪽 대응 지점은 `FF14Accessibility.csproj:128-129`(CS를 `$(DALAMUD_HOME)`에서 참조)
- 한국판 실행 증거: KR Dalamud 설치 후 `FFXIVClientStructs.dll`의 FileVersion 확인. 그 버전으로 플러그인을 빌드했을 때 컴파일이 통과하는지 확인
- 틀렸을 경우 다음: 가설 5(그래도 API 레벨이 안 맞는 경우)
- **파생 요구사항**: 플러그인을 **글로벌 CS 7.55로 빌드하면 KR 런타임(7.51)에서 `MissingMethodException`/`TypeLoadException` 위험**이 있다. KR 빌드는 KR 호환 CS로 컴파일해야 한다 (강한 추론 — 실측 미완)

### 가설 4 — 메모리 레이아웃/시그니처/오프셋 차이

- **판정: 확인 (Dalamud 코어 한정). 플러그인 자체 오프셋은 미확인**
- 근거:
  - Dalamud 코어: 키보드 시그니처 2개가 실제로 다르다(글로벌 `8B 04 31` → KR `8B 04 39`, 그리고 인덱스 시그니처 전체 교체). `DalamudKrSignaturePatch.cs:11-14`
  - `IsLoggedIn`이 한국 클라이언트에서 존 진입 후에도 false (`DalamudKrSignaturePatch.cs:130-131` 주석)
  - **플러그인 자체는 시그니처 스캔을 하지 않는다** — 이건 유리한 조건이다. 자체 선언 오프셋은 3곳뿐(`GameChatFilters.cs:188` 0x48, `TripleTriadService.cs:30-32` 576/1416/2256, `CharaMakePalette.cs:48-53`)
  - 다른 KR 패치들이 같은 계열 문제를 보고: Umbra의 `AtkResNode.IsVisible` 폴백, Simple Heels의 탑승 기울기 필드 폴백 + `CalculateFloatHeight` 훅 비활성
- 위치: 플러그인 측 위험 지점 = 위 3개 오프셋 + `TooltipService.cs:81-86`(CS 주소 기반 훅 3개)
- 한국판 실행 증거:
  - `GameChatFilters`는 자체 무결성 검사가 있다(`:66-68` Broken 상태, `:813` stride 검산) → **KR에서 Broken으로 떨어지는지 로그로 확인 가능**. 이게 가장 값싼 진단이다
  - 툴팁 후킹 3개가 KR에서 주소 해석에 성공하는지 로그 확인
  - 트리플 트라이어드 보드 읽기가 쓰레기값을 내는지 확인
- 틀렸을 경우 다음: 가설 7

### 가설 5 — 플러그인 프레임워크/API 버전 차이

- **판정: 기각 (현 시점 한정)**
- 근거: KR 배포 설정 `HookVersion: 15.0.3.2` → API level **15**. 플러그인 요구 `DalamudApiLevel 15`(`FF14Accessibility.csproj:4`, `repo.json:10`)와 **일치**
- 위치: 외부 `MiqoKR/kr-dalamud-updater` `DalamudUpdaterConfig.json`
- 한국판 실행 증거: KR Dalamud 설치본의 `Dalamud.dll` 어셈블리 버전 major 확인
- 틀렸을 경우 다음: 가설 6
- **주의**: 이건 시점 의존적 판정이다. 글로벌 Dalamud가 API 16으로 올라가고 KR 파이프라인이 뒤처지면 되살아난다. **지속 감시 항목.**

### 가설 6 — 한국 클라이언트에서 프레임워크 자체가 미지원

- **판정: 기각**
- 근거: `MiqoKR/kr-dalamud-updater`가 조사 당일(2026-08-17) 푸시됨. `%APPDATA%\XIVLauncherKR` 프로필, GitHub Actions 릴리스 파이프라인, SHA-256 검증, 실패 시 롤백까지 갖춘 실사용 배포물. 부가 저장소 `kr-dalamud-patches`는 Customize+, Glamourer, Penumbra, Umbra, Simple Heels, BossModReborn, GatherBuddyReborn 7종에 대해 "격리 검증 완료" 상태를 유지 중
- 위치: 외부 저장소
- 한국판 실행 증거: 실제 설치해서 아무 플러그인이나 로드되는지 확인
- 틀렸을 경우 다음: 이 가설이 되살아나면 포팅 전체가 무의미해진다. **최우선 검증 대상.**
- **주의**: 이건 **개인 유지 프로젝트**(스타 0, 단독 메인테이너)다. 기술적으로는 열려 있지만 **공급 리스크가 크다**(§12)

### 가설 7 — 게임 데이터 시트 / Excel row ID / action·status·object ID 차이

- **판정: 미확인 — 그리고 이것이 남은 최대 불확실성이다**
- 근거(간접):
  - KR 언어 패치가 **`PanicOnSheetChecksumMismatch`를 끈다** → KR 시트가 Lumina의 글로벌 기준 스키마와 체크섬이 어긋난다는 직접 증거
  - `kr-dalamud-patches`의 BossModReborn 모듈 검증 조건이 "**KR Lumina 시트 호출**과 legacy map-effect 참조 제거"
  - 플러그인은 Addon 시트 행 ID를 하드코딩한다: 10440, 10420-10422, 10113, 10418-10419, 1227-1283, 2127
  - 원시 시트 2종을 컬럼 인덱스 가정과 함께 읽는다(`DungeonSide.cs:110-113,127-128`)
- 위치: `DeepDungeonFloor.cs:226,363-365`, `DeepDungeonNav.cs:49-51`, `GameChatFilters.cs:251-265`, `CharaMakeReader.cs:261`, `DungeonSide.cs:127-128`
- **한국판 실행 증거(필수)**: KR 클라이언트에서 `Addon` 시트 행 10440을 읽어 "층"에 해당하는 한국어 라벨이 나오는지 확인. 하나라도 어긋나면 하드코딩 행 ID 전수 재매핑이 필요하다. → **이게 §7의 1순위 항목이다**
- 틀렸을 경우 다음: 차이가 없다면 작업량이 크게 줄고 경로 2가 더 유리해진다

### 가설 8 — 네트워크 opcode / 패킷 구조 차이

- **판정: 기각**
- 근거: 플러그인에 네트워크 코드가 **존재하지 않는다**. 검색어 `opcode`, `Opcode`, `packet`, `Packet`, `NetworkMessage`, `INetworkMonitor`, `GamePacket` 전부 0건. 채팅은 Dalamud `IChatGui` + `RaptureLogModule.GetLogMessageDetail`로만 수집
- 위치: 부재가 근거. 채팅 수집은 `ChatReaderService.cs`, `ChatBackfill.cs:132-141`
- 한국판 실행 증거: 불필요
- 틀렸을 경우 다음: 없음

### 가설 9 — 프로세스명/모듈명/실행 경로/런처 차이

- **판정: 확인 (설치·빌드 계층 한정). 런타임 플러그인은 무관**
- 근거:
  - 플러그인 런타임: 프로세스명·모듈명 하드코딩 **0건**
  - Installer: `%APPDATA%\XIVLauncher` 하드코딩(`InstallerService.cs:44`), 글로벌 XIVLauncher 다운로드·설치(`:161`), `dalamudConfig.json` 패치(`:46`)
  - 빌드: `FF14Accessibility.csproj:58` Debug 배포 대상 동일
  - KR 실제 경로: `%APPDATA%\XIVLauncherKR`
- 위치: `Installer/InstallerService.cs:43-46,161`, `FF14Accessibility.csproj:56-61`
- 한국판 실행 증거: KR Dalamud 설치 후 실제 프로필 디렉토리 이름 확인, devPlugins 경로 존재 여부 확인
- 틀렸을 경우 다음: 없음. 확정

### 가설 10 — 글로벌 전용 서비스/CDN/저장소/인증 의존

- **판정: 확인 (설치 프로그램 한정)**
- 근거: Installer가 goatcorp/FFXIVQuickLauncher 릴리스(`InstallerService.cs:122-204`)와 puni.sh 저장소(`:36,278-367`, vnavmesh)에 의존. 둘 다 글로벌 생태계
- 반면 `repo.json`의 배포 링크는 GitHub 릴리스라 지역 무관
- 위치: `Installer/InstallerService.cs:36,133,161`
- 한국판 실행 증거: KR 환경에서 vnavmesh가 puni.sh 배포본 그대로 동작하는지 확인 — **vnavmesh는 길찾기 전체의 토대라 이게 깨지면 내비게이션 기능군이 통째로 죽는다**
- 틀렸을 경우 다음: 가설 6

### 가설 11 — 문자 인코딩 / 한국어 형태소·조사·숫자 읽기 등 음성 출력 계층

- **판정: 기각 (차단 요인 아님). 품질 과제로 재분류**
- 근거:
  - 인코딩: `Tolk_Output/Speak/Braille` 전부 `CharSet.Unicode` + `LPWStr`(`TolkNative.cs:55-68`) → UTF-16 무손실
  - `Sanitize`(`TolkService.cs:68-87`)는 SeString 페이로드·PUA·제어문자만 제거, 한글 미영향
  - `CleanRaceName`(`UIReaderService.cs:6273-6285`)은 유니코드 문자+공백+아포스트로피 유지 → 한글 통과
- 위치: 위와 동일
- **잔여 품질 과제**: 모드가 **조립하는** 문장의 한국어 어순·조사(예: `MenuPosition` = `"{item}, {index} von {count}"` → 한국어는 "{item}, {count} 중 {index}"). 이건 **번역 시 문장 단위로 다시 쓰면 해결**되므로 카탈로그화(§9)가 전제되면 자동으로 풀린다
- **주의**: 프로젝트 규칙상 스크린리더 발음 가공(특수문자 제거·띄어쓰기 조정 등)은 사용자 명시 지시 없이 하지 않는다. 원문 보존이 기본
- 틀렸을 경우 다음: 실기에서 Tolk가 한글을 못 넘기면 가설 6 재검토

### 가설 12 — 출력 계층은 되는데 입력 데이터 수집 계층만 실패

- **판정: 확인 — 그리고 이것이 지배적 위험이다**
- 근거: 정확히 이 형태다.
  - **출력(Tolk/NVDA)**: KR 무관하게 동작 (가설 11)
  - **입력 수집**: Dalamud `IKeyState`(키보드 시그니처 의존) + `IsLoggedIn`(KR에서 false) + Lumina 시트(언어 강제 필요) — 셋 다 KR에서 어긋난다
  - 게다가 **실패가 조용하다**: `IsLoggedIn` 게이트는 조기 반환하고(`CooldownService.cs:79` 등), 독일어 문자열 매칭은 no-op으로 떨어진다. 예외가 안 난다
- 위치: `Plugin.cs:26,759-779`(입력), `CooldownService.cs:79`·`EmoteService.cs:85`·`FateService.cs:49`·`HotbarService.cs:365,381,416,450,1111`(게이트)
- **한국판 실행 증거(최우선)**: KR + 패치된 Dalamud에서 모드 단축키 **하나라도** 반응하는지. 예: `Ctrl+F11`(음성 정지)나 `/acc status`. 이게 안 되면 나머지 조사는 전부 무의미하다
- 틀렸을 경우 다음: 가설 4로 되돌아가 시그니처 패치 적용 여부 확인

### 가설 13 — 소스상 제한은 없으나 upstream이 한국판을 테스트하지 않아 제외

- **판정: 확인**
- 근거: `README.md:475-478` 원문 — "Spieltexte (Dialoge, Menüs, Gegenstandsnamen) werden immer in der Sprache des Spiel-Clients vorgelesen. **Entwickelt und getestet wird vorrangig mit dem deutschen Client.**" (게임 텍스트는 항상 클라이언트 언어로 낭독된다. 개발과 테스트는 주로 독일어 클라이언트로 이루어진다.) 영어판 `README.en.md:460-465` 동일
- README/STATUS/known-issues/anweisung.txt/forum-post 어디에도 한국 언급 없음. **배제한 게 아니라 고려 범위 밖이었다**
- 위치: `README.md:475-478`, `README.en.md:460-465`
- 한국판 실행 증거: 불필요 (문서 근거로 충분)
- 틀렸을 경우 다음: 없음
- **함의**: 업스트림이 한국을 거부한 적이 없다. PR 7건 중 5건을 병합했고 `origin/test/prs` 스테이징 브랜치까지 운영한다. **기여 수용 가능성이 실제로 있다.**

---

## 5. 접근성 기능 인벤토리

각 기능 뒤 대괄호는 포팅 등급이다:

- **[A] 그대로 동작 가능성 높음** — 글로벌 데이터 비종속
- **[B] 로케일 대응만 필요** — 모드 출력 번역
- **[C] KR 데이터 어댑터 필요** — 시트/행 ID/문자열 매칭
- **[D] 메모리·시그니처 강종속** — 실기 검증 없이는 판단 불가
- **[E] 실기에서만 검증 가능**

### 음성 코어

- `TolkService.cs` — Tolk 음성/점자 출력, SeString 정화, 10초 중복 억제, 0.5초 인터럽트 디바운스 **[A]**
- `Native/TolkNative.cs` — Tolk P/Invoke, nvdaControllerClient64 전체경로 선로딩 **[A]**
- `AtkText.cs` — 유일한 안전 Utf8String/텍스트노드 판독기(VirtualQuery 가드) **[A]** (가드 자체는 Win32 API, 게임 무관)
- `AccessibilityStrings.cs` + `.Chat.cs` — DE/EN 문자열 표 전체(2,783줄) **[B — 최대 작업량]**
- `Loc.cs` — 언어 모드 **[B]**

### UI 낭독

- `UIReaderService.cs`(10,338줄) — 범용 화면 낭독기. 포커스 노드 추적 + 창별 특수 판독기 체인 **[C/D 혼재]**
  - 창 열림/닫힘 안내, HUD 소음 뮤트 목록, 로그인 후 정숙 구간 **[A]**
  - Talk/TalkSubtitle/_BattleTalk 대화 낭독 **[A]** (게임 텍스트 그대로)
  - SelectYesno **[C]** (`YesNoLabels`에 한국어 없음)
  - ContentsTutorial **[C — 치명적]** ("Schließen" 매칭 실패 시 팝업 탈출 불가)
  - 퀘스트 창 + 보상 셀 **[C]** (헤더 9종 독일어)
  - ConfigSystem 슬라이더/드롭다운/탭 **[C]** ("Bilder/Sek")
  - 캐릭터 생성 핸들러군 **[D]** (CustomizeData 바이트 인덱스 직접 해석)
  - 타이틀/DC 월드맵 넘패드 내비 **[A]** (UI 텍스트끼리 매칭이라 언어 일관)
  - 노드 덤프(Ctrl+F5) **[A]** — **포팅 진단 도구로 그대로 재활용 가능**
- `TooltipService.cs` — AtkTooltipManager 후킹. 아이콘 전용 버튼의 유일한 이름 출처 **[D]** (CS 주소 의존)
- `ToastService.cs` — 오류/정보/퀘스트 토스트 **[A]**
- `SpokenMenu.cs` / `OptionsMenu.cs` — 넘패드 음성 메뉴, Shift+F9 설정 **[B]**

### 채팅 (두 시스템 병행)

- `ChatReaderService.cs` — 게임 자체 탭/필터 모델 경유 라우팅 **[A]**
- `GameChatFilters.cs` — LogFilter 시트 + LogFilterConfig 바이트 + 탭 이름 **[D]** (자체 오프셋 0x48, 단 자체 무결성 검사 있음)
- `ChatTabSpeech.cs` / `ChatTabControl.cs` / `ChatBackfill.cs` **[A]**
- `MessageHistoryService.cs` / `LegacyChat*` (2개) / `ChatChannelService.cs` **[A]** (채널 ID 1/2/6/17은 실측값 — **[E]**로 재확인 필요)

### 내비게이션·월드

- `NavigationService.cs`(2,700줄) — 오브젝트 브라우저 17개 카테고리, 타겟 변경 안내, 보행 가이드, Numpad5 정면 전환 **[A/B]**
- `AutoWalkService.cs` / `NavmeshIpc.cs` / `RouteService.cs` — vnavmesh IPC 기반 자동보행·경로 **[E]** (vnavmesh의 KR 동작 여부에 전적으로 의존)
- `TrailService.cs` — 사용자 기록 경로 **[A]**
- `PlacesService.cs` — MapMarker 시트 웨이포인트, 픽셀↔월드 좌표 변환 **[C]**
- `QuestMarkerService.cs` — Map 싱글톤 마커, _ToDoList 노드 ID 70001-70099/20000-20999 **[D]**
- `HeadingService.cs` — 나침반 방위 **[B]**
- `ObjectNameService.cs` — 명명 단일 권위, 독일어 격변화 마커 제거 **[C]**
- `ObjectMemoryService.cs` / `FateService.cs` / `ShopNpcService.cs` / `SpecialShopService.cs` **[A/C]**
- `DungeonSide.cs` — EObj.Data → InstanceContentGuide **[C]** (원시 시트 컬럼 인덱스 가정)
- `CombatSide.cs` — 적/아군 분류 **[A]**

### 전투·캐릭터

- `CombatService.cs` — 전투 시작/종료, HP 임계, 적 시전 경고, 레벨업, 경험치 **[A/D]**
- `AoeWarningService.cs` / `ActionShapeService.cs` / `AoeShape.cs` — AoE 도형 판정(CastType 7종 실측) **[A]**
- `CooldownService.cs` — oGCD 준비 큐 **[A]** (단 `IsLoggedIn` 게이트 **[E]**)
- `VitalsService.cs` — HP/MP 10% 단위 톤 **[A]**
- `LootRollService.cs` — Need/Greed 굴림 **[A]**
- `HotbarService.cs` — 핫바 낭독, 넘패드 스킬 배정 메뉴 **[D]** (`IsLoggedIn` 게이트 5곳)
- `KeybindService.cs` — 게임 키바인드 덤프 + 충돌 검사 **[A]** — **포팅 진단에 유용**
- `EquipmentService.cs` / `GearInfoService.cs` — 착용 장비, 추천 장비 최적화 **[C]** (`GetExcelSheet<ClassJob>(ClientLanguage.English)` → 영문 약어 리플렉션, **KR 언어 강제 패치와 정면 충돌**)
- `InventoryService.cs` — 인벤토리, 길, 기어세트 경고 **[C]**

### 깊은 던전 (7파일)

`DeepDungeonState/Floor/RoomMap/Nav/Mesh/Panel/Text` — 층 효과·보물상자·방 지도·아이콘 전용 창 낭독 **[C/D]**. Addon 시트 행 ID 하드코딩 6개, `planmap.lgb` 파일 경로 조립, DeepDungeonMap5X 서브행 시트, 방 ID/100 인코딩 가정이 집중된 구역 — **가장 취약**

### 기타

- `TripleTriadService.cs` — 보드/패 읽기 **[D]** (자체 오프셋 576/1416/2256)
- `BestiaryService.cs` — 서식지, 몬스터까지 보행 **[C]** (독일어 격변화 정규식)
- `FishingService.cs` — 낚시터, 입질 큐 **[C]** (GatherBuddy의 KR 패치가 "낚시 Regex fallback"을 요구했다는 선례)
- `GatheringService.cs` / `EmoteService.cs` / `DalamudPluginsService.cs` **[A/C]**
- `CharaMake*` 5파일 + `ColorNamer.cs` — 캐릭터 생성. 라이브 프리뷰 모델의 CustomizeData 직접 판독, human.cmp 팔레트 **[D]**
- `ToneSynth.cs` — 공용 벨 음색 **[A]**

### 입력 처리

- **키보드**: `Plugin.cs`가 소유. `Framework.Update` → `UpdateKeyEdges`(`:759-779`)가 **Dalamud `IKeyState`만** 폴링. Win32 키보드 훅 없음, WndProc 없음. 약 50개 바인딩(`Configuration.cs:20-133`), 문자열 `"Strg+Umschalt+F1"` 형식 파싱. 게임 텍스트 입력 중에는 전부 억제(`:1210-1214`) **[D — KR 키보드 시그니처에 전적 의존]**
- **리바인딩 UI 없음.** JSON 직접 편집만 가능. `KeyNames.cs`(키 이름 낭독 + 키 녹음 헬퍼)는 **호출자가 0개** — 준비만 되고 배선 안 됨
- **게임패드**: 소스 전체에서 매핑은 **정확히 하나**
  - `Plugin.cs:28` `IGamepadState` 주입
  - `Plugin.cs:1678-1680` D-Pad 좌/우 → `_uiReader.NavigateGamepad(∓1)`
  - `UIReaderService.cs:6839-6848` — **SelectYesno가 떠 있을 때만**, 예/아니오 라벨을 **낭독만** 한다. 버튼을 누르지 않는다
  - 그 외 스틱·트리거·페이스 버튼·범용 게임패드 내비게이션 **전무**. 핫바 게임패드 크로스바는 명시적으로 제외(`HotbarService.cs:52-54`)
  - **사용자가 Xbox 게임패드를 쓰지만, 소스에 없는 매핑은 여기 적지 않는다.** 현 상태로는 게임패드 지원이 사실상 없다고 봐야 한다 **[별도 과제]**

### 설정

`Configuration.cs` — 키바인드, 채널/탭별 음성 스위치, 레거시 채팅 토글, 6종 볼륨, 로그인 정숙 시간, 낚시 오버라이드, 경로. 변경 즉시 저장. 설정 마이그레이션 11버전 **[B]**

---

## 6. 한국판과 글로벌판 사이의 확인된 차이

전부 외부 저장소 소스에서 직접 읽은 것이다.

1. **Dalamud `ClientLanguage` 열거형에 한국어가 없다** — 공식은 JP/EN/DE/FR 4개. KR 패치가 `Korean = 6`을 IL로 주입한다
2. **Lumina에는 한국어가 있다** — `Language.Korean = 7`, 코드 `"ko"`. 데이터 계층은 준비돼 있고 API 계층만 막혀 있다
3. **Excel 시트 접근을 IL로 강제 재작성해야 한다** — `GetExcelSheet`/`GetSubrowExcelSheet`가 `Lumina.Data.Language.Korean`을 강제하도록. 즉 **호출부에서 언어를 지정해도 무시된다** → `GearInfoService.cs:291`의 `ClientLanguage.English` 요청이 무력화된다
4. **시트 체크섬이 어긋난다** — KR 패치가 `PanicOnSheetChecksumMismatch`를 끈다
5. **키보드 입력 시그니처가 다르다** — 글로벌 `8B 04 31` vs KR `8B 04 39`, 인덱스 시그니처는 패턴 전체가 다름
6. **`IsLoggedIn`이 존 진입 후에도 false일 수 있다** — 패치 후 판정식 `AgentLobby.IsLoggedIn || IsLoggedIntoZone || TerritoryType != 0`
7. **FFXIVClientStructs 버전이 다르다** — 글로벌 7.55.1.8875 vs KR 호환 7.51.0.8667
8. **게임 빌드 버전이 다르다** — KR `2026.08.05.0000.0000` vs 글로벌 `2026.08.11.0000.0000`
9. **런처 프로필 경로가 다르다** — `%APPDATA%\XIVLauncher` vs `%APPDATA%\XIVLauncherKR`
10. **KR 캐릭터는 이름이 하나다** — 글로벌의 Forename+Surname 구조와 다르다 (Customize+/Penumbra KR 패치가 "한국어 단일 캐릭터명" 처리를 요구)
11. **KR 월드 ID 집합이 다르다** — 여러 KR 패치 모듈의 검증 조건에 등장
12. **`AtkResNode.IsVisible`이 KR에서 해석되지 않는 경우가 있다** — Umbra KR 패치가 폴백을 요구. **이 플러그인의 `UIReaderService`가 노드 가시성 플래그(`NodeVisibleFlag = 0x10` 등)에 크게 의존하므로 직접 관련된다**

---

## 7. 아직 증거가 없는 차이

여기 적힌 것은 **추측이 아니라 "확인 안 된 상태"라는 사실의 기록**이다. 실기 없이 메울 수 없다.

1. **[최우선] Addon 시트 행 ID가 KR에서 같은가.** 플러그인이 10440/10420-10422/10113/10418-10419/1227-1283/2127을 하드코딩한다. 다르면 전수 재매핑
2. **[최우선] 모드 단축키가 KR에서 하나라도 반응하는가.** `IKeyState` 동작 여부. 실패 시 다른 모든 작업이 무의미
3. **addon(창) 내부 이름 약 90종이 KR에서 동일한가.** 내부 식별자라 같을 가능성이 높지만(강한 추론) 미검증
4. **플러그인 자체 오프셋 3곳이 KR에서 유효한가** — `GameChatFilters` 0x48, TripleTriad 576/1416/2256, human.cmp 0x4800/0x1400/0x400
5. **툴팁 후킹 3개의 CS 주소가 KR에서 해석되는가** — CS 7.51의 시그니처가 KR 7.55 바이너리에 맞는지
6. **vnavmesh가 KR에서 동작하는가** — 내비게이션 기능군 전체의 전제
7. **플러그인을 CS 7.51로 컴파일했을 때 빌드가 통과하는가** — 7.55 전용 API를 쓰고 있으면 소스 수정 필요
8. **KR 클라이언트에 영어 시트 데이터가 존재하는가** — `GearInfoService.cs:291`의 거동 결정
9. **UI 노드 ID/타입 휴리스틱이 KR에서 유효한가** — `UIReaderService`가 창별로 실측 노드 ID에 의존(예: `_ToDoList` 70001-70099). SE가 ULD를 다시 만들면 CS가 최신이어도 깨진다
10. **KR 채팅 채널 ID(1/2/6/17)와 전투로그 범위(41-49)가 같은가**
11. **KR Dalamud가 커스텀 저장소 플러그인을 실제로 로드하는가** — 설정상 `DisableCustomRepoPlugins: false`이지만 실측 미완
12. **한국어 Windows에서 Tolk→NVDA 한글 전달이 실제로 되는가** — 코드 경로상 문제없지만(§4 가설 11) 실측 미완

**자료 부족의 소재를 명확히 하면**: 글로벌 플러그인 소스는 **충분하다**(53,971줄 전부 접근 가능, 커밋 이력·문서·라이선스 확인 완료). 부족한 것은 **한국 클라이언트 환경 자료 100%**다 — 나는 KR 클라이언트도, KR Dalamud 설치본도, KR 게임 데이터도 갖고 있지 않다.

---

## 8. Reuse / Adapt / Fork / Reimplement 비교

### 경로 1 — upstream 설정 또는 기존 다국어/리전 확장점 재사용

- **기존 확장점 존재 여부**: `Loc.cs` + `LanguageMode` 열거형이 **유일한 확장점**이고, DE/EN 2개만 표현한다. locale abstraction, provider interface, data adapter — **전부 없다.** 문자열은 712개 인라인 삼항이다
- **코드 수정 없이 가능한가**: **불가능.** `/acc lang ko`는 `ParseArg`(`Loc.cs:42-48`)에서 null을 반환한다
- **upstream이 한국 지원을 추가할 수 있는 구조인가**: **구조적으로는 아니지만, 방향은 이미 정해져 있다.** `templates/shared/Loc.cs.template`이 dictionary + `Loc.Get(key)`를 규정하고 "필요에 따라 언어 추가"라고 명시한다. 업스트림 CLAUDE.md도 같은 규칙을 강제한다. **즉 카탈로그화는 업스트림 자신의 미이행 규칙을 이행하는 작업이다**
- **평가**: 단독으로는 불가. **하지만 다른 경로의 전제 조건으로서 필수적이다.**

### 경로 2 — 별도 한국판 호환 어댑터 / 얇은 compatibility layer

- **upstream 소스를 깨끗하게 유지할 수 있는가**: **대체로 가능.** 근거:
  - 플러그인이 시그니처 스캔을 안 한다 → 주소 계층 차이는 전부 Dalamud/CS가 흡수한다 (KR Dalamud가 이미 처리)
  - 네트워크 코드가 없다 → opcode 어댑터 불필요
  - 후킹이 3개뿐 → 훅 계층 분기 최소
  - 리전 체크가 없다 → 제거할 게 없다
- **격리 가능한 차이**:
  - 문자열: `Loc.Get(key)` 카탈로그 + `ko.json` (업스트림 기여 대상)
  - 게임 텍스트 매칭 6곳: 언어별 라벨 집합으로 외부화 (업스트림 기여 대상)
  - 시트 행 ID: KR 매핑 테이블 (KR 전용 오버레이)
  - 설치/배포: KR 전용 설치 경로 (KR 전용, 업스트림과 무관)
  - 빌드: CS 7.51 참조 구성 (빌드 설정, 소스 무관)
- **공식 업데이트 후 재검증 범위를 좁힐 수 있는가**: **가능.** 어댑터가 건드리는 건 (a) 문자열 카탈로그, (b) 라벨 집합, (c) 행 ID 표 3개뿐이고 전부 데이터다. 게임 패치가 나면 데이터만 재검증하면 된다
- **평가: 최선.** 단 경로 1(카탈로그화 업스트림 기여)이 선행되지 않으면 (a)(b)가 어댑터가 아니라 fork가 된다

### 경로 3 — 유지되는 fork

- **upstream 내부 수정이 불가피한가**: **아니다.** 위에서 본 대로 필요한 변경이 전부 일반화(generalization) 형태로 표현 가능하다. "KR이면 X" 분기가 아니라 "언어별 카탈로그"·"로케일별 라벨 집합"이다
- **충돌 가능성이 높은 파일**: 정확히 **포팅이 건드려야 할 파일들이다**
  - `UIReaderService.cs` — 10,338줄, 2.5개월간 45회 변경 (churn 5위). 게임 텍스트 매칭 6곳이 **전부 여기 있다**
  - `AccessibilityStrings.cs` — 2,547줄, 37회 변경 (6위). 712개 삼항이 **전부 여기 있다**
  - `Plugin.cs` — 1,935줄, 69회 변경 (2위)
- **병합 비용**: **매우 높다.** 140커밋 중 **130+가 최근 5주에 집중**(W29:32, W30:33, W31:17, W32:15, W33:40). 태그 48개 ≈ 거의 매일 릴리스. 이력은 선형(머지 7건)이라 rebase는 깔끔하지만, **충돌 지점이 우리 변경 지점과 정확히 겹친다**
- **라이선스/배포**: AGPL-3.0이라 fork 자체는 합법. 단 HEAD 이후에서 떠야 함(§2.2)
- **fork를 선택해야만 하는 명확한 이유**: **현재 없다.** 업스트림이 PR을 실제로 병합하고(7건 중 5건) 스테이징 브랜치까지 운영한다
- **평가: 반대.** 이 저장소의 churn 프로필에서 장기 fork는 유지 비용이 기능 개발을 압도한다

### 경로 4 — 독립 재구현

- **평가: 반대.** 재사용 불가라는 강한 근거가 없다. 오히려 반대 근거가 명확하다:
  - 53,971줄에 축적된 것은 코드가 아니라 **측정된 게임 지식**이다 — 노드 ID 휴리스틱, CastType 7종, 방 ID 인코딩, 필터 블록 stride, human.cmp 레이아웃. 전부 실측으로만 얻어지는 값이고 재현하려면 같은 시간이 든다
  - 접근성 설계 자체가 비자명하다 — ImGui를 의도적으로 배제하고 넘패드 음성 메뉴로 대체한 판단, 침묵이 곧 실패인 환경에서의 중복 억제 정책 등
- 단, **게임패드 지원은 사실상 없으므로**(§5) 그 부분만은 재구현이 아니라 **신규 개발** 영역이다

### 기준별 비교

**기술적 실현 가능성**: 경로1 불가 / **경로2 높음** / 경로3 높음 / 경로4 낮음(시간)

**KR 클라이언트 버전 변화 내구성**: 경로2·3 동등 — 둘 다 KR Dalamud 파이프라인에 의존하므로 **차이가 없다.** 이 축은 경로 선택 근거가 못 된다

**upstream 업데이트 추종 비용**: **경로2 낮음**(데이터 3종만) / 경로3 매우 높음(주 30커밋, 충돌 파일 일치) / 경로4 해당없음(추종 포기 = 개선 유실)

**접근성 기능 회귀 위험**: **경로2 낮음**(업스트림 로직 그대로) / 경로3 중간(병합 실수) / 경로4 매우 높음(측정값 재현 실패)

**테스트 가능성**: **경로2 높음** — 카탈로그·라벨·행ID가 전부 데이터라 게임 없이 계약 테스트 가능 / 경로3 동일하나 회귀 표면이 넓음 / 경로4 낮음

**설치·배포 복잡도**: 세 경로 모두 KR Dalamud 선행 설치가 필요해 **동등하게 높다.** 이것이 최종 사용자 관점 최대 장벽이다

**라이선스·재배포 위험**: 경로2에서 오버레이가 업스트림 코드를 복사하지 않으면 위험 최소. 경로3은 AGPL 전체 의무 + 기여자 동의 잔여 이슈 승계. **경로2 우위**

**게임 업데이트 후 고장 탐지**: 경로2·3 동등. 단 경로2는 어댑터 데이터에 대해 **결정적 검증기**를 붙일 수 있어 약간 우위 (§10)

**rollback 용이성**: **경로2 우위** — 오버레이만 되돌리면 업스트림 원본으로 복귀. 경로3은 fork 자체가 상태라 되돌릴 지점이 모호

---

## 9. 권장 아키텍처

**경로 2를 채택하되, 그 전제로 경로 1을 만들어낸다.** 즉 "업스트림을 일반화하는 기여" + "KR 전용 얇은 오버레이" 2단 구조다.

### 저장소 구조

```
ff14-ko-accessibility/            (이 저장소, AGPL-3.0)
  vendor/ff14-accessibility/      upstream 읽기 전용 (submodule 권장)
  overlay/                        KR 전용 자산 (코드 최소, 데이터 위주)
    ko.json                       한국어 문자열 카탈로그
    ko-labels.json                게임 UI 라벨 집합 (확인/닫기/예아니오/헤더)
    ko-sheet-ids.json             KR Addon 시트 행 ID 매핑
  patches/                        업스트림 기여 대기 중인 변경 (PR 단위)
  tests/                          계약·골든 테스트
  docs/
```

### 업스트림에 기여할 일반화 (KR 언급 없이)

1. **`LanguageMode`에 언어 추가 가능 구조 도입** — 열거형 확장 + `ParseArg` 확장
2. **`AccessibilityStrings` 712개 삼항 → `Loc.Get(key)` 카탈로그 이관.** 업스트림 자신의 템플릿과 CLAUDE.md 규칙에 부합. 대규모지만 기계적이라 단계 분할 가능
3. **게임 UI 라벨 집합 6곳 외부화** — `ConfirmButtonLabels`, `"Schließen"`, 퀘스트 헤더, `YesNoLabels`, FPS 패턴, 소셜 탭 폴백을 언어별 데이터로. **업스트림에도 이익이다** — 지금 프랑스어·일본어 클라이언트에서도 이 6곳은 깨진다
4. **`GearInfoService.cs:291` 영문 약어 의존 제거** — `ClassJob.RowId`로 직접 컬럼을 찾도록. KR 언어 강제 패치와의 충돌 제거

### KR 오버레이가 소유하는 것 (업스트림에 안 올림)

1. `ko.json` 한국어 문자열 — 조사·어순을 문장 단위로 재작성
2. `ko-labels.json` KR 클라이언트 라벨
3. `ko-sheet-ids.json` — **행 ID가 실제로 다를 때만.** 같으면 이 파일은 존재하지 않는다
4. KR 설치 경로 대응 — `%APPDATA%\XIVLauncherKR`, KR Dalamud 안내
5. KR 호환 FFXIVClientStructs(7.51)로 빌드하는 구성

### 명시적으로 하지 않는 것

- upstream 소스 직접 패치 (vendor는 읽기 전용 유지)
- Dalamud 자체 패치 — **MiqoKR 파이프라인에 위임한다.** 우리가 IL 패치를 중복 구현하면 유지 대상이 하나 더 는다
- 게임 프로세스 조작·메모리 쓰기 추가

---

## 10. 첫 번째 RED 테스트 제안

**이번 단계에서는 파일을 만들지 않았다.** 아래는 다음 승인 후 작성할 첫 테스트다.

### 제안: `Loc.ParseArg("ko")`가 한국어 모드를 반환한다

- **대상 동작 하나**: 사용자가 `/acc lang ko`를 입력하면 한국어가 선택된다
- **현재 상태(RED 근거)**: `Loc.cs:42-48`의 `ParseArg`는 `de/deutsch/german`, `en/english/englisch`, `auto`만 인식하고 **그 외는 null**. `LanguageMode`(`Loc.cs:7-13`)에 Korean 자체가 없다. → **지금 작성하면 컴파일 단계에서 실패하고, 열거형을 추가해도 어서션에서 실패한다. 진짜 RED다**
- **최소 구현**: `LanguageMode`에 `Korean` 추가 + `ParseArg`에 `"ko" or "korean" or "한국어"` 분기 1줄
- **왜 이것이 첫 테스트인가**:
  1. **게임 없이 실행된다** — 순수 정적 메서드, Dalamud 의존 0
  2. **행동이 정확히 하나다** — 파싱 결과 하나만 검증
  3. **모든 후속 작업이 이 seam에 걸린다** — 문자열 카탈로그, 라벨 집합, 출력 언어 전부 "한국어 모드가 표현 가능한가"에서 출발한다
  4. **업스트림에 그대로 기여 가능한 형태다** — KR 하드코딩이 아니라 언어 추가
- **주의**: `Loc.IsGerman`이 bool이라는 점이 곧바로 드러난다(`Loc.cs:31-39`). 3개국어에서 bool은 성립하지 않으므로 **두 번째 RED는 자연히 `Loc.Current` 도입**이 된다. 이 순서가 수직 TDD로 자연스럽다

### 후속 RED 순서 (각각 하나의 행동)

2. `Loc.Current`가 `LanguageMode.Korean`일 때 한국어를 가리킨다 (bool → 3값 전환)
3. 카탈로그가 키 하나에 대해 한국어 문자열을 반환한다
4. 카탈로그에 한국어 항목이 없을 때 영어로 폴백한다
5. 확인 버튼 라벨 집합이 로케일별로 조회된다 (`ConfirmButtonLabels` 외부화)
6. `ko-labels.json`의 모든 키가 DE/EN 집합과 동일한 키 집합을 가진다 (계약 테스트)
7. `ResolveJobColumn`이 시트 언어와 무관하게 직업 컬럼을 찾는다 (`GearInfoService.cs:289-304` 일반화)

---

## 11. 실제 한국 클라이언트 검증 계획

### 테스트 계층 설계 (§E 요구사항 대응)

**1. 게임 없이 실행 가능한 단위 테스트**
- `Loc.ParseArg` / `Loc.Current` 언어 해석
- 카탈로그 조회·폴백
- 좌표 변환(`PlacesService` 픽셀↔월드), 나침반 구간 접기(`RouteService`), AoE 도형 판정(`AoeShape`) — 전부 순수 함수
- 프레임워크: 업스트림에 테스트가 **하나도 없으므로** xUnit 신규 도입. 단 vendor가 아니라 우리 저장소에

**2. 저장 샘플 기반 fixture 테스트**
- `UIReaderService`의 Ctrl+F5 노드 덤프(`:9830`)와 `KeybindService`의 키바인드 덤프(`:138-140`)를 **KR 실기에서 캡처해 fixture로 고정**한다. 이게 KR 데이터의 유일한 합법적 확보 수단이다
- 덤프에서 addon 이름·노드 ID·라벨 텍스트를 추출해 글로벌 덤프와 대조

**3. contract test (글로벌/한국 입력 → 동일 중간 표현)**
- 라벨 집합: `{de, en, ko}` 세 카탈로그가 **동일한 키 집합**을 가져야 한다
- 시트 행 ID: `ko-sheet-ids.json`이 존재한다면, 글로벌 ID 목록과 **키가 1:1 대응**해야 한다
- 이것이 "한 쪽만 조용히 비어 있는" 상황을 막는다

**4. 한국어 음성 출력 snapshot/golden 테스트**
- 대표 문장 30~50개(메뉴 위치, HP 경고, 좌표 안내, 상점 행)에 대해 **최종 발화 문자열**을 골든 파일로 고정
- `TolkService.Sanitize` 통과 후 문자열을 비교 — 한글이 정화 단계에서 손상되지 않음을 증명
- **조사·어순 회귀를 여기서 잡는다.** 단 발음 가공은 사용자 지시 없이 넣지 않는다

**5. 프레임워크 API 호환성 테스트**
- KR Dalamud의 `Dalamud.dll` 어셈블리 major == 플러그인 `DalamudApiLevel`
- `FFXIVClientStructs.dll` FileVersion이 빌드 참조 버전과 일치
- 이건 CI에서 돌릴 수 없으므로(설치본 필요) **설치 시 자체 점검 + 로그**로 구현

**6. 게임 업데이트 후 깨짐 탐지 (signature/data validation)**
- 기동 시 **결정적 검증기**를 돌린다:
  - `GameChatFilters`의 기존 무결성 검사(`:66-68`, `:813` stride 검산) 결과를 **로그가 아니라 명시적 상태로 승격**
  - 하드코딩 Addon 행 ID 6개가 비어 있지 않은 텍스트를 반환하는지
  - 툴팁 후킹 3개의 주소 해석 성공 여부
  - 실패 시 **조용히 넘어가지 말고 사용자에게 1회 음성 통보** — 침묵이 곧 오진인 환경이므로
- 이것이 §12의 "고장 탐지" 요구를 충족한다

**7. KR 실기 최소 smoke test (순서 고정)**
- S1. KR Dalamud 설치 후 플러그인이 **로드되는가** (로그에 버전 안내)
- S2. **단축키가 반응하는가** — `Ctrl+F11` 또는 `/acc status`. **실패하면 여기서 중단.** 가설 12
- S3. NVDA로 **한글이 발화되는가** — 대화창 하나 낭독
- S4. `IsLoggedIn` 의존 기능이 동작하는가 — `Ctrl+F9` 핫바 낭독
- S5. Addon 시트 행 ID 확인 — 깊은 던전 진입해 층 안내
- S6. `GameChatFilters`가 Broken이 아닌가 — 채팅 탭 전환
- S7. vnavmesh 경로 탐색 — `/acc nav`
- S8. ContentsTutorial 팝업 탈출 (`"Schließen"` 매칭 실패 확인)

**8. NVDA 실사용 흐름**
- 타이틀 → 캐릭터 선택 → 로그인 → 대화 낭독 → 이동 → 상점 → 로그아웃
- 각 단계에서 **모드 안내(한국어)와 게임 텍스트(한국어)가 구분되어 들리는지** 확인

**9. 글로벌판 회귀 테스트**
- 동일 빌드를 글로벌 클라이언트에서 돌려 DE/EN 동작이 **변하지 않았음**을 확인
- 골든 테스트를 `de`/`en`에 대해서도 유지 → 카탈로그 이관이 문자열을 바꾸지 않았음을 증명. **712개 삼항 이관의 안전망은 이것뿐이다**

### TDD 진행 규약 (다음 단계부터 적용)

- 한 번에 행동 하나
- 실패하는 테스트 먼저, **실제 RED 확인**
- 그 테스트만 통과시키는 최소 구현
- GREEN + 전체 회귀 확인
- 다음 행동으로

---

## 12. 위험, 라이선스, 업데이트 유지 전략

### 최상위 위험

1. **KR Dalamud 파이프라인 공급 리스크 [높음]**
   - `MiqoKR/*`는 스타 0, 단독 메인테이너, 개인 배포 프로젝트다. 활발하지만(당일 커밋) **버스 팩터 1**
   - 이 프로젝트가 멈추면 우리 포팅 전체가 멈춘다. **우리가 통제할 수 없는 단일 실패점**
   - 완화: 우리 산출물을 데이터 위주로 유지해 Dalamud 계층 교체 시 재작업을 최소화. 대안 파이프라인 등장을 주기 감시
2. **KR 클라이언트 버전과 CS 버전의 결합 [높음]**
   - KR은 게임 버전 2026.08.05, 필요한 CS는 7.51.0.8667(공식은 7.55.1.8875). **게임 패치마다 이 짝이 다시 맞춰져야 한다**
   - 완화: 빌드 시 CS 버전 고정 + 기동 시 버전 검증기(§11-5)
3. **업스트림 churn [중간]**
   - 주 30커밋, 거의 매일 릴리스. 우리가 vendor를 따라가는 주기가 길어지면 격차가 빠르게 벌어진다
   - 완화: submodule 포인터를 **릴리스 태그 단위로만** 올리고, 올릴 때마다 회귀 테스트(§11-9)
4. **조용한 실패 [중간, 그러나 사용자 영향 최대]**
   - `IsLoggedIn` 게이트와 문자열 매칭 실패가 **예외 없이 무동작**으로 떨어진다. 전맹 사용자는 고장과 정상을 구분할 수 없다
   - 완화: 검증기 결과를 음성으로 1회 통보(§11-6). **이건 선택이 아니라 필수 요구사항으로 취급한다**
5. **ContentsTutorial 갇힘 [낮은 빈도, 높은 심각도]**
   - `"Schließen"` 매칭 실패 시 팝업 탈출 불가. 게임이 ESC를 무시한다
   - 완화: 라벨 외부화를 **초기 작업에 포함**

### 라이선스 전략

- 우리 저장소도 **AGPL-3.0**으로 간다. 파생물이 될 가능성이 높고, 어차피 Dalamud 자체가 AGPL이다
- vendor는 **submodule로 두어 코드 복사를 피한다** — 재배포 의무 범위를 명확히 유지
- 배포 시 LICENSE + THIRD-PARTY-NOTICES.md 동봉 (`THIRD-PARTY-NOTICES.md:8` 요구)
- **fork를 뜬다면 반드시 HEAD(30512023) 이후** — 이전 태그는 라이선스 부재 구간
- 업스트림의 기여자 동의 미수령 건(`STATUS.md:49-56`)은 **우리 통제 밖**이다. 상황을 주시하되 법률 판단은 하지 않는다
- KR Dalamud 패치 도구들은 **재배포하지 않는다** — 사용자가 직접 설치하도록 안내만 한다. 그쪽 라이선스를 별도 확인해야 하고(그 저장소도 "외부 프로젝트 코드/바이너리 배포 전 라이선스 확인 필요"라고 스스로 적어뒀다), 우리가 배포 책임을 질 이유가 없다

### 업데이트 추종 전략

**여기서 결론만 냈고, 실제 규칙과 절차는 [sync.md](../upstream/sync.md)가 소유한다.** 이 조사가 세운 방침 셋은 그대로 살아 있다.

- vendor는 **업스트림 태그 단위로만** 이동 → `docs/upstream/sync.md` §4
- 이동할 때마다 회귀 검사 → §5.2, §7
- 우리가 올린 일반화가 병합되면 오버레이가 줄어든다. **크기를 건강 지표로 추적** → §12

조사 시점에 못 본 것이 하나 있었다. **업스트림이 독일어로 개발된다는 사실이 추종 비용에 들어가 있지 않았다** — 변경 이력을 한국어로 옮기지 않으면 무엇이 들어왔는지 읽을 수 있는 사람이 없다. 그건 `docs/upstream/sync.md` §6이 갖는다.

---

## 13. 다음 구현 단계

> **이 절은 착수 전 계획이고 동결이다.** 실제로 무엇이 남았는지는 [현황판](../status.md) §2가 갖는다. 여기 숫자와 단계 구분은 조사 시점 것이라 지금과 다르다 — 예를 들어 "712개 삼항"은 실측 688쌍이었고, 단계 2는 런타임 카탈로그 조회가 아니라 **소스를 생성하는 방식**으로 바뀌었다([overlay/patches/README.md](../../overlay/patches/README.md)). 맞추지 않는다.

승인 후 진행할 순서다. **각 단계는 RED → 최소 구현 → GREEN → 회귀 확인.**

**단계 0 — 실기 증거 확보 (구현 아님, 선행 필수)**
- KR 클라이언트 + KR Dalamud 환경에서 §11-7의 S1~S3만 수행
- **S2(단축키 반응)가 실패하면 이후 전부 보류하고 재설계한다**

**단계 1 — 언어 seam**
- RED 1: `Loc.ParseArg("ko")` → Korean
- RED 2: `Loc.Current` 3값화 (`IsGerman` bool 제거)

**단계 2 — 문자열 카탈로그**
- RED 3~4: 카탈로그 조회 + 폴백
- 712개 삼항을 **기능군 단위로 분할 이관**(채팅 → 내비 → 전투 → 캐릭터 생성 순). 각 이관마다 DE/EN 골든 테스트로 무변경 증명

**단계 3 — 게임 UI 라벨 외부화**
- RED 5~6: 확인 버튼 라벨 로케일 조회 + 키 집합 계약
- 6곳 전부. `"Schließen"` 우선

**단계 4 — 언어 독립 조회**
- RED 7: `ResolveJobColumn`을 RowId 기반으로

**단계 5 — 검증기**
- 기동 시 시트 행 ID·후킹·필터 무결성 점검 + 실패 시 음성 통보

**단계 6 — KR 데이터 어댑터**
- 단계 0에서 확보한 덤프로 행 ID 차이 판정. **차이가 없으면 이 단계는 삭제된다**

**단계 7 — 배포**
- KR 설치 경로 대응, CS 7.51 빌드 구성

**단계 8 — 업스트림 기여**
- 단계 1~4를 KR 언급 없는 일반화 PR로 분할 제출

---

## 14. 사용자에게 추가로 필요한 자료

조사 결과 **글로벌 플러그인 소스는 부족하지 않다.** 부족한 것은 전부 한국 클라이언트 환경 자료다. 우선순위 순으로:

1. **[필수] 한국 FFXIV 클라이언트 설치 여부와 접근 가능성** — 없으면 §11의 실기 검증 전체가 불가능하고, 이 프로젝트는 단계 1~4(로케일 일반화)까지만 진행 가능하다
2. **[필수] KR Dalamud(`MiqoKR/kr-dalamud-updater`) 설치 의사** — 비공식 제3자 IL 패치 도구다. 게임 이용약관 위반 소지와 개인 유지 프로젝트라는 공급 리스크를 감수할지에 대한 판단이 필요하다. **이건 내가 대신 결정할 사안이 아니다**
3. **[중요] KR 실기 덤프 2종** — 플러그인이 이미 갖고 있는 기능으로 생성 가능하다:
   - `Ctrl+F5` UI 노드 덤프 (`UIReaderService.cs:9830`, 바탕화면 저장)
   - `KeybindService` 키바인드 덤프 (`Desktop\FFXIV_Keybinds.txt`)
   - 단, 이건 플러그인이 KR에서 최소한 로드·동작해야 얻을 수 있다 (닭-달걀)
4. **[중요] .NET 10 SDK 설치 여부** — 이 머신에는 **SDK가 없다**(런타임 6.0.36만 확인됨). 빌드 검증을 하려면 필요하다
5. **[선택] 게임패드 지원 범위 결정** — 현재 소스의 게임패드 지원은 SelectYesno 낭독 하나뿐이다. 사용자가 Xbox 패드를 쓴다면 이건 **포팅이 아니라 신규 기능**이고 별도 계획이 필요하다
6. **[선택] 한국어 번역 톤 기준** — 모드 안내 문장 712개를 새로 쓰게 된다. 존대/평서, 용어 통일(예: aetheryte = 에테라이트/에테리테), 숫자 읽기 방식에 대한 사용자 기준이 필요하다

---

## 부록: 실행한 조사 명령과 결과 요약

- `git clone --no-checkout` + `git checkout` — upstream 클론 (vendor, 읽기 전용 유지)
- `git remote -v` / `git branch -a` / `git log` / `git status` — origin 확인, main, 30512023, clean
- `git ls-files` / `wc -l` — 155 tracked, .cs 80개 53,971줄
- `git log --format= --name-only | sort | uniq -c | sort -rn` — churn 순위
- `git log --since=90.days --oneline | wc -l` — 140
- `grep -rniE "korea|korean|KR|한국|actoz|china|CN"` — 플러그인 관련 히트 0
- `grep -rn "ISigScanner|ScanText|GetStaticAddressFromSig|\[Signature\]"` — 0건
- `grep -rn "opcode|packet|NetworkMessage"` — 0건
- `grep -rn "IsGerman" | wc -l` — 712
- `gh api repos/goatcorp/Dalamud/contents/Dalamud/Game/ClientLanguage.cs` — JP/EN/DE/FR 확인
- `gh api repos/NotAdam/Lumina/contents/src/Lumina/Data/Language.cs` — Korean=7 확인
- `gh api search/repositories` (여러 질의) — KR Dalamud 생태계 발견
- `gh api repos/MiqoKR/*` — README·트리·패치 소스 확인
- `dotnet --info` — SDK 없음, 런타임 6.0.36만

**하지 않은 것**: 프로덕션 소스 수정, 의존성 설치, 빌드, 게임 프로세스 조작, vendor 코드 패치.
