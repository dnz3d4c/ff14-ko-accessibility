"""배포 산출물이 정말 '바닐라'인지 검사한다.

`run\\pack.bat`이 내는 두 파일(`dist\\FF14Accessibility.zip`,
`dist\\FF14AccessibilityInstaller-KR.exe`)에 **이 머신의 것이 섞였는지**와,
그 산출물이 **Dalamud가 정식 플러그인으로 읽는 모양인지**를 본다.

세 갈래다.

1. **위생** - 압축 안에 들어갈 것만 들어 있나, 사용자 이름·홈 경로·설정 파일이
   섞이지 않았나, 매니페스트가 빌드와 같은 버전인가
2. **모양** - 설치 결과가 `installedPlugins\\<이름>\\<버전>\\<이름>.dll`인가.
   Dalamud는 **버전으로 파싱되지 않는 폴더를 지운다**(`PluginManager.CleanupPlugins`),
   그래서 폴더 이름은 취향이 아니라 적재 여부를 가르는 조건이다
3. **실물 검증(`--e2e`)** - 설치기를 버리는 프로필 루트(`FF14ACC_KR_PROFILE`)에
   대고 `--install`로 실제로 돌려 보고 그 결과를 위 규칙으로 잰다.
   설치기는 창이라 눈으로만 볼 수 있는데, 이 경로는 기계가 볼 수 있다

**왜 방향을 뒤집나**: "설치기가 성공이라고 말했다"와 "파일이 Dalamud가 보는
자리에 있다"는 다른 주장이다. 앞의 것만 믿다가 갈린 적이 있다(현황판 §8-1).

사용법:
    uv run --no-project python tools/pack-check/pack_check.py [--dist DIR] [--e2e]
"""

from __future__ import annotations

import argparse
import json
import locale
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

#: 플러그인 내부 이름. Dalamud는 폴더 이름·DLL 이름·매니페스트가 다 이것이길 요구한다.
INTERNAL_NAME = "FF14Accessibility"

#: 받는 폴더에 함께 나가는 안내 문서. 원본은 `overlay/ko/README.ko.md`다.
GUIDE_NAME = "사용 안내.md"

#: 릴리스에 같이 올라가는 매니페스트 둘. `tools/release-manifest`가 만들고
#: `run\\pack.bat`이 부른다. 여기서는 **나갈 자리에 있나**만 본다 - 값이 맞나는
#: 그 도구의 `--check`가, 릴리스에 올라갔나는 `--release`가 잰다.
RELEASE_MANIFESTS = ("repo.json", "installer.json")

#: 사람이 안 여는 것이 들어가는 자리. `dist` 루트는 **받는 사람에게 그대로 줄
#: 수 있는 폴더**로 두고 여기에 기계용을 내린다 - 사용 안내가 "셋을 같은 폴더에
#: 두고 실행합니다"라고 말하는 그 폴더라, 거기 파일이 많으면 무엇을 눌러야
#: 하는지 헷갈린다. 이름의 원천은 `tools/release-manifest`의 `RELEASE_DIR_NAME`이다.
RELEASE_DIR_NAME = "release"

#: 릴리스 노트. 사람이 쓰고, 받는 사람이 "이번에 뭐가 바뀌었나"를 읽는
#: 유일한 자리다. `run\\release.bat`이 `--notes-file`로 넘긴다.
RELEASE_NOTES_NAME = "release-notes.md"

#: 받는 사람이 실제로 받는 것. `tools/release-manifest`가 `dist` 루트의 셋을
#: 그대로 담아 만든다. 여기서는 나갈 자리에 있나만 본다 - 안에 무엇이 들었나는
#: 그 도구의 `--check`가 잰다.
SETUP_ZIP_NAME = "FF14Accessibility-KR-Setup.zip"

#: Dalamud가 "공식 저장소에서 왔다"에 쓰는 값(`SpecialPluginSource.MainRepo`).
#: 설치 프로그램이 **처음에 쓰는** 값이고, 설정에 저장소를 등록한 뒤 아래
#: `KR_REPO_URL`로 옮긴다. 끝나고도 이 값이면 그 단계가 안 돈 것이다.
OFFICIAL_SOURCE = "OFFICIAL"

#: 우리 저장소. 설치가 끝난 매니페스트의 `InstalledFromUrl`이 이것이어야 하고,
#: 같은 문자열이 `dalamudConfig.json`의 `ThirdRepoList`에도 있어야 한다.
#:
#: **`OFFICIAL`로 두면 왜 안 되나**: 적재는 된다. 그런데 그건 공식 저장소가
#: 우리를 목록에 갖고 있다는 주장이고 사실이 아니라서, Dalamud가
#: `IsDecommissioned`를 세운다(`LocalPlugin.cs:196-198`). 그러면 프로필을 다시
#: 적용할 때 - 캐릭터를 바꿀 때가 그렇다 - 켜지지 않고 경고만 남는다
#: (`ProfileManager.cs:258`). 갱신도 안 된다.
#:
#: Dalamud가 `==`로 대조하므로 대소문자와 후행 슬래시까지 같아야 한다.
KR_REPO_URL = "https://github.com/dnz3d4c/ff14-ko-accessibility/releases/latest/download/repo.json"

#: 압축에 들어가도 되는 정확한 이름들.
ALLOWED_EXACT = {
    f"{INTERNAL_NAME}.dll",
    f"{INTERNAL_NAME}.json",
    f"{INTERNAL_NAME}.deps.json",
    f"{INTERNAL_NAME}.pdb",
    "Tolk.dll",
    "nvdaControllerClient64.dll",
    "LICENSE",
    "THIRD-PARTY-NOTICES.md",
}

#: 이름이 판마다 늘어나는 것들. NAudio는 우리가 고르는 목록이 아니라 의존성이다.
ALLOWED_PATTERNS = (re.compile(r"^NAudio(\.[A-Za-z]+)?\.dll$"),)

#: 배포물에 있으면 안 되는 것. 설치기가 설치할 때 **붙이는** 필드라서,
#: 압축 안에 이미 있으면 누군가 설치된 사본을 다시 압축했다는 뜻이다.
LOCAL_ONLY_FIELDS = ("InstalledFromUrl", "WorkingPluginId", "Disabled", "ScheduledForDeletion")


def _text_variants(needle: str) -> tuple[bytes, ...]:
    """.NET 바이너리는 문자열을 UTF-16으로 갖는다. 둘 다 본다."""
    return needle.encode("utf-8"), needle.encode("utf-16-le")


def personal_traces(blob: bytes, needles: list[str]) -> list[str]:
    """바이트 안에서 발견된 개인 흔적. 없으면 빈 목록."""
    return [n for n in needles if any(v in blob for v in _text_variants(n))]


def default_needles() -> list[str]:
    """이 머신을 가리키는 문자열들. 인자로 받는 이유는 테스트 때문이다.

    빌드 경로(`C:\\project`)는 **일부러 뺐다.** .NET 어셈블리는 PDB 경로를
    디버그 디렉토리에 박고, 그건 모든 .NET 빌드가 하는 일이라 개인 설정이
    아니다. 여기서 막는 것은 **사람을 가리키는 것** - 계정 이름과 홈 경로다.
    """
    user = os.environ.get("USERNAME", "")
    needles = [str(Path.home())]
    if user:
        needles.append(user)
    return [n for n in needles if n]


def zip_problems(names: list[str]) -> list[str]:
    """압축 목록에서 규칙을 어긴 것들."""
    problems = []
    for name in names:
        if "/" in name or "\\" in name:
            problems.append(f"압축 안에 폴더가 있다: {name}")
            continue
        if name in ALLOWED_EXACT:
            continue
        if any(p.match(name) for p in ALLOWED_PATTERNS):
            continue
        problems.append(f"목록에 없는 파일이 들어 있다: {name}")

    for required in (f"{INTERNAL_NAME}.dll", f"{INTERNAL_NAME}.json"):
        if required not in names:
            problems.append(f"있어야 할 파일이 없다: {required}")
    return problems


def manifest_problems(manifest: dict, csproj_version: str | None) -> list[str]:
    """배포용 매니페스트 검사. 설치 뒤의 매니페스트는 규칙이 다르다."""
    problems = []
    if manifest.get("InternalName") != INTERNAL_NAME:
        problems.append(f"InternalName이 {manifest.get('InternalName')!r}다")

    version = manifest.get("AssemblyVersion")
    if not version:
        problems.append("AssemblyVersion이 없다")
    elif csproj_version and version != csproj_version:
        problems.append(f"버전이 빌드 설정과 다르다: 매니페스트 {version}, csproj {csproj_version}")

    if not isinstance(manifest.get("DalamudApiLevel"), int):
        problems.append("DalamudApiLevel이 없거나 숫자가 아니다")

    for field in LOCAL_ONLY_FIELDS:
        if field in manifest:
            problems.append(f"설치 뒤에나 붙는 필드가 배포물에 있다: {field}")
    return problems


def parse_version(text: str) -> tuple[int, ...] | None:
    """`Version.TryParse`가 받아들이는 모양인가. 2~4마디 숫자만 통과한다."""
    parts = text.split(".")
    if not 2 <= len(parts) <= 4:
        return None
    if not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def installed_layout_problems(plugin_root: Path) -> list[str]:
    """설치 결과가 Dalamud가 읽는 모양인가."""
    if not plugin_root.is_dir():
        return [f"설치 폴더가 없다: {plugin_root}"]

    version_dirs = [d for d in plugin_root.iterdir() if d.is_dir()]
    if len(version_dirs) != 1:
        names = ", ".join(sorted(d.name for d in version_dirs)) or "(없음)"
        return [f"버전 폴더가 하나여야 하는데 {len(version_dirs)}개다: {names}"]

    version_dir = version_dirs[0]
    problems = []
    if parse_version(version_dir.name) is None:
        # Dalamud가 이런 폴더를 지운다. 조용히 사라지고 플러그인만 없어진다.
        problems.append(f"버전 폴더 이름이 버전이 아니다: {version_dir.name}")

    dll = version_dir / f"{INTERNAL_NAME}.dll"
    if not dll.is_file():
        problems.append(f"DLL이 폴더 이름과 안 맞거나 없다: {dll}")

    manifest_path = version_dir / f"{INTERNAL_NAME}.json"
    if not manifest_path.is_file():
        return problems + [f"매니페스트가 없다: {manifest_path}"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = manifest.get("InstalledFromUrl")
    if source != KR_REPO_URL:
        # 두 갈래를 갈라서 말한다. `OFFICIAL`이면 설치는 됐는데 저장소로 옮기는
        # 마지막 단계가 안 돈 것이고, 그 밖이면 어느 저장소와도 안 맞아 고아다.
        problems.append(
            f"InstalledFromUrl이 아직 {OFFICIAL_SOURCE!r}다. 저장소로 옮기는 단계가 안 돌았다"
            if source == OFFICIAL_SOURCE
            else f"InstalledFromUrl이 {source!r}다. {KR_REPO_URL!r}가 아니면 "
            f"Dalamud가 고아로 보고 적재를 건너뛴다"
        )
    if manifest.get("Disabled") is not False:
        problems.append("매니페스트가 Disabled를 거짓으로 갖고 있지 않다")
    if manifest.get("AssemblyVersion") != version_dir.name:
        problems.append(
            f"폴더 이름과 매니페스트 버전이 다르다: {version_dir.name} vs {manifest.get('AssemblyVersion')}"
        )
    if not manifest.get("WorkingPluginId"):
        problems.append("WorkingPluginId가 비었다. 프로필 항목과 이어지지 않는다")
    return problems


def working_plugin_id(plugin_root: Path) -> str | None:
    """설치된 사본의 WorkingPluginId. 없으면 None."""
    for version_dir in sorted(plugin_root.glob("*")):
        manifest = version_dir / f"{INTERNAL_NAME}.json"
        if manifest.is_file():
            return json.loads(manifest.read_text(encoding="utf-8")).get("WorkingPluginId")
    return None


def config_problems(config: dict, expected_id: str | None, dev_dll: str) -> list[str]:
    """dalamudConfig.json이 정식 경로를 가리키고 dev 흔적이 없는가."""
    problems = []

    entries = (config.get("DefaultProfile") or {}).get("Plugins", {}).get("$values", [])
    ours = [e for e in entries if e.get("InternalName") == INTERNAL_NAME]
    if len(ours) != 1:
        problems.append(f"기본 프로필의 우리 항목이 {len(ours)}개다. 하나여야 한다")
    else:
        entry = ours[0]
        if entry.get("IsEnabled") is not True:
            problems.append("기본 프로필에서 꺼져 있다")
        if expected_id and entry.get("WorkingPluginId") != expected_id:
            problems.append(
                "프로필 항목의 WorkingPluginId가 매니페스트와 다르다: "
                f"{entry.get('WorkingPluginId')} vs {expected_id}"
            )

    locations = (config.get("DevPluginLoadLocations") or {}).get("$values", [])
    if any(str(loc.get("Path", "")).lower() == dev_dll.lower() for loc in locations):
        problems.append("dev 적재 경로가 남아 있다. 같은 모드가 두 번 적재된다")

    dev_settings = config.get("DevPluginSettings") or {}
    if any(k.lower() == dev_dll.lower() for k in dev_settings):
        problems.append("DevPluginSettings 항목이 남아 있다")

    # 매니페스트가 가리키는 저장소가 여기 없으면 그게 고아다. 대소문자를 접지
    # 않는 이유는 Dalamud가 `==`로 재기 때문이다 - 철자가 다르면 다른 저장소다.
    repos = (config.get("ThirdRepoList") or {}).get("$values", [])
    ours_repo = [r for r in repos if r.get("Url") == KR_REPO_URL]
    if not ours_repo:
        problems.append(f"저장소가 등록되지 않았다: {KR_REPO_URL}")
    elif ours_repo[0].get("IsEnabled") is not True:
        problems.append("저장소는 등록됐는데 꺼져 있다")

    return problems


# ── 산출물 검사 ────────────────────────────────────────────────────────────


def csproj_assembly_version(repo: Path) -> str | None:
    csproj = repo / "vendor" / "ff14-accessibility" / INTERNAL_NAME / f"{INTERNAL_NAME}.csproj"
    if not csproj.is_file():
        return None
    match = re.search(r"<AssemblyVersion>([^<]+)</AssemblyVersion>", csproj.read_text(encoding="utf-8"))
    return match.group(1) if match else None


def dist_layout_problems(dist: Path) -> list[str]:
    """받는 폴더에 있어야 할 것이 다 있고, 없어야 할 것이 없나.

    안내 문서가 여기 끼는 이유는 편의가 아니다. 설치의 첫 단계가 "문서를
    읽는 것"인데 그 문서가 저장소에만 있으면, 받는 사람은 무엇부터 눌러야
    하는지 알 방법이 없다.

    매니페스트 둘도 같은 이유로 여기 있다. 릴리스에 그 둘이 같이 안 올라가면
    자기 갱신과 커스텀 저장소가 통째로 죽는데, **받는 쪽은 그것을 오류가
    아니라 "새 판이 없다"로 읽는다.** 만드는 것은 `tools/release-manifest`고
    여기서는 나갈 자리에 있나만 본다.

    **자리가 둘로 갈린다.** 루트는 받는 사람에게 그대로 주는 셋이고,
    `release/`는 사람이 안 여는 것이다. 사용 안내가 "셋을 같은 폴더에 두고
    실행합니다"라고 말하는 그 폴더가 루트라, 거기 파일이 많으면 무엇을
    눌러야 하는지 헷갈린다.
    """
    problems = []
    root_expected = {
        f"{INTERNAL_NAME}.zip",
        "FF14AccessibilityInstaller-KR.exe",
        GUIDE_NAME,
    }
    # 노트는 **있어도 되지만 여기서 요구하지는 않는다.** 판마다 사람이 쓰는
    # 것이고 `run\\pack.bat`은 그 전에 돈다 - 여기서 요구하면 그냥 빌드만
    # 하려던 사람이 매번 걸린다. 없으면 낼 수 없다는 것은 `run\\release.bat`이
    # 못박는다.
    release_required = {*RELEASE_MANIFESTS, SETUP_ZIP_NAME}
    release_allowed = release_required | {RELEASE_NOTES_NAME}
    release = dist / RELEASE_DIR_NAME

    for name in sorted(root_expected):
        if not (dist / name).is_file():
            problems.append(f"산출물이 없다: {dist / name}")

    # 하위 폴더는 "배포물이 아닌 것"이 아니다. 이름만 빼고 따로 본다.
    extra = sorted(p.name for p in dist.iterdir() if p.name not in root_expected | {RELEASE_DIR_NAME})
    if extra:
        problems.append(f"dist 루트에 받는 사람이 안 쓰는 것이 있다: {', '.join(extra)}")

    if not release.is_dir():
        return problems + [f"릴리스용 폴더가 없다: {release}"]

    for name in sorted(release_required):
        if not (release / name).is_file():
            problems.append(f"산출물이 없다: {release / name}")

    extra = sorted(p.name for p in release.iterdir() if p.name not in release_allowed)
    if extra:
        problems.append(f"{RELEASE_DIR_NAME}에 배포물이 아닌 것이 있다: {', '.join(extra)}")

    return problems


def check_artifacts(dist: Path, repo: Path, needles: list[str]) -> list[str]:
    zip_path = dist / f"{INTERNAL_NAME}.zip"
    exe_path = dist / "FF14AccessibilityInstaller-KR.exe"

    problems = dist_layout_problems(dist)
    if any(p.startswith("산출물이 없다") for p in problems):
        return problems

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        problems += zip_problems(names)
        for name in names:
            found = personal_traces(archive.read(name), needles)
            if found:
                problems.append(f"압축의 {name}에 개인 흔적이 있다: {', '.join(found)}")
        if f"{INTERNAL_NAME}.json" in names:
            manifest = json.loads(archive.read(f"{INTERNAL_NAME}.json").decode("utf-8"))
            problems += manifest_problems(manifest, csproj_assembly_version(repo))

    found = personal_traces(exe_path.read_bytes(), needles)
    if found:
        problems.append(f"설치기 EXE에 개인 흔적이 있다: {', '.join(found)}")

    return problems


# ── 실물 검증 ──────────────────────────────────────────────────────────────


def installer_seed_containers(repo: Path) -> set[str]:
    """`KrProfile.ConfigSeed`가 만드는 최상위 컨테이너 이름들.

    **왜 소스에서 읽나**: 검사가 설치 프로그램보다 더 갖춰진 프로필을 만들면,
    설치 프로그램이 못 만드는 구조를 검사가 대신 만들어 주는 셈이 된다. 그러면
    실물에서만 터지고 검사는 조용히 통과한다. 실제로 그래서 **첫 설치가 반드시
    실패하는 결함**이 배포 직전까지 안 잡혔다 - 씨앗에는 `$type` 하나뿐인데
    여기서는 컨테이너 둘을 미리 채워 놓고 있었다(2026-08-19).

    베끼지 않고 세는 쪽을 골랐다. 값까지 맞추면 그게 두 번째 사본이 된다.
    """
    source = (repo / "vendor" / "ff14-accessibility" / "Installer" / "KrProfile.cs").read_text(
        encoding="utf-8"
    )
    match = re.search(r"private const string ConfigSeed\s*=(.*?);\n", source, re.DOTALL)
    if match is None:
        raise ValueError("KrProfile.cs에서 ConfigSeed를 못 찾았다")

    # C# 문자열 리터럴 조각을 이어 붙여 실제 JSON으로 되돌린다. 세는 것보다
    # 이쪽이 나은 이유는 **씨앗이 파싱되는지까지 여기서 걸리기 때문**이다 -
    # 안 그러면 그건 사용자 기계에서만 드러난다.
    pieces = re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1))
    seed = json.loads("".join(pieces).replace('\\"', '"').replace("\\\\", "\\"))
    return {key for key, value in seed.items() if isinstance(value, dict)}


def _seed_dalamud(root: Path, *, marker: bool = True, assets: bool = True) -> None:
    """업데이터가 일을 마쳤을 때 남는 자취.

    **폴더 하나로는 모자란다.** 설치 프로그램이 준비 완료로 보는 조건이
    `addon\\Hooks` 존재였던 동안, 이 검사는 빈 폴더 하나로 통과하면서 실물에서
    업데이터가 **아직 쓰는 중인** 상태를 한 번도 안 태웠다(2026-08-20 실측:
    설치 프로그램이 07:57:41에 플러그인을 깔았는데 에셋은 07:57:46에 왔다).

    `marker`·`assets`를 끄면 그 중간 상태를 만들 수 있다. 정상 실행에서는 안
    생기는 조합이라 인위로만 만들어진다.
    """
    hooks = root / "addon" / "Hooks" / "15.0.0.0"
    hooks.mkdir(parents=True, exist_ok=True)
    if marker:
        # 이름 셋이 아니라 `Dalamud.KR.*.Patch.json` 패턴이 기준이다. 하나만
        # 만드는 것은 그 패턴이 개수에 안 기대는지도 같이 보기 때문이다.
        (hooks / "Dalamud.KR.Compatibility.Patch.json").write_text("{}", encoding="utf-8")
    if assets:
        (root / "dalamudAssets").mkdir(parents=True, exist_ok=True)
        (root / "dalamudAssets" / "asset.ver").write_text("437", encoding="utf-8")


def _seed_profile(root: Path) -> None:
    """설치기가 "Dalamud가 있다"고 볼 만큼만 갖춘 가짜 프로필.

    담는 것은 **설치 프로그램의 `KrProfile.ConfigSeed`가 담는 것과 같아야
    한다.** 여기가 더 갖춰져 있으면 첫 설치가 겪는 상태를 한 번도 안 태운다 -
    `installer_seed_containers`가 그걸 지킨다.
    """
    _seed_dalamud(root)
    (root / "dalamudConfig.json").write_text(
        json.dumps(
            {
                "$type": "Dalamud.Configuration.Internal.DalamudConfiguration, Dalamud",
                "DevPluginLoadLocations": {"$values": []},
                "ThirdRepoList": {"$values": []},
                "DefaultProfile": {"Plugins": {"$values": []}},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def run_installer(exe: Path, root: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["FF14ACC_KR_PROFILE"] = str(root)
    return subprocess.run(
        [str(exe), "--install", "--skip-vnavmesh"],
        capture_output=True,
        text=True,
        # 설치 프로그램은 `Console.WriteLine`으로 쓴다. 그건 콘솔 코드페이지지
        # utf-8이 아니라서, utf-8로 읽으면 **한국어가 전부 깨진 글자로 나온다.**
        # 실패했을 때 여기 담긴 출력이 유일한 단서인데 그게 안 읽혔다.
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        env=env,
        timeout=300,
    )


#: `KrCheck.Run`이 준비 완료 판정을 내는 줄. `[OK ]`면 참, `[-- ]`면 거짓이다.
READY_LABEL = "dalamud ready"


def run_check(exe: Path, root: Path) -> subprocess.CompletedProcess[str]:
    """`--check`를 가짜 프로필에 대고 돌린다.

    `--bootstrap`이 아니라 `--check`인 것이 중요하다 - 이쪽은 읽기만 하고,
    `--bootstrap`은 **사용자 환경변수 DALAMUD_RUNTIME을 실제로 쓴다**
    (`KrCheck.cs`의 `EnsureRuntimeVariable`). 검사가 기계 설정을 건드리면 안 된다.
    """
    env = dict(os.environ)
    env["FF14ACC_KR_PROFILE"] = str(root)
    return subprocess.run(
        [str(exe), "--check"],
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        env=env,
        timeout=120,
    )


def dalamud_ready(stdout: str) -> bool:
    """`--check` 출력에서 준비 완료 판정만 골라낸다."""
    for line in stdout.splitlines():
        if READY_LABEL in line:
            return line.lstrip().startswith("[OK ]")
    raise ValueError(f"`--check` 출력에 `{READY_LABEL}` 줄이 없다:\n{stdout}")


def binding_detail(stdout: str, stderr: str = "") -> str:
    """asmref-check 출력에서 사람이 볼 줄만 남긴다.

    931건 중 걸린 것은 보통 한 줄이다. 전문을 그대로 뱉으면 그 한 줄이 묻힌다.
    아무 줄도 못 고르면 잘라서라도 원문을 보여 준다 - 조용히 "실패"만 남기는
    것이 제일 나쁘다.
    """
    picked = [
        line.strip() for line in stdout.splitlines()
        if "MISSING" in line or "ARITY" in line
    ]
    if picked:
        return "; ".join(picked)
    return (stdout + stderr).strip()[-400:] or "(출력 없음)"


def kr_dalamud_dir() -> Path | None:
    """KR Dalamud의 Hooks 폴더. 이름이 버전이라 최신을 고른다.

    규칙을 여기서 새로 만들지 않는다 - 프로필 루트는 `kr_profile`이 정하고,
    `dev`를 건너뛰는 것은 `run\\_env.cmd`와 같다.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kr-setup"))
    import kr_profile  # noqa: PLC0415 - 배치가 파일 경로로 직접 부른다

    hooks = Path(kr_profile.resolve_root()) / "addon" / "Hooks"
    if not hooks.is_dir():
        return None
    versions = sorted(d for d in hooks.iterdir() if d.is_dir() and d.name != "dev")
    return versions[-1] if versions else None


def dotnet_path() -> Path:
    scoop = Path(os.environ.get("SCOOP", str(Path.home() / "scoop")))
    return scoop / "apps" / "dotnet-sdk" / "current" / "dotnet.exe"


def check_kr_binding(dist: Path, repo: Path, kr_dalamud: str | None, dotnet: str | None) -> list[str]:
    """압축 안의 DLL이 **KR이 깔아 둔** FFXIVClientStructs에 붙는가.

    이게 왜 필요한가: `run\\check.bat`은 같은 소스를 KR(7.51)과 글로벌(7.55)로
    두 번 빌드하고 **둘 다 같은 bin에 쓴다.** 마지막이 글로벌이라, 검사 직후에
    패킹하면 글로벌 바인딩 DLL이 배포물로 나간다. 그건 적재는 되고 **첫
    장비세트 호출에서 죽는다** - 게임 안에서만 드러나는 고장이다.

    2026-08-18에 실제로 그렇게 나갔다. 순서를 지키는 것으로는 못 막는다 -
    산출물을 직접 재야 한다.
    """
    refdir = Path(kr_dalamud) if kr_dalamud else kr_dalamud_dir()
    if refdir is None or not refdir.is_dir():
        return ["KR Dalamud를 못 찾아 바인딩을 대조하지 못했다"]

    exe = Path(dotnet) if dotnet else dotnet_path()
    if not exe.is_file():
        return [f".NET SDK를 못 찾아 바인딩을 대조하지 못했다: {exe}"]

    workdir = Path(tempfile.mkdtemp(prefix="ff14acc-asmref-"))
    try:
        with zipfile.ZipFile(dist / f"{INTERNAL_NAME}.zip") as archive:
            archive.extract(f"{INTERNAL_NAME}.dll", workdir)

        result = subprocess.run(
            [
                str(exe), "run", "-c", "Release",
                "--project", str(repo / "tools" / "asmref-check"), "--",
                str(workdir / f"{INTERNAL_NAME}.dll"), str(refdir),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(repo), timeout=600,
        )
        if result.returncode != 0:
            return [
                "압축 안의 DLL이 KR FFXIVClientStructs에 안 붙는다. 글로벌 빌드가 섞였을 수 "
                f"있다 (run\\check.bat 뒤에 패킹하면 그렇게 된다): {binding_detail(result.stdout, result.stderr)}"
            ]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return []


def check_install_e2e(dist: Path) -> list[str]:
    """설치기를 버리는 프로필에 대고 실제로 돌려 보고 결과를 잰다."""
    exe = dist / "FF14AccessibilityInstaller-KR.exe"
    if not exe.is_file():
        return [f"설치기가 없다: {exe}"]

    problems = []
    workdir = Path(tempfile.mkdtemp(prefix="ff14acc-e2e-"))
    try:
        root = workdir / "profile"
        root.mkdir()
        _seed_profile(root)

        # 옛 dev 설치가 남아 있는 머신을 흉내 낸다. 설치기가 이걸 걷어내야
        # 같은 모드가 두 번 적재되지 않는다.
        dev_dir = root / "devPlugins" / INTERNAL_NAME
        dev_dir.mkdir(parents=True)
        (dev_dir / f"{INTERNAL_NAME}.dll").write_bytes(b"stale")

        first = run_installer(exe, root)
        if first.returncode != 0:
            problems.append(f"설치기가 실패했다(코드 {first.returncode}):\n{first.stdout}{first.stderr}")
            return problems

        plugin_root = root / "installedPlugins" / INTERNAL_NAME
        problems += installed_layout_problems(plugin_root)

        if dev_dir.exists():
            problems.append(f"dev 설치가 그대로 남았다: {dev_dir}")

        config = json.loads((root / "dalamudConfig.json").read_text(encoding="utf-8"))
        first_id = working_plugin_id(plugin_root)
        problems += config_problems(
            config, first_id, str(dev_dir / f"{INTERNAL_NAME}.dll")
        )

        # 두 번째 실행: 갱신 경로다. 신원이 바뀌면 프로필에 죽은 항목이 쌓인다.
        second = run_installer(exe, root)
        if second.returncode != 0:
            problems.append(f"두 번째 설치가 실패했다(코드 {second.returncode})")
        elif working_plugin_id(plugin_root) != first_id:
            problems.append("두 번 설치했더니 WorkingPluginId가 바뀌었다")

        problems += installed_layout_problems(plugin_root)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return problems


def main(argv: list[str]) -> int:
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="배포 산출물 위생·모양 검사")
    parser.add_argument("--dist", default=str(repo / "dist"))
    parser.add_argument("--e2e", action="store_true", help="설치기를 실제로 돌려 본다")
    parser.add_argument("--kr-dalamud", help="KR Dalamud Hooks 폴더. 안 주면 프로필에서 찾는다")
    parser.add_argument("--dotnet", help=".NET SDK 경로. 안 주면 scoop 기본값")
    args = parser.parse_args(argv[1:])

    dist = Path(args.dist)
    problems = check_artifacts(dist, repo, default_needles())
    if not problems:
        problems += check_kr_binding(dist, repo, args.kr_dalamud, args.dotnet)
    if args.e2e:
        problems += check_install_e2e(dist)

    if problems:
        print("== 배포 검사: 확인 필요 ==\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("== 배포 검사: 통과 ==")
    print(f"  {dist}")
    if args.e2e:
        print("  설치 경로까지 실제로 돌려 봤다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
