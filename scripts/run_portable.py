"""Run an unchanged legacy entry point with Unicode-safe XML input."""
import argparse
from pathlib import Path
import runpy
import sys
from portable_xml import portable_xml_loading


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('script',choices=['view_trajectory.py','simulate_controls.py','validate_package.py'])
    args,forwarded=p.parse_known_args()
    script=Path(__file__).resolve().parent/args.script
    previous=sys.argv
    try:
        sys.argv=[str(script),*forwarded]
        with portable_xml_loading():runpy.run_path(str(script),run_name='__main__')
    finally:sys.argv=previous


if __name__=='__main__':main()
