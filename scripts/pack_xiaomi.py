#!/usr/bin/env python3
"""Use an explicitly selected external packer, then independently validate n67 output."""
import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from n67_validation import ValidationError, require, validate_package, validate_project


def run_packer(executable, project, output, timeout):
    command = [str(executable), "pack", str(project), str(output), "n67"]
    # No shell, download, PATH lookup, or implicit tool selection.
    process = subprocess.Popen(command, cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, errors="replace", start_new_session=os.name == "posix")
    def stop_owned_processes():
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass
        process.communicate()

    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        stop_owned_processes()
        raise ValidationError(f"External packer exceeded {timeout} seconds and was stopped") from error
    except BaseException:
        stop_owned_processes()
        raise
    if os.name == "posix":
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            pass
        else:
            stop_owned_processes()
            raise ValidationError("External packer left background children; its owned process group was stopped")
    if process.returncode != 0:
        detail = (stderr or stdout).strip()[-2000:]
        raise ValidationError(f"External packer exited {process.returncode}: {detail}")
    return stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--packer", required=True, type=Path,
                        help="Explicit executable/wrapper implementing: pack PROJECT OUTPUT n67")
    parser.add_argument("--profile", choices=["n67"], default="n67")
    parser.add_argument("--timeout", type=int, default=120, help="External process deadline, 1..300 seconds")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output only after verification")
    args = parser.parse_args()
    try:
        project, executable, output = args.project.resolve(), args.packer.resolve(), args.output.resolve()
        require(1 <= args.timeout <= 300, "--timeout must be in 1..300 seconds")
        require(executable.is_file() and os.access(executable, os.X_OK),
                "--packer must identify an existing executable; no tool is downloaded or chosen automatically")
        require(not output.is_relative_to(project), "--output must be outside the input project")
        require(output.suffix.lower() == ".bin", "--output must end in .bin")
        require(not output.exists() or args.overwrite, "Output already exists; use --overwrite to replace after validation")
        _, _, source_report = validate_project(project, args.profile)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".n67-pack-", dir=output.parent) as directory:
            staged = Path(directory) / "verified.bin"
            run_packer(executable, project, staged, args.timeout)
            require(staged.is_file() and not staged.is_symlink(),
                    "External packer must produce a regular package file, not a symlink")
            package_report = validate_package(staged, project)
            require(not output.exists() or args.overwrite, "Output appeared while packing; refusing to overwrite")
            if args.overwrite:
                staged.replace(output)
            else:
                # Hard-link creation fails atomically if a target appears between
                # the existence check and publication; the temporary link is then removed.
                os.link(staged, output)
        print(json.dumps({"result": "PASS", "output": str(output), "project": source_report,
                          "package": package_report}, ensure_ascii=False, indent=2))
        return 0
    except (ValidationError, OSError, ValueError, TypeError, KeyError) as error:
        print(f"Packing failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
