"""공식 가이드 수집기 검사.

이 도구가 막는 사고는 ko-terms와 같다 - **문체와 용어를 지어내는 것**. 우리
사용자 가이드는 공식 가이드의 형식을 따르기로 했는데, 그 "형식"이 무엇인지를
기억으로 적으면 확인한 것과 그럴듯한 것이 섞인다.

그래서 원문을 받아 두고, 스킬과 문서가 인용한 문장이 **실제로 그 문서에 있는지**
대조한다. 구조 검사는 늘 돌고, 원문 대조는 캐시가 있을 때만 돈다.
"""

import json

import guide
import pytest

REPO = guide.REPO
CORPUS = guide.CORPUS
QUOTES = guide.QUOTES


# --- 인덱스 읽기 -----------------------------------------------------------

INDEX_HTML = """
<div class="contents_box"><div class="inner">
  <h2 class="title_sub">초보자 가이드</h2>
  <p class="sub_desc">Updated for 7.55 / 2026. 08. 04</p>
  <div class="box_site t1"><div class="area2"><ul class="list">
    <li><dl>
      <dt>기초 가이드</dt>
      <dd>
        <strong>게임시작</strong>
        <ul>
          <li><a href="/lodestone/playguide/view/107">회원가입</a></li>
          <li><a href="/lodestone/playguide/view/106">보안서비스</a></li>
        </ul>
      </dd>
      <dd><strong><a href="/lodestone/playguide/view/104">조작법</a></strong></dd>
    </dl></li>
    <li><dl>
      <dt>편의 기능</dt>
      <dd><strong><a href="/lodestone/playguide/view/153">여관</a></strong></dd>
    </dl></li>
  </ul></div></div>
</div></div>
"""


def test_인덱스가_대분류_중분류_문서를_읽는다():
    index = guide.parse_index(INDEX_HTML)
    docs = {d["id"]: d for d in index["docs"]}

    assert docs[107]["title"] == "회원가입"
    assert docs[107]["group"] == "기초 가이드"
    assert docs[107]["sub"] == "게임시작"

    # 중분류 없이 대분류 밑에 바로 붙는 문서가 있다. 없는 것을 지어내지 않는다.
    assert docs[104]["title"] == "조작법"
    assert docs[104]["group"] == "기초 가이드"
    assert docs[104]["sub"] is None

    assert docs[153]["group"] == "편의 기능"


def test_인덱스가_판번호를_읽는다():
    # 게임이 올라가면 가이드도 바뀐다. 언제 것인지 없으면 못 되짚는다.
    index = guide.parse_index(INDEX_HTML)
    assert index["game_version"] == "7.55"
    assert index["updated"] == "2026. 08. 04"


# --- 본문 정규화 -----------------------------------------------------------

DOC_HTML = """
<div class="contents_box"><div class="inner">
  <h2 class="title_sub">인터페이스/HUD</h2>
  <p class="sub_desc">게임 화면의 인터페이스와 각 구성 요소(HUD)에 대해 알아봅니다.</p>
  <div class="edit_area">
    <h2>1. 게임 화면 구성</h2>
    <p>첫 접속 시 기본 화면이 나타납니다.</p>
    <p>&nbsp;</p>
    <figure><p><img src="https://static.ff14.co.kr/Contents/2024/12/ABC.png" width="700"></p></figure>
    <h3>ㄱ. 진행 중인 주요 퀘스트</h3>
    <p>퀘스트를 확인할 수 있습니다.<br>지도가 실행됩니다.</p>
    <h3>ㄴ. 공식 가이드</h3>
    <p>[캐릭터 설정 &gt; 사용자 인터페이스 설정 &gt; 일반 탭]에서 설정할 수 있습니다.</p>
    <ul><li>첫째 줄</li><li>둘째 줄</li></ul>
    <table><tr><th>키</th><th>기능</th></tr><tr><td>ESC</td><td>시스템 메뉴</td></tr></table>
  </div>
</div></div>
"""


@pytest.fixture(scope="module")
def doc() -> dict:
    return guide.parse_doc(DOC_HTML)


def test_제목과_소개를_읽는다(doc):
    assert doc["title"] == "인터페이스/HUD"
    assert doc["lead"] == "게임 화면의 인터페이스와 각 구성 요소(HUD)에 대해 알아봅니다."


def test_제목_계층을_보존한다(doc):
    # 공식 가이드의 뼈대가 `1.` -> `ㄱ.`이다. 계층이 뭉개지면 형식을 못 베낀다.
    assert "## 1. 게임 화면 구성" in doc["markdown"]
    assert "### ㄱ. 진행 중인 주요 퀘스트" in doc["markdown"]


def test_줄바꿈_태그가_줄바꿈이_된다(doc):
    assert "퀘스트를 확인할 수 있습니다.\n지도가 실행됩니다." in doc["markdown"]


def test_빈_문단을_버린다(doc):
    # 이 사이트는 문단 사이를 `<p>&nbsp;</p>`로 벌린다. 그게 다 남으면 못 읽는다.
    assert "\xa0" not in doc["markdown"]
    assert "\n\n\n" not in doc["markdown"]


def test_그림은_대체_텍스트_없음으로_남는다(doc):
    # 이 사이트의 이미지에는 alt가 없다. 그 사실 자체가 우리한테 필요한 정보다 -
    # 그림에 실린 내용은 코퍼스에 안 남으므로, 그 자리를 비워 두면 안 된다.
    assert "[그림: 대체 텍스트 없음 - ABC.png]" in doc["markdown"]


def test_UI_경로_표기를_안_건드린다(doc):
    # `&gt;`를 되돌리지 않으면 우리가 베낄 표기가 깨진다.
    assert "[캐릭터 설정 > 사용자 인터페이스 설정 > 일반 탭]" in doc["markdown"]


def test_목록과_표가_마크다운이_된다(doc):
    assert "- 첫째 줄" in doc["markdown"]
    assert "| 키 | 기능 |" in doc["markdown"]
    assert "| ESC | 시스템 메뉴 |" in doc["markdown"]


# --- 시각 의존 표현 찾기 ---------------------------------------------------


def test_시각_의존_표현을_찾는다():
    hits = guide.visual_hits("우측의 설정(톱니바퀴) 버튼을 클릭하여 설정이 가능합니다.")
    kinds = {h["kind"] for h in hits}
    assert "위치" in kinds  # 우측
    assert "마우스" in kinds  # 클릭


def test_색으로만_구분하는_것을_찾는다():
    hits = guide.visual_hits("흰색일 경우 활성화, 파란색일 경우 비활성화 상태입니다.")
    assert {h["kind"] for h in hits} == {"색"}


def test_멀쩡한_문장은_안_잡는다():
    # 오탐이 많으면 아무도 안 본다. 게임 안의 방위(동/서/남/북)나 메뉴 이름은
    # 시각 의존이 아니다.
    assert guide.visual_hits("[시스템(ESC) > 허드 배열 변경] 메뉴에서 바꿉니다.") == []
    assert guide.visual_hits("북쪽 에테라이트로 이동할 수 있습니다.") == []


def test_찾은_자리를_그대로_돌려준다():
    hits = guide.visual_hits("아래 이미지와 같이 진행합니다.")
    assert hits[0]["text"] == "아래 이미지"
    assert hits[0]["kind"] == "그림 참조"


# --- 문서 대장 - 늘 돈다 ---------------------------------------------------


@pytest.fixture(scope="module")
def corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def test_대장이_있다():
    assert CORPUS.is_file(), f"{CORPUS}가 없다"


def test_문서_번호가_겹치지_않는다(corpus):
    ids = [d["id"] for d in corpus["docs"]]
    assert len(ids) == len(set(ids))


def test_줄마다_출처가_있다(corpus):
    for row in corpus["docs"]:
        assert isinstance(row["id"], int) and row["id"] > 0, row
        assert row["title"], row
        assert row["url"].startswith("https://guide.ff14.co.kr/"), row
        assert row["group"], row


def test_언제_어느_판을_받았는지_적혀_있다(corpus):
    assert corpus["game_version"]
    assert corpus["fetched"]


def test_대분류는_따로_센다(corpus):
    """콘텐츠 가이드 랜딩은 문서와 성격이 다르다 - 홍보문이라 문체의 근거가 못 된다.

    같은 목록에 섞으면 "62건을 근거로 문체를 정했다"가 거짓말이 된다.
    """
    slugs = [s["slug"] for s in corpus["sections"]]
    assert len(slugs) == len(set(slugs))
    for row in corpus["sections"]:
        assert row["title"], row
        assert row["url"].startswith("https://guide.ff14.co.kr/"), row


def test_문체_통계가_대장에_있다(corpus):
    # 스킬이 "공식 가이드는 습니다체다"라고 주장하는 근거다. 근거가 대장에
    # 없으면 그 주장은 기억에서 나온 것이 된다.
    for key in ("습니다체 종결", "한다체 종결", "시각 의존", "도입문"):
        assert key in corpus["stats"], key


def test_통계가_원문과_맞는다(corpus):
    """캐시가 있을 때만 돈다. 정규화를 고쳐 놓고 대장을 안 고친 것을 잡는다."""
    measured = guide.stats()
    if not measured:
        pytest.skip("캐시 없음 - run\\guide.bat fetch")
    assert measured == corpus["stats"], "run\\guide.bat md로 대장을 다시 적어라"


# --- 인용 대장 -------------------------------------------------------------


@pytest.fixture(scope="module")
def quotes() -> dict:
    return json.loads(QUOTES.read_text(encoding="utf-8"))


def test_인용_대장이_있다():
    assert QUOTES.is_file(), f"{QUOTES}가 없다"


def test_인용마다_문서_번호가_있고_대장에_있는_문서다(quotes, corpus):
    known: set[int | str] = {d["id"] for d in corpus["docs"]}
    known |= {s["slug"] for s in corpus["sections"]}
    for row in quotes["quotes"]:
        assert row["doc"] in known, row
        assert row["text"].strip(), row
        assert row["why"].strip(), row  # 왜 인용했는지 없으면 다음 사람이 못 쓴다


def test_인용이_원문에_실제로_있다(quotes):
    """캐시가 있을 때만 돈다 - ko-terms 덤프 검사와 같은 규약.

    이게 이 도구의 존재 이유다. 스킬이 공식 가이드를 인용하는데 그 문장이
    실제로는 없으면, `Aetheryte -> 에테라이트`와 똑같은 사고다.
    """
    missing_cache = []
    for row in quotes["quotes"]:
        path = guide.md_path(row["doc"])
        if not path.is_file():
            missing_cache.append(row["doc"])
            continue
        body = path.read_text(encoding="utf-8")
        assert row["text"] in body, f"{row['doc']}번 문서에 없는 문장이다: {row['text']}"

    if missing_cache:
        pytest.skip(f"캐시 없음: {sorted(set(missing_cache))} - run\\guide.bat fetch")
