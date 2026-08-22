"""커밋 메시지 검사기.

문체를 단속하려는 게 아니다. 이 저장소의 변경은 두 갈래다 - 원래 플러그인
만든 사람한테 보낼 수 있는 것(`[업스트림]`)과 우리만 쓰는 것(`[한국전용]`).
둘이 한 커밋에 섞이면 나중에 보낼 것만 떼어낼 수가 없고, 그때 남는 방법은
이력을 다시 쓰는 것뿐이다. 그 사고를 커밋할 때 막는다.

규칙과 근거: docs/dev/commit-rules.md
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

#: 제목 앞에 붙일 수 있는 말. docs/dev/commit-rules.md 표와 같아야 한다.
AREAS = ("업스트림", "한국전용", "검증", "문서", "벤더", "도구")

#: 갈래별로 건드리면 안 되는 경로. 걸리면 커밋을 쪼개라는 뜻이다.
#: 한국전용 항목이 없는 것은 반대쪽 경계가 경로가 아니게 돼서다 - 업스트림에
#: 보낼 것은 이제 패치 파일이 아니라 vendor(kr-port) 커밋이고, 그쪽은 C11이 본다.
FORBIDDEN_PATHS = {
    "업스트림": ("overlay/",),
}

#: vendor 포인터(gitlink). 우리 저장소는 kr-port 커밋 하나를 이 경로로 가리킨다.
VENDOR_PATH = "vendor/ff14-accessibility"

#: vendor 포인터를 옮겨도 되는 갈래. 나머지 갈래에서 포인터가 움직이면
#: 실수(`git add -A`)다 - vendor가 왜 바뀌었는지 이력에 안 남는다.
VENDOR_AREAS = ("업스트림", "한국전용", "벤더")

#: `[업스트림]` 커밋에 반드시 있어야 하는 줄.
REQUIRED_UPSTREAM_TRAILERS = ("Upstream-Files", "Upstream-Subject")

#: `[벤더]` 커밋에 반드시 있어야 하는 줄. 어디서 어디까지 올렸는지가 없으면
#: 나중에 "이 판에서 뭐가 들어왔나"를 되짚을 수가 없다.
REQUIRED_VENDOR_TRAILERS = ("Upstream-Range",)

#: 핀을 옮기는 파일과, 그때 한국어로 남겨야 하는 이력.
PIN_PATH = "upstream.json"
CHANGES_PATH = "docs/upstream/changes.md"

#: 현황판을 같이 고쳐야 하는 갈래. 코드나 설비가 움직이는 쪽만이다.
#: `[문서]`와 `[벤더]`는 뺀다 - 근거 문서를 고치거나 업스트림 포인터를 옮기는
#: 것 자체는 할 일의 이동이 아니다.
BOARD_AREAS = ("업스트림", "한국전용", "검증", "도구")

#: 남은 일은 여기만 보면 된다.
BOARD_PATH = "docs/status.md"

#: 현황판을 안 건드리는 이유를 밝히는 트레일러. 값이 비면 면제가 아니다.
BOARD_TRAILER = "Status-Board"

#: 사용자가 받는 것이 바뀌는 경로. 여기를 건드린 커밋은 릴리스 노트로 그대로
#: 옮길 한 줄을 같이 남긴다.
#:
#: 갈래가 아니라 경로로 묻는 이유가 있다. `b979baf`는 `[문서]` 커밋인데
#: 배포되는 안내의 원본을 77줄 고쳤다 - 사용자가 읽는 변경이다. 갈래로
#: 나눴으면 그 부류가 샌다. C7·C11이 이미 경로로 묻는 것과 같은 방식이다.
RELEASE_NOTE_PATHS = (
    VENDOR_PATH,
    "overlay/ko/README.ko.md",
    "overlay/ko/KEYS.ko.md",
    "overlay/ko/ko.json",
)

#: 릴리스 노트로 옮길 한 줄. **제목과 독자가 다르다** - 제목은 여섯 달 뒤에
#: `git log --oneline`으로 커밋을 찾는 사람이 읽고(C12가 대상 이름을 요구하는
#: 이유), 이 줄은 새 판을 받은 사람이 읽는다. 한 줄에 둘을 담으려니 판마다
#: 한쪽이 졌고, 노트를 쓸 때마다 커밋 본문을 다시 읽어야 했다.
#:
#: `Upstream-Subject`와 발상이 같다. 변경이 머릿속에 있을 때 다른 독자를 위한
#: 한 줄을 미리 써 두는 것이고, 몇 달 뒤 diff로 복원하는 것보다 정확하다.
NOTE_TRAILER = "Release-Note"

#: 노트를 안 남기는 이유를 밝히는 값. 뒤에 이유가 붙어야 한다.
NOTE_EXEMPT_PREFIX = "없음"

#: 노트 줄이 끝나야 하는 꼴. 사용자가 읽는 문장이라 명사형이다.
NOTE_SUFFIX = "함."

#: 노트 줄에 쓰지 않는 말. 사용자 화면 어디에도 안 뜨는 내부 이름이다.
#: 백틱으로 감싼 자리는 안 본다 - 사용자가 직접 실행하는 파일 이름은
#: 노트에 나오는 것이 맞다(`FF14AccessibilityInstaller-KR.exe`).
#: SUBJECT_BANNED와 같이 목록이 규칙의 전부고, 오탐이 나면 여기서 뺀다.
NOTE_BANNED = (
    "Launcher",
    "Installer",
    "csproj",
    "pack-check",
    "release-manifest",
    "commit-lint",
    "KrProfile",
    "Dalamud",
    "repo.json",
    "installer.json",
)

SUBJECT_MAX = 72

#: 제목에 쓰지 않는 말. 고른 기준은 취향이 아니라 실측이다 - 이력 166건에서
#: 대상을 지우고 그 자리에 들어앉은 것들이고, 여섯 달 뒤에 `git log --oneline`을
#: 읽는 사람이 무슨 커밋인지 복원할 수 없게 만든 낱말이다.
#: 오탐이 나면 여기서 빼면 된다. 목록이 규칙의 전부고 다른 곳에 근거가 없다.
#: 활용형을 따로 적는다. 한글은 음절이 단위라 `걷어낸다`에 `걷어내`가 없다
#: (`걷어`+`낸다`로 쪼개진다). 어간만 넣거나 형태를 나열해야 실제로 걸린다.
SUBJECT_BANNED = (
    "삼키",
    "삼킨",
    "삼켰",
    "걷어",
    "말하게",
    "임자",
    "꼬리를",
    "같은 얼굴",
    "세운다",
    "세우기",
    "세웠",
    "박는다",
    "박아",
    "박힌",
    "밀다",
    "밀게",
    "민다",
)

_SUBJECT_RE = re.compile(r"^\[(?P<area>[^\]]+)\]\s+(?P<rest>.*)$")

#: `[영역] 대상: 무엇이 어떻게`. 대상은 고친 것의 이름 그대로 - 파일명, 도구명,
#: 클래스, 명령. 첫 콜론에서 자르므로 설명 안에 콜론이 또 있어도 된다.
_TARGET_RE = re.compile(r"^(?P<target>[^:]+):\s*(?P<what>.+)$")

#: `판`은 `docs/status.md`를 가리키는 은어로 쓰였다. `현황판`처럼 앞에 한글이
#: 붙은 낱말은 제대로 된 이름이므로 건드리지 않는다.
_BOARD_SLANG_RE = re.compile(r"(?<![가-힣])판[이가을를은는에]")
_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)"
    r"(\([^)]*\))?!?:",
    re.IGNORECASE,
)
_SCISSORS_RE = re.compile(r"^#\s*-+\s*>8\s*-+")
_UMLAUT_RE = re.compile(r"[äöüÄÖÜß]")

#: 백틱으로 감싼 자리. 노트 줄에서 내부 이름을 찾을 때 먼저 걷어낸다.
_BACKTICK_RE = re.compile(r"`[^`]*`")


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


def note_problem(note: str | None) -> str | None:
    """릴리스 노트 줄의 문제. 없으면 None."""
    if not note:
        return (
            "사용자가 받는 것이 바뀌었다. 릴리스 노트로 그대로 옮길 한 줄을 "
            f"남겨라 - 예: `{NOTE_TRAILER}: 바탕화면 바로가기로 게임과 "
            "KR 달라무드 업데이터가 실행되도록 함.` "
            f"사용자에게 안 닿는 변경이면 `{NOTE_TRAILER}: 없음 - <이유>`"
        )

    if note.startswith(NOTE_EXEMPT_PREFIX):
        reason = note[len(NOTE_EXEMPT_PREFIX) :].strip(" -")
        if not reason:
            return (
                f"`{NOTE_TRAILER}: {NOTE_EXEMPT_PREFIX}` 뒤에 이유를 대라 - "
                "예: `없음 - 주석만 고침`. 값이 비면 면제가 아니다"
            )
        return None

    if not note.endswith(NOTE_SUFFIX):
        return (
            "노트 줄은 사용자가 읽을 문장 그대로다. "
            f"`~하도록 {NOTE_SUFFIX}` 꼴로 끝내라 - 제목의 `~한다`와 독자가 다르다"
        )

    banned = [word for word in NOTE_BANNED if word in _BACKTICK_RE.sub("", note)]
    if banned:
        return (
            f"노트 줄에 내부 이름을 쓰지 않는다: {', '.join(banned)}. "
            "사용자 화면에 뜨는 이름으로 바꿔라 - 사용자가 보는 것은 "
            "`Launcher`가 아니라 `바탕화면 바로가기`다. "
            "직접 실행하는 파일 이름이면 백틱으로 감싼다"
        )

    return None


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

    # C12/C13은 갈래를 제대로 붙인 제목에만 묻는다. C1이 이미 걸린 줄에
    # 두 개를 더 얹으면 무엇부터 고쳐야 하는지가 안 보인다.
    if area is not None:
        target = _TARGET_RE.match(rest)
        if target is None or not target.group("target").strip():
            violations.append(
                Violation(
                    "C12",
                    "제목에 대상이 없다. `[갈래] 대상: 무엇이 어떻게` 모양으로 "
                    "고친 것의 이름을 앞세워라 - 파일명, 도구명, 클래스, 명령. "
                    "이름을 못 고르겠으면 대개 커밋이 너무 크다는 뜻이다",
                )
            )

        banned = [word for word in SUBJECT_BANNED if word in rest]
        if _BOARD_SLANG_RE.search(rest):
            banned.append("판(→ status.md)")
        if banned:
            violations.append(
                Violation(
                    "C13",
                    f"제목에 비유·은어를 쓰지 않는다: {', '.join(banned)}. "
                    "본문에는 써도 된다 - 막는 것은 `git log --oneline`에 "
                    "남는 한 줄뿐이다",
                )
            )

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

    if area == "벤더":
        missing = [
            key for key in REQUIRED_VENDOR_TRAILERS if not trailer_value(body, key)
        ]
        if missing:
            violations.append(
                Violation(
                    "C9",
                    f"[벤더] 커밋에 빠진 줄이 있다: {', '.join(missing)}. "
                    "예: `Upstream-Range: v5.85..v5.87 (3051202..a8ac7c5)`",
                )
            )

        if PIN_PATH in changed_paths and CHANGES_PATH not in changed_paths:
            violations.append(
                Violation(
                    "C10",
                    f"핀을 옮기면서 {CHANGES_PATH}를 안 건드렸다. "
                    "업스트림은 독일어로 개발된다 - 이력을 한국어로 남기지 않으면 "
                    "무엇이 들어왔는지 아무도 못 읽는다",
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

    if area and area not in VENDOR_AREAS and changed_paths:
        moved = [
            path
            for path in changed_paths
            if path == VENDOR_PATH or path.startswith(f"{VENDOR_PATH}/")
        ]
        if moved:
            violations.append(
                Violation(
                    "C11",
                    f"[{area}] 커밋이 vendor 포인터를 옮긴다. 이 갈래로는 "
                    "vendor가 왜 바뀌었는지 이력에 안 남는다 - "
                    f"{', '.join(f'[{a}]' for a in VENDOR_AREAS)} 커밋으로 떼어내라",
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

    touches_user = any(
        path == prefix or path.startswith(f"{prefix}/")
        for path in changed_paths
        for prefix in RELEASE_NOTE_PATHS
    )
    if touches_user:
        problem = note_problem(trailer_value(body, NOTE_TRAILER))
        if problem:
            violations.append(Violation("C14", problem))

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

    print("커밋 메시지가 규칙에 안 맞는다 (docs/dev/commit-rules.md):", file=sys.stderr)
    for violation in violations:
        print(f"  {violation}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
