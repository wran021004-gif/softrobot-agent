"""Native MuJoCo saved scene entry point."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.native_replay import main
if __name__ == '__main__':
    main()
