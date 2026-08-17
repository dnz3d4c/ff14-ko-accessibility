"""Tests for the offline signature probe.

The probe has to agree with Dalamud's SigScanner, because a signature we ship in
the plugin is only as good as the offline check that produced it. Everything here
runs on synthetic bytes - no game install needed.
"""
from __future__ import annotations

import struct

import pytest
from sig_probe import (
    Match,
    find_matches,
    load_text_section,
    parse_signature,
    resolve_target,
    split_directive,
)


class TestSplitDirective:
    """ClientStructs appends "+relfollow[n]" to say "the answer is the address
    the relative operand at byte n points at" - rip-relative loads, not calls."""

    def test_directive_is_split_off(self) -> None:
        clean, rel = split_directive("48 8B 05 ?? ?? ?? ??+relfollow[3]")
        assert clean == "48 8B 05 ?? ?? ?? ??"
        assert rel == 3

    def test_signature_without_directive(self) -> None:
        assert split_directive("48 85 C9") == ("48 85 C9", None)

    def test_directive_in_the_middle_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            split_directive("48+relfollow[0] 85 C9")


class TestParseSignature:
    def test_hex_bytes(self) -> None:
        pattern, mask = parse_signature("48 85 C9")
        assert pattern == b"\x48\x85\xc9"
        assert mask == b"\xff\xff\xff"

    def test_wildcards(self) -> None:
        pattern, mask = parse_signature("E8 ?? ?? ?? ?? 3C 01")
        assert mask == b"\xff\x00\x00\x00\x00\xff\xff"
        assert pattern[1:5] == b"\x00\x00\x00\x00"

    def test_single_question_mark_is_a_wildcard(self) -> None:
        # Dalamud accepts both "??" and "?" for one unknown byte.
        _, mask = parse_signature("48 ? C9")
        assert mask == b"\xff\x00\xff"

    def test_lowercase_and_extra_spaces(self) -> None:
        pattern, _ = parse_signature("  48  85   c9 ")
        assert pattern == b"\x48\x85\xc9"

    def test_empty_signature_rejected(self) -> None:
        with pytest.raises(ValueError):
            parse_signature("   ")

    def test_garbage_token_rejected(self) -> None:
        with pytest.raises(ValueError):
            parse_signature("48 ZZ")


class TestFindMatches:
    def test_finds_every_occurrence(self) -> None:
        text = b"\x00\x48\x85\xc9\x00\x48\x85\xc9\x00"
        assert find_matches(text, "48 85 C9") == [1, 5]

    def test_wildcard_matches_any_byte(self) -> None:
        text = b"\x48\x00\xc9" + b"\x48\xff\xc9"
        assert find_matches(text, "48 ?? C9") == [0, 3]

    def test_overlapping_matches_are_all_reported(self) -> None:
        text = b"\xaa\xaa\xaa\xaa"
        assert find_matches(text, "AA AA") == [0, 1, 2]

    def test_no_match(self) -> None:
        assert find_matches(b"\x01\x02\x03", "48 85 C9") == []

    def test_signature_starting_with_wildcards(self) -> None:
        # The fixed bytes are not at the front, so the search has to anchor
        # inside the pattern and step back. Getting this wrong silently drops
        # matches, which would make an ambiguous signature look unique.
        text = b"\x11\x22\x48\x85\xc9\x33"
        assert find_matches(text, "?? ?? 48 85 C9") == [0]

    def test_anchor_step_back_does_not_underflow(self) -> None:
        text = b"\x48\x85\xc9\x33"
        assert find_matches(text, "?? ?? 48 85 C9") == []

    def test_match_running_past_the_end_is_not_reported(self) -> None:
        text = b"\x48\x85\xc9"
        assert find_matches(text, "48 85 C9 ??") == []

    def test_limit_caps_the_result(self) -> None:
        text = b"\xaa" * 10
        assert find_matches(text, "AA", limit=3) == [0, 1, 2]


class TestResolveTarget:
    def test_call_follows_the_relative_operand(self) -> None:
        # E8 at .text offset 0 with rel32 = +0x10 -> target is 0 + 5 + 0x10.
        text = b"\xe8" + struct.pack("<i", 0x10) + b"\x90" * 32
        assert resolve_target(text, 0x1000, 0) == 0x1000 + 5 + 0x10

    def test_backward_call(self) -> None:
        text = b"\x90" * 8 + b"\xe8" + struct.pack("<i", -0x20) + b"\x90" * 8
        assert resolve_target(text, 0x1000, 8) == 0x1000 + 8 + 5 - 0x20

    def test_jmp_follows_too(self) -> None:
        text = b"\xe9" + struct.pack("<i", 0x40) + b"\x90" * 32
        assert resolve_target(text, 0x2000, 0) == 0x2000 + 5 + 0x40

    def test_other_opcodes_resolve_to_the_match_itself(self) -> None:
        text = b"\x48\x85\xc9"
        assert resolve_target(text, 0x1000, 0) == 0x1000

    def test_relfollow_reads_the_operand_at_the_given_byte(self) -> None:
        # lea rcx, [rip+0x30] at .text offset 0: operand at byte 3, next
        # instruction at byte 7, so the target is 0x1000 + 7 + 0x30.
        text = b"\x48\x8d\x0d" + struct.pack("<i", 0x30) + b"\x90" * 32
        assert resolve_target(text, 0x1000, 0, rel_offset=3) == 0x1000 + 7 + 0x30

    def test_relfollow_wins_over_the_call_rule(self) -> None:
        text = b"\xe8" + struct.pack("<i", 0x10) + struct.pack("<i", 0x20) + b"\x90" * 16
        assert resolve_target(text, 0, 0, rel_offset=5) == 5 + 4 + 0x20


def _synthetic_pe(text_bytes: bytes, text_rva: int = 0x1000) -> bytes:
    """Smallest PE the loader in sig_probe has to understand."""
    pe_offset = 0x80
    opt_size = 0xF0
    header = bytearray(pe_offset + 24 + opt_size + 40 * 2)
    header[0:2] = b"MZ"
    struct.pack_into("<I", header, 0x3C, pe_offset)
    header[pe_offset:pe_offset + 4] = b"PE\0\0"
    struct.pack_into("<H", header, pe_offset + 6, 2)          # NumberOfSections
    struct.pack_into("<H", header, pe_offset + 20, opt_size)  # SizeOfOptionalHeader
    sections = pe_offset + 24 + opt_size
    raw_ptr = len(header)
    for i, (name, rva, size) in enumerate(
            [(b".text", text_rva, len(text_bytes)), (b".data", 0x9000, 0)]):
        off = sections + i * 40
        header[off:off + len(name)] = name
        struct.pack_into("<IIII", header, off + 8, size, rva, size,
                         raw_ptr if i == 0 else 0)
    return bytes(header) + text_bytes


class TestLoadTextSection:
    def test_reads_the_text_section_and_its_rva(self, tmp_path) -> None:
        body = b"\x48\x85\xc9\xc3"
        path = tmp_path / "fake.exe"
        path.write_bytes(_synthetic_pe(body, text_rva=0x1234))
        text, rva = load_text_section(path)
        assert text == body
        assert rva == 0x1234

    def test_rejects_a_non_pe_file(self, tmp_path) -> None:
        path = tmp_path / "not.exe"
        path.write_bytes(b"MZ" + b"\x00" * 0x100)
        with pytest.raises(ValueError):
            load_text_section(path)


class TestMatchReporting:
    def test_match_carries_both_the_site_and_the_target(self) -> None:
        text = b"\xe8" + struct.pack("<i", 0x10) + b"\x3c\x01\x75\x7f" + b"\x90" * 16
        matches = Match.collect(text, 0x1000, "E8 ?? ?? ?? ?? 3C 01 75 7F")
        assert len(matches) == 1
        assert matches[0].site == 0x1000
        assert matches[0].target == 0x1000 + 5 + 0x10

    def test_distinct_targets_are_counted(self) -> None:
        # Two call sites reach 0x105 and one reaches 0x205. The operand is
        # relative, so the same target needs a different operand per site -
        # which is exactly what target counting has to see through.
        def call_to(site: int, target: int) -> bytes:
            return b"\xe8" + struct.pack("<i", target - (site + 5)) + b"\x3c\x01"

        text = call_to(0, 0x105) + call_to(7, 0x205) + call_to(14, 0x105)
        text += b"\x90" * 0x400
        counts = Match.target_counts(Match.collect(text, 0, "E8 ?? ?? ?? ?? 3C 01"))
        assert counts == {0x105: 2, 0x205: 1}

    def test_collect_honours_a_relfollow_directive(self) -> None:
        text = b"\x48\x8d\x0d" + struct.pack("<i", 0x40) + b"\x90" * 32
        matches = Match.collect(text, 0x1000, "48 8D 0D ?? ?? ?? ??+relfollow[3]")
        assert [m.target for m in matches] == [0x1000 + 7 + 0x40]
