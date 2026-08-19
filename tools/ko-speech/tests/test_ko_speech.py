"""`Pick` 밖에서 문장으로 새는 외국어 리터럴을 잡는다.

막는 사고는 하나다 - **카탈로그를 안 거치는 자리는 검사도 카탈로그도 안 본다.**
사용자가 인게임에서 `불멸대 막사 방향 통로, Übergang, 54미터, 왼쪽`을 들었는데,
그 `Übergang`은 소스에 맨 리터럴로 박혀 있어서 스냅샷에도 카탈로그에도 없었다.
같은 부류로 `NavCategory.Fates => "FATEs"`가 있었다 - 형제 열다섯이 전부
`Pick(...)`인데 혼자 맨 리터럴이었다.

두 갈래를 따로 시험한다. 한 규칙으로 묶으면 오탐이 섞여 둘 다 죽기 때문이다.
"""

import ko_speech
import pytest

GOLDEN = ko_speech.GOLDEN
SOURCE_ROOT = ko_speech.SOURCE_ROOT


def rules(text: str) -> list[str]:
    return [f.rule for f in ko_speech.scan_text(text, "T.cs")]


def texts(text: str) -> list[str]:
    return [f.text for f in ko_speech.scan_text(text, "T.cs")]


# --- 움라우트 갈래 ---------------------------------------------------------


def test_맨_리터럴에_움라우트가_있으면_잡는다():
    got = texts('class T { void M() { type = "Übergang"; } }')
    assert got == ["Übergang"], got


def test_픽_안의_독일어는_안_잡는다():
    # 카탈로그가 보는 자리다. 여기 독일어가 있는 것이 정상이다.
    assert texts('class T { string M() => Pick("Übergang", "Transition", "통로"); }') == []


def test_삼항_안의_독일어도_안_잡는다():
    # 아직 안 옮긴 자리. `tools/ko-apply`가 옮길 대상이지 이 검사의 대상이 아니다.
    assert texts('class T { string M() => IsGerman ? "Ätheryt" : "Aetheryte"; }') == []


def test_움라우트가_없는_외국어는_이_갈래로_안_잡는다():
    # 라틴 문자만으로는 한국어 문장인지 명령어인지 갈리지 않는다. `FATEs`는
    # 형제 대조 갈래가 잡는다.
    assert texts('class T { void M() { type = "Aethernet"; } }') == []


# --- 오탐 1: 비교 키 -------------------------------------------------------


def test_is_패턴의_피연산자는_통과한다():
    # `PlacesService.cs:425` - 발화가 아니라 식별자다. 리터럴만 바꾸면
    # 에테라이트 분류가 예외도 로그도 없이 죽는다.
    assert texts('class T { bool M(P p) => p.TypeLabel is "Ätheryt" or "Aethernet"; }') == []


def test_등호_비교의_피연산자는_통과한다():
    assert texts('class T { bool M(string s) => s == "Ätheryt"; }') == []
    assert texts('class T { bool M(string s) => "Ätheryt" != s; }') == []


def test_case_라벨과_스위치_가지_라벨은_통과한다():
    assert texts('class T { void M(string s) { switch (s) { case "Ätheryt": break; } } }') == []
    assert texts('class T { string M(string s) => s switch { "Übergang" => Empty, _ => s }; }') == []


# --- 오탐 2: 로그 ----------------------------------------------------------


def test_로그_인자는_통과한다():
    # `NavigationService.cs:2141`, `PlacesService.cs:444`. 사람이 듣는 문장이 아니다.
    assert texts('class T { void M() { _log.Info($"[Nav] Übergang gefunden."); } }') == []
    assert texts('class T { void M() { Log.Error("Kein Gewölbe."); } }') == []


def test_로그가_아닌_호출의_인자는_통과하지_않는다():
    got = texts('class T { void M() { Speak("Übergang."); } }')
    assert got == ["Übergang."], got


# --- 오탐 3: 파서가 모양을 못 읽은 언어 분기 -------------------------------


def test_언어_분기_안의_리터럴은_통과한다():
    # `AccessibilityStrings.cs:1043`의 `, ausgewählt`가 이 모양이다. 한국어가
    # 이미 있는데 파서가 중첩 삼항을 못 읽을 뿐이라, `strings-golden`이 세는
    # 미해석 목록과 같은 부류다.
    source = (
        'class T { string M(bool sel) =>\n'
        '    Loc.IsKorean ? $"{o}{(sel ? ", 선택됨" : "")}"\n'
        '    : IsGerman ? $"{o}{(sel ? ", ausgewählt" : "")}"\n'
        '    : $"{o}{(sel ? ", selected" : "")}"; }'
    )
    assert texts(source) == []


def test_별칭_분기는_통과하지_않는다():
    # `ColorNamer.cs`는 `De`라는 자기 별칭을 둬서 표식(`IsGerman`)에 안 잡힌다.
    # **이건 오탐이 아니라 진짜 결함이다** - 한국어가 0곳이라 영어로 나간다(W-44).
    got = texts('class T { string M() { if (s < 0.16) return De ? "gräuliches" : "greyish"; } }')
    assert got == ["gräuliches"], got


# --- 형제 대조 갈래 --------------------------------------------------------


def test_형제가_픽인데_혼자_맨_리터럴이면_잡는다():
    # `NavCategory.Fates => "FATEs"`가 이 모양이었다. 움라우트가 없어서
    # 문자셋으로는 안 갈리고 형제와 대조해야만 나온다.
    source = (
        'class T { string M(C c) => c switch {\n'
        '    C.Duties => Pick("Inhalte", "Duties", "임무"),\n'
        '    C.Fates  => "FATEs",\n'
        '    C.Places => Pick("Orte", "Places", "장소"),\n'
        '}; }'
    )
    found = ko_speech.scan_text(source, "T.cs")
    assert [f.text for f in found] == ["FATEs"]
    assert [f.rule for f in found] == [ko_speech.SIBLING]


def test_형제가_전부_맨_리터럴이면_안_잡는다():
    # 그냥 조회표다. 발화 여부를 형제로는 알 수 없으니 아무 말도 안 한다.
    source = 'class T { string M(C c) => c switch { C.A => "one", C.B => "two" }; }'
    assert texts(source) == []


def test_배열_초기화도_형제로_본다():
    source = 'class T { string[] M() => new[] { Pick("Ort", "Place", "장소"), "Aethernet" }; }'
    assert texts(source) == ["Aethernet"]


def test_형제가_픽이어도_비교_라벨은_통과한다():
    # `SpokenPlaceType`이 이 모양이다 - 가지 라벨은 식별자고 값만 발화된다.
    source = (
        'class T { string M(string t) => t switch {\n'
        '    "Übergang"  => string.Empty,\n'
        '    "Aethernet" => Pick("Aethernet", "Aethernet", "전송망"),\n'
        '    _           => t,\n'
        '}; }'
    )
    assert texts(source) == []


# --- 공통 ------------------------------------------------------------------


def test_글자가_없는_리터럴은_안_잡는다():
    # `AccessibilityStrings.cs:2522`의 빈 가지가 이 모양이다 - 일부러 아무 말도
    # 안 하는 자리라 형제가 `Pick`이어도 새는 것이 없다.
    source = (
        'class T { string M(C c) => c switch {\n'
        '    C.Echo       => Pick("Echo", "Echo", "혼잣말"),\n'
        '    C.Gathering  => "",\n'
        '}; }'
    )
    assert texts(source) == []


def test_주석_속_예시는_안_센다():
    # 주석에 적은 예시를 코드로 읽으면 개수가 가짜로 늘어 진짜 증가를 못 본다.
    source = 'class T {\n    // 예: type = "Übergang";\n    void M() { }\n}'
    assert texts(source) == []


def test_한_갈래에서_두_번_안_잡는다():
    # 움라우트도 있고 형제가 픽이기도 한 자리. 한 자리는 한 건이다.
    source = (
        'class T { string M(C c) => c switch {\n'
        '    C.A => Pick("Inhalte", "Duties", "임무"),\n'
        '    C.B => "Übergang",\n'
        '}; }'
    )
    found = ko_speech.scan_text(source, "T.cs")
    assert len(found) == 1, found


# --- 골든 ------------------------------------------------------------------


def test_골든이_있다():
    assert GOLDEN.is_file(), f"{GOLDEN}가 없다 - ko_speech.py --write로 만든다"


def test_골든이_정렬돼_있고_중복이_없다():
    keys = [(s["file"], s["rule"], s["text"]) for s in ko_speech.load_golden()]
    assert keys == sorted(set(keys)), "정렬·중복 제거해서 저장한다 - diff가 읽히게"


def test_골든의_모든_자리에_왜인지가_적혀_있다():
    # 골든에 넣는 것은 판단이다. 왜 통과시키는지를 사람이 안 적으면 다음 사람이
    # 그 줄을 근거 없이 믿는다.
    빈칸 = [s for s in ko_speech.load_golden() if not s.get("why", "").strip()]
    assert not 빈칸, f"왜인지가 안 적힌 자리가 있다: {[s['text'] for s in 빈칸]}"


def test_캐릭터_생성_묘사는_범위_밖이다():
    # 3,023건이 통째로 W-12 소유다. 여기서 다시 세면 상태가 두 벌이 되고
    # 골든이 안 읽힌다. 뺀 파일이 늘어나면 그것도 판단이라 여기서 막는다.
    assert ko_speech.OUT_OF_SCOPE == {
        "Services/CharaMakeIconText.cs",
        "Services/CharaMakeShapeText.cs",
    }


@pytest.fixture(scope="module")
def 실물():
    """소스 전체를 훑은 결과. **한 번만 훑는다.**

    아래 둘이 각각 `scan()`을 부르면 같은 일을 두 번 하고 그것만으로 18초가
    더 든다(`run\\check.bat` 전체의 17%였다). 검사는 그대로 두고 준비 과정만
    나눠 쓴다.
    """
    if not SOURCE_ROOT.is_dir():
        pytest.skip("vendor 클론이 없다")
    return ko_speech.scan()


def test_새_자리가_말없이_들어오지_않는다(실물):
    # 빨개지면 둘 중 하나다. 발화에 외국어가 새기 시작했거나(고친다), 통과시킬
    # 자리가 새로 생겼거나(--write로 갱신하고 `why`를 적는다).
    added, dropped = ko_speech.compare(실물, ko_speech.load_golden())
    assert not added, f"발화 경로에 외국어 리터럴이 새로 들어왔다: {added}"
    assert not dropped, f"골든에만 남은 자리가 있다 - --write로 갱신해라: {dropped}"


def test_실물에서_형제_대조가_돈다(실물):
    # 규칙이 배선만 되고 실물에서 0건이면 살아 있는지 알 수 없다. 실제로
    # `PlacesService.cs`의 `type = "Übergang"`이 잡혀야 한다.
    assert any(
        f.text == "Übergang" and f.file.endswith("PlacesService.cs") for f in 실물
    ), "PlacesService의 맨 리터럴을 못 잡았다 - 검사가 실물에서 안 돈다"
