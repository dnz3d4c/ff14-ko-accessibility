"""릴리스 매니페스트 생성기 테스트.

지키려는 것 둘.

- **값은 산출물에서 나온다.** 손으로 옮겨 적은 숫자는 낡고, 이 저장소는
  그걸로 이미 한 번 다쳤다(현황판 §8-1). 그래서 여기서는 "만든 것"이 아니라
  **"산출물에서 다시 계산한 것과 같은가"**를 잰다
- **못 읽었으면 만들지 않는다.** 버전을 못 읽었는데 빈 값으로 내보내면
  설치 프로그램이 자기 갱신을 무한히 다시 권한다(`ParseVersionLoose` 주석)

읽는 쪽의 규칙이 근거다 - `Installer/InstallerService.cs`의
`TrySelfUpdateAsync`(필드 셋)와 `ParseVersionLoose`(네 자리 채우기)다.
"""

import json
import os
import zipfile
from pathlib import Path

import pytest

import release_manifest as rm

VERSION = "5.88.0.0"

#: 업스트림이 쓰는 독일어 원문. 이게 그대로 나가면 한국 사용자가 못 읽는다.
GERMAN_DESCRIPTION = (
    "Macht FF14 für blinde Spieler zugänglich via NVDA/TOLK Integration, "
    "Audio-Navigation und vollständiger Tastatursteuerung."
)
GERMAN_PUNCHLINE = "FF14 für blinde Spieler via NVDA und Tastatur zugänglich machen."


def plugin_manifest(**overrides) -> dict:
    base = {
        "Author": "FF14 Accessibility Project",
        "Name": "FF14 Accessibility",
        "InternalName": "FF14Accessibility",
        "AssemblyVersion": VERSION,
        "Description": GERMAN_DESCRIPTION,
        "Punchline": GERMAN_PUNCHLINE,
        "ApplicableVersion": "any",
        "DalamudApiLevel": 15,
        "Tags": ["accessibility", "blind", "screenreader", "nvda"],
        "AcceptsFeedback": True,
    }
    base.update(overrides)
    return base


def make_zip(dist: Path, manifest: dict | None = plugin_manifest()) -> Path:
    path = dist / rm.ZIP_NAME
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{rm.INTERNAL_NAME}.dll", b"dll")
        if manifest is not None:
            archive.writestr(f"{rm.INTERNAL_NAME}.json", json.dumps(manifest))
    return path


def make_exe(dist: Path) -> Path:
    """버전 자원이 없는 가짜 EXE. 버전은 따로 넘겨 쓴다."""
    path = dist / rm.INSTALLER_NAME
    path.write_bytes(b"not a real PE")
    return path


# ── 압축에서 읽기 ──────────────────────────────────────────────────────────


def test_압축에서_매니페스트를_읽는다(tmp_path):
    make_zip(tmp_path)
    assert rm.read_plugin_manifest(tmp_path / rm.ZIP_NAME)["AssemblyVersion"] == VERSION


def test_압축이_없으면_만들지_않는다(tmp_path):
    with pytest.raises(rm.ManifestError, match="압축이 없다"):
        rm.read_plugin_manifest(tmp_path / rm.ZIP_NAME)


def test_압축_안에_매니페스트가_없으면_만들지_않는다(tmp_path):
    make_zip(tmp_path, manifest=None)
    with pytest.raises(rm.ManifestError, match="매니페스트가 없다"):
        rm.read_plugin_manifest(tmp_path / rm.ZIP_NAME)


# ── repo.json ──────────────────────────────────────────────────────────────


def entry(**overrides) -> dict:
    return rm.build_repo_manifest(plugin_manifest(**overrides))[0]


def test_배열_안에_객체_하나다():
    made = rm.build_repo_manifest(plugin_manifest())
    assert isinstance(made, list)
    assert len(made) == 1


def test_값을_손으로_안_적고_압축에서_가져온다():
    made = entry(AssemblyVersion="9.9.9.9", DalamudApiLevel=16)
    assert made["AssemblyVersion"] == "9.9.9.9"
    assert made["DalamudApiLevel"] == 16
    assert made["InternalName"] == "FF14Accessibility"


def test_저장소_주소와_내려받기_링크는_우리_것이다():
    made = entry()
    assert made["RepoUrl"] == rm.REPO_URL
    for field in ("DownloadLinkInstall", "DownloadLinkUpdate", "DownloadLinkTesting"):
        assert made[field] == rm.DOWNLOAD_URL
    # 업스트림 주소가 한 자리도 안 남아야 한다.
    assert "derbruedi" not in json.dumps(made)


def test_독일어_설명을_한국어로_바꾼다():
    made = entry()
    assert "blinde Spieler" not in made["Description"]
    assert "파이널 판타지 14" in made["Description"]
    assert "파이널 판타지 14" in made["Punchline"]


def test_이미_한국어면_그대로_둔다():
    made = entry(Punchline="한국어 한 줄 소개입니다.")
    assert made["Punchline"] == "한국어 한 줄 소개입니다."


def test_모르는_외국어_문장은_조용히_안_내보낸다():
    # 업스트림이 문구를 고치면 표가 빗나간다. 그때 독일어가 그대로 나가면
    # 아무도 모른 채 배포된다.
    with pytest.raises(rm.ManifestError, match="옮길 문장"):
        entry(Description="Ein ganz neuer Satz vom Upstream.")


def test_있어야_할_필드가_비면_만들지_않는다():
    with pytest.raises(rm.ManifestError, match="AssemblyVersion"):
        entry(AssemblyVersion="")


def test_업스트림_필드_순서를_따른다():
    assert list(entry()) == list(rm.FIELD_ORDER)


# ── installer.json ─────────────────────────────────────────────────────────


def test_설치_프로그램_매니페스트는_세_필드다(tmp_path):
    exe = make_exe(tmp_path)
    made = rm.build_installer_manifest(exe, "1.1.0.0")
    assert set(made) == {"InstallerVersion", "AssetName", "Sha256"}
    assert made["AssetName"] == rm.INSTALLER_NAME


def test_해시는_실제_파일에서_계산한다(tmp_path):
    import hashlib

    exe = make_exe(tmp_path)
    made = rm.build_installer_manifest(exe, "1.1.0.0")
    assert made["Sha256"].lower() == hashlib.sha256(exe.read_bytes()).hexdigest()


def test_버전이_세_자리면_네_자리로_채운다(tmp_path):
    # 읽는 쪽(`ParseVersionLoose`)이 네 자리로 채워 비교한다. 우리가 세 자리로
    # 내보내면 같은 판을 새 판으로 읽어 갱신을 무한히 다시 권한다.
    made = rm.build_installer_manifest(make_exe(tmp_path), "1.1.0")
    assert made["InstallerVersion"] == "1.1.0.0"


def test_버전_정규화():
    assert rm.normalize_version("1.1.0.0") == "1.1.0.0"
    assert rm.normalize_version("1.1.0") == "1.1.0.0"
    assert rm.normalize_version("1.1") == "1.1.0.0"
    assert rm.normalize_version("v1.1.0") == "1.1.0.0"


def test_읽는_쪽이_못_읽을_버전은_거른다():
    # 마디가 다섯이면 `ParseVersionLoose`가 null을 돌려주고, 그러면 비교가
    # 문자열 같음으로 떨어져 갱신을 계속 권한다.
    for bad in ("1.1.0.0.1", "1.1.0-kr.1", ""):
        with pytest.raises(rm.ManifestError, match="버전"):
            rm.normalize_version(bad)


def test_EXE에서_버전을_못_읽으면_만들지_않는다(tmp_path):
    with pytest.raises(rm.ManifestError, match="버전 자원"):
        rm.file_version(make_exe(tmp_path))


def test_EXE가_없으면_만들지_않는다(tmp_path):
    with pytest.raises(rm.ManifestError, match="설치 프로그램이 없다"):
        rm.file_version(tmp_path / rm.INSTALLER_NAME)


@pytest.mark.skipif(
    not (Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "notepad.exe").is_file(),
    reason="윈도 표준 EXE가 없다",
)
def test_진짜_PE에서는_버전을_읽는다():
    """ctypes 배선이 실제로 도는가. 값이 아니라 모양만 본다."""
    exe = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "notepad.exe"
    version = rm.file_version(exe)
    assert len(version.split(".")) == 4
    assert all(part.isdigit() for part in version.split("."))


# ── 다시 재기 ──────────────────────────────────────────────────────────────
#
# 만든 뒤에 산출물만 다시 빌드하면 매니페스트가 조용히 낡는다. 그 상태가
# 제일 나쁘다 - 설치 프로그램이 해시가 안 맞는다며 갱신을 거부하는데,
# 그건 사용자 화면에서만 보인다.


def make_dist(tmp_path) -> Path:
    make_zip(tmp_path)
    make_exe(tmp_path)
    rm.write_manifests(tmp_path, installer_version="1.1.0.0")
    return tmp_path


def test_갓_만든_것은_통과한다(tmp_path):
    dist = make_dist(tmp_path)
    assert rm.manifest_problems(dist, installer_version="1.1.0.0") == []


def test_해시가_실제_파일과_다르면_잡는다(tmp_path):
    dist = make_dist(tmp_path)
    path = dist / rm.INSTALLER_MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["Sha256"] = "0" * 64
    path.write_text(json.dumps(manifest), encoding="utf-8")

    problems = rm.manifest_problems(dist, installer_version="1.1.0.0")
    assert any("Sha256" in p for p in problems)


def test_압축을_다시_빌드해_버전이_갈리면_잡는다(tmp_path):
    dist = make_dist(tmp_path)
    make_zip(dist, plugin_manifest(AssemblyVersion="5.89.0.0"))

    problems = rm.manifest_problems(dist, installer_version="1.1.0.0")
    assert any("AssemblyVersion" in p for p in problems)


def test_매니페스트가_아예_없으면_잡는다(tmp_path):
    make_zip(tmp_path)
    make_exe(tmp_path)
    problems = rm.manifest_problems(tmp_path, installer_version="1.1.0.0")
    assert any(rm.REPO_MANIFEST_NAME in p for p in problems)
    assert any(rm.INSTALLER_MANIFEST_NAME in p for p in problems)


def test_쓴_파일은_둘뿐이다(tmp_path):
    """`dist`의 기존 산출물을 건드리지 않는다."""
    dist = make_dist(tmp_path)
    assert sorted(p.name for p in dist.iterdir()) == sorted(
        [rm.ZIP_NAME, rm.INSTALLER_NAME, rm.REPO_MANIFEST_NAME, rm.INSTALLER_MANIFEST_NAME]
    )
