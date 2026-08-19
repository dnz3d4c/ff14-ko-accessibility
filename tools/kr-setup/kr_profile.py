"""KR Dalamud 프로필 루트가 어디인지 정하는 한 곳.

## 무엇을 막나

**우리가 플러그인을 넣은 곳과 업데이터가 보는 곳이 갈리는 것.**

갈려도 오류가 안 난다. 업데이터는 자기 설정대로 다른 폴더를 보고, 거기가
비어 있으면 **빈 프로필을 새로 만들어 주입한다.** 게임은 뜨고 Dalamud도 뜨고
플러그인만 조용히 빠진다 - `docs/status.md` §6-1이 "아무 일도 안 일어난다의
원인은 늘 경로 중 하나다"라고 적어 둔 바로 그 실패다.

## 왜 박아 두면 안 되나

전에는 세 군데가 각자 `XIVLauncherKR`을 박아 뒀다.

- `Installer/KrProfile.cs` - 우리가 남에게 주는 EXE
- `run/_env.cmd` - 빌드·배포·로그 배치가 전부 여기서 경로를 얻는다
- `tools/kr-setup/check_log.py` - 로그 판정

셋이 서로 맞는지 아무도 안 봤고, 업데이터의 **실제** 설정과 맞는지는 더더욱
안 봤다. 저장소가 이미 같은 부류를 결함으로 갖고 있다 - `W-04`, 키 이름 표가
둘로 갈려 바인딩 셋이 죽은 것.

## 권위는 업데이터의 설정이다

`%APPDATA%\\KrDalamudUpdater\\settings.json`의 `ProfileRoot`. 이건 우리가
찾아낸 내부 값이 아니라 **문서에 적힌 사용자 설정**이다 - `README-KR.txt`:
"사용자 설정은 %APPDATA%\\KrDalamudUpdater\\settings.json에 보관됩니다".
업데이터가 `settings.json.bak`을 남기며 자기가 다시 쓰므로 살아 있는 값이다.

**읽기만 한다.** 남의 설정 파일을 우리가 쓰지 않는다 - 그건 `status.md` §5-7
방침(남의 것은 남이 관리하게 둔다)에 걸린다. 읽는 것은 거기 해당하지 않고,
오히려 **박아 두는 쪽이 결합이 더 세다**: 박아 두면 "그쪽 기본값이 안 바뀐다"와
"사용자가 안 고친다" 둘 다에 걸어야 하는데, 읽으면 전자만 남고 그마저 폴백이
받는다.

## 순서

1. `FF14ACC_KR_PROFILE` - 우리 탈출구. 옮긴 프로필을 가리키거나, 아무것도
   없는 상태의 분기를 이미 다 있는 머신에서 돌려 보려고 쓴다
2. 업데이터 설정의 `ProfileRoot` (환경변수 펼친 뒤)
3. `%APPDATA%\\XIVLauncherKR` - 업데이터의 기본값과 같은 값

2번이 없거나 못 읽거나 못 쓸 값이면 조용히 3번으로 간다. **남의 파일이
깨졌다고 우리가 죽지 않는다.**

사용법:
    uv run --no-project python tools/kr-setup/kr_profile.py        # 루트를 찍는다
    uv run --no-project python tools/kr-setup/kr_profile.py --why  # 어디서 나왔는지도
"""

from __future__ import annotations

import json
import ntpath
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: 우리 탈출구. 설치기(`KrProfile.cs`)와 같은 이름이어야 한다.
ROOT_OVERRIDE_VARIABLE = "FF14ACC_KR_PROFILE"

#: 업데이터가 사용자 설정을 두는 곳. `README-KR.txt`에 적힌 자리다.
UPDATER_SETTINGS_DIR = "KrDalamudUpdater"
UPDATER_SETTINGS_NAME = "settings.json"
PROFILE_ROOT_KEY = "ProfileRoot"

#: 업데이터의 기본값과 같은 폴더 이름. 우리가 지은 이름이 아니다.
DEFAULT_FOLDER = "XIVLauncherKR"

#: 업데이터를 받아 오는 곳. 태그를 박지 않는다 - 최신 릴리스를 묻는다.
UPDATER_RELEASE_API = "https://api.github.com/repos/MiqoKR/kr-dalamud-updater/releases/latest"

#: 자산 둘 중 어느 쪽인가. `Payload`는 업데이터가 자기 갱신에 쓰는 것이라
#: 실행 파일이 없다. 이름으로 가르는 표지는 이 낱말 하나다.
UPDATER_ASSET_MARKER = "Portable"

#: 어디에 푸나. `%LOCALAPPDATA%` 밑이라 관리자 권한이 필요 없고, 업데이터
#: 자신의 `README-KR.txt`가 요구하는 "쓰기 가능한 일반 폴더"를 만족한다.
UPDATER_INSTALL_FOLDER = "KR-Dalamud-Updater"
UPDATER_APP_FOLDER = "app"
UPDATER_EXE_NAME = "Dalamud.Updater.exe"


def _appdata() -> str:
    return os.environ.get("APPDATA", "")


def settings_path() -> Path:
    return Path(_appdata()) / UPDATER_SETTINGS_DIR / UPDATER_SETTINGS_NAME


def default_root() -> str:
    return str(Path(_appdata()) / DEFAULT_FOLDER)


def usable(candidate: str) -> bool:
    """업데이터가 거부하는 값은 우리도 안 쓴다.

    거부는 둘뿐이다 - `%APPDATA%` 자신과 드라이브 루트. 둘 다 프로필 루트로
    삼으면 남의 폴더를 통째로 프로필처럼 다루게 된다.
    """
    if not candidate or not candidate.strip():
        return False

    normalized = ntpath.normcase(ntpath.normpath(candidate))
    if normalized == ntpath.normcase(ntpath.normpath(_appdata())):
        return False

    return ntpath.dirname(normalized) != normalized


def from_settings() -> str | None:
    """업데이터 설정의 `ProfileRoot`. 못 읽으면 None.

    깨진 JSON·없는 키·빈 값·거부 대상은 전부 None이다. 남의 파일이라
    우리가 고쳐 주지 않고 그냥 안 쓴다.
    """
    path = settings_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    if not isinstance(raw, dict):
        return None

    value = raw.get(PROFILE_ROOT_KEY)
    if not isinstance(value, str):
        return None

    # 업데이터가 실제로 `%APPDATA%\XIVLauncherKR` 모양으로 저장한다.
    expanded = os.path.expandvars(value).strip()
    return expanded if usable(expanded) else None


def resolve_root() -> str:
    override = os.environ.get(ROOT_OVERRIDE_VARIABLE, "").strip()
    if override:
        return override
    return from_settings() or default_root()


def source() -> str:
    """루트가 어디서 나왔는지. 진단용 - 갈렸을 때 어느 쪽인지 알아야 한다."""
    if os.environ.get(ROOT_OVERRIDE_VARIABLE, "").strip():
        return f"환경변수 {ROOT_OVERRIDE_VARIABLE}"
    if from_settings():
        return f"업데이터 설정 {settings_path()}"
    return "기본값 (업데이터 설정 없음/못 씀)"


def updater_install_root() -> str:
    """업데이터를 두는 폴더."""
    return str(Path(os.environ.get("LOCALAPPDATA", "")) / UPDATER_INSTALL_FOLDER)


def updater_extract_dir() -> str:
    """배포 zip을 푸는 폴더.

    zip이 평평해서(루트에 `Dalamud.Updater.exe`·`README-KR.txt`·
    `UpdaterReleaseConfig.json`) 여기에 통째로 푼다. `UpdaterReleaseConfig.json`은
    exe 옆에 있어야 자기 갱신이 도므로 셋을 갈라 놓으면 안 된다.
    """
    return str(Path(updater_install_root()) / UPDATER_APP_FOLDER)


def updater_path() -> str:
    """업데이터 실행 파일. 설치기가 "있나 없나"를 이 경로로 묻는다."""
    return str(Path(updater_extract_dir()) / UPDATER_EXE_NAME)


def pick_updater_asset(assets) -> str | None:
    """릴리스 자산 목록에서 받을 zip의 URL. 못 고르면 None.

    이름에 `Portable`이 들어간 zip만 받는다. 같은 릴리스에 올라오는
    `Payload` zip은 업데이터가 자기를 갱신할 때 쓰는 것이라 실행 파일이
    없고, 그걸 받으면 **압축은 멀쩡히 풀리고 exe만 없다.**
    """
    if not isinstance(assets, list):
        return None

    marker = UPDATER_ASSET_MARKER.lower()
    for entry in assets:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        url = entry.get("browser_download_url")
        if not isinstance(name, str) or not isinstance(url, str):
            continue
        lowered = name.lower()
        if marker in lowered and lowered.endswith(".zip"):
            return url
    return None


def main(argv: list[str]) -> int:
    print(resolve_root())
    if "--why" in argv:
        print(f"  출처: {source()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
