"""갓 클론한 vendor를 작업 가능한 상태로 세운다. 멱등이다.

`git clone --recurse-submodules`는 gitlink이 가리키는 커밋을 **detached로**
체크아웃한다 - `.gitmodules`에 `branch = kr-port`를 적어도 로컬 브랜치는 안
만든다. 그 상태로는 빌드 관문에 걸리고 커밋도 못 얹는다. 손으로 세우게 하지
않는다 - 설치기가 대신할 수 있는 일을 안내 문장으로 넘기지 않는 것이 이
저장소의 규칙이라, `run\\build.bat`이 빌드 전에 이 도구를 부른다.

하는 일 (이미 돼 있으면 각각 건너뛴다):

1. vendor가 안 받아져 있으면(빈 디렉토리) `git submodule update --init`
2. 브랜치 없이 떠 있고 그 자리가 기록(gitlink)의 조상이면 - 갓 클론이거나
   gitlink만 새로 받은 모양이다 - `kr-port`를 기록 자리에 세워 체크아웃
3. 원격 정리 - `mirror`(`.gitmodules`의 미러 주소)와 `upstream`
   (`upstream.json`의 업스트림 주소)을 등록한다. origin은 **건드리지 않는다**:
   클론 방식에 따라 미러일 수도(서브모듈) 업스트림일 수도(이 개발 머신) 있고,
   origin을 바꾸면 `git submodule update`의 fetch가 깨진다

kr-port가 아닌 **다른 브랜치**에 있거나, 기록 너머의 커밋에 떠 있으면
아무것도 바꾸지 않고 막는다 - 작업 중인 상태를 도구가 덮으면 안 된다.

사용법:
    uv run --no-project python tools/kr-setup/vendor_setup.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# 상태 판정과 gitlink 읽기는 검사기가 이미 갖고 있다. 두 벌 만들지 않는다.
sys.path.insert(0, str(REPO / "tools" / "patch-check"))
import patch_check  # noqa: E402

WORK_BRANCH = patch_check.WORK_BRANCH
GITLINK = patch_check.GITLINK

#: 업스트림을 가리키는 원격의 push 주소에 넣는 값. git이 이 주소로 밀려다
#: 실패하므로 실수로 남의 저장소에 브랜치를 만드는 일이 막힌다.
NO_PUSH = "no_push"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def _mirror_url(repo: Path) -> str | None:
    """미러 주소. `.gitmodules`가 단일 원천이다."""
    result = _git("config", "-f", ".gitmodules", f"submodule.{GITLINK}.url", cwd=repo)
    return result.stdout.strip() if result.returncode == 0 else None


def _upstream_url(repo: Path) -> str | None:
    """업스트림 주소. `upstream.json`이 단일 원천이다."""
    pin = repo / "upstream.json"
    if not pin.is_file():
        return None
    url = json.loads(pin.read_text(encoding="utf-8")).get("repo")
    return str(url) if url else None


def _ensure_branch(vendor: Path, recorded: str) -> str | None:
    """kr-port를 세운다. 실패하면 이유를 돌려준다 - 성공이면 None."""
    branch = _git("symbolic-ref", "--short", "-q", "HEAD", cwd=vendor).stdout.strip()
    if branch == WORK_BRANCH:
        return None
    if branch:
        return (
            f"vendor가 {branch} 브랜치에 있다. 작업 중일 수 있어 여기서 옮기지 "
            f"않는다 - 확인하고 옮긴다: git -C vendor/ff14-accessibility "
            f"checkout {WORK_BRANCH}"
        )

    head = _git("rev-parse", "HEAD", cwd=vendor).stdout.strip()
    existing = _git(
        "rev-parse", "--verify", "-q", f"refs/heads/{WORK_BRANCH}", cwd=vendor
    ).stdout.strip()

    if existing:
        if existing == head:
            done = _git("checkout", WORK_BRANCH, cwd=vendor)
            if done.returncode != 0:
                return f"{WORK_BRANCH}를 체크아웃하지 못했다: {done.stderr.strip()}"
            print(f"{WORK_BRANCH} 브랜치를 체크아웃했다.")
            return None
        return (
            f"{WORK_BRANCH} 브랜치가 있는데 다른 자리({head[:7]})에 떠 있다. "
            f"확인하고 옮긴다: git -C vendor/ff14-accessibility checkout {WORK_BRANCH}"
        )

    # 떠 있는 자리가 기록의 조상이면(기록 자신 포함) 잃을 작업이 없다.
    ancestor = _git("merge-base", "--is-ancestor", head, recorded, cwd=vendor)
    if ancestor.returncode != 0:
        return (
            f"vendor가 기록({recorded[:7]}) 너머의 커밋({head[:7]})에 떠 있다. "
            "떠서 한 작업이 있으면 브랜치로 붙잡는다: "
            f"git -C vendor/ff14-accessibility checkout -b <이름>"
        )
    made = _git("checkout", "-B", WORK_BRANCH, recorded, cwd=vendor)
    if made.returncode != 0:
        return f"{WORK_BRANCH}를 세우지 못했다: {made.stderr.strip()}"
    print(f"{WORK_BRANCH} 브랜치를 기록된 자리({recorded[:7]})에 세웠다.")
    return None


def _ensure_remote(vendor: Path, name: str, url: str | None) -> str | None:
    """원격을 등록한다. 실패하면 이유를 돌려준다 - 성공이면 None."""
    if url is None:
        return f"원격 {name}의 주소를 못 찾았다 - 등록을 건너뛴다"
    current = _git("remote", "get-url", name, cwd=vendor)
    if current.returncode != 0:
        added = _git("remote", "add", name, url, cwd=vendor)
        if added.returncode != 0:
            return f"원격 {name}을 못 붙였다: {added.stderr.strip()}"
        print(f"원격 {name}을 등록했다: {url}")
    elif current.stdout.strip() != url:
        moved = _git("remote", "set-url", name, url, cwd=vendor)
        if moved.returncode != 0:
            return f"원격 {name}의 주소를 못 고쳤다: {moved.stderr.strip()}"
        print(f"원격 {name}의 주소를 맞췄다: {url}")
    return None


def _seal_upstream_push(vendor: Path) -> list[str]:
    """업스트림을 가리키는 원격의 push 주소를 막는다.

    **우리가 밀 곳은 `mirror` 하나뿐인데 이름만으로는 그게 안 드러난다.**
    `origin`은 클론이 만든 것이고 `upstream`은 우리가 붙인 것이라 둘 다 남의
    공개 저장소를 가리킨다. `git push origin kr-port`를 한 번 잘못 치면 우리
    브랜치가 거기 생기고, 그건 지우기 전까지 남이 본다.

    받기는 그대로 둔다 - 업스트림 따라잡기가 fetch만 쓰고, PR은 fork로 낸다.
    원격 설정은 저장소가 아니라 로컬 `.git/config`에 있어서 클론마다 다시
    해야 하고, 그래서 여기가 그 자리다.
    """
    sealed = []
    mirror = _mirror_url(vendor.parent.parent)

    for name in ("origin", "upstream"):
        url = _git("remote", "get-url", name, cwd=vendor)
        if url.returncode != 0:
            continue  # 그 원격이 없으면 막을 것도 없다.
        if mirror is not None and url.stdout.strip() == mirror:
            continue  # 미러를 가리키는 이름이면 막으면 안 된다.

        pushed = _git("remote", "get-url", "--push", name, cwd=vendor)
        if pushed.stdout.strip() == NO_PUSH:
            continue

        closed = _git("remote", "set-url", "--push", name, NO_PUSH, cwd=vendor)
        if closed.returncode == 0:
            sealed.append(name)
    return sealed


def setup(repo: Path = REPO) -> int:
    """vendor를 세운다. 0이면 작업 가능한 상태다."""
    vendor = repo / "vendor" / "ff14-accessibility"

    state = patch_check.vendor_state(vendor)
    if state == "broken":
        print("vendor가 받다 말았거나 깨졌다 - 다시 받는다:", file=sys.stderr)
        print("  git submodule update --init --force", file=sys.stderr)
        return 1
    if state == "absent":
        print("vendor가 안 받아져 있다 - 받는다.")
        got = _git("submodule", "update", "--init", "--", GITLINK, cwd=repo)
        if got.returncode != 0:
            print(f"못 받았다: {got.stderr.strip()}", file=sys.stderr)
            return 1

    recorded = patch_check.gitlink_commit(repo)
    if recorded is None:
        print(
            "저장소에 vendor 기록(gitlink)이 없다 - 세울 기준이 없다.", file=sys.stderr
        )
        return 1

    problem = _ensure_branch(vendor, recorded)
    if problem is not None:
        print(problem, file=sys.stderr)
        return 1

    for name, url in (("mirror", _mirror_url(repo)), ("upstream", _upstream_url(repo))):
        warning = _ensure_remote(vendor, name, url)
        if warning is not None:
            # 빌드에는 지장이 없어서 막지 않는다. 동기화는 원격이 없으면
            # 자기 단계에서 명확하게 실패한다.
            print(f"주의: {warning}", file=sys.stderr)

    sealed = _seal_upstream_push(vendor)
    if sealed:
        print(f"업스트림으로는 못 밀게 닫았다: {', '.join(sealed)}")

    tip = _git("rev-parse", "HEAD", cwd=vendor).stdout.strip()
    print(f"vendor 준비 완료 - {WORK_BRANCH}({tip[:7]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(setup())
