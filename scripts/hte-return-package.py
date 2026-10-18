#!/usr/bin/env python3
"""Create one private return ZIP after saving instrument logs/raw files locally."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hte.transfer import return_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="local_data")
    parser.add_argument("--runs", nargs="+", default=["output"], help="Run folders; defaults to all output, including practice")
    parser.add_argument("--output", default="transfer/hte-results.zip")
    args = parser.parse_args()
    try:
        report = return_package(ROOT, args.data, args.runs, args.output)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Packaging stopped: {error}\n")
    print("PRIVATE RETURN PACKAGE:", args.output)
    print(f"Saved {len(report['files'])} files with SHA-256 hashes; no API call or robot operation.")
    for name, present in report["external_records_present"].items():
        print(f"{name}: {'included' if present else 'NOT supplied - copy into local_data before the final handoff'}")


if __name__ == "__main__":
    main()
