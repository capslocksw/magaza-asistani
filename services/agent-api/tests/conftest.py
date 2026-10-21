"""Makes the shared test helpers importable (pytest runs with --import-mode=importlib)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
