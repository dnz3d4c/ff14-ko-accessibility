"""게임 용어 대장 검사.

이 대장이 막는 사고는 하나고, 이 저장소는 그걸 이미 한 번 겪었다 - 그럴듯한
용어를 지어내 결정으로 박아 두는 것. `Aetheryte`를 "에테라이트"라고 스킬에
적어 놨었는데 그때는 확인한 적이 없었다(지금은 확인됐다, Addon 2723행).

그래서 모든 줄이 **행 번호와 그 행의 원문**을 함께 갖는다. 구조 검사는 늘
돌고, 게임 데이터와의 대조는 덤프가 있을 때만 돈다.
"""

import json

import pytest
import terms

CATALOG = terms.CATALOG
DUMP = terms.DUMP


@pytest.fixture(scope="module")
def catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


# --- 구조 - 늘 돈다 --------------------------------------------------------


def test_대장이_있다():
    assert CATALOG.is_file(), f"{CATALOG}가 없다"


def test_줄마다_행_번호가_있다(catalog):
    # 번호 없는 줄은 "어디서 봤는지 모르는 용어"다. 그게 지어낸 것과 구분이 안 된다.
    for row in catalog["terms"]:
        assert isinstance(row["addon"], int), row
        assert row["addon"] > 0, row


def test_한국어가_원문_안에_있다(catalog):
    # 대장이 자기 안에서 먼저 앞뒤가 맞아야 한다.
    for row in catalog["terms"]:
        assert row["ko"] in row["row_text"], row


def test_영어가_겹치지_않는다(catalog):
    names = [row["en"] for row in catalog["terms"]]
    assert len(names) == len(set(names)), "같은 영어에 두 답이 있으면 어느 쪽인지 모른다"


def test_못_찾은_것을_지우지_않는다(catalog):
    # 없다는 것도 결과다. 특히 이것 - 게임은 "채팅"을 안 쓴다.
    assert "채팅" in catalog["not_found"]


def test_게임_판번호를_적어_뒀다(catalog):
    # 게임이 올라가면 용어가 바뀔 수 있다. 언제 뽑았는지 없으면 못 되짚는다.
    assert catalog["game_version"]
    assert catalog["dumped"]


# --- 게임 데이터와 대조 - 덤프가 있을 때만 --------------------------------

needs_dump = pytest.mark.skipif(
    not DUMP.is_file(),
    reason="게임 데이터 덤프가 없다 - run\\terms.bat dump tools\\ko-terms\\out",
)


@needs_dump
def test_행마다_게임이_같은_말을_한다(catalog):
    # 게임이 올라가면서 낱말을 바꾸면 여기가 빨개진다.
    rows = terms.load_dump()
    missing = []
    changed = []
    for row in catalog["terms"]:
        text = rows.get(row["addon"])
        if text is None:
            missing.append(row)
        elif text != row["row_text"]:
            changed.append((row, text))

    assert not missing, f"게임 데이터에 없는 행: {missing}"
    assert not changed, f"게임이 다른 말을 한다: {changed}"


@needs_dump
def test_못_찾았다고_적은_낱말이_정말_없다(catalog):
    rows = terms.load_dump()
    for word in catalog["not_found"]:
        hits = [n for n, text in rows.items() if word in text]
        assert not hits, f"'{word}'는 없다고 적었는데 {len(hits)}행에 있다: {hits[:5]}"
