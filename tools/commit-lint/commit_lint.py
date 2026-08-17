"""커밋 메시지 검사기.

문체를 단속하려는 게 아니다. 이 저장소의 변경은 두 갈래다 - 원래 플러그인
만든 사람한테 보낼 수 있는 것(`[업스트림]`)과 우리만 쓰는 것(`[한국전용]`).
둘이 한 커밋에 섞이면 나중에 보낼 것만 떼어낼 수가 없고, 그때 남는 방법은
이력을 다시 쓰는 것뿐이다. 그 사고를 커밋할 때 막는다.

규칙과 근거: docs/commit-rules.md
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: 제목 앞에 붙일 수 있는 말. docs/commit-rules.md 표와 같아야 한다.
AREAS = ("업스트림", "한국전용", "검증", "문서", "벤더", "도구")

#: 갈래별로 건드리면 안 되는 경로. 걸리면 커밋을 쪼개라는 뜻이다.
FORBIDDEN_PATHS = {
    "업스트림": ("overlay/",),
    "한국전용": ("patches/",),
}

#: `[업스트림]` 커밋에 반드시 있어야 하는 줄.
REQUIRED_UPSTREAM_TRAILERS = ("Upstream-Files", "Upstream-Subject")

#: 현황판을 같이 고쳐야 하는 갈래. 코드나 설비가 움직이는 쪽만이다.
#: `[문서]`와 `[벤더]`는 뺀다 - 근거 문서를 고치거나 업스트림 포인터를 옮기는
#: 것 자체는 할 일의 이동이 아니다.
BOARD_AREAS = ("업스트림", "한국전용", "검증", "도구")

#: 남은 일은 여기만 보면 된다.
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
    """어긴 것 목록. 비어 있으면 통과."""
    body = strip_comments(message)
    subject = next((line for line in body.splitlines() if line.strip()), "")

    violations: list[Violation] = []
    match = _SUBJECT_RE.match(subject)

    if match is None or match.group("area") not in AREAS:
        violations.append(
            Violation(
                "C1",
                f"제목이 갈래로 시작해야 한다. 쓸 수 있는 것: "
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

    if area == "업스트림":
        missing = [
            key
            for key in REQUIRED_UPSTREAM_TRAILERS
            if not trailer_value(body, key)
        ]
        if missing:
            violations.append(
                Violation(
                    "C5",
                    f"[업스트림] 커밋에 빠진 줄이 있다: {', '.join(missing)}. "
                    "이게 없으면 나중에 보낼 것을 모아 만들 수가 없다",
                )
            )

        upstream_subject = trailer_value(body, "Upstream-Subject")
        if upstream_subject and _UMLAUT_RE.search(upstream_subject):
            violations.append(
                Violation(
                    "C6",
                    "Upstream-Subject의 움라우트를 ae/oe/ue/ss로 바꿔라 "
                    "(원래 저장소 커밋 140/140이 그렇게 쓴다)",
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
                    "섞이면 보낼 것만 떼어낼 수 없다 - 커밋을 쪼개라",
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
    """커밋에 올라간 경로. 못 읽으면 빈 목록(섞임 검사만 건너뛴다)."""
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

    print("커밋 메시지가 규칙에 안 맞는다 (docs/commit-rules.md):", file=sys.stderr)
    for violation in violations:
        print(f"  {violation}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
