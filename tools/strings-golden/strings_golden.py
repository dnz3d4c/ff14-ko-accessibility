"""한국어화 전에 독일어·영어가 뭐라고 말하는지 찍어 둔다.

번역은 `IsGerman ? "독일어" : "영어"` 삼항 **722곳**을 카탈로그로 옮기는
작업이다(2026-08-18 실측). 기계적이지만 그래서 위험하다 - 옮기다 한 문장을
떨어뜨리거나 바꿔도 **컴파일은 통과한다.** 독일어 사용자는 그걸 다음 릴리스에
귀로 알게 된다.

그걸 막으려면 옮기기 **전에** 원본을 찍어 둬야 한다. 이 도구가 그 스냅샷이고,
`golden/de-en.json`이 그 결과다. 옮긴 뒤에도 독일어·영어 문장이 한 자도
안 바뀐 것을 이 파일로 증명한다.

**못 읽은 것을 숨기지 않는다.** 단순 삼항이 아닌 것(데이터 주도, 중첩 삼항)의
개수도 같이 기록한다. 개수가 늘면 새 형태가 생긴 것이니 손으로 본다.

지금 41개 중 하나는 진짜 문장이 아니다 - `AccessibilityStrings.Pick` 축약이
`Loc.Pick(de, en, ko)`로 넘기는 줄이고, 인자가 문자열이 아니라 변수라서
못 읽는다. 나머지 40개가 실제로 손으로 옮길 자리다(docs/ko-hand-cases.md).

사용법:
    uv run --no-project python tools/strings-golden/strings_golden.py          # 대조
    uv run --no-project python tools/strings-golden/strings_golden.py --write  # 갱신
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO / "vendor" / "ff14-accessibility" / "FF14Accessibility"
GOLDEN = Path(__file__).resolve().parent / "golden" / "de-en.json"

MARKER = "IsGerman"

#: 번역하면서 삼항이 이 모양으로 바뀐다. 옮긴 줄도 같은 쌍을 내야 스냅샷이
#: "문장이 사라졌다"고 하지 않는다. 앞 글자를 보고 PickItem 같은 이름은 거른다.
PICK = "Pick("
_IDENT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


@dataclass(frozen=True)
class Pair:
    de: str
    en: str


@dataclass(frozen=True)
class Unparsed:
    file: str
    line: int
    snippet: str


NEWLINE = '\n'


def strip_comments(text: str) -> str:
    """주석을 같은 길이의 공백으로 지운다.

    주석에 `IsGerman ? de : en` 같은 **예시**를 적어 두면 검사기가 그걸 코드로
    읽어 미해석 개수를 부풀린다. 개수가 곧 신호라서, 가짜로 늘면 진짜 증가를
    못 본다.

    길이를 유지하는 이유는 줄 번호와 위치를 안 흔들기 위해서다. 문자열 안의
    `//`(URL 같은 것)는 주석이 아니므로 문자열도 같이 따라가며 읽는다.
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            # 문자열은 통째로 건너뛴다 - 안에 //가 있어도 주석이 아니다.
            i += 1
            while i < n:
                if text[i] == chr(92) and i + 1 < n:
                    i += 2
                    continue
                if text[i] == '"' or text[i] == NEWLINE:
                    i += 1
                    break
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != NEWLINE:
                out[i] = " "
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                if text[i] != NEWLINE:
                    out[i] = " "
                i += 1
            for _ in range(2):
                if i < n:
                    out[i] = " "
                    i += 1
            continue
        i += 1
    return "".join(out)


def _read_literal(text: str, i: int) -> tuple[str | None, int]:
    """`i`에서 시작하는 C# 문자열 리터럴을 읽는다. (내용, 끝위치+1).

    `$` 접두는 삼켜서 없는 것처럼 다룬다 - 보간 자리(`{item}`)는 내용 그대로
    남긴다. 그게 곧 번역할 때 지켜야 할 자리이기 때문이다.

    축자 문자열(`@"..."`)은 읽지 않는다. 만나면 None을 돌려 미해석으로 센다.
    """
    if i < len(text) and text[i] == "$":
        i += 1
    if i >= len(text) or text[i] != '"':
        return None, i
    if i > 0 and text[i - 1] == "@":
        return None, i

    i += 1
    out: list[str] = []
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            out.append(text[i : i + 2])
            i += 2
            continue
        if ch == '"':
            return "".join(out), i + 1
        if ch == "\n":
            return None, i
        out.append(ch)
        i += 1
    return None, i


def _skip_space(text: str, i: int) -> int:
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    return i


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _extract_pick(text: str, name: str) -> tuple[list[Pair], list[Unparsed]]:
    """`Pick(독일어, 영어[, 한국어])` 호출에서 쌍을 뽑는다."""
    pairs: list[Pair] = []
    missed: list[Unparsed] = []

    start = 0
    while True:
        found = text.find(PICK, start)
        if found < 0:
            break
        start = found + len(PICK)

        # `PickItem(` 같은 다른 이름을 거른다. 앞 글자가 식별자면 우리 게 아니다.
        before = text[found - 1] if found > 0 else ""
        if before in _IDENT:
            continue

        i = _skip_space(text, start)
        de, i = _read_literal(text, i)
        if de is None:
            # 선언(`Pick(string de, ...)`)은 호출이 아니다. 첫 인자가 문자열이
            # 아니면서 타입 이름으로 시작하면 그냥 넘긴다 - 미해석으로 세면
            # 개수가 영원히 부풀어 있다.
            if text[i : i + 7] == "string ":
                continue
            missed.append(Unparsed(name, _line_of(text, found),
                                   text[found : found + 60].replace("\n", " ")))
            continue

        i = _skip_space(text, i)
        if i >= len(text) or text[i] != ",":
            missed.append(Unparsed(name, _line_of(text, found),
                                   text[found : found + 60].replace("\n", " ")))
            continue

        i = _skip_space(text, i + 1)
        en, i = _read_literal(text, i)
        if en is None:
            missed.append(Unparsed(name, _line_of(text, found),
                                   text[found : found + 60].replace("\n", " ")))
            continue

        # 한국어가 뒤에 붙어 있어도 독일어/영어 쌍은 그대로다. 세 번째 인자는 안 본다.
        pairs.append(Pair(de, en))

    return pairs, missed


def extract(text: str, name: str) -> tuple[list[Pair], list[Unparsed]]:
    """한 파일에서 (독일어, 영어) 쌍과 못 읽은 자리를 뽑는다.

    두 모양을 읽는다 - 아직 안 옮긴 `IsGerman ? de : en`과, 옮긴
    `Pick(de, en, ko)`. 둘이 같은 쌍을 내므로 옮기는 동안 스냅샷이 안 흔들린다.
    """
    text = strip_comments(text)
    pairs: list[Pair] = []
    missed: list[Unparsed] = []

    start = 0
    while True:
        found = text.find(MARKER, start)
        if found < 0:
            break
        start = found + len(MARKER)

        i = _skip_space(text, start)
        if i >= len(text) or text[i] != "?":
            # 삼항이 아니다 - 선언, 주석, `=> Loc.IsGerman` 같은 것.
            continue

        i = _skip_space(text, i + 1)
        de, i = _read_literal(text, i)
        if de is None:
            missed.append(Unparsed(name, text.count("\n", 0, found) + 1,
                                   text[found : found + 60].replace("\n", " ")))
            continue

        i = _skip_space(text, i)
        if i >= len(text) or text[i] != ":":
            missed.append(Unparsed(name, text.count("\n", 0, found) + 1,
                                   text[found : found + 60].replace("\n", " ")))
            continue

        i = _skip_space(text, i + 1)
        en, i = _read_literal(text, i)
        if en is None:
            missed.append(Unparsed(name, text.count("\n", 0, found) + 1,
                                   text[found : found + 60].replace("\n", " ")))
            continue

        pairs.append(Pair(de, en))

    pick_pairs, pick_missed = _extract_pick(text, name)
    pairs.extend(pick_pairs)
    missed.extend(pick_missed)

    return pairs, missed


def scan(root: Path = SOURCE_ROOT) -> tuple[dict[str, list[list[str]]], list[Unparsed]]:
    """소스 전체를 훑는다. 파일별로 정렬된 쌍 목록과 미해석 목록."""
    by_file: dict[str, list[list[str]]] = {}
    missed: list[Unparsed] = []

    for path in sorted(root.rglob("*.cs")):
        if "obj" in path.parts or "bin" in path.parts:
            continue
        name = path.relative_to(root).as_posix()
        pairs, file_missed = extract(path.read_text(encoding="utf-8"), name)
        missed.extend(file_missed)
        if pairs:
            # 줄 번호를 안 넣는다. 무관한 편집마다 골든이 흔들리면 아무도 안 본다.
            by_file[name] = sorted([p.de, p.en] for p in pairs)

    return by_file, missed


def build(root: Path = SOURCE_ROOT) -> dict:
    by_file, missed = scan(root)
    return {
        "note": "한국어화 전 독일어/영어 스냅샷. 옮긴 뒤에도 이게 그대로여야 한다.",
        "pairs": sum(len(v) for v in by_file.values()),
        "unparsed": len(missed),
        "by_file": by_file,
    }


def main(argv: list[str]) -> int:
    if not SOURCE_ROOT.is_dir():
        print(f"vendor 클론이 없다 - 건너뛴다: {SOURCE_ROOT}")
        return 0

    current = build()
    _, missed = scan()

    if "--write" in argv:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(
            json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"기록: {GOLDEN.relative_to(REPO).as_posix()}")
        print(f"  쌍 {current['pairs']}개, 미해석 {current['unparsed']}개")
        if missed:
            print("\n미해석 - 손으로 옮길 자리다:")
            for item in missed:
                print(f"  {item.file}:{item.line}  {item.snippet}")
        return 0

    if not GOLDEN.is_file():
        print(f"골든이 없다. 먼저 --write로 만든다: {GOLDEN}", file=sys.stderr)
        return 2

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    if golden.get("by_file") == current["by_file"]:
        print(f"통과 - 독일어/영어 {current['pairs']}개가 스냅샷 그대로다")
        return 0

    print("독일어/영어 문장이 스냅샷과 다르다:", file=sys.stderr)
    gone: list[list[str]] = []
    fresh: list[list[str]] = []
    for name in sorted(set(golden["by_file"]) | set(current["by_file"])):
        was = golden["by_file"].get(name, [])
        now = current["by_file"].get(name, [])
        if was == now:
            continue
        removed = [p for p in was if p not in now]
        added = [p for p in now if p not in was]
        gone.extend(removed)
        fresh.extend(added)
        print(f"  {name}: {len(was)}개 -> {len(now)}개", file=sys.stderr)
        for pair in removed[:3]:
            print(f"    사라짐: {pair[0][:50]}", file=sys.stderr)
        for pair in added[:3]:
            print(f"    새로:   {pair[0][:50]}", file=sys.stderr)

    # 두 경우를 구분한다. 업스트림을 올린 직후에는 문장이 **늘기만** 하는 게
    # 정상이고, 그때 갱신은 안전하다. 사라진 게 있으면 그건 다른 사건이다 -
    # 우리가 옮기다 떨어뜨렸거나 업스트림이 문장을 고친 것이고, 둘 다
    # 갱신하기 전에 봐야 한다.
    print("", file=sys.stderr)
    if not gone:
        print(
            f"사라진 문장 없음 / 새 문장 {len(fresh)}개. 업스트림이 더한 것뿐이라면 "
            "--write로 갱신해도 기존 문장은 안 바뀐다.",
            file=sys.stderr,
        )
        print("새로 늘어난 만큼 한국어 번역이 밀린다 - docs/upstream-sync.md §7.", file=sys.stderr)
    else:
        print(
            f"사라진 문장 {len(gone)}개. 업스트림을 올린 게 아니라면 옮기다 "
            "떨어뜨린 것이다 - 갱신하기 전에 그 줄을 찾아라.",
            file=sys.stderr,
        )
    print("의도한 변경이면 --write로 갱신하고, 왜 바뀌는지 커밋에 적어라.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
