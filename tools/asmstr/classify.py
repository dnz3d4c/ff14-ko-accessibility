"""Judge a plugin's signatures against a game binary it was not built for.

A Dalamud plugin written for the global client is a bet that the Korean build
compiled the same functions to the same bytes. This settles the bet per
signature, offline:

  UNIQUE     one match - the plugin finds what it is looking for
  NOT FOUND  no match - `ScanText` throws and that hook is dead
  AMBIGUOUS  several - `ScanText` takes the first, which may be the wrong one

Scanning is `sig-probe`'s job (already checked against 2,203 resolutions the
running game produced), extraction is `extract_sigs`'s. This only pairs them
and counts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from extract_sigs import extract_signatures

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "sig-probe"))
from sig_probe import Match, load_text_section  # noqa: E402


def verdict(match_count: int) -> str:
    return "UNIQUE" if match_count == 1 else "NOT FOUND" if not match_count \
        else "AMBIGUOUS"


def report(name: str, signatures: list[str], text: bytes, text_rva: int) -> None:
    """One source's signatures, verdict each, then the tally."""
    print(f"\n=== {name}: {len(signatures)} signature(s) ===")
    counts = {"UNIQUE": 0, "NOT FOUND": 0, "AMBIGUOUS": 0}
    for signature in signatures:
        matches = Match.collect(text, text_rva, signature)
        label = verdict(len(matches))
        counts[label] += 1
        targets = ", ".join(f"0x{m.target:X}" for m in matches[:4])
        print(f"  {label:<10} {signature}")
        if targets:
            print(f"             -> {targets}"
                  f"{' ...' if len(matches) > 4 else ''}")
    print(f"  totals: UNIQUE {counts['UNIQUE']}   "
          f"NOT FOUND {counts['NOT FOUND']}   AMBIGUOUS {counts['AMBIGUOUS']}")


def cache_sample(path: Path, count: int) -> list[str]:
    """Signatures Dalamud already resolved in the live game - the control.

    These have to come back UNIQUE. If they do not, the fault is in this tool,
    not in the plugin under test.
    """
    cache = json.loads(path.read_text(encoding="utf-8-sig"))
    cache = cache.get("Cache", cache)
    return [s for s in sorted(cache) if "+relfollow[" not in s][:count]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, help="game executable")
    parser.add_argument("assemblies", nargs="*", type=Path,
                        help=".NET plugin assemblies to judge")
    parser.add_argument("--cache", type=Path, metavar="CS_JSON",
                        help="also run Dalamud's cached signatures as a control")
    parser.add_argument("--sample", type=int, default=20,
                        help="how many cached signatures to use")
    args = parser.parse_args(argv)

    text, text_rva = load_text_section(args.binary)
    print(f"{args.binary.name}: .text {len(text):,} bytes at RVA 0x{text_rva:X}")

    for assembly in args.assemblies:
        report(assembly.name, extract_signatures(assembly), text, text_rva)
    if args.cache:
        report(f"control: {args.cache.name} (first {args.sample})",
               cache_sample(args.cache, args.sample), text, text_rva)
    return 0


if __name__ == "__main__":
    sys.exit(main())
