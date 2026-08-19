"""Resolve Dalamud-style byte signatures against a game binary, offline.

Why this exists: the plugin ships a hardcoded Korean signature for
`AtkResNode::IsVisible` (`Compat/NodeVisibilityCompat.cs` on the `kr-port`
branch). A signature is only worth
shipping if someone checked that it matches exactly once, and the game does not
have to be running to check that - the bytes are in `ffxiv_dx11.exe`.

Two modes:

  probe    is this signature present, how often, and where does it point
  verify   do our resolutions agree with the ones the real game process produced
           (`%APPDATA%\\XIVLauncherKR\\addon\\Hooks\\<v>\\cachedSigs\\cs.json`)

The rules follow Dalamud's `SigScanner`: `??` is one unknown byte, and a match
that starts on `E8`/`E9` resolves to the target of that relative call/jump
instead of to the match itself.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

# Signatures whose first byte is one of these are call/jump sites: Dalamud
# resolves them to the callee, not to the instruction.
_RELATIVE_OPCODES = (0xE8, 0xE9)


def split_directive(signature: str) -> tuple[str, int | None]:
    """Separate ClientStructs' trailing "+relfollow[n]" from the byte pattern.

    The directive means the resolved address is what the 4-byte relative operand
    at byte n of the match points at - how ClientStructs reaches a static object
    through a rip-relative `lea`/`mov` instead of through a call.
    """
    marker = "+relfollow["
    if marker not in signature:
        return signature, None
    head, _, tail = signature.partition(marker)
    offset, closed, rest = tail.partition("]")
    if not closed or rest.strip():
        raise ValueError(f"malformed relfollow directive: {signature!r}")
    return head, int(offset)


def parse_signature(signature: str) -> tuple[bytes, bytes]:
    """Split a signature string into bytes and a mask (0xFF = must match)."""
    pattern, mask = bytearray(), bytearray()
    for token in signature.split():
        if token in ("?", "??"):
            pattern.append(0)
            mask.append(0x00)
            continue
        try:
            pattern.append(int(token, 16))
        except ValueError:
            raise ValueError(f"not a signature token: {token!r}") from None
        mask.append(0xFF)
    if not pattern:
        raise ValueError("empty signature")
    return bytes(pattern), bytes(mask)


def _longest_fixed_run(mask: bytes) -> tuple[int, int]:
    """Start and length of the longest run of fixed bytes, for use as an anchor."""
    best_start = best_len = run_start = run_len = 0
    for i, byte in enumerate(mask):
        if byte:
            run_start = i if run_len == 0 else run_start
            run_len += 1
            if run_len > best_len:
                best_start, best_len = run_start, run_len
        else:
            run_len = 0
    return best_start, best_len


def find_matches(text: bytes, signature: str, limit: int | None = None) -> list[int]:
    """Every offset in `text` where the signature matches, in order.

    Overlapping matches all count. A signature made only of wildcards would match
    everywhere, so at least one fixed byte is required.
    """
    pattern, mask = parse_signature(split_directive(signature)[0])
    anchor_at, anchor_len = _longest_fixed_run(mask)
    if anchor_len == 0:
        raise ValueError("signature has no fixed byte to search for")
    anchor = pattern[anchor_at:anchor_at + anchor_len]

    matches: list[int] = []
    position = 0
    while limit is None or len(matches) < limit:
        found = text.find(anchor, position)
        if found < 0:
            break
        position = found + 1
        start = found - anchor_at
        if start < 0 or start + len(pattern) > len(text):
            continue
        window = text[start:start + len(pattern)]
        if all(not m or window[i] == pattern[i] for i, m in enumerate(mask)):
            matches.append(start)
    return matches


def resolve_target(text: bytes, text_rva: int, offset: int,
                   rel_offset: int | None = None) -> int:
    """RVA a match points at: the callee for E8/E9, else the match itself.

    With `rel_offset` set (a "+relfollow[n]" signature) the operand at that byte
    decides instead, relative to the instruction that follows it.
    """
    if rel_offset is not None:
        relative = struct.unpack_from("<i", text, offset + rel_offset)[0]
        return text_rva + offset + rel_offset + 4 + relative
    if text[offset] in _RELATIVE_OPCODES:
        relative = struct.unpack_from("<i", text, offset + 1)[0]
        return text_rva + offset + 5 + relative
    return text_rva + offset


@dataclass(frozen=True)
class Match:
    """One signature hit: where it sits and what it points at, both as RVAs."""

    site: int
    target: int

    @classmethod
    def collect(cls, text: bytes, text_rva: int, signature: str,
                limit: int | None = None) -> list[Match]:
        rel_offset = split_directive(signature)[1]
        return [cls(site=text_rva + offset,
                    target=resolve_target(text, text_rva, offset, rel_offset))
                for offset in find_matches(text, signature, limit)]

    @staticmethod
    def target_counts(matches: list[Match]) -> dict[int, int]:
        """How many sites reach each target, most-referenced first."""
        counts: dict[int, int] = {}
        for match in matches:
            counts[match.target] = counts.get(match.target, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def load_text_section(path: Path) -> tuple[bytes, int]:
    """Raw bytes of the .text section and the RVA it is mapped at."""
    data = path.read_bytes()
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError(f"{path} is not an executable")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if len(data) < pe + 24 or data[pe:pe + 4] != b"PE\0\0":
        raise ValueError(f"{path} has no PE header")
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    sections = pe + 24 + optional_size
    for index in range(section_count):
        entry = sections + index * 40
        name = data[entry:entry + 8].rstrip(b"\0")
        virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<III", data, entry + 12)
        if name == b".text":
            return data[raw_pointer:raw_pointer + raw_size], virtual_address
    raise ValueError(f"{path} has no .text section")


def _probe(text: bytes, text_rva: int, signature: str, expect_unique: bool) -> int:
    matches = Match.collect(text, text_rva, signature)
    counts = Match.target_counts(matches)
    print(f"signature: {signature}")
    print(f"  matches: {len(matches)}   distinct targets: {len(counts)}")
    for target, hits in list(counts.items())[:10]:
        print(f"    -> 0x{target:X}   from {hits} site(s)")
    if expect_unique and len(matches) != 1:
        print(f"  NOT UNIQUE: expected exactly one match, got {len(matches)}")
        return 1
    return 0


def _verify(text: bytes, text_rva: int, cache_path: Path, sample: int) -> int:
    """Check our resolutions against the ones the running game produced."""
    cache = json.loads(cache_path.read_text(encoding="utf-8-sig"))
    cache = cache.get("Cache", cache)
    signatures = sorted(cache)[:sample] if sample else sorted(cache)
    agree = disagree = 0
    skipped: list[str] = []
    for signature in signatures:
        try:
            matches = Match.collect(text, text_rva, signature, limit=8)
        except ValueError as unusable:
            # Not silently: a signature this tool cannot read is a hole in the
            # verification, and the whole point is to know where the holes are.
            skipped.append(f"{signature[:50]} ({unusable})")
            continue
        if cache[signature] in {m.target for m in matches}:
            agree += 1
        else:
            disagree += 1
            if disagree <= 5:
                print(f"  disagree: {signature[:60]!r} "
                      f"cached=0x{cache[signature]:X} matches={len(matches)}")
    print(f"agree {agree} / {agree + disagree}   skipped {len(skipped)}")
    for entry in skipped[:5]:
        print(f"  skipped: {entry}")
    return 0 if disagree == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, help="game executable")
    parser.add_argument("signature", nargs="?", help="Dalamud-style byte signature")
    parser.add_argument("--expect-unique", action="store_true",
                        help="fail unless the signature matches exactly once")
    parser.add_argument("--verify-cache", type=Path, metavar="CS_JSON",
                        help="compare against Dalamud's cached resolutions")
    parser.add_argument("--sample", type=int, default=0,
                        help="only the first N cached signatures (0 = all)")
    args = parser.parse_args(argv)

    text, text_rva = load_text_section(args.binary)
    print(f"{args.binary.name}: .text {len(text):,} bytes at RVA 0x{text_rva:X}")

    if args.verify_cache:
        return _verify(text, text_rva, args.verify_cache, args.sample)
    if not args.signature:
        parser.error("give a signature or --verify-cache")
    return _probe(text, text_rva, args.signature, args.expect_unique)


if __name__ == "__main__":
    sys.exit(main())
