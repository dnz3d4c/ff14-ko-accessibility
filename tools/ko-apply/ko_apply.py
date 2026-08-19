"""한국어를 카탈로그에서 소스로 써 넣는다. 소스는 생성물이다.

## 왜 이렇게 하나

한국어화는 `AccessibilityStrings.cs` 안의 688쌍을 고치는 일이다. 그걸 손으로
쓴 diff로 쌓으면 700줄짜리 변경이 되는데, **그 파일을 업스트림이 계속
고친다** - 8일에 릴리스 7개다(docs/status.md §5-4).

그러면 업스트림을 올릴 때마다 700줄 diff의 충돌을 손으로 푼다. 문제는 충돌
빈도가 아니라 **해결 비용**이다 - 손으로 쓴 diff는 손으로 푸는 수밖에 없다.

그래서 한국어를 diff가 아니라 **데이터**로 저장한다. `overlay/ko/ko.json`이
`(독일어, 영어) -> 한국어` 표를 갖고, 이 도구가 소스를 다시 쓴다. 그 결과는
`kr-port`의 **생성 커밋**(제목 고정형, 아래 GENERATED_SUBJECT)이고,
**충돌하면 푸는 게 아니라 버리고 다시 만든다.** 실패 모드가 "diff 충돌"에서
"카탈로그의 문장 N개를 소스에서 못 찾음"으로 바뀐다.

## 무엇을 건드리고 무엇을 안 건드리나

건드리는 자리는 **카탈로그에 있는 쌍뿐이다.** 이게 이중 안전장치다.

- 못 읽는 모양(중첩 삼항 등 손 케이스, docs/korean/hand-cases.md)은 애초에
  안 잡힌다. 잡히더라도 카탈로그에 없으므로 안 건드린다
- 잘못 읽어 조각난 문자열도 카탈로그에 있을 리 없다

독일어·영어 리터럴은 **읽기만 한다.** 세 번째 인자를 붙일 뿐이라 골든
스냅샷(`tools/strings-golden`)이 그대로여야 하고, 그게 이 도구의 회귀 검사다.

## 빠진 자리도 여기서 센다

옮기는 동안 소스를 훑는 파서가 이미 답을 갖고 있다 - 어느 자리에 한국어
인자가 있고 없는지를 `find_sites`가 말해 준다. 그래서 **한국어가 없어 조용히
영어가 나갈 자리**를 같은 파서로 센다(`missing_korean`). `Loc.Pick`의 폴백이
그걸 예외도 로그도 없이 덮기 때문에, 안 세면 배포될 때까지 아무도 모른다.

## 손 케이스는 여기 넣지 않는다

손 케이스는 이 도구가 못 다룬다. 그건 **별도 커밋**으로 간다 - 생성 커밋에
손편집을 섞으면 다시 만들 때 조용히 사라진다.

사용법:
    uv run --no-project python tools/ko-apply/ko_apply.py           # 대조
    uv run --no-project python tools/ko-apply/ko_apply.py --write   # 소스에 반영
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "strings-golden"))

import strings_golden  # noqa: E402 - 위에서 경로를 넣어야 찾는다

REPO = Path(__file__).resolve().parents[2]
VENDOR = REPO / "vendor" / "ff14-accessibility"
SOURCE_ROOT = VENDOR / "FF14Accessibility"
CATALOG = REPO / "overlay" / "ko" / "ko.json"

#: 생성 커밋이 앉아 있는 브랜치.
WORK_BRANCH = "kr-port"

#: 생성 커밋을 **제목으로** 찾는다. 끝 커밋이라고 가정하지 않는다 - 도구가
#: 못 읽는 모양(중첩 삼항·이어붙이기·배열)은 손으로 쓴 별도 커밋으로 그 뒤에
#: 붙기 때문이다. 제목이 고정형인 이유가 이것이기도 하다.
GENERATED_SUBJECT = "Korean: the mod's own strings, generated from the catalogue"

#: 소스 루트가 vendor 안에서 갖는 이름.
SOURCE_NAME = "FF14Accessibility"

MARKER = "IsGerman"
PICK = "Pick("
_IDENT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")

#: 한 줄에 이 칸을 넘으면 인자마다 줄을 나눈다. 업스트림 소스의 폭에 맞췄다.
WIDTH = 100

#: 보간 자리. `{{`는 중괄호 자체라 자리가 아니다.
SLOT = re.compile(r"(?<!\{)\{([^{}]+)\}")

#: 축약을 쓰는 파일에 넣어 주는 선언. 이것도 생성물이다 - 손으로 넣어 두면
#: 다시 만들 때 이 줄만 손편집으로 남아 그 자리에서 충돌이 난다.
SHORTHAND = """
    // Three-language form. Generated from overlay/ko/ko.json by tools/ko-apply -
    // do not hand-edit the Korean in this file, the catalogue is the original.
    private static string Pick(string de, string en, string? ko = null) =>
        Loc.Pick(de, en, ko);
"""

#: 선언을 끼우는 자리. 같은 갈래의 축약 바로 다음이다.
ANCHOR = "    private static bool IsGerman => Loc.IsGerman;\n"


@dataclass(frozen=True)
class Site:
    """소스에서 한 문장이 앉아 있는 자리."""

    start: int
    end: int
    de: str
    en: str
    de_raw: str
    en_raw: str
    ko: str | None  # 이미 소스에 박혀 있는 한국어 (3인자 Pick)
    line: int
    #: `Loc.` 또는 빈 문자열. 그 자리가 쓰던 표기를 그대로 되쓴다.
    qualifier: str = ""


@dataclass
class Result:
    text: str
    applied: list[tuple[str, str]] = field(default_factory=list)
    seen: list[tuple[str, str]] = field(default_factory=list)
    stray: list[str] = field(default_factory=list)
    bad_slots: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


# --- 카탈로그 --------------------------------------------------------------


def load_catalog(path: Path = CATALOG) -> dict[tuple[str, str], str]:
    """`(독일어, 영어) -> 한국어`.

    독일어와 영어를 **둘 다** 키로 쓴다. 독일어만으로는 같은 낱말이 다른
    문장에서 다른 영어를 갖는 경우를 못 가른다.
    """
    if not path.is_file():
        return {}

    rows = json.loads(path.read_text(encoding="utf-8"))["strings"]
    catalog: dict[tuple[str, str], str] = {}
    for row in rows:
        key = (row["de"], row["en"])
        if not row["ko"].strip():
            raise ValueError(f"한국어가 비어 있다: {row['en'][:60]}")
        if key in catalog:
            raise ValueError(f"카탈로그에 같은 쌍이 중복이다: {row['en'][:60]}")
        catalog[key] = row["ko"]
    return catalog


def orphans(
    catalog: dict[tuple[str, str], str], seen: list[tuple[str, str]]
) -> list[tuple[str, str]]:
    """카탈로그에는 있는데 소스에서 못 만난 쌍.

    **업스트림이 그 문장을 고쳤다는 신호다.** 옛날 같으면 패치 충돌로 나던
    것이 여기서 목록으로 나온다.
    """
    found = set(seen)
    return [key for key in catalog if key not in found]


# --- 읽기 ------------------------------------------------------------------


def _read_literal(text: str, i: int) -> tuple[str | None, int, int]:
    """C# 문자열 리터럴을 읽는다. (내용, 시작, 끝).

    시작은 `$` 접두를 포함한다 - 원문을 그대로 되쓰기 위해서다. 축자
    문자열(`@"..."`)은 안 읽는다.
    """
    raw_start = i
    if i < len(text) and text[i] == "$":
        i += 1
    if i >= len(text) or text[i] != '"':
        return None, raw_start, i
    if i > 0 and text[i - 1] == "@":
        return None, raw_start, i

    i += 1
    out: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            out.append(text[i : i + 2])
            i += 2
            continue
        if ch == '"':
            return "".join(out), raw_start, i + 1
        if ch == "\n":
            return None, raw_start, i
        out.append(ch)
        i += 1
    return None, raw_start, i


def _skip(text: str, i: int) -> int:
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def _qualified(text: str, found: int) -> tuple[int, str]:
    """`Loc.`이 앞에 붙어 있으면 자리를 그만큼 앞으로 물리고 표기를 돌려준다.

    파일마다 관례가 다르다 - `AccessibilityStrings.cs`는 축약 `IsGerman`을
    두고 쓰고 `Compat/CompatReport.cs`는 `Loc.IsGerman`을 그대로 쓴다. 한쪽으로
    통일해 버리면 그 파일이 안 쓰던 표기가 섞여 들어간다.
    """
    prefix = "Loc."
    if text[max(0, found - len(prefix)) : found] == prefix:
        return found - len(prefix), prefix
    return found, ""


def find_sites(text: str) -> list[Site]:
    """소스에서 고칠 수 있는 자리를 위치와 함께 뽑는다.

    주석은 같은 길이의 공백으로 지우고 찾는다 - 길이가 그대로라 위치가 원문과
    1대1로 맞고, 주석에 적힌 예시를 코드로 읽지 않는다.
    """
    stripped = strings_golden.strip_comments(text)
    sites = [*_ternary_sites(stripped, text), *_pick_sites(stripped, text)]
    return sorted(sites, key=lambda s: s.start)


def _ternary_sites(stripped: str, text: str) -> list[Site]:
    """아직 안 옮긴 `IsGerman ? de : en`."""
    sites: list[Site] = []
    start = 0
    while True:
        found = stripped.find(MARKER, start)
        if found < 0:
            return sites
        start = found + len(MARKER)

        i = _skip(stripped, start)
        if i >= len(stripped) or stripped[i] != "?":
            continue

        i = _skip(stripped, i + 1)
        de, de_start, i = _read_literal(stripped, i)
        if de is None:
            continue
        de_end = i

        i = _skip(stripped, i)
        if i >= len(stripped) or stripped[i] != ":":
            continue

        i = _skip(stripped, i + 1)
        en, en_start, i = _read_literal(stripped, i)
        if en is None:
            continue

        span, qualifier = _qualified(stripped, found)
        sites.append(Site(
            start=span, end=i, de=de, en=en,
            de_raw=text[de_start:de_end], en_raw=text[en_start:i],
            ko=None, line=stripped.count("\n", 0, found) + 1,
            qualifier=qualifier,
        ))


def _pick_sites(stripped: str, text: str) -> list[Site]:
    """이미 옮긴 `Pick(de, en[, ko])`."""
    sites: list[Site] = []
    start = 0
    while True:
        found = stripped.find(PICK, start)
        if found < 0:
            return sites
        start = found + len(PICK)

        # `PickItem(` 같은 다른 이름을 거른다.
        if found > 0 and stripped[found - 1] in _IDENT:
            continue

        i = _skip(stripped, start)
        de, de_start, i = _read_literal(stripped, i)
        if de is None:
            continue  # 선언(`Pick(string de, ...)`)이거나 우리 게 아니다
        de_end = i

        i = _skip(stripped, i)
        if i >= len(stripped) or stripped[i] != ",":
            continue

        i = _skip(stripped, i + 1)
        en, en_start, i = _read_literal(stripped, i)
        if en is None:
            continue
        en_end = i

        ko: str | None = None
        i = _skip(stripped, i)
        if i < len(stripped) and stripped[i] == ",":
            i = _skip(stripped, i + 1)
            ko, _, i = _read_literal(stripped, i)
            if ko is None:
                continue
            i = _skip(stripped, i)

        if i >= len(stripped) or stripped[i] != ")":
            continue

        span, qualifier = _qualified(stripped, found)
        sites.append(Site(
            start=span, end=i + 1, de=de, en=en,
            de_raw=text[de_start:de_end], en_raw=text[en_start:en_end],
            ko=ko, line=stripped.count("\n", 0, found) + 1,
            qualifier=qualifier,
        ))


# --- 쓰기 ------------------------------------------------------------------


def _slots(text: str) -> set[str]:
    return set(SLOT.findall(text))


def _literal(ko: str) -> str:
    """한국어를 C# 리터럴로. 보간 자리가 있으면 `$`를 붙인다."""
    return ('$"' if SLOT.search(ko) else '"') + ko + '"'


def _render(site: Site, ko: str, text: str) -> str:
    """`Pick(...)` 호출을 만든다. 길면 여는 괄호에 맞춰 줄을 나눈다."""
    args = [site.de_raw, site.en_raw, _literal(ko)]
    head = site.qualifier + PICK
    column = site.start - text.rfind("\n", 0, site.start) - 1

    single = f"{head}{', '.join(args)})"
    if column + len(single) <= WIDTH:
        return single

    pad = " " * (column + len(head))
    return f"{head}{args[0]},\n{pad}{args[1]},\n{pad}{args[2]})"


def declares_shorthand(text: str) -> bool:
    return "private static string Pick(" in text


def ensure_shorthand(text: str) -> tuple[str, str | None]:
    """선언이 없으면 넣는다. (본문, 문제).

    자리를 못 찾으면 **아무 데나 끼워 넣지 않는다.** 잘못 끼우면 컴파일이
    깨지고, 그건 카탈로그를 고친 사람이 알아야 할 일이다.

    **파일 하나가 아니라 클래스 하나에 한 번이다.** `AccessibilityStrings`는
    `partial`이라 `AccessibilityStrings.Chat.cs`가 선언 없이 축약을 쓴다 -
    파일마다 넣으면 같은 멤버를 두 번 선언해 컴파일이 깨진다. 그래서 이건
    `_sweep`이 트리 전체를 보고 한 번만 부른다.
    """
    if declares_shorthand(text):
        return text, None
    if ANCHOR not in text:
        return text, (
            "축약 `Pick`을 넣을 자리를 못 찾았다 - "
            f"`{ANCHOR.strip()}` 다음에 넣는다"
        )
    return text.replace(ANCHOR, ANCHOR + SHORTHAND, 1), None


def rewrite(text: str, catalog: dict[tuple[str, str], str]) -> Result:
    """소스 한 파일을 카탈로그대로 다시 쓴다.

    카탈로그에 없는 자리는 **한 자도 안 건드린다.** W-06이 도는 동안 대부분이
    그 상태고, 안 옮긴 문장은 영어로 나가야 한다 - 침묵은 고장과 구분이 안 된다.
    """
    result = Result(text=text)
    edits: list[tuple[int, int, str]] = []

    for site in find_sites(text):
        key = (site.de, site.en)
        result.seen.append(key)

        wanted = catalog.get(key)
        if wanted is None:
            if site.ko is not None:
                result.stray.append(
                    f"{site.line}행: 소스에만 한국어가 있다 - {site.ko[:40]}"
                )
            continue

        if _slots(wanted) != _slots(site.en):
            result.bad_slots.append(
                f"{site.line}행: 보간 자리가 안 맞는다 - "
                f"영어 {sorted(_slots(site.en))} vs 한국어 {sorted(_slots(wanted))}"
            )
            continue

        # 삼항 자리는 `ko`가 늘 None이라 여기 안 걸린다. 이미 같은 값이 박힌
        # `Pick(de, en, ko)`만 건너뛴다.
        if site.ko == wanted:
            continue

        edits.append((site.start, site.end, _render(site, wanted, text)))
        result.applied.append(key)

    # 뒤에서부터 갈아 끼운다 - 앞을 먼저 고치면 뒤쪽 위치가 밀린다.
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]

    result.text = text
    return result


def uses_shorthand(text: str) -> bool:
    """`Loc.` 없이 `Pick(...)`을 부르는 한국어 자리가 있나."""
    return any(site.ko is not None and not site.qualifier for site in find_sites(text))


# --- 파일 ------------------------------------------------------------------


def source_files(root: Path = SOURCE_ROOT) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.cs"))
        if "obj" not in path.parts and "bin" not in path.parts
    ]


def _sweep(catalog: dict[tuple[str, str], str], root: Path) -> tuple[list[str], list[tuple[Path, str]], list[tuple[str, str]]]:
    """전 파일을 훑는다. (문제 목록, 바뀔 파일, 만난 쌍)."""
    problems: list[str] = []
    written: dict[Path, str] = {}
    seen: list[tuple[str, str]] = []
    original: dict[Path, str] = {}

    for path in source_files(root):
        before = path.read_text(encoding="utf-8")
        original[path] = before
        result = rewrite(before, catalog)
        seen += result.seen
        name = path.relative_to(root).as_posix()
        problems += [
            f"{name}:{line}"
            for line in result.stray + result.bad_slots + result.problems
        ]
        written[path] = result.text

    # 축약 선언은 **클래스에 하나**다. 파일마다 넣으면 partial 조각들이 같은
    # 멤버를 여러 번 선언한다. 그래서 트리를 다 훑은 다음 한 번만 손댄다.
    if any(uses_shorthand(text) for text in written.values()):
        if not any(declares_shorthand(text) for text in written.values()):
            anchors = [p for p, text in written.items() if ANCHOR in text]
            if not anchors:
                problems.append(
                    f"축약 `Pick`을 선언할 파일을 못 찾았다 - `{ANCHOR.strip()}`이 있는 파일이 없다"
                )
            else:
                fixed, problem = ensure_shorthand(written[anchors[0]])
                if problem is not None:
                    problems.append(f"{anchors[0].relative_to(root).as_posix()}: {problem}")
                else:
                    written[anchors[0]] = fixed

    changed = [(path, text) for path, text in written.items() if text != original[path]]
    return problems, changed, seen


def check(root: Path = SOURCE_ROOT, catalog_path: Path = CATALOG) -> list[str]:
    """소스가 카탈로그대로인지. 문제 목록을 돌려준다 - 비면 통과."""
    catalog = load_catalog(catalog_path)
    problems, changed, seen = _sweep(catalog, root)

    for path, _ in changed:
        problems.append(
            f"{path.relative_to(root).as_posix()}: 카탈로그와 다르다 - --write로 반영해라"
        )
    for de, en in orphans(catalog, seen):
        problems.append(
            f"카탈로그에 있는데 소스에 없다 - 업스트림이 고쳤을 수 있다: {en[:60]}"
        )
    return problems


# --- 한국어가 빠진 자리 ----------------------------------------------------
#
# `Loc.Pick`이 `LanguageMode.Korean => ko ?? en`이다(`Loc.cs:94-99`). 한국어
# 인자가 없으면 **예외도 로그도 없이 영어가 나간다.** 옮기는 동안에는 그게
# 맞았다 - 침묵보다 영어가 낫다. 옮기기가 끝난 지금은 그 폴백이 **빠진 자리를
# 덮는 뚜껑**이다.
#
# 실제로 `4 of 29`의 `of`가 그렇게 배포됐다. 현황판에 "지금은 영어로 나간다"고
# 적혀 있었는데도 나갔다 - **적어 두는 것으로는 안 막힌다.** 그래서 검사한다.


#: 한국어를 넣으면 **안 되는** 쌍. 여기 적힌 것만 통과한다.
#:
#: `von`/`of`는 세는 말이다. 모드가 자기가 찍은 문장을 다시 읽는다 -
#: `UIReaderService.TryParseSpokenProgress`가 `"3 von 48"`을 공백으로 셋으로
#: 쪼개 **가운데를 이 상수와 글자까지 비교해서** 토벌수첩 줄을 알아본다
#: (`UIReaderService.cs:8963`). 한국어는 수를 앞뒤로 바꿔 놓으므로(`48 중 3`)
#: 낱말만 갈면 그 비교가 어긋나고, **예외도 로그도 없이 그 기능만 죽는다.**
#: 낱말과 `Counter()`와 읽는 쪽이 한꺼번에 움직여야 하고, 그건 번역이 아니라
#: 코드 변경이다 - 현황판 `W-19`.
#:
#: **W-19가 끝나면 여기서 지운다.** 그때 이 표는 비고 검사는 예외 없이 0이 된다.
UNTRANSLATABLE = {
    ("von", "of"): "세는 말 - 모드가 자기 발화를 되읽어 파싱한다 (W-19)",
}


def gaps(text: str) -> list[str]:
    """한국어가 없어 영어가 나갈 자리. 소스 한 파일치를 행 번호와 함께.

    두 갈래를 통과시킨다.

    - **독일어와 영어가 글자까지 같은 자리.** 보간 자리뿐이라 언어가 안 걸린다
      (`AccessibilityStrings.cs`의 `TargetDirection`). 옮길 것이 없으니 빠진
      게 아니다 - 이건 판단이 아니라 계산이라 예외 표에 안 적는다
    - **`UNTRANSLATABLE`에 적힌 쌍.** 옮기면 기능이 깨지는 것들이고, 왜인지가
      그 표 위에 적혀 있다
    """
    problems: list[str] = []
    for site in find_sites(text):
        if site.ko is not None or site.de == site.en:
            continue
        if (site.de, site.en) in UNTRANSLATABLE:
            continue
        problems.append(f"{site.line}행: 한국어가 없어 영어로 나간다 - {site.en[:60]}")
    return problems


def missing_korean(root: Path = SOURCE_ROOT) -> list[str]:
    """트리 전체. 문제 목록을 돌려준다 - 비면 통과.

    **목표는 0이다.** 새 문장이 업스트림에서 오면 여기가 먼저 빨개지고, 옮기든
    예외로 적든 사람이 한 번은 본다.
    """
    problems: list[str] = []
    for path in source_files(root):
        name = path.relative_to(root).as_posix()
        problems += [
            f"{name}:{problem}" for problem in gaps(path.read_text(encoding="utf-8"))
        ]
    return problems


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def generated_commit(vendor: Path = VENDOR) -> str | None:
    """제목으로 생성 커밋을 찾는다. 없으면 None."""
    found = _git(
        "log", "--format=%H", "--fixed-strings", f"--grep={GENERATED_SUBJECT}",
        WORK_BRANCH, cwd=vendor,
    )
    if found.returncode != 0:
        return None
    heads = found.stdout.split()
    return heads[0] if heads else None


def tip_is_generated(vendor: Path = VENDOR, catalog_path: Path = CATALOG) -> list[str]:
    """생성 커밋이 정말 생성물인지 왕복으로 확인한다.

    이게 이 도구의 존재 이유를 지키는 검사다. **그 커밋을 손으로 고치는 순간
    여기가 빨개진다** - 손편집이 섞이면 다음 재생성 때 그 줄만 조용히 사라지고,
    사라진 게 한국어라 독일어·영어 검사에는 안 걸린다.

    부모 커밋(생성 전)을 임시 워크트리에 꺼내 생성기를 돌리고, 결과가 생성
    커밋과 같은지 파일 단위로 본다.

    **끝 커밋이라고 가정하지 않는다.** 도구가 못 읽는 모양은 손으로 쓴 별도
    커밋으로 그 뒤에 붙는다.
    """
    if not (vendor / ".git").exists():
        return []

    target = generated_commit(vendor)
    if target is None:
        return [f"생성 커밋을 못 찾았다 - 제목이 `{GENERATED_SUBJECT}`인 커밋이 없다"]

    catalog = load_catalog(catalog_path)
    workdir = Path(tempfile.mkdtemp(prefix="ko-apply-"))
    tree = workdir / "tree"
    try:
        added = _git("worktree", "add", "--detach", str(tree), f"{target}~1", cwd=vendor)
        if added.returncode != 0:
            return [f"임시 워크트리를 못 만들었다: {added.stderr.strip()}"]

        problems, changed, _ = _sweep(catalog, tree / SOURCE_NAME)
        made = {path: text for path, text in changed}

        for path in source_files(tree / SOURCE_NAME):
            relative = f"{SOURCE_NAME}/{path.relative_to(tree / SOURCE_NAME).as_posix()}"
            want = _git("show", f"{target}:{relative}", cwd=vendor)
            if want.returncode != 0:
                problems.append(f"{relative}: 생성 커밋에 없는 파일이다")
                continue
            got = made.get(path, path.read_text(encoding="utf-8"))
            if got.replace("\r\n", "\n") != want.stdout.replace("\r\n", "\n"):
                problems.append(
                    f"{relative}: 생성기가 만든 것과 생성 커밋이 다르다 - "
                    "그 커밋을 손으로 고쳤거나 생성기가 바뀌었다"
                )
        return problems
    finally:
        _git("worktree", "remove", "--force", str(tree), cwd=vendor)
        shutil.rmtree(workdir, ignore_errors=True)


def main(argv: list[str]) -> int:
    if not SOURCE_ROOT.is_dir():
        print(f"vendor 클론이 없다 - 건너뛴다: {SOURCE_ROOT}")
        return 0

    catalog = load_catalog()
    print(f"카탈로그: {len(catalog)}개")

    if "--write" not in argv:
        problems = check()
        if problems:
            print("\n소스가 카탈로그와 어긋난다:", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            return 1

        silent = missing_korean()
        if silent:
            print("\n한국어가 없어 영어로 나갈 자리:", file=sys.stderr)
            for problem in silent:
                print(f"  - {problem}", file=sys.stderr)
            return 1

        print("통과 - 소스가 카탈로그대로고, 한국어가 빠진 자리가 없다")
        return 0

    problems, changed, seen = _sweep(catalog, SOURCE_ROOT)
    if problems:
        print("\n먼저 볼 것이 있다:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    for path, text in changed:
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"  고침: {path.relative_to(SOURCE_ROOT).as_posix()}")

    print(f"{len(changed)}개 파일에 반영했다.")
    missing = orphans(catalog, seen)
    if missing:
        print("\n카탈로그에 있는데 소스에서 못 찾은 문장 "
              f"{len(missing)}개 - 업스트림이 고쳤을 수 있다:", file=sys.stderr)
        for _, en in missing:
            print(f"  {en[:70]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
