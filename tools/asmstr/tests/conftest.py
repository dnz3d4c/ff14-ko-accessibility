import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2]
# `sig-probe` has a hyphen, so it is a directory on the path, not an import.
sys.path.insert(0, str(TOOLS / "asmstr"))
sys.path.insert(0, str(TOOLS / "sig-probe"))
