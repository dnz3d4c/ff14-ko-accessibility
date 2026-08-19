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

import pack_check

VERSION = "5.87.0.0"


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
        "InstalledFromUrl": "OFFICIAL",
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


# ── dalamudConfig ──────────────────────────────────────────────────────────

DEV_DLL = r"C:\p\devPlugins\FF14Accessibility\FF14Accessibility.dll"
ID = "3a0abc23-2f5e-4a55-bbd2-f517f16e51db"


def config(entries: list[dict], locations=None, dev_settings=None) -> dict:
    return {
        "DefaultProfile": {"Plugins": {"$values": entries}},
        "DevPluginLoadLocations": {"$values": locations or []},
        "DevPluginSettings": dev_settings or {},
    }


def enabled_entry(**overrides) -> dict:
    entry = {"InternalName": "FF14Accessibility", "WorkingPluginId": ID, "IsEnabled": True}
    entry.update(overrides)
    return entry


def test_정상_설정은_통과한다():
    assert pack_check.config_problems(config([enabled_entry()]), ID, DEV_DLL) == []


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


def make_dist(tmp_path, *, doc=True):
    (tmp_path / "FF14Accessibility.zip").write_bytes(b"")
    (tmp_path / "FF14AccessibilityInstaller-KR.exe").write_bytes(b"")
    if doc:
        (tmp_path / pack_check.GUIDE_NAME).write_text("안내", encoding="utf-8")
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
