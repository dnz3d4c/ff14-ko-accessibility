"""커밋 메시지 검증기.

목적은 문체 단속이 아니라 **기여 가능성 보존**이다. 이 저장소의 변경은 두
종류로 갈린다 - 업스트림에 되돌릴 수 있는 일반화(`[상류]`)와 한국 전용
오버레이(`[오버레이]`). 둘이 한 커밋에 섞이면 나중에 PR로 떼어낼 수 없고,
그때는 이력을 다시 쓰는 것 말고 방법이 없다. 그 사고를 커밋 시점에 막는다.

규칙 원문과 근거: docs/commit-rules.md
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: 제목 접두로 쓸 수 있는 영역. docs/commit-rules.md 와 같은 목록이어야 한다.
AREAS = ("상류", "오버레이", "검증", "문서", "벤더", "도구")

#: 영역별로 건드리면 안 되는 경로. 여기 걸리면 커밋을 쪼개야 한다는 뜻이다.
FORBIDDEN_PATHS = {
    "상류": ("overlay/",),
    "오버레이": ("patches/",),
}

#: `[상류]` 커밋이 반드시 달아야 하는 트레일러.
REQUIRED_UPSTREAM_TRAILERS = ("Upstream-Files", "Upstream-Subject")

#: 현황판을 같이 갱신해야 하는 영역. 코드·설비가 움직이는 쪽만이다.
#: `[문서]`와 `[벤더]`는 뺀다 - 근거 문서를 고치거나 업스트림 포인터를 옮기는
#: 것 자체는 할 일의 이동이 아니다.
BOARD_AREAS = ("상류", "오버레이", "검증", "도구")

#: 남은 일의 단일 원천. 규약은 이 파일의 §9.
BOARD_PATH = "docs/status.md"

#: 현황판을 안 건드리는 이유를 밝히는 트레일러. 값이 비면 면제가 아니다.
BOARD_TRAILER = "Status-Board"

SUBJECT_MAX = 72

_SUBJECT_RE = re.compile(r"^\[(?P<area>[^\]]+)\]\s+(?P<rest>.*)$")
_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)"
    r"(\([^)]*\))?!?:",
    re.IGNORECASE,
)
_SCISSORS_RE = re.compile(r"^#\s*-+\s*>8\s*-+")
_UMLAUT_RE = re.compile(r"[äöüÄÖÜß]")


@dataclass(frozen=True)
class Violation:
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def strip_comments(message: str) -> str:
    """git이 커밋 시 지우는 부분을 미리 지운다.

    가위선(`# ------ >8 ------`) 아래는 diff 미리보기라 검사 대상이 아니다.
    """
    lines: list[str] = []
    for line in message.splitlines():
        if _SCISSORS_RE.match(line):
            break
        if line.startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def trailer_value(message: str, key: str) -> str | None:
    """트레일러 값을 돌려준다. 없으면 None.

    git 관행대로 마지막에 나온 것을 채택한다.
    """
    found: str | None = None
    for line in message.splitlines():
        prefix = f"{key}:"
        if line.startswith(prefix):
            found = line[len(prefix) :].strip()
    return found


def check(message: str, changed_paths: list[str]) -> list[Violation]:
    """위반 목록을 돌려준다. 빈 목록이면 통과."""
    body = strip_comments(message)
    subject = next((line for line in body.splitlines() if line.strip()), "")

    violations: list[Violation] = []
    match = _SUBJECT_RE.match(subject)

    if match is None or match.group("area") not in AREAS:
        violations.append(
            Violation(
                "C1",
                f"제목은 영역 접두로 시작해야 한다. 쓸 수 있는 것: "
                f"{', '.join(f'[{a}]' for a in AREAS)}",
            )
        )
        area = None
        rest = subject
    else:
        area = match.group("area")
        rest = match.group("rest")

    if _CONVENTIONAL_RE.match(subject) or _CONVENTIONAL_RE.match(rest):
        violations.append(
            Violation(
                "C2",
                "feat:/fix: 같은 Conventional Commits 접두는 쓰지 않는다 "
                "(업스트림 이력 140건 전부 미사용)",
            )
        )

    if len(subject) > SUBJECT_MAX:
        violations.append(
            Violation("C3", f"제목이 {len(subject)}자다. {SUBJECT_MAX}자 이하로 줄여라")
        )

    if subject.endswith("."):
        violations.append(Violation("C4", "제목을 마침표로 끝내지 않는다"))

    if area == "상류":
        missing = [
            key
            for key in REQUIRED_UPSTREAM_TRAILERS
            if not trailer_value(body, key)
        ]
        if missing:
            violations.append(
                Violation(
                    "C5",
                    f"[상류] 커밋에 트레일러가 빠졌다: {', '.join(missing)}. "
                    "이게 없으면 나중에 PR을 기계적으로 조립할 수 없다",
                )
            )

        upstream_subject = trailer_value(body, "Upstream-Subject")
        if upstream_subject and _UMLAUT_RE.search(upstream_subject):
            violations.append(
                Violation(
                    "C6",
                    "Upstream-Subject의 움라우트를 ae/oe/ue/ss로 치환해라 "
                    "(업스트림 커밋 140/140이 치환한다)",
                )
            )

    if area and changed_paths:
        forbidden = FORBIDDEN_PATHS.get(area, ())
        hits = [
            path
            for path in changed_paths
            if any(path.startswith(prefix) for prefix in forbidden)
        ]
        if hits:
            violations.append(
                Violation(
                    "C7",
                    f"[{area}] 커밋이 {', '.join(hits)}를 건드린다. "
                    "영역을 섞으면 업스트림 PR로 떼어낼 수 없다 - 커밋을 쪼개라",
                )
            )

    if area in BOARD_AREAS and changed_paths:
        touched_board = BOARD_PATH in changed_paths
        excused = bool(trailer_value(body, BOARD_TRAILER))
        if not touched_board and not excused:
            violations.append(
                Violation(
                    "C8",
                    f"{BOARD_PATH}를 같이 갱신하거나 안 하는 이유를 밝혀라 - "
                    f"예: `{BOARD_TRAILER}: W-01 진행` 또는 "
                    f"`{BOARD_TRAILER}: 해당 없음 - 오타 수정`",
                )
            )

    return violations


def staged_paths(repo_root: Path) -> list[str]:
    """인덱스에 올라간 경로. 읽을 수 없으면 빈 목록(혼합 검사만 건너뛴다)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("사용법: commit_lint.py <커밋메시지파일>", file=sys.stderr)
        return 2

    message = Path(argv[1]).read_text(encoding="utf-8")
    # git은 commit-msg 훅을 워킹트리 최상위에서 실행한다.
    violations = check(message, staged_paths(Path.cwd()))

    if not violations:
        return 0

    print("커밋 메시지 규칙 위반 (docs/commit-rules.md):", file=sys.stderr)
    for violation in violations:
        print(f"  {violation}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
