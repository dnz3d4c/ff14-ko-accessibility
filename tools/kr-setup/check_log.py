"""Dalamud 로그를 읽고 이번 판이 정상인지 판정한다.

`docs/dev/kr-runtime.md` §10이 "적용 완료 알림을 믿으면 안 된다"고 적은 그
판정을 눈 대신 기계가 한다. 25만 자짜리 로그에서 다섯 줄을 찾는 일을 매번
손으로 하지 않게 하는 것이 목적이다.

**마지막 세션만 본다.** 로그는 세션을 이어 붙이기 때문에, 앞판의 성공 줄이
이번 판의 실패를 가린다.

언어 판정만 로그가 아니라 옆의 `dalamud.troubleshooting.json`을 본다. 로그
전문에 `"Language"` 문자열이 **0건**이라서다(2026-08-18 실측). 그전까지
`kr-runtime-setup.md` §10이 로그에서 찾으라고 적어 뒀는데 틀린 안내였다.

사용법:
    uv run --no-project python tools/kr-setup/check_log.py [로그경로]

경로를 안 주면 `kr_profile`이 정한 프로필 루트의 `dalamud-kr-gui.log`를 본다.
루트를 여기서 박지 않는 이유는 그 모듈이 갖는다 - 박아 두면 설치기와 갈리고,
갈리면 **엉뚱한 판의 로그를 읽고 정상이라고 말한다.**
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kr_profile  # noqa: E402  - 같은 폴더. 배치가 파일 경로로 직접 부른다

#: 세션 경계. Dalamud가 주입될 때마다 찍는다.
SESSION_START = "Initializing a session.."


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    #: 통과 근거로 삼은 줄. 실패면 None.
    evidence: str | None
    #: 실패했을 때 어디를 보라고 할지.
    hint: str


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    key_conflicts: int = 0
    unknown_keys: int = 0
    #: 어느 경로로 적재됐나. 개발 중에는 개발용이 정상이고 배포 상태에서는
    #: 정식이 정상이라, 이건 합격/불합격이 아니라 사실 보고다.
    route: str = "알 수 없음"

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)


def last_session(text: str) -> list[str]:
    """마지막 세션의 줄만 돌려준다. 경계가 없으면 전체를 한 판으로 본다."""
    lines = text.splitlines()
    start = 0
    for index, line in enumerate(lines):
        if SESSION_START in line:
            start = index
    return lines[start:]


def _find(lines: list[str], *needles: str) -> str | None:
    """모든 조각을 한 줄 안에서 만족하는 첫 줄. 없으면 None."""
    for line in lines:
        if all(needle in line for needle in needles):
            return line.strip()
    return None


def inspect(text: str, sidecar: str = "") -> Report:
    """로그 전문과 troubleshooting json 전문을 받아 판정 결과를 돌려준다."""
    lines = last_session(text)
    report = Report()

    language_ok = '"Language": "Korean"' in sidecar
    report.checks.append(
        Check(
            "KR 언어 패치",
            language_ok,
            '"Language": "Korean"' if language_ok else None,
            "업데이터의 Check Update가 KR 패치를 안 붙였다. kr-runtime-setup.md 5절",
        )
    )

    # (이름, 찾을 조각들, 실패 시 안내)
    probes: list[tuple[str, tuple[str, ...], str]] = [
        (
            "게임 데이터 판독",
            ("Lumina is ready",),
            "sqpack을 못 읽었다. 게임 설치 경로를 본다",
        ),
        (
            "접근성 모드 적재",
            ("Finished loading FF14Accessibility",),
            "설정 시딩 세 조건 중 하나가 어긋났다. kr-runtime-setup.md 7절",
        ),
        (
            "vnavmesh 적재",
            ("Finished loading vnavmesh",),
            "자동 이동이 안 된다. kr-runtime-setup.md 8절",
        ),
        (
            "노드 가시성이 게임 함수",
            ("[Compat]", "IsVisible", "Korean signature"),
            "모드 내 구현으로 내려갔다. 게임 패치로 시그니처가 깨졌을 수 있다 - "
            "tools/sig-probe 테스트를 돌린다",
        ),
        (
            "음성 출력 도달",
            ("[Speak]",),
            "Tolk가 스크린리더에 닿지 못했다",
        ),
        (
            "자동 이동 도착",
            ("[Speak]", "Target reached"),
            "이번 판에서 자동 이동을 안 썼거나 도착에 실패했다",
        ),
    ]

    for name, needles, hint in probes:
        evidence = _find(lines, *needles)
        report.checks.append(Check(name, evidence is not None, evidence, hint))

    # 어느 경로로 들어왔나. 설치기는 installedPlugins에 넣고(정식), run\build.bat은
    # devPlugins에 넣는다(개발용). Dalamud가 줄 모양으로 구분해 준다.
    as_installed = _find(lines, "Loading plugin FF14Accessibility")
    as_dev = _find(lines, "Loading dev plugin FF14Accessibility")
    report.route = (
        "정식 플러그인" if as_installed and not as_dev
        else "개발용 플러그인" if as_dev and not as_installed
        else "둘 다" if as_dev and as_installed
        else "알 수 없음"
    )
    # **두 사본이 동시에 뜨는 것만 결함이다.** 같은 명령과 같은 단축키를 두 번
    # 등록하고, 게임 안에서는 "가끔 두 번 말한다"로만 드러난다.
    report.checks.append(
        Check(
            "사본이 하나뿐",
            not (as_dev and as_installed),
            as_installed if as_dev and as_installed else None,
            "정식 설치와 개발용 설치가 같이 있다. 설치기를 다시 돌려 dev 사본을 걷어낸다",
        )
    )

    for line in lines:
        if "[ERR]" in line or "[FTL]" in line:
            report.errors += 1
        elif "[WRN]" in line:
            report.warnings += 1
            if "KONFLIKT" in line:
                report.key_conflicts += 1
            elif "Unbekannte Tastenangabe" in line:
                report.unknown_keys += 1

    return report


def default_log_path() -> Path:
    # 프로필 루트를 여기서 정하지 않는다. 박아 두면 설치기·배치와 갈리고,
    # 갈리면 **엉뚱한 판의 로그를 읽고 정상이라고 말한다.** 규칙은 kr_profile이 갖는다.
    return Path(kr_profile.resolve_root()) / "dalamud-kr-gui.log"


def render(report: Report) -> str:
    lines = ["== 마지막 세션 판정 ==", ""]
    for check in report.checks:
        mark = "통과" if check.passed else "실패"
        lines.append(f"[{mark}] {check.name}")
        if not check.passed:
            lines.append(f"         -> {check.hint}")

    lines.append("")
    lines.append(f"적재 경로: {report.route}")
    lines.append(f"오류 {report.errors}건, 경고 {report.warnings}건")
    if report.key_conflicts:
        lines.append(f"  키 충돌 {report.key_conflicts}건 (현황판 W-03)")
    if report.unknown_keys:
        lines.append(f"  모르는 키 이름 {report.unknown_keys}건 (현황판 W-04)")

    lines.append("")
    lines.append("전체: 정상" if report.ok else "전체: 확인 필요")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else default_log_path()
    if not path.is_file():
        print(f"로그가 없다: {path}", file=sys.stderr)
        return 2

    # Dalamud가 UTF-8로 쓰지만 깨진 바이트가 섞이면 판정 자체를 못 하게 된다.
    text = path.read_text(encoding="utf-8", errors="replace")

    sidecar_path = path.with_name("dalamud.troubleshooting.json")
    sidecar = (
        sidecar_path.read_text(encoding="utf-8", errors="replace")
        if sidecar_path.is_file()
        else ""
    )

    report = inspect(text, sidecar)
    print(render(report))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
