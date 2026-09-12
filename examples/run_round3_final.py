"""Run the authorized staged study once, reusing a single real MATLAB Engine."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.matlab_tools import MatlabTools
from tools.round3_studies import run_round3_final


def main():
    matlab = MatlabTools()
    class Shared:
        def __getattr__(self,name):
            return getattr(matlab,name)
        def close(self):
            pass
    try:
        run_round3_final(matlab_factory=Shared)
    finally:
        matlab.close()


if __name__ == '__main__':
    main()
