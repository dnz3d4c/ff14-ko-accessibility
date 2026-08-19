"""vendor 세우기 테스트.

`git clone --recurse-submodules`가 만드는 상태(detached HEAD, 로컬 kr-port
없음)를 로컬 미러·슈퍼프로젝트로 **실제로 재현**해서 검사한다. 배선 확인만으로는
완료가 아니다 - 이 결함 자체가 갓 클론 실증에서 나왔다.
"""

import json
import subprocess
from pathlib import Path

import pytest
import vendor_setup


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


def _branch(vendor: Path) -> str:
    """현재 브랜치. detached면 빈 문자열."""
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "-q", "HEAD"],
        cwd=vendor,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _world(tmp_path: Path) -> tuple[Path, Path, Path]:
    """업스트림·미러·슈퍼프로젝트를 만든다. (super, src, mirror)를 돌려준다.

    src가 업스트림 흉내(main + kr-port), mirror는 그 bare 클론,
    슈퍼프로젝트는 mirror를 gitlink으로 기록한다 - 우리 저장소의 실제 배선이다.
    """
    src = tmp_path / "src"
    src.mkdir()
    _run("init", "-b", "main", cwd=src)
    _run("config", "user.email", "t@example.invalid", cwd=src)
    _run("config", "user.name", "t", cwd=src)
    (src / "a.txt").write_text("업스트림\n", encoding="utf-8")
    _run("add", "a.txt", cwd=src)
    _run("commit", "-m", "upstream: base", cwd=src)
    base = _out("rev-parse", "HEAD", cwd=src)
    _run("checkout", "-b", "kr-port", cwd=src)
    (src / "a.txt").write_text("우리 것\n", encoding="utf-8")
    _run("commit", "-am", "ours", cwd=src)

    # HEAD가 kr-port인 채로 bare를 뜨면 미러의 HEAD도 kr-port다.
    mirror = tmp_path / "mirror.git"
    _run("clone", "--bare", str(src), str(mirror), cwd=tmp_path)

    super_ = tmp_path / "super"
    super_.mkdir()
    _run("init", "-b", "master", cwd=super_)
    _run("config", "user.email", "t@example.invalid", cwd=super_)
    _run("config", "user.name", "t", cwd=super_)
    (super_ / "upstream.json").write_text(
        json.dumps(
            {"commit": base, "repo": str(src), "synced": "2026-08-19", "tag": "v0.1"}
        ),
        encoding="utf-8",
    )
    _run("add", "upstream.json", cwd=super_)
    _run(
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(mirror),
        "vendor/ff14-accessibility",
        cwd=super_,
    )
    _run("commit", "-m", "gitlink", cwd=super_)
    return super_, src, mirror


def _fresh(tmp_path: Path, super_: Path, recurse: bool = True) -> Path:
    """슈퍼프로젝트를 실제로 클론한다. 결함이 나온 그 경로다.

    file 클론은 https 클론과 달리 로컬 kr-port 브랜치가 생긴 채로 온다
    (체크아웃은 똑같이 detached). 실측(github 클론)의 "브랜치 자체가 없음"
    상태는 각 테스트가 `branch -D`로 만든다 - 둘 다 실존하는 상태라 둘 다
    검사한다.
    """
    fresh = tmp_path / ("fresh-r" if recurse else "fresh")
    args = ["clone", "--recurse-submodules"] if recurse else ["clone"]
    _run(
        "-c",
        "protocol.file.allow=always",
        *args,
        str(super_),
        str(fresh),
        cwd=tmp_path,
    )
    return fresh


def _allow_file_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """setup 안의 submodule update가 file:// 미러를 받을 수 있게 한다.

    로컬 repo config로는 안 된다 - 클론은 새 저장소를 만드는 명령이라
    슈퍼프로젝트의 config를 읽지 않는다. 실사용(https)에는 필요 없다.
    """
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "protocol.file.allow")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "always")


def _vendor(fresh: Path) -> Path:
    return fresh / "vendor" / "ff14-accessibility"


# --- 갓 클론 ---------------------------------------------------------------


def test_갓_클론은_detached다(tmp_path: Path):
    # 전제 확인. 이게 아니면 아래 테스트들이 다른 것을 검사하게 된다.
    super_, _, _ = _world(tmp_path)
    vendor = _vendor(_fresh(tmp_path, super_))
    assert _branch(vendor) == ""


def test_갓_클론을_세운다(tmp_path: Path):
    super_, src, mirror = _world(tmp_path)
    fresh = _fresh(tmp_path, super_)
    vendor = _vendor(fresh)
    recorded = _out("rev-parse", "HEAD:vendor/ff14-accessibility", cwd=fresh)

    assert vendor_setup.setup(fresh) == 0

    assert _branch(vendor) == "kr-port"
    assert _out("rev-parse", "HEAD", cwd=vendor) == recorded
    assert _out("remote", "get-url", "mirror", cwd=vendor) == str(mirror)
    assert _out("remote", "get-url", "upstream", cwd=vendor) == str(src)


def test_두_번_돌려도_같다(tmp_path: Path):
    # 멱등이어야 build.bat이 매번 불러도 된다.
    super_, _, _ = _world(tmp_path)
    fresh = _fresh(tmp_path, super_)
    vendor = _vendor(fresh)
    assert vendor_setup.setup(fresh) == 0
    tip = _out("rev-parse", "HEAD", cwd=vendor)
    assert vendor_setup.setup(fresh) == 0
    assert _branch(vendor) == "kr-port"
    assert _out("rev-parse", "HEAD", cwd=vendor) == tip


def test_로컬_브랜치가_아예_없어도_기록_자리에_세운다(tmp_path: Path):
    # 실측(github 클론)에서 나온 그 상태다 - detached이고 로컬 kr-port가 없다.
    super_, _, _ = _world(tmp_path)
    fresh = _fresh(tmp_path, super_)
    vendor = _vendor(fresh)
    _run("branch", "-D", "kr-port", cwd=vendor)
    recorded = _out("rev-parse", "HEAD:vendor/ff14-accessibility", cwd=fresh)

    assert vendor_setup.setup(fresh) == 0
    assert _branch(vendor) == "kr-port"
    assert _out("rev-parse", "HEAD", cwd=vendor) == recorded


def test_서브모듈_없이_클론해도_받아_세운다(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # `--recurse-submodules`를 빼먹으면 vendor가 빈 디렉토리다.
    super_, _, _ = _world(tmp_path)
    fresh = _fresh(tmp_path, super_, recurse=False)
    vendor = _vendor(fresh)
    assert not (vendor / ".git").exists()

    _allow_file_transport(monkeypatch)
    assert vendor_setup.setup(fresh) == 0
    assert _branch(vendor) == "kr-port"


# --- 손대면 안 되는 상태 ----------------------------------------------------


def test_다른_브랜치면_손대지_않는다(tmp_path: Path):
    # 사용자가 딴 브랜치에서 작업 중일 수 있다. 도구가 덮으면 안 된다.
    super_, _, _ = _world(tmp_path)
    fresh = _fresh(tmp_path, super_)
    vendor = _vendor(fresh)
    _run("checkout", "-b", "main", cwd=vendor)

    assert vendor_setup.setup(fresh) == 1
    assert _branch(vendor) == "main"


def test_기록_너머의_커밋에_떠_있으면_막는다(tmp_path: Path):
    # detached에서 커밋을 얹은 상태. 브랜치를 세우면 그 작업이 가려진다.
    super_, _, _ = _world(tmp_path)
    fresh = _fresh(tmp_path, super_)
    vendor = _vendor(fresh)
    _run("branch", "-D", "kr-port", cwd=vendor)
    _run("config", "user.email", "t@example.invalid", cwd=vendor)
    _run("config", "user.name", "t", cwd=vendor)
    (vendor / "b.txt").write_text("떠서 한 작업\n", encoding="utf-8")
    _run("add", "b.txt", cwd=vendor)
    _run("commit", "-m", "detached work", cwd=vendor)
    stray = _out("rev-parse", "HEAD", cwd=vendor)

    assert vendor_setup.setup(fresh) == 1
    assert _branch(vendor) == ""
    assert _out("rev-parse", "HEAD", cwd=vendor) == stray


def test_기록_뒤에_떠_있으면_기록_자리로_세운다(tmp_path: Path):
    # gitlink만 새로 받고 submodule update를 안 한 모양. 떠 있는 자리가
    # 기록의 조상이면 잃을 작업이 없으니 기록 자리에 세운다.
    super_, _, _ = _world(tmp_path)
    fresh = _fresh(tmp_path, super_)
    vendor = _vendor(fresh)
    recorded = _out("rev-parse", "HEAD:vendor/ff14-accessibility", cwd=fresh)
    _run("checkout", "--detach", f"{recorded}~1", cwd=vendor)
    _run("branch", "-D", "kr-port", cwd=vendor)

    assert vendor_setup.setup(fresh) == 0
    assert _branch(vendor) == "kr-port"
    assert _out("rev-parse", "HEAD", cwd=vendor) == recorded
