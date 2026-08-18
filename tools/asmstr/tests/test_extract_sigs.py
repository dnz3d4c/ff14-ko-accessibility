"""Tests for the assembly string extractor.

The judgement that matters is `is_signature`: it decides which literals get
probed against the game binary. Too loose and the report fills with noise that
looks like a broken plugin; too strict and a real signature goes unchecked and
we ship a claim we never tested. The heap parser gets the same treatment,
because a wrong length decode drops every string after it - silently.

Everything except the last class runs on synthetic bytes, no install needed.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest
from extract_sigs import (
    drop_contained,
    extract_signatures,
    is_signature,
    iter_blob_strings,
    iter_us_blobs,
    metadata_heaps,
    read_compressed_uint,
)

def _our_plugin() -> Path:
    """배포된 우리 플러그인 DLL. 경로가 둘이라 둘 다 본다.

    정식 설치(`installedPlugins\\<이름>\\<버전>\\`)가 먼저고, 없으면 개발
    배포(`devPlugins\\<이름>\\`)를 본다. 프로필 루트를 여기서 박지 않는 이유는
    `tools/kr-setup/kr_profile.py`가 갖는다 - 박아 두면 설치기와 갈린다.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kr-setup"))
    import kr_profile

    root = Path(kr_profile.resolve_root())
    installed = root / "installedPlugins" / "FF14Accessibility"
    if installed.is_dir():
        found = sorted(installed.glob("*/FF14Accessibility.dll"))
        if found:
            return found[-1]
    return root / "devPlugins" / "FF14Accessibility" / "FF14Accessibility.dll"


PLUGIN = _our_plugin()


class TestIsSignature:
    def test_a_plain_signature(self) -> None:
        assert is_signature("48 89 5C 24 ?? 57 48 83 EC 20")

    def test_single_question_mark_wildcard(self) -> None:
        # Dalamud's SigScanner accepts "?" as well as "??".
        assert is_signature("48 89 5C 24 ? 57 48 83 EC 20")

    def test_lowercase_hex(self) -> None:
        assert is_signature("48 89 5c 24 ?? 57 48 83 ec 20")

    def test_seven_tokens_is_too_short(self) -> None:
        # Short patterns are ordinary text as often as they are signatures;
        # eight is where the plugin's own literals start.
        assert not is_signature("48 89 5C 24 ?? 57 48")

    def test_prose_is_not_a_signature(self) -> None:
        assert not is_signature("Could not find the address of the function")

    def test_a_hex_word_longer_than_a_byte_is_rejected(self) -> None:
        assert not is_signature("48 89 5C 24 ?? 57 48 8300 EC 20")

    def test_a_non_hex_token_is_rejected(self) -> None:
        assert not is_signature("48 89 5C 24 ?? 57 48 ZZ EC 20")

    def test_all_wildcards_is_rejected(self) -> None:
        # It would match everywhere, so it is never a signature someone wrote -
        # and the probe refuses to scan it for exactly that reason.
        assert not is_signature("?? ?? ?? ?? ?? ?? ?? ?? ??")

    def test_empty_string(self) -> None:
        assert not is_signature("")

    def test_a_guid_is_not_a_signature(self) -> None:
        # Dashes, not spaces, so it never tokenises into byte-sized pieces.
        assert not is_signature("d3b07384-d113-4ec4-9f43-1a2b3c4d5e6f")

    def test_leading_and_trailing_whitespace_is_tolerated(self) -> None:
        assert is_signature("  48 89 5C 24 ?? 57 48 83 EC 20  ")


class TestReadCompressedUint:
    """ECMA-335 II.23.2: one, two or four bytes depending on the top bits."""

    def test_one_byte_form(self) -> None:
        assert read_compressed_uint(b"\x03", 0) == (3, 1)

    def test_two_byte_form(self) -> None:
        # 0x80 | (value >> 8), value & 0xFF -> 0x1234 fits in 14 bits.
        assert read_compressed_uint(b"\x92\x34", 0) == (0x1234, 2)

    def test_four_byte_form(self) -> None:
        assert read_compressed_uint(b"\xc0\x12\x34\x56", 0) == (0x123456, 4)

    def test_reads_at_an_offset(self) -> None:
        assert read_compressed_uint(b"\xff\xff\x05", 2) == (5, 1)


def _us_blob(text: str) -> bytes:
    """One #US entry: compressed length, UTF-16LE body, terminal flag byte."""
    body = text.encode("utf-16-le") + b"\x00"
    if len(body) < 0x80:
        return bytes([len(body)]) + body
    return struct.pack(">H", 0x8000 | len(body)) + body


class TestIterUsBlobs:
    def test_reads_consecutive_strings(self) -> None:
        heap = b"\x00" + _us_blob("hello") + _us_blob("world")
        assert list(iter_us_blobs(heap)) == ["hello", "world"]

    def test_a_long_string_uses_the_two_byte_length(self) -> None:
        long_text = "48 89 5C 24 ?? " * 20
        heap = b"\x00" + _us_blob(long_text) + _us_blob("after")
        # "after" only appears if the long entry's length was decoded correctly.
        assert list(iter_us_blobs(heap)) == [long_text, "after"]

    def test_trailing_padding_does_not_raise(self) -> None:
        heap = b"\x00" + _us_blob("hello") + b"\x00\x00\x00"
        assert list(iter_us_blobs(heap)) == ["hello"]

    def test_a_truncated_entry_is_dropped_not_fatal(self) -> None:
        heap = b"\x00" + _us_blob("hello") + b"\x40" + b"ab"
        assert list(iter_us_blobs(heap)) == ["hello"]


def _ser_string(text: str) -> bytes:
    """One custom-attribute SerString: compressed length, then UTF-8."""
    body = text.encode("utf-8")
    if len(body) < 0x80:
        return bytes([len(body)]) + body
    return struct.pack(">H", 0x8000 | len(body)) + body


class TestIterBlobStrings:
    """`[Signature("...")]` arguments are UTF-8 in `#Blob`, not UTF-16 in `#US`,
    so a `#US`-only extractor misses every attribute-driven hook - which is how
    most plugins declare them."""

    SIG = "48 89 5C 24 ?? 57 48 83 EC 20 48 8B D9"

    def test_finds_a_length_prefixed_string(self) -> None:
        heap = b"\x00\x01\x00" + _ser_string(self.SIG) + b"\x00\x00"
        assert self.SIG in list(iter_blob_strings(heap))

    def test_finds_one_behind_a_two_byte_length(self) -> None:
        long_sig = " ".join(["48"] * 60)
        heap = b"\x00" + _ser_string(long_sig)
        assert long_sig in list(iter_blob_strings(heap))

    def test_a_run_cut_short_by_binary_data_is_not_yielded(self) -> None:
        # A length that overshoots into raw metadata must not produce a string:
        # that is the failure mode that would invent signatures out of noise.
        heap = b"\x40" + self.SIG.encode()[:20] + b"\xff\xfe\x00\x01"
        assert self.SIG not in list(iter_blob_strings(heap))

    def test_short_runs_are_skipped(self) -> None:
        heap = b"\x00" + _ser_string("System.String")
        assert list(iter_blob_strings(heap)) == []


class TestDropContained:
    """Trying every offset as a length prefix means the tail of a real
    signature parses as a signature too. Reporting those as separate hooks
    would inflate the count and, worse, make a truncated pattern look like a
    plugin feature that broke."""

    def test_a_tail_of_another_signature_is_dropped(self) -> None:
        whole = "E8 ?? ?? ?? ?? 0F B6 0D ?? ?? ?? ?? B8"
        tail = "?? ?? ?? ?? 0F B6 0D ?? ?? ?? ??"
        assert drop_contained([tail, whole]) == [whole]

    def test_unrelated_signatures_all_survive(self) -> None:
        first = "E8 ?? ?? ?? ?? 0F B6 53 6C"
        second = "E8 ?? ?? ?? ?? 84 C0 75 03 88 47 3F"
        assert drop_contained([first, second]) == [first, second]

    def test_output_is_sorted(self) -> None:
        assert drop_contained(["FF 00 11 22 33 44 55 66",
                               "00 11 22 33 44 55 66 77"])[0].startswith("00")


@pytest.mark.skipif(not PLUGIN.exists(), reason=f"plugin not built at {PLUGIN}")
class TestAgainstOurOwnPlugin:
    """The end-to-end path only exists in a real assembly: PE -> CLI header ->
    metadata root -> #US. Our plugin is the control - it works on the Korean
    client, so its signatures have to come out."""

    def test_both_heaps_are_found_and_have_strings(self) -> None:
        heaps = metadata_heaps(PLUGIN)
        assert len(list(iter_us_blobs(heaps["#US"]))) > 100
        assert heaps["#Blob"]

    def test_signatures_come_out(self) -> None:
        signatures = extract_signatures(PLUGIN)
        assert signatures, "no signatures in a plugin known to scan for them"
        assert all(is_signature(s) for s in signatures)

    def test_results_are_deduplicated_and_ordered(self) -> None:
        signatures = extract_signatures(PLUGIN)
        assert len(signatures) == len(set(signatures))
        assert signatures == sorted(signatures)
