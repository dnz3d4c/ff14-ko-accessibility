"""문서가 인용한 사실을 산출물에서 다시 계산해 대조한다.

## 무엇을 막나

**문서가 조용히 낡는 것.** 커밋 훅의 C8은 `docs/status.md`를 *건드렸나*만 본다.
그래서 2026-08-18에 이렇게 됐다.

- `README.md`가 12커밋 동안 "한국어화는 아직 시작 전"이라고 적고 있었다.
  `[문서]` 갈래는 C8의 검사 대상이 아니고, README는 아예 어느 규칙의
  대상도 아니었다
- 현황판 §1이 "남은 것은 캐릭터 생성 하나"라고 적어 두고, 바로 아래 §2에
  P1이 셋 열려 있었다. 절끼리 어긋나는 것은 아무도 안 봤다
- `675쌍`·`C1~C8`·`40곳` 같은 숫자가 네 문서에 손으로 복사돼 있었고,
  원본이 바뀌어도 아무 일도 안 일어났다

## 방향을 뒤집는다

`tools/ko-words`와 같은 수법이다. 문서에 적힌 것을 지키는 게 아니라 **산출물에서
값을 다시 계산해** 문서와 대조한다. 문서를 고치는 사람이 잊어도 검사가 안다.

## 인용 자리가 사라지는 것도 실패다

정규식이 아무것도 못 찾으면 검사는 조용히 통과한다. **그게 제일 나쁜 실패다** -
문장을 고쳐 쓰다 인용 자리를 지웠는데 초록이면, 그날로 이 장치가 죽는다.
그래서 `찾은 자리가 정확히 하나`가 아니면 실패로 센다.

사용법:
    uv run --no-project python tools/docs-check/docs_check.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# 손 케이스 커밋을 읽는 헬퍼는 ko-words가 갖고 있다 - 같은 일을 두 번 만들지
# 않는다 (선례: tools/ko-apply가 strings_golden을 이렇게 가져다 쓴다).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ko-words"))

import ko_words  # noqa: E402 - 위에서 경로를 넣어야 찾는다

REPO = Path(__file__).resolve().parents[2]

BOARD = REPO / "docs" / "status.md"
GOLDEN = REPO / "tools" / "strings-golden" / "golden" / "de-en.json"
CATALOG = REPO / "overlay" / "ko" / "ko.json"
TERMS = REPO / "overlay" / "ko" / "terms.json"
LINT = REPO / "tools" / "commit-lint" / "commit_lint.py"
HAND_CASES_DOC = REPO / "docs" / "korean" / "hand-cases.md"
GUIDE_SKILL = ".claude/skills/ko-user-guide/SKILL.md"
LOC_SKILL = ".claude/skills/ko-localization/SKILL.md"

CONFIG_CS = REPO / "vendor" / "ff14-accessibility" / "FF14Accessibility" / "Configuration.cs"
INSTALLER_LOC = REPO / "vendor" / "ff14-accessibility" / "Installer" / "Loc.cs"

#: 설치 프로그램 사전의 언어 블록 머리와 그 안의 키. 블록은 `},`로 닫힌다 -
#: 키 줄은 그보다 깊게 들여쓰기되므로 이 경계로 언어끼리 안 섞인다.
_LOC_LANG = re.compile(
    r"^\s*\[(German|English|Korean)\]\s*=\s*new Dictionary<string, string>", re.M
)
_LOC_KEY = re.compile(r'^\s+\["(\w+)"\]\s*=', re.M)
_LOC_END = "\n        },"

#: 단축키 목록을 갖는 **하나뿐인** 문서. 배포물에 나가는 것이 이것이라 뺄 수
#: 없고, 다른 문서는 여기로 링크만 한다.
#:
#: 전에는 루트 README도 같은 목록을 갖고 있어서 이 상수가 둘이었고, `check_keys`가
#: 문서끼리 먼저 대조했다. W-65에서 README가 한국 서버 고유 내용만 갖게 되면서
#: 그 사본이 없어졌다 - 목록을 한 자리에 두는 것이 대조보다 먼저다.
KEY_DOC = "overlay/ko/README.ko.md"

_KEY_IN_SOURCE = re.compile(r"^\s*public string (Key\w+)\s*=", re.M)
_KEY_IN_DOC = re.compile(r"`(Key\w+)`")

#: 살아 있는 문서만 본다. 날짜가 박힌 기록(`frozen/ko-review-2026-08-18.md`)과
#: 동결한 조사 문서(`frozen/port-feasibility.md`)는 **그때 그대로가 맞다.**
#: 거기 숫자를 지금 값으로 맞추면 기록이 아니게 된다.


# ---------------------------------------------------------------- 사실 계산


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def hand_sites(repo: Path = REPO) -> int:
    """손으로 한국어를 넣은 자리. 손 케이스 커밋이 더한 줄 중 `IsKorean`이 있는 것.

    커밋을 못 찾으면 `ko_words.hand_commit`이 소리를 낸다 - 조용히 0을 세던
    패치 glob 시절의 함정이 여기 없다.
    """
    lines = ko_words.hand_lines(repo / "vendor" / "ff14-accessibility")
    return sum("IsKorean" in line for line in lines)


def lint_rule_max(path: Path = LINT) -> int:
    """커밋 검사기가 실제로 내는 규칙 코드의 최대값."""
    codes = [int(m) for m in re.findall(r'"C(\d+)"', path.read_text(encoding="utf-8"))]
    if not codes:
        raise ValueError(f"규칙 코드를 못 찾았다: {path}")
    return max(codes)


def hand_type_sum(path: Path = HAND_CASES_DOC) -> int:
    """`korean/hand-cases.md` 유형별 표의 합. 표 자신이 근거다."""
    text = path.read_text(encoding="utf-8")
    section = text.split("## 유형별", 1)
    if len(section) != 2:
        raise ValueError(f"`## 유형별` 절을 못 찾았다: {path}")
    body = section[1].split("## ", 1)[0]
    rows = re.findall(r"^\|[^|]+\|\s*(\d+)\s*\|", body, re.MULTILINE)
    if not rows:
        raise ValueError(f"유형별 표에서 개수를 못 읽었다: {path}")
    return sum(int(n) for n in rows)


def installer_loc_keys(path: Path = INSTALLER_LOC) -> dict[str, set[str]]:
    """설치 프로그램 사전의 언어별 키 이름.

    판이 이 사전을 `147키 중 한국어 92개`라고 적고 있었는데 실측은 189 대
    161이었다(2026-08-20). 그 자리가 `CITATIONS`에 없어서, 사전이 커지는
    동안 아무 일도 안 일어났고 거기서 파생된 `55키`까지 같이 죽었다.

    **모양이 바뀌면 조용히 0을 세지 않고 소리를 낸다.** 0은 판의 숫자와
    안 맞아 빨개지긴 하지만 원인이 "사전이 비었다"로 보여서, 고칠 곳을
    엉뚱하게 짚게 만든다.
    """
    text = path.read_text(encoding="utf-8")
    heads = [(m.group(1), m.end()) for m in _LOC_LANG.finditer(text)]
    if len(heads) != 3:
        raise ValueError(
            f"언어 블록 셋을 못 찾았다 ({len(heads)}개): {path}. "
            f"사전 모양이 바뀌었으면 `_LOC_LANG`도 같이 고쳐라"
        )

    found: dict[str, set[str]] = {}
    for i, (lang, begin) in enumerate(heads):
        end = heads[i + 1][1] if i + 1 < len(heads) else len(text)
        block = text[begin:end]
        cut = block.find(_LOC_END)
        if cut != -1:
            block = block[:cut]
        keys = set(_LOC_KEY.findall(block))
        if not keys:
            raise ValueError(f"{lang} 블록에서 키를 하나도 못 읽었다: {path}")
        found[lang] = keys
    return found


def guide_facts(repo: Path = REPO) -> dict[str, int]:
    """공식 가이드 코퍼스에서 센 값. `tools/ko-guide`가 원문에서 계산해 대장에 적는다.

    ko-user-guide 스킬이 "공식 가이드는 이렇게 쓴다"고 주장하는 근거가 전부
    여기 있다. 가이드가 개정되면 값이 움직이고, 그때 스킬이 빨개진다.
    """
    corpus = _json(repo / "tools" / "ko-guide" / "corpus.json")
    stats = corpus["stats"]
    kinds = stats["시각 의존 갈래"]
    quotes = _json(repo / "overlay" / "ko" / "guide-quotes.json")
    return {
        "가이드 문서": len(corpus["docs"]),
        "가이드 대분류": len(corpus["sections"]),
        "가이드 인용": len(quotes["quotes"]),
        "가이드 도입문": stats["도입문"],
        "가이드 보충 표기": stats["보충 표기"],
        "가이드 도해 라벨": stats["도해 라벨"],
        "가이드 습니다체": stats["습니다체 종결"],
        "가이드 한다체": stats["한다체 종결"],
        "가이드 가능형": stats["가능형"],
        "가이드 모험가님": stats["모험가님"],
        "가이드 UI 경로": stats["UI 경로"],
        "가이드 시각 의존": stats["시각 의존"],
        "가이드 시각 마우스": kinds["마우스"],
        "가이드 시각 위치": kinds["위치"],
        "가이드 시각 색": kinds["색"],
        "가이드 시각 모양": kinds["모양"],
        "가이드 시각 그림 참조": kinds["그림 참조"],
        "가이드 그림": stats["그림"],
        "가이드 대체 텍스트": stats["대체 텍스트 있는 그림"],
    }


def facts(repo: Path = REPO) -> dict[str, int]:
    golden = _json(repo / "tools" / "strings-golden" / "golden" / "de-en.json")
    loc = installer_loc_keys(
        repo / "vendor" / "ff14-accessibility" / "Installer" / "Loc.cs"
    )
    return {
        **guide_facts(repo),
        # 독일어가 원본이다. 한국어에만 있는 키는 있을 수 없으므로 전체 수는
        # 독일어 쪽이 갖는다.
        "설치 프로그램 키": len(loc["German"]),
        "설치 프로그램 한국어": len(loc["Korean"]),
        "설치 프로그램 미번역": len(loc["German"] - loc["Korean"]),
        "골든 쌍": golden["pairs"],
        # 같은 문장이 소스 여러 자리에 나오면 쌍은 여러 번 세지만 옮길 자리는
        # 하나다. 판이 "몇 자리를 옮겼나"를 적는 곳은 이쪽과 대조해야 한다 -
        # `689자리 중 687`이 2026-08-20까지 실측 어디와도 안 맞은 채 남아
        # 있었고, 원인은 그 자리가 `CITATIONS`에 없던 것이다.
        "골든 고유 쌍": len({tuple(p) for f in golden["by_file"].values() for p in f}),
        "골든 미해석": golden["unparsed"],
        "카탈로그 문장": len(_json(repo / "overlay" / "ko" / "ko.json")["strings"]),
        "대장 낱말": len(_json(repo / "overlay" / "ko" / "terms.json")["terms"]),
        "손으로 옮긴 자리": hand_sites(repo),
        "손으로 볼 자리": hand_type_sum(repo / "docs" / "korean" / "hand-cases.md"),
        "커밋 규칙 최대": lint_rule_max(repo / "tools" / "commit-lint" / "commit_lint.py"),
    }


# ---------------------------------------------------------------- 인용 대조

#: (문서, 사실 이름, 정규식). 정규식은 숫자 한 자리를 잡는 그룹이 하나여야 하고,
#: **문서에서 정확히 한 번** 걸려야 한다.
CITATIONS: tuple[tuple[str, str, str], ...] = (
    # 개발 안내는 저장소 설비를 적는 자리라 골든 쌍 같은 번역 수치는 안 적는다.
    # 그 값은 판(status.md)과 ko-localization 스킬, overlay/patches/README.md가
    # 갖는다. 이 문장은 2026-08-20까지 루트 `README.md` 7장에 있었고, 그 장이
    # 통째로 여기로 옮겨 왔다 - 경로를 같이 안 고쳤으면 검사가 그 자리에서 죽는다.
    ("docs/dev/README.md", "커밋 규칙 최대", r"규칙 C1~C(\d+)"),
    ("docs/dev/commit-rules.md", "커밋 규칙 최대", r"규칙 코드는 C1~C(\d+)"),
    ("docs/status.md", "골든 쌍", r"`AccessibilityStrings` 삼항 \| (\d+)쌍"),
    ("docs/status.md", "골든 고유 쌍", r"삼항 \| \d+쌍\(고유 (\d+)\)"),
    ("docs/status.md", "카탈로그 문장", r"→ \*\*(\d+)자리 옮김"),
    ("docs/status.md", "골든 쌍", r"문장을 한국어로 옮기기 \((\d+)쌍"),
    ("docs/status.md", "손으로 옮긴 자리", r"\+ 손 (\d+)곳\)"),
    ("docs/status.md", "손으로 볼 자리", r"복잡해 못 읽은 것 \| (\d+)곳 중"),
    ("docs/status.md", "대장 낱말", r"대장은 (\d+)개가 됐고"),
    # 설치 프로그램 사전. 2026-08-20까지 등록이 없어서 `147키 중 92개`가
    # 실측 189 대 161과 갈린 채 남아 있었고, 거기서 나온 `55키`도 같이 죽었다.
    ("docs/status.md", "설치 프로그램 키", r"\*\*(\d+)키 중 한국어"),
    ("docs/status.md", "설치 프로그램 한국어", r"키 중 한국어 (\d+)개\*\*"),
    ("docs/status.md", "설치 프로그램 미번역", r"(\d+)키가 아직 독일어"),
    # 한국어화 스킬. 2026-08-19까지 여기 한 자리도 없어서 숫자 넷이 낡은 채
    # 남았다 - 등록 안 한 인용은 아무도 안 지킨다.
    (LOC_SKILL, "골든 쌍", r"(\d+)문장이고, 결정은"),
    (LOC_SKILL, "골든 쌍", r"de-en\.json`에 (\d+)쌍"),
    (LOC_SKILL, "골든 쌍", r"(\d+)쌍을 한 자 단위로 대조"),
    (LOC_SKILL, "대장 낱말", r"지금 (\d+)개가 있다"),
    (LOC_SKILL, "손으로 볼 자리", r"손으로 봐야 하는 (\d+)곳"),
    ("overlay/patches/README.md", "골든 쌍", r"AccessibilityStrings\.cs`의 (\d+)쌍"),
    ("docs/korean/hand-cases.md", "골든 미해석", r"\*\*(\d+)\*\* \| 스냅샷 파서가 못 읽은"),
    ("docs/korean/hand-cases.md", "손으로 볼 자리", r"\*\*(\d+)\*\* \| 그중 진짜 손으로 볼"),
    ("docs/korean/hand-cases.md", "손으로 옮긴 자리", r"\*\*(\d+)\*\* \| 실제로 한국어를 넣은"),
    # 공식 가이드 코퍼스. 스킬이 대는 숫자는 전부 원문에서 다시 계산해 대조한다.
    (GUIDE_SKILL, "가이드 문서", r"원문 (\d+)건 \+ 대분류"),
    (GUIDE_SKILL, "가이드 대분류", r"\+ 대분류 (\d+)건"),
    (GUIDE_SKILL, "가이드 도입문", r"문서 (\d+)건이 빠짐없이"),
    (GUIDE_SKILL, "가이드 보충 표기", r"`※`로 시작한다\*\* \((\d+)회\)"),
    (GUIDE_SKILL, "가이드 도해 라벨", r"있지만 \((\d+)회\)"),
    (GUIDE_SKILL, "가이드 습니다체", r"`~습니다`가 ([\d,]+)회"),
    (GUIDE_SKILL, "가이드 한다체", r"`~된다`가 \*\*(\d+)\*\*회"),
    (GUIDE_SKILL, "가이드 가능형", r"`~할 수 있습니다` \((\d+)회\)"),
    (GUIDE_SKILL, "가이드 모험가님", r"`모험가님`을 쓰지만\((\d+)회\)"),
    (GUIDE_SKILL, "가이드 UI 경로", r"대괄호 쪽이 (\d+)회로"),
    (GUIDE_SKILL, "가이드 시각 의존", r"그런 자리가 (\d+)곳이다"),
    (GUIDE_SKILL, "가이드 시각 마우스", r"\| 마우스 조작 \| (\d+) \|"),
    (GUIDE_SKILL, "가이드 시각 위치", r"\| 위치 지시 \| (\d+) \|"),
    (GUIDE_SKILL, "가이드 시각 색", r"\| 색 구분 \| (\d+) \|"),
    (GUIDE_SKILL, "가이드 시각 모양", r"\| 아이콘 모양 \| (\d+) \|"),
    (GUIDE_SKILL, "가이드 시각 그림 참조", r"\| 그림 참조 \| (\d+) \|"),
    (GUIDE_SKILL, "가이드 그림", r"그림 (\d+)장을 싣는데"),
    (GUIDE_SKILL, "가이드 대체 텍스트", r"붙은 것은 (\d+)장\*\*"),
    ("docs/korean/guide-corpus.md", "가이드 문서", r"문서 (\d+)건을 받아"),
    ("docs/korean/guide-corpus.md", "가이드 대분류", r"대분류 랜딩 (\d+)건"),
    ("docs/korean/guide-corpus.md", "가이드 인용", r"지금 (\d+)줄이다"),
    ("docs/korean/guide-corpus.md", "가이드 시각 의존", r"(\d+)곳을 센다"),
)


def check_citations(repo: Path = REPO) -> list[str]:
    known = facts(repo)
    bad: list[str] = []

    for rel, name, pattern in CITATIONS:
        path = repo / rel
        if not path.is_file():
            bad.append(f"{rel}: 파일이 없다")
            continue
        hits = re.findall(pattern, path.read_text(encoding="utf-8"))
        if len(hits) != 1:
            bad.append(
                f"{rel}: `{name}`를 인용한 자리를 {len(hits)}번 찾았다 (1번이어야 한다). "
                f"문장을 고쳐 썼으면 CITATIONS의 정규식도 같이 고쳐라 - "
                f"안 고치면 이 검사가 조용히 죽는다"
            )
            continue
        # 천 단위 쉼표는 문서 쪽 표기다(`1,254회`). 값 비교에서는 걷어낸다.
        if int(hits[0].replace(",", "")) != known[name]:
            bad.append(
                f"{rel}: `{name}`가 {hits[0]}라고 적혀 있는데 실제는 {known[name]}이다"
            )

    # 손 케이스 세 숫자의 관계. 41(파서가 못 읽음) = 40(진짜 자리) + 1(Pick 헬퍼 선언)
    if known["손으로 볼 자리"] != known["골든 미해석"] - 1:
        bad.append(
            f"손 케이스 유형별 표의 합이 {known['손으로 볼 자리']}인데 "
            f"골든 미해석은 {known['골든 미해석']}이다. "
            f"둘의 차는 `Pick` 헬퍼 선언 하나여야 한다 - "
            f"업스트림이 새 모양을 들여왔으면 표를 늘려라"
        )

    return bad


# -------------------------------------------------------------- 현황판 정합

_ROW = re.compile(r"^\|\s*(W-\d+)\s*\|(.+?)\|\s*(P\d)\s*\|\s*(\S+)\s*\|")
_OPEN = ("대기", "진행")

#: §2 표가 쓸 수 있는 상태값 전부. **동의어를 열어 두면 규약이 조용히
#: 우회된다** - `완료`는 §9로 옮기라고 아래에서 막는데, `끝`이라고 적으면
#: 그 검사도 `_OPEN` 검사도 안 걸리고 표에 남는다. 값을 늘릴 때는 §8의
#: 규약을 먼저 고친다.
BOARD_STATES = ("대기", "진행", "막힘", "버림", "완료")

#: 판의 절 제목. **절을 재편하면 여기부터 고친다.** 문자열 비교라 파일이
#: 바뀌어도 저절로는 안 걸리므로, `_section`이 "못 찾음"을 실패로 센다.
OPEN_HEADING = "## 2. 열린 작업"
DONE_HEADING = "## 7. 끝난 것"

#: §7이 ID를 닫는 자리. **여는 괄호 바로 뒤만 본다.**
#:
#: 절 전체에서 `W-\d+`를 긁으면 산문에 스쳐 지나간 ID까지 "닫힌 것"으로 세고,
#: 그러면 열린 일이 완료 목록 안에 숨어도 결번 검사가 통과한다 - W-35가 실제로
#: 그렇게 묻혔다(§4-6). 줄 끝 `)`로 고정하는 것도 안 된다: 항목이 마크다운
#: 링크로 끝나면 `)`가 하나 더 붙어서 열아홉 줄이 통째로 안 잡힌다.
_DONE_ID = re.compile(r"\(W-\d+(?:[·,]\s*W-\d+)*")


def _section(text: str, heading: str) -> str:
    """`heading` 아래부터 다음 `## `까지. **못 찾으면 실패다.**

    `split(...)[-1]`을 쓰면 안 된다 - 구분자가 없을 때 문서 전체를 돌려주고,
    그러면 결번 검사가 §2의 ID를 전부 "닫힌 것"으로 센다. 오류 없이 영원히
    통과하는 실패라, 이 도구가 막으려던 바로 그 모양이다.
    """
    if heading not in text:
        raise ValueError(f"판에서 `{heading}` 절을 못 찾았다. 절을 재편했으면 상수도 같이 고쳐라")
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def board_rows(text: str) -> list[tuple[str, str, str]]:
    """§2 표. (ID, 우선순위, 상태)."""
    section = _section(text, OPEN_HEADING)
    return [(m[1], m[3], m[4]) for m in (_ROW.match(line) for line in section.splitlines()) if m]


def done_ids(text: str) -> set[str]:
    """§7이 닫았다고 말하는 ID."""
    found: set[str] = set()
    for line in _section(text, DONE_HEADING).splitlines():
        if line.startswith("- ") and (m := _DONE_ID.search(line)):
            found.update(re.findall(r"W-\d+", m.group(0)))
    return found


def _line(text: str, prefix: str) -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line
    return ""


def check_board(path: Path = BOARD) -> list[str]:
    text = path.read_text(encoding="utf-8")
    rows = board_rows(text)
    bad: list[str] = []

    if not rows:
        return ["docs/status.md: §2 표를 못 읽었다"]

    ids = [row[0] for row in rows]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        bad.append(f"§2에 같은 ID가 두 번 있다: {', '.join(dup)}")

    # 아래 `완료` 검사가 §9로 옮기라고 막는데, 같은 뜻을 다른 낱말로 적으면
    # 그 검사도 `_OPEN` 검사도 안 걸린다. 값 자체를 막는다.
    unknown = [(i, s) for i, _, s in rows if s not in BOARD_STATES]
    if unknown:
        bad.append(
            "§2에 모르는 상태값이 있다: "
            + ", ".join(f"{i}({s})" for i, s in unknown)
            + f". 쓸 수 있는 것은 {', '.join(BOARD_STATES)}뿐이다 - "
            f"동의어를 쓰면 규약이 조용히 우회된다"
        )

    done_in_table = [i for i, _, state in rows if state == "완료"]
    if done_in_table:
        bad.append(
            f"§2에 `완료`가 남아 있다: {', '.join(done_in_table)}. "
            f"§8대로 표에서 지우고 §9에 한 줄로 옮겨라"
        )

    grades = [p for _, p, _ in rows]
    if grades != sorted(grades):
        bad.append(f"§2가 우선순위 순이 아니다: {' '.join(grades)}")

    # §1 "다음"은 열린 것 중 제일 높은 등급을 전부 덮어야 한다.
    open_rows = [(i, p) for i, p, s in rows if s in _OPEN]
    if open_rows:
        top = min(p for _, p in open_rows)
        must = {i for i, p in open_rows if p == top}
        named = set(re.findall(r"W-\d+", _line(text, "- 다음:")))
        missing = sorted(must - named)
        if missing:
            bad.append(
                f"§1 '다음'이 §2의 최상위 등급({top})을 빠뜨렸다: {', '.join(missing)}"
            )
        stray = sorted(named - set(ids))
        if stray:
            bad.append(f"§1 '다음'이 §2에 없는 ID를 가리킨다: {', '.join(stray)}")

    # §1 "막힘"에 적은 것은 §2에서도 막힘이어야 한다.
    state_of = {i: s for i, _, s in rows}
    for wid in re.findall(r"W-\d+", _line(text, "- 막힘:")):
        if state_of.get(wid) != "막힘":
            bad.append(
                f"§1이 {wid}를 막힘이라고 적었는데 §2 상태는 `{state_of.get(wid, '없음')}`이다"
            )

    # ID가 조용히 사라지지 않았나. §2 ∪ §7이 W-01..W-max를 전부 덮어야 한다.
    done = done_ids(text)
    have = set(ids) | done
    top_num = max(int(i.split("-")[1]) for i in have)
    lost = [f"W-{n:02d}" for n in range(1, top_num + 1) if f"W-{n:02d}" not in have]
    if lost:
        bad.append(f"§2에도 §7에도 없는 ID: {', '.join(lost)}. ID는 재사용하지 않는다")

    # 한 ID가 양쪽에 닫혀 있으면 §2만 읽는 사람과 §7만 읽는 사람이 다른 답을
    # 듣는다. 마일스톤이 끝났어도 §2에 남았으면 §7에서 괄호로 닫지 않는다(§8).
    both = sorted(set(ids) & done)
    if both:
        bad.append(
            f"§2에 열려 있는데 §7이 닫았다고 적은 ID: {', '.join(both)}. "
            f"§8대로 §7에서는 괄호를 빼고 `남은 것은 §2 W-NN`으로 가리켜라"
        )

    return bad


# --------------------------------------------------------------- 단축키 대조


def source_keys() -> set[str] | None:
    """`Configuration.cs`가 선언한 키 설정 이름. vendor가 없으면 `None`."""
    if not CONFIG_CS.is_file():
        return None
    return set(_KEY_IN_SOURCE.findall(CONFIG_CS.read_text(encoding="utf-8")))


def doc_keys(rel: str) -> set[str]:
    """문서가 백틱으로 적어 둔 키 설정 이름."""
    return set(_KEY_IN_DOC.findall((REPO / rel).read_text(encoding="utf-8")))


def check_keys() -> list[str]:
    """키 목록이 소스와 어긋나는 자리.

    전에는 소스보다 **문서끼리** 먼저 봤다. 목록이 두 벌이었고 갈라지는 것이 제일
    흔한 사고였기 때문이다(W-04). 사본이 없어진 지금 그 대조는 **약해진 것이 아니라
    상대가 없어 성립하지 않는다** - 목록이 한 벌이면 갈라질 두 벌이 없다. 다시
    두 벌이 되면 그때 이 함수가 아니라 `KEY_DOC`이 먼저 늘어난다.

    소스를 못 보면(권한 없이 클론해 vendor가 없는 경우) 볼 것이 남지 않는다.
    """
    src = source_keys()
    if src is None:
        return []  # vendor를 못 받은 상태. 다른 검사와 같은 규약으로 건너뛴다

    names = doc_keys(KEY_DOC)
    bad = [f"{name}: `{KEY_DOC}`에 있는데 `Configuration.cs`에 없다"
           for name in sorted(names - src)]
    bad += [f"{name}: `Configuration.cs`에 있는데 `{KEY_DOC}`에 없다"
            for name in sorted(src - names)]
    return bad


# ------------------------------------------------------------- 문서 위생

#: 마크다운에 있으면 안 되는 제어 문자. 탭(`0x09`)·줄바꿈(`0x0A`)·복귀(`0x0D`)는
#: 뺀다. 나머지는 **화면에 아무것도 안 그리면서** diff·검색·스크린리더를
#: 어긋나게 한다 - 눈으로 봐서는 절대 못 찾는 부류다.
_CONTROL = re.compile(r"[\x00-\x08\x0B\x0C]")

#: 마크다운 링크. 앵커(`#...`)는 대상에서 뗀다.
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)#]+?)(?:#[^)]*)?\)")

#: 산출물이 움직였는데 문서에 남은 옛 값. `(사실 이름, 옛값)`.
#:
#: `CITATIONS`는 **등록한 자리 하나**만 본다. 같은 숫자가 산문 여기저기에
#: 흩어져 있으면 거기까지는 안 간다 - `688`이 실제로 그렇게 세 자리에 남아
#: 지금 값 691과 갈렸다. 값이 움직이면 여기 옛 값을 적는다.
RETIRED_VALUES = (("골든 쌍", "688"), ("골든 쌍", "691"))

#: 폐기값을 안 보는 자리. 날짜가 박힌 기록과 동결 문서는 **그때 그대로가
#: 맞다**(`CLAUDE.md`의 현황판 규약). `docs/status.md`는 §7(끝난 것)만 뺀다.
RETIRED_SKIP = ("docs/frozen/", "docs/upstream/changes.md")


def living_docs(repo: Path = REPO) -> list[Path]:
    """살아 있는 문서. `docs/` 아래 마크다운 전부."""
    return sorted((repo / "docs").rglob("*.md"))


def check_control_chars(repo: Path = REPO) -> list[str]:
    """제어 문자가 섞였나. 눈으로는 못 찾고 검색·비교만 조용히 어긋난다."""
    bad = []
    for path in living_docs(repo):
        text = path.read_text(encoding="utf-8")
        for match in _CONTROL.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            bad.append(
                f"{path.relative_to(repo).as_posix()}:{line}: "
                f"제어 문자 {hex(ord(match.group(0)))}가 있다. 화면에 안 보이면서 "
                f"검색과 비교를 어긋나게 한다"
            )
    return bad


def check_link_names(repo: Path = REPO) -> list[str]:
    """링크 글자가 파일 이름인데 실제 대상과 다른 자리.

    문서를 옮기면 대상 경로는 고치는데 **글자는 안 고친다.** 그러면 링크는
    멀쩡히 열리면서 본문은 없는 파일 이름을 부르고, 그 이름으로 검색하는
    사람은 아무것도 못 찾는다.
    """
    bad = []
    for path in living_docs(repo):
        rel = path.relative_to(repo).as_posix()
        for text, target in _MD_LINK.findall(path.read_text(encoding="utf-8")):
            label = text.strip()
            if not label.endswith(".md") or target.startswith(("http", "mailto")):
                continue
            if Path(label).name != Path(target).name:
                bad.append(
                    f"{rel}: 링크 글자가 `{label}`인데 가리키는 것은 `{target}`이다. "
                    f"글자를 대상 이름으로 고쳐라"
                )
    return bad


def check_retired(repo: Path = REPO) -> list[str]:
    """폐기된 값이 살아 있는 문서에 남아 있나."""
    bad = []
    for name, old in RETIRED_VALUES:
        # 앞뒤에 숫자나 쉼표가 붙은 것은 다른 수다(`46,688색`).
        pattern = re.compile(rf"(?<![\d,]){re.escape(old)}(?![\d])")
        for path in living_docs(repo):
            rel = path.relative_to(repo).as_posix()
            if any(rel.startswith(skip) for skip in RETIRED_SKIP):
                continue

            text = path.read_text(encoding="utf-8")
            if rel == "docs/status.md":
                text = text.split(DONE_HEADING, 1)[0]  # 이력은 그때 그대로다

            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                bad.append(
                    f"{rel}:{line}: 폐기된 값 `{old}`이 남아 있다(`{name}`). "
                    f"지금 값으로 고쳐라"
                )
    return bad


# ------------------------------------------------------------------- 실행


def main(argv: list[str]) -> int:
    bad = (
        check_citations()
        + check_board()
        + check_keys()
        + check_control_chars()
        + check_link_names()
        + check_retired()
    )
    if bad:
        print("문서가 실제와 어긋난다:", file=sys.stderr)
        for item in bad:
            print(f"  {item}", file=sys.stderr)
        return 1

    keys = doc_keys(KEY_DOC)
    print(f"통과 - 인용 {len(CITATIONS)}자리, 현황판 정합, 단축키 {len(keys)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
