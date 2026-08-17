# KR 실행 환경 구축 절차

- 작성: 2026-08-17
- 상태: **이 절차 그대로 캐릭터 생성 완료까지 검증됨**
- 대상: 프로필이 없는 머신에서 KR 클라이언트에 플러그인을 붙이기까지

`docs/environment.md`가 "무엇이 어디 있는가"를 적는다면 이 문서는 "무엇을 어떤 순서로 하는가"를 적는다.

## 이 절차가 왜 따로 필요한가

KR Dalamud 업데이터는 **기존 `%APPDATA%\XIVLauncherKR` 프로필이 있다고 전제한다**(README-KR.txt: "완전히 새 PC에 프로필을 처음 만드는 설치 프로그램은 아닙니다"). 글로벌은 XIVLauncher가 그 프로필을 만들어 주지만 한국어 런처는 그런 일을 하지 않는다.

그래서 **XIVLauncher가 해 주던 일 세 가지를 사람이 대신 해야 한다.** 하나라도 빠지면 아래처럼 실패한다.

| 빠진 것 | 증상 |
|---------|------|
| `dalamudConfig.json`, `installedPlugins` | 업데이터가 오류 창을 무한 생성 |
| `DALAMUD_RUNTIME` 환경변수 | "적용 완료"가 뜨는데 실제로는 게임 안에서 CLR이 안 뜸 |
| dev 플러그인 설정 시딩 | 플러그인이 **조용히** 안 뜸 (오류도 없음) |

## 0. 설치기가 이 절차를 대신한다

아래 §3~§8은 **손으로 하는 경우의 절차**다. 지금은 설치기가 같은 일을 한다 — `run\pack.bat`이 낸 `dist/` 폴더를 옮기고 그 안의 EXE를 실행하면 프로필 부트스트랩부터 vnavmesh 시딩까지 끝난다. KR화한 지점과 근거는 [overlay/patches/README.md](../overlay/patches/README.md) `0006`.

이 문서를 남겨 두는 이유는 둘이다. **설치기가 무엇을 왜 하는지의 근거**이고, 설치기가 막혔을 때 손으로 짚는 순서다.

무엇을 찾았는지만 보려면(설치는 안 한다):

dist\FF14AccessibilityInstaller-KR.exe --check

## 1. 사전 조건

- 한국어 FFXIV 클라이언트
- Microsoft .NET 10 Desktop Runtime x64 (시스템 설치, `C:\Program Files\dotnet`)
- .NET 10 SDK — 빌드용. 이 머신은 scoop에 있고 PATH가 가리므로 **절대 경로로 부른다**(`docs/environment.md` §2)

## 2. KR Dalamud 업데이터 설치

`MiqoKR/kr-dalamud-updater` 릴리스의 Portable zip을 받아 쓰기 가능한 폴더에 푼다. 재배포하지 않는다(라이선스 미표기).

현재 위치: `%LOCALAPPDATA%\KR-Dalamud-Updater\app\Dalamud.Updater.exe`

## 3. 프로필의 빠진 조각 만들기

업데이터의 사전 검사(`Program.cs`의 `GetMissingParts`)가 여섯 가지를 확인하는데, 새 프로필에는 둘이 없다.

mkdir "%APPDATA%\XIVLauncherKR\installedPlugins" "%APPDATA%\XIVLauncherKR\devPlugins"

그리고 `%APPDATA%\XIVLauncherKR\dalamudConfig.json`에 아래 한 줄만 넣는다. Dalamud가 첫 실행에서 나머지 기본값을 채운다. **BOM 없이 저장한다.**

{"$type":"Dalamud.Configuration.Internal.DalamudConfiguration, Dalamud"}

## 4. `DALAMUD_RUNTIME` 환경변수

`Dalamud.Boot.dll`이 게임 안에서 .NET 런타임을 찾을 때 읽는 변수다(바이너리 문자열로 확인). 글로벌에서는 XIVLauncher가 자기 전용 런타임을 받아 이 값을 넣어 준다. 없으면 Boot 로그에 `Error: Unable to find .NET runtime path`가 찍히고 `Dalamud.Boot::Initialize returned 2147942403`으로 끝난다.

setx DALAMUD_RUNTIME "C:\Program Files\dotnet"

시스템 dotnet이면 충분하다. `Dalamud.runtimeconfig.json`이 `Microsoft.NETCore.App 10.0.0` + `Microsoft.WindowsDesktop.App 10.0.0`에 `rollForward: LatestMinor`를 요구하는데 거기에 10.0.11이 둘 다 있다.

**변수를 넣은 뒤 게임을 새로 켜야 한다.** 프로세스는 시작할 때 환경을 물고 간다.

## 5. Dalamud 내려받기와 KR 패치

게임을 끈 상태에서 업데이터를 실행하고 **Check Update**를 누른다. 공식 stable과 에셋을 받아 KR 호환 패치까지 적용한다.

결과: `addon\Hooks\<버전>\`(KR 패치 마커 3종 + FFXIVClientStructs 7.51.0.8667), `dalamudAssets\<번호>\`

hook 폴더 이름이 버전이라 **업데이트마다 바뀐다.** 빌드용 `DALAMUD_HOME`도 같이 옮겨야 한다.

## 6. 플러그인 빌드와 배치

저장소 루트에서 vendor 클론에 KR 패치를 적용한 뒤 빌드한다(`overlay/patches/README.md` 참조).

빌드 (한 줄):

DALAMUD_HOME="C:\Users\USER\AppData\Roaming\XIVLauncherKR\addon\Hooks\15.0.3.2" C:\Users\USER\scoop\apps\dotnet-sdk\current\dotnet.exe build -c Release vendor/ff14-accessibility/FF14Accessibility/FF14Accessibility.csproj

산출물 `bin/Release/net10.0-windows/FF14Accessibility/latest.zip`을 `%APPDATA%\XIVLauncherKR\devPlugins\FF14Accessibility\`에 푼다.

## 7. dev 플러그인 설정 시딩

**게임을 끈 상태에서** 한 번만 하면 된다. Dalamud는 종료할 때 설정을 저장하므로 켜져 있으면 덮인다.

uv run --no-project python tools/kr-setup/seed_devplugin.py "%APPDATA%\XIVLauncherKR\dalamudConfig.json" "%APPDATA%\XIVLauncherKR\devPlugins\FF14Accessibility\FF14Accessibility.dll" FF14Accessibility

세 조건을 동시에 맞춘다 — `DevMode`, `DevPluginSettings.StartOnBoot`, `DefaultProfile`의 **같은 GUID**로 `IsEnabled`. 근거는 업스트림 `Installer/InstallerService.cs:505-576`이 디컴파일로 확인해 둔 것이고, 하나라도 어긋나면 오류 없이 조용히 안 뜬다.

`AutomaticReloading`을 켜 두므로 **이후 재빌드는 파일만 덮어쓰면 게임 재시작 없이 반영된다.**

## 8. vnavmesh 설치

자동 이동 계열 단축키가 이 플러그인을 부른다. 없으면 넘패드3에서 `Auto-walk not available. The vnavmesh plugin is missing or not loaded.`가 들린다(`%APPDATA%\XIVLauncherKR\dalamud-kr-gui.log:6206`, 2026-08-18 00:07:16). 결함이 아니라 미설치다.

**접근성 모드가 요구하는 외부 플러그인은 이것 하나뿐이다.** 업스트림 소스에서 외부 IPC 호출을 전수로 뽑으면 16건이 전부 `vnavmesh.*`다 — `Services/NavmeshIpc.cs:47-62`에 13건, `Services/RouteService.cs:41-46`에 3건. Tolk와 nvdaControllerClient64는 플러그인이 아니라 동봉 DLL이다. 업스트림도 vnavmesh를 optional로 취급한다(`README.en.md:236`).

**재배포하지 않는다.** vnavmesh는 `awgil/ffxiv_navmesh`이고 LICENSE 파일이 없다. KR Dalamud 도구와 같은 취급이라 사용자가 직접 받는 것만 안내한다.

Dalamud 자체 플러그인 설치창을 쓰지 않는 이유는 그 창이 ImGui라 스크린리더에 읽히지 않기 때문이다. 그래서 dev 플러그인 경로로 우회한다. 경로 규약은 업스트림 인스톨러와 같다(`Installer/InstallerService.cs:326`).

**이 절은 게임을 끈 상태에서 한다.**

### 받아서 푼다

출처는 puni.sh 저장소 매니페스트 `https://puni.sh/api/repository/veyn`이고, 업스트림 인스톨러가 읽는 것과 같다(`Installer/InstallerService.cs:36`). `vnavmesh` 항목의 `DownloadLinkInstall`이 zip 주소다.

받은 판은 **1.2.3.13**이다 — DalamudApiLevel 15, ApplicableVersion any.

아래 zip 주소는 2026-08-18에 그 매니페스트에서 꺼낸 것이다. 받아서 푼 결과는 확인했지만 이 한 줄을 그대로 돌려 보지는 않았다(복사용 한 줄):

curl -sSL -o "C:\Users\USER\AppData\Local\Temp\vnavmesh-1.2.3.13.zip" https://puni.sh/api/plugins/download/48/vnavmesh/versions/1.2.3.13/install/latest.zip && 7z x -y -o"C:\Users\USER\AppData\Roaming\XIVLauncherKR\devPlugins\vnavmesh" "C:\Users\USER\AppData\Local\Temp\vnavmesh-1.2.3.13.zip"

버전이 올라가면 매니페스트를 다시 열어 새 `DownloadLinkInstall`을 꺼낸다.

푼 결과는 zip 내용 그대로 **21개 파일**이고 그 안에 `vnavmesh.dll`과 `vnavmesh.json`이 있다.

### 설정에 심는다

§7과 같은 스크립트를 대상만 바꿔 부른다. 한 번만 하면 되고, 게임이 꺼져 있어야 하는 이유도 §7과 같다 — 켜져 있으면 Dalamud가 종료할 때 덮는다.

uv run --no-project python tools/kr-setup/seed_devplugin.py "%APPDATA%\XIVLauncherKR\dalamudConfig.json" "%APPDATA%\XIVLauncherKR\devPlugins\vnavmesh\vnavmesh.dll" vnavmesh

세 조건이 동시에 맞은 것을 확인했다 — `DevMode=true`, `DevPluginSettings[...].StartOnBoot=true`, `DefaultProfile`에 같은 WorkingPluginId(`ed98dbb9-5a32-46ce-ad00-0d8cf35ec5a2`)로 `IsEnabled=true`.

백업 두 개가 남는다.

- `dalamudConfig.json.bak-20260818-pre-vnavmesh` — 시딩 전 원본
- `dalamudConfig.json.bak-kr-seed` — 스크립트가 만든 것

### 여기까지가 확인된 범위다

파일 배치와 설정 시딩까지다. **게임 안에서 실제로 적재되는지는 아직 확인 못 했다.** 키를 사람이 눌러야 하는데 이 클라이언트에는 키 주입이 통하지 않는다(`docs/environment.md` §5). 확인 방법은 §10에 있다.

게임을 켜지 않고 할 수 있는 사전 검증(어셈블리 참조, 멤버 참조, 시그니처)은 통과했다. 근거는 `docs/environment.md` §7.

## 9. 실행 순서

**배치가 이 순서를 갖고 있다.** 아래 하나만 실행하면 1~3이 순서대로 나온다.

C:\project\games\ff14-ko-accessibility\run\play.bat

배치가 하는 일은 이렇다.

1. 한국어 런처로 게임 실행 — `%ProgramData%\Microsoft\Windows\Start Menu\Programs\FINAL FANTASY XIV - KOREA\FINAL FANTASY XIV - KOREA.lnk`
2. 로그인하고 게임 시작 (사람이 한다 — 배치가 여기서 기다린다)
3. 업데이터 실행 — `%LOCALAPPDATA%\KR-Dalamud-Updater\app\Dalamud.Updater.exe`
4. **달라무드 적용** (사람이 누른다 — GUI 버튼이라 자동화가 안 된다)

업데이터는 게임을 띄우지 않는다. 돌고 있는 `ffxiv_dx11` 프로세스에 붙을 뿐이다(`inject <pid>`). XIVLauncher는 이 구성에서 쓰지 않는다 — `XIVLauncherKR`은 프로그램이 아니라 폴더 이름이다.

## 10. 성공 확인

**"적용 완료" 알림을 믿으면 안 된다.** 인젝터가 종료 코드 0으로 끝나면 뜨는데, 게임 안에서 실패해도 0으로 끝난 적이 있다.

**손으로 찾지 않는다.** `run\log.bat`이 아래 판정을 대신 한다(`tools/kr-setup/check_log.py`). 로그는 세션을 이어 붙이므로 **마지막 세션만** 봐야 하는데, 그걸 눈으로 하면 앞판의 성공 줄에 속는다.

판정 근거는 이렇다.

| 보는 것 | 어디에 있나 | 뜻 |
|---------|-------------|-----|
| `"Language": "Korean"` | `dalamud.troubleshooting.json` | KR 언어 패치 작동 |
| `Lumina is ready: ...\game\sqpack` | `dalamud-kr-gui.log` | 게임 데이터 판독 가능 |
| `[LocalPlugin] Finished loading FF14Accessibility` | 같은 로그 | 플러그인 로드 |
| `[LocalPlugin] Finished loading vnavmesh` | 같은 로그 | 자동 이동 가능 |
| `[Compat] ... Korean signature` | 같은 로그 | 노드 가시성이 게임 함수 |
| `[Speak] '...'` | 같은 로그 | 음성 출력 도달 |
| `[Speak] ... Target reached` | 같은 로그 | 자동 이동이 끝까지 갔다 |

**언어 표시만 로그가 아니라 옆의 json에 있다.** 2026-08-18 실측에서 로그 전문의 `"Language"` 문자열이 0건이었다 — 그전까지 이 절이 로그에서 찾으라고 적어 둔 것은 틀린 안내였다.

`dalamudConfig.json`이 72바이트에서 7만 바이트대로 커졌으면 Dalamud가 실제로 돌았다는 뜻이다.

### vnavmesh 적재 확인

같은 로그에서 두 줄을 본다.

- `[LocalPlugin] Finished loading vnavmesh` — Dalamud가 dev 플러그인을 적재하면 찍는 줄이다. FF14Accessibility가 이 형식으로 찍히는 것은 확인했고(`dalamud-kr-gui.log:51`), vnavmesh 쪽은 **아직 못 봤다**
- `[Nav] Auto-Lauf: vnavmesh antwortet nicht (Plugin installiert und aktiv?)` — 이 경고가 보이면 아직 안 붙은 것이다(`dalamud-kr-gui.log:6206`)

넘패드3을 누르면 모드가 세 경우를 구분해 말해 준다(`Services/AutoWalkService.cs:355-370`). 이게 판정 기준이다.

| 들리는 말 | 뜻 |
|-----------|-----|
| `Auto-walk not available. The vnavmesh plugin is missing or not loaded.` | 여전히 안 붙었다 |
| `Navmesh still loading, N percent.` | **붙었다.** 첫 존 진입 때 길 그물망을 새로 만드느라 몇 분 걸린다 |
| `Navmesh is not ready yet. Try again shortly.` | 붙었는데 그물망이 아직 없다 |
