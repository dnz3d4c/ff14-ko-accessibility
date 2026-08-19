"""업스트림 추종 도구 테스트.

판정 로직은 전부 순수 함수로 두고 여기서 검사한다. git을 부르는 부분은
vendor 클론이 있을 때만 돌린다 - 클론이 없는 머신에서 빨간불이 뜨면
아무도 안 본다.

가장 중요한 것은 **미번역 검출**이다. 업스트림 릴리스 노트는 독일어고,
번역되지 않은 채로 동기화가 끝나면 사용자는 자기 저장소에 뭐가 들어왔는지
영영 모른다. 그 상태를 통과시키지 않는 것이 이 파일의 첫 번째 책임이다.
"""

import subprocess
from pathlib import Path

import pytest
import upstream_sync as us


# --- 태그 정렬 ------------------------------------------------------------


def test_태그를_숫자로_비교한다():
    # 문자열로 비교하면 v5.9가 v5.87보다 뒤로 간다.
    assert us.version_key("v5.9") < us.version_key("v5.87")
    assert us.version_key("v5.85") < us.version_key("v5.86")


def test_형식이_다른_태그도_죽지_않는다():
    # 업스트림이 규칙을 바꿔도 도구가 죽는 것보다 뒤로 미는 게 낫다.
    assert us.version_key("nightly") == (-1,)


def test_핀보다_새_태그만_고른다():
    tags = ["v5.84", "v5.85", "v5.86", "v5.87"]
    assert us.newer_tags(tags, "v5.85") == ["v5.86", "v5.87"]


def test_새_태그가_없으면_빈_목록():
    assert us.newer_tags(["v5.84", "v5.85"], "v5.85") == []


def test_핀_태그를_모르면_전부_새것으로_본다():
    # 핀이 태그가 아닌 커밋을 가리키는 경우. 조용히 0건이라고 하면 안 된다.
    assert us.newer_tags(["v5.86", "v5.87"], "없는태그") == ["v5.86", "v5.87"]


def test_바로_앞선_태그를_고른다():
    tags = ["v5.85", "v5.86", "v5.87", "v5.88"]
    assert us.previous_tag("v5.88", tags) == "v5.87"
    assert us.previous_tag("v5.86", tags) == "v5.85"


def test_앞선_태그가_없으면_없다고_한다():
    # 첫 판이면 앞이 없다. 지어내면 커밋 범위가 저장소 처음부터가 된다.
    assert us.previous_tag("v5.85", ["v5.85", "v5.86"]) is None


# --- 변경 이력 문서 --------------------------------------------------------


HEADER = "# 업스트림 변경 이력\n\n앞줄 설명.\n"

DOC = (
    HEADER
    + """
## v5.86 — 2026-08-17

사냥수첩 목표를 개체 목록에서 고를 수 있다

- `70d6ae3` 사냥수첩 목표가 개체 목록에 나온다
  원문: Release v5.86: Jagdziele im Objekt-Browser

## v5.85 — 2026-08-16

숫자만 읽히던 창 세 곳이 뜻을 말한다

- `d1cee70` 숫자만 있던 창 세 곳
  원문: Release v5.85: drei Fenster
"""
)


def test_태그별로_쪼갠다():
    sections = us.split_sections(DOC)
    assert list(sections) == ["v5.86", "v5.85"]
    assert "70d6ae3" in sections["v5.86"]


def test_미번역이_없으면_통과():
    assert us.untranslated_tags(DOC) == []


def test_미번역_표시가_남아_있으면_잡는다():
    doc = DOC.replace("사냥수첩 목표가 개체 목록에 나온다", us.UNTRANSLATED)
    assert us.untranslated_tags(doc) == ["v5.86"]


def test_이력에_없는_태그를_찾아낸다():
    # 동기화는 했는데 이력을 안 쓴 경우. 미번역보다 더 조용한 실패다.
    assert us.missing_tags(DOC, ["v5.85", "v5.86", "v5.87"]) == ["v5.87"]


def test_핀을_옮긴_뒤에도_핀_태그의_자리를_만든다():
    # `--to`가 끝나면 핀은 이미 새 태그다. 그 시점엔 "새 태그"가 없으므로
    # 새것만 세면 만들 자리도 없다고 답한다 - 그런데 `--check`는 같은 상태를
    # "이력에 없는 판"이라고 말한다. 한 사실에 두 명령이 다르게 답한 것이고,
    # v5.88 동기화에서 실제로 걸려 그 절을 손으로 썼다.
    tags = ["v5.86", "v5.87", "v5.88"]
    assert us.newer_tags(tags, "v5.88") == []
    assert us.tags_to_write("v5.88", tags, DOC) == ["v5.88"]


def test_이력에_이미_있으면_다시_만들지_않는다():
    assert us.tags_to_write("v5.86", ["v5.85", "v5.86"], DOC) == []


def test_핀_태그와_새_태그가_같이_빠졌으면_둘_다_만든다():
    # 오래된 것이 먼저다 - 문서에는 뒤집어 넣지만 커밋 범위는 순서대로 잰다.
    tags = ["v5.85", "v5.86", "v5.87", "v5.88"]
    assert us.tags_to_write("v5.87", tags, DOC) == ["v5.87", "v5.88"]


# --- 자리 만들기 -----------------------------------------------------------


COMMITS = [
    us.Commit("a8ac7c5", "Release v5.87: Jagdziele laufen direkt zum Monster"),
    us.Commit("07e0769", "STATUS: Release v5.87 ist draussen"),
]


def test_자리에_원문과_미번역_표시가_같이_들어간다():
    section = us.render_section("v5.87", "2026-08-17", COMMITS)
    assert "## v5.87 — 2026-08-17" in section
    assert "a8ac7c5" in section
    # 원문을 지우지 않는다. 옮긴 게 틀렸을 때 되짚을 자리가 그것뿐이다.
    assert "Jagdziele laufen direkt zum Monster" in section
    assert us.UNTRANSLATED in section


def test_만든_자리는_바로_미번역으로_잡힌다():
    # 자리만 만들고 커밋하면 검사기가 막아야 한다.
    doc = us.insert_sections(DOC, [us.render_section("v5.87", "2026-08-17", COMMITS)])
    assert us.untranslated_tags(doc) == ["v5.87"]


def test_새_항목이_맨_위에_붙는다():
    doc = us.insert_sections(DOC, [us.render_section("v5.87", "2026-08-17", COMMITS)])
    assert list(us.split_sections(doc)) == ["v5.87", "v5.86", "v5.85"]


def test_머리말을_안_건드린다():
    doc = us.insert_sections(DOC, [us.render_section("v5.87", "2026-08-17", COMMITS)])
    assert doc.startswith(HEADER)


def test_항목이_없으면_문서가_그대로다():
    assert us.insert_sections(DOC, []) == DOC


def test_이력이_비어_있어도_붙는다():
    # 첫 동기화. 아직 아무 항목도 없는 문서다.
    doc = us.insert_sections(HEADER, [us.render_section("v5.87", "2026-08-17", COMMITS)])
    assert list(us.split_sections(doc)) == ["v5.87"]


# --- 감시가 여는 이슈 -------------------------------------------------------
#
# 이걸 CI 안에서 조립하면 이 머신에서 돌려 볼 수가 없다. 못 돌려 보는
# 코드는 처음 필요한 날 깨져 있는다 - 그래서 도구가 만들고 여기서 잡는다.


FOUND = {
    "pin": {"tag": "v5.85", "commit": "30512023e7a6", "synced": "2026-08-18"},
    "new_tags": ["v5.86", "v5.87"],
    "newest": "v5.87",
    "commits": 5,
    "changed_files": 10,
    "overlap": ["FF14Accessibility/Plugin.cs"],
    "applies": True,
    "failing_patch": None,
    "subjects": [{"sha": "a8ac7c5", "subject": "Release v5.87: Jagdziele laufen"}],
}


def test_새_태그가_없으면_이슈도_없다():
    assert us.render_issue_body({**FOUND, "newest": None, "new_tags": []}) is None


def test_첫_줄이_제목이다():
    body = us.render_issue_body(FOUND)
    assert body.splitlines()[0] == "업스트림 v5.87 — 동기화 대기"
    assert body.splitlines()[1] == ""


def test_독일어_원문을_그대로_싣는다():
    # 러너에는 옮길 수단이 없다. 원문이라도 있어야 무슨 일인지 짐작한다.
    assert "Release v5.87: Jagdziele laufen" in us.render_issue_body(FOUND)


def test_붙는지_여부를_말한다():
    assert "깨끗이 붙는다" in us.render_issue_body(FOUND)
    broken = {**FOUND, "applies": False, "failing_patch": "Compat shim"}
    body = us.render_issue_body(broken)
    assert "안 붙는다" in body and "Compat shim" in body


def test_겹치는_파일이_없으면_없다고_말한다():
    body = us.render_issue_body({**FOUND, "overlap": []})
    assert "겹치는 파일 없음" in body


# --- 핀 ------------------------------------------------------------------


def test_핀을_읽고_쓴다(tmp_path: Path):
    path = tmp_path / "upstream.json"
    us.write_pin({"tag": "v5.85", "commit": "3051202"}, path)
    assert us.read_pin(path)["tag"] == "v5.85"


def test_핀이_없으면_안_지어낸다(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        us.read_pin(tmp_path / "없다.json")


# --- kr-port가 새 자리에 얹히는가 -------------------------------------------
#
# 이게 이 프로젝트에서 실제로 일어나는 일이다. 업스트림은 8일에 릴리스를 7개
# 내고, 우리가 고치는 줄 바로 옆에 새 문장을 끼워 넣는다. rebase의 merge
# 백엔드는 3-way라 문맥이 밀린 것은 합쳐야 하고, 같은 줄을 양쪽이 다르게
# 고친 진짜 충돌은 그대로 실패해야 한다.


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _out(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _lines(*changes: tuple[int, str]) -> str:
    """1~10번 줄짜리 파일. `changes`로 지정한 줄만 바꾼다."""
    rows = [f"line {i}" for i in range(1, 11)]
    for number, text in changes:
        rows[number - 1] = text
    return "\n".join(rows) + "\n"


def _drifted(root: Path) -> tuple[Path, str, str]:
    """우리가 고친 줄의 문맥을 업스트림이 건드린 vendor.

    돌려주는 것은 (vendor, 옛 밑동, 새 밑동)이다. kr-port는 옛 밑동 위에
    커밋 하나(5번 줄)를 갖고, 새 밑동은 3번과 7번 줄 - 우리 hunk의 문맥
    안이다 - 을 고쳤다.
    """
    vendor = root / "vendor"
    vendor.mkdir()
    _run("init", "-b", "main", cwd=vendor)
    _run("config", "user.email", "t@example.invalid", cwd=vendor)
    _run("config", "user.name", "t", cwd=vendor)

    target = vendor / "a.txt"
    target.write_text(_lines(), encoding="utf-8")
    _run("add", "a.txt", cwd=vendor)
    _run("commit", "-m", "upstream: base", cwd=vendor)
    old_base = _out("rev-parse", "HEAD", cwd=vendor)

    _run("checkout", "-b", us.WORK_BRANCH, cwd=vendor)
    target.write_text(_lines((5, "line 5 - ours")), encoding="utf-8")
    _run("commit", "-am", "ours: line 5", cwd=vendor)

    _run("checkout", "main", cwd=vendor)
    target.write_text(
        _lines((3, "line 3 - upstream"), (7, "line 7 - upstream")), encoding="utf-8"
    )
    _run("commit", "-am", "upstream: moved", cwd=vendor)
    new_base = _out("rev-parse", "HEAD", cwd=vendor)

    _run("checkout", us.WORK_BRANCH, cwd=vendor)
    return vendor, old_base, new_base


def _clash(vendor: Path) -> str:
    """우리와 같은 5번 줄을 업스트림도 고친 커밋. 진짜 충돌이다."""
    _run("checkout", "--detach", "main", cwd=vendor)
    (vendor / "a.txt").write_text(_lines((5, "line 5 - upstream")), encoding="utf-8")
    _run("commit", "-am", "upstream: took line 5 too", cwd=vendor)
    sha = _out("rev-parse", "HEAD", cwd=vendor)
    _run("checkout", us.WORK_BRANCH, cwd=vendor)
    return sha


def test_문맥이_밀려도_3way로_얹힌다(tmp_path: Path):
    vendor, old_base, new_base = _drifted(tmp_path)
    assert us.applies_onto(new_base, old_base, vendor=vendor) is None


def test_얹어_봐도_kr_port는_안_움직인다(tmp_path: Path):
    # 얹어 보는 것과 옮기는 것은 다른 일이다.
    vendor, old_base, new_base = _drifted(tmp_path)
    before = _out("rev-parse", us.WORK_BRANCH, cwd=vendor)
    us.applies_onto(new_base, old_base, vendor=vendor)
    assert _out("rev-parse", us.WORK_BRANCH, cwd=vendor) == before


def test_진짜_같은_줄이_충돌하면_그건_잡는다(tmp_path: Path):
    # 3-way가 아무거나 통과시키면 검사기가 죽는다. 같은 줄을 양쪽이 다르게
    # 고친 것은 사람이 봐야 한다.
    vendor, old_base, _ = _drifted(tmp_path)
    clash = _clash(vendor)
    assert us.applies_onto(clash, old_base, vendor=vendor) is not None


def test_patched_files가_우리가_건드린_파일을_센다(tmp_path: Path):
    vendor, old_base, _ = _drifted(tmp_path)
    (vendor / "b.txt").write_text("새 파일\n", encoding="utf-8")
    _run("add", "b.txt", cwd=vendor)
    _run("commit", "-m", "ours: b", cwd=vendor)
    assert us.patched_files(old_base, vendor=vendor) == {"a.txt", "b.txt"}


# --- 실제로 얹기와 되돌리기 -------------------------------------------------


def test_rebase가_kr_port를_새_밑동에_얹고_백업을_남긴다(tmp_path: Path):
    vendor, old_base, new_base = _drifted(tmp_path)
    old_tip = _out("rev-parse", us.WORK_BRANCH, cwd=vendor)

    assert us.rebase_kr_port(new_base, old_base, "kr-port-old", vendor=vendor) is None

    # 밑동이 새 자리다.
    assert _out("rev-parse", f"{us.WORK_BRANCH}~1", cwd=vendor) == new_base
    # 옛 이력은 백업이 붙잡고 있다.
    assert _out("rev-parse", "kr-port-old", cwd=vendor) == old_tip
    # 3-way라 양쪽 변경이 다 남았다.
    text = (vendor / "a.txt").read_text(encoding="utf-8")
    assert "line 5 - ours" in text
    assert "line 3 - upstream" in text


def test_rebase가_실패하면_kr_port를_되돌린다(tmp_path: Path):
    vendor, old_base, _ = _drifted(tmp_path)
    clash = _clash(vendor)
    old_tip = _out("rev-parse", us.WORK_BRANCH, cwd=vendor)

    problem = us.rebase_kr_port(clash, old_base, "kr-port-old", vendor=vendor)

    assert problem is not None
    assert _out("rev-parse", us.WORK_BRANCH, cwd=vendor) == old_tip
    # 붙이다 만 상태가 안 남는다.
    assert _out("status", "--porcelain", cwd=vendor) == ""


def test_upstream_원격이_있으면_그것으로_받는다(tmp_path: Path):
    # 갓 클론한 vendor는 origin이 미러다(서브모듈이 그 주소로 받는다).
    # vendor_setup이 업스트림을 upstream 이름으로 등록하면 그쪽을 본다.
    vendor, _, _ = _drifted(tmp_path)
    assert us.upstream_remote(vendor) == "origin"
    _run("remote", "add", "upstream", str(tmp_path / "어딘가"), cwd=vendor)
    assert us.upstream_remote(vendor) == "upstream"


# --- 미러 push -------------------------------------------------------------
#
# gitlink이 가리킬 커밋이 원격에 없으면 다음에 클론하는 사람이 못 받는다.


def _with_mirror(tmp_path: Path) -> tuple[Path, str, Path]:
    """미러(bare)와 백업 브랜치·태그까지 갖춘 vendor. (vendor, 새 밑동, 미러)."""
    vendor, _, new_base = _drifted(tmp_path)
    bare = tmp_path / "mirror.git"
    _run("init", "--bare", str(bare), cwd=tmp_path)
    _run("remote", "add", us.MIRROR, str(bare), cwd=vendor)
    _run("branch", "kr-port-old", us.WORK_BRANCH, cwd=vendor)
    _run("tag", "v9.99", new_base, cwd=vendor)
    return vendor, new_base, bare


def test_push_mirror가_세_ref를_민다(tmp_path: Path):
    vendor, new_base, bare = _with_mirror(tmp_path)
    assert us.push_mirror("kr-port-old", "v9.99", vendor=vendor) is None
    assert _out("rev-parse", us.WORK_BRANCH, cwd=bare) == _out(
        "rev-parse", us.WORK_BRANCH, cwd=vendor
    )
    assert _out("rev-parse", "kr-port-old", cwd=bare)
    assert _out("rev-parse", "v9.99^{commit}", cwd=bare) == new_base


def test_이력이_바뀌어도_민다(tmp_path: Path):
    # rebase 뒤의 kr-port는 이력이 다르다. force가 아니면 여기서 막힌다.
    vendor, _, bare = _with_mirror(tmp_path)
    assert us.push_mirror("kr-port-old", "v9.99", vendor=vendor) is None
    _run("commit", "--amend", "-m", "ours: rewritten", cwd=vendor)
    assert us.push_mirror("kr-port-old", "v9.99", vendor=vendor) is None
    assert _out("rev-parse", us.WORK_BRANCH, cwd=bare) == _out(
        "rev-parse", us.WORK_BRANCH, cwd=vendor
    )


def test_미러가_없으면_이유를_돌려준다(tmp_path: Path):
    vendor, _, new_base = _drifted(tmp_path)
    _run("branch", "kr-port-old", us.WORK_BRANCH, cwd=vendor)
    _run("tag", "v9.99", new_base, cwd=vendor)
    assert us.push_mirror("kr-port-old", "v9.99", vendor=vendor) is not None


# --- 실제 저장소 ----------------------------------------------------------


needs_vendor = pytest.mark.skipif(not us.vendor_present(), reason="vendor 클론이 없다")


def test_이_저장소의_핀이_읽힌다():
    pin = us.read_pin()
    assert pin["commit"] and pin["tag"] and pin["repo"]


@needs_vendor
def test_핀이_가리키는_커밋이_vendor에_있다():
    # 핀이 존재하지 않는 커밋을 가리키면 패치 검사 전체가 의미를 잃는다.
    assert us.commit_exists(us.read_pin()["commit"])


def test_이력에_핀_태그가_있고_번역돼_있다():
    # 지금 vendor가 가리키는 판이 무엇인지 사용자가 한국어로 읽을 수 있어야 한다.
    text = us.CHANGES.read_text(encoding="utf-8")
    pin = us.read_pin()
    assert us.missing_tags(text, [pin["tag"]]) == []
    assert us.untranslated_tags(text) == []
