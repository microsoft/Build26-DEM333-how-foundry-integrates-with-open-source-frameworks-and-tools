from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONPATH", str(SRC))
    from dem333_common.agui_gateway import main

    main()
