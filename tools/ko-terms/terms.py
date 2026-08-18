"""게임 용어 대장을 읽는다.

뽑는 쪽은 C#(`Program.cs`)이다 - Lumina로 sqpack을 읽어야 해서다. 이 파일은
그 결과를 다루는 파이썬 쪽이고, 검사가 여기 붙는다.

대장: `overlay/ko/terms.json`
덤프: `tools/ko-terms/out/addon-Korean.tsv` (버전 관리 밖 - 게임 텍스트다)
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CATALOG = REPO / "overlay" / "ko" / "terms.json"
DUMP = Path(__file__).resolve().parent / "out" / "addon-Korean.tsv"


def load_dump(path: Path = DUMP) -> dict[int, str]:
    """`행 번호 -> 문자열`. 덤프가 없으면 빈 사전."""
    if not path.is_file():
        return {}

    rows: dict[int, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        number, _, text = line.partition("\t")
        if number.isdigit():
            rows[int(number)] = text
    return rows
