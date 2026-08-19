"""문서가 실제와 어긋나면 빨개진다.

막는 사고는 하나다 - **문서가 조용히 낡는 것.** 커밋 훅 C8은 현황판을
*건드렸나*만 보고, 그 밖의 문서는 아예 안 본다. 그래서 실제로 이렇게 됐다.

- `README.md`가 12커밋 동안 "한국어화는 아직 시작 전"이라고 적고 있었다
- 현황판 §1이 "남은 것은 캐릭터 생성 하나"인데 §2에 P1이 셋 열려 있었다
- `675쌍`·`C1~C8`·`40곳`이 네 문서에 손으로 복사돼 원본과 갈라졌다

아래 테스트는 두 갈래다. **지금 저장소가 맞나**(늘 도는 것)와 **어긋났을 때
정말 걸리나**(합성 문서로 실증). 둘째가 없으면 검사가 죽었는지 알 수 없다.
"""

import re

import docs_check
import pytest


# --- 지금 저장소 - 늘 돈다 -------------------------------------------------


def test_문서와_산출물이_맞는다():
    bad = docs_check.check_citations()
    assert bad == [], "\n".join(bad)


def test_현황판_절끼리_안_어긋난다():
    bad = docs_check.check_board()
    assert bad == [], "\n".join(bad)


def test_인용_자리가_하나도_안_비어_있다():
    # 문장을 고쳐 쓰다 인용 자리가 사라지면 검사가 조용히 죽는다. 그게 제일
    # 나쁜 실패라 여기서 따로 못박는다.
    for rel, name, pattern in docs_check.CITATIONS:
        text = (docs_check.REPO / rel).read_text(encoding="utf-8")
        assert len(re.findall(pattern, text)) == 1, f"{rel}: `{name}` 인용 자리"


def test_손_케이스_숫자_셋의_관계():
    got = docs_check.facts()
    # 41(파서가 못 읽음) = 40(진짜 손으로 볼 자리) + 1(`Pick` 헬퍼 선언)
    assert got["손으로 볼 자리"] == got["골든 미해석"] - 1
    # 40(볼 자리) = 35(옮긴 자리) + 5(데이터 표 참조 = W-12)
    assert got["손으로 옮긴 자리"] == got["손으로 볼 자리"] - 5


def test_손_케이스_커밋이_아직_거기_있다():
    # 커밋 제목이 바뀌면 조용히 0을 세는 대신 ko_words.hand_commit이 소리를
    # 낸다. 여기서는 세어진 값이 실재하는지만 못박는다.
    assert docs_check.hand_sites() > 0


# --- 어긋났을 때 정말 걸리나 - 합성 문서 -----------------------------------

HEAD = """# 판

## 1. 지금

- 다음: {next}
- 막힘: {blocked}

## 2. 열린 작업

| ID | 제목 | 우선 | 상태 | 비고 |
|----|------|------|------|------|
{rows}

## 9. 끝난 것

{done}
"""


def board(rows, next_="**W-01**", blocked="`W-02`", done="- W-02 끝"):
    return HEAD.format(rows="\n".join(rows), next=next_, blocked=blocked, done=done)


def write(tmp_path, text):
    path = tmp_path / "status.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_완료가_표에_남아_있으면_걸린다(tmp_path):
    text = board(["| W-01 | 하나 | P1 | 완료 | |", "| W-02 | 둘 | P2 | 막힘 | |"])
    bad = docs_check.check_board(write(tmp_path, text))
    assert any("완료" in item for item in bad), bad


def test_우선순위_순서가_깨지면_걸린다(tmp_path):
    text = board(
        ["| W-01 | 하나 | P2 | 대기 | |", "| W-03 | 셋 | P1 | 대기 | |",
         "| W-02 | 둘 | P2 | 막힘 | |"],
        next_="**W-03**",
        done="- W-02 끝",
    )
    bad = docs_check.check_board(write(tmp_path, text))
    assert any("우선순위 순이 아니다" in item for item in bad), bad


def test_다음이_최상위_등급을_빠뜨리면_걸린다(tmp_path):
    # 이번에 실제로 난 사고다 - §1이 P2 하나만 가리키고 P1 셋이 열려 있었다.
    text = board(
        ["| W-01 | 하나 | P1 | 대기 | |", "| W-03 | 셋 | P2 | 대기 | |",
         "| W-02 | 둘 | P2 | 막힘 | |"],
        next_="캐릭터 생성(W-03)",
    )
    bad = docs_check.check_board(write(tmp_path, text))
    assert any("최상위 등급" in item and "W-01" in item for item in bad), bad


def test_막힘이_아닌_것을_막힘이라고_적으면_걸린다(tmp_path):
    text = board(["| W-01 | 하나 | P1 | 대기 | |", "| W-02 | 둘 | P2 | 대기 | |"])
    bad = docs_check.check_board(write(tmp_path, text))
    assert any("막힘이라고 적었는데" in item for item in bad), bad


def test_ID가_둘_다에서_사라지면_걸린다(tmp_path):
    text = board(
        ["| W-01 | 하나 | P1 | 대기 | |", "| W-03 | 셋 | P2 | 막힘 | |"],
        blocked="`W-03`",
        done="- 끝난 것 없음",
    )
    bad = docs_check.check_board(write(tmp_path, text))
    assert any("W-02" in item for item in bad), bad


def test_ID가_두_번_나오면_걸린다(tmp_path):
    text = board(
        ["| W-01 | 하나 | P1 | 대기 | |", "| W-01 | 또 하나 | P1 | 대기 | |",
         "| W-02 | 둘 | P2 | 막힘 | |"],
    )
    bad = docs_check.check_board(write(tmp_path, text))
    assert any("같은 ID가 두 번" in item for item in bad), bad


def test_멀쩡한_판은_통과한다(tmp_path):
    text = board(
        ["| W-01 | 하나 | P1 | 대기 | |", "| W-03 | 셋 | P2 | 대기 | |",
         "| W-02 | 둘 | P2 | 막힘 | |"],
        next_="**W-01**",
    )
    assert docs_check.check_board(write(tmp_path, text)) == []


# --- 유형별 표 합계 --------------------------------------------------------


def test_유형별_표를_더한다(tmp_path):
    path = tmp_path / "hand.md"
    path.write_text(
        "# 앞\n\n## 유형별\n\n| 유형 | 개수 | 무슨 일인가 |\n|---|---|---|\n"
        "| 중첩 삼항 | 16 | 갈림길 |\n| 배열 | 1 | 순서 |\n\n## 뒤\n\n| 기타 | 99 | |\n",
        encoding="utf-8",
    )
    assert docs_check.hand_type_sum(path) == 17


def test_유형별_절이_없으면_소리를_낸다(tmp_path):
    path = tmp_path / "hand.md"
    path.write_text("# 앞\n\n아무것도 없다\n", encoding="utf-8")
    with pytest.raises(ValueError):
        docs_check.hand_type_sum(path)


# --- 단축키 대장 (W-39) ----------------------------------------------------
#
# 키 목록이 저장소 안에 두 벌이다. 루트 README는 저장소를 여는 사람이 보고,
# 사용 안내는 배포물에 그것만 나가서 뺄 수가 없다. W-04에서 키 이름 표가
# 둘로 갈려 기본 바인딩 셋이 조용히 죽은 적이 있어서, 여기서 못박는다.


def test_단축키가_문서끼리_그리고_소스와_맞는다():
    bad = docs_check.check_keys()
    assert bad == [], "\n".join(bad)


def test_문서_한쪽에서_키가_빠지면_걸린다(monkeypatch):
    real = docs_check.doc_keys
    빠뜨릴_문서 = docs_check.KEY_DOCS[1]

    def 한쪽만_모자라게(rel):
        names = real(rel)
        return names - {"KeyHelp"} if rel == 빠뜨릴_문서 else names

    monkeypatch.setattr(docs_check, "doc_keys", 한쪽만_모자라게)
    bad = docs_check.check_keys()
    assert any("KeyHelp" in line for line in bad), bad


def test_소스에만_있는_키가_잡힌다(monkeypatch):
    if docs_check.source_keys() is None:
        pytest.skip("vendor를 못 받은 상태")
    문서에_있는_것 = docs_check.doc_keys(docs_check.KEY_DOCS[0])
    monkeypatch.setattr(
        docs_check, "source_keys", lambda: 문서에_있는_것 | {"KeyNieDokumentiert"}
    )
    bad = docs_check.check_keys()
    assert any("KeyNieDokumentiert" in line for line in bad), bad


def test_vendor가_없으면_문서끼리만_본다(monkeypatch):
    # 권한 없이 클론하면 vendor가 안 받아진다. 그때도 두 문서 대조는 돌아야
    # 한다 - 소스를 못 봐도 문서끼리 갈라진 것은 잡을 수 있다.
    monkeypatch.setattr(docs_check, "source_keys", lambda: None)
    assert docs_check.check_keys() == []
