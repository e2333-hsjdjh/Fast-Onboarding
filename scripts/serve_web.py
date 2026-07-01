"""Compatibility wrapper for serving the Web UI."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (SRC, ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from fast_onboarding.cli.web import main


if __name__ == "__main__":
    raise SystemExit(main())
