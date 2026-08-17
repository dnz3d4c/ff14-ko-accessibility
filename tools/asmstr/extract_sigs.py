"""Pull byte signatures out of a .NET plugin assembly, without running it.

Why this exists: a Dalamud plugin finds game functions by scanning for byte
patterns, and those patterns are written for one client build. Before putting a
foreign plugin (vnavmesh) on the Korean client we want to know which of its
signatures still resolve - and that question is answerable offline, because the
patterns are plain string literals in the assembly and the bytes they look for
are in `ffxiv_dx11.exe`.

The literals live in two places, and both matter. Code that calls
`ScanText("...")` puts the pattern in the `#US` heap as UTF-16; code that
declares `[Signature("...")]` puts it in `#Blob` as UTF-8, because attribute
arguments are serialised, not interned. vnavmesh uses both, so reading only
`#US` would have reported half its hooks and called the rest clean.

We walk the metadata by hand - PE header, CLI header, metadata root, stream
table (ECMA-335 II.24.2) - because `System.Reflection.Metadata` is a .NET
library and this is Python.

Output is only the literals that look like an AOB pattern. That filter is a
guess by construction: a signature is just a string until something scans with
it, so `classify.py` is what turns this list into a verdict.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Iterator

# Below this, "48 89 5C 24" style text shows up in ordinary prose and hex dumps
# often enough to drown the real hits. Dalamud signatures are far longer.
_MIN_TOKENS = 8
_WILDCARDS = ("?", "??")
_HEX_DIGITS = set("0123456789abcdefABCDEF")

# Shortest string `_MIN_TOKENS` can produce ("?? " * 8 minus the last space).
_MIN_CHARS = _MIN_TOKENS * 3 - 1
_PRINTABLE = frozenset(range(0x20, 0x7F))


def is_signature(text: str) -> bool:
    """Does this literal read as a Dalamud AOB pattern?

    Dalamud's SigScanner splits on spaces and accepts a two-digit hex byte or
    a `?`/`??` wildcard, nothing else. An all-wildcard pattern is rejected too:
    it matches everywhere, so nobody wrote it as a signature.
    """
    tokens = text.split()
    if len(tokens) < _MIN_TOKENS:
        return False
    fixed = 0
    for token in tokens:
        if token in _WILDCARDS:
            continue
        if len(token) != 2 or not set(token) <= _HEX_DIGITS:
            return False
        fixed += 1
    return fixed > 0


def read_compressed_uint(data: bytes, offset: int) -> tuple[int, int]:
    """Decode ECMA-335 II.23.2 compressed integer. Returns (value, size)."""
    first = data[offset]
    if first & 0x80 == 0:
        return first, 1
    if first & 0xC0 == 0x80:
        return ((first & 0x3F) << 8) | data[offset + 1], 2
    return struct.unpack_from(">I", data, offset)[0] & 0x1FFFFFFF, 4


def iter_us_blobs(heap: bytes) -> Iterator[str]:
    """Every string in a `#US` heap, in heap order.

    Entries are length-prefixed UTF-16LE with one trailing flag byte. The heap
    starts with a single zero byte (the empty string) and can end in padding,
    so a zero length means "skip", not "stop".
    """
    position = 0
    while position < len(heap):
        try:
            length, header = read_compressed_uint(heap, position)
        except (IndexError, struct.error):
            return
        position += header
        if length == 0:
            continue
        body = heap[position:position + length]
        position += length
        # A short read means the heap was truncated; a body without the flag
        # byte or with an odd number of UTF-16 bytes is not a string entry.
        if len(body) != length or length % 2 == 0:
            continue
        yield body[:-1].decode("utf-16-le", errors="replace")


def iter_blob_strings(heap: bytes) -> Iterator[str]:
    """Printable ASCII SerStrings anywhere in a `#Blob` heap.

    Attribute blobs only make sense against the constructor signature they were
    written for, and reading the metadata tables to recover those would be a
    disassembler. Instead every offset is tried as a length prefix and kept only
    if the whole run it claims is printable - a wrong guess almost always lands
    on a non-printable byte, and `is_signature` rejects whatever slips past.
    """
    for position in range(len(heap)):
        try:
            length, header = read_compressed_uint(heap, position)
        except (IndexError, struct.error):
            continue
        if length < _MIN_CHARS:
            continue
        body = heap[position + header:position + header + length]
        if len(body) != length or not all(byte in _PRINTABLE for byte in body):
            continue
        yield body.decode("ascii")


def _rva_to_offset(data: bytes, pe: int, rva: int) -> int:
    """File offset of an RVA, via the section table."""
    section_count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    sections = pe + 24 + optional_size
    for index in range(section_count):
        entry = sections + index * 40
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from(
            "<IIII", data, entry + 8)
        if virtual_address <= rva < virtual_address + max(virtual_size, raw_size):
            return raw_pointer + (rva - virtual_address)
    raise ValueError(f"RVA 0x{rva:X} is in no section")


def metadata_heaps(path: Path) -> dict[str, bytes]:
    """Every metadata stream in the assembly, by name (`#US`, `#Blob`, ...).

    A stream that is not there is simply absent from the dict: an assembly with
    no string literals has no `#US`, and that is not an error.
    """
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError(f"{path} is not a PE file")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError(f"{path} has no PE header")

    magic = struct.unpack_from("<H", data, pe + 24)[0]
    directories = pe + 24 + (112 if magic == 0x20B else 96)
    cli_rva = struct.unpack_from("<I", data, directories + 14 * 8)[0]
    if cli_rva == 0:
        raise ValueError(f"{path} is not a managed assembly")

    cli = _rva_to_offset(data, pe, cli_rva)
    metadata_rva = struct.unpack_from("<I", data, cli + 8)[0]
    root = _rva_to_offset(data, pe, metadata_rva)
    if data[root:root + 4] != b"BSJB":
        raise ValueError(f"{path} has no metadata root")

    version_length = struct.unpack_from("<I", data, root + 12)[0]
    # The version string is padded to a 4-byte boundary before Flags/Streams.
    cursor = root + 16 + (version_length + 3 & ~3)
    stream_count = struct.unpack_from("<H", data, cursor + 2)[0]
    cursor += 4
    heaps: dict[str, bytes] = {}
    for _ in range(stream_count):
        offset, size = struct.unpack_from("<II", data, cursor)
        cursor += 8
        end = data.index(b"\0", cursor)
        name = data[cursor:end].decode("ascii")
        cursor += (end - cursor) + 4 & ~3
        heaps[name] = data[root + offset:root + offset + size]
    return heaps


def drop_contained(signatures: list[str]) -> list[str]:
    """Remove signatures that are a substring of another one.

    The `#Blob` scan tries every offset, so the tail of a real pattern parses
    as a pattern in its own right. The cost of this rule: an assembly that
    genuinely scans with two patterns where one contains the other loses the
    shorter one. Nothing in the assembly distinguishes those two cases, and
    over-reporting hooks is the more misleading of the two errors.
    """
    unique = sorted(set(signatures))
    return [candidate for candidate in unique
            if not any(candidate != other and candidate in other
                       for other in unique)]


def extract_signatures(path: Path) -> list[str]:
    """Sorted, deduplicated AOB signature literals from both heaps."""
    heaps = metadata_heaps(path)
    found = set(iter_us_blobs(heaps.get("#US", b"")))
    found |= set(iter_blob_strings(heaps.get("#Blob", b"")))
    return drop_contained([text.strip() for text in found if is_signature(text)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assembly", type=Path, help=".NET assembly (.dll)")
    parser.add_argument("--json", action="store_true", help="emit a JSON array")
    args = parser.parse_args(argv)

    signatures = extract_signatures(args.assembly)
    if args.json:
        print(json.dumps(signatures, indent=2))
    else:
        for signature in signatures:
            print(signature)
    return 0


if __name__ == "__main__":
    sys.exit(main())
