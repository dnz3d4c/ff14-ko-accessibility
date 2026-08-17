"""The Korean signature we ship has to still match exactly once.

`overlay/patches/0004` hands ClientStructs a hand-found address for
`AtkResNode::IsVisible`, located by a byte signature. If a game patch moves or
recompiles that function the signature goes ambiguous or missing, and the mod
silently drops to the managed replica. This test is how that gets noticed: it
reads the signature out of the shipped patch - not out of a copy - and checks it
against the installed Korean binary.

Skipped when the game is not installed on this machine. Point FFXIV_KR_GAME at
`...\\game\\ffxiv_dx11.exe` to run it elsewhere.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from sig_probe import Match, load_text_section

REPO = Path(__file__).resolve().parents[3]
PATCHES = REPO / "overlay" / "patches"
DEFAULT_GAME = Path(
    r"C:\Program Files (x86)\FINAL FANTASY XIV - KOREA\game\ffxiv_dx11.exe")
GAME = Path(os.environ.get("FFXIV_KR_GAME", DEFAULT_GAME))

_CONSTANT = "KoreanBodySignature"
_LITERAL_RE = re.compile(r'"([^"]*)"')


def shipped_signature() -> str:
    """The signature literal as the patch series actually ships it."""
    for patch in sorted(PATCHES.glob("*.patch")):
        added = [line[1:] for line in patch.read_text(encoding="utf-8").splitlines()
                 if line.startswith("+")]
        for index, line in enumerate(added):
            if _CONSTANT not in line or "const string" not in line:
                continue
            parts: list[str] = []
            for tail in added[index:]:
                parts += _LITERAL_RE.findall(tail)
                if tail.rstrip().endswith(";"):
                    break
            if parts:
                return "".join(parts)
    raise AssertionError(f"no {_CONSTANT} in {PATCHES}")


class TestShippedSignature:
    def test_it_is_a_signature_and_not_an_accident(self) -> None:
        signature = shipped_signature()
        tokens = signature.split()
        assert len(tokens) >= 16, f"suspiciously short: {signature!r}"
        assert all(token == "??" or len(token) == 2 for token in tokens)

    @pytest.mark.skipif(not GAME.exists(), reason=f"game not installed at {GAME}")
    def test_it_matches_the_korean_binary_exactly_once(self) -> None:
        text, text_rva = load_text_section(GAME)
        matches = Match.collect(text, text_rva, shipped_signature())
        assert len(matches) == 1, (
            f"{len(matches)} matches - the plugin refuses to install the address "
            "when it is not unique, so node visibility would fall back to the "
            "managed replica"
        )

    @pytest.mark.skipif(not GAME.exists(), reason=f"game not installed at {GAME}")
    def test_upstreams_call_site_signature_is_still_absent(self) -> None:
        # The premise of the whole patch: this is why ClientStructs comes up
        # empty on the Korean client. If it ever matches, the patch is obsolete.
        text, text_rva = load_text_section(GAME)
        upstream = "E8 ?? ?? ?? ?? 3C 01 75 7F"
        assert Match.collect(text, text_rva, upstream) == []
