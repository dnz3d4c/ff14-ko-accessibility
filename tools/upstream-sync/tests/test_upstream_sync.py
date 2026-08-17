"""업스트림 추종 도구 테스트.

판정 로직은 전부 순수 함수로 두고 여기서 검사한다. git을 부르는 부분은
vendor 클론이 있을 때만 돌린다 - 클론이 없는 머신에서 빨간불이 뜨면
아무도 안 본다.

가장 중요한 것은 **미번역 검출**이다. 업스트림 릴리스 노트는 독일어고,
번역되지 않은 채로 동기화가 끝나면 사용자는 자기 저장소에 뭐가 들어왔는지
영영 모른다. 그 상태를 통과시키지 않는 것이 이 파일의 첫 번째 책임이다.
"""

from pathlib import Path

import pytest
import upstream_sync as us


# --- 태그 정렬 ------------------------------------------------------------


def test_태그를_숫자로_비교한다():
    # 문자열로 비교하면 v5.9가 v5.87보다 뒤로 간다.
    assert us.version_key("v5.9") < us.version_key("v5.87")
    assert us.version_key("v5.85") < us.version_key("v5.86")


def test_형식이_다른_태그도_죽지_않는다():
    # 업스트림이 규칙을 바꿔도 도구가 죽는 것보다 뒤로 미는 게 낫다.
    assert us.version_key("nightly") == (-1,)


def test_핀보다_새_태그만_고른다():
    tags = ["v5.84", "v5.85", "v5.86", "v5.87"]
    assert us.newer_tags(tags, "v5.85") == ["v5.86", "v5.87"]


def test_새_태그가_없으면_빈_목록():
    assert us.newer_tags(["v5.84", "v5.85"], "v5.85") == []


def test_핀_태그를_모르면_전부_새것으로_본다():
    # 핀이 태그가 아닌 커밋을 가리키는 경우. 조용히 0건이라고 하면 안 된다.
    assert us.newer_tags(["v5.86", "v5.87"], "없는태그") == ["v5.86", "v5.87"]


# --- 변경 이력 문서 --------------------------------------------------------


HEADER = "# 업스트림 변경 이력\n\n앞줄 설명.\n"

DOC = (
    HEADER
    + """
## v5.86 — 2026-08-17

사냥수첩 목표를 개체 목록에서 고를 수 있다

- `70d6ae3` 사냥수첩 목표가 개체 목록에 나온다
  원문: Release v5.86: Jagdziele im Objekt-Browser

## v5.85 — 2026-08-16

숫자만 읽히던 창 세 곳이 뜻을 말한다

- `d1cee70` 숫자만 있던 창 세 곳
  원문: Release v5.85: drei Fenster
"""
)


def test_태그별로_쪼갠다():
    sections = us.split_sections(DOC)
    assert list(sections) == ["v5.86", "v5.85"]
    assert "70d6ae3" in sections["v5.86"]


def test_미번역이_없으면_통과():
    assert us.untranslated_tags(DOC) == []


def test_미번역_표시가_남아_있으면_잡는다():
    doc = DOC.replace("사냥수첩 목표가 개체 목록에 나온다", us.UNTRANSLATED)
    assert us.untranslated_tags(doc) == ["v5.86"]


def test_이력에_없는_태그를_찾아낸다():
    # 동기화는 했는데 이력을 안 쓴 경우. 미번역보다 더 조용한 실패다.
    assert us.missing_tags(DOC, ["v5.85", "v5.86", "v5.87"]) == ["v5.87"]


# --- 자리 만들기 -----------------------------------------------------------


COMMITS = [
    us.Commit("a8ac7c5", "Release v5.87: Jagdziele laufen direkt zum Monster"),
    us.Commit("07e0769", "STATUS: Release v5.87 ist draussen"),
]


def test_자리에_원문과_미번역_표시가_같이_들어간다():
    section = us.render_section("v5.87", "2026-08-17", COMMITS)
    assert "## v5.87 — 2026-08-17" in section
    assert "a8ac7c5" in section
    # 원문을 지우지 않는다. 옮긴 게 틀렸을 때 되짚을 자리가 그것뿐이다.
    assert "Jagdziele laufen direkt zum Monster" in section
    assert us.UNTRANSLATED in section


def test_만든_자리는_바로_미번역으로_잡힌다():
    # 자리만 만들고 커밋하면 검사기가 막아야 한다.
    doc = us.insert_sections(DOC, [us.render_section("v5.87", "2026-08-17", COMMITS)])
    assert us.untranslated_tags(doc) == ["v5.87"]


def test_새_항목이_맨_위에_붙는다():
    doc = us.insert_sections(DOC, [us.render_section("v5.87", "2026-08-17", COMMITS)])
    assert list(us.split_sections(doc)) == ["v5.87", "v5.86", "v5.85"]


def test_머리말을_안_건드린다():
    doc = us.insert_sections(DOC, [us.render_section("v5.87", "2026-08-17", COMMITS)])
    assert doc.startswith(HEADER)


def test_항목이_없으면_문서가_그대로다():
    assert us.insert_sections(DOC, []) == DOC


def test_이력이_비어_있어도_붙는다():
    # 첫 동기화. 아직 아무 항목도 없는 문서다.
    doc = us.insert_sections(HEADER, [us.render_section("v5.87", "2026-08-17", COMMITS)])
    assert list(us.split_sections(doc)) == ["v5.87"]


# --- 핀 ------------------------------------------------------------------


def test_핀을_읽고_쓴다(tmp_path: Path):
    path = tmp_path / "upstream.json"
    us.write_pin({"tag": "v5.85", "commit": "3051202"}, path)
    assert us.read_pin(path)["tag"] == "v5.85"


def test_핀이_없으면_안_지어낸다(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        us.read_pin(tmp_path / "없다.json")


# --- 실제 저장소 ----------------------------------------------------------


needs_vendor = pytest.mark.skipif(not us.vendor_present(), reason="vendor 클론이 없다")


def test_이_저장소의_핀이_읽힌다():
    pin = us.read_pin()
    assert pin["commit"] and pin["tag"] and pin["repo"]


@needs_vendor
def test_핀이_가리키는_커밋이_vendor에_있다():
    # 핀이 존재하지 않는 커밋을 가리키면 패치 검사 전체가 의미를 잃는다.
    assert us.commit_exists(us.read_pin()["commit"])


def test_이력에_핀_태그가_있고_번역돼_있다():
    # 지금 vendor가 가리키는 판이 무엇인지 사용자가 한국어로 읽을 수 있어야 한다.
    text = us.CHANGES.read_text(encoding="utf-8")
    pin = us.read_pin()
    assert us.missing_tags(text, [pin["tag"]]) == []
    assert us.untranslated_tags(text) == []
