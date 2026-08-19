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

재는 갈래가 둘 더 있고, **보는 곳이 다르다.**

- `--check`는 `dist`를 잰다. 산출물만 다시 빌드하고 매니페스트를 안 고친
  상태를 잡는다
- `--release <태그>`는 **`dist`를 안 보고 릴리스에서 도로 받아** 잰다.
  `dist`가 완벽해도 업로드에서 하나 빠지면 그대로 나가는데, 그 실패는
  오류가 아니라 침묵이다

사용법:
    uv run --no-project python tools/release-manifest/release_manifest.py [--dist DIR] [--check]
    uv run --no-project python tools/release-manifest/release_manifest.py --release v5.88.0.0
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
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

#: 안내 문서가 **릴리스에 올라갈 때의 이름**이다. 폴더에 나갈 때는
#: `사용 안내.md`이고 그쪽은 `tools/pack-check`가 본다.
#:
#: **`gh`가 윈도에서 한글 파일 이름을 못 다룬다.** 2026-08-19 첫 릴리스에서
#: `사용 안내.md`가 `default.md`로 올라갔다. 오류도 안 났고 `gh release
#: upload`는 0으로 끝났다 - 받는 사람 화면에서만 이름이 틀린 것이라, 이
#: 검사가 아니었으면 그대로 나갔다.
#:
#: 폴더에 나가는 이름은 그대로 둔다. 거기서는 한글이 문제가 없고, 받는
#: 사람이 무슨 파일인지 아는 쪽이 낫다.
GUIDE_ASSET_NAME = "README.ko.md"

#: 우리 저장소. 업스트림(derbruedi)이 아니라 여기로 받아야 한다.
REPO_URL = "https://github.com/dnz3d4c/ff14-ko-accessibility"
DOWNLOAD_URL = f"{REPO_URL}/releases/latest/download/{ZIP_NAME}"

#: `gh`에 넘기는 꼴. 주소에서 뽑으므로 둘이 갈릴 일이 없다.
GH_REPO = REPO_URL.removeprefix("https://github.com/")

#: Dalamud에 등록되는 저장소 주소. 설치 프로그램이 이 문자열을 박아 두고
#: (`InstallerService.cs:73`) Dalamud가 `==`로 대조한다. 여기가 안 열리면
#: 커스텀 저장소 경로가 통째로 죽는다.
REPO_JSON_URL = f"{REPO_URL}/releases/latest/download/{REPO_MANIFEST_NAME}"

#: 한 릴리스에 같이 올라가야 하는 자산. `run\\release.bat`이 올리는 목록이다.
#: 하나라도 빠지면 받는 쪽은 오류가 아니라 "새 판이 없다"로 읽는다.
RELEASE_ASSETS = (
    INSTALLER_NAME,
    ZIP_NAME,
    GUIDE_ASSET_NAME,
    REPO_MANIFEST_NAME,
    INSTALLER_MANIFEST_NAME,
)

#: `repo.json`에서 내려받기 주소를 담는 자리. 셋이 같아야 한다.
DOWNLOAD_FIELDS = ("DownloadLinkInstall", "DownloadLinkUpdate", "DownloadLinkTesting")

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


def _parse_json(text: str, what: str) -> object:
    """JSON 하나를 읽는다. 깨졌으면 **그렇게 말한다.**

    스택트레이스로 죽으면 검사를 안 한 것과 같다 - 릴리스가 멀쩡한 것과
    검사가 못 읽은 것이 같은 얼굴이 된다. 이 도구가 존재하는 이유가 그
    부류를 가르는 것이다.
    """
    try:
        return json.loads(text)
    except ValueError as error:
        raise ManifestError(f"{what}을 못 읽었다: {error}") from error


def _parse_object(text: str, what: str) -> dict:
    """객체 하나를 담은 JSON."""
    loaded = _parse_json(text, what)
    if not isinstance(loaded, dict):
        raise ManifestError(f"{what}이 객체가 아니다: {type(loaded).__name__}")
    return loaded


def read_plugin_manifest(zip_path: Path) -> dict:
    """압축 안의 `FF14Accessibility.json`. repo.json의 값이 전부 여기서 나온다."""
    if not zip_path.is_file():
        raise ManifestError(f"압축이 없다: {zip_path}")

    name = f"{INTERNAL_NAME}.json"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            if name not in archive.namelist():
                raise ManifestError(f"압축 안에 매니페스트가 없다: {zip_path} 안의 {name}")
            # 빌드가 BOM을 붙여 낼 때가 있다. `utf-8-sig`는 없어도 그대로 읽는다.
            raw = archive.read(name).decode("utf-8-sig")
    except (zipfile.BadZipFile, OSError, UnicodeDecodeError) as error:
        # 올라간 압축이 깨진 것은 이 도구가 잡아야 할 바로 그 사고다.
        raise ManifestError(f"압축을 못 읽었다: {zip_path} ({error})") from error

    return _parse_object(raw, f"{zip_path.name} 안의 {name}")


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
        loaded = _parse_json(path.read_text(encoding="utf-8"), path.name)
        if isinstance(loaded, list):
            loaded = loaded[0] if loaded else {}
        # 객체가 아니면 빈 것으로 본다. 필드마다 어긋난다고 말하게 된다.
        actual = loaded if isinstance(loaded, dict) else {}
        for field, want in expected.items():
            if actual.get(field) != want:
                problems.append(f"{name}의 {field}가 산출물과 다르다: {actual.get(field)!r} != {want!r}")
    return problems



# ── 릴리스를 다시 재기 ─────────────────────────────────────────────────────
#
# **`dist`를 안 본다.** `dist`가 완벽해도 업로드에서 하나 빠지면 그대로
# 나가고, 그 실패는 오류가 아니라 침묵이다 - 받는 쪽은 "새 판이 없다"로
# 읽는다. 그래서 릴리스에서 도로 받아 다시 계산한다. `tools/pack-check`가
# "설치 프로그램이 성공이라 말했다"를 안 믿고 산출물을 다시 재는 것과
# 같은 수법이다.


class ReleaseFacts(NamedTuple):
    """릴리스에서 **실제로 확인한** 것. I/O는 여기까지고 판정은 순수 함수다."""

    tag: str
    asset_names: tuple[str, ...]
    repo_manifest: list[dict]
    installer_manifest: dict
    #: 릴리스 zip 안의 `FF14Accessibility.json`. `repo.json`과 대조한다.
    plugin_manifest: dict
    exe: Path
    exe_version: str
    #: 주소 -> 200 또는 못 연 이유.
    link_status: dict[str, int | str]
    #: 초안이면 받는 쪽에서 아예 안 보인다. 내는 사람 화면에서는 정상이다.
    is_draft: bool
    #: 비공개면 자산은 멀쩡한데 주소만 404다. `gh`로는 절대 안 드러난다.
    is_private: bool


def gh_failure(tag: str, stderr: str, returncode: int, missing: str | None = None) -> ManifestError:
    """`gh`가 실패했을 때 무엇을 말할지. 못 찾은 것은 따로 말한다.

    `missing`은 "못 찾았다"에 쓸 문장이다. 릴리스를 찾을 때와 저장소를 찾을
    때가 같은 말을 하면 원인을 엉뚱한 데서 찾게 된다.
    """
    if "not found" in stderr.lower() or "404" in stderr:
        return ManifestError(
            missing or f"릴리스가 없다: {tag} ({GH_REPO}). `run\\release.bat`으로 먼저 내고 다시 잰다"
        )
    return ManifestError(f"gh가 실패했다(코드 {returncode}): {stderr.strip() or '(출력 없음)'}")


def _gh(args: list[str], tag: str, timeout: int = 600, missing: str | None = None) -> str:
    """`gh`를 부르고 표준 출력을 돌려준다."""
    try:
        result = subprocess.run(
            ["gh", *args], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
        )
    except FileNotFoundError as error:
        raise ManifestError("gh를 못 찾았다. `scoop install gh` 뒤에 `gh auth login`") from error

    if result.returncode != 0:
        raise gh_failure(tag, result.stderr, result.returncode, missing)
    return result.stdout


def link_status(url: str, timeout: int = 30) -> int | str:
    """주소가 실제로 열리나. 본문은 안 읽는다.

    `gh`로는 못 보는 것을 본다 - **저장소가 비공개면 자산은 멀쩡히 있는데
    이 주소만 404다.** 받는 쪽이 쓰는 것은 이 주소뿐이다.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 - 상수 주소다
            return int(response.status)
    except urllib.error.HTTPError as error:
        return int(error.code)
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        return f"못 열었다: {error}"


def repo_is_private(repo: str) -> bool:
    """저장소가 비공개인가.

    **주소가 404일 때 원인을 말하려면 이게 필요하다.** `gh`는 인증을 갖고
    있어서 비공개 저장소의 자산도 멀쩡히 보고, 그래서 자산 목록만으로는
    "올라갔는데 아무도 못 받는" 상태가 절대 안 드러난다.
    """
    listing = _parse_object(
        _gh(["repo", "view", repo, "--json", "isPrivate"], repo, missing=f"저장소를 못 찾았다: {repo}"),
        "gh의 저장소 정보",
    )
    return bool(listing.get("isPrivate"))


def gather_release(tag: str, workdir: Path, repo: str = GH_REPO) -> ReleaseFacts:
    """릴리스에서 받아 온다. EXE가 160MB쯤이라 여기가 오래 걸린다."""
    listing = _parse_object(
        _gh(["release", "view", tag, "--repo", repo, "--json", "assets,isDraft"], tag),
        "gh의 릴리스 정보",
    )
    asset_names = tuple(asset["name"] for asset in listing.get("assets", []))

    downloaded = {}
    for name in (REPO_MANIFEST_NAME, INSTALLER_MANIFEST_NAME, INSTALLER_NAME, ZIP_NAME):
        if name not in asset_names:
            continue  # 없는 것은 `release_problems`가 자산 목록에서 말한다
        _gh(
            ["release", "download", tag, "--repo", repo, "--pattern", name,
             "--dir", str(workdir), "--clobber"],
            tag,
        )
        downloaded[name] = workdir / name

    exe = downloaded.get(INSTALLER_NAME)
    zip_path = downloaded.get(ZIP_NAME)
    repo_manifest = _read_repo_manifest(downloaded.get(REPO_MANIFEST_NAME))
    urls = {REPO_JSON_URL} | {
        url for field in DOWNLOAD_FIELDS if isinstance(url := repo_manifest[0].get(field), str)
    }
    return ReleaseFacts(
        tag=tag,
        asset_names=asset_names,
        repo_manifest=repo_manifest,
        installer_manifest=_read_installer_manifest(downloaded.get(INSTALLER_MANIFEST_NAME)),
        plugin_manifest=read_plugin_manifest(zip_path) if zip_path else {},
        exe=exe if exe else workdir / INSTALLER_NAME,
        exe_version=file_version(exe) if exe else "",
        link_status={url: link_status(url) for url in sorted(urls)},
        is_draft=bool(listing.get("isDraft")),
        is_private=repo_is_private(repo),
    )


def _load(path: Path) -> object:
    """릴리스에서 받은 JSON. 깨졌으면 그렇게 말한다 - 그것도 배포 사고다."""
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise ManifestError(f"릴리스의 {path.name}을 못 읽었다: {error}") from error
    return _parse_json(raw, f"릴리스의 {path.name}")


def _read_repo_manifest(path: Path | None) -> list[dict]:
    """못 받았으면 빈 껍데기. 없다는 말은 자산 목록이 한 번만 한다."""
    if path is None:
        return [{}]
    loaded = _load(path)
    if not isinstance(loaded, list) or not loaded or not isinstance(loaded[0], dict):
        raise ManifestError(f"릴리스의 {REPO_MANIFEST_NAME}이 객체 하나를 담은 배열이 아니다")
    return loaded


def _read_installer_manifest(path: Path | None) -> dict:
    if path is None:
        return {}
    loaded = _load(path)
    if not isinstance(loaded, dict):
        raise ManifestError(f"릴리스의 {INSTALLER_MANIFEST_NAME}이 객체가 아니다")
    return loaded


def _asset_problems(facts: ReleaseFacts) -> list[str]:
    """자산 다섯이 이름까지 정확히 있나."""
    problems = []
    for name in RELEASE_ASSETS:
        if name in facts.asset_names:
            continue
        near = [other for other in facts.asset_names if other.lower() == name.lower()]
        if near:
            # 설치 프로그램은 `OrdinalIgnoreCase`로 찾아 넘어가는데, 내려받기
            # 주소는 이름을 그대로 쓴다. 한쪽만 되는 상태다.
            problems.append(f"자산 이름의 대소문자가 다르다: {near[0]} (올려야 하는 이름은 {name})")
        else:
            problems.append(f"릴리스에 자산이 없다: {name}")
    return problems


def _installer_problems(facts: ReleaseFacts) -> list[str]:
    """설치 프로그램 자기 갱신이 실제로 도나."""
    problems = []
    manifest = facts.installer_manifest

    version = manifest.get("InstallerVersion")
    parts = version.split(".") if isinstance(version, str) else []
    if len(parts) != 4 or not all(part.isdigit() for part in parts):
        problems.append(f"installer.json의 InstallerVersion이 네 마디 숫자가 아니다: {version!r}")
    elif facts.exe_version and version != facts.exe_version:
        problems.append(
            f"installer.json의 InstallerVersion이 릴리스 EXE의 PE 버전과 다르다: "
            f"{version} != {facts.exe_version}"
        )

    asset_name = manifest.get("AssetName")
    if asset_name not in facts.asset_names:
        problems.append(f"installer.json의 AssetName이 릴리스에 없는 자산을 가리킨다: {asset_name!r}")

    if facts.exe.is_file():
        actual = sha256(facts.exe)
        if str(manifest.get("Sha256", "")).upper() != actual:
            problems.append(
                f"installer.json의 Sha256이 릴리스 EXE를 다시 계산한 값과 다르다: "
                f"{manifest.get('Sha256')!r} != {actual}"
            )
    return problems


def _why_blocked(facts: ReleaseFacts, url: str, status: int | str | None) -> str | None:
    """주소가 안 열리는 **까닭**. "404"만 말하면 받는 사람이 원인을 모른다.

    지어내지 않는다 - 아는 까닭이 없으면 모른다고 말한다. 이미 다른 줄이
    말한 까닭이면 `None`이다. 한 고장을 세 줄로 말하면 그중 아무것도 안 읽힌다.
    """
    wanted = url.rsplit("/", 1)[-1]
    if wanted not in facts.asset_names:
        return None  # 자산이 없다는 말은 위에서 이미 했다
    if facts.is_private:
        return (
            f"{url}이 {status}다. **저장소가 비공개라 받는 쪽에서 안 열린다** - "
            f"자산은 올라가 있고 `gh`로는 정상으로 보인다. 공개로 전환해야 한다"
        )
    if facts.is_draft:
        return f"{url}이 {status}다. 릴리스가 초안이라 받는 쪽에 아직 안 나간다"
    return f"{url}이 {status}다. 자산도 있고 공개인데 안 열린다 - 원인을 못 찾았다"


def _download_link_problems(facts: ReleaseFacts) -> list[str]:
    """받는 쪽이 실제로 여는 주소가 열리나."""
    problems = []
    entry = facts.repo_manifest[0] if facts.repo_manifest else {}

    links = {field: entry.get(field) for field in DOWNLOAD_FIELDS}
    install = links[DOWNLOAD_FIELDS[0]]
    for field, url in links.items():
        if url != install:
            problems.append(f"repo.json의 {field}가 다른 링크와 갈렸다: {url!r} != {install!r}")

    if isinstance(install, str):
        wanted = install.rsplit("/", 1)[-1]
        if wanted not in facts.asset_names:
            problems.append(f"repo.json의 내려받기 링크가 릴리스에 없는 파일을 가리킨다: {wanted}")

    for url in sorted({install, REPO_JSON_URL} if isinstance(install, str) else {REPO_JSON_URL}):
        status = facts.link_status.get(url)
        if status != 200 and (why := _why_blocked(facts, url, status)) is not None:
            problems.append(why)
    return problems


def _repo_manifest_problems(facts: ReleaseFacts) -> list[str]:
    """올라간 `repo.json`이 받는 쪽에서 쓸 수 있는 모양인가."""
    problems = []
    entry = facts.repo_manifest[0] if facts.repo_manifest else {}
    version = entry.get("AssemblyVersion")

    # 만드는 쪽은 `GERMAN_TO_KOREAN`이 막는다. 여기는 **올라간 쪽**이다.
    # 손으로 고친 것을 올렸거나 옛 판이 올라갔으면 여기서만 걸린다.
    for field in TRANSLATED:
        if not _HANGUL.search(str(entry.get(field, ""))):
            problems.append(
                f"repo.json의 {field}에 한국어가 없다: {entry.get(field)!r}. "
                f"Dalamud 플러그인 목록에 그대로 그려진다"
            )

    # 태그가 곧 플러그인 버전이다. `ChoosePluginSourceAsync`가 태그에서 v를
    # 떼어 설치된 버전과 비교하므로, 태그가 낮으면 새 판이 올라가 있어도
    # 받는 쪽은 "이미 최신"으로 읽는다.
    if version and facts.tag.lstrip("vV") != version:
        problems.append(f"태그가 플러그인 버전과 다르다: {facts.tag} (repo.json은 {version})")

    # 올라간 zip이 repo.json이 말하는 그 판인가. 어긋나면 Dalamud가 받아
    # 놓고 같은 판을 다시 받는다.
    built = facts.plugin_manifest.get("AssemblyVersion")
    if built and version and built != version:
        problems.append(
            f"repo.json과 릴리스 압축 안 매니페스트의 버전이 다르다: {version} != {built}. "
            f"Dalamud가 받아 놓고 같은 판을 다시 받는다"
        )
    return problems


def release_problems(facts: ReleaseFacts) -> list[str]:
    """릴리스가 받는 쪽이 기대하는 모양인가. `dist`는 안 본다."""
    problems = []
    if facts.is_draft:
        # 내는 사람 화면에서는 멀쩡해 보이는데 받는 쪽에서는 아예 안 보인다.
        problems.append(f"{facts.tag}가 초안이다. 받는 쪽에서는 아예 안 보인다")

    return (
        problems
        + _asset_problems(facts)
        + _installer_problems(facts)
        + _repo_manifest_problems(facts)
        + _download_link_problems(facts)
    )


def check_release(tag: str, repo: str = GH_REPO) -> list[str]:
    """릴리스를 받아 재고 문제를 돌려준다. 받은 것은 지운다."""
    workdir = Path(tempfile.mkdtemp(prefix="ff14acc-release-"))
    try:
        return release_problems(gather_release(tag, workdir, repo))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


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
    parser.add_argument(
        "--release",
        metavar="태그",
        help="릴리스에 실제로 올라간 것을 받아 다시 잰다. 자산을 내려받아 몇 분 걸린다",
    )
    args = parser.parse_args(argv[1:])

    dist = Path(args.dist)
    try:
        # 릴리스를 낸 다음에 돌린다. `--check`는 `dist`가 자기 자신과 맞나를
        # 보고, 이쪽은 **올라간 것**을 받아 잰다 - 업로드에서 하나 빠진 것은
        # `dist`를 아무리 봐도 안 나온다.
        if args.release:
            problems = check_release(args.release)
            if problems:
                print(f"== 릴리스 {args.release}: 확인 필요 ==\n")
                for problem in problems:
                    print(f"  - {problem}")
                return 1
            print(f"== 릴리스 {args.release}: 받는 쪽이 읽을 수 있다 ==")
            print(f"  자산 {len(RELEASE_ASSETS)}개, 해시·버전·주소 대조 통과")
            return 0

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
