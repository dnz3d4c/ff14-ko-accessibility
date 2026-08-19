"""한국어 적용기 테스트.

이 도구가 하는 일은 하나다 - **한국어가 소스에 손으로 들어가지 못하게** 막는
것. 카탈로그(`overlay/ko/ko.json`)가 유일한 원본이고 C# 쪽은 생성물이다.

그러니 테스트도 두 방향을 본다.

- 카탈로그에 있는 것만 소스에 들어가는가
- 카탈로그에 없는 것은 **한 자도 안 건드리는가** (독일어·영어 보존)
"""

import json

import ko_apply
import pytest
import strings_golden


def cat(*rows: tuple[str, str, str]) -> dict[tuple[str, str], str]:
    return {(de, en): ko for de, en, ko in rows}


def apply(src: str, catalog: dict[tuple[str, str], str]) -> str:
    return ko_apply.rewrite(src, catalog).text


# --- 옮긴다 ----------------------------------------------------------------


def test_단순_삼항을_Pick_세_인자로_바꾼다():
    src = 'public static string A => IsGerman ? "Titel" : "Title";'
    got = apply(src, cat(("Titel", "Title", "제목")))
    assert got == 'public static string A => Pick("Titel", "Title", "제목");'


def test_줄바꿈된_삼항도_바꾼다():
    src = 'string A =>\n    IsGerman\n        ? "Zurück"\n        : "Back";'
    got = apply(src, cat(("Zurück", "Back", "뒤로")))
    assert got == 'string A =>\n    Pick("Zurück", "Back", "뒤로");'


def test_두_인자_Pick을_세_인자로_채운다():
    # 그릇만 먼저 깔고 한국어는 나중에 오는 경우.
    src = 'string A => Pick("Ja", "Yes");'
    got = apply(src, cat(("Ja", "Yes", "예")))
    assert got == 'string A => Pick("Ja", "Yes", "예");'


def test_이미_같은_값이면_안_건드린다():
    src = 'string A => Pick("Ja", "Yes", "예");'
    assert apply(src, cat(("Ja", "Yes", "예"))) == src


def test_소스와_카탈로그가_다르면_카탈로그가_이긴다():
    # 소스를 손으로 고쳐 놓는 경로를 막는다. 원본은 하나여야 한다.
    src = 'string A => Pick("Ja", "Yes", "손으로 고침");'
    got = apply(src, cat(("Ja", "Yes", "예")))
    assert got == 'string A => Pick("Ja", "Yes", "예");'


def test_같은_문장이_여러_자리에_있으면_전부_바꾼다():
    src = 'string A => IsGerman ? "Gruppe" : "Party";\nstring B => IsGerman ? "Gruppe" : "Party";'
    got = apply(src, cat(("Gruppe", "Party", "파티")))
    assert got.count('Pick("Gruppe", "Party", "파티")') == 2


# --- 표기를 따라간다 -------------------------------------------------------
#
# 파일마다 관례가 다르다. `AccessibilityStrings.cs`는 축약 `IsGerman`을 두고
# 쓰고, `Compat/CompatReport.cs`는 `Loc.IsGerman`을 그대로 쓴다. 생성기가
# 한쪽으로 통일해 버리면 안 쓰던 표기가 파일에 섞여 들어간다.


def test_Loc_붙은_삼항은_Loc_붙여_되쓴다():
    src = 'string A => Loc.IsGerman ? "Ja" : "Yes";'
    got = apply(src, cat(("Ja", "Yes", "예")))
    assert got == 'string A => Loc.Pick("Ja", "Yes", "예");'


def test_Loc_없는_삼항은_축약으로_되쓴다():
    src = 'string A => IsGerman ? "Ja" : "Yes";'
    got = apply(src, cat(("Ja", "Yes", "예")))
    assert got == 'string A => Pick("Ja", "Yes", "예");'


def test_이미_Loc_Pick이면_그대로_유지한다():
    src = 'string A => Loc.Pick("Ja", "Yes");'
    got = apply(src, cat(("Ja", "Yes", "예")))
    assert got == 'string A => Loc.Pick("Ja", "Yes", "예");'


# --- 축약 선언 -------------------------------------------------------------
#
# 축약도 생성물이다 - 손으로 넣어 두면 다시 만들 때 이 줄만 손편집으로 남는다.
#
# **클래스에 하나지 파일에 하나가 아니다.** AccessibilityStrings는 partial이라
# Chat.cs 조각이 선언 없이 축약을 쓴다. 파일마다 넣으면 같은 멤버를 두 번
# 선언해서 컴파일이 깨진다.

HEAD = "public static partial class S\n{\n    private static bool IsGerman => Loc.IsGerman;\n"


def test_선언이_없으면_닻_다음에_넣는다():
    got, problem = ko_apply.ensure_shorthand(HEAD + "}\n")
    assert problem is None
    assert got.count("private static string Pick") == 1
    assert got.index("private static string Pick") > got.index("private static bool IsGerman")


def test_선언이_이미_있으면_안_늘린다():
    src = HEAD + ko_apply.SHORTHAND + "}\n"
    got, problem = ko_apply.ensure_shorthand(src)
    assert problem is None
    assert got == src


def test_닻이_없으면_아무_데나_안_넣는다():
    got, problem = ko_apply.ensure_shorthand("class S {\n}\n")
    assert problem
    assert "Pick" not in got


def test_축약을_쓰는_자리를_알아본다():
    assert ko_apply.uses_shorthand('string A => Pick("Ja", "Yes", "예");')
    assert not ko_apply.uses_shorthand('string A => Loc.Pick("Ja", "Yes", "예");')
    # 아직 한국어가 안 붙은 자리는 축약을 쓰는 게 아니다.
    assert not ko_apply.uses_shorthand('string A => IsGerman ? "Ja" : "Yes";')


def test_partial_조각에는_선언을_안_넣는다(tmp_path):
    # 이게 이 도구가 실제로 부딪히는 자리다. Chat.cs가 그 조각이다.
    catalog = tmp_path / "ko.json"
    catalog.write_text(
        json.dumps({"strings": [
            {"de": "Ja", "en": "Yes", "ko": "예"},
            {"de": "Nein", "en": "No", "ko": "아니오"},
        ]}),
        encoding="utf-8",
    )
    root = tmp_path / "src"
    root.mkdir()
    (root / "S.cs").write_text(
        HEAD + '\n    string A => IsGerman ? "Ja" : "Yes";\n}\n', encoding="utf-8"
    )
    (root / "S.Chat.cs").write_text(
        'public static partial class S\n{\n    string B => IsGerman ? "Nein" : "No";\n}\n',
        encoding="utf-8",
    )

    _, changed, _ = ko_apply._sweep(ko_apply.load_catalog(catalog), root)
    texts = {path.name: text for path, text in changed}
    assert texts["S.cs"].count("private static string Pick") == 1
    assert "private static string Pick" not in texts["S.Chat.cs"]
    assert 'Pick("Nein", "No", "아니오")' in texts["S.Chat.cs"]


# --- 안 건드린다 ----------------------------------------------------------


def test_카탈로그에_없으면_그대로_둔다():
    # W-06이 도는 동안 대부분이 이 상태다. 손 안 댄 자리가 영어로 나가야 한다.
    src = 'string A => IsGerman ? "Titel" : "Title";'
    assert apply(src, cat(("Ja", "Yes", "예"))) == src


def test_주석_속_예시는_안_건드린다():
    src = '// IsGerman ? "Ja" : "Yes" 는 예시다\nstring A => 1;'
    assert apply(src, cat(("Ja", "Yes", "예"))) == src


def test_못_읽는_모양은_안_건드린다():
    # 중첩 삼항 - 손으로 옮길 40곳이다. 여기 손대면 컴파일이 깨진다.
    src = 'string A => IsGerman ? $"{n} von {(x ? "a" : "b")}" : $"{n} of {(x ? "a" : "b")}";'
    assert apply(src, cat(("Ja", "Yes", "예"))) == src


def test_독일어_영어는_한_자도_안_바뀐다():
    # 골든이 지키는 불변이다. 옮긴 뒤에도 쌍이 그대로여야 한다.
    src = 'string A => IsGerman ? $"Stufe {n}" : $"Level {n}";'
    got = apply(src, cat(("Stufe {n}", "Level {n}", "레벨 {n}")))
    before, _ = strings_golden.extract(src, "x.cs")
    after, _ = strings_golden.extract(got, "x.cs")
    assert [(p.de, p.en) for p in before] == [(p.de, p.en) for p in after]


# --- 보간 자리 -------------------------------------------------------------


def test_보간이_있으면_달러를_붙인다():
    src = 'string A => IsGerman ? $"Stufe {n}" : $"Level {n}";'
    got = apply(src, cat(("Stufe {n}", "Level {n}", "레벨 {n}")))
    assert got == 'string A => Pick($"Stufe {n}", $"Level {n}", $"레벨 {n}");'


def test_보간이_없으면_달러를_안_붙인다():
    src = 'string A => IsGerman ? "Titel" : "Title";'
    got = apply(src, cat(("Titel", "Title", "제목")))
    assert "$" not in got


def test_보간_자리가_모자라면_거부한다():
    # 컴파일은 통과하고 값만 사라진다. 제일 조용한 사고다.
    src = 'string A => IsGerman ? $"Stufe {n}" : $"Level {n}";'
    result = ko_apply.rewrite(src, cat(("Stufe {n}", "Level {n}", "레벨")))
    assert result.bad_slots
    assert result.text == src, "거부한 자리는 손대지 않는다"


def test_보간_자리_순서가_바뀌는_것은_허용한다():
    # 한국어는 어순이 다르다. 이름이 같으면 순서는 자유다.
    src = 'string A => IsGerman ? $"{a} von {b}" : $"{a} of {b}";'
    result = ko_apply.rewrite(src, cat(("{a} von {b}", "{a} of {b}", "{b} 중 {a}")))
    assert not result.bad_slots
    assert '$"{b} 중 {a}"' in result.text


def test_없는_보간_자리를_지어내면_거부한다():
    src = 'string A => IsGerman ? $"Stufe {n}" : $"Level {n}";'
    result = ko_apply.rewrite(src, cat(("Stufe {n}", "Level {n}", "레벨 {m}")))
    assert result.bad_slots
    assert result.text == src


# --- 어긋난 것을 보고한다 --------------------------------------------------


def test_소스에만_있는_한국어는_stray로_잡는다():
    # 카탈로그를 안 거치고 손으로 넣은 것. 다음 재생성 때 조용히 사라진다.
    src = 'string A => Pick("Nein", "No", "아니오");'
    result = ko_apply.rewrite(src, cat(("Ja", "Yes", "예")))
    assert result.stray


def test_카탈로그에만_있는_것은_고아다():
    # 업스트림이 그 문장을 고쳤다는 신호다. 충돌 대신 이 보고가 나온다.
    catalog = cat(("Ja", "Yes", "예"), ("Nein", "No", "아니오"))
    result = ko_apply.rewrite('string A => IsGerman ? "Ja" : "Yes";', catalog)
    assert ko_apply.orphans(catalog, result.seen) == [("Nein", "No")]


def test_고아가_없으면_빈_목록():
    catalog = cat(("Ja", "Yes", "예"))
    result = ko_apply.rewrite('string A => IsGerman ? "Ja" : "Yes";', catalog)
    assert ko_apply.orphans(catalog, result.seen) == []


# --- 한국어가 빠진 자리 ----------------------------------------------------
#
# `Loc.Pick`이 `Korean => ko ?? en`이다. 한국어 인자가 없으면 **예외도 로그도
# 없이 영어가 나간다.** 실제로 그렇게 배포됐고(`4 of 29`의 `of`), 현황판에
# "지금은 영어로 나간다"고 적혀 있었는데도 나갔다. 적어 두는 것으로는 안 막힌다.


def test_한국어가_없는_자리를_잡는다():
    src = 'string A => Pick("Ja", "Yes");'
    assert ko_apply.gaps(src)


def test_한국어가_있으면_안_잡는다():
    src = 'string A => Pick("Ja", "Yes", "예");'
    assert ko_apply.gaps(src) == []


def test_아직_안_옮긴_삼항도_잡는다():
    # 삼항은 한국어 자리 자체가 없다. 이것도 영어로 나간다.
    src = 'string A => IsGerman ? "Ja" : "Yes";'
    assert ko_apply.gaps(src)


def test_몇_행인지_말한다():
    src = 'class S\n{\n    string A => Pick("Ja", "Yes");\n}\n'
    assert "3행" in ko_apply.gaps(src)[0]


def test_독일어와_영어가_같으면_통과시킨다():
    # 보간 자리뿐이라 언어가 안 걸린다. 옮길 것이 없으니 빠진 게 아니다.
    # 판단이 아니라 계산이라 예외 표에 안 적는다.
    src = 'string A => IsGerman ? $"{name}: {dist}." : $"{name}: {dist}.";'
    assert ko_apply.gaps(src) == []


def test_세는_말은_예외로_통과시킨다():
    # 번역하면 기능이 조용히 깨진다. 왜인지는 UNTRANSLATABLE에 적혀 있다.
    src = 'string A => IsGerman ? "von" : "of";'
    assert ko_apply.gaps(src) == []


def test_예외는_적어_둔_쌍에만_적용된다():
    # 예외가 부류로 번지면 검사가 죽는다. `of`가 들어간 다른 문장은 잡혀야 한다.
    src = 'string A => IsGerman ? "Teil von {n}" : "Part of {n}";'
    assert ko_apply.gaps(src)


def test_주석_속_예시는_안_잡는다():
    src = '// Pick("Ja", "Yes") 는 예시다\nstring A => 1;'
    assert ko_apply.gaps(src) == []


# --- 모양 -----------------------------------------------------------------


def test_길면_여러_줄로_나누고_괄호에_맞춘다():
    src = (
        "    public static string LanguageUsage =>\n"
        "        IsGerman\n"
        '            ? "Sprache wählen mit: /acc lang de, /acc lang en oder /acc lang auto."\n'
        '            : "Choose a language with: /acc lang de, /acc lang en or /acc lang auto.";\n'
    )
    got = apply(src, cat((
        "Sprache wählen mit: /acc lang de, /acc lang en oder /acc lang auto.",
        "Choose a language with: /acc lang de, /acc lang en or /acc lang auto.",
        "언어를 고르려면 /acc lang ko, /acc lang en, /acc lang de 중 하나를 입력한다.",
    )))
    lines = got.splitlines()
    assert lines[1].startswith("        Pick(")
    # 이어지는 인자는 여는 괄호 다음 칸에 선다.
    assert lines[2].startswith(" " * 13 + '"')
    assert lines[3].startswith(" " * 13 + '"')
    assert lines[3].rstrip().endswith(");")


def test_짧으면_한_줄로_둔다():
    src = 'string A => IsGerman ? "Ja" : "Yes";'
    assert "\n" not in apply(src, cat(("Ja", "Yes", "예")))


# --- 카탈로그 파일 --------------------------------------------------------


def test_카탈로그를_읽는다(tmp_path):
    path = tmp_path / "ko.json"
    path.write_text(
        json.dumps({"strings": [{"de": "Ja", "en": "Yes", "ko": "예"}]}),
        encoding="utf-8",
    )
    assert ko_apply.load_catalog(path) == {("Ja", "Yes"): "예"}


def test_같은_쌍이_두_번_있으면_거부한다(tmp_path):
    # 어느 쪽이 이기는지 조용히 정해지면 안 된다.
    path = tmp_path / "ko.json"
    path.write_text(
        json.dumps({"strings": [
            {"de": "Ja", "en": "Yes", "ko": "예"},
            {"de": "Ja", "en": "Yes", "ko": "네"},
        ]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="중복"):
        ko_apply.load_catalog(path)


def test_한국어가_비면_거부한다(tmp_path):
    path = tmp_path / "ko.json"
    path.write_text(
        json.dumps({"strings": [{"de": "Ja", "en": "Yes", "ko": ""}]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="비어"):
        ko_apply.load_catalog(path)


# --- 실제 저장소 ----------------------------------------------------------

needs_vendor = pytest.mark.skipif(
    not ko_apply.SOURCE_ROOT.is_dir(), reason="vendor 클론이 없다"
)


@needs_vendor
def test_소스가_카탈로그대로다():
    # 이게 빨개지면 누가 소스를 손으로 고쳤거나 카탈로그를 갱신하고 안 돌렸다.
    problems = ko_apply.check()
    assert problems == [], problems


@needs_vendor
def test_생성_커밋을_제목으로_찾는다():
    # 끝 커밋이라고 가정하면 안 된다 - 손으로 쓴 커밋이 그 뒤에 붙는다.
    assert ko_apply.generated_commit() is not None


@needs_vendor
def test_생성_커밋이_정말_생성물이다():
    # 이 도구의 존재 이유를 지키는 검사다. 그 커밋에 손편집이 섞이면 다음
    # 재생성 때 그 줄만 조용히 사라지고, 사라지는 게 한국어라 독일어·영어
    # 스냅샷에는 안 걸린다.
    problems = ko_apply.tip_is_generated()
    assert problems == [], problems


@needs_vendor
def test_한국어_없이_영어로_나가는_자리가_없다():
    # 이 검사의 목표는 0이다. 빨개지면 그 자리는 **말없이 영어로 발화된다** -
    # 사용자는 모드가 고장 난 것인지 아직 안 옮긴 것인지 구분할 수 없다.
    #
    # 새 문장이 업스트림에서 오면 여기가 먼저 빨개진다. 옮기거나(카탈로그),
    # 옮기면 안 되는 것이면 왜인지를 `UNTRANSLATABLE`에 적는다.
    problems = ko_apply.missing_korean()
    assert problems == [], problems


@needs_vendor
def test_카탈로그에_고아가_없다():
    # 업스트림이 우리가 옮긴 문장을 고치면 여기가 먼저 빨개진다.
    catalog = ko_apply.load_catalog()
    seen: list[tuple[str, str]] = []
    for path in ko_apply.source_files():
        seen += ko_apply.rewrite(path.read_text(encoding="utf-8"), catalog).seen
    assert ko_apply.orphans(catalog, seen) == []
