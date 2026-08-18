"""업스트림을 따라잡는 도구.

업스트림(`derbruedi/ff14-accessibility`)은 **주 30커밋에 거의 매일 릴리스**다.
우리 패치는 그 위에 얹혀 있고, 우리가 안 보는 동안에도 밑바닥이 움직인다.
그걸 손으로 쫓으면 따라잡는 일이 본업이 된다.

이 도구가 하는 일은 셋이다.

1. **얼마나 벌어졌는지 잰다** (`--check`) - 새 태그, 바뀐 파일이 우리 패치와
   겹치는지, 우리 패치가 새 태그에 아직 붙는지, 안내 문장이 몇 개 늘었는지
2. **변경 이력을 한국어로 남길 자리를 만든다** (`--notes`) - 업스트림은
   **독일어로 개발된다.** 커밋도 릴리스 노트도 독일어라 그대로는 못 읽는다.
   원문과 함께 `(미번역)` 자리를 만들고, 그 자리가 채워지기 전에는 검사가
   통과하지 않는다
3. **깨끗한 경우에 한해 실제로 올린다** (`--to <태그>`) - 패치가 충돌 없이
   붙을 때만. 하나라도 어긋나면 아무것도 건드리지 않고 멈춘다

**핀(`upstream.json`)이 이 저장소의 기준이다.** `vendor/`는 버전 관리 밖이라
우리 저장소에는 "지금 어느 판 위에 있는지"가 아무 데도 안 적혀 있었다. 그러면
다른 머신에서 클론한 사람은 그날의 최신 `main` 위에 패치를 붙이게 되고, 붙는
자리가 다른 것을 아무도 모른다. 핀이 그 자리를 못박는다.

사용법:
    run\\sync.bat            점검 (아무것도 안 옮긴다)
    run\\sync.bat v5.87      v5.87로 올린다

    uv run --no-project python tools/upstream-sync/upstream_sync.py --notes  # 이력 자리
    uv run --no-project python tools/upstream-sync/upstream_sync.py --json   # CI가 읽는 것

`--json`은 사람이 읽는 것과 **같은 조사 결과**를 낸다. 출력을 두 벌 만들면
둘이 갈라지고, 갈라진 쪽을 아무도 안 본다.

절차와 판단 기준: docs/upstream-sync.md
"""

from __future__ import annotations

import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VENDOR = REPO / "vendor" / "ff14-accessibility"
PIN = REPO / "upstream.json"
CHANGES = REPO / "docs" / "upstream-changes.md"

#: 번역이 안 된 자리. 이 표시가 남아 있으면 검사가 통과하지 않는다.
UNTRANSLATED = "(미번역)"

#: `## v5.87 — 2026-08-17`
_SECTION_RE = re.compile(r"^## (?P<tag>\S+)(?:\s+—\s+(?P<date>.*))?$", re.M)

#: `v5.87` -> (5, 87)
_VERSION_RE = re.compile(r"(\d+)")

WORK_BRANCH = "kr-port"

#: 패치를 다시 뽑을 때 쓰는 디렉토리. 순서가 곧 적용 순서다.
PATCH_DIRS = ("patches", "overlay/patches")


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str


# --- 태그 -----------------------------------------------------------------


def version_key(tag: str) -> tuple[int, ...]:
    """태그를 숫자로 비교할 수 있게 바꾼다.

    문자열로 비교하면 `v5.9`가 `v5.87`보다 뒤로 간다. 숫자를 못 찾으면
    `(-1,)`을 돌려 맨 뒤로 민다 - 형식이 바뀌었을 때 도구가 죽는 것보다
    "새 태그가 아니다"로 조용히 미는 쪽이 낫다. 그래도 `--check`가 전체
    태그 수를 같이 찍으므로 사라지지는 않는다.
    """
    numbers = _VERSION_RE.findall(tag)
    if not numbers:
        return (-1,)
    return tuple(int(n) for n in numbers)


def newer_tags(tags: list[str], current: str) -> list[str]:
    """핀보다 새 태그만, 오래된 것부터."""
    here = version_key(current)
    return sorted((t for t in tags if version_key(t) > here), key=version_key)


def previous_tag(tag: str, tags: list[str]) -> str | None:
    """`tag` 바로 앞선 태그. 없으면 None.

    핀을 이미 옮긴 뒤에 그 판의 이력 자리를 만들 때 커밋 범위의 시작이
    필요한데, 핀 파일에는 이전 태그가 안 남는다(덮어쓴다). 태그 목록에서
    다시 고른다. 없으면 **지어내지 않는다** - 아무거나 넣으면 범위가
    저장소 처음까지 벌어져서 이력이 아니라 전사가 된다.
    """
    older = [t for t in tags if version_key(t) < version_key(tag)]
    return max(older, key=version_key) if older else None


# --- 핀 -------------------------------------------------------------------


def read_pin(path: Path = PIN) -> dict:
    """핀을 읽는다. 없으면 지어내지 않고 터진다."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_pin(pin: dict, path: Path = PIN) -> None:
    path.write_text(
        json.dumps(pin, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


# --- 변경 이력 문서 --------------------------------------------------------


def split_sections(text: str) -> dict[str, str]:
    """태그별 구획. 문서에 적힌 순서(최신이 위)를 지킨다."""
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group("tag")] = text[match.start() : end]
    return sections


def untranslated_tags(text: str) -> list[str]:
    """아직 한국어로 안 옮긴 구획.

    이게 비어 있지 않으면 동기화는 끝난 게 아니다. 원문만 있는 이력은
    독일어를 읽는 사람에게만 이력이다.
    """
    return [tag for tag, body in split_sections(text).items() if UNTRANSLATED in body]


def missing_tags(text: str, tags: list[str]) -> list[str]:
    """이력에 아예 없는 태그. 미번역보다 더 조용한 실패다."""
    known = split_sections(text)
    return [tag for tag in tags if tag not in known]


def tags_to_write(pin_tag: str, tags: list[str], text: str) -> list[str]:
    """이력에 자리를 만들어야 하는 판. 오래된 것부터.

    **핀 태그 자신도 대상이다.** `--to`가 끝나면 핀은 이미 새 태그이고 그
    시점에 "새 태그"는 0개다. 정작 없는 것은 방금 올라탄 그 판의 이력인데,
    새것만 세면 만들 자리가 없다고 답한다.

    `--check`와 `--notes`가 **같은 목록을 보게** 하는 것이 이 함수의 목적이다.
    갈라졌던 실물이 있다 - v5.88 동기화에서 `--check`는 "변경 이력에 없는 판:
    v5.88"이라고 하고 `--notes`는 "새로 만들 자리가 없다"고 답했다. 그래서
    그 절을 손으로 썼다.
    """
    return missing_tags(text, [pin_tag, *newer_tags(tags, pin_tag)])


def render_section(tag: str, date: str, commits: list[Commit]) -> str:
    """번역을 기다리는 구획을 만든다.

    **원문을 같이 남긴다.** 옮긴 것이 틀렸을 때 되짚을 자리가 그것뿐이고,
    독일어를 아는 사람이 나중에 검토할 수도 있다.
    """
    lines = [f"## {tag} — {date}", "", UNTRANSLATED, ""]
    for commit in commits:
        lines.append(f"- `{commit.sha}` {UNTRANSLATED}")
        lines.append(f"  원문: {commit.subject}")
    lines.append("")
    return "\n".join(lines)


def insert_sections(text: str, sections: list[str]) -> str:
    """새 구획을 맨 위(머리말 바로 아래)에 넣는다. 역순 문서다."""
    if not sections:
        return text
    block = "\n".join(section.rstrip("\n") + "\n" for section in sections)
    first = _SECTION_RE.search(text)
    if first is None:
        return text.rstrip("\n") + "\n\n" + block
    return text[: first.start()] + block + "\n" + text[first.start() :]


# --- git ------------------------------------------------------------------


def _git(*args: str, cwd: Path = VENDOR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        # 우리 저장소의 core.hooksPath가 새 나가면 am이 죽는다.
        ["git", "-c", "core.hooksPath=", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def vendor_present(vendor: Path = VENDOR) -> bool:
    return (vendor / ".git").exists()


def commit_exists(sha: str, vendor: Path = VENDOR) -> bool:
    return _git("cat-file", "-e", f"{sha}^{{commit}}", cwd=vendor).returncode == 0


def fetch(vendor: Path = VENDOR) -> str | None:
    """업스트림에서 받아 온다. 실패하면 이유를 돌려준다(오프라인일 수 있다)."""
    result = _git("fetch", "--tags", "origin", cwd=vendor)
    return None if result.returncode == 0 else result.stderr.strip()


def all_tags(vendor: Path = VENDOR) -> list[str]:
    result = _git("tag", "--list", cwd=vendor)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def tag_date(tag: str, vendor: Path = VENDOR) -> str:
    result = _git("log", "-1", "--format=%cs", tag, cwd=vendor)
    return result.stdout.strip() or "날짜 미상"


def rev(ref: str, vendor: Path = VENDOR) -> str:
    return _git("rev-parse", ref, cwd=vendor).stdout.strip()


def commits_between(base: str, head: str, vendor: Path = VENDOR) -> list[Commit]:
    """오래된 것부터. 제목만 쓴다 - 본문까지 옮기면 아무도 안 읽는다."""
    result = _git(
        "log", "--reverse", "--format=%h%x09%s", f"{base}..{head}", cwd=vendor
    )
    commits: list[Commit] = []
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        commits.append(Commit(sha.strip(), subject.strip()))
    return commits


def changed_files(base: str, head: str, vendor: Path = VENDOR) -> list[str]:
    result = _git("diff", "--name-only", base, head, cwd=vendor)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def ordered_patches(repo: Path = REPO) -> list[Path]:
    """적용 순서대로. `patches/`가 먼저다 - 근거는 patches/README.md."""
    found: list[Path] = []
    for name in PATCH_DIRS:
        directory = repo / name
        if directory.is_dir():
            found.extend(sorted(directory.glob("*.patch")))
    return found


def patched_files(repo: Path = REPO) -> set[str]:
    """우리 패치가 건드리는 업스트림 파일. 겹치면 충돌 위험이 있다."""
    files: set[str] = set()
    for patch in ordered_patches(repo):
        for line in patch.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("+++ b/"):
                files.add(line[len("+++ b/") :].strip())
    return files


def applies_onto(base: str, patches: list[Path], vendor: Path = VENDOR) -> str | None:
    """임시 워크트리에서 붙여 본다. 붙으면 None, 아니면 실패한 자리.

    **vendor를 건드리지 않는다.** 붙여 보는 것과 옮기는 것은 다른 일이다.
    """
    if not patches:
        return None

    workdir = Path(tempfile.mkdtemp(prefix="upstream-sync-"))
    tree = workdir / "tree"
    try:
        added = _git("worktree", "add", "--detach", str(tree), base, cwd=vendor)
        if added.returncode != 0:
            return f"임시 워크트리를 못 만들었다: {added.stderr.strip()}"

        applied = _git("am", "-3", *(str(p) for p in patches), cwd=tree)
        if applied.returncode == 0:
            return None

        _git("am", "--abort", cwd=tree)
        tried = [
            line[len("Applying: ") :].strip()
            for line in applied.stdout.splitlines()
            if line.startswith("Applying: ")
        ]
        return tried[-1] if tried else "첫 패치부터 안 붙는다"
    finally:
        _git("worktree", "remove", "--force", str(tree), cwd=vendor)
        shutil.rmtree(workdir, ignore_errors=True)


# --- 명령 -----------------------------------------------------------------


def _string_count() -> int | None:
    """지금 vendor에 있는 안내 문장 쌍의 수. 못 세면 None."""
    sys.path.insert(0, str(REPO / "tools" / "strings-golden"))
    try:
        import strings_golden  # noqa: PLC0415 - 도구 사이 경로 주입이라 위에서 못 한다
    except ImportError:
        return None
    if not strings_golden.SOURCE_ROOT.is_dir():
        return None
    by_file, _ = strings_golden.scan()
    return sum(len(v) for v in by_file.values())


def survey(offline: bool) -> dict:
    """지금 얼마나 벌어져 있는지를 사실만 모아 돌려준다.

    사람이 읽는 것(`cmd_check`)과 CI가 읽는 것(`--json`)이 **같은 것을 보게**
    한다. 출력을 두 벌 만들면 둘이 갈라지고, 갈라진 쪽을 아무도 안 본다.
    """
    pin = read_pin()
    result: dict = {
        "pin": pin,
        "fetch_error": None,
        "new_tags": [],
        "newest": None,
        "commits": 0,
        "untagged_commits": 0,
        "changed_files": 0,
        "overlap": [],
        "applies": None,
        "failing_patch": None,
        "missing_notes": [],
        "untranslated": [],
    }

    if not offline:
        result["fetch_error"] = fetch()

    if not commit_exists(pin["commit"]):
        result["pin_missing"] = True
        return result

    tags = all_tags()
    fresh = newer_tags(tags, pin["tag"])
    result["new_tags"] = fresh
    result["untagged_commits"] = len(commits_between(pin["commit"], "origin/main"))

    if fresh:
        newest = fresh[-1]
        result["newest"] = newest
        commits = commits_between(pin["commit"], newest)
        result["commits"] = len(commits)
        # 독일어 원문 그대로. 옮기는 것은 사람이 하므로 여기서 지어내지 않는다.
        result["subjects"] = [{"sha": c.sha, "subject": c.subject} for c in commits]
        touched = set(changed_files(pin["commit"], newest))
        result["changed_files"] = len(touched)
        result["overlap"] = sorted(touched & patched_files())
        failing = applies_onto(newest, ordered_patches())
        result["applies"] = failing is None
        result["failing_patch"] = failing

    if CHANGES.is_file():
        text = CHANGES.read_text(encoding="utf-8")
        result["missing_notes"] = tags_to_write(pin["tag"], tags, text)
        result["untranslated"] = untranslated_tags(text)
    else:
        result["missing_notes"] = [pin["tag"], *fresh]

    return result


def render_issue_body(found: dict) -> str | None:
    """감시가 열 이슈. 첫 줄이 제목이고, 빈 줄 하나 뒤가 본문이다.

    새 태그가 없으면 None - 알릴 게 없으면 이슈도 없다.

    **이걸 CI 안에서 만들지 않는다.** 러너에만 있는 도구로 조립하면 이
    머신에서 돌려 볼 수가 없고, 못 돌려 보는 코드는 처음 필요한 날
    깨져 있는다.
    """
    newest = found.get("newest")
    if not newest:
        return None

    pin = found["pin"]
    overlap = found["overlap"]
    lines = [
        f"업스트림 {newest} — 동기화 대기",
        "",
        f"핀 `{pin['tag']}` (`{pin['commit'][:7]}`, {pin['synced']} 동기화) 이후 "
        "업스트림이 움직였다.",
        "",
        f"- 새 태그 {len(found['new_tags'])}개: {', '.join(found['new_tags'])}",
        f"- 새 커밋 {found['commits']}건, 바뀐 파일 {found['changed_files']}개",
    ]
    if overlap:
        lines.append(f"- 우리 패치가 건드리는 파일과 겹침: {', '.join(overlap)}")
    else:
        lines.append("- 우리 패치와 겹치는 파일 없음")
    lines.append(
        "- 우리 패치는 새 태그에 **깨끗이 붙는다**"
        if found["applies"]
        else f"- **패치가 안 붙는다** (처음 실패: {found['failing_patch']})"
    )

    lines += ["", "## 원문 (독일어)", ""]
    lines.append("여기서는 못 옮긴다. 한국어 이력은 로컬에서 만든다.")
    lines.append("")
    for item in found.get("subjects", []):
        lines.append(f"- `{item['sha']}` {item['subject']}")

    lines += ["", "## 할 것", "", "```", f"run\\sync.bat {newest}", "```", ""]
    lines.append("그다음 변경 이력을 한국어로 채운다 — `docs/upstream-sync.md` §6.")
    return "\n".join(lines) + "\n"


def cmd_issue_body(offline: bool) -> int:
    if not vendor_present():
        return 0
    body = render_issue_body(survey(offline))
    if body is None:
        return 0
    print(body, end="")
    return 0


def cmd_check(offline: bool, fail_on_new: bool, as_json: bool) -> int:
    if not vendor_present():
        if as_json:
            print(json.dumps({"vendor": False}, ensure_ascii=False))
            return 0
        print("vendor 클론이 없다 - 점검을 건너뛴다.")
        print("  클론: overlay/patches/README.md")
        return 0

    found = survey(offline)
    if as_json:
        print(json.dumps(found, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        _render(found)

    if found.get("pin_missing"):
        return 1
    if found["applies"] is False:
        return 1
    if fail_on_new and found["new_tags"]:
        return 1
    return 1 if found["untranslated"] else 0


def _render(found: dict) -> None:
    pin = found["pin"]
    print("== 업스트림 추종 점검 ==\n")
    print(f"핀: {pin['tag']} ({pin['commit'][:7]}, {pin['synced']} 동기화)")

    if found["fetch_error"]:
        print(f"\n받아오지 못했다 - 있는 것으로만 본다: {found['fetch_error']}")

    if found.get("pin_missing"):
        print(f"\n핀이 가리키는 커밋이 vendor에 없다: {pin['commit']}")
        print("  받아온다: cd vendor/ff14-accessibility && git fetch --tags origin")
        return

    fresh = found["new_tags"]
    if not fresh:
        print("업스트림: 새 태그 없음")
        if found["untagged_commits"]:
            print(
                f"  태그 없는 커밋 {found['untagged_commits']}건이 main에 있다"
                " - 릴리스를 기다린다"
            )
    else:
        newest = found["newest"]
        print(f"업스트림: {newest}")
        print(f"\n새 태그 {len(fresh)}개: {', '.join(fresh)}")
        print(f"새 커밋 {found['commits']}건")

        overlap = found["overlap"]
        print(f"바뀐 파일 {found['changed_files']}개", end="")
        if overlap:
            print(f" - 우리 패치가 건드리는 것과 겹치는 것 {len(overlap)}개:")
            for name in overlap:
                print(f"  {name}")
        else:
            print(" - 우리 패치와 겹치는 것 없음")

        if found["applies"]:
            print(f"\n패치를 {newest}에 붙여 봤다: 깨끗하다")
            print(f"\n다음: run\\sync.bat {newest}")
        else:
            print(f"\n패치가 {newest}에 안 붙는다 (처음 실패: {found['failing_patch']})")
            print("  손으로 붙여 충돌을 본다 - docs/upstream-sync.md §5")

    if found["missing_notes"]:
        print(f"\n변경 이력에 없는 판: {', '.join(found['missing_notes'])}")
        print("  자리 만들기: --notes")
    if found["untranslated"]:
        print(f"\n한국어로 안 옮긴 판: {', '.join(found['untranslated'])}")
        print(f"  {CHANGES.relative_to(REPO).as_posix()}의 {UNTRANSLATED}를 채운다")
    if not found["missing_notes"] and not found["untranslated"]:
        print("\n변경 이력: 전부 한국어로 남아 있다")


def cmd_notes(offline: bool) -> int:
    """새 태그의 변경 이력 자리를 만든다. 번역은 사람이 채운다."""
    if not vendor_present():
        print("vendor 클론이 없다.", file=sys.stderr)
        return 1

    if not offline:
        fetch()

    pin = read_pin()
    tags = all_tags()
    text = CHANGES.read_text(encoding="utf-8") if CHANGES.is_file() else ""
    wanted = tags_to_write(pin["tag"], tags, text)

    if not wanted:
        print("새로 만들 자리가 없다.")
        return 0

    base = pin["commit"]
    sections: list[str] = []
    # 최신이 위로 가야 하므로 오래된 것부터 만들어 뒤집는다.
    for tag in wanted:
        if tag == pin["tag"]:
            # 핀이 이미 이 태그다(`--to`를 먼저 돌린 경우). 커밋 범위의 시작은
            # 핀이 아니라 **그 앞 태그**다 - 핀을 쓰면 범위가 비어서 원문 한
            # 줄 없는 자리가 나온다.
            start = previous_tag(tag, tags)
            if start is None:
                print(f"  {tag}보다 앞선 태그가 없다 - 원문 없이 자리만 만든다")
            commits = commits_between(start, tag) if start else []
        else:
            commits = commits_between(base, tag)
        sections.append(render_section(tag, tag_date(tag), commits))
        base = tag

    CHANGES.write_text(insert_sections(text, list(reversed(sections))), encoding="utf-8")
    print(f"자리 {len(wanted)}개를 만들었다: {', '.join(wanted)}")
    print(f"  {CHANGES.relative_to(REPO).as_posix()}의 {UNTRANSLATED}를 한국어로 채운다")
    print("  원문은 지우지 않는다 - 옮긴 게 틀렸을 때 되짚을 자리다")
    return 0


def cmd_to(tag: str, offline: bool) -> int:
    """실제로 올린다. **깨끗할 때만.**"""
    if not vendor_present():
        print("vendor 클론이 없다.", file=sys.stderr)
        return 1

    if not offline:
        problem = fetch()
        if problem:
            print(f"받아오지 못했다: {problem}", file=sys.stderr)
            return 1

    dirty = [line for line in _git("status", "--porcelain").stdout.splitlines() if line.strip()]
    if dirty:
        print("vendor에 커밋되지 않은 변경이 있다. 먼저 정리한다:", file=sys.stderr)
        for line in dirty[:10]:
            print(f"  {line}", file=sys.stderr)
        return 1

    if not commit_exists(tag):
        print(f"그런 태그가 없다: {tag}", file=sys.stderr)
        return 1

    pin = read_pin()
    patches = ordered_patches()

    failing = applies_onto(tag, patches)
    if failing is not None:
        print(f"패치가 {tag}에 안 붙는다 (처음 실패: {failing}).", file=sys.stderr)
        print("아무것도 건드리지 않았다. 손으로 붙여 충돌을 본다 - "
              "docs/upstream-sync.md §4", file=sys.stderr)
        return 1

    # 되돌릴 자리를 먼저 만든다. 여기서부터 vendor를 건드린다.
    backup = f"kr-port-{pin['tag']}"
    _git("branch", "-f", backup, WORK_BRANCH)
    print(f"되돌릴 자리: {backup}")

    _git("checkout", "--detach", tag)
    _git("branch", "-f", "main", tag)
    _git("branch", "-f", WORK_BRANCH, tag)
    _git("checkout", WORK_BRANCH)

    # 붙여 보기(`applies_onto`)와 같은 방식이어야 한다. 한쪽만 3-way면
    # "붙여 보기는 됐는데 실제 적용이 실패"가 상시로 뜬다.
    applied = _git("am", "-3", *(str(p) for p in patches))
    if applied.returncode != 0:
        _git("am", "--abort")
        _git("branch", "-f", WORK_BRANCH, backup)
        _git("checkout", WORK_BRANCH)
        print("붙여 보기는 됐는데 실제 적용이 실패했다. 되돌렸다.", file=sys.stderr)
        print(applied.stderr, file=sys.stderr)
        return 1

    # 패치를 다시 뽑는다. 부모가 바뀌었으므로 파일 내용도 바뀐다.
    counts = [len(sorted((REPO / name).glob("*.patch"))) for name in PATCH_DIRS]
    revisions = _git("rev-list", "--reverse", f"{tag}..{WORK_BRANCH}").stdout.split()
    boundary = revisions[counts[0] - 1] if counts[0] else tag

    for path in ordered_patches():
        path.unlink()
    _git("format-patch", f"{tag}..{boundary}", "-o", str(REPO / PATCH_DIRS[0]))
    _git("format-patch", f"{boundary}..{WORK_BRANCH}", "-o", str(REPO / PATCH_DIRS[1]))

    write_pin(
        {
            "repo": pin["repo"],
            "tag": tag,
            "commit": rev(tag),
            "synced": datetime.date.today().isoformat(),
        }
    )
    print(f"핀을 {tag}로 옮겼다. 패치 {len(patches)}건을 다시 뽑았다.")

    count = _string_count()
    if count is not None:
        print(f"안내 문장: 지금 {count}쌍")
    print("\n남은 것 - 이 순서로 한다:")
    print("  1. 변경 이력 한국어로: --notes 로 자리를 만들고 채운다")
    print("  2. 골든 대조: uv run --no-project python "
          "tools/strings-golden/strings_golden.py")
    print("  3. 빌드와 검사: run\\check.bat")
    print("  4. 인게임 확인 - 사용자 몫이다")
    return 0


def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    if "--issue-body" in argv:
        return cmd_issue_body(offline)
    if "--notes" in argv:
        return cmd_notes(offline)
    if "--to" in argv:
        index = argv.index("--to")
        if index + 1 >= len(argv):
            print("--to 다음에 태그를 준다. 예: --to v5.87", file=sys.stderr)
            return 2
        return cmd_to(argv[index + 1], offline)
    return cmd_check(
        offline, fail_on_new="--fail-on-new" in argv, as_json="--json" in argv
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
