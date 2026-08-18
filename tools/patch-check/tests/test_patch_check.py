"""패치 정합성 검사기 테스트.

순수 로직(순서·개수 판정)은 저장소 없이 검사하고, 실제 적용 검사는 vendor
클론이 있을 때만 돌린다. 클론이 없는 머신에서 빨간불이 뜨면 아무도 안 본다.
"""

import subprocess
from pathlib import Path

import patch_check
import pytest


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


# --- 적용 순서 ------------------------------------------------------------


def test_patches가_overlay보다_먼저다(tmp_path: Path):
    # 순서가 뒤집히면 업스트림이 받아들인 뒤 우리 패치가 전부 어긋난다.
    (tmp_path / "patches").mkdir()
    (tmp_path / "overlay" / "patches").mkdir(parents=True)
    (tmp_path / "patches" / "0001-up.patch").touch()
    (tmp_path / "overlay" / "patches" / "0001-kr.patch").touch()

    names = [p.name for p in patch_check.ordered_patches(tmp_path)]
    assert names == ["0001-up.patch", "0001-kr.patch"]


def test_같은_디렉토리_안에서는_번호순(tmp_path: Path):
    (tmp_path / "overlay" / "patches").mkdir(parents=True)
    for name in ("0003-c.patch", "0001-a.patch", "0002-b.patch"):
        (tmp_path / "overlay" / "patches" / name).touch()

    names = [p.name for p in patch_check.ordered_patches(tmp_path)]
    assert names == ["0001-a.patch", "0002-b.patch", "0003-c.patch"]


def test_없는_디렉토리는_건너뛴다(tmp_path: Path):
    assert patch_check.ordered_patches(tmp_path) == []


def test_patch가_아닌_파일은_안_센다(tmp_path: Path):
    (tmp_path / "patches").mkdir()
    (tmp_path / "patches" / "README.md").touch()
    (tmp_path / "patches" / "0001-x.patch").touch()

    names = [p.name for p in patch_check.ordered_patches(tmp_path)]
    assert names == ["0001-x.patch"]


# --- 붙는 자리 ------------------------------------------------------------


def test_핀이_붙는_자리를_정한다(tmp_path: Path):
    # `main`은 클론한 날짜에 따라 다른 커밋이다. 핀이 그걸 못박는다.
    (tmp_path / "upstream.json").write_text(
        '{"commit": "abc1234", "tag": "v5.85"}', encoding="utf-8"
    )
    assert patch_check.base_commit(tmp_path) == "abc1234"


def test_핀이_없으면_main으로_물러선다(tmp_path: Path):
    # 핀을 도입하기 전에 만든 클론에서도 검사가 죽지 않아야 한다.
    assert patch_check.base_commit(tmp_path) == "main"


def test_이_저장소의_핀이_커밋을_가리킨다():
    base = patch_check.base_commit()
    assert base != "main", "upstream.json이 있어야 한다"
    assert len(base) == 40, "짧은 sha는 다른 커밋과 겹칠 수 있다"


# --- 개수 판정 ------------------------------------------------------------


def test_개수가_같으면_통과():
    assert patch_check.check_counts([Path("a.patch")], 1) == []


def test_커밋이_더_많으면_거부():
    # vendor에 커밋해 놓고 떼어내지 않은 경우. 우리 저장소에는 증상이 없다.
    problems = patch_check.check_counts([Path("a.patch")], 3)
    assert len(problems) == 1
    assert "3" in problems[0] and "1" in problems[0]


def test_패치가_더_많으면_거부():
    # 패치를 남겨 둔 채 vendor 브랜치를 되감은 경우.
    assert patch_check.check_counts([Path("a.patch"), Path("b.patch")], 1)


def test_둘_다_없으면_통과():
    assert patch_check.check_counts([], 0) == []


# --- 실제 저장소 ----------------------------------------------------------

needs_vendor = pytest.mark.skipif(
    not patch_check.vendor_present(), reason="vendor 클론이 없다"
)


@needs_vendor
def test_이_저장소의_개수가_맞는다():
    patches = patch_check.ordered_patches()
    assert patch_check.check_counts(patches, patch_check.vendor_commit_count()) == []


@needs_vendor
def test_이_저장소의_패치가_순서대로_붙고_kr_port와_같다():
    # docs가 적어 둔 적용 명령이 실제로 성립하는지. 업스트림 태그를 올릴 때
    # 여기가 먼저 깨지므로 이게 조기 경보다.
    assert patch_check.check_applies_and_matches(patch_check.ordered_patches()) == []


# --- 업스트림이 문맥을 건드렸을 때 ----------------------------------------
#
# 이게 이 프로젝트에서 실제로 일어나는 일이다. 업스트림은 8일에 릴리스를 7개
# 내고, 우리 패치가 고치는 줄 바로 옆에 새 문장을 끼워 넣는다. 그러면 패치에
# 딸려 있는 문맥 세 줄이 안 맞는다.
#
# 3-way 없이 붙이면 hunk 하나가 어긋나는 순간 시리즈 전체가 죽고, 어디까지
# 멀쩡했는지도 안 남는다. 원본 blob이 저장소에 있으므로 3-way면 합쳐진다.


def _out(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return result.stdout.strip()


def _lines(*changes: tuple[int, str]) -> str:
    """1~10번 줄짜리 파일. `changes`로 지정한 줄만 바꾼다."""
    rows = [f"line {i}" for i in range(1, 11)]
    for number, text in changes:
        rows[number - 1] = text
    return "\n".join(rows) + "\n"


def _drifted(root: Path) -> tuple[Path, list[Path], str]:
    """우리가 고친 줄의 문맥을 업스트림이 건드린 저장소.

    돌려주는 것은 (vendor, 패치 목록, 붙는 자리)다.
    """
    vendor = root / "vendor"
    vendor.mkdir()
    _run("init", "-b", "main", cwd=vendor)
    _run("config", "user.email", "t@example.invalid", cwd=vendor)
    _run("config", "user.name", "t", cwd=vendor)

    target = vendor / "a.txt"

    # 패치를 뽑은 시점의 업스트림.
    target.write_text(_lines(), encoding="utf-8")
    _run("add", "a.txt", cwd=vendor)
    _run("commit", "-m", "upstream: base", cwd=vendor)
    old_base = _out("rev-parse", "HEAD", cwd=vendor)

    # 우리 변경 - 5번 줄. 문맥으로 2~4번과 6~8번 줄이 패치에 딸려 간다.
    target.write_text(_lines((5, "line 5 - ours")), encoding="utf-8")
    _run("commit", "-am", "ours: line 5", cwd=vendor)

    outdir = root / "patches"
    _run("format-patch", f"{old_base}..HEAD", "-o", str(outdir), cwd=vendor)
    patches = sorted(outdir.glob("*.patch"))

    # 그 사이 업스트림이 3번과 7번 줄을 고쳤다 - 우리 hunk의 문맥 안이다.
    _run("checkout", "--detach", old_base, cwd=vendor)
    target.write_text(
        _lines((3, "line 3 - upstream"), (7, "line 7 - upstream")), encoding="utf-8"
    )
    _run("commit", "-am", "upstream: moved", cwd=vendor)
    new_base = _out("rev-parse", "HEAD", cwd=vendor)
    _run("branch", "-f", "main", new_base, cwd=vendor)

    # 붙인 뒤에 나와야 하는 모양 - 업스트림의 3·7번 줄에 우리 5번 줄.
    _run("checkout", "-B", patch_check.WORK_BRANCH, new_base, cwd=vendor)
    target.write_text(
        _lines(
            (3, "line 3 - upstream"),
            (5, "line 5 - ours"),
            (7, "line 7 - upstream"),
        ),
        encoding="utf-8",
    )
    _run("commit", "-am", "ours: line 5", cwd=vendor)

    return vendor, patches, new_base


def test_문맥이_밀려도_3way로_붙는다(tmp_path: Path):
    vendor, patches, base = _drifted(tmp_path)
    problems = patch_check.check_applies_and_matches(patches, vendor=vendor, base=base)
    assert problems == [], problems


def test_진짜_같은_줄이_충돌하면_그건_잡는다(tmp_path: Path):
    # 3-way가 아무거나 통과시키면 검사기가 죽는다. 같은 줄을 양쪽이 다르게
    # 고친 것은 사람이 봐야 한다.
    vendor, patches, _ = _drifted(tmp_path)
    target = vendor / "a.txt"

    _run("checkout", "--detach", "main", cwd=vendor)
    target.write_text(_lines((5, "line 5 - upstream")), encoding="utf-8")
    _run("commit", "-am", "upstream: took line 5 too", cwd=vendor)
    clash = _out("rev-parse", "HEAD", cwd=vendor)

    problems = patch_check.check_applies_and_matches(patches, vendor=vendor, base=clash)
    assert problems, "같은 줄 충돌은 통과시키면 안 된다"
