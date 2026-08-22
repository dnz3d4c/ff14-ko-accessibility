"""릴리스 노트 본문이 판마다 다르게 쓰이는 것을 막는다.

## 무엇을 막나

**노트 본문을 만드는 코드도 본도 없었다.** 사람이 `dist\\release\\release-notes.md`에
손으로 쓰고 `run\\release.bat`이 `--notes-file`로 올린다. 그런데 `dist/`가
`.gitignore`에 있어 **본문이 판마다 사라진다** - `git log --all -- '*release-notes*'`가
0건이다. 다음 판을 쓸 때 이전 판을 볼 수 없으니 매번 새로 지어냈고, 그래서
`v5.88.0.0`과 `v5.88.0.1`의 절 이름과 종결형이 이미 서로 달랐다.

커밋 트레일러 한 줄(`Release-Note:`)은 `commit_lint`의 C14가 갖는다. 그 줄들을
모아 **노트 전체를 조립하는 단계**에 소유자가 없었고, 이 검사기가 그 자리다.

규칙과 근거: docs/dev/release.md §3-2

## 규칙 접두가 `N`인 이유

`docs_check.lint_rule_max`가 커밋 검사기에서 `"C(\\d+)"`를 긁어 문서와 대조한다.
여기서 `C`를 쓰면 코드 공간이 섞여 그 대조가 엉뚱한 최대값을 잡는다.

## 기계가 못 보는 것

**`모드 변경사항:` 줄의 진위는 판정 불가가 확정이다.** 세 갈래가 다 막힌다 -
판 번호는 설치 프로그램만 고친 판에서도 오르고(v5.88.0.1이 그 실물), 산출물
바이트는 판 번호가 zip 안 매니페스트에 들어가는 데다 DLL의 MVID가 빌드마다
바뀌며, vendor 포인터는 csproj 둘이 `vendor/` 안이라 판 올림만 하는 커밋도
gitlink를 움직인다. 그래서 이 검사기는 **줄의 꼴만** 보고 진위는 안 본다.

나머지도 문서가 갖는다 - 산문 절의 도입 문단, 변경 항목의 순서와 취사,
강조 한 번을 어디에 쓸까, 제한사항이 현황과 맞나, 문장이 사실인가.

사용법:
    uv run --no-project python tools/notes-check/notes_check.py --version 5.88.0.1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# 같은 일을 두 번 만들지 않는다 - 선례는 `docs_check`가 `ko_words`를 가져다
# 쓰는 방식이다. 특히 `note_problem`은 **트레일러와 노트 항목이 같은 문자열**
# 이라서, 그대로 부르면 규칙이 저절로 같아진다.
for _sibling in ("commit-lint", "ko-style", "release-manifest", "pack-check"):
    sys.path.insert(0, str(REPO / "tools" / _sibling))

import commit_lint  # noqa: E402 - 위에서 경로를 넣어야 찾는다
import ko_style  # noqa: E402
import pack_check  # noqa: E402
import release_manifest  # noqa: E402

Violation = commit_lint.Violation

#: 검사할 파일. `pack_check`가 배포물에서 이 이름을 허용 목록에 넣는다.
NOTES_PATH = REPO / "dist" / "release" / pack_check.RELEASE_NOTES_NAME

#: 본. 판마다 여기서 떠서 쓴다.
TEMPLATE_PATH = Path(__file__).resolve().parent / "template.md"

#: 절 이름과 순서. **열거 밖은 통과가 아니라 위반이다** - 이슈 링크 절이
#: 실제로 그렇게 되살아났고, "모르는 절은 그냥 둔다"로 두면 다시 그렇게 된다.
CHANGES_SECTION = "v{version} 변경사항"
SECTION_NAMES = (
    "설치",
    CHANGES_SECTION,
    "준비물",
    "업데이트 방법",
    "알려진 제한사항",
    "라이선스",
)

#: 제목 바로 아래가 목록이어야 하는 절. "도입 문단을 넣지 않는다"를 기계가
#: 잴 수 있게 좁힌 판이다 - 절 전체의 산문 여부는 안 본다.
LIST_SECTIONS = (CHANGES_SECTION, "준비물", "알려진 제한사항")

#: 모드가 바뀌었는지 알리는 줄. **분류가 아니라 받는 방법을 가르는 신호다** -
#: 모드가 바뀌면 게임을 켤 때 Dalamud가 자동으로 갱신하고, 안 바뀌면 사용자가
#: 설치 프로그램을 다시 돌려야 한다.
MOD_PREFIX = "모드 변경사항:"
MOD_NONE = "없음."

#: 보충 표기. 공식 가이드가 쓰는 꼴이고 노트에서는 자산 안내 한 줄이다.
NOTE_MARK = "※"

#: 백틱 안에 한글을 써도 되는 것. 사용자가 손에 쥐는 파일 이름이다.
BACKTICK_HANGUL_OK = (release_manifest.GUIDE_NAME, release_manifest.KEYS_NAME)

#: 항목 하나를 통째로 강조한 것으로 세는 비율. **밀도로 재면 사고를 못 잡는다** -
#: 발행본의 강조 밀도 8.5%가 사용자가 쓴 `README.ko.md`의 11.6%보다 낮았다.
#: 실측에서 사용자가 쓴 565줄(항목 202개)에 전면 강조가 0개라 오탐 여지가 없다.
FULL_EMPHASIS_RATIO = 2

#: 한 절에 허용하는 굵게. 기울임은 세 문서 모두 0회라 여는 것 자체가 근거 없다.
BOLD_PER_SECTION = 1

_HEADING = re.compile(r"^(#+)\s+(.*)$")
_ITEM = re.compile(r"^- (.*)$")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"\*([^*]+)\*")
_LINK = re.compile(r"\[[^\]]+\]\([^)]+\)")
_VERSION = re.compile(r"v\d+(?:\.\d+)+")
_PLACEHOLDER = re.compile(r"\{\{([^}]*)\}\}")
_HANGUL = re.compile(r"[가-힣]")
_BACKTICK = commit_lint._BACKTICK_RE  # noqa: SLF001 - 같은 규칙을 두 벌로 두지 않는다


def sections_of(version: str) -> tuple[str, ...]:
    """이번 판의 절 이름. 변경사항 절만 판 번호를 이름에 갖는다."""
    return tuple(name.format(version=version) for name in SECTION_NAMES)


def title_of(version: str) -> str:
    return f"## {release_manifest.PLUGIN_DISPLAY_NAME} v{version}"


def split_sections(text: str) -> list[tuple[str, list[str]]]:
    """`(절 이름, 본문 줄)`. 첫 항목은 `###` 앞의 서두이고 이름이 빈 문자열이다."""
    found: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        head = _HEADING.match(line)
        if head is not None and len(head.group(1)) == 3:
            found.append((head.group(2).strip(), []))
        else:
            found[-1][1].append(line)
    return found


def placeholders(text: str) -> set[str]:
    """`{{...}}` 자리 이름. `<버전>` 꼴을 안 쓰는 것은 세 문서가 이미 다른 뜻으로 써서다."""
    return set(_PLACEHOLDER.findall(text))


def template() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def render(version: str) -> str:
    """본에서 판 번호만 채운다. 나머지 셋은 사람이 채우고 N6이 안 채운 것을 막는다."""
    return template().replace("{{버전}}", release_manifest.normalize_version(version))


def decode(raw: bytes) -> tuple[str, list[Violation]]:
    """읽은 바이트를 본문으로. BOM은 떼고 알린다.

    BOM이 붙으면 첫 줄이 `## `로 안 시작해 **제목이 본문 글자가 된다.** 그
    상태로 올리면 릴리스 페이지에서 제목 줄만 조용히 문단이 되고, 내는 사람
    화면에는 아무 오류도 안 남는다.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return "", [
            Violation(
                "N1",
                f"UTF-8로 못 읽는다({error.reason}, {error.start}바이트째). "
                "편집기 인코딩을 UTF-8로 바꿔 다시 저장해라",
            )
        ]

    if text.startswith("﻿"):
        return text.lstrip("﻿"), [
            Violation(
                "N1",
                "맨 앞에 BOM이 있다. 첫 줄이 `## `로 안 시작해 제목이 본문 글자가 된다 - "
                "BOM 없는 UTF-8로 다시 저장해라",
            )
        ]

    return text, []


def _emphasis_len(line: str) -> int:
    """강조 안 글자 수. 굵게와 기울임을 함께 센다."""
    bold = _BOLD.findall(line)
    rest = _BOLD.sub(" ", line)
    return sum(len(t) for t in bold) + sum(len(t) for t in _ITALIC.findall(rest))


def _mod_line_problem(body: list[str]) -> str | None:
    """변경사항 절의 `모드 변경사항:` 줄 문제. 없으면 None."""
    marks = [i for i, line in enumerate(body) if line.startswith(MOD_PREFIX)]
    if len(marks) != 1:
        return (
            f"`{MOD_PREFIX}` 줄이 {len(marks)}개다. 변경 항목 목록 **뒤에** 하나만 둔다 - "
            f"모드가 안 바뀌었으면 `{MOD_PREFIX} {MOD_NONE}`, 바뀌었으면 "
            f"`{MOD_PREFIX}` 아래에 목록으로 적는다. 받는 방법이 갈리는 자리라 생략하지 않는다"
        )

    at = marks[0]
    before = [line for line in body[:at] if _ITEM.match(line)]
    after = [line for line in body[at + 1 :] if _ITEM.match(line)]
    if not before:
        return f"`{MOD_PREFIX}` 줄이 변경 항목보다 앞에 있다. 항목 목록 뒤로 내려라"

    value = body[at][len(MOD_PREFIX) :].strip()
    if value == MOD_NONE:
        if after:
            return f"`{MOD_PREFIX} {MOD_NONE}`이라고 적고 아래에 항목 {len(after)}개를 뒀다"
        return None
    if value:
        return (
            f"`{MOD_PREFIX} {value}`는 쓰지 않는다. "
            f"`{MOD_PREFIX} {MOD_NONE}`이거나, 값을 비우고 아래에 목록을 적는다"
        )
    if not after:
        return f"`{MOD_PREFIX}` 값이 비었는데 아래에 목록이 없다"
    return None


def check(text: str, version: str) -> list[Violation]:
    """어긴 것 목록. 비어 있으면 통과."""
    version = release_manifest.normalize_version(version)
    want_sections = sections_of(version)
    parts = split_sections(text)
    lines = text.splitlines()
    bare = _BACKTICK.sub(" ", text)

    violations: list[Violation] = []

    # N2 - 본문 제목. 릴리스 페이지 제목과 겹치지만, 소리로 본문만 훑을 때
    # 기준점이 되므로 남긴다.
    head = next((line for line in lines if line.strip()), "")
    want_title = title_of(version)
    if head.strip() != want_title:
        violations.append(
            Violation("N2", f"첫 줄이 `{want_title}`여야 한다. 지금은 `{head.strip()}`이다")
        )
    tops = [line for line in lines if _HEADING.match(line) and line.startswith("## ")]
    if len(tops) != 1:
        violations.append(
            Violation("N2", f"`##` 제목이 {len(tops)}개다. 본문 제목 하나뿐이고 절은 전부 `###`다")
        )

    # N3 - 절 구성. **리스트 동등 비교다.** 열거 밖 절은 통과가 아니라 위반이다.
    got_sections = tuple(name for name, _ in parts[1:])
    if got_sections != want_sections:
        message = (
            f"절 구성이 다르다. 있어야 하는 것: {' → '.join(want_sections)}. "
            f"지금: {' → '.join(got_sections) or '(없음)'}"
        )
        if any("문제를 알릴 곳" in name or "이슈" in name for name in got_sections):
            message += ". 이슈 링크 절은 넣지 않는다"
        violations.append(Violation("N3", message))

    # N4 - 제목 깊이. 발행본이 절을 전부 `##`로 쓴 것이 이 규칙이 잡는 실물이다.
    depths = [len(m.group(1)) for m in (_HEADING.match(line) for line in lines) if m]
    if depths.count(2) != 1 or depths.count(3) != len(want_sections) or len(depths) != 1 + len(want_sections):
        violations.append(
            Violation(
                "N4",
                f"제목 깊이가 `##` 1개 + `###` {len(want_sections)}개여야 한다. "
                f"지금 깊이별로 {depths}다",
            )
        )

    # N5 - 지난 판을 복사해 한 자리를 안 고치는 것.
    stale = sorted({v for v in _VERSION.findall(text) if v != f"v{version}"})
    if stale:
        violations.append(
            Violation("N5", f"이번 판이 아닌 판 번호가 있다: {', '.join(stale)}. 이번 판은 v{version}이다")
        )

    # N6 - 안 채운 자리.
    left = placeholders(text)
    if left:
        violations.append(
            Violation("N6", f"본의 자리표시자가 남아 있다: {', '.join(f'{{{{{n}}}}}' for n in sorted(left))}")
        )

    changes = CHANGES_SECTION.format(version=version)
    body_of = {name: body for name, body in parts[1:]}

    # N7 - 변경 항목. **트레일러와 같은 문자열이라 `note_problem`을 그대로 부른다.**
    # 다만 `없음 - <이유>` 면제는 트레일러의 것이고 노트 항목에서는 안 통한다.
    for line in body_of.get(changes, []):
        item = _ITEM.match(line)
        if item is None or line.startswith(MOD_PREFIX):
            continue
        note = item.group(1).strip()
        if note.startswith(commit_lint.NOTE_EXEMPT_PREFIX):
            violations.append(
                Violation("N7", f"변경 항목에 `{note}`를 적었다. 트레일러의 면제는 노트 항목에 옮기지 않는다")
            )
            continue
        problem = commit_lint.note_problem(note)
        if problem:
            violations.append(Violation("N7", f"변경 항목 `{note}`: {problem}"))

    # N8 - 받는 방법을 가르는 줄.
    if changes in body_of:
        problem = _mod_line_problem(body_of[changes])
        if problem:
            violations.append(Violation("N8", problem))

    # N9 - 인라인 링크.
    links = _LINK.findall(text)
    if links:
        violations.append(
            Violation("N9", f"인라인 링크를 쓰지 않는다: {', '.join(links)}")
        )

    # N10 - 전면 강조. 항목을 통째로 굵게 하면 강조가 아니라 배경이 된다.
    for line in lines:
        item = _ITEM.match(line)
        if item is None:
            continue
        rest = item.group(1)
        if rest and _emphasis_len(rest) * FULL_EMPHASIS_RATIO >= len(rest):
            violations.append(
                Violation("N10", f"항목을 통째로 강조했다: {line.strip()}")
            )

    # N11 - 강조 개수.
    for name, body in parts:
        bold = sum(len(_BOLD.findall(line)) for line in body)
        if bold > BOLD_PER_SECTION:
            violations.append(
                Violation(
                    "N11",
                    f"`{name or '서두'}` 절에 굵게가 {bold}개다. "
                    f"절당 {BOLD_PER_SECTION}개까지다",
                )
            )
    italic = _ITALIC.findall(_BOLD.sub(" ", text))
    if italic:
        violations.append(
            Violation("N11", f"기울임을 쓰지 않는다: {', '.join(italic)}")
        )

    # N12 - 백틱 안 한글. 사용자가 손에 쥐는 파일 이름만 그 자리에 온다.
    for quoted in re.findall(r"`([^`]*)`", text):
        if _HANGUL.search(quoted) and quoted not in BACKTICK_HANGUL_OK:
            violations.append(
                Violation(
                    "N12",
                    f"백틱 안에 한글이 있다: `{quoted}`. "
                    f"그 자리에 오는 것은 {', '.join(BACKTICK_HANGUL_OK)}뿐이다",
                )
            )

    # N13 - 말투. 사람이 읽는 문서라 습니다체다(모드가 말하는 문장과 반대다).
    strays = [n for n, kind in ko_style.endings(text) if kind == "한다체"]
    if len(strays) >= ko_style.MIXED_LIMIT:
        violations.append(
            Violation(
                "N13",
                f"한다체가 {len(strays)}곳이다({', '.join(str(n) for n in strays[:6])}행). "
                "노트는 사람이 읽는 문서라 습니다체다",
            )
        )

    # N14 - 내부 이름. `※` 줄의 `Dalamud`만 예외다 - 플러그인 로더 자체를 가리킨다.
    for number, line in enumerate(bare.splitlines(), 1):
        allowed = ("Dalamud",) if line.lstrip().startswith(NOTE_MARK) else ()
        banned = [w for w in commit_lint.NOTE_BANNED if w in line and w not in allowed]
        if banned:
            violations.append(
                Violation(
                    "N14",
                    f"{number}행에 내부 이름이 있다: {', '.join(banned)}. "
                    "사용자 화면에 뜨는 이름으로 바꿔라 - 직접 실행하는 파일 이름이면 백틱으로 감싼다",
                )
            )

    # N15 - 자산 안내. 사람이 받을 것 하나를 위로 올리고 나머지를 여기서 내린다.
    marks = [line for line in lines if line.strip().startswith(NOTE_MARK)]
    tail = next((line for line in reversed(lines) if line.strip()), "")
    if len(marks) != 1 or tail.strip() != marks[0].strip():
        violations.append(
            Violation(
                "N15",
                f"`{NOTE_MARK}`로 시작하는 줄이 맨 끝에 하나 있어야 한다(지금 {len(marks)}개). "
                "나머지 자산이 무엇인지 알리는 자리다",
            )
        )

    # N16 - 도입 문단. 목록 절은 제목 바로 아래가 목록이다.
    for name in (n.format(version=version) for n in LIST_SECTIONS):
        body = body_of.get(name)
        if body is None:
            continue
        first = next((line for line in body if line.strip()), "")
        if not _ITEM.match(first):
            violations.append(
                Violation(
                    "N16",
                    f"`{name}` 절이 목록으로 시작하지 않는다: {first.strip()}. "
                    "제목 바로 아래에 도입 문단을 두지 않는다",
                )
            )

    return violations


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="릴리스 노트 본문을 검사한다")
    parser.add_argument("path", nargs="?", type=Path, default=NOTES_PATH)
    parser.add_argument("--version", required=True, help="이번 판 번호 (예: 5.88.0.1)")
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"릴리스 노트가 없다: {args.path}", file=sys.stderr)
        return 1

    text, violations = decode(args.path.read_bytes())
    if text:
        violations += check(text, args.version)

    if violations:
        print(f"릴리스 노트가 규칙에 안 맞는다 (docs/dev/release.md §3-2): {args.path}", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        return 1

    print(f"통과 - 절 {len(SECTION_NAMES)}개 구성과 마크업 규칙을 지켰다: {args.path}")
    print("  이 검사는 절 구성과 마크업과 `모드 변경사항:` 줄의 꼴만 본다.")
    print("  문장이 사실인가, 항목 순서가 맞나는 사람이 본다 - docs/dev/release.md §3-2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
