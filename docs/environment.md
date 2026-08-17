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
| Hook 루트 | `%APPDATA%\XIVLauncherKR\addon\Hooks\dev` |

Hook 루트에는 goatcorp 공식 Dalamud stable(`15.0.3.2`)을 받아 넣고 업데이터의 `--patch-hook`으로 KR 호환 패치를 적용했다. 결과는 자체 검증까지 통과했다("Dalamud KR compatibility patch applied and verified").

적용 확인:

- `Dalamud.dll` 15.0.3.2 (IL 패치됨, 원본은 `kr-language-backup\Dalamud.dll.official`)
- `FFXIVClientStructs.dll` **7.51.0.8667** (공식 7.55.1.8875에서 다운그레이드됨)
- `version.json`의 `supportedGameVer`가 `2026.08.11` → `2026.08.05`로 재작성됨
- 마커 3종: `Dalamud.KR.Compatibility.Patch.json`, `Dalamud.KR.Language.Patch.json`, `Dalamud.KR.755.Signature.Patch.json`

### `DALAMUD_HOME`

사용자 환경변수로 걸어 뒀다.

DALAMUD_HOME=C:\Users\USER\AppData\Roaming\XIVLauncherKR\addon\Hooks\dev

글로벌 클라이언트용으로 빌드하려면 그 쉘에서만 덮어쓴다. 사용자 환경변수는 KR로 둔다.

### 아직 안 한 것 — 게임 주입은 사용자 작업이다

업데이터의 GUI 단계는 자동화하지 않았다. 프로필 초기화 CLI(`--initialize-first-install-profile`)는 안전장치가 걸려 있어 메인 프로필에 쓰지 못한다("테스트 전용 프로필만 허용"). 게임에 실제로 붙이려면 GUI로 해야 한다.

절차(README-KR.txt 기준):

1. 게임을 종료한 상태에서 `Dalamud.Updater.exe` 실행 → Check Update
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

**아직 안 정한 것**: 이 1건을 어떻게 다룰지. 후보는 (a) 7.51에 있는 다른 API로 대체, (b) 조건부 컴파일, (c) 리플렉션. 어느 쪽이든 업스트림에 올릴 성격은 아니라 오버레이/패치 영역이다. CS 7.51에 대체 API가 있는지는 **미확인**이다.

재현 명령(복사용, 저장소 루트에서):

DALAMUD_HOME="C:\Users\USER\AppData\Roaming\XIVLauncherKR\addon\Hooks\dev" C:\Users\USER\scoop\apps\dotnet-sdk\current\dotnet.exe build -c Release vendor/ff14-accessibility/FF14Accessibility/FF14Accessibility.csproj

## 5. 남은 미확인 항목

조사 §7의 12개 중 이번에 해소된 것은 7번 하나다. 새로 알게 된 것을 반영해 우선순위를 다시 매기면:

1. **Addon 시트 행 ID가 KR에서 같은가** — `sqpack`이 있으므로 **게임 실행 없이 Lumina로 확인 가능하다.** 지금 할 수 있는 것 중 가장 값싸고 가장 크다
2. **모드 단축키가 KR에서 반응하는가** — 실기 필요(§3의 GUI 주입 이후)
3. **CS 7.51 구조체 레이아웃이 KR 7.55 바이너리와 맞는가** — 실기 필요
4. 나머지는 조사 §7 그대로
