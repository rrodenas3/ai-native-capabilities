#!/usr/bin/env python3
"""Run golden principles checks for all capabilities."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.harness.golden_principles import main

if __name__ == "__main__":
    sys.exit(main())
