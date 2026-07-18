import sys
from pathlib import Path

# Add the backend directory to sys.path so tests can import from app
sys.path.insert(0, str(Path(__file__).parent.parent))
