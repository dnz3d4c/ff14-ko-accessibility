"""릴리스 노트 검사기.

**두 판을 그대로 박아 둔다.** 사용자가 고친 판은 통과해야 하고 발행본은
걸려야 한다 - 규칙이 어느 쪽으로도 미끄러지면 여기서 빨개진다.
"""

from __future__ import annotations

import notes_check

VERSION = "5.88.0.1"

#: 사용자가 2026-08-22에 직접 고쳐 준 판. **이것이 규칙의 원본이다.**
#: 사용자는 릴리스 페이지에서 복사해 고쳤으므로 백틱과 헤딩 깊이가 렌더링에
#: 씻겨 있었다. 마크업만 되살리고 문장은 한 자도 안 건드렸다 - 다만 `## 준비물`
#: 하나가 다른 절과 깊이가 달라서 `###`로 맞췄다(사용자가 제안하라고 한 자리).
USER_EDITED = """\
## FF14 접근성 모드 (한국 서버용) v5.88.0.1

### 설치

`FF14Accessibility-KR-Setup.zip`을 받아 압축을 풀고, 폴더 안의 `FF14AccessibilityInstaller-KR.exe`를 실행합니다.

설치 방법과 사용법은 `사용 안내.md`, 모드에서 사용하는 단축키 목록은 `단축키 목록.md`를 참고하세요.

### v5.88.0.1 변경사항

- 바탕화면 바로가기로 게임과 KR 달라무드 업데이터가 실행되도록 함.
- 설치 프로그램이 .NET 10 데스크톱 런타임을 자동으로 내려받아 설치하도록 함.
- 사용 안내의 달라무드 적용 절차를 실제 동작에 맞게 고침.

모드 변경사항: 없음.

### 준비물

- 한국 서버 파이널 판타지 14 계정과 클라이언트
- 스크린 리더(NVDA등)

.NET 10 데스크톱 런타임과 KR 달라무드 업데이터, vnavmesh는 설치 프로그램이 직접 내려받아 설치합니다. vnavmesh는 설치 전 설치 여부를 묻는 창이 표시됩니다.

### 업데이트 방법

`FF14AccessibilityInstaller-KR.exe`를 실행합니다.

설치 프로그램은 새 버전이 있는지 확인하고 새 버전 설치를 묻는 대화상자가 표시됩니다. [예]를 선택하면 프로그램이 업데이트됩니다.

### 알려진 제한사항

- 방향 안내에 할당된 `N` 키가 게임의 제작 메뉴와 겹칩니다
- 기본 단축키 셋(`Ctrl+F`, `Shift+Home`, `Alt+Home`)이 동작하지 않습니다
- 알림 수락 안내에서 키 이름이 독일어(`Strg+F12`)로 들립니다
- 캐릭터 생성 화면의 외모 묘사는 한국어로 음성 출력되지 않습니다.

자세한 내용과 대처 방법은 `사용 안내.md`의 문제 해결 절에 있습니다.

### 라이선스

AGPL-3.0. 원본은 derbruedi/ff14-accessibility이고, 이 저장소는 한국 서버용으로 옮긴 것입니다.

※ 아래 나머지 파일은 설치 프로그램과 Dalamud가 자동 업데이트에 사용합니다. 직접 받을 필요는 없습니다.
"""

#: 실제로 나간 v5.88.0.1 노트. **이것이 고쳐야 할 판이다.**
PUBLISHED = """\
FF14 접근성 모드 (한국 서버용) v5.88.0.1 입니다. 파이널 판타지 14를 한국 서버에서 스크린 리더로 플레이할 수 있습니다.

## 설치

`FF14Accessibility-KR-Setup.zip`을 받아 압축을 풀고, 폴더 안의 `FF14AccessibilityInstaller-KR.exe`를 실행합니다.

## 이번 판에서 바뀐 것

설치할 때 사용자가 직접 하던 일 둘을 설치 프로그램이 대신합니다.

- **바탕화면 바로가기로 게임과 KR 달라무드 업데이터가 실행되도록 함.**
- **설치 프로그램이 .NET 10 데스크톱 런타임을 자동으로 내려받아 설치하도록 함.**
- **사용 안내의 달라무드 적용 절차를 실제 동작에 맞게 고침.**

모드 자체는 바뀌지 않았습니다. 버전만 v5.88.0.1로 올랐습니다.

## 준비물

- 한국 서버 파이널 판타지 14 계정과 클라이언트
- NVDA 등 스크린 리더

## 알려진 제한

- 캐릭터 생성 화면의 외모 묘사는 아직 한국어로 옮기지 않았습니다

## 문제를 알릴 곳

[이슈](https://github.com/dnz3d4c/ff14-ko-accessibility/issues)로 알려 주시면 됩니다.

## 라이선스

AGPL-3.0. 원본은 [derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility)이고, 이 저장소는 한국 서버용으로 옮긴 것입니다.

※ 아래 나머지 파일은 설치 프로그램과 Dalamud가 자동 업데이트에 사용합니다. 직접 받을 필요는 없습니다.
"""


def codes(text: str, version: str = VERSION) -> set[str]:
    return {v.code for v in notes_check.check(text, version)}


def swap(old: str, new: str, text: str = USER_EDITED) -> str:
    """통과하는 판에서 한 자리만 어긋뜨린다. **못 찾으면 실패다** - 픽스처를
    고치다 대상 문자열이 사라지면 그 테스트가 조용히 통과하기 때문이다."""
    if old not in text:
        raise AssertionError(f"픽스처에 `{old}`가 없다. 테스트를 같이 고쳐라")
    return text.replace(old, new, 1)


# ------------------------------------------------------------------ 두 판


def test_사용자가_고친_판이_통과한다():
    assert notes_check.check(USER_EDITED, VERSION) == []


def test_발행본이_걸린다():
    found = codes(PUBLISHED)
    # 제목·절 구성·제목 깊이·링크·굵게 남발이 전부 다르다. **N7·N8은 여기서
    # 안 걸린다** - 절을 전부 `##`로 써서 변경사항 절 자체가 안 잡히고, 그것을
    # 먼저 말하는 것이 N3다.
    assert {"N2", "N3", "N4", "N9", "N10", "N11"} <= found


def test_본이_검사를_통과한다():
    """본과 규칙이 갈리는 것을 막는다. 사람이 채우는 자리는 여기서 채운다."""
    text = notes_check.render(VERSION)
    text = text.replace("{{변경 항목}}", "- 무엇이 어떻게 바뀌도록 함.")
    text = text.replace("{{모드 변경 목록}}", "없음.")
    text = text.replace("{{알려진 제한사항}}", "- 무엇이 아직 안 됩니다")
    assert notes_check.check(text, VERSION) == []


# ------------------------------------------------------------------ 규칙별


def test_N1_BOM이_붙으면_걸린다():
    text, found = notes_check.decode(("﻿" + USER_EDITED).encode("utf-8"))
    assert [v.code for v in found] == ["N1"]
    # BOM을 뗀 나머지는 그대로 검사한다 - 첫 줄이 제목으로 되살아나야 한다.
    assert notes_check.check(text, VERSION) == []


def test_N1_UTF8이_아니면_걸린다():
    _, found = notes_check.decode(USER_EDITED.encode("cp949"))
    assert [v.code for v in found] == ["N1"]


def test_N2_제목이_다르면_걸린다():
    assert "N2" in codes(swap("## FF14 접근성 모드 (한국 서버용) v5.88.0.1", "## 릴리스 노트"))


def test_N2_제목이_둘이면_걸린다():
    assert "N2" in codes(swap("### 라이선스", "## 라이선스"))


def test_N3_절을_빠뜨리면_걸린다():
    assert "N3" in codes(swap("### 준비물\n", ""))


def test_N3_절_순서를_바꾸면_걸린다():
    swapped = swap("### 준비물", "### 업데이트 방법")
    swapped = swap("### 업데이트 방법\n\n`FF14AccessibilityInstaller", "### 준비물\n\n`FF14AccessibilityInstaller", swapped)
    assert "N3" in codes(swapped)


def test_N3_모르는_절을_넣으면_걸린다():
    """열거 밖은 통과가 아니라 위반이다. 이슈 절이 실제로 그렇게 되살아났다."""
    extra = "### 문제를 알릴 곳\n\n이슈로 알려 주시면 됩니다.\n\n### 라이선스"
    assert "N3" in codes(swap("### 라이선스", extra))


def test_N4_깊이가_다르면_걸린다():
    assert "N4" in codes(swap("### 준비물", "#### 준비물"))


def test_N5_지난_판_번호가_남으면_걸린다():
    assert "N5" in codes(swap("### v5.88.0.1 변경사항", "### v5.88.0.0 변경사항"))


def test_N6_자리표시자가_남으면_걸린다():
    assert "N6" in codes(swap("스크린 리더(NVDA등)", "{{스크린 리더}}"))


def test_N7_항목이_명사형이_아니면_걸린다():
    assert "N7" in codes(swap("실행되도록 함.", "실행되도록 고쳤습니다."))


def test_N7_항목에_내부_이름을_쓰면_걸린다():
    assert "N7" in codes(swap("바탕화면 바로가기로", "Launcher가"))


def test_N7_항목에_없음을_쓰면_걸린다():
    """트레일러의 `없음 - <이유>` 면제는 노트 항목에서는 통하지 않는다."""
    assert "N7" in codes(swap("- 바탕화면 바로가기로 게임과 KR 달라무드 업데이터가 실행되도록 함.",
                              "- 없음 - 주석만 고침"))


def test_N8_모드_변경_줄이_없으면_걸린다():
    assert "N8" in codes(swap("모드 변경사항: 없음.\n\n", ""))


def test_N8_모드_변경_줄이_둘이면_걸린다():
    assert "N8" in codes(swap("모드 변경사항: 없음.", "모드 변경사항: 없음.\n모드 변경사항: 없음."))


def test_N8_어중간한_값이면_걸린다():
    assert "N8" in codes(swap("모드 변경사항: 없음.", "모드 변경사항: 있음."))


def test_N8_없음인데_목록이_붙으면_걸린다():
    assert "N8" in codes(swap("모드 변경사항: 없음.", "모드 변경사항: 없음.\n- 무엇이 바뀌도록 함."))


def test_N8_비었는데_목록이_없으면_걸린다():
    assert "N8" in codes(swap("모드 변경사항: 없음.", "모드 변경사항:"))


def test_N8_비고_목록이_붙으면_통과한다():
    assert notes_check.check(
        swap("모드 변경사항: 없음.", "모드 변경사항:\n- 무엇이 어떻게 말하도록 함."), VERSION
    ) == []


def test_N8_항목보다_앞서면_걸린다():
    moved = swap("모드 변경사항: 없음.\n\n", "")
    moved = swap("### v5.88.0.1 변경사항\n", "### v5.88.0.1 변경사항\n\n모드 변경사항: 없음.\n", moved)
    assert "N8" in codes(moved)


def test_N9_인라인_링크가_있으면_걸린다():
    assert "N9" in codes(swap("derbruedi/ff14-accessibility이고",
                              "[derbruedi/ff14-accessibility](https://github.com/derbruedi/ff14-accessibility)이고"))


def test_N10_항목을_통째로_굵게_하면_걸린다():
    assert "N10" in codes(swap("- 사용 안내의 달라무드 적용 절차를 실제 동작에 맞게 고침.",
                               "- **사용 안내의 달라무드 적용 절차를 실제 동작에 맞게 고침.**"))


def test_N10_한_낱말만_굵게_하면_통과한다():
    assert notes_check.check(
        swap("게임과 KR 달라무드 업데이터가", "게임과 **KR 달라무드 업데이터**가"), VERSION
    ) == []


def test_N11_한_절에_굵게가_둘이면_걸린다():
    twice = swap("게임과 KR 달라무드 업데이터가", "게임과 **KR 달라무드 업데이터**가")
    twice = swap(".NET 10 데스크톱 런타임을 자동으로", "**.NET 10 데스크톱 런타임**을 자동으로", twice)
    assert "N11" in codes(twice)


def test_N11_기울임이_있으면_걸린다():
    assert "N11" in codes(swap("게임과 KR 달라무드", "게임과 *KR* 달라무드"))


def test_N12_백틱_안_한글은_배포물_이름만_통과한다():
    assert "N12" in codes(swap("모드에서 사용하는 단축키 목록은", "모드에서 사용하는 `단축키 목록`은"))


def test_N13_한다체가_섞이면_걸린다():
    assert "N13" in codes(swap("프로그램이 업데이트됩니다.", "프로그램이 업데이트된다."))


def test_N14_내부_이름이_본문에_있으면_걸린다():
    assert "N14" in codes(swap("설치 프로그램은 새 버전이", "Installer는 새 버전이"))


def test_N14_Dalamud는_보충_줄_밖에서_걸린다():
    assert "N14" in codes(swap("설치 프로그램은 새 버전이", "Dalamud는 새 버전이"))


def test_N15_보충_줄이_없으면_걸린다():
    assert "N15" in codes(swap("※ 아래 나머지 파일은", "아래 나머지 파일은"))


def test_N15_보충_줄이_둘이면_걸린다():
    assert "N15" in codes(swap("※ 아래 나머지 파일은", "※ 무엇을 더 적습니다.\n\n※ 아래 나머지 파일은"))


def test_N16_절이_도입_문단으로_시작하면_걸린다():
    assert "N16" in codes(swap("### 준비물\n\n- 한국 서버",
                               "### 준비물\n\n다음이 미리 있어야 합니다.\n\n- 한국 서버"))


# ------------------------------------------------------------------ 본 자체


def test_본의_자리표시자가_넷이다():
    """`render()`가 채우는 것과 사람이 채우는 것의 경계. 늘리면 문서도 같이 고친다."""
    assert notes_check.placeholders(notes_check.template()) == {
        "버전", "변경 항목", "모드 변경 목록", "알려진 제한사항"
    }


def test_render가_버전만_채운다():
    text = notes_check.render(VERSION)
    assert "{{버전}}" not in text
    assert notes_check.placeholders(text) == {"변경 항목", "모드 변경 목록", "알려진 제한사항"}
