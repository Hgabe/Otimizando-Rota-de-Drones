"""Executa a mesma arena visual definida em `arena.py`."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arena import main as run_arena


def main() -> None:
    """Executa a arena legacy, mantendo o mesmo comportamento de `arena.py`."""
    run_arena()


if __name__ == "__main__":
    main()
