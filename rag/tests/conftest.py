from __future__ import annotations

import sys
from pathlib import Path

RAG_SRC = Path(__file__).parents[1] / "src"
sys.path.insert(0, str(RAG_SRC))
