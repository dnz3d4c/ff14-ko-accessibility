"""문자열 스냅샷 도구 테스트.

이 도구가 하는 일은 하나다 - 한국어화가 독일어·영어를 건드리면 알려주는 것.
그러니 테스트도 "바뀐 걸 잡는가"를 본다.
"""

import json

import pytest
import strings_golden


def pairs(src: str):
    got, _ = strings_golden.extract(src, "x.cs")
    return [(p.de, p.en) for p in got]


def missed(src: str):
    _, bad = strings_golden.extract(src, "x.cs")
    return bad


# --- 뽑기 -----------------------------------------------------------------


def test_한_줄_삼항을_뽑는다():
    src = 'public static string A => IsGerman ? "Titel" : "Title";'
    assert pairs(src) == [("Titel", "Title")]


def test_줄바꿈된_삼항도_뽑는다():
    src = 'public static string A => IsGerman\n    ? "Zurück"\n    : "Back";'
    assert pairs(src) == [("Zurück", "Back")]


def test_보간_자리를_그대로_남긴다():
    # 번역할 때 지켜야 할 자리다. 이름이 바뀌면 컴파일이 깨지므로 여기 보존이 중요.
    src = 'IsGerman ? $"{item}, {index} von {count}" : $"{item}, {index} of {count}";'
    assert pairs(src) == [
        ("{item}, {index} von {count}", "{item}, {index} of {count}")
    ]


def test_이스케이프된_따옴표를_삼키지_않는다():
    src = r'IsGerman ? "sagt \"ja\"" : "says \"yes\"";'
    de, en = pairs(src)[0]
    assert de.endswith(r'\"') and "sagt" in de and "says" in en


def test_삼항이_아닌_IsGerman은_무시한다():
    # 선언, 주석, 위임에 걸리면 안 된다.
    src = "public static bool IsGerman => Loc.IsGerman;\n// IsGerman entscheidet"
    assert pairs(src) == []
    assert missed(src) == []


# --- 못 읽은 것을 숨기지 않는다 --------------------------------------------


def test_중첩_삼항은_미해석으로_보고한다():
    # 조용히 빠뜨리면 번역에서 통째로 누락된다. 세어서 드러낸다.
    src = 'IsGerman ? $"{n}, {(on ? "an" : "aus")}" : $"{n}, {(on ? "on" : "off")}";'
    assert pairs(src) == []
    assert len(missed(src)) == 1


def test_배열은_미해석으로_보고한다():
    src = 'IsGerman ? new[] { "Erfahrung" } : new[] { "EXP" };'
    assert pairs(src) == []
    assert len(missed(src)) == 1


def test_미해석은_파일과_줄을_남긴다():
    src = "\n\nIsGerman ? Foo : Bar;"
    item = missed(src)[0]
    assert item.file == "x.cs" and item.line == 3


# --- 실제 저장소 ----------------------------------------------------------

needs_source = pytest.mark.skipif(
    not strings_golden.SOURCE_ROOT.is_dir(), reason="vendor 클론이 없다"
)


@needs_source
def test_골든이_지금_소스와_같다():
    # 한국어화 도중 독일어/영어가 바뀌면 여기가 빨개진다.
    golden = json.loads(strings_golden.GOLDEN.read_text(encoding="utf-8"))
    assert golden["by_file"] == strings_golden.build()["by_file"]


@needs_source
def test_미해석_개수가_늘지_않았다():
    # 늘었으면 새 형태가 생긴 것이다. 손으로 봐야 한다.
    golden = json.loads(strings_golden.GOLDEN.read_text(encoding="utf-8"))
    _, now = strings_golden.scan()
    assert len(now) <= golden["unparsed"]


# --- Pick(...)로 옮긴 뒤에도 같은 쌍이 나와야 한다 --------------------------
#
# 번역은 `IsGerman ? de : en`을 `Pick(de, en, ko)`로 바꾸는 일이다. 스냅샷이
# 삼항만 읽으면 옮긴 줄마다 "문장이 사라졌다"고 하고, 676번 그러면 아무도
# 안 본다. 모양이 바뀌어도 독일어·영어 쌍은 그대로 잡혀야 한다.


def test_Pick_두_인자를_쌍으로_읽는다():
    assert pairs('Pick("Zurück", "Back")') == [("Zurück", "Back")]


def test_Pick_한국어까지_있어도_독영_쌍은_그대로():
    # 한국어가 붙었다고 독일어/영어가 바뀐 건 아니다.
    assert pairs('Pick("Zurück", "Back", "뒤로")') == [("Zurück", "Back")]


def test_Loc_붙은_호출도_읽는다():
    assert pairs('Loc.Pick("Ja", "Yes", "예")') == [("Ja", "Yes")]


def test_보간_Pick도_읽는다():
    assert pairs('Pick($"{n} von {c}", $"{n} of {c}", $"{c}개 중 {n}")') == [
        ("{n} von {c}", "{n} of {c}")
    ]


def test_삼항에서_Pick으로_옮겨도_쌍이_같다():
    before = 'public static string A => IsGerman ? "Titel" : "Title";'
    after = 'public static string A => Pick("Titel", "Title", "제목");'
    assert pairs(before) == pairs(after)


def test_Pick이라는_다른_이름은_안_읽는다():
    # PickItem 같은 게 있어도 걸리면 안 된다.
    assert pairs('PickItem("a", "b")') == []


def test_문자열이_아닌_Pick은_미해석으로_센다():
    assert pairs('Pick(t.De, t.En, t.Ko)') == []
    assert len(missed('Pick(t.De, t.En, t.Ko)')) == 1


def test_Pick_정의부는_호출이_아니다():
    # `public static string Pick(string de, ...)`는 선언이지 호출이 아니다.
    # 이걸 미해석으로 세면 개수가 영원히 하나 부풀어 있다.
    src = 'public static string Pick(string de, string en, string? ko = null) => 1;'
    assert pairs(src) == []
    assert missed(src) == []


# --- 주석은 코드가 아니다 --------------------------------------------------
#
# 주석에 `IsGerman ? de : en` 같은 예시를 적으면 검사기가 그걸 코드로 읽어
# 미해석 개수를 부풀린다. 개수가 신호라서, 가짜로 늘면 진짜 증가를 못 본다.


def test_한줄_주석_속_예시는_안_읽는다():
    src = '// moves from "IsGerman ? de : en" to "Pick(de, en, ko)"\n'
    assert pairs(src) == []
    assert missed(src) == []


def test_문서_주석_속_예시도_안_읽는다():
    src = '/// <summary>IsGerman ? "a" : "b" 를 Pick("a", "b", "가")로 옮긴다.</summary>\n'
    assert pairs(src) == []
    assert missed(src) == []


def test_블록_주석_속_예시도_안_읽는다():
    src = '/*\n IsGerman ? "a" : "b"\n Pick("a", "b")\n*/\n'
    assert pairs(src) == []
    assert missed(src) == []


def test_주석을_지워도_진짜_코드는_남는다():
    src = '// IsGerman ? "주석" : "comment"\npublic static string A => Pick("Ja", "Yes", "예");'
    assert pairs(src) == [("Ja", "Yes")]


def test_문자열_안의_슬래시두개는_주석이_아니다():
    # URL 같은 게 문자열에 들어 있어도 거기서 잘리면 안 된다.
    src = 'Pick("http://a.de/x", "http://a.com/x", "http://a.kr/x");'
    assert pairs(src) == [("http://a.de/x", "http://a.com/x")]


def test_미해석_41개_중_하나는_축약_정의다():
    # 진짜 손으로 옮길 자리는 40개다. 나머지 하나는 Pick 축약이 Loc.Pick으로
    # 넘기는 줄이라 문장이 아니다. 이걸 적어 두지 않으면 다음 사람이 41개를
    # 다 뒤진다.
    _, now = strings_golden.scan()
    forwarding = [u for u in now if u.snippet.startswith("Pick(de, en, ko)")]
    assert len(forwarding) == 1
    assert len(now) - len(forwarding) == 40
