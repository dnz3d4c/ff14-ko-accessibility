"""번역이 쓰는 낱말 중 게임에 없는 것을 골라내 고정한다.

## 무엇을 막나

**게임이 안 쓰는 낱말을 그럴듯해서 쓰는 것.** 대장(`overlay/ko/terms.json`)이
같은 사고를 막으라고 있지만, 대장은 "적어 둔 낱말"만 본다 - 적기를 잊으면
아무 일도 안 일어난다. 실제로 그렇게 됐다. 대장이 28줄일 때 번역은 그 두 배가
넘는 게임 낱말을 쓰고 있었고, 그중 여섯이 게임에 아예 없는 말이었다
(`장판`·`손패`·`방위`·`월드`·`훈련장`·`우편함`).

그래서 반대 방향에서 본다. 번역이 실제로 쓰는 낱말을 전부 모아 KR Addon
덤프에 없는 것을 골라내고, **그 목록 자체를 골든으로 고정한다.** 새 낱말이
말없이 들어오면 빨개진다.

## 0건이 곧 잘못은 아니다

모드가 지어야 하는 말이 있다 - `길안내`·`발자취`·`경유지` 같은 것은 게임에
없는 개념이라 게임 시트에 있을 리가 없다. 그래서 이 검사는 "0건 금지"가
아니라 **"0건 목록이 조용히 늘지 않는다"**이다. 새로 늘었으면 둘 중 하나고,
어느 쪽인지는 사람이 정한다.

- 게임 낱말을 잘못 지어냈다 → 고친다
- 모드가 지어야 하는 말이 새로 생겼다 → `--write`로 갱신하고 **커밋 본문에
  왜인지 적는다**. 조용히 갱신하면 이 장치는 그날로 죽는다

## 어디를 보나

`overlay/ko/ko.json`의 한국어와, 생성기가 못 읽어 손으로 쓴 자리(`kr-port`
브랜치의 손 케이스 커밋)가 더한 줄. 손 케이스도 봐야 한다 - `월드`가 거기
있었다.

사용법:
    uv run --no-project python tools/ko-words/ko_words.py           # 대조
    uv run --no-project python tools/ko-words/ko_words.py --write   # 골든 갱신
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CATALOG = REPO / "overlay" / "ko" / "ko.json"
TERMS = REPO / "overlay" / "ko" / "terms.json"
VENDOR = REPO / "vendor" / "ff14-accessibility"
DUMP = REPO / "tools" / "ko-terms" / "out" / "addon-Korean.tsv"
GOLDEN = Path(__file__).resolve().parent / "golden" / "mod-words.json"

#: 손 케이스 커밋이 앉아 있는 브랜치.
WORK_BRANCH = "kr-port"

#: 손 케이스 커밋을 **제목으로** 찾는다 - `tools/ko-apply`가 생성 커밋을 찾는
#: 수법 그대로다. 제목의 줄 수("the 36 lines")는 손 케이스가 늘면 움직이므로,
#: 안 움직이는 꼬리만 건다.
HAND_SUBJECT = "lines the generator cannot reach"

#: 한 글자는 조사·의존명사라 신호가 없다.
TOKEN = re.compile(r"[가-힣]{2,}")

#: 낱말에 붙은 조사. **떼어 낸 나머지가 게임에 있을 때만** 떼어낸 것으로 친다 -
#: 그래서 `소지품에`는 `소지품`으로 잡히고 `장판`은 아무것도 못 떼어 그대로 남는다.
#: 긴 것부터 본다: `에게`를 `에`로 먼저 자르면 `누구에`가 남는다.
PARTICLES = (
    "에서는", "에게서", "으로는", "이라는", "이라고", "에게는", "까지는",
    "에서", "에게", "으로", "이라", "부터", "까지", "보다", "처럼", "마다",
    "한테", "밖에", "조차", "이나", "이란", "라는", "라고",
    "은", "는", "이", "가", "을", "를", "에", "와", "과", "의", "도", "만",
    "로", "나", "야", "아", "뿐", "께",
)


def tokens(text: str) -> set[str]:
    """한국어 낱말. 보간 자리·영문·숫자는 이 검사 대상이 아니다."""
    return set(TOKEN.findall(text))


def load_dump(path: Path = DUMP) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30,
    )


def hand_commit(vendor: Path = VENDOR) -> str:
    """제목으로 손 케이스 커밋을 찾는다. 못 찾으면 소리를 낸다.

    패치 glob 시절에는 이름이 바뀌면 조용히 0줄을 읽었다. 같은 실패 모드를
    남기지 않으려고, 제목이 바뀌어도 침묵 대신 예외다.
    """
    found = _git(
        "log", "--format=%H", "--fixed-strings", f"--grep={HAND_SUBJECT}",
        WORK_BRANCH, cwd=vendor,
    )
    if found.returncode != 0:
        raise LookupError(
            f"{vendor}에서 {WORK_BRANCH}를 못 읽었다: {found.stderr.strip()}"
        )
    heads = found.stdout.split()
    if not heads:
        raise LookupError(
            f"손 케이스 커밋을 못 찾았다 - {WORK_BRANCH}에 제목이 "
            f"`{HAND_SUBJECT}`인 커밋이 없다"
        )
    return heads[0]


def hand_lines(vendor: Path = VENDOR) -> list[str]:
    """손 케이스 커밋이 더한 줄. `+` 접두는 걷어내고 `+++` 머리글은 버린다."""
    shown = _git("show", "--format=", hand_commit(vendor), cwd=vendor)
    if shown.returncode != 0:
        raise LookupError(f"손 케이스 커밋을 못 읽었다: {shown.stderr.strip()}")
    return [
        line[1:]
        for line in shown.stdout.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def korean_text(catalog: Path = CATALOG, vendor: Path = VENDOR) -> list[str]:
    """번역이 실제로 내보내는 한국어. 카탈로그와 손 케이스 둘 다."""
    rows = json.loads(catalog.read_text(encoding="utf-8"))["strings"]
    return [row["ko"] for row in rows] + hand_lines(vendor)


def known_terms(path: Path = TERMS) -> set[str]:
    """대장에 행 번호와 함께 적힌 낱말. 이미 확인된 것이라 다시 안 센다."""
    if not path.is_file():
        return set()
    rows = json.loads(path.read_text(encoding="utf-8"))["terms"]
    return {row["ko"] for row in rows}


def in_game(word: str, dump: str) -> bool:
    """게임이 이 낱말을 쓰나. 조사는 **떼어 낸 나머지가 게임에 있을 때만** 뗀다."""
    if word in dump:
        return True
    for particle in PARTICLES:
        stem = word.removesuffix(particle)
        if stem != word and len(stem) >= 2 and stem in dump:
            return True
    return False


def unknown(texts: list[str], dump: str, terms: set[str] | None = None) -> set[str]:
    """덤프에도 대장에도 없는 낱말.

    덤프는 통짜 문자열로 훑는다. 낱말이 어느 행에 있는지가 아니라 **게임이 그
    낱말을 쓰긴 하는가**가 질문이라, 부분 문자열 일치면 충분하다.
    """
    found: set[str] = set()
    for text in texts:
        found |= tokens(text)
    return {word for word in found if not in_game(word, dump)} - (terms or set())


def main(argv: list[str]) -> int:
    if not DUMP.is_file():
        print(f"게임 데이터 덤프가 없다 - 건너뛴다: {DUMP}")
        return 0

    now = sorted(unknown(korean_text(), load_dump(), known_terms()))

    if "--write" in argv:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(
            json.dumps(
                {
                    "note": "번역이 쓰는데 KR Addon 시트에는 없는 낱말. 대개는 "
                            "모드가 지어야 하는 말이다 - 게임에 없는 개념이라 "
                            "게임 시트에 있을 리가 없다. 늘어날 때 왜인지 "
                            "커밋 본문에 적는다.",
                    "source": "overlay/ko/ko.json + kr-port 손 케이스 커밋",
                    "words": now,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"골든 갱신: {len(now)}개")
        return 0

    if not GOLDEN.is_file():
        print(f"골든이 없다 - --write로 만든다: {GOLDEN}", file=sys.stderr)
        return 1

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["words"]
    added = [word for word in now if word not in golden]
    dropped = [word for word in golden if word not in now]
    if added or dropped:
        print("골든과 다르다:", file=sys.stderr)
        for word in added:
            print(f"  + {word}  (게임에 없는 낱말이 새로 들어왔다)", file=sys.stderr)
        for word in dropped:
            print(f"  - {word}  (이제 안 쓴다 - --write로 갱신해라)", file=sys.stderr)
        return 1

    print(f"통과 - 게임에 없는 낱말 {len(now)}개, 골든 그대로")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
