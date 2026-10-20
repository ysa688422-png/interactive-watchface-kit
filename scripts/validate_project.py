#!/usr/bin/env python3
"""Validate the supported n67 Lua + native-AOD project without running a packer."""
import argparse
import json
import sys
from pathlib import Path

from n67_validation import ValidationError, validate_package, validate_project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--profile", choices=["n67"], default="n67")
    parser.add_argument("--package", type=Path, help="Also independently verify an existing package")
    args = parser.parse_args()
    try:
        _, _, report = validate_project(args.project, args.profile)
        if args.package:
            report["package"] = validate_package(args.package, args.project)
    except (ValidationError, OSError, ValueError, TypeError, KeyError) as error:
        print(f"Validation failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
