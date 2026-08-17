"""Tests for the verdict side.

Every signature we probed came back UNIQUE, which is also exactly what a
classifier stuck on one answer would report. These make the other two verdicts
observable - once synthetically, once against the real Korean binary with a
pattern already known to be absent from it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from classify import cache_sample, verdict
from sig_probe import Match, load_text_section

DEFAULT_GAME = Path(
    r"C:\Program Files (x86)\FINAL FANTASY XIV - KOREA\game\ffxiv_dx11.exe")
GAME = Path(os.environ.get("FFXIV_KR_GAME", DEFAULT_GAME))

# `sig-probe` ships a test proving this global-client pattern does not exist on
# the Korean build - the reason our own patch had to hand-find that address.
KNOWN_ABSENT = "E8 ?? ?? ?? ?? 3C 01 75 7F"


class TestVerdict:
    def test_one_match(self) -> None:
        assert verdict(1) == "UNIQUE"

    def test_no_match(self) -> None:
        assert verdict(0) == "NOT FOUND"

    def test_several_matches(self) -> None:
        assert verdict(2) == "AMBIGUOUS"


@pytest.mark.skipif(not GAME.exists(), reason=f"game not installed at {GAME}")
class TestAgainstTheKoreanBinary:
    def test_a_pattern_known_to_be_absent_reports_not_found(self) -> None:
        text, text_rva = load_text_section(GAME)
        matches = Match.collect(text, text_rva, KNOWN_ABSENT)
        assert verdict(len(matches)) == "NOT FOUND"

    def test_a_common_prologue_reports_ambiguous(self) -> None:
        # `48 89 5C 24 08 57 48 83 EC 20` opens thousands of functions, so it
        # proves the count reaches the classifier rather than being capped.
        text, text_rva = load_text_section(GAME)
        matches = Match.collect(text, text_rva, "48 89 5C 24 08 57 48 83 EC 20")
        assert verdict(len(matches)) == "AMBIGUOUS"


class TestCacheSample:
    def test_relfollow_entries_are_left_out(self, tmp_path: Path) -> None:
        # They resolve through a rip-relative operand to a static object, not to
        # a function, so a match count says nothing about a plugin's hooks.
        cache = tmp_path / "cs.json"
        cache.write_text('{"48 8B 05 ?? ?? ?? ??+relfollow[3]": 1, "48 85 C9": 2}',
                         encoding="utf-8")
        assert cache_sample(cache, 10) == ["48 85 C9"]

    def test_the_sample_is_capped(self, tmp_path: Path) -> None:
        cache = tmp_path / "cs.json"
        cache.write_text(json.dumps({f"48 85 C{i}": i for i in range(9)}),
                         encoding="utf-8")
        assert len(cache_sample(cache, 3)) == 3
