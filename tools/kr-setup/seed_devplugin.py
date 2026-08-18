"""KR 프로필의 dalamudConfig.json에 dev 플러그인 항목을 심는다.

업스트림 `Installer/InstallerService.cs:391-576`을 따르되 경로만 KR로 바꾼 것이다.
그쪽이 디컴파일로 확인해 둔 조건은 셋이고, **하나라도 어긋나면 플러그인이 조용히
안 뜬다** - 오류도 안 난다.

1. `DevMode = true` (없으면 Dalamud가 DevPluginLoadLocations를 아예 스캔 안 함)
2. `DevPluginSettings[<dll 전체경로>].StartOnBoot = true`
3. `DefaultProfile.Plugins`에 **같은 WorkingPluginId**로 `IsEnabled = true`

BOM을 붙이면 안 된다. 업스트림이 기록해 둔 함정 - Dalamud가 조용히 예전 SQLite
사본으로 폴백한다.

사용법:
    uv run --no-project python tools/kr-setup/seed_devplugin.py <config> <dll> <내부이름>

**게임을 끈 상태에서 실행한다.** Dalamud가 종료할 때 설정을 저장하면 덮인다.
"""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

DEV_SETTINGS_TYPE = (
    "System.Collections.Generic.Dictionary`2[[System.String, "
    "System.Private.CoreLib],[Dalamud.Configuration.Internal."
    "DevPluginSettings, Dalamud]], System.Private.CoreLib"
)
STRING_LIST_TYPE = (
    "System.Collections.Generic.List`1[[System.String, "
    "System.Private.CoreLib]], System.Private.CoreLib"
)
LOCATION_TYPE = "Dalamud.Configuration.DevPluginLocationSettings, Dalamud"
SETTINGS_TYPE = "Dalamud.Configuration.Internal.DevPluginSettings, Dalamud"
PROFILE_PLUGIN_TYPE = (
    "Dalamud.Plugin.Internal.Profiles.ProfileModelV1+ProfileModelV1Plugin, Dalamud"
)


def seed(config: dict, dll_path: str, internal_name: str, new_id: str) -> str:
    """설정 딕셔너리를 제자리에서 고치고 쓰인 WorkingPluginId를 돌려준다.

    이미 있는 항목은 재사용한다 - GUID가 바뀌면 3번 조건이 깨진다.
    """
    config["DevMode"] = True

    locations = config["DevPluginLoadLocations"]["$values"]
    if not any(str(e.get("Path", "")).lower() == dll_path.lower() for e in locations):
        locations.append({
            "$type": LOCATION_TYPE,
            "Path": dll_path,
            "IsEnabled": True,
            "Nickname": None,
        })

    dev_settings = config.get("DevPluginSettings")
    if not isinstance(dev_settings, dict):
        dev_settings = {"$type": DEV_SETTINGS_TYPE}
        config["DevPluginSettings"] = dev_settings

    entry = dev_settings.get(dll_path)
    if isinstance(entry, dict):
        entry["StartOnBoot"] = True
        working_id = entry.get("WorkingPluginId") or new_id
        entry["WorkingPluginId"] = working_id
    else:
        working_id = new_id
        dev_settings[dll_path] = {
            "$type": SETTINGS_TYPE,
            "StartOnBoot": True,
            "NotifyForErrors": True,
            # 파일이 바뀌면 게임 재시작 없이 다시 읽는다. 빌드-배포 반복에 필수.
            "AutomaticReloading": True,
            "WorkingPluginId": working_id,
            "DismissedValidationProblems": {
                "$type": STRING_LIST_TYPE,
                "$values": [],
            },
        }

    profile = config["DefaultProfile"]["Plugins"]["$values"]
    existing = next(
        (p for p in profile if p.get("InternalName") == internal_name), None
    )
    if existing is not None:
        existing["IsEnabled"] = True
        existing["WorkingPluginId"] = working_id
    else:
        profile.append({
            "$type": PROFILE_PLUGIN_TYPE,
            "InternalName": internal_name,
            "WorkingPluginId": working_id,
            "IsEnabled": True,
        })

    return working_id


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(
            "사용법: seed_devplugin.py <dalamudConfig.json> <dll 전체경로> <내부이름>",
            file=sys.stderr,
        )
        return 2

    config_path = Path(argv[1])
    dll_path, internal_name = argv[2], argv[3]

    raw = config_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        print("BOM이 붙어 있다. 손대지 않는다.", file=sys.stderr)
        return 1

    config = json.loads(raw.decode("utf-8"))
    before = json.dumps(config, sort_keys=True)

    working_id = seed(config, dll_path, internal_name, str(uuid.uuid4()))

    # 바뀐 게 없으면 쓰지 않는다. 게임이 떠 있는 동안 이 파일을 건드리면
    # Dalamud가 자기 메모리 상태로 종료할 때 덮어써서 우리 쓴 것이 사라진다.
    # 개발 배포(run\build.bat)는 게임이 떠 있는 채로 도는 것이 정상이라,
    # "이미 심겨 있다"를 조용히 지나갈 수 있어야 한다.
    if json.dumps(config, sort_keys=True) == before:
        print(f"이미 심겨 있다. 건드리지 않았다. WorkingPluginId: {working_id}")
        return 0

    backup = config_path.with_suffix(".json.bak-kr-seed")
    shutil.copy2(config_path, backup)

    # BOM 금지 - 위 모듈 주석 참조.
    config_path.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"백업: {backup}")
    print(f"WorkingPluginId: {working_id}")
    print("설정을 새로 심었다. 게임이 떠 있었다면 껐다 켜야 반영된다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
