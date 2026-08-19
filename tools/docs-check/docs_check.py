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
    return {
        **guide_facts(repo),
        "골든 쌍": golden["pairs"],
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
    # 루트 README는 프로젝트 소개라 골든 쌍 같은 내부 수치를 안 적는다. 그 값은
    # 판(status.md)과 ko-localization 스킬, overlay/patches/README.md가 갖는다.
    ("README.md", "커밋 규칙 최대", r"규칙 C1~C(\d+)"),
    ("docs/dev/commit-rules.md", "커밋 규칙 최대", r"규칙 코드는 C1~C(\d+)"),
    ("docs/status.md", "골든 쌍", r"`AccessibilityStrings` 삼항 \| (\d+)쌍"),
    ("docs/status.md", "골든 쌍", r"문장을 한국어로 옮기기 \((\d+)쌍"),
    ("docs/status.md", "손으로 옮긴 자리", r"\+ 손 (\d+)곳\)"),
    ("docs/status.md", "손으로 볼 자리", r"복잡해 못 읽은 것 \| (\d+)곳 중"),
    ("docs/status.md", "대장 낱말", r"대장은 (\d+)개가 됐고"),
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
    (GUIDE_SKILL, "가이드 모험가님", r"아예 없다\*\* \((\d+)회\)"),
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


def board_rows(text: str) -> list[tuple[str, str, str]]:
    """§2 표. (ID, 우선순위, 상태)."""
    section = text.split("## 2. 열린 작업", 1)[1].split("\n## ", 1)[0]
    return [(m[1], m[3], m[4]) for m in (_ROW.match(line) for line in section.splitlines()) if m]


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

    # ID가 조용히 사라지지 않았나. §2 ∪ §9가 W-01..W-max를 전부 덮어야 한다.
    done = set(re.findall(r"W-\d+", text.split("## 9. 끝난 것", 1)[-1]))
    have = set(ids) | done
    top_num = max(int(i.split("-")[1]) for i in have)
    lost = [f"W-{n:02d}" for n in range(1, top_num + 1) if f"W-{n:02d}" not in have]
    if lost:
        bad.append(f"§2에도 §9에도 없는 ID: {', '.join(lost)}. ID는 재사용하지 않는다")

    return bad


# ------------------------------------------------------------------- 실행


def main(argv: list[str]) -> int:
    bad = check_citations() + check_board()
    if bad:
        print("문서가 실제와 어긋난다:", file=sys.stderr)
        for item in bad:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"통과 - 인용 {len(CITATIONS)}자리와 현황판 정합")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
