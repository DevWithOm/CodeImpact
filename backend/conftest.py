import os
import sys
from pathlib import Path

# Ensure both backend root and repository root are on sys.path
backend_dir = Path(__file__).resolve().parent
repo_root = backend_dir.parent

for p in (str(backend_dir), str(repo_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Align working directory to repo_root so relative fixture paths (fixtures/... and backend/tests/...) resolve consistently
os.chdir(repo_root)
