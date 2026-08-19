"""설치 프로그램 문구가 한국어로 안 나가면 빨개진다.

막는 사고는 넷이고 전부 **조용하다.**

- 한국어 키가 없으면 `Loc.Get`이 영어로 떨어진다(`Loc.cs:29`)
- 어느 사전에도 없으면 **키 이름을 그대로** 돌려준다
- 값이 비면 접두만 붙은 빈 줄이 나간다(`ConfigNotExist4`가 그랬다)
- `Loc.Get`을 아예 안 거치면 어느 언어로도 안 갈린다

아래는 두 갈래다. **규칙이 정말 잡나**(합성 소스로 실증)와 **지금 저장소가
맞나**(늘 도는 것). 둘째만 있으면 검사가 죽었는지 알 수 없다.
"""

import json

import loc_check
import pytest

SOURCE_ROOT = loc_check.SOURCE_ROOT


def loc_source(german: str = "", english: str = "", korean: str = "") -> str:
    """`Loc.cs`의 모양만 갖춘 최소 사전."""
    return f"""
namespace X;
public static class Loc {{
    private static readonly Dictionary<string, Dictionary<string, string>> Texts = new()
    {{
        [German] = new Dictionary<string, string>
        {{
            {german}
        }},
        [English] = new Dictionary<string, string>
        {{
            {english}
        }},
        [Korean] = new Dictionary<string, string>
        {{
            {korean}
        }},
    }};
}}
"""


@pytest.fixture
def world(tmp_path):
    """합성 설치 프로그램 소스. `Loc.cs`와 그걸 부르는 파일 하나."""

    def build(german="", english="", korean="", caller=""):
        (tmp_path / "Loc.cs").write_text(
            loc_source(german, english, korean), encoding="utf-8"
        )
        (tmp_path / "Caller.cs").write_text(
            f"class C {{ void M() {{ {caller} }} }}", encoding="utf-8"
        )
        return tmp_path

    return build


@pytest.fixture
def golden(tmp_path):
    path = tmp_path / "dead.json"

    def write(keys):
        path.write_text(json.dumps({"note": "t", "keys": keys}), encoding="utf-8")
        return path

    write([])
    return write


# --- 사전 읽기 -------------------------------------------------------------


def test_세_사전을_읽는다(world):
    root = world(
        german='["A"] = "eins",', english='["A"] = "one",', korean='["A"] = "하나",'
    )
    got = loc_check.dictionaries(root / "Loc.cs")
    assert got["Korean"]["A"] == "하나"
    assert got["English"]["A"] == "one"
    assert got["German"]["A"] == "eins"


def test_여러_줄로_이어붙인_값을_모은다(world):
    # 긴 문장은 `"앞" +\n"뒤"`로 나뉘어 있다. 빈 값 판정이 여기 걸린다.
    root = world(english='["A"] = "앞" +\n                "뒤",')
    assert loc_check.dictionaries(root / "Loc.cs")["English"]["A"] == "앞뒤"


def test_값_안의_슬래시두개는_주석이_아니다(world):
    # `https://goatcorp.github.io/`가 실제로 들어 있다. 주석으로 읽으면 그
    # 줄이 통째로 지워져 멀쩡한 값이 비었다고 잡힌다.
    root = world(english='["A"] = "가라 https://example.invalid/ 그리고",')
    assert "example.invalid" in loc_check.dictionaries(root / "Loc.cs")["English"]["A"]


def test_주석_속_항목은_안_읽는다(world):
    root = world(english='// ["Ghost"] = "x",\n            ["A"] = "one",')
    assert set(loc_check.dictionaries(root / "Loc.cs")["English"]) == {"A"}


# --- 부르는 키 -------------------------------------------------------------


def test_부르는_키를_모은다(world):
    root = world(caller='var a = Loc.Get("A"); var b = Loc.Get("B", 1);')
    assert set(loc_check.called(root)) == {"A", "B"}


def test_주석_속_호출은_안_센다(world):
    root = world(caller='// Loc.Get("Ghost");\n var a = Loc.Get("A");')
    assert set(loc_check.called(root)) == {"A"}


# --- 검사 1: 한국어가 없다 -------------------------------------------------


def test_부르는데_한국어가_없으면_잡는다(world, golden):
    root = world(
        english='["A"] = "one",', korean="", caller='Info(Loc.Get("A"));'
    )
    bad = loc_check.check(root, golden([]))
    assert any("한국어가 없어 영어로 나간다" in line and "A" in line for line in bad), bad


def test_한국어가_있으면_통과한다(world, golden):
    root = world(
        english='["A"] = "one",', korean='["A"] = "하나",', caller='Info(Loc.Get("A"));'
    )
    assert loc_check.check(root, golden([])) == []


def test_안_부르는_키는_골든이_맡는다(world, golden):
    # 화면에 안 나가므로 결함이 아니다. 늘어나는 것만 막는다.
    root = world(english='["Dead"] = "one",', korean="", caller="")
    assert loc_check.check(root, golden(["Dead"])) == []


# --- 검사 2: 어느 사전에도 없다 --------------------------------------------


def test_사전에_없는_키를_부르면_잡는다(world, golden):
    # `Loc.Get`이 키 이름을 그대로 돌려준다. 영어보다 나쁘다.
    root = world(caller='Info(Loc.Get("NieDefiniert"));')
    bad = loc_check.check(root, golden([]))
    assert any("어느 사전에도 없다" in line for line in bad), bad


# --- 검사 3: 값이 비었다 ---------------------------------------------------


def test_한국어_값이_비면_잡는다(world, golden):
    # `ConfigNotExist4`가 이 모양이었다. 키가 있어서 폴백도 안 탄다.
    root = world(
        english='["A"] = "one",', korean='["A"] = "",', caller='Info(Loc.Get("A"));'
    )
    bad = loc_check.check(root, golden([]))
    assert any("값이 비어 있다" in line and "Korean" in line for line in bad), bad


def test_공백뿐인_값도_빈_값이다(world, golden):
    root = world(
        english='["A"] = "one",', korean='["A"] = "   ",', caller='Info(Loc.Get("A"));'
    )
    assert any("값이 비어 있다" in line for line in loc_check.check(root, golden([])))


# --- 검사 4: `Loc.Get` 밖 리터럴 -------------------------------------------


def test_말하는_호출의_맨_리터럴을_잡는다():
    got = loc_check.scan_text('class C { void M() { Info("Fertig."); } }', "C.cs")
    assert [f.text for f in got] == ["Fertig."]
    assert [f.rule for f in got] == [loc_check.SPOKEN]


def test_움라우트는_어디_있든_잡는다():
    got = loc_check.scan_text('class C { void M() { var s = "Gewölbe"; } }', "C.cs")
    assert [f.text for f in got] == ["Gewölbe"]
    assert [f.rule for f in got] == [loc_check.UMLAUT]


def test_Loc_Get을_거치면_안_잡는다():
    assert loc_check.scan_text('class C { void M() { Info(Loc.Get("Done")); } }', "C.cs") == []


def test_말하는_호출이_아니면_안_잡는다():
    # 파일 이름·설정 키 같은 식별자다. 발화가 아니다.
    assert loc_check.scan_text('class C { void M() { Open("config.json"); } }', "C.cs") == []


def test_글자가_없는_리터럴은_안_잡는다():
    # `Info("  " + path)`가 실제로 있다. 들여쓰기지 문장이 아니다.
    assert loc_check.scan_text('class C { void M() { Info("  " + p); } }', "C.cs") == []


def test_주석_속_예시는_안_잡는다():
    assert loc_check.scan_text('class C {\n // Info("Fertig.");\n void M() { } }', "C.cs") == []


def test_밖의_리터럴이_검사에_올라온다(world, golden):
    root = world(caller='Info("Fertig.");')
    bad = loc_check.check(root, golden([]))
    assert any("`Loc.Get` 밖의 리터럴" in line for line in bad), bad


# --- 검사 5: 죽은 키 골든 --------------------------------------------------


def test_죽은_키가_늘면_잡는다(world, golden):
    root = world(english='["Dead"] = "one",', korean="", caller="")
    bad = loc_check.check(root, golden([]))
    assert any("새로 생겼다" in line and "Dead" in line for line in bad), bad


def test_골든에만_남으면_갱신하라고_한다(world, golden):
    root = world(english='["A"] = "one",', korean='["A"] = "하나",', caller="")
    bad = loc_check.check(root, golden(["Gone"]))
    assert any("골든에만 남은" in line for line in bad), bad


def test_죽은_키를_센다(world):
    root = world(
        english='["A"] = "one",\n            ["Dead"] = "two",',
        korean='["A"] = "하나",',
        caller='Info(Loc.Get("A"));',
    )
    entries = loc_check.dictionaries(root / "Loc.cs")
    assert loc_check.dead_keys(entries, loc_check.called(root)) == ["Dead"]


# --- 지금 저장소 - 늘 돈다 -------------------------------------------------

needs_source = pytest.mark.skipif(
    not SOURCE_ROOT.is_dir(), reason="vendor 클론이 없다"
)


@needs_source
def test_지금_저장소가_통과한다():
    bad = loc_check.check()
    assert bad == [], "\n".join(bad)


@needs_source
def test_골든이_정렬돼_있고_중복이_없다():
    keys = loc_check.load_golden()
    assert keys == sorted(set(keys)), "정렬·중복 제거해서 저장한다 - diff가 읽히게"


@needs_source
def test_실물에서_사전을_실제로_읽는다():
    """파서가 배선만 되고 0개를 읽으면 위 검사들이 전부 조용히 통과한다.

    **README `## 한계` 4가 기대는 자리다.** 사전과 호출부를 동시에 못 읽으면
    0 대 0이라 아무 말도 안 나오는데, 그걸 막는 것이 이 테스트뿐이다.
    지우면 위 검사 넷이 조용히 무의미해진다.
    """
    entries = loc_check.dictionaries()
    assert len(entries["Korean"]) > 100
    assert len(entries["English"]) >= len(entries["Korean"])
    assert len(loc_check.called()) > 100


# --- 한계가 정말 그 모양인가 (README `## 한계`) -----------------------------
#
# 한계를 글로만 적어 두면 낡는다. 이 저장소는 그걸 겪었다 - `ko-words`
# README의 한계를 검수가 인용까지 해 놓고 결론에 반영하지 않았다. 여기서는
# 적어 둔 것이 지금도 사실인지를 검사가 지킨다.


def test_한계1_말하는_호출_밖은_안_본다():
    # README 1: `MessageBox`·`Text`·`AccessibleName`은 이 검사 밖이다.
    # 초록이라고 "안내가 다 한국어다"가 아니라는 근거.
    for source in (
        'class C { void M() { MessageBox.Show("Fertig"); } }',
        'class C { void M() { var b = new Button { Text = "설치" }; } }',
        'class C { void M() { var b = new Button { AccessibleName = "설치" }; } }',
    ):
        assert loc_check.scan_text(source, "C.cs") == [], source


def test_한계3_변수로_넘긴_키는_집계에서_빠진다(world, golden):
    # README 3: `Loc.Get(key)`는 "안 불린다"로 분류되고, 한국어가 없어도
    # 죽은 키 골든이 통과시킨다. **조용히 새는 유일한 갈래다.**
    root = world(english='["A"] = "one",', korean="", caller="Info(Loc.Get(key));")
    assert loc_check.called(root) == {}
    assert loc_check.check(root, golden(["A"])) == []


def test_한계4_사전_블록을_못_찾으면_죽는다(tmp_path):
    # README 4: 조용히 0개가 되는 게 아니라 예외로 죽는다.
    (tmp_path / "Loc.cs").write_text("public static class Loc { }", encoding="utf-8")
    with pytest.raises(ValueError):
        loc_check.dictionaries(tmp_path / "Loc.cs")


def test_한계4_항목_모양만_바뀌면_전부_정의없음으로_걸린다(world, golden):
    # README 4: 사전이 0개가 돼도 부르는 키가 있으면 시끄럽다.
    root = world(english='{ "A", "one" },', korean="", caller='Info(Loc.Get("A"));')
    assert loc_check.dictionaries(root / "Loc.cs")["English"] == {}
    bad = loc_check.check(root, golden([]))
    assert any("어느 사전에도 없다" in line for line in bad), bad
