"""패치 묶음이 아직 성립하는지 검사한다.

이 저장소의 소스 변경은 전부 `vendor/` 클론의 `kr-port` 브랜치에 있고, 우리
저장소에는 **패치 파일로만** 남는다. `vendor/`는 버전 관리 밖이라, 둘이
어긋나면 우리 저장소에는 아무 증상도 안 나타난다 - 다음에 클론하는 사람이
빌드했을 때 조용히 다른 물건이 나온다.

세 가지를 본다.

1. **개수** - `kr-port`의 커밋 수와 패치 파일 수가 같은가. 다르면 vendor에
   커밋해 놓고 떼어내지 않은 것이다
2. **적용** - 문서에 적힌 순서(`patches/` 먼저, `overlay/patches/` 나중)로
   핀이 가리키는 커밋에 깨끗이 붙는가. 업스트림 태그를 올릴 때 여기가 먼저 깨진다
3. **동등** - 붙인 결과가 `kr-port`와 같은 트리인가. 패치를 뽑은 뒤 vendor에서
   더 손댔으면 여기서 잡힌다

**붙는 자리는 `main`이 아니라 핀(`upstream.json`)이다.** `main`은 클론한
날짜에 따라 다른 커밋을 가리킨다 - 업스트림이 거의 매일 릴리스를 내므로,
어제 클론한 사람과 오늘 클론한 사람의 `main`이 다르고 그러면 이 검사가
서로 다른 것을 검사하게 된다. 그걸 조용히 지나가지 않으려고 핀에 못박는다.
핀을 옮기는 것은 `tools/upstream-sync`다.

`vendor/` 클론이 없으면 검사를 건너뛴다(오류가 아니다). 있는데 깨졌으면 막는다.

사용법:
    uv run --no-project python tools/patch-check/patch_check.py [--quick]

`--quick`은 1번만 본다. 2·3번은 임시 워크트리에 `git am`을 돌리므로 몇 초 걸린다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VENDOR = REPO / "vendor" / "ff14-accessibility"

#: 적용 순서. `patches/`가 먼저다 - 근거는 patches/README.md.
#: 업스트림에 병합되면 앞쪽이 사라지고 뒤쪽은 그대로 붙어야 한다.
PATCH_DIRS = ("patches", "overlay/patches")

#: 우리 패치가 어느 판 위에 얹혀 있는지. tools/upstream-sync가 옮긴다.
PIN = REPO / "upstream.json"

WORK_BRANCH = "kr-port"


def ordered_patches(repo: Path = REPO) -> list[Path]:
    """적용 순서대로 정렬한 패치 파일 목록.

    디렉토리 사이는 `PATCH_DIRS` 순서, 디렉토리 안에서는 이름순이다
    (`git format-patch`가 번호를 앞에 붙이므로 이름순이 곧 번호순).
    """
    found: list[Path] = []
    for name in PATCH_DIRS:
        directory = repo / name
        if directory.is_dir():
            found.extend(sorted(directory.glob("*.patch")))
    return found


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        # 훅을 끈다. 우리 저장소의 core.hooksPath가 새 나가면 am이 죽는다.
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def base_commit(repo: Path = REPO) -> str:
    """패치가 붙는 자리.

    핀이 없으면 `main`으로 물러선다 - 핀을 도입하기 전에 만든 클론에서도
    검사가 죽지 않게 한다. 다만 그때는 클론 시점에 따라 자리가 달라진다.
    """
    pin = repo / "upstream.json"
    if not pin.is_file():
        return "main"
    return json.loads(pin.read_text(encoding="utf-8"))["commit"]


def vendor_present(vendor: Path = VENDOR) -> bool:
    return (vendor / ".git").exists()


def vendor_commit_count(vendor: Path = VENDOR, base: str | None = None) -> int:
    """핀에서 `kr-port`까지의 커밋 수."""
    base = base or base_commit()
    result = _git("rev-list", "--count", f"{base}..{WORK_BRANCH}", cwd=vendor)
    if result.returncode != 0:
        raise RuntimeError(
            f"핀({base[:7]})에서 kr-port까지를 셀 수 없다: {result.stderr.strip()}\n"
            "  핀이 가리키는 커밋이 vendor에 없으면 받아온다: "
            "cd vendor/ff14-accessibility && git fetch --tags origin"
        )
    return int(result.stdout.strip())


def vendor_dirty(vendor: Path = VENDOR) -> list[str]:
    """커밋되지 않은 변경 목록. 우리 저장소에서는 안 보이는 작업이다."""
    result = _git("status", "--porcelain", cwd=vendor)
    return [line for line in result.stdout.splitlines() if line.strip()]


def check_counts(patches: list[Path], commits: int) -> list[str]:
    """개수 검사. 문제 목록을 돌려준다 - 비면 통과."""
    if len(patches) == commits:
        return []
    return [
        f"vendor의 kr-port 커밋은 {commits}건인데 패치 파일은 {len(patches)}개다. "
        "vendor에 커밋하고 떼어내지 않았으면 "
        "`git format-patch`로 뽑아 patches/ 또는 overlay/patches/에 넣어라"
    ]


def check_applies_and_matches(
    patches: list[Path], vendor: Path = VENDOR, base: str | None = None
) -> list[str]:
    """임시 워크트리에서 실제로 붙여 보고 결과 트리를 비교한다."""
    if not patches:
        return []

    base = base or base_commit()
    problems: list[str] = []
    workdir = Path(tempfile.mkdtemp(prefix="patch-check-"))
    tree = workdir / "tree"
    try:
        added = _git("worktree", "add", "--detach", str(tree), base, cwd=vendor)
        if added.returncode != 0:
            return [f"임시 워크트리를 못 만들었다: {added.stderr.strip()}"]

        applied = _git("am", *(str(p) for p in patches), cwd=tree)
        if applied.returncode != 0:
            # 붙이다 만 상태를 남기지 않는다 - 워크트리를 지우기 전에 중단한다.
            _git("am", "--abort", cwd=tree)
            failing = _first_failing(applied.stdout)
            problems.append(
                f"패치가 핀({base[:7]})에 붙지 않는다"
                + (f" (처음 실패: {failing})" if failing else "")
                + ". 업스트림이 움직였으면 여기가 먼저 깨진다 - "
                "patches/README.md의 순서대로 손으로 붙여 충돌을 본다"
            )
            return problems

        got = _git("rev-parse", "HEAD^{tree}", cwd=tree).stdout.strip()
        want = _git("rev-parse", f"{WORK_BRANCH}^{{tree}}", cwd=vendor).stdout.strip()
        if got != want:
            problems.append(
                "패치를 다 붙인 결과가 kr-port와 다르다. "
                "패치를 뽑은 뒤 vendor에서 더 손댔을 가능성이 높다 - "
                "그 변경을 커밋하고 패치를 다시 뽑아라"
            )
    finally:
        _git("worktree", "remove", "--force", str(tree), cwd=vendor)
        shutil.rmtree(workdir, ignore_errors=True)

    return problems


def _first_failing(am_output: str) -> str | None:
    """`git am` 출력에서 마지막으로 시도한 패치 제목을 뽑는다."""
    tried = [
        line[len("Applying: ") :].strip()
        for line in am_output.splitlines()
        if line.startswith("Applying: ")
    ]
    return tried[-1] if tried else None


def main(argv: list[str]) -> int:
    quick = "--quick" in argv

    if not vendor_present():
        print("vendor 클론이 없다 - 패치 검사를 건너뛴다.")
        return 0

    base = base_commit()
    print(f"붙는 자리: {base[:7]} (upstream.json)")
    patches = ordered_patches()
    print(f"패치 {len(patches)}개:")
    for path in patches:
        print(f"  {path.relative_to(REPO).as_posix()}")

    problems = check_counts(patches, vendor_commit_count())

    dirty = vendor_dirty()
    if dirty:
        print(f"\n주의: vendor에 커밋되지 않은 변경 {len(dirty)}건이 있다.")
        print("우리 저장소에서는 안 보이는 작업이다. 커밋하고 패치를 뽑아라.")
        for line in dirty[:10]:
            print(f"  {line}")

    if not quick:
        problems += check_applies_and_matches(patches)

    if problems:
        print("\n패치 묶음이 깨졌다:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print("\n통과" + (" (개수만 봤다)" if quick else " - 순서대로 붙고 kr-port와 같다"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
