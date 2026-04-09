import sys
from pathlib import Path

# Add the references directory to sys.path so `import statusline` works
REFERENCES_DIR = Path(__file__).resolve().parent.parent / "skills" / "custom-status-line" / "references"
sys.path.insert(0, str(REFERENCES_DIR))
