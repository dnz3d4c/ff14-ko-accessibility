"""커밋 메시지 검증기 테스트.

규칙 근거: docs/dev/commit-rules.md
검증기가 막아야 하는 것은 "나중에 업스트림 PR을 조립할 수 없게 되는 커밋"이다.
"""

import commit_lint


def codes(message: str, paths: list[str] | None = None) -> list[str]:
    """위반 코드만 뽑는다. 메시지 문구가 바뀌어도 테스트가 안 깨지게."""
    return [v.code for v in commit_lint.check(message, paths or [])]


# --- C1 영역 접두 ---------------------------------------------------------


def test_영역_접두가_없으면_거부한다():
    assert "C1" in codes("한국어 문자열 카탈로그 추가")


def test_알려지지_않은_영역은_거부한다():
    assert "C1" in codes("[잡동사니] 뭔가 고침")


def test_알려진_영역은_통과한다():
    assert codes("[문서] port-feasibility.md: 빌드 검증 결과 추가", ["docs/x.md"]) == []


def test_영역_목록_전체가_받아들여진다():
    for area in ("업스트림", "한국전용", "검증", "문서", "벤더", "도구"):
        assert "C1" not in codes(f"[{area}] 무언가 바꿈")


# --- C2 Conventional Commits 금지 ----------------------------------------


def test_conventional_commits_접두는_거부한다():
    # upstream 이력 140건 전부 미사용. 우리도 쓰지 않는다.
    assert "C2" in codes("[문서] feat: 새 기능")
    assert "C2" in codes("feat(loc): add korean")


def test_콜론_자체는_금지가_아니다():
    assert "C2" not in codes("[문서] 조사 보고서: 빌드 결과 반영")


# --- C3 제목 길이 ---------------------------------------------------------


def test_제목이_72자를_넘으면_거부한다():
    assert "C3" in codes("[문서] " + "가" * 70)


def test_제목_72자_경계는_통과한다():
    subject = "[문서] " + "가" * 67
    assert len(subject) == 72
    assert "C3" not in codes(subject)


# --- C4 제목 끝 마침표 ----------------------------------------------------


def test_제목이_마침표로_끝나면_거부한다():
    assert "C4" in codes("[문서] 보고서를 고쳤다.")


# --- C5 업스트림 커밋 트레일러 -------------------------------------------------

UPSTREAM_OK = (
    "[업스트림] UIReaderService: 확인 버튼 라벨을 로케일별 데이터로 분리\n"
    "\n"
    "독일어 리터럴이 박혀 있어 다른 클라이언트에서 눌리지 않는다.\n"
    "\n"
    "Status-Board: W-07 진행\n"
    "Upstream-Files: FF14Accessibility/Services/UIReaderService.cs\n"
    "Upstream-Subject: Bestaetigen-Button-Label je Sprache aus Daten lesen\n"
    "Release-Note: 확인 버튼이 한국어 클라이언트에서도 눌리도록 함.\n"
)


def test_업스트림_커밋에_트레일러가_다_있으면_통과한다():
    assert codes(UPSTREAM_OK, ["vendor/ff14-accessibility"]) == []


def test_업스트림_커밋에_Upstream_Files가_없으면_거부한다():
    msg = UPSTREAM_OK.replace(
        "Upstream-Files: FF14Accessibility/Services/UIReaderService.cs\n", ""
    )
    assert "C5" in codes(msg, ["vendor/ff14-accessibility"])


def test_업스트림_커밋에_Upstream_Subject가_없으면_거부한다():
    msg = UPSTREAM_OK.replace(
        "Upstream-Subject: Bestaetigen-Button-Label je Sprache aus Daten lesen\n", ""
    )
    assert "C5" in codes(msg, ["vendor/ff14-accessibility"])


def test_업스트림이_아니면_트레일러를_요구하지_않는다():
    assert "C5" not in codes("[한국전용] 한국어 라벨 집합 초안", ["overlay/ko-labels.json"])


# --- C6 움라우트 치환 ------------------------------------------------------


def test_Upstream_Subject의_움라우트는_거부한다():
    # upstream 커밋 140/140이 ae/oe/ue/ss로 치환한다. 이탈하면 안 된다.
    msg = UPSTREAM_OK.replace("Bestaetigen", "Bestätigen")
    assert "C6" in codes(msg, ["vendor/ff14-accessibility"])


def test_움라우트_검사는_Upstream_Subject에만_적용한다():
    # 우리 저장소 본문에 독일어 원문을 인용할 수 있어야 한다.
    msg = UPSTREAM_OK.replace(
        "독일어 리터럴이 박혀 있어", 'upstream 원문은 "Schließen"이다.'
    )
    assert "C6" not in codes(msg, ["vendor/ff14-accessibility"])


# --- C7 영역 혼합 금지 -----------------------------------------------------
#
# 한국전용 쪽 검사는 없다. 패치 파일이 사라지면서 업스트림에 보낼 것은
# 경로가 아니라 vendor(kr-port) 커밋이 됐고, 그쪽 섞임은 C11이 본다.


def test_업스트림_커밋이_overlay를_건드리면_거부한다():
    # 섞이는 순간 PR로 떼어낼 수 없다. 이게 이 검증기의 존재 이유다.
    assert "C7" in codes(UPSTREAM_OK, ["vendor/ff14-accessibility", "overlay/ko.json"])


def test_경로_목록이_비면_혼합_검사를_건너뛴다():
    # 훅이 인덱스를 못 읽는 상황(rebase 등)에서 오탐을 내면 안 된다.
    assert "C7" not in codes(UPSTREAM_OK, [])


# --- C8 현황판 갱신 --------------------------------------------------------
#
# 남은 일은 현황판(docs/status.md)만 보면 된다. 코드가 움직였는데 판이
# 그대로면 판은 며칠 만에 거짓말이 되고, 그 뒤로는 아무도 안 본다. 그래서
# 판을 같이 건드리거나, 안 건드리는 이유를 한 줄로 밝히게 한다.


def test_한국전용_커밋이_현황판을_안_건드리면_거부한다():
    assert "C8" in codes("[한국전용] 설치기를 KR 경로로", ["vendor/ff14-accessibility"])


def test_현황판을_같이_건드리면_통과한다():
    assert "C8" not in codes(
        "[한국전용] 설치기를 KR 경로로",
        ["vendor/ff14-accessibility", "docs/status.md"],
    )


def test_트레일러로_면제받을_수_있다():
    msg = "[도구] 스크립트 오타 수정\n\nStatus-Board: 해당 없음 - 오타 수정\n"
    assert "C8" not in codes(msg, ["tools/kr-setup/seed_devplugin.py"])


def test_빈_트레일러는_면제가_아니다():
    # "Status-Board:" 만 붙여 검사를 통과시키는 우회를 막는다.
    msg = "[도구] 스크립트 오타 수정\n\nStatus-Board:\n"
    assert "C8" in codes(msg, ["tools/kr-setup/seed_devplugin.py"])


def test_문서_커밋은_현황판을_요구하지_않는다():
    # 근거 문서를 고치는 것 자체는 할 일의 이동이 아니다.
    assert "C8" not in codes("[문서] 환경 문서에 실측 결과 추가", ["docs/dev/environment.md"])


def test_벤더_커밋은_현황판을_요구하지_않는다():
    assert "C8" not in codes("[벤더] 업스트림 v5.86으로 이동", ["vendor"])


def test_경로_목록이_비면_현황판_검사를_건너뛴다():
    # 훅이 인덱스를 못 읽는 상황에서 오탐을 내면 안 된다. C7과 같은 취급.
    assert "C8" not in codes("[한국전용] 설치기를 KR 경로로", [])


# --- C9·C10 업스트림을 올릴 때 ---------------------------------------------
#
# 업스트림은 독일어로 개발된다. 핀만 옮기고 이력을 안 남기면 우리 저장소에
# 뭐가 들어왔는지 **읽을 수 있는 사람이 아무도 없다.** 어디서 어디까지
# 올렸는지(C9)와, 그게 한국어로 남았는지(C10)를 커밋 시점에 막는다.


VENDOR_RANGE = "Upstream-Range: v5.85..v5.87 (3051202..a8ac7c5)"
VENDOR_PATHS = ["upstream.json", "docs/upstream/changes.md"]


def test_벤더_커밋에_올린_범위가_없으면_거부한다():
    assert "C9" in codes("[벤더] 업스트림 v5.87로 올림", VENDOR_PATHS)


def test_올린_범위를_적으면_통과한다():
    msg = f"[벤더] 업스트림 v5.87로 올림\n\n{VENDOR_RANGE}\n"
    assert "C9" not in codes(msg, VENDOR_PATHS)


def test_범위만_적고_이력을_안_남기면_거부한다():
    # 핀은 옮겼는데 무엇이 들어왔는지는 독일어로만 남은 상태.
    msg = f"[벤더] 업스트림 v5.87로 올림\n\n{VENDOR_RANGE}\n"
    assert "C10" in codes(msg, ["upstream.json", "vendor/ff14-accessibility"])


def test_핀을_안_건드리는_벤더_커밋은_이력을_요구하지_않는다():
    # 핀은 그대로 두고 vendor 포인터만 고치는 경우 같은 것.
    msg = f"[벤더] vendor 포인터를 미러 팁으로 되돌림\n\n{VENDOR_RANGE}\n"
    assert "C10" not in codes(msg, ["vendor/ff14-accessibility"])


def test_다른_영역은_이_규칙을_안_받는다():
    assert "C9" not in codes("[문서] 동기화 절차 정리", ["docs/upstream/sync.md"])
    assert "C10" not in codes("[문서] 핀 설명 추가", ["upstream.json"])


# --- C11 vendor 포인터 -----------------------------------------------------
#
# vendor/ff14-accessibility는 gitlink다 - 우리 저장소는 kr-port 커밋 하나를
# 가리키는 포인터만 기록한다. 그 포인터가 엉뚱한 갈래에 섞여 움직이면
# (`git add -A`가 제일 흔한 사고다) vendor가 왜 바뀌었는지 이력에 안 남는다.


def test_문서_커밋이_vendor_포인터를_옮기면_거부한다():
    assert "C11" in codes(
        "[문서] 환경 문서 오타 수정",
        ["docs/dev/environment.md", "vendor/ff14-accessibility"],
    )


def test_검증_도구_커밋도_vendor_포인터를_못_옮긴다():
    for area in ("검증", "도구"):
        msg = f"[{area}] 무언가 바꿈\n\nStatus-Board: 해당 없음 - 테스트\n"
        assert "C11" in codes(msg, ["vendor/ff14-accessibility"])


def test_벤더_업스트림_한국전용_커밋은_vendor_포인터를_옮길_수_있다():
    # kr-port에 커밋이 쌓이면 포인터가 같이 움직인다. 그게 정상 경로다.
    assert "C11" not in codes(
        f"[벤더] 업스트림 v5.89로 올림\n\n{VENDOR_RANGE}\n",
        ["upstream.json", "docs/upstream/changes.md", "vendor/ff14-accessibility"],
    )
    assert "C11" not in codes(UPSTREAM_OK, ["vendor/ff14-accessibility"])
    assert "C11" not in codes(
        "[한국전용] 한국어 안내 문장 손질\n\nStatus-Board: W-11 진행\n",
        ["vendor/ff14-accessibility"],
    )


def test_vendor_하위_경로도_잡는다():
    # gitlink이 풀려 vendor 안의 파일이 직접 스테이징된 사고도 같은 취급이다.
    assert "C11" in codes("[문서] 뭔가 고침", ["vendor/ff14-accessibility/File.cs"])


def test_경로_목록이_비면_vendor_검사를_건너뛴다():
    # C7·C8과 같은 취급 - 인덱스를 못 읽는 상황에서 오탐을 내면 안 된다.
    assert "C11" not in codes("[문서] 뭔가 고침", [])


# --- 주석줄 처리 -----------------------------------------------------------


def test_주석줄은_무시한다():
    msg = "# 이 줄은 git이 지운다\n[문서] x.md: 실제 제목\n"
    assert codes(msg, ["docs/x.md"]) == []


def test_빈_메시지는_거부한다():
    assert "C1" in codes("\n# 주석만 있음\n")


def test_가위선_아래는_검사하지_않는다():
    msg = (
        "[문서] x.md: 제목\n"
        "# ------------------------ >8 ------------------------\n"
        "# 아래는 diff 미리보기\n"
        "feat: 이건 diff 안의 남의 커밋 인용\n"
    )
    assert codes(msg, ["docs/x.md"]) == []


# --- C12 제목에 대상 이름 --------------------------------------------------
#
# 이력 166건이 전부 대상 없이 쓰였고, 여섯 달 뒤에 `git log --oneline`만 보고는
# 무엇을 고친 커밋인지 알 수 없었다. 실제 사례를 그대로 시험값으로 쓴다.


def test_대상을_안_적으면_거부한다():
    assert "C12" in codes(
        "[도구] gh가 한글 자산 이름을 삼키는 것을 피한다", ["run/release.bat"]
    )


def test_콜론으로_대상을_앞세우면_통과한다():
    assert "C12" not in codes(
        "[도구] release_manifest: 한글 자산명이 default.md로 올라가던 것 수정",
        ["tools/release-manifest/release_manifest.py"],
    )


def test_콜론만_있고_대상이_비면_거부한다():
    assert "C12" in codes("[문서] : 뭔가 고침", ["docs/x.md"])


def test_대상이_한글_파일명이어도_통과한다():
    assert "C12" not in codes(
        "[문서] 사용 안내.md: 설치 절차를 압축 하나 받는 흐름으로 고침",
        ["overlay/ko/README.ko.md"],
    )


# --- C13 제목의 비유·은어 ---------------------------------------------------


def test_제목의_비유_동사를_거부한다():
    assert "C13" in codes("[문서] status.md: 끝난 일을 걷어낸다", ["docs/status.md"])


def test_제목의_은어를_거부한다():
    assert "C13" in codes("[도구] check.bat: 판에 옮긴다", ["run/check.bat"])


def test_의인화를_거부한다():
    assert "C13" in codes(
        "[문서] release.md: 문서가 말하게 한다", ["docs/dev/release.md"]
    )


def test_본문에_쓴_같은_말은_막지_않는다():
    # 제목만 본다. `git log --oneline`이 보여 주는 것이 제목이고, 본문까지
    # 단속하면 사고 경위를 제 말로 적을 수가 없다.
    msg = (
        "[문서] status.md: 완료 기록을 지워 49,774자를 23,783자로 줄임\n"
        "\n"
        "끝난 일의 서사를 걷어냈다. 판이 남은 일만 갖게 했다.\n"
        "\n"
        "Status-Board: W-49 진행\n"
    )
    assert "C13" not in codes(msg, ["docs/status.md"])


# --- C14 릴리스 노트 줄 ---------------------------------------------------

GUIDE_PATH = "overlay/ko/README.ko.md"


def test_사용자가_받는_것을_바꿨는데_노트_줄이_없으면_거부한다():
    assert "C14" in codes(
        "[한국전용] Launcher: 바로가기를 만든다", [commit_lint.VENDOR_PATH]
    )


def test_노트_줄이_있으면_통과한다():
    msg = (
        "[한국전용] Launcher: 게임과 업데이터를 함께 띄우는 바로가기를 만든다\n"
        "\n"
        "Status-Board: W-76 진행\n"
        "Release-Note: 바탕화면 바로가기로 게임과 KR 달라무드 업데이터가 "
        "실행되도록 함.\n"
    )
    assert "C14" not in codes(msg, [commit_lint.VENDOR_PATH])


def test_문서_갈래여도_배포되는_안내를_고치면_요구한다():
    # b979baf가 `[문서]`로 배포되는 안내의 원본을 77줄 고쳤다. 갈래로 나누면
    # 이 부류가 샌다 - 그래서 경로로 묻는다.
    assert "C14" in codes("[문서] README.ko.md: 달라무드 절을 고친다", [GUIDE_PATH])


def test_값이_비면_면제가_아니다():
    msg = "[한국전용] ko.json: 문장을 고친다\n\nRelease-Note:\n"
    assert "C14" in codes(msg, ["overlay/ko/ko.json"])


def test_없음은_이유를_대야_통과한다():
    msg = "[한국전용] ko.json: 주석 오타를 고친다\n\nRelease-Note: 없음 - 주석만 고침\n"
    assert "C14" not in codes(msg, ["overlay/ko/ko.json"])


def test_이유_없는_없음은_거부한다():
    msg = "[한국전용] ko.json: 문장을 고친다\n\nRelease-Note: 없음\n"
    assert "C14" in codes(msg, ["overlay/ko/ko.json"])


def test_사용자가_읽을_문장은_함으로_끝낸다():
    # 제목은 `~한다`, 노트는 `~함.`이다. 독자가 달라서 문체도 다르다.
    msg = (
        "[한국전용] Launcher: 바로가기를 만든다\n\n"
        "Release-Note: 바탕화면 바로가기로 게임이 실행되도록 한다\n"
    )
    assert "C14" in codes(msg, [commit_lint.VENDOR_PATH])


def test_노트에_내부_이름을_쓰면_거부한다():
    # `Launcher`는 사용자 화면 어디에도 안 뜬다. 사용자가 보는 것은
    # `바탕화면 바로가기`다.
    msg = (
        "[한국전용] Launcher: 바로가기를 만든다\n\n"
        "Release-Note: Launcher가 게임과 업데이터를 함께 띄우도록 함.\n"
    )
    assert "C14" in codes(msg, [commit_lint.VENDOR_PATH])


def test_백틱_안의_파일_이름은_내부_이름으로_보지_않는다():
    # 사용자가 직접 실행하는 파일이라 노트에 나오는 것이 맞다.
    msg = (
        "[한국전용] Installer: 닷넷 10 데스크톱 런타임을 대신 받아 깐다\n\n"
        "Release-Note: `FF14AccessibilityInstaller-KR.exe`가 .NET 10 데스크톱 "
        "런타임을 자동으로 내려받아 설치하도록 함.\n"
    )
    assert "C14" not in codes(msg, [commit_lint.VENDOR_PATH])


def test_사용자에게_안_닿는_경로만_고치면_요구하지_않는다():
    assert "C14" not in codes(
        "[검증] commit_lint: 검사를 더한다", ["tools/commit-lint/commit_lint.py"]
    )


# --- staged_paths 실패 경로 -----------------------------------------------


def test_git이_없는_디렉토리에서는_빈_목록을_돌려준다(tmp_path):
    # 실패 시 예외를 던지면 커밋 자체가 막힌다. 조용히 혼합 검사만 포기해야 한다.
    assert commit_lint.staged_paths(tmp_path) == []
