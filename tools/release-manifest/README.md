# release-manifest — 릴리스 매니페스트를 산출물에서 만든다

`dist`에 이미 있는 산출물을 읽어, 릴리스에 같이 올릴 매니페스트 둘을 같은 자리에 만든다.

uv run --no-project python tools/release-manifest/release_manifest.py

만들지 않고 대조만 하려면 이렇게 부른다.

uv run --no-project python tools/release-manifest/release_manifest.py --check

## 왜 있나

**값을 손으로 안 적기 위해서다.** 이 저장소는 손으로 옮겨 적은 숫자가 낡아서 이미 한 번 다쳤다(현황판 §8-1). `tools/docs-check`가 문서의 숫자를 두고 하는 일을, 이 도구는 릴리스 매니페스트를 두고 한다.

릴리스 매니페스트는 그중에서도 **낡은 것이 제일 늦게 드러나는 자리다.** 버전이나 해시가 어긋나도 여기서는 아무 일도 안 일어난다. 드러나는 곳은 받는 사람의 화면이고, 그때 보이는 것은 "설치 프로그램이 갱신을 거부한다"나 "새 판이 안 내려온다"뿐이다. 무엇이 어긋났는지는 안 보인다.

## 무엇을 만드나

### `dist\repo.json` — Dalamud 커스텀 저장소 매니페스트

사용자가 Dalamud에 이 저장소 주소를 등록해 두면, Dalamud가 이 파일을 보고 새 판을 알아서 받는다. 형식은 업스트림 `repo.json`을 그대로 본떴고 **필드 순서까지 맞춘다.**

값은 셋 중 하나에서 온다.

- **압축 안의 `FF14Accessibility.json`에서 그대로** — `AssemblyVersion`·`DalamudApiLevel`·`InternalName`·`Name`·`Author`·`ApplicableVersion`·`Tags`·`AcceptsFeedback`
- **우리 것으로 갈아 끼운다** — `RepoUrl`과 내려받기 링크 셋(`DownloadLinkInstall`·`DownloadLinkUpdate`·`DownloadLinkTesting`). 업스트림 주소가 한 자리도 안 남아야 한다
- **한국어로 옮긴다** — `Description`과 `Punchline`. 업스트림은 독일어로 개발되므로 압축 안의 값이 독일어다

**독일어 문구는 표를 거쳐서 나간다**(`GERMAN_TO_KOREAN`). 한국어가 아닌 문장이 표에 없으면 **만들지 않고 멈춘다.** "한국어가 아니면 원문을 그대로 쓴다"로 두면 업스트림이 문구를 고치는 날 독일어가 조용히 배포된다. 한국어 문구의 근거는 `overlay/ko/README.ko.md` 첫머리가 모드를 소개하는 문장이다.

### `dist\installer.json` — 설치 프로그램 자기 갱신용

읽는 쪽은 `Installer/InstallerService.cs`의 `TrySelfUpdateAsync`이고, 거기서 쓰는 필드는 셋뿐이다.

- **`InstallerVersion`** — `dist\FF14AccessibilityInstaller-KR.exe`의 **PE 버전 자원**에서 읽는다. 파일 이름이나 `csproj`가 아니라 배포할 그 파일에서 직접 읽으므로, 소스와 산출물이 갈린 상태까지 잡힌다
- **`AssetName`** — 릴리스에 올라가는 EXE 이름. 파일 이름에서 나온다
- **`Sha256`** — 그 EXE의 SHA-256. 읽는 쪽이 내려받은 파일을 이 값으로 검증한다

**버전은 항상 네 마디로 채워 낸다.** 읽는 쪽의 `ParseVersionLoose`가 모자란 마디를 `.0`으로 채우고 비교하는데, 마디가 다섯이거나 숫자가 아니면 `null`을 돌려주고 비교가 문자열 같음으로 떨어진다. 그러면 **같은 판을 새 판으로 보고 갱신을 무한히 다시 권한다.** 그래서 `1.1.0`은 `1.1.0.0`으로 채우고, `1.1.0-kr.1` 같은 것은 아예 거른다.

## 못 만들면 안 만든다

빈 값이나 반쪽짜리를 내보내는 것보다 안 만드는 것이 낫다. 압축이 없을 때, 압축 안에 매니페스트가 없을 때, 있어야 할 필드가 비었을 때, EXE에 버전 자원이 없을 때, 읽는 쪽이 못 읽을 버전일 때, 옮길 한국어 문장을 못 찾았을 때는 만들지 않고 이유를 말한다.

## 다시 재기 (`--check`)

만든 뒤에 산출물만 다시 빌드하면 매니페스트가 조용히 낡는다. `--check`는 **산출물에서 다시 계산해** 이미 있는 파일과 필드별로 대조한다. 만들지는 않는다.

## 테스트

uv run --no-project --with pytest pytest tools/release-manifest -q
