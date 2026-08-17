"""커밋 메시지 검증기 테스트.

규칙 근거: docs/commit-rules.md
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
    assert codes("[문서] 조사 보고서에 빌드 검증 결과 추가", ["docs/x.md"]) == []


def test_영역_목록_전체가_받아들여진다():
    for area in ("상류", "오버레이", "검증", "문서", "벤더", "도구"):
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


# --- C5 상류 커밋 트레일러 -------------------------------------------------

UPSTREAM_OK = (
    "[상류] 확인 버튼 라벨을 로케일별 데이터로 분리\n"
    "\n"
    "독일어 리터럴이 박혀 있어 다른 클라이언트에서 눌리지 않는다.\n"
    "\n"
    "Upstream-Files: FF14Accessibility/Services/UIReaderService.cs\n"
    "Upstream-Subject: Bestaetigen-Button-Label je Sprache aus Daten lesen\n"
)


def test_상류_커밋에_트레일러가_다_있으면_통과한다():
    assert codes(UPSTREAM_OK, ["patches/0001-confirm-labels.patch"]) == []


def test_상류_커밋에_Upstream_Files가_없으면_거부한다():
    msg = UPSTREAM_OK.replace(
        "Upstream-Files: FF14Accessibility/Services/UIReaderService.cs\n", ""
    )
    assert "C5" in codes(msg, ["patches/x.patch"])


def test_상류_커밋에_Upstream_Subject가_없으면_거부한다():
    msg = UPSTREAM_OK.replace(
        "Upstream-Subject: Bestaetigen-Button-Label je Sprache aus Daten lesen\n", ""
    )
    assert "C5" in codes(msg, ["patches/x.patch"])


def test_상류가_아니면_트레일러를_요구하지_않는다():
    assert "C5" not in codes("[오버레이] 한국어 라벨 집합 초안", ["overlay/ko-labels.json"])


# --- C6 움라우트 치환 ------------------------------------------------------


def test_Upstream_Subject의_움라우트는_거부한다():
    # upstream 커밋 140/140이 ae/oe/ue/ss로 치환한다. 이탈하면 안 된다.
    msg = UPSTREAM_OK.replace("Bestaetigen", "Bestätigen")
    assert "C6" in codes(msg, ["patches/x.patch"])


def test_움라우트_검사는_Upstream_Subject에만_적용한다():
    # 우리 저장소 본문에 독일어 원문을 인용할 수 있어야 한다.
    msg = UPSTREAM_OK.replace(
        "독일어 리터럴이 박혀 있어", 'upstream 원문은 "Schließen"이다.'
    )
    assert "C6" not in codes(msg, ["patches/x.patch"])


# --- C7 영역 혼합 금지 -----------------------------------------------------


def test_상류_커밋이_overlay를_건드리면_거부한다():
    # 섞이는 순간 PR로 떼어낼 수 없다. 이게 이 검증기의 존재 이유다.
    assert "C7" in codes(UPSTREAM_OK, ["patches/x.patch", "overlay/ko.json"])


def test_오버레이_커밋이_patches를_건드리면_거부한다():
    assert "C7" in codes(
        "[오버레이] 한국어 문자열 초안", ["overlay/ko.json", "patches/x.patch"]
    )


def test_경로_목록이_비면_혼합_검사를_건너뛴다():
    # 훅이 인덱스를 못 읽는 상황(rebase 등)에서 오탐을 내면 안 된다.
    assert "C7" not in codes(UPSTREAM_OK, [])


# --- 주석줄 처리 -----------------------------------------------------------


def test_주석줄은_무시한다():
    msg = "# 이 줄은 git이 지운다\n[문서] 실제 제목\n"
    assert codes(msg, ["docs/x.md"]) == []


def test_빈_메시지는_거부한다():
    assert "C1" in codes("\n# 주석만 있음\n")


def test_가위선_아래는_검사하지_않는다():
    msg = (
        "[문서] 제목\n"
        "# ------------------------ >8 ------------------------\n"
        "# 아래는 diff 미리보기\n"
        "feat: 이건 diff 안의 남의 커밋 인용\n"
    )
    assert codes(msg, ["docs/x.md"]) == []


# --- staged_paths 실패 경로 -----------------------------------------------


def test_git이_없는_디렉토리에서는_빈_목록을_돌려준다(tmp_path):
    # 실패 시 예외를 던지면 커밋 자체가 막힌다. 조용히 혼합 검사만 포기해야 한다.
    assert commit_lint.staged_paths(tmp_path) == []
