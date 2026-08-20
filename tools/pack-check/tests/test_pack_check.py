"""배포 검사 테스트.

지키려는 것 둘.

- **배포물에 이 머신의 것이 섞이지 않는다.** 사용자 이름·홈 경로·설정 파일
- **설치 결과가 Dalamud가 읽는 모양이다.** 어긋나면 오류가 아니라 **침묵**이다.
  버전이 아닌 폴더 이름은 Dalamud가 지우고, 고아 판정을 받으면 적재를 건너뛴다.
  둘 다 게임 안에서는 "모드가 안 뜬다"로만 보인다

여기 있는 것은 규칙 자체다. 산출물을 실제로 재는 것은 `--e2e`가 하고,
그건 `run\\pack.bat`이 패킹 직후에 돌린다.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pack_check
import pytest

VERSION = "5.87.0.0"
REPO = Path(__file__).resolve().parents[3]


def zip_names(extra: list[str] | None = None) -> list[str]:
    names = [
        "FF14Accessibility.dll",
        "FF14Accessibility.json",
        "FF14Accessibility.deps.json",
        "FF14Accessibility.pdb",
        "NAudio.dll",
        "NAudio.Core.dll",
        "Tolk.dll",
        "nvdaControllerClient64.dll",
        "LICENSE",
        "THIRD-PARTY-NOTICES.md",
    ]
    return names + (extra or [])


def manifest(**overrides) -> dict:
    base = {
        "InternalName": "FF14Accessibility",
        "AssemblyVersion": VERSION,
        "DalamudApiLevel": 15,
    }
    base.update(overrides)
    return base


# ── 압축 위생 ──────────────────────────────────────────────────────────────


def test_정상_목록은_통과한다():
    assert pack_check.zip_problems(zip_names()) == []


def test_모르는_파일이_섞이면_잡는다():
    problems = pack_check.zip_problems(zip_names(["dalamudConfig.json"]))
    assert any("dalamudConfig.json" in p for p in problems)


def test_설정_폴더째_들어가면_잡는다():
    problems = pack_check.zip_problems(zip_names(["pluginConfigs/FF14Accessibility.json"]))
    assert any("폴더" in p for p in problems)


def test_dll이_빠지면_잡는다():
    names = [n for n in zip_names() if n != "FF14Accessibility.dll"]
    assert any("FF14Accessibility.dll" in p for p in pack_check.zip_problems(names))


def test_개인_흔적을_utf16으로도_찾는다():
    blob = b"\x00\x01" + "tester".encode("utf-16-le")
    assert pack_check.personal_traces(blob, ["tester"]) == ["tester"]


def test_흔적이_없으면_조용하다():
    assert pack_check.personal_traces(b"harmless bytes", ["tester"]) == []


# ── 매니페스트 ─────────────────────────────────────────────────────────────


def test_매니페스트가_빌드와_같으면_통과():
    assert pack_check.manifest_problems(manifest(), VERSION) == []


def test_버전이_어긋나면_잡는다():
    problems = pack_check.manifest_problems(manifest(), "5.88.0.0")
    assert any("버전이 빌드 설정과 다르다" in p for p in problems)


def test_설치_뒤에_붙는_필드가_배포물에_있으면_잡는다():
    problems = pack_check.manifest_problems(manifest(WorkingPluginId="x"), VERSION)
    assert any("WorkingPluginId" in p for p in problems)


# ── 설치 모양 ──────────────────────────────────────────────────────────────


def install(tmp_path, version_dir: str = VERSION, **manifest_overrides):
    root = tmp_path / "installedPlugins" / "FF14Accessibility"
    target = root / version_dir
    target.mkdir(parents=True)
    (target / "FF14Accessibility.dll").write_bytes(b"dll")
    fields = {
        "InternalName": "FF14Accessibility",
        "AssemblyVersion": version_dir,
        "DalamudApiLevel": 15,
        "InstalledFromUrl": pack_check.KR_REPO_URL,
        "Disabled": False,
        "ScheduledForDeletion": False,
        "WorkingPluginId": "3a0abc23-2f5e-4a55-bbd2-f517f16e51db",
    }
    fields.update(manifest_overrides)
    (target / "FF14Accessibility.json").write_text(json.dumps(fields), encoding="utf-8")
    return root


def test_정식_설치_모양은_통과한다(tmp_path):
    assert pack_check.installed_layout_problems(install(tmp_path)) == []


def test_버전이_아닌_폴더_이름을_잡는다(tmp_path):
    # Dalamud의 CleanupPlugins가 이런 폴더를 지운다. 조용히 사라진다.
    root = install(tmp_path, version_dir="latest")
    assert any("버전이 아니다" in p for p in pack_check.installed_layout_problems(root))


def test_고아가_되는_출처를_잡는다(tmp_path):
    root = install(tmp_path, InstalledFromUrl="")
    problems = pack_check.installed_layout_problems(root)
    assert any("고아" in p for p in problems)


def test_저장소를_안_가리키면_잡는다(tmp_path):
    # OFFICIAL은 적재는 되지만 "공식 저장소가 우리를 목록에 갖고 있다"는 주장이고
    # 그건 사실이 아니다. Dalamud가 IsDecommissioned를 세우고, 프로필을 다시
    # 적용할 때(캐릭터 전환) 켜지지 않는다. 설치 프로그램이 저장소를 등록한 뒤
    # 매니페스트를 옮기므로, 끝나고도 OFFICIAL이면 그 단계가 안 돈 것이다.
    root = install(tmp_path, InstalledFromUrl="OFFICIAL")
    assert any("저장소" in p for p in pack_check.installed_layout_problems(root))


def test_설치_프로그램의_씨앗과_같은_컨테이너를_만든다(tmp_path):
    # 검사가 설치 프로그램보다 더 갖춰진 프로필을 만들면, 설치 프로그램이 못
    # 만드는 구조를 검사가 대신 만들어 주는 셈이 된다. 그래서 첫 설치가 반드시
    # 실패하는 결함이 배포 직전까지 안 잡혔다(2026-08-19).
    root = tmp_path / "profile"
    root.mkdir()
    pack_check._seed_profile(root)

    seeded = json.loads((root / "dalamudConfig.json").read_text(encoding="utf-8"))
    assert set(seeded) - {"$type"} == pack_check.installer_seed_containers(REPO)


def test_버전_폴더가_둘이면_잡는다(tmp_path):
    root = install(tmp_path)
    (root / "5.86.0.0").mkdir()
    assert any("하나여야" in p for p in pack_check.installed_layout_problems(root))


def test_신원이_비면_잡는다(tmp_path):
    root = install(tmp_path, WorkingPluginId="")
    assert any("WorkingPluginId" in p for p in pack_check.installed_layout_problems(root))


def test_버전_파싱():
    assert pack_check.parse_version("5.87.0.0") == (5, 87, 0, 0)
    assert pack_check.parse_version("5.87") == (5, 87)
    assert pack_check.parse_version("latest") is None
    assert pack_check.parse_version("5.87.0-rc1") is None


# ── KR 바인딩 ──────────────────────────────────────────────────────────────

ASMREF_FAIL = """\
# plugin: FF14Accessibility.dll
# Dalamud ref=15.0.3.2 actual=15.0.3.2
  (no issues)
# FFXIVClientStructs ref=7.55.1.8875 actual=7.51.0.8667
  MISSING MEMBER  ...RaptureGearsetModule.IsItemRegisteredToGearset    want Boolean ...
SUMMARY: 931 checked, 0 missing-type, 1 missing-member, 0 arity, 0 sig-diff
"""


def test_안_붙는_멤버만_뽑아_말한다():
    # 931건 중 걸린 한 줄이 전문에 묻히면 아무도 안 읽는다.
    detail = pack_check.binding_detail(ASMREF_FAIL)
    assert "IsItemRegisteredToGearset" in detail
    assert "no issues" not in detail


def test_고를_줄이_없으면_원문이라도_보여_준다():
    assert "터졌다" in pack_check.binding_detail("", "도구가 터졌다")
    assert pack_check.binding_detail("", "") == "(출력 없음)"


# ── Dalamud 준비 완료 판정 ─────────────────────────────────────────────────
#
# **넷 중 셋은 정상 실행에서 안 생긴다.** 마커 없이 폴더만 있는 상태는 업데이터가
# 아직 쓰는 중일 때이고, 2026-08-20에 설치 프로그램이 정확히 그 틈에 끼어들어
# 플러그인을 먼저 깔았다(07:57:41 배치, 에셋은 07:57:46 도착). 조건을 인위로
# 만들지 않으면 한 번도 안 태워지는 휴면 경로다.
#
# 판정을 파이썬으로 옮겨 적지 않고 **실물 EXE에 물어본다.** 옮겨 적으면 그게
# 두 번째 사본이 되고, 사본은 조용히 갈라진다(`installer_seed_containers`가
# 소스에서 씨앗을 읽는 것과 같은 이유다).

INSTALLER_CSPROJ = (
    REPO / "vendor" / "ff14-accessibility" / "Installer" / "FF14AccessibilityInstaller.csproj"
)


@pytest.fixture(scope="module")
def installer_exe() -> Path:
    """지금 소스에서 빌드한 설치 프로그램.

    `dist/`의 것을 안 쓴다 - 그건 **마지막 패킹 시점의 것**이라, 판정을 고친
    직후에 재면 낡은 바이너리를 재고 초록이 거짓말이 된다.
    """
    dotnet = pack_check.dotnet_path()
    if not dotnet.is_file() or not INSTALLER_CSPROJ.is_file():
        pytest.skip("dotnet SDK나 설치 프로그램 소스가 없다")

    built = subprocess.run(
        [str(dotnet), "build", "-c", "Release", str(INSTALLER_CSPROJ), "-v", "quiet", "--nologo"],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if built.returncode != 0:
        pytest.fail(f"설치 프로그램 빌드 실패:\n{built.stdout}{built.stderr}")

    # `publish\`는 제외한다. `run\pack.bat`이 거기에 배포용 EXE를 남기는데,
    # 그건 방금 빌드한 것이 아니라 **마지막 패킹 시점의 것**이다. 실제로 그걸
    # 집어서 옛 판정을 재고 있었다.
    exes = [
        exe
        for exe in (INSTALLER_CSPROJ.parent / "bin" / "Release").rglob("*-KR.exe")
        if "publish" not in exe.parts
    ]
    if not exes:
        pytest.fail("빌드는 됐는데 EXE를 못 찾았다")
    return max(exes, key=lambda exe: exe.stat().st_mtime)


@pytest.mark.parametrize(
    ("marker", "assets", "ready", "label"),
    [
        (False, False, False, "빈 Hooks 폴더만 - 옛 설치 잔재도 이 모양이다"),
        (False, True, False, "마커 없이 에셋만"),
        (True, False, False, "마커는 왔고 에셋이 아직 없다 - 실제로 겪은 상태"),
        (True, True, True, "둘 다 있다"),
    ],
)
def test_준비_완료_판정(installer_exe, tmp_path, marker, assets, ready, label):
    root = tmp_path / "profile"
    root.mkdir()
    pack_check._seed_dalamud(root, marker=marker, assets=assets)

    done = pack_check.run_check(installer_exe, root)
    assert pack_check.dalamud_ready(done.stdout) is ready, f"{label}\n{done.stdout}"


def test_판정_줄이_없으면_조용히_통과하지_않는다():
    # 라벨이 바뀌면 위 넷이 전부 무의미해진다. 그때 예외로 죽어야 한다.
    with pytest.raises(ValueError):
        pack_check.dalamud_ready("[OK ] profile root  C:\\x")


# ── dalamudConfig ──────────────────────────────────────────────────────────

DEV_DLL = r"C:\p\devPlugins\FF14Accessibility\FF14Accessibility.dll"
ID = "3a0abc23-2f5e-4a55-bbd2-f517f16e51db"


def config(entries: list[dict], locations=None, dev_settings=None, repos=None) -> dict:
    return {
        "DefaultProfile": {"Plugins": {"$values": entries}},
        "DevPluginLoadLocations": {"$values": locations or []},
        "DevPluginSettings": dev_settings or {},
        "ThirdRepoList": {
            "$values": [{"Url": pack_check.KR_REPO_URL, "IsEnabled": True}] if repos is None else repos
        },
    }


def enabled_entry(**overrides) -> dict:
    entry = {"InternalName": "FF14Accessibility", "WorkingPluginId": ID, "IsEnabled": True}
    entry.update(overrides)
    return entry


def test_정상_설정은_통과한다():
    assert pack_check.config_problems(config([enabled_entry()]), ID, DEV_DLL) == []


def test_저장소가_등록_안_되면_잡는다():
    # 매니페스트가 가리키는 저장소가 설정에 없으면 그게 고아다. 오류 없이 안 뜬다.
    problems = pack_check.config_problems(config([enabled_entry()], repos=[]), ID, DEV_DLL)
    assert any("저장소" in p for p in problems)


def test_등록은_됐는데_꺼져_있으면_잡는다():
    disabled = [{"Url": pack_check.KR_REPO_URL, "IsEnabled": False}]
    problems = pack_check.config_problems(config([enabled_entry()], repos=disabled), ID, DEV_DLL)
    assert any("저장소" in p for p in problems)


def test_꺼져_있으면_잡는다():
    problems = pack_check.config_problems(config([enabled_entry(IsEnabled=False)]), ID, DEV_DLL)
    assert any("꺼져" in p for p in problems)


def test_신원이_갈리면_잡는다():
    entry = enabled_entry(WorkingPluginId="99999999-9999-9999-9999-999999999999")
    problems = pack_check.config_problems(config([entry]), ID, DEV_DLL)
    assert any("WorkingPluginId" in p for p in problems)


def test_dev_적재_경로가_남으면_잡는다():
    cfg = config([enabled_entry()], locations=[{"Path": DEV_DLL, "IsEnabled": True}])
    problems = pack_check.config_problems(cfg, ID, DEV_DLL)
    assert any("두 번 적재" in p for p in problems)


def test_dev_설정_항목이_남으면_잡는다():
    cfg = config([enabled_entry()], dev_settings={DEV_DLL: {"StartOnBoot": True}})
    problems = pack_check.config_problems(cfg, ID, DEV_DLL)
    assert any("DevPluginSettings" in p for p in problems)


def test_항목이_둘이면_잡는다():
    cfg = config([enabled_entry(), enabled_entry()])
    assert any("하나여야" in p for p in pack_check.config_problems(cfg, ID, DEV_DLL))


# ── 받는 폴더에 무엇이 있나 ────────────────────────────────────────────────
#
# 설치를 시작하려면 읽어야 하는 문서를 정작 받는 사람이 못 갖고 있었다
# (2026-08-19). exe와 zip만 나가고 안내는 저장소에만 있었다.


def make_dist(tmp_path, *, doc=True, manifests=True, notes=True):
    """받는 사람에게 그대로 주는 루트 셋 + 기계가 읽는 `release/` 셋."""
    (tmp_path / "FF14Accessibility.zip").write_bytes(b"")
    (tmp_path / "FF14AccessibilityInstaller-KR.exe").write_bytes(b"")
    if doc:
        (tmp_path / pack_check.GUIDE_NAME).write_text("안내", encoding="utf-8")

    release = tmp_path / pack_check.RELEASE_DIR_NAME
    release.mkdir(exist_ok=True)
    if manifests:
        for name in pack_check.RELEASE_MANIFESTS:
            (release / name).write_text("{}", encoding="utf-8")
        (release / pack_check.SETUP_ZIP_NAME).write_bytes(b"")
    if notes:
        (release / pack_check.RELEASE_NOTES_NAME).write_text("판", encoding="utf-8")
    return tmp_path


def test_안내_문서가_배포물로_센다(tmp_path):
    """있다고 "배포물이 아닌 것"으로 잡히면 안 된다."""
    problems = pack_check.dist_layout_problems(make_dist(tmp_path))
    assert problems == []


def test_안내_문서가_빠지면_잡는다(tmp_path):
    problems = pack_check.dist_layout_problems(make_dist(tmp_path, doc=False))
    assert any(pack_check.GUIDE_NAME in p for p in problems)


def test_모르는_파일은_여전히_잡는다(tmp_path):
    dist = make_dist(tmp_path)
    (dist / "내_설정.json").write_text("{}", encoding="utf-8")
    problems = pack_check.dist_layout_problems(dist)
    assert any("내_설정.json" in p for p in problems)


def test_릴리스_매니페스트가_빠지면_잡는다(tmp_path):
    """릴리스에 이 둘이 안 올라가면 자기 갱신과 커스텀 저장소가 통째로 죽는다.

    그런데 받는 쪽은 그걸 오류가 아니라 "새 판이 없다"로 읽는다 - 설치
    프로그램은 `installer.json`이 없으면 안내 한 줄만 남기고 넘어간다.
    나갈 자리에 있나를 여기서 못박는다.
    """
    problems = pack_check.dist_layout_problems(make_dist(tmp_path, manifests=False))
    for name in pack_check.RELEASE_MANIFESTS:
        assert any(name in p for p in problems), (name, problems)


def test_릴리스_매니페스트는_배포물로_센다(tmp_path):
    """있다고 "배포물이 아닌 것"으로 잡히면 패킹이 매번 걸린다."""
    assert pack_check.dist_layout_problems(make_dist(tmp_path)) == []


# ── 루트는 사용자 것, release는 기계 것 ────────────────────────────────────
#
# 사용 안내가 "셋을 같은 폴더에 두고 실행합니다"라고 말하는 그 폴더가 dist
# 루트다. 거기에 사람이 안 여는 파일이 섞이면 무엇을 눌러야 하는지 헷갈린다.


def test_루트에_기계용_파일이_섞이면_잡는다(tmp_path):
    dist = make_dist(tmp_path)
    (dist / "repo.json").write_text("{}", encoding="utf-8")
    problems = pack_check.dist_layout_problems(dist)
    assert any("repo.json" in p for p in problems)


def test_release_폴더가_있다고_잡지_않는다(tmp_path):
    """하위 폴더를 "배포물이 아닌 것"으로 세면 패킹이 매번 걸린다."""
    assert pack_check.dist_layout_problems(make_dist(tmp_path)) == []


def test_release_폴더가_통째로_없으면_잡는다(tmp_path):
    dist = make_dist(tmp_path)
    shutil.rmtree(dist / pack_check.RELEASE_DIR_NAME)
    problems = pack_check.dist_layout_problems(dist)
    assert any(pack_check.RELEASE_DIR_NAME in p for p in problems)


def test_릴리스_노트는_있어도_되고_없어도_된다(tmp_path):
    """판마다 사람이 쓰는 것이라 여기서 요구하지 않는다.

    `run\\pack.bat`은 노트를 쓰기 전에 도니까, 여기서 요구하면 그냥 빌드만
    하려던 사람이 매번 걸린다. 없으면 낼 수 없다는 것은 `run\\release.bat`이
    못박는다 - 거기가 맞는 자리다.
    """
    assert pack_check.dist_layout_problems(make_dist(tmp_path, notes=False)) == []
    assert pack_check.dist_layout_problems(make_dist(tmp_path, notes=True)) == []


def test_사용자용_아카이브가_빠지면_잡는다(tmp_path):
    """받는 사람이 실제로 받는 것이다. 이게 없으면 릴리스에 올릴 것이 없다."""
    dist = make_dist(tmp_path)
    (dist / pack_check.RELEASE_DIR_NAME / pack_check.SETUP_ZIP_NAME).unlink()
    problems = pack_check.dist_layout_problems(dist)
    assert any(pack_check.SETUP_ZIP_NAME in p for p in problems)


def test_release_폴더에_모르는_것이_있으면_잡는다(tmp_path):
    dist = make_dist(tmp_path)
    (dist / pack_check.RELEASE_DIR_NAME / "메모.txt").write_text("x", encoding="utf-8")
    problems = pack_check.dist_layout_problems(dist)
    assert any("메모.txt" in p for p in problems)
