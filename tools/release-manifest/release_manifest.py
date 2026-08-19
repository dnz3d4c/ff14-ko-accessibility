"""릴리스에 같이 올릴 매니페스트 둘을 산출물에서 만든다.

`dist`에 이미 있는 것을 읽어 같은 자리에 두 파일을 낸다.

1. **`dist\\repo.json`** - Dalamud 커스텀 저장소 매니페스트. 사용자가 저장소
   주소를 등록해 두면 Dalamud가 이걸 보고 새 판을 알아서 받는다. 형식은
   업스트림 `repo.json`을 본뜨고, 값은 **압축 안의
   `FF14Accessibility.json`에서 읽는다** - 저장소 주소와 내려받기 링크만
   우리 것으로 갈아 끼운다
2. **`dist\\installer.json`** - 설치 프로그램 자기 갱신용. 읽는 쪽은
   `Installer/InstallerService.cs`의 `TrySelfUpdateAsync`이고, 거기서 쓰는
   필드는 `InstallerVersion`·`AssetName`·`Sha256` 셋이다

**값을 손으로 안 적는 것이 이 도구의 존재 이유다.** 이 저장소는 손으로 옮겨
적은 숫자가 낡아서 실제로 다친 적이 있다(현황판 §8-1, `tools/docs-check`가
같은 이유로 있다). 릴리스 매니페스트는 그중에서도 낡은 것이 제일 늦게
드러나는 자리다 - 해시가 어긋나면 설치 프로그램이 갱신을 거부하는데, 그건
받는 사람 화면에서만 보인다.

`--check`는 만들지 않고 다시 잰다. 산출물만 다시 빌드하고 매니페스트를 안
고친 상태를 잡는다.

사용법:
    uv run --no-project python tools/release-manifest/release_manifest.py [--dist DIR] [--check]
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import NamedTuple

#: 플러그인 내부 이름. 압축 안의 매니페스트 파일 이름이기도 하다.
INTERNAL_NAME = "FF14Accessibility"

#: 릴리스에 올라가는 산출물 이름. `AssetName`도 여기서 나온다.
ZIP_NAME = f"{INTERNAL_NAME}.zip"
INSTALLER_NAME = "FF14AccessibilityInstaller-KR.exe"

#: 이 도구가 만드는 것. `dist`의 나머지는 건드리지 않는다.
REPO_MANIFEST_NAME = "repo.json"
INSTALLER_MANIFEST_NAME = "installer.json"

#: 우리 저장소. 업스트림(derbruedi)이 아니라 여기로 받아야 한다.
REPO_URL = "https://github.com/dnz3d4c/ff14-ko-accessibility"
DOWNLOAD_URL = f"{REPO_URL}/releases/latest/download/{ZIP_NAME}"

#: 업스트림 `repo.json`의 필드 순서. 형식을 본뜨는 자리라 순서까지 맞춘다.
FIELD_ORDER = (
    "Author",
    "Name",
    "InternalName",
    "AssemblyVersion",
    "Description",
    "Punchline",
    "ApplicableVersion",
    "DalamudApiLevel",
    "RepoUrl",
    "Tags",
    "AcceptsFeedback",
    "DownloadLinkInstall",
    "DownloadLinkUpdate",
    "DownloadLinkTesting",
)

#: 압축 안 매니페스트가 아니라 우리가 정하는 값.
OURS = {
    "RepoUrl": REPO_URL,
    "DownloadLinkInstall": DOWNLOAD_URL,
    "DownloadLinkUpdate": DOWNLOAD_URL,
    "DownloadLinkTesting": DOWNLOAD_URL,
}

#: 한국어로 옮겨 넣는 자리. 나머지는 압축 안의 값을 그대로 쓴다.
TRANSLATED = ("Description", "Punchline")

#: 비어 있으면 만들지 않는다. Dalamud 플러그인 목록이 이 값들로 그려진다.
REQUIRED = ("InternalName", "Name", "AssemblyVersion", "DalamudApiLevel", "Description", "Punchline")

#: 업스트림 독일어 문장 -> 한국어. 문구의 근거는 `overlay/ko/README.ko.md`
#: 첫머리가 모드를 소개하는 문장이다.
#:
#: **표를 키로 두는 이유**: 업스트림이 문구를 고치면 여기서 못 찾고 걸린다.
#: "한국어가 아니면 그냥 원문을 쓴다"로 두면 독일어가 조용히 배포된다.
GERMAN_TO_KOREAN = {
    "Macht FF14 für blinde Spieler zugänglich via NVDA/TOLK Integration, "
    "Audio-Navigation und vollständiger Tastatursteuerung.": (
        "파이널 판타지 14를 한국 서버에서 스크린 리더로 플레이할 수 있게 합니다. "
        "NVDA와 Tolk 연동, 소리 안내, 키보드만으로 하는 조작을 제공합니다."
    ),
    "FF14 für blinde Spieler via NVDA und Tastatur zugänglich machen.": (
        "파이널 판타지 14를 한국 서버에서 스크린 리더로 플레이할 수 있게 하는 모드입니다."
    ),
}

_HANGUL = re.compile(r"[가-힣]")


class ManifestError(Exception):
    """매니페스트를 만들 수 없다. 빈 값으로 내보내는 것보다 안 만드는 것이 낫다."""


# ── 압축에서 읽기 ──────────────────────────────────────────────────────────


def read_plugin_manifest(zip_path: Path) -> dict:
    """압축 안의 `FF14Accessibility.json`. repo.json의 값이 전부 여기서 나온다."""
    if not zip_path.is_file():
        raise ManifestError(f"압축이 없다: {zip_path}")

    name = f"{INTERNAL_NAME}.json"
    with zipfile.ZipFile(zip_path) as archive:
        if name not in archive.namelist():
            raise ManifestError(f"압축 안에 매니페스트가 없다: {zip_path} 안의 {name}")
        # 빌드가 BOM을 붙여 낼 때가 있다. `utf-8-sig`는 없어도 그대로 읽는다.
        return json.loads(archive.read(name).decode("utf-8-sig"))


# ── repo.json ──────────────────────────────────────────────────────────────


def korean_text(field: str, value: str) -> str:
    """설명 문구를 한국어로. 한국어면 그대로, 아니면 표에서 찾는다."""
    if _HANGUL.search(value):
        return value

    korean = GERMAN_TO_KOREAN.get(value.strip())
    if korean is None:
        raise ManifestError(
            f"{field}에 한국어가 없고 옮길 문장도 표에 없다: {value!r}. "
            f"업스트림이 문구를 고쳤으면 GERMAN_TO_KOREAN에 새 원문을 등록해라"
        )
    return korean


def build_repo_manifest(plugin: dict) -> list[dict]:
    """Dalamud 커스텀 저장소 매니페스트. 배열 안에 객체 하나다."""
    missing = [field for field in REQUIRED if not plugin.get(field)]
    if missing:
        raise ManifestError(f"압축 안 매니페스트에 값이 없다: {', '.join(missing)}")

    entry: dict = {}
    for field in FIELD_ORDER:
        if field in OURS:
            entry[field] = OURS[field]
        elif field in TRANSLATED:
            entry[field] = korean_text(field, plugin[field])
        elif field in plugin:
            entry[field] = plugin[field]
    return [entry]


# ── installer.json ─────────────────────────────────────────────────────────


class _FixedFileInfo(ctypes.Structure):
    """`VS_FIXEDFILEINFO`. 파일 버전은 32비트 둘에 16비트씩 네 마디로 들어 있다."""

    _fields_ = [
        (name, ctypes.c_uint32)
        for name in (
            "dwSignature",
            "dwStrucVersion",
            "dwFileVersionMS",
            "dwFileVersionLS",
            "dwProductVersionMS",
            "dwProductVersionLS",
            "dwFileFlagsMask",
            "dwFileFlags",
            "dwFileOS",
            "dwFileType",
            "dwFileSubtype",
            "dwFileDateMS",
            "dwFileDateLS",
        )
    ]


def file_version(exe: Path) -> str:
    """EXE의 PE 버전 자원에서 FileVersion을 읽는다.

    **왜 파일 이름이나 csproj가 아닌가**: 읽는 쪽이 대조하는 것은 실행 중인
    EXE의 어셈블리 버전이다(`InstallerService.cs:134`). 그 값이 나가는 자리가
    PE 버전 자원이고, `Installer.csproj`가 `AssemblyVersion`과 `FileVersion`을
    같은 값으로 박는다. 그러니 **배포할 그 파일에서 직접 읽는 것**이 소스와
    산출물이 갈린 상태까지 잡는다.
    """
    if not exe.is_file():
        raise ManifestError(f"설치 프로그램이 없다: {exe}")

    version_dll = ctypes.WinDLL("version.dll")
    path = str(exe.resolve())

    size = version_dll.GetFileVersionInfoSizeW(path, None)
    if not size:
        raise ManifestError(f"설치 프로그램에 버전 자원이 없다: {exe}")

    buffer = ctypes.create_string_buffer(size)
    if not version_dll.GetFileVersionInfoW(path, 0, size, buffer):
        raise ManifestError(f"설치 프로그램의 버전 자원을 못 읽었다: {exe}")

    block = ctypes.c_void_p()
    length = ctypes.c_uint()
    if not version_dll.VerQueryValueW(buffer, "\\", ctypes.byref(block), ctypes.byref(length)):
        raise ManifestError(f"설치 프로그램의 버전 자원이 비어 있다: {exe}")

    info = ctypes.cast(block, ctypes.POINTER(_FixedFileInfo)).contents
    return ".".join(
        str(part)
        for part in (
            info.dwFileVersionMS >> 16,
            info.dwFileVersionMS & 0xFFFF,
            info.dwFileVersionLS >> 16,
            info.dwFileVersionLS & 0xFFFF,
        )
    )


def normalize_version(text: str) -> str:
    """읽는 쪽이 비교하는 모양으로 맞춘다 - 숫자 네 마디다.

    `ParseVersionLoose`가 모자란 마디를 `.0`으로 채우고 나서 비교한다. 우리가
    세 마디로 내보내도 읽는 쪽에서 같아지긴 하지만, **채우기 전의 문자열이
    남아 다른 자리(`IsNewer`의 문자열 폴백)로 새면** 같은 판을 새 판으로 보고
    갱신을 무한히 다시 권한다. 마디가 다섯이거나 숫자가 아니면 그 폴백에
    떨어지므로 아예 거른다.
    """
    parts = text.strip().lstrip("vV").split(".")
    if not 1 <= len(parts) <= 4 or not all(part.isdigit() for part in parts):
        raise ManifestError(f"읽는 쪽이 못 읽는 버전이다(숫자 네 마디까지): {text!r}")
    return ".".join(parts + ["0"] * (4 - len(parts)))


def sha256(path: Path) -> str:
    """읽는 쪽(`ComputeSha256`)이 `Convert.ToHexString`을 쓴다. 대문자로 맞춘다."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def build_installer_manifest(exe: Path, version: str) -> dict[str, str]:
    """설치 프로그램 자기 갱신용. `TrySelfUpdateAsync`가 읽는 셋뿐이다."""
    return {
        "InstallerVersion": normalize_version(version),
        "AssetName": exe.name,
        "Sha256": sha256(exe),
    }


# ── 만들기와 다시 재기 ─────────────────────────────────────────────────────


class Manifests(NamedTuple):
    """만든 두 매니페스트. `repo.json`은 배열이고 `installer.json`은 객체다."""

    repo: list[dict]
    installer: dict[str, str]


def _files(made: Manifests) -> tuple[tuple[str, list[dict] | dict[str, str]], ...]:
    """(파일 이름, 그 파일에 들어갈 것). 쓸 때와 다시 잴 때가 같은 목록을 본다."""
    return ((REPO_MANIFEST_NAME, made.repo), (INSTALLER_MANIFEST_NAME, made.installer))


def _build(dist: Path, installer_version: str | None) -> Manifests:
    """두 매니페스트의 내용. 값은 전부 `dist`의 산출물에서 나온다."""
    exe = dist / INSTALLER_NAME
    version = installer_version if installer_version else file_version(exe)
    return Manifests(
        repo=build_repo_manifest(read_plugin_manifest(dist / ZIP_NAME)),
        installer=build_installer_manifest(exe, version),
    )


def write_manifests(dist: Path, installer_version: str | None = None) -> Manifests:
    """두 파일을 `dist`에 쓴다. 다른 산출물은 건드리지 않는다."""
    made = _build(dist, installer_version)
    for name, content in _files(made):
        (dist / name).write_text(
            json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return made


def manifest_problems(dist: Path, installer_version: str | None = None) -> list[str]:
    """이미 있는 매니페스트가 지금 산출물과 맞나. 만들지 않고 재기만 한다."""
    problems = []
    for name, content in _files(_build(dist, installer_version)):
        path = dist / name
        if not path.is_file():
            problems.append(f"매니페스트가 없다: {path}")
            continue

        expected = content[0] if isinstance(content, list) else content
        actual = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(actual, list):
            actual = actual[0] if actual else {}
        for field, want in expected.items():
            if actual.get(field) != want:
                problems.append(f"{name}의 {field}가 산출물과 다르다: {actual.get(field)!r} != {want!r}")
    return problems


def main(argv: list[str]) -> int:
    repo = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="릴리스 매니페스트를 산출물에서 만든다")
    parser.add_argument("--dist", default=str(repo / "dist"))
    parser.add_argument("--check", action="store_true", help="만들지 않고 산출물과 대조만 한다")
    parser.add_argument(
        "--print-version",
        action="store_true",
        help="플러그인 버전만 한 줄로 낸다. `run\\release.bat`이 릴리스 태그를 이걸로 만든다",
    )
    args = parser.parse_args(argv[1:])

    dist = Path(args.dist)
    try:
        # 태그가 곧 플러그인 버전이다 - 설치 프로그램이 태그에서 v를 떼어
        # 설치된 버전과 비교한다(`ChoosePluginSourceAsync`). 그래서 손으로
        # 짓지 않고 배포할 압축에서 그대로 뽑는다.
        if args.print_version:
            print(build_repo_manifest(read_plugin_manifest(dist / ZIP_NAME))[0]["AssemblyVersion"])
            return 0

        if args.check:
            problems = manifest_problems(dist)
            if problems:
                print("== 릴리스 매니페스트: 확인 필요 ==\n")
                for problem in problems:
                    print(f"  - {problem}")
                return 1
            print("== 릴리스 매니페스트: 산출물과 맞는다 ==")
            return 0

        made = write_manifests(dist)
    except ManifestError as error:
        print(f"== 릴리스 매니페스트: 만들지 못했다 ==\n\n  - {error}", file=sys.stderr)
        return 1

    plugin, installer = made.repo[0], made.installer
    print("== 릴리스 매니페스트 ==")
    print(f"  {dist / REPO_MANIFEST_NAME}")
    print(f"    {plugin['InternalName']} {plugin['AssemblyVersion']} (Dalamud API {plugin['DalamudApiLevel']})")
    print(f"  {dist / INSTALLER_MANIFEST_NAME}")
    print(f"    {installer['AssetName']} {installer['InstallerVersion']}")
    print(f"    SHA-256 {installer['Sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
