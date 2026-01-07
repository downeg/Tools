#!/usr/bin/env python3
"""
Parse plain-text Nmap output (e.g. `nmap -Pn -sC -sV -p ...`) and emit a CSV with:
Port, Protocol, State, Service, Version

Defaults (only when invoked with no CLI args):
- Input:  ./enum/nmap_sv_sc.nmap
- Output: ./enum/surface_map.csv

After writing the CSV, attempts to open it with `Tablecruncher` (must be in PATH).
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

DEFAULT_IN = Path("./enum/nmap_sv_sc.nmap")
DEFAULT_OUT = Path("./enum/surface_map.csv")

PORT_LINE_RE = re.compile(
    r"^(?P<port>\d+)/(?:\s*)?(?P<proto>tcp|udp)\s+"
    r"(?P<state>\S+)\s+"
    r"(?P<service>\S+)"
    r"(?:\s+(?P<version>.*\S))?\s*$",
    re.IGNORECASE,
)


def parse_nmap_lines(lines: Iterable[str], only_open: bool = True) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for raw in lines:
        line = raw.rstrip("\n")

        # Ignore indented script output and empty lines
        if not line or line[:1].isspace():
            continue

        m = PORT_LINE_RE.match(line)
        if not m:
            continue

        port = m.group("port")
        proto = m.group("proto").lower()
        state = m.group("state")
        service = m.group("service")
        version = m.group("version") or ""

        if only_open and not state.lower().startswith("open"):
            continue

        rows.append(
            {
                "Port": port,
                "Protocol": proto,
                "State": state,
                "Service": service,
                "Version": version,
            }
        )

    return rows


def open_with_tablecruncher(csv_path: Path) -> None:
    try:
        # Detach from the controlling terminal so the shell prompt returns immediately.
        with open("/dev/null", "rb") as devnull_in, open("/dev/null", "ab") as devnull_out:
            subprocess.Popen(
                ["Tablecruncher", str(csv_path)],
                stdin=devnull_in,
                stdout=devnull_out,
                stderr=devnull_out,
                start_new_session=True,  # detach from terminal/session
                close_fds=True,
            )
    except FileNotFoundError:
        print("Warning: 'Tablecruncher' not found in PATH; CSV written but not opened.", file=sys.stderr)
    except Exception as e:
        print(f"Warning: failed to launch Tablecruncher: {e}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert plain-text Nmap output to CSV (Port, Protocol, State, Service, Version)."
    )
    ap.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        default=DEFAULT_IN,
        help="Path to a text file containing Nmap output (default: ./enum/nmap_sv_sc.nmap when no args).",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output CSV path.",
    )
    ap.add_argument(
        "--include-non-open",
        action="store_true",
        help="Include ports not in an open* state (default: only open/open|filtered etc.).",
    )

    args = ap.parse_args()

    # "No parameters configured" == invoked with no CLI args besides script name.
    no_cli_args = (len(sys.argv) == 1)

    in_path: Path = args.input_file

    if args.output is not None:
        out_path: Path = args.output
    else:
        out_path = DEFAULT_OUT if no_cli_args else in_path.with_suffix(in_path.suffix + ".csv")

    if not in_path.is_file():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    # Ensure output directory exists.
    out_path.parent.mkdir(parents=True, exist_ok=True)

    text_lines = in_path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = parse_nmap_lines(text_lines, only_open=not args.include_non_open)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Port", "Protocol", "State", "Service", "Version"])
        w.writeheader()
        w.writerows(rows)

    open_with_tablecruncher(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
