"""문서가 실제와 어긋나면 빨개진다.

막는 사고는 하나다 - **문서가 조용히 낡는 것.** 커밋 훅 C8은 현황판을
*건드렸나*만 보고, 그 밖의 문서는 아예 안 본다. 그래서 실제로 이렇게 됐다.

- `README.md`가 12커밋 동안 "한국어화는 아직 시작 전"이라고 적고 있었다
- 현황판 §1이 "남은 것은 캐릭터 생성 하나"인데 §2에 P1이 셋 열려 있었다
- `675쌍`·`C1~C8`·`40곳`이 네 문서에 손으로 복사돼 원본과 갈라졌다

아래 테스트는 두 갈래다. **지금 저장소가 맞나**(늘 도는 것)와 **어긋났을 때
정말 걸리나**(합성 문서로 실증). 둘째가 없으면 검사가 죽었는지 알 수 없다.
"""

from pathlib import Path

import docs_check
import pytest


# --- 지금 저장소 - 늘 돈다 -------------------------------------------------


def test_문서와_산출물이_맞는다():
    bad = docs_check.check_citations()
    assert bad == [], "\n".join(bad)


def test_현황판_절끼리_안_어긋난다():
    bad = docs_check.check_board()
    assert bad == [], "\n".join(bad)


def test_손_케이스_숫자_셋의_관계():
    # 41 = 40 + 1(`Pick` 헬퍼 선언)은 `check_citations`가 이미 본다. 여기는
    # 도구에 없는 관계만 남긴다 - 40(볼 자리) = 35(옮긴 자리) + 5(W-12 몫).
    got = docs_check.facts()
    assert got["손으로 옮긴 자리"] == got["손으로 볼 자리"] - 5


def test_손_케이스_커밋이_아직_거기_있다():
    # 커밋 제목이 바뀌면 조용히 0을 세는 대신 ko_words.hand_commit이 소리를
    # 낸다. 여기서는 세어진 값이 실재하는지만 못박는다.
    assert docs_check.hand_sites() > 0


# --- 어긋났을 때 정말 걸리나 - 합성 문서 -----------------------------------

#: 절 제목은 **도구가 가진 상수를 쓴다.** 판을 재편하면 번호가 바뀌는데
#: (실제로 §9가 §7이 됐다), 여기 손으로 적어 두면 그날 합성 판 테스트가
#: 통째로 죽는다 - 검사한 적도 없는 것을 고치느라 시간을 쓰게 된다.
HEAD = """# 판

## 1. 지금

- 다음: {next}
- 막힘: {blocked}

""" + docs_check.OPEN_HEADING + """

| ID | 제목 | 우선 | 상태 | 비고 |
|----|------|------|------|------|
{rows}

""" + docs_check.DONE_HEADING + """

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


# --- 상태값 화이트리스트 ----------------------------------------------------


def test_모르는_상태값을_잡는다(tmp_path):
    # `완료`는 §9로 옮기라고 막는데, 같은 뜻을 `끝`이라고 적으면 그 검사도
    # 열림 검사도 안 걸리고 표에 남는다. 값 자체를 막아야 우회가 안 된다.
    text = board(["| W-01 | 하나 | P1 | 끝 | |", "| W-02 | 둘 | P2 | 막힘 | |"])
    bad = docs_check.check_board(write(tmp_path, text))
    assert any("모르는 상태값" in item and "W-01" in item for item in bad), bad


def test_아는_상태값은_통과한다(tmp_path):
    rows = [f"| W-0{n} | 것 | P{n} | {state} | |"
            for n, state in enumerate(("대기", "진행", "막힘", "버림"), start=1)]
    text = board(rows, next_="**W-01**", blocked="`W-03`", done="- 없음")
    assert [b for b in docs_check.check_board(write(tmp_path, text))
            if "모르는 상태값" in b] == []


# --- 문서 위생 --------------------------------------------------------------


def _docs(tmp_path, name, body):
    root = tmp_path / "docs"
    (root / Path(name).parent).mkdir(parents=True, exist_ok=True)
    (root / name).write_text(body, encoding="utf-8")
    return tmp_path


def test_제어_문자를_잡는다(tmp_path):
    # 화면에 아무것도 안 그리면서 검색과 비교만 어긋나게 한다.
    bad = docs_check.check_control_chars(_docs(tmp_path, "a.md", "앞\x0c뒤\n"))
    assert any("제어 문자" in item and "a.md:1" in item for item in bad), bad


def test_탭과_줄바꿈은_제어_문자가_아니다(tmp_path):
    assert docs_check.check_control_chars(_docs(tmp_path, "a.md", "앞\t뒤\r\n")) == []


def test_링크_글자가_대상과_다르면_잡는다(tmp_path):
    # 문서를 옮기면 경로는 고치는데 글자는 안 고친다. 링크는 열리고 본문만
    # 없는 이름을 부른다.
    root = _docs(tmp_path, "a.md", "[옛이름.md](sub/새이름.md)를 본다\n")
    bad = docs_check.check_link_names(root)
    assert any("옛이름.md" in item for item in bad), bad


def test_이름이_같으면_경로가_달라도_통과한다(tmp_path):
    root = _docs(tmp_path, "a.md", "[status.md](../docs/status.md)\n")
    assert docs_check.check_link_names(root) == []


def test_앵커가_붙어도_이름으로_본다(tmp_path):
    root = _docs(tmp_path, "a.md", "[sync.md](upstream/sync.md#3-절)\n")
    assert docs_check.check_link_names(root) == []


def test_파일_이름이_아닌_링크_글자는_안_본다(tmp_path):
    root = _docs(tmp_path, "a.md", "[동기화 절차](upstream/sync.md)\n")
    assert docs_check.check_link_names(root) == []


def test_바깥_주소는_안_본다(tmp_path):
    root = _docs(tmp_path, "a.md", "[README.md](https://example.invalid/x.md)\n")
    assert docs_check.check_link_names(root) == []


def test_폐기값이_남아_있으면_잡는다(tmp_path, monkeypatch):
    monkeypatch.setattr(docs_check, "RETIRED_VALUES", (("골든 쌍", "688"),))
    bad = docs_check.check_retired(_docs(tmp_path, "a.md", "골든 688쌍을 대조한다\n"))
    assert any("688" in item for item in bad), bad


def test_다른_수에_섞인_폐기값은_안_잡는다(tmp_path, monkeypatch):
    # `46,688색`의 688은 다른 수다. 앞뒤에 숫자나 쉼표가 붙으면 건너뛴다.
    monkeypatch.setattr(docs_check, "RETIRED_VALUES", (("골든 쌍", "688"),))
    assert docs_check.check_retired(_docs(tmp_path, "a.md", "팔레트 46,688색\n")) == []
    assert docs_check.check_retired(_docs(tmp_path, "a.md", "6885개\n")) == []


def test_동결_문서의_폐기값은_그때_그대로다(tmp_path, monkeypatch):
    # 날짜가 박힌 기록과 동결 문서는 지금 값으로 맞추면 기록이 아니게 된다.
    monkeypatch.setattr(docs_check, "RETIRED_VALUES", (("골든 쌍", "688"),))
    root = _docs(tmp_path, "frozen/old.md", "그때는 688쌍이었다\n")
    assert docs_check.check_retired(root) == []


# --- 지금 저장소 ------------------------------------------------------------


def test_지금_문서에_제어_문자가_없다():
    bad = docs_check.check_control_chars()
    assert bad == [], "\n".join(bad)


# --- 절 제목·닫힌 ID·양쪽 중복 (W-49 재편에서 붙었다) ----------------------


def test_절_제목을_못_찾으면_소리를_낸다():
    """`split(...)[-1]`은 못 찾을 때 문서 전체를 돌려준다.

    그러면 결번 검사가 §2의 ID를 전부 "닫힌 것"으로 세고 **오류 없이 영원히
    통과한다.** 이 도구가 막으려던 실패와 같은 모양이라, 조용히 넘어가면 안 된다.
    """
    with pytest.raises(ValueError, match="절을 못 찾았다"):
        docs_check._section("# 판\n\n## 1. 지금\n\n아무것도 없다\n", docs_check.DONE_HEADING)


def test_닫힌_ID는_여는_괄호_뒤만_센다():
    """산문에 스쳐 지나간 ID는 안 닫는다. W-35가 그렇게 묻혔다."""
    text = (
        "# 판\n\n"
        + docs_check.DONE_HEADING
        + "\n\n"
        "- **2026-08-19** 무엇을 했다 (W-11, [vendor.md](upstream/vendor.md))\n"
        "- **2026-08-19** 둘을 했다 (W-33·W-34, `overlay/patches/0015`)\n"
        "- **2026-08-19** 문제를 찾아 `W-35`로 올렸다\n"
        "- **2026-08-19** 커밋 강제(C8) — 이 문서\n"
    )
    # 마크다운 링크로 끝나는 줄도 잡혀야 한다. 줄 끝 `)`로 고정하면 링크의
    # 괄호 때문에 통째로 안 잡힌다 - 실제로 열아홉 줄이 그렇게 샜다.
    assert docs_check.done_ids(text) == {"W-11", "W-33", "W-34"}


def test_열린_ID를_끝난것절이_닫았다고_적으면_걸린다(tmp_path):
    text = board(
        ["| W-01 | 하나 | P1 | 진행 | |", "| W-02 | 둘 | P2 | 막힘 | |"],
        next_="**W-01**",
        done="- 무엇을 했다 (W-01, 링크)\n- 또 했다 (W-02, 링크)",
    )
    bad = docs_check.check_board(write(tmp_path, text))
    assert any("§2에 열려 있는데 §7이 닫았다" in b and "W-01" in b for b in bad), bad


def test_마일스톤을_본문으로_가리키면_통과한다(tmp_path):
    """§8의 규약대로 괄호를 빼면 §2와 §7이 안 부딪힌다."""
    text = board(
        ["| W-01 | 하나 | P1 | 진행 | |", "| W-02 | 둘 | P2 | 막힘 | |"],
        next_="**W-01**",
        done="- 1단계를 끝냈다. 남은 것은 §2 W-01\n- 둘도 했다. 남은 것은 §2 W-02",
    )
    assert docs_check.check_board(write(tmp_path, text)) == []
