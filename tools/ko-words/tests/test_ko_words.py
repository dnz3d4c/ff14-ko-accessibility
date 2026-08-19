"""번역이 쓰는 낱말 중 게임에 없는 것의 목록을 고정한다.

막는 사고는 하나다 - **게임이 안 쓰는 낱말을 그럴듯해서 쓰는 것.** 검수에서
실제로 나왔다: `장판`(플레이어 은어), `손패`, `방위`, `월드`, `훈련장`,
`우편함`. 전부 KR Addon 시트에 0건인데 뜻이 통해서 안 걸렸다.

대장(`terms.json`)은 "쓴 낱말"이 아니라 "적어 둔 낱말"만 본다. 적기를 잊으면
아무 일도 안 일어난다. 그래서 반대 방향에서 본다 - 번역이 쓰는 낱말을 전부
모아 게임 덤프에 없는 것을 골라내고, 그 목록을 골든으로 고정한다.
"""

import json
import subprocess

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


# --- 손 케이스 - kr-port 커밋에서 읽는다 -----------------------------------


def test_손_케이스_커밋을_제목으로_찾는다():
    sha = ko_words.hand_commit()
    assert len(sha) == 40 and set(sha) <= set("0123456789abcdef"), sha


def test_손_케이스_줄을_커밋에서_읽는다():
    lines = ko_words.hand_lines()
    assert any("IsKorean" in line for line in lines), "손 케이스 커밋의 더한 줄이어야 한다"
    # `+` 접두는 걷어낸 상태여야 하고, `+++` 파일 머리글은 아예 안 들어온다.
    assert all(not line.startswith("++") for line in lines)


def test_커밋이_없으면_소리를_낸다(tmp_path):
    # 패치 glob 시절과 같은 함정 자리다 - 제목이 바뀌면 조용히 0줄을 읽는 대신
    # 여기서 소리를 내야 한다.
    subprocess.run(
        ["git", "init", "-q", "-b", "kr-port", str(tmp_path)], check=True, timeout=10,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "--allow-empty", "-q", "-m", "다른 커밋"],
        check=True, timeout=10,
    )
    with pytest.raises(LookupError):
        ko_words.hand_commit(tmp_path)


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
