"""공식 가이드(guide.ff14.co.kr)를 받아 두고 우리가 베낄 형식을 뽑는다.

## 왜 있나

우리 사용자 가이드는 **공식 가이드의 형식과 문체를 따른다**. 그런데 그 "형식"이
무엇인지를 기억으로 적으면 확인한 것과 그럴듯한 것이 섞인다 - 이 저장소는
`Aetheryte -> 에테라이트`로 그걸 한 번 겪었다.

그래서 원문을 받아 두고, 스킬과 문서가 인용한 문장이 실제로 거기 있는지
검사한다(`tests/test_guide.py`).

## 하나 더 - 공식 가이드는 눈으로 읽는 문서다

`우측의 설정(톱니바퀴) 버튼을 클릭하여`, `흰색일 경우 활성화`, `아래 이미지와
같이`. 이런 자리는 **베끼면 안 되는 곳**이고, 어디가 그런 자리인지도 기억이 아니라
`scan`이 센다.

## 게임 텍스트를 저장소에 넣지 않는다

`out/`은 `.gitignore`에 있다. ko-terms와 같은 규약이다 - 남의 문서를 통째로
재배포하지 않고, **우리가 실제로 인용한 문장만** 출처를 붙여
`overlay/ko/guide-quotes.json`에 남긴다.

사용법:
    uv run --no-project python tools/ko-guide/guide.py fetch      # 인덱스 + 문서 전량
    uv run --no-project python tools/ko-guide/guide.py md         # 캐시 -> 마크다운 (네트워크 없음)
    uv run --no-project python tools/ko-guide/guide.py scan       # 시각 의존 표현 통계
    uv run --no-project python tools/ko-guide/guide.py find 단축바 # 코퍼스에서 낱말 찾기
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
CORPUS = HERE / "corpus.json"
QUOTES = REPO / "overlay" / "ko" / "guide-quotes.json"

BASE = "https://guide.ff14.co.kr"
INDEX_URL = f"{BASE}/lodestone/playguide"
DOC_URL = BASE + "/lodestone/playguide/view/{id}"

#: 초보자 가이드 밖의 대분류. 랜딩 페이지라 문체가 다르고(홍보문) 문서 번호도
#: 없다. 용어를 찾을 때는 쓸모가 있어서 같이 받아 두되 **문체의 근거로는 쓰지
#: 않는다** - 그건 `docs`가 갖는다.
SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("deepdungeon", "딥 던전: 망자의 궁전", "/deepdungeon"),
    ("deepdungeon2", "딥 던전: 천궁탑", "/deepdungeon2"),
    ("deepdungeon3", "딥 던전: 에우레카 오르토스", "/deepdungeon3"),
    ("deepdungeon4", "딥 던전: 노르브란트 순례길", "/deepdungeon4"),
    ("housing", "하우징", "/housing"),
    ("goldsaucer", "맨더빌 골드 소서", "/Goldsaucer"),
    ("islandsanctuary", "무인도 개척", "/IslandSanctuary"),
    ("cosmic", "우주 개척", "/cosmic_exploration"),
    ("ishgard", "이슈가르드 부흥", "/Ishgard"),
    ("job", "전투 직업 가이드", "/job"),
    ("job-craft", "생활 직업 가이드", "/job/CraftingGathering"),
    ("map", "풍맥 가이드", "/map"),
)

#: 헤더는 latin-1로만 실린다. 한글을 넣으면 요청 자체가 못 나간다.
USER_AGENT = "ff14-ko-accessibility/guide-corpus (personal a11y mod; not redistributed)"
DELAY_SEC = 1.0


# ---------------------------------------------------------------- 캐시 경로


def html_path(key: int | str) -> Path:
    return OUT / "html" / f"{key}.html"


def md_path(key: int | str) -> Path:
    return OUT / "md" / f"{key}.md"


# ---------------------------------------------------------------- HTML 자르기


def _slice_div(html: str, cls: str) -> str | None:
    """`class="<cls>"`인 div를 여는 태그부터 짝이 맞는 닫는 태그까지 돌려준다."""
    opening = re.search(rf'<div[^>]*\bclass="[^"]*\b{re.escape(cls)}\b[^"]*"[^>]*>', html)
    if not opening:
        return None
    depth = 1
    pos = opening.end()
    for tag in re.finditer(r"<div\b|</div>", html[pos:]):
        depth += 1 if tag.group().startswith("<div") else -1
        if depth == 0:
            return html[pos : pos + tag.start()]
    return html[pos:]


def _text(fragment: str) -> str:
    """태그를 걷어내고 공백을 하나로 만든다."""
    plain = re.sub(r"<[^>]+>", " ", fragment)
    plain = _unescape(plain)
    return re.sub(r"[\s\xa0]+", " ", plain).strip()


def _unescape(text: str) -> str:
    import html as _html

    return _html.unescape(text)


# ---------------------------------------------------------------- 인덱스


def parse_index(html: str) -> dict:
    """초보자 가이드 인덱스에서 카테고리 나무와 문서 목록을 읽는다."""
    stamp = re.search(r'class="sub_desc"[^>]*>\s*Updated for ([\d.]+)\s*/\s*([^<]+)<', html)
    docs: list[dict] = []

    for dl in re.findall(r"<dl>(.*?)</dl>", html, re.S):
        dt = re.search(r"<dt>(.*?)</dt>", dl, re.S)
        group = _text(dt.group(1)) if dt else ""
        for dd in re.findall(r"<dd>(.*?)</dd>", dl, re.S):
            strong = re.search(r"<strong>(.*?)</strong>", dd, re.S)
            head = strong.group(1) if strong else ""
            # `<strong>` 안에 링크가 있으면 그 자체가 문서다. 없으면 중분류 이름이다.
            titled = "playguide/view/" in head
            sub = None if titled else (_text(head) or None)
            for doc_id, title in re.findall(
                r'<a href="/lodestone/playguide/view/(\d+)"[^>]*>(.*?)</a>', dd, re.S
            ):
                docs.append(
                    {"id": int(doc_id), "title": _text(title), "group": group, "sub": sub}
                )

    return {
        "game_version": stamp.group(1) if stamp else "",
        "updated": stamp.group(2).strip() if stamp else "",
        "docs": docs,
    }


# ---------------------------------------------------------------- 본문


class _Markdown(HTMLParser):
    """공식 가이드 본문을 마크다운으로 옮긴다.

    뼈대(`1.` -> `ㄱ.`)와 UI 경로 표기(`[캐릭터 설정 > ...]`)를 보존하는 것이
    목적이다. 꾸밈(굵게·색)은 버린다 - 우리가 베낄 것이 아니다.
    """

    BLOCKS = {"h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ", "h5": "##### ", "p": "", "li": "- "}
    SKIP = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._buf: list[str] = []
        self._prefix: str | None = None
        self._skip = 0
        self._rows: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    # -- 수집

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIP:
            self._skip += 1
            return
        if self._skip:
            return
        if tag == "br":
            # 표 칸 안에서는 줄바꿈을 못 쓴다. 안 넣으면 앞뒤 말이 붙어버린다.
            (self._cell if self._cell is not None else self._buf).append(
                " / " if self._cell is not None else "\n"
            )
            return
        if tag == "img":
            self._buf.append(self._image(dict(attrs)))
            return
        if tag == "table":
            self._flush()
            self._rows = []
            return
        if tag == "tr" and self._rows is not None:
            self._row = []
            return
        if tag in ("td", "th") and self._row is not None:
            self._cell = []
            return
        if tag in self.BLOCKS:
            self._flush()
            self._prefix = self.BLOCKS[tag]

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag in ("td", "th") and self._cell is not None:
            assert self._row is not None
            self._row.append(_squash("".join(self._cell)))
            self._cell = None
            return
        if tag == "tr" and self._row is not None:
            assert self._rows is not None
            self._rows.append(self._row)
            self._row = None
            return
        if tag == "table" and self._rows is not None:
            self._emit_table(self._rows)
            self._rows = None
            return
        if tag in self.BLOCKS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._cell is not None:
            self._cell.append(data)
            return
        if self._prefix is None:
            if not data.strip():
                return
            self._prefix = ""  # 블록 태그 밖에 놓인 글도 버리지 않는다
        self._buf.append(data)

    # -- 출력

    @staticmethod
    def _image(attrs: dict[str, str | None]) -> str:
        name = (attrs.get("src") or "").rsplit("/", 1)[-1] or "이름 없음"
        alt = (attrs.get("alt") or "").strip()
        return f"[그림: {alt or '대체 텍스트 없음'} - {name}]"

    def _flush(self) -> None:
        text = _squash("".join(self._buf))
        if text:
            self.blocks.append((self._prefix or "") + text)
        self._buf = []
        self._prefix = None

    def _emit_table(self, rows: list[list[str]]) -> None:
        rows = [r for r in rows if any(c for c in r)]
        if not rows:
            return
        width = max(len(r) for r in rows)
        lines = []
        for i, row in enumerate(rows):
            padded = row + [""] * (width - len(row))
            lines.append("| " + " | ".join(padded) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * width) + " |")
        # 표는 한 덩어리다. 줄 사이가 벌어지면 마크다운이 표로 안 읽힌다.
        self.blocks.append("\n".join(lines))

    def result(self) -> str:
        self._flush()
        return "\n\n".join(self.blocks)


def _squash(text: str) -> str:
    """`&nbsp;`와 들여쓰기를 걷어내되 `<br>`이 만든 줄바꿈은 지킨다."""
    text = text.replace("\xa0", " ")
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def to_markdown(fragment: str) -> str:
    parser = _Markdown()
    parser.feed(fragment)
    return parser.result()


def parse_doc(html: str) -> dict:
    """문서 하나를 제목·소개·본문 마크다운으로."""
    title = re.search(r'class="title_sub"[^>]*>(.*?)</h2>', html, re.S)
    lead = re.search(r'class="sub_desc"[^>]*>(.*?)</p>', html, re.S)
    body = _slice_div(html, "edit_area")
    if body is None:
        # 콘텐츠 가이드 랜딩 페이지에는 `edit_area`가 없다. 통째로 읽되
        # 좌측 메뉴(`lnb`)는 잘라낸 뒤다.
        body = _slice_div(html, "contents_box") or ""
    return {
        "title": _text(title.group(1)) if title else "",
        "lead": _text(lead.group(1)) if lead else "",
        "markdown": to_markdown(body),
    }


# ---------------------------------------------------------------- 시각 의존

#: 공식 가이드가 **눈으로 읽는 것을 전제하는** 표현. 우리 가이드는 여기만
#: 안 베낀다. 낱말은 지어낸 것이 아니라 받아 놓은 원문에서 `scan`으로 세어
#: 실제로 나온 것들이다.
VISUAL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("그림 참조", r"(?:아래|위|다음)\s*(?:이미지|그림|화면|사진)|(?:이미지|그림)와\s*같이|참고\s*이미지"),
    ("위치", r"[좌우]측|오른쪽|왼쪽|상단|하단|화면\s*중앙|[좌우][상하]단"),
    ("색", r"(?:흰|하얀|파란|푸른|빨간|붉은|노란|초록|녹|회|주황|검은)색|색상으로|색으로\s*구분"),
    ("마우스", r"더블\s*클릭|좌클릭|우클릭|클릭|드래그|드롭|마우스|스크롤"),
    ("모양", r"톱니바퀴|돋보기|화살표\s*모양|아이콘\s*모양"),
)


def visual_hits(text: str) -> list[dict]:
    """시각 의존 표현이 나온 자리를 앞에서부터 돌려준다. 겹치면 앞엣것만."""
    found: list[dict] = []
    for kind, pattern in VISUAL_PATTERNS:
        for m in re.finditer(pattern, text):
            found.append({"kind": kind, "text": m.group(), "start": m.start(), "end": m.end()})
    found.sort(key=lambda h: (h["start"], -h["end"]))

    kept: list[dict] = []
    edge = -1
    for hit in found:
        if hit["start"] < edge:
            continue
        kept.append(hit)
        edge = hit["end"]
    return kept


# ---------------------------------------------------------------- 받아오기


def fetch(url: str, *, tries: int = 3) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last: Exception | None = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover - 망 상태
            last = exc
            time.sleep(DELAY_SEC * (attempt + 1))
    raise RuntimeError(f"못 받았다: {url} ({last})")


def _cache(key: int | str, url: str, *, refresh: bool) -> str:
    path = html_path(key)
    if path.is_file() and not refresh:
        return path.read_text(encoding="utf-8")
    body = fetch(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    time.sleep(DELAY_SEC)
    return body


def _write_md(key: int | str, html: str) -> dict:
    doc = parse_doc(html)
    path = md_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    head = f"# {doc['title']}\n\n{doc['lead']}\n\n" if doc["title"] else ""
    path.write_text(head + doc["markdown"] + "\n", encoding="utf-8")
    return doc


#: 스킬이 "공식 가이드는 이렇게 쓴다"고 주장하는 근거. 기억이 아니라 코퍼스에서
#: 센 값이고, 다시 세서 문서와 대조하는 것은 `tools/docs-check`가 한다.
STYLE_COUNTS: tuple[tuple[str, str], ...] = (
    ("습니다체 종결", r"습니다[.\n]"),
    ("한다체 종결", r"(?:한다|된다|이다)[.\n]"),
    ("가능형", r"할 수 있습니다"),
    ("UI 경로", r"\[[^\]\n]{1,60}>[^\]\n]{1,60}\]"),
    ("버튼 표기", r"\[[^\]\n]{1,30}\]\s*버튼"),
    ("보충 표기", r"※"),
    ("모험가님", r"모험가님"),
    ("도해 라벨", r"\n### [ㄱ-ㅎ]\."),
    ("그림", r"\[그림: "),
    ("대체 텍스트 있는 그림", r"\[그림: (?!대체 텍스트 없음)"),
)


def stats() -> dict:
    """캐시에서 문체와 시각 의존을 센다. 캐시가 없으면 셀 것이 없다.

    **문서 62건만 센다.** 대분류 랜딩(`sections`)은 홍보문이고 `edit_area`도
    없어서 머리글 이미지 같은 것이 섞인다 - 문체의 근거로 삼으면 안 된다.
    """
    bodies: dict[str, str] = {}
    for row in _corpus()["docs"]:
        path = md_path(row["id"])
        if path.is_file():
            bodies[str(row["id"])] = path.read_text(encoding="utf-8")
    if not bodies:
        return {}

    joined = "\n".join(bodies.values())
    counted = {name: len(re.findall(pattern, joined)) for name, pattern in STYLE_COUNTS}

    lead = 0
    for body in bodies.values():
        blocks = body.split("\n\n")
        if len(blocks) > 1 and "알아봅니다" in blocks[1]:
            lead += 1

    kinds: dict[str, int] = {}
    for body in bodies.values():
        for hit in visual_hits(body):
            kinds[hit["kind"]] = kinds.get(hit["kind"], 0) + 1

    return {
        **counted,
        "도입문": lead,
        "시각 의존": sum(kinds.values()),
        "시각 의존 갈래": dict(sorted(kinds.items(), key=lambda kv: -kv[1])),
    }


def _write_stats() -> dict:
    """대장에 통계를 다시 적는다. 캐시가 있을 때만 손댄다."""
    measured = stats()
    if not measured:
        return {}
    corpus = _corpus()
    corpus["stats"] = measured
    CORPUS.write_text(
        json.dumps(corpus, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return measured


def cmd_fetch(refresh: bool) -> int:
    index = parse_index(_cache("index", INDEX_URL, refresh=refresh))
    if not index["docs"]:
        print("[실패] 인덱스에서 문서를 못 읽었다. 사이트 구조가 바뀌었을 수 있다.")
        return 1

    for doc in index["docs"]:
        html = _cache(doc["id"], DOC_URL.format(id=doc["id"]), refresh=refresh)
        _write_md(doc["id"], html)
        doc["url"] = DOC_URL.format(id=doc["id"])
        print(f"  {doc['id']:>4}  {doc['group']} / {doc['sub'] or '-'} / {doc['title']}")

    sections = []
    for slug, title, path in SECTIONS:
        html = _cache(slug, BASE + path, refresh=refresh)
        _write_md(slug, html)
        sections.append({"slug": slug, "title": title, "url": BASE + path})
        print(f"  {slug:>16}  {title}")

    CORPUS.write_text(
        json.dumps(
            {
                "note": (
                    "공식 가이드(guide.ff14.co.kr) 문서 대장. 원문은 저장소에 넣지 않는다 - "
                    "`tools/ko-guide/out/`에 받아 두고 여기에는 무엇을 어디서 받았는지만 남긴다. "
                    "우리가 인용한 문장은 overlay/ko/guide-quotes.json에 따로 있다."
                ),
                "method": "uv run --no-project python tools/ko-guide/guide.py fetch",
                "game_version": index["game_version"],
                "guide_updated": index["updated"],
                "fetched": date.today().isoformat(),
                "docs": index["docs"],
                "sections": sections,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    measured = _write_stats()
    print(f"\n문서 {len(index['docs'])}건 + 대분류 {len(sections)}건 -> {CORPUS}")
    print(f"시각 의존 {measured.get('시각 의존', 0)}건 / 습니다체 {measured.get('습니다체 종결', 0)}건")
    return 0


def cmd_md() -> int:
    """네트워크 없이 캐시 HTML만 다시 옮긴다. 정규화를 고칠 때 쓴다."""
    count = 0
    for path in sorted(html_path("x").parent.glob("*.html")):
        if path.stem == "index":
            continue
        _write_md(path.stem, path.read_text(encoding="utf-8"))
        count += 1
    _write_stats()  # 정규화가 바뀌면 세는 값도 바뀐다. 대장이 뒤처지면 안 된다
    print(f"{count}건 다시 옮겼다 -> {md_path('*').parent}")
    return 0


def _corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def _titles() -> dict[str, str]:
    corpus = _corpus()
    titles = {str(d["id"]): d["title"] for d in corpus["docs"]}
    titles.update({s["slug"]: s["title"] for s in corpus.get("sections", ())})
    return titles


def cmd_scan(limit: int) -> int:
    """어디가 눈으로 읽는 자리인가. 스킬 §5의 근거가 여기서 나온다."""
    titles = _titles()
    tally: dict[str, int] = {}
    words: dict[str, int] = {}
    worst: list[tuple[int, str, str]] = []

    for key, title in titles.items():
        path = md_path(key)
        if not path.is_file():
            continue
        hits = visual_hits(path.read_text(encoding="utf-8"))
        for hit in hits:
            tally[hit["kind"]] = tally.get(hit["kind"], 0) + 1
            words[hit["text"]] = words.get(hit["text"], 0) + 1
        worst.append((len(hits), key, title))

    if not worst:
        print("캐시가 없다. 먼저: run\\guide.bat fetch")
        return 1

    print("갈래별")
    for kind, count in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>5}  {kind}")
    print("\n낱말별")
    for word, count in sorted(words.items(), key=lambda kv: -kv[1])[:limit]:
        print(f"  {count:>5}  {word}")
    print("\n문서별 (많은 순)")
    for count, key, title in sorted(worst, reverse=True)[:limit]:
        print(f"  {count:>5}  {key} {title}")
    print(f"\n합계 {sum(tally.values())}건 / 문서 {len(worst)}건")
    return 0


def cmd_find(word: str, context: int) -> int:
    """코퍼스에서 낱말을 찾는다. 게임이 아니라 **공식 문서**가 뭐라고 부르나."""
    titles = _titles()
    total = 0
    for key, title in titles.items():
        path = md_path(key)
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if word in line:
                total += 1
                shown = line if len(line) <= context else line[:context] + " …"
                print(f"{key:>16}:{number:<4} [{title}] {shown}")
    print(f"\n{total}건")
    return 0 if total else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__ or "")
    sub = parser.add_subparsers(dest="cmd", required=True)

    grab = sub.add_parser("fetch", help="인덱스와 문서를 받아 캐시에 넣는다")
    grab.add_argument("--refresh", action="store_true", help="캐시를 무시하고 다시 받는다")

    sub.add_parser("md", help="캐시 HTML을 마크다운으로 다시 옮긴다 (네트워크 없음)")

    scan = sub.add_parser("scan", help="시각 의존 표현이 어디에 몇 건인가")
    scan.add_argument("--limit", type=int, default=20)

    find = sub.add_parser("find", help="코퍼스에서 낱말 찾기")
    find.add_argument("word")
    find.add_argument("--context", type=int, default=120)

    args = parser.parse_args(argv)
    if args.cmd == "fetch":
        return cmd_fetch(args.refresh)
    if args.cmd == "md":
        return cmd_md()
    if args.cmd == "scan":
        return cmd_scan(args.limit)
    return cmd_find(args.word, args.context)


if __name__ == "__main__":
    sys.exit(main())
