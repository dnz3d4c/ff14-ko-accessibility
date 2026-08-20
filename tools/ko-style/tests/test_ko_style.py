"""문서 말투가 갈리는 것과 걷어낸 표현이 되살아나는 것을 잡는다.

막는 사고는 하나다 - **문장 품질에만 기계 검사가 0개였다.** 그래서 같은 지적이
반복해서 왔고, 2026-08-20에 사용자가 `README.md` 14자리를 직접 고쳤다.

두 갈래를 따로 시험한다. 말투는 `아니다`를 습니다체로 잘못 세는 함정이 있고,
금지 표현은 인용을 본문으로 잘못 세는 함정이 있다. 한 규칙으로 묶으면 오탐이
섞여 둘 다 죽는다.
"""

import ko_style
import pytest

REPO = ko_style.REPO


# ------------------------------------------------------------ 말투 판정


@pytest.mark.parametrize(
    "word",
    ["합니다", "있습니다", "입니다", "봅니다", "아닙니다", "됩니다"],
)
def test_ㅂ받침이_있으면_습니다체다(word):
    assert ko_style.register_of(word) == "습니다체"


@pytest.mark.parametrize(
    "word",
    ["아니다", "한다", "된다", "이다", "있다", "없다", "같다", "만든다"],
)
def test_ㅂ받침이_없으면_한다체다(word):
    assert ko_style.register_of(word) == "한다체"


def test_아니다를_습니다체로_세지_않는다():
    # `니다`로 끝나는지만 보면 여기서 무너진다. 실측에서 개발 문서 다섯의
    # "습니다체" 22건이 전부 `아니다`였다.
    assert ko_style.register_of("아니다") != ko_style.register_of("아닙니다")


@pytest.mark.parametrize("word", ["함", "됨", "키", "Dalamud", ""])
def test_종결이_아니면_안_센다(word):
    assert ko_style.register_of(word) is None


# ------------------------------------------------------------ 세는 범위


def test_코드_블록은_안_센다():
    text = "먼저 확인합니다.\n```\nreturn 0;\n이것은 코드다.\n```\n다음을 봅니다."
    assert [kind for _, kind in ko_style.endings(text)] == ["습니다체", "습니다체"]


@pytest.mark.parametrize(
    "line",
    ["> 인용한 문장이다.", "| 표 | 안이다 |", "# 제목이다"],
)
def test_인용과_표와_제목은_안_센다(line):
    assert ko_style.endings(line) == []


def test_인라인_코드는_문장에서_뺀다():
    # 명령어와 키 이름이 한글 종결처럼 보이면 안 된다.
    assert ko_style.endings("`/acc lang ko`") == []


def test_줄_번호를_그대로_돌려준다():
    text = "첫 줄입니다.\n\n셋째 줄이다."
    assert ko_style.endings(text) == [(1, "습니다체"), (3, "한다체")]


# ------------------------------------------------------------ 혼재 검사


def test_저장소가_지금_통과한다():
    assert ko_style.check_register() == []


def test_사용자_문서에_한다체가_한_줄만_섞여도_잡는다(tmp_path, monkeypatch):
    # **임계가 1인 것이 핵심이다.** 2 이상이면 "한 줄만 섞인" 상태가 정상으로
    # 통과하고, 그러면 이 검사가 막으려던 바로 그 자리를 놓친다.
    assert ko_style.MIXED_LIMIT == 1

    (tmp_path / "README.md").write_text(
        "모드를 설치할 수 있습니다.\n이것은 한다체 문장이다.\n", encoding="utf-8"
    )
    monkeypatch.setattr(ko_style, "tracked_docs", lambda repo=None: ["README.md"])
    problems = ko_style.check_register(tmp_path)
    assert len(problems) == 1
    assert "한다체가 1곳" in problems[0]


def test_개발_문서에_습니다체가_섞이면_잡는다(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.md").write_text(
        "이렇게 한다.\n그런데 이 줄은 습니다체입니다.\n", encoding="utf-8"
    )
    monkeypatch.setattr(ko_style, "tracked_docs", lambda repo=None: ["docs/note.md"])
    problems = ko_style.check_register(tmp_path)
    assert len(problems) == 1
    assert "습니다체가 1곳" in problems[0]


def test_한_말투로만_쓰면_통과한다(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text(
        "모드를 설치합니다.\n안내가 한국어로 나옵니다.\n", encoding="utf-8"
    )
    monkeypatch.setattr(ko_style, "tracked_docs", lambda repo=None: ["README.md"])
    assert ko_style.check_register(tmp_path) == []


# ------------------------------------------------------------ 금지 표현


def test_저장소에_걷어낸_표현이_없다():
    assert ko_style.check_banned() == []


def test_걷어낸_표현이_되살아나면_잡는다(tmp_path, monkeypatch):
    monkeypatch.setattr(ko_style, "USER_DOCS", frozenset({"README.md"}))
    (tmp_path / "README.md").write_text(
        "게임에 Dalamud를 붙여 주는 프로그램입니다.\n", encoding="utf-8"
    )
    problems = ko_style.check_banned(tmp_path)
    assert len(problems) == 1
    assert "붙여 주는" in problems[0]
    assert "비유 동사" in problems[0]


def test_인용_안의_표현은_안_잡는다(tmp_path, monkeypatch):
    # 사용 안내가 백틱으로 감싸는 것은 설치 프로그램이 실제로 말하는 문장이다.
    # 여기서 고치면 문서가 실물과 어긋난다 - 2026-08-19에 그 실수를 했다.
    monkeypatch.setattr(ko_style, "USER_DOCS", frozenset({"README.md"}))
    (tmp_path / "README.md").write_text(
        "- `게임에 Dalamud를 붙여 주는 프로그램입니다.`\n", encoding="utf-8"
    )
    assert ko_style.check_banned(tmp_path) == []


def test_대상_문서가_없으면_소리를_낸다(tmp_path, monkeypatch):
    # 조용히 0을 세면 검사가 죽은 것을 아무도 모른다.
    monkeypatch.setattr(ko_style, "USER_DOCS", frozenset({"없는문서.md"}))
    problems = ko_style.check_banned(tmp_path)
    assert len(problems) == 1
    assert "USER_DOCS" in problems[0]


# ------------------------------------------------------------ 목록 위생


def test_금지_표현_목록에_why가_다_있다():
    # `ko-speech` 골든과 같은 규약이다. 근거 없는 줄을 다음 사람이 믿게
    # 두지 않는다.
    assert ko_style.check_banned_entries() == []


def test_금지_표현이_비어_있지_않다():
    assert ko_style.BANNED


# ------------------------------------------------------------ 대상 목록


def test_추적하는_마크다운만_본다():
    docs = ko_style.tracked_docs()
    assert "README.md" in docs
    assert "overlay/ko/README.ko.md" in docs
    # `dist/`는 배포 산출물이라 추적 밖이고, vendor는 업스트림 것이다.
    assert not [d for d in docs if d.startswith(("dist/", "vendor/"))]


def test_사용자_문서가_실재한다():
    for rel in ko_style.USER_DOCS:
        assert (REPO / rel).is_file(), rel
