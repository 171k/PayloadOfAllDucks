"""Enable ``python3 -m poad``."""

from __future__ import annotations

import sys

from poad.cli import main

if __name__ == "__main__":
    sys.exit(main())
