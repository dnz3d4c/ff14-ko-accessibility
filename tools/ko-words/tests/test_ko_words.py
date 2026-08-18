"""번역이 쓰는 낱말 중 게임에 없는 것의 목록을 고정한다.

막는 사고는 하나다 - **게임이 안 쓰는 낱말을 그럴듯해서 쓰는 것.** 검수에서
실제로 나왔다: `장판`(플레이어 은어), `손패`, `방위`, `월드`, `훈련장`,
`우편함`. 전부 KR Addon 시트에 0건인데 뜻이 통해서 안 걸렸다.

대장(`terms.json`)은 "쓴 낱말"이 아니라 "적어 둔 낱말"만 본다. 적기를 잊으면
아무 일도 안 일어난다. 그래서 반대 방향에서 본다 - 번역이 쓰는 낱말을 전부
모아 게임 덤프에 없는 것을 골라내고, 그 목록을 골든으로 고정한다.
"""

import json

import ko_words
import pytest

GOLDEN = ko_words.GOLDEN
DUMP = ko_words.DUMP


# --- 구조 - 늘 돈다 --------------------------------------------------------


def test_골든이_있다():
    assert GOLDEN.is_file(), f"{GOLDEN}가 없다 - ko_words.py --write로 만든다"


def test_골든이_정렬돼_있고_중복이_없다():
    words = json.loads(GOLDEN.read_text(encoding="utf-8"))["words"]
    assert words == sorted(set(words)), "정렬·중복 제거해서 저장한다 - diff가 읽히게"


def test_낱말을_뽑는다():
    got = ko_words.tokens("길안내 켜짐. {count}개, ABC.")
    assert got == {"길안내", "켜짐"}, got


def test_한_글자와_숫자와_영문은_안_센다():
    # 한 글자는 조사·의존명사라 신호가 없고, 영문·숫자는 이 검사 대상이 아니다.
    assert ko_words.tokens("길 3개 HP") == set()


def test_게임에_있는_낱말은_안_걸린다():
    unknown = ko_words.unknown(["소지품에 아이템 없음."], "520\t소지품\n953\t아이템\n")
    assert unknown == {"없음"}


def test_게임에_없는_낱말이_걸린다():
    unknown = ko_words.unknown(["장판 경고 켜짐."], "520\t소지품\n")
    assert "장판" in unknown


# --- 게임 데이터와 대조 - 덤프가 있을 때만 --------------------------------


@pytest.mark.skipif(
    not DUMP.is_file(),
    reason="게임 데이터 덤프가 없다 - run\\terms.bat dump tools\\ko-terms\\out",
)
def test_새_낱말이_말없이_들어오지_않는다():
    # 빨개지면 둘 중 하나다. 게임 낱말을 잘못 지어냈거나(고친다), 모드가 지어야
    # 하는 말이 새로 생겼거나(--write로 갱신하고 커밋 본문에 왜인지 적는다).
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["words"]
    now = sorted(ko_words.unknown(ko_words.korean_text(), ko_words.load_dump()))

    added = [word for word in now if word not in golden]
    dropped = [word for word in golden if word not in now]
    assert not added, f"게임에 없는 낱말이 새로 들어왔다: {added}"
    assert not dropped, f"골든에만 남은 낱말이 있다 - --write로 갱신해라: {dropped}"
