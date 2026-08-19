"""저장소가 기록한 vendor 자리(gitlink)가 성립하는지 검사한다.

이 저장소의 소스 변경은 전부 `vendor/` 클론의 `kr-port` 브랜치에 있고, 우리
저장소는 그 팁을 gitlink(서브모듈 항목)으로 기록한다. **원본은 `kr-port`
하나다** - 전에는 패치 파일이 두 번째 원본이라 이 도구가 "패치와 `kr-port`가
어긋났는가"를 붙여 보며 검사했지만, 원본이 하나가 된 지금 그 사고는 존재하지
않는다. 대신 **기록이 실물을 가리키는가**를 본다.

세 가지를 본다.

1. **기록** - 저장소의 gitlink이 vendor의 `kr-port` 팁과 같은가. vendor에
   커밋해 놓고 `git add vendor/ff14-accessibility`를 안 하면 여기서 잡힌다 -
   안 잡으면 다음에 클론하는 사람이 조용히 옛 물건을 받는다
2. **핀** - 핀(`upstream.json`)이 가리키는 업스트림 커밋이 기록된 이력의
   조상인가. 핀만 옮기고 kr-port를 다시 얹지 않았거나 핀을 손으로 고치면
   잡힌다 - 핀은 tools/upstream-sync가 옮긴다
3. **작업 트리** - vendor에 커밋되지 않은 변경이 있는가. 작업 중일 수
   있으므로 경고만 한다

gitlink은 **스테이징(index)을 먼저** 읽고 없으면 HEAD로 물러선다. `git add`를
막 마친 커밋 직전 상태에서 HEAD를 먼저 보면, 방금 옮긴 기록을 어긋났다고 잡는다.

vendor가 아직 안 받아졌으면(빈 디렉토리) 검사를 건너뛴다(오류가 아니다).
받다 말았으면 막는다. 서브모듈로 받으면 `.git`이 디렉토리가 아니라 **파일**이라,
`.git`의 존재만 봐서는 두 상태를 못 가른다.

사용법:
    uv run --no-project python tools/patch-check/patch_check.py [--quick]

`--quick`은 이제 전체와 같다 - 전부 순간에 끝나는 git 조회다. 부르는 자리
(`.githooks/pre-commit`, `run\\check.bat`)를 안 바꾸려고 받기만 한다.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VENDOR = REPO / "vendor" / "ff14-accessibility"

#: 저장소가 vendor를 기록하는 자리. `git add`가 옮기는 그 경로다.
GITLINK = "vendor/ff14-accessibility"

WORK_BRANCH = "kr-port"

#: 기록이나 핀이 가리키는 커밋이 vendor에 없을 때의 안내. 원격 이름이 클론
#: 방법에 따라 다르므로(전체 클론은 mirror, 서브모듈은 origin) 전부 받는다.
_FETCH = "cd vendor/ff14-accessibility && git fetch --all --tags"

#: 갓 클론한 vendor를 작업 가능하게 세우는 도구. 손으로 세우게 하지 않는다.
_SETUP = "uv run --no-project python tools/kr-setup/vendor_setup.py"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def vendor_state(vendor: Path = VENDOR) -> str:
    """vendor가 어떤 상태인지: "ok" | "absent" | "broken".

    absent(안 받아짐)는 건너뛸 일이고 broken(받다 맒)은 막을 일이라 갈라야
    한다. 서브모듈로 받으면 `.git`이 파일이고 전체 클론이면 디렉토리다 -
    형태가 아니라 **git이 실제로 응답하는지**로 본다.
    """
    if not vendor.is_dir():
        return "absent"
    entries = [path.name for path in vendor.iterdir()]
    if not entries:
        return "absent"
    if not (vendor / ".git").exists() or entries == [".git"]:
        return "broken"
    if _git("rev-parse", "--git-dir", cwd=vendor).returncode != 0:
        # `.git` 파일이 가리키는 곳이 사라진 경우. 존재 검사는 통과한다.
        return "broken"
    return "ok"


def gitlink_commit(repo: Path = REPO) -> str | None:
    """저장소가 기록한 vendor 자리. 스테이징 먼저, 없으면 HEAD, 그마저 없으면 None."""
    for ref in (f":{GITLINK}", f"HEAD:{GITLINK}"):
        result = _git("rev-parse", ref, cwd=repo)
        if result.returncode == 0:
            return result.stdout.strip()
    return None


def base_commit(repo: Path = REPO) -> str | None:
    """핀(`upstream.json`)이 가리키는 업스트림 커밋. 핀이 없으면 None.

    우리 커밋이 어느 업스트림 판 위에 얹혀 있는지다. tools/upstream-sync가 옮긴다.
    """
    pin = repo / "upstream.json"
    if not pin.is_file():
        return None
    return str(json.loads(pin.read_text(encoding="utf-8"))["commit"])


def vendor_dirty(vendor: Path = VENDOR) -> list[str]:
    """커밋되지 않은 변경 목록. 우리 저장소에서는 안 보이는 작업이다."""
    result = _git("status", "--porcelain", cwd=vendor)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _exists(sha: str, vendor: Path) -> bool:
    return _git("cat-file", "-e", f"{sha}^{{commit}}", cwd=vendor).returncode == 0


def _count(base: str, tip: str, vendor: Path) -> int:
    result = _git("rev-list", "--count", f"{base}..{tip}", cwd=vendor)
    return int(result.stdout.strip() or 0)


def check_recorded(recorded: str | None, vendor: Path = VENDOR) -> list[str]:
    """기록 검사. 문제 목록을 돌려준다 - 비면 통과."""
    if recorded is None:
        return [
            "저장소에 vendor 기록(gitlink)이 없다. "
            "`git add vendor/ff14-accessibility`로 기록하고 같이 커밋한다"
        ]
    if not _exists(recorded, vendor):
        return [f"기록된 자리({recorded[:7]})가 vendor에 없다. 받아온다: {_FETCH}"]
    tip = _git("rev-parse", "--verify", "-q", f"refs/heads/{WORK_BRANCH}", cwd=vendor)
    if tip.returncode != 0:
        # 갓 클론: 서브모듈은 gitlink 커밋을 detached로 체크아웃하고 로컬
        # 브랜치를 안 만든다. 받은 것이 기록과 같으면 그 자체는 정상이다 -
        # 작업하려면 브랜치가 필요하다는 안내는 main()이 한다.
        head = _git("rev-parse", "HEAD", cwd=vendor).stdout.strip()
        if head == recorded:
            return []
        return [
            f"vendor에 {WORK_BRANCH} 브랜치가 없고, 떠 있는 자리({head[:7]})가 "
            f"기록({recorded[:7]})과 다르다. 세운다: {_SETUP}"
        ]
    tip_sha = tip.stdout.strip()
    if recorded == tip_sha:
        return []
    ahead = _count(recorded, tip_sha, vendor)
    behind = _count(tip_sha, recorded, vendor)
    if ahead and not behind:
        return [
            f"vendor의 {WORK_BRANCH}가 기록된 자리보다 {ahead}커밋 앞서 있다. "
            "`git add vendor/ff14-accessibility`로 기록을 옮겨 같이 커밋한다"
        ]
    if behind and not ahead:
        return [
            f"기록된 자리가 {WORK_BRANCH}보다 {behind}커밋 앞서 있다. "
            f"{WORK_BRANCH}를 되감았으면 기록도 옮긴다: "
            "`git add vendor/ff14-accessibility`"
        ]
    return [
        f"{WORK_BRANCH}와 기록된 자리가 갈라졌다"
        f"(공통 조상 뒤로 {WORK_BRANCH} {ahead}커밋, 기록 {behind}커밋). "
        f"{WORK_BRANCH}를 다시 얹었으면(rebase) 기록을 옮긴다: "
        "`git add vendor/ff14-accessibility`"
    ]


def check_pin_ancestry(
    pin_commit: str | None, recorded: str | None, vendor: Path = VENDOR
) -> list[str]:
    """핀 검사. 핀이 기록된 이력의 조상인가."""
    if pin_commit is None:
        return ["upstream.json이 없다 - 어느 판 위에 있는지 아무 데도 안 적혀 있다"]
    if recorded is None:
        return []  # 기록 검사가 이미 잡았다. 같은 문제를 두 번 말하지 않는다.
    if not _exists(pin_commit, vendor):
        return [
            f"핀({pin_commit[:7]})이 가리키는 커밋이 vendor에 없다. 받아온다: {_FETCH}"
        ]
    result = _git("merge-base", "--is-ancestor", pin_commit, recorded, cwd=vendor)
    if result.returncode == 0:
        return []
    if result.returncode == 1:
        return [
            f"핀({pin_commit[:7]})이 기록된 {WORK_BRANCH} 이력에 없다. "
            "핀만 옮기고 kr-port를 다시 얹지 않았거나 핀을 손으로 고친 것이다 - "
            "핀은 run\\sync.bat이 옮긴다"
        ]
    return [f"핀 조상 검사가 실패했다: {result.stderr.strip()}"]


def main(argv: list[str]) -> int:
    del argv  # --quick도 전체와 같다. 옛 인터페이스라 받기만 한다.

    state = vendor_state()
    if state == "absent":
        print("vendor가 아직 안 받아졌다 - 기록 검사를 건너뛴다.")
        print("  받기: git submodule update --init")
        return 0
    if state == "broken":
        print(
            "vendor가 받다 말았거나 깨졌다 - 검사도 빌드도 성립하지 않는다.",
            file=sys.stderr,
        )
        print("  다시 받기: git submodule update --init --force", file=sys.stderr)
        return 1

    recorded = gitlink_commit()
    print(f"기록된 자리: {recorded[:7] if recorded else '없음'} (gitlink)")
    pin = base_commit()
    print(f"핀: {pin[:7] if pin else '없음'} (upstream.json)")

    problems = check_recorded(recorded)
    problems += check_pin_ancestry(pin, recorded)

    dirty = vendor_dirty()
    if dirty:
        print(f"\n주의: vendor에 커밋되지 않은 변경 {len(dirty)}건이 있다.")
        print("우리 저장소에서는 안 보이는 작업이다. kr-port에 커밋하고 기록을 옮긴다.")
        for line in dirty[:10]:
            print(f"  {line}")

    if problems:
        print("\nvendor 기록이 어긋났다:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    branchless = (
        _git(
            "rev-parse", "--verify", "-q", f"refs/heads/{WORK_BRANCH}", cwd=VENDOR
        ).returncode
        != 0
    )
    if branchless:
        # 갓 클론 상태. 받은 것은 기록과 일치하니 실패가 아니다.
        print("\nvendor가 브랜치 없이 기록된 자리에 떠 있다(갓 클론 상태).")
        print(f"작업 전에 세운다: {_SETUP}")

    print("\n통과 - 기록이 kr-port 팁이고 핀이 그 이력의 조상이다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
