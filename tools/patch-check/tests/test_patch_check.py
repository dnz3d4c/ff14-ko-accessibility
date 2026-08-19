"""vendor 기록 검사기 테스트.

판정 로직(상태 구분·기록 대조·핀 조상)은 tmp_path에 만든 작은 저장소로
검사하고, 실제 저장소 검사는 vendor가 온전할 때만 돌린다. 클론이 없는
머신에서 빨간불이 뜨면 아무도 안 본다.
"""

import shutil
import stat
import subprocess
from pathlib import Path

import patch_check
import pytest


def _rmtree_git(path: Path) -> None:
    """git 오브젝트는 읽기 전용이라 Windows에서 rmtree가 그대로는 못 지운다."""

    def _retry(func, target, _exc):
        Path(target).chmod(stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onexc=_retry)


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


def _out(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _commit(repo: Path, name: str, text: str) -> str:
    (repo / name).write_text(text, encoding="utf-8")
    _run("add", name, cwd=repo)
    _run("commit", "-m", f"edit {name}", cwd=repo)
    return _out("rev-parse", "HEAD", cwd=repo)


def _vendor(tmp_path: Path) -> tuple[Path, str, str]:
    """base 커밋 위에 kr-port 커밋 둘이 있는 vendor 흉내.

    돌려주는 것은 (vendor, base, tip)이다.
    """
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    _run("init", "-b", "main", cwd=vendor)
    _run("config", "user.email", "t@example.invalid", cwd=vendor)
    _run("config", "user.name", "t", cwd=vendor)
    base = _commit(vendor, "a.txt", "업스트림\n")
    _run("checkout", "-b", patch_check.WORK_BRANCH, cwd=vendor)
    _commit(vendor, "a.txt", "우리 것 1\n")
    tip = _commit(vendor, "a.txt", "우리 것 2\n")
    return vendor, base, tip


# --- vendor 상태 -----------------------------------------------------------
#
# 서브모듈로 받으면 `.git`이 디렉토리가 아니라 **파일**이다. 그리고 안 받아진
# 것(빈 디렉토리)은 건너뛸 일이고, 받다 만 것은 막을 일이라 갈라야 한다.


def test_디렉토리가_없으면_absent(tmp_path: Path):
    assert patch_check.vendor_state(tmp_path / "없다") == "absent"


def test_빈_디렉토리는_absent(tmp_path: Path):
    # 서브모듈 없이 클론하면 git이 빈 디렉토리만 만들어 둔다.
    (tmp_path / "v").mkdir()
    assert patch_check.vendor_state(tmp_path / "v") == "absent"


def test_git만_있으면_broken(tmp_path: Path):
    # 받다 만 클론. 소스가 없으니 검사도 빌드도 성립하지 않는다.
    (tmp_path / "v" / ".git").mkdir(parents=True)
    assert patch_check.vendor_state(tmp_path / "v") == "broken"


def test_소스만_있고_git이_없으면_broken(tmp_path: Path):
    (tmp_path / "v").mkdir()
    (tmp_path / "v" / "a.txt").touch()
    assert patch_check.vendor_state(tmp_path / "v") == "broken"


def test_온전한_클론은_ok(tmp_path: Path):
    vendor, _, _ = _vendor(tmp_path)
    assert patch_check.vendor_state(vendor) == "ok"


def test_서브모듈처럼_git이_파일이어도_ok(tmp_path: Path):
    vendor, _, _ = _vendor(tmp_path)
    clone = tmp_path / "clone"
    gitdir = tmp_path / "gitdir"
    _run(
        "clone",
        "--separate-git-dir",
        str(gitdir),
        str(vendor),
        str(clone),
        cwd=tmp_path,
    )
    assert (clone / ".git").is_file(), "이 형태를 만들려고 separate-git-dir를 썼다"
    assert patch_check.vendor_state(clone) == "ok"


def test_git_파일이_빈_곳을_가리키면_broken(tmp_path: Path):
    # `.git` 존재만 보면 이 상태를 통과시키고 이후 모든 git 명령이 죽는다.
    vendor, _, _ = _vendor(tmp_path)
    clone = tmp_path / "clone"
    gitdir = tmp_path / "gitdir"
    _run(
        "clone",
        "--separate-git-dir",
        str(gitdir),
        str(vendor),
        str(clone),
        cwd=tmp_path,
    )
    _rmtree_git(gitdir)
    assert patch_check.vendor_state(clone) == "broken"


# --- gitlink 읽기 ----------------------------------------------------------


def _parent(tmp_path: Path) -> Path:
    repo = tmp_path / "parent"
    repo.mkdir()
    _run("init", "-b", "master", cwd=repo)
    _run("config", "user.email", "t@example.invalid", cwd=repo)
    _run("config", "user.name", "t", cwd=repo)
    return repo


def _stage_gitlink(repo: Path, sha: str) -> None:
    _run(
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{sha},{patch_check.GITLINK}",
        cwd=repo,
    )


def test_스테이징된_gitlink을_읽는다(tmp_path: Path):
    repo = _parent(tmp_path)
    _stage_gitlink(repo, "1" * 40)
    assert patch_check.gitlink_commit(repo) == "1" * 40


def test_스테이징이_HEAD보다_먼저다(tmp_path: Path):
    # `git add vendor/...`를 막 마친 커밋 직전 상태. HEAD를 먼저 보면
    # 방금 옮긴 기록을 어긋났다고 잡는다.
    repo = _parent(tmp_path)
    _stage_gitlink(repo, "1" * 40)
    _run("commit", "-m", "gitlink", cwd=repo)
    _stage_gitlink(repo, "2" * 40)
    assert patch_check.gitlink_commit(repo) == "2" * 40


def test_기록이_없으면_None(tmp_path: Path):
    repo = _parent(tmp_path)
    assert patch_check.gitlink_commit(repo) is None


# --- 기록 검사 -------------------------------------------------------------


def test_기록이_팁과_같으면_통과(tmp_path: Path):
    vendor, _, tip = _vendor(tmp_path)
    assert patch_check.check_recorded(tip, vendor) == []


def test_kr_port가_앞서_있으면_잡는다(tmp_path: Path):
    # vendor에 커밋해 놓고 git add를 안 한 경우. 제일 흔한 사고다.
    vendor, _, tip = _vendor(tmp_path)
    old = _out("rev-parse", f"{patch_check.WORK_BRANCH}~1", cwd=vendor)
    problems = patch_check.check_recorded(old, vendor)
    assert len(problems) == 1
    assert "1커밋" in problems[0]
    assert "git add vendor/ff14-accessibility" in problems[0]


def test_기록이_앞서_있으면_잡는다(tmp_path: Path):
    # kr-port를 되감은 경우.
    vendor, _, tip = _vendor(tmp_path)
    _run("checkout", "--detach", cwd=vendor)
    _run("branch", "-f", patch_check.WORK_BRANCH, f"{tip}~1", cwd=vendor)
    problems = patch_check.check_recorded(tip, vendor)
    assert len(problems) == 1
    assert "git add vendor/ff14-accessibility" in problems[0]


def test_다시_얹어서_갈라지면_잡는다(tmp_path: Path):
    # rebase 뒤의 모양. 옛 기록은 새 이력에 없다.
    vendor, base, tip = _vendor(tmp_path)
    _run("checkout", "--detach", base, cwd=vendor)
    _commit(vendor, "b.txt", "다시 얹은 것\n")
    _run("branch", "-f", patch_check.WORK_BRANCH, cwd=vendor)
    problems = patch_check.check_recorded(tip, vendor)
    assert len(problems) == 1
    assert "git add vendor/ff14-accessibility" in problems[0]


def test_기록이_vendor에_없으면_받아오라고_한다(tmp_path: Path):
    # 남이 gitlink을 옮겼는데 내 vendor가 낡은 경우.
    vendor, _, _ = _vendor(tmp_path)
    problems = patch_check.check_recorded("deadbeef" * 5, vendor)
    assert len(problems) == 1
    assert "fetch" in problems[0]


def test_기록_자체가_없으면_잡는다(tmp_path: Path):
    vendor, _, _ = _vendor(tmp_path)
    problems = patch_check.check_recorded(None, vendor)
    assert len(problems) == 1
    assert "git add vendor/ff14-accessibility" in problems[0]


# --- 핀 조상 검사 ----------------------------------------------------------


def test_핀이_조상이면_통과(tmp_path: Path):
    vendor, base, tip = _vendor(tmp_path)
    assert patch_check.check_pin_ancestry(base, tip, vendor) == []


def test_핀이_이력_밖이면_잡는다(tmp_path: Path):
    # 핀만 옮기고 kr-port를 다시 얹지 않았거나, 핀을 손으로 고친 경우.
    vendor, base, tip = _vendor(tmp_path)
    _run("checkout", "--detach", base, cwd=vendor)
    stray = _commit(vendor, "c.txt", "다른 줄기\n")
    problems = patch_check.check_pin_ancestry(stray, tip, vendor)
    assert len(problems) == 1


def test_핀_커밋이_vendor에_없으면_받아오라고_한다(tmp_path: Path):
    vendor, _, tip = _vendor(tmp_path)
    problems = patch_check.check_pin_ancestry("deadbeef" * 5, tip, vendor)
    assert len(problems) == 1
    assert "fetch" in problems[0]


def test_핀_파일이_없으면_잡는다(tmp_path: Path):
    vendor, _, tip = _vendor(tmp_path)
    assert patch_check.check_pin_ancestry(None, tip, vendor)


# --- 핀 읽기 ---------------------------------------------------------------


def test_핀이_기준_커밋을_정한다(tmp_path: Path):
    (tmp_path / "upstream.json").write_text(
        '{"commit": "abc1234", "tag": "v5.85"}', encoding="utf-8"
    )
    assert patch_check.base_commit(tmp_path) == "abc1234"


def test_핀이_없으면_None(tmp_path: Path):
    assert patch_check.base_commit(tmp_path) is None


# --- 작업 트리 -------------------------------------------------------------


def test_커밋_안_된_변경을_센다(tmp_path: Path):
    vendor, _, _ = _vendor(tmp_path)
    assert patch_check.vendor_dirty(vendor) == []
    (vendor / "a.txt").write_text("만진다\n", encoding="utf-8")
    assert len(patch_check.vendor_dirty(vendor)) == 1


# --- 실제 저장소 ----------------------------------------------------------

needs_vendor = pytest.mark.skipif(
    patch_check.vendor_state() != "ok", reason="vendor가 없다"
)


def test_이_저장소의_핀이_커밋을_가리킨다():
    base = patch_check.base_commit()
    assert base is not None, "upstream.json이 있어야 한다"
    assert len(base) == 40, "짧은 sha는 다른 커밋과 겹칠 수 있다"


@needs_vendor
def test_이_저장소의_기록이_kr_port_팁이다():
    recorded = patch_check.gitlink_commit()
    assert recorded is not None, "gitlink이 있어야 한다"
    assert patch_check.check_recorded(recorded) == []


@needs_vendor
def test_이_저장소의_핀이_기록의_조상이다():
    problems = patch_check.check_pin_ancestry(
        patch_check.base_commit(), patch_check.gitlink_commit()
    )
    assert problems == []
