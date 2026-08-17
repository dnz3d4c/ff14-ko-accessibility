"""패치 정합성 검사기 테스트.

순수 로직(순서·개수 판정)은 저장소 없이 검사하고, 실제 적용 검사는 vendor
클론이 있을 때만 돌린다. 클론이 없는 머신에서 빨간불이 뜨면 아무도 안 본다.
"""

from pathlib import Path

import patch_check
import pytest


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
