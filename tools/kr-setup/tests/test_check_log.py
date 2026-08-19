"""Dalamud 로그 판정기 테스트.

이 도구가 있는 이유는 판정을 눈으로 하지 않기 위해서다. docs/dev/kr-runtime.md
§10이 "적용 완료 알림을 믿으면 안 된다"고 적은 그 판정을 기계가 한다.

그래서 테스트가 지켜야 할 것은 문구가 아니라 **판정**이다 - 통과를 실패라고
하거나, 없는 것을 있다고 하면 안 된다.
"""

import check_log


#: 언어 표시는 로그가 아니라 옆에 놓인 troubleshooting json에 있다.
#: 2026-08-18 실측 - 로그 전문에 `"Language"` 문자열이 0건이다.
SIDECAR = '{"GameVersion":"2026.08.05.0000.0000","Language": "Korean"}'


def verdicts(text: str, sidecar: str = SIDECAR) -> dict[str, bool]:
    """검사 이름 -> 통과 여부."""
    return {c.name: c.passed for c in check_log.inspect(text, sidecar).checks}


# 실기에서 통과한 판(2026-08-18 05:41~05:51)에서 판정에 쓰이는 줄만 뽑은 것.
GOOD = """\
2026-08-18 05:41:21.285 +09:00 [INF] Initializing a session..
2026-08-18 05:41:22.100 +09:00 [INF] Lumina is ready: C:\\Program Files (x86)\\FINAL FANTASY XIV - KOREA\\game\\sqpack
2026-08-18 05:41:22.818 +09:00 [INF] [PluginManager] Loading dev plugin vnavmesh
2026-08-18 05:41:22.900 +09:00 [INF] [PluginManager] Loading plugin FF14Accessibility
2026-08-18 05:41:23.210 +09:00 [INF] [FF14Accessibility] [Compat] AtkResNode::IsVisible resolved by the Korean signature at 0x7FF61438E7E0 (ClientStructs left it null).
2026-08-18 05:41:23.276 +09:00 [INF] [FF14Accessibility] [Compat] Kompatibilitätshinweis: Ausrüstungsset-Markierung geht nach Gegenstands-ID.
2026-08-18 05:41:23.290 +09:00 [INF] [FF14Accessibility] [Speak] 'FF14 Accessibility 버전 5 점 87 준비됨.'
2026-08-18 05:41:23.711 +09:00 [INF] [LocalPlugin] Finished loading vnavmesh
2026-08-18 05:41:24.000 +09:00 [INF] [LocalPlugin] Finished loading FF14Accessibility
2026-08-18 05:42:39.820 +09:00 [INF] [FF14Accessibility] [Speak] INT 'Walking to 츠츠모코.'
2026-08-18 05:42:40.620 +09:00 [INF] [FF14Accessibility] [Speak] INT 'Target reached: 츠츠모코.'
2026-08-18 05:51:47.397 +09:00 [INF] Session has ended.
"""


def test_정상_판_전체_통과():
    assert all(verdicts(GOOD).values())


def test_플러그인이_안_뜨면_실패():
    text = GOOD.replace("Finished loading FF14Accessibility", "Loading FF14Accessibility")
    assert verdicts(text)["접근성 모드 적재"] is False


def test_vnavmesh가_안_뜨면_실패():
    text = GOOD.replace("Finished loading vnavmesh", "Loading vnavmesh")
    assert verdicts(text)["vnavmesh 적재"] is False


def test_한국어_패치가_없으면_실패():
    assert verdicts(GOOD, '{"Language": "English"}')["KR 언어 패치"] is False


def test_troubleshooting_파일이_없어도_나머지는_판정한다():
    # 사이드카가 없다고 판정 전체를 포기하면 도구가 쓸모없어진다.
    result = verdicts(GOOD, "")
    assert result["KR 언어 패치"] is False
    assert result["접근성 모드 적재"] is True


def test_도착_안내가_없으면_오토웍은_미확인():
    text = GOOD.replace("Target reached: 츠츠모코.", "No route active.")
    assert verdicts(text)["자동 이동 도착"] is False


def test_가시성이_모드_구현으로_내려가면_실패():
    # 폴백은 게임과 답이 달라질 수 있는 경로다. 조용히 지나가면 안 된다.
    text = GOOD.replace(
        "resolved by the Korean signature at 0x7FF61438E7E0 (ClientStructs left it null).",
        "signature matched 0 times, expected 1 - refused; using the managed replica",
    )
    assert verdicts(text)["노드 가시성이 게임 함수"] is False


def test_오류를_세어_보고한다():
    text = GOOD + "2026-08-18 05:41:23.270 +09:00 [ERR] [vnavmesh] Failed to load config\n"
    report = check_log.inspect(text, SIDECAR)
    assert report.errors == 1


def test_알려진_경고는_따로_센다():
    text = GOOD + (
        "2026-08-18 05:42:08.463 +09:00 [WRN] [FF14Accessibility] [Keys] KONFLIKT N: MENU_CRAFT (N)\n"
        "2026-08-18 05:41:23.312 +09:00 [WRN] [FF14Accessibility] Unbekannte Tastenangabe in der Konfiguration: 'Strg+F'\n"
    )
    report = check_log.inspect(text, SIDECAR)
    assert report.key_conflicts == 1
    assert report.unknown_keys == 1


def test_마지막_세션만_본다():
    # 로그는 세션을 이어 붙인다. 앞판이 통과했다고 이번 판을 통과로 읽으면
    # 고장을 놓친다.
    text = GOOD + "2026-08-18 06:00:00.000 +09:00 [INF] Initializing a session..\n"
    assert verdicts(text)["접근성 모드 적재"] is False


def test_빈_로그는_전부_실패():
    # "사본이 하나뿐"만 빼고다. 그건 "두 번 뜨지 않았다"를 보는 검사라
    # 아무것도 안 뜬 로그에서도 참이다 - 없는 것을 있다고 말하지 않는다.
    results = verdicts("", "")
    del results["사본이 하나뿐"]
    assert not any(results.values())


def test_적재_경로를_구분해_말한다():
    assert check_log.inspect(GOOD, SIDECAR).route == "정식 플러그인"

    dev = GOOD.replace(
        "Loading plugin FF14Accessibility", "Loading dev plugin FF14Accessibility"
    )
    # 개발 중에는 이게 정상이다. 사실만 말하고 실패로 세지 않는다.
    report = check_log.inspect(dev, SIDECAR)
    assert report.route == "개발용 플러그인"
    assert report.checks[-1].passed


def test_두_사본이_같이_뜨면_실패():
    # 정식 설치 옆에 옛 dev 사본이 남은 상태다. 같은 명령과 같은 단축키를
    # 두 번 등록하고, 게임 안에서는 "가끔 두 번 말한다"로만 드러난다.
    both = GOOD.replace(
        "Loading plugin FF14Accessibility",
        "Loading plugin FF14Accessibility\n"
        "2026-08-18 05:41:22.950 +09:00 [INF] [PluginManager] Loading dev plugin FF14Accessibility",
    )
    report = check_log.inspect(both, SIDECAR)
    assert report.route == "둘 다"
    assert verdicts(both)["사본이 하나뿐"] is False
