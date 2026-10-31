import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent
backend_dir = repo_root / "backend"

for p in (str(backend_dir), str(repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)
