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
