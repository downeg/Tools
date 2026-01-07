#!/usr/bin/env python3
"""
Parse plain-text Nmap output (e.g. `nmap -Pn -sC -sV -p ...`) and emit a CSV with:
Enum, Port, Protocol, State, Service, Version, Hypothesis, Notes, Loot

Defaults (only when invoked with no CLI args):
- Input:  ./enum/nmap_sv_sc.nmap
- Output: ./enum/surface_map.csv

If output CSV already exists:
- Prompt: overwrite? "y/n/o"
  - y: overwrite
  - n: cancel
  - o: prompt for alternative filename, saved under ./enum/

After writing the CSV, attempts to open it with `Tablecruncher` (must be in PATH),
and fully detaches so the shell prompt returns immediately.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

DEFAULT_IN = Path("./enum/nmap_sv_sc.nmap")
DEFAULT_OUT = Path("./enum/surface_map.csv")
ENUM_DIR = Path("./enum")

PORT_LINE_RE = re.compile(
    r"^(?P<port>\d+)/(?:\s*)?(?P<proto>tcp|udp)\s+"
    r"(?P<state>\S+)\s+"
    r"(?P<service>\S+)"
    r"(?:\s+(?P<version>.*\S))?\s*$",
    re.IGNORECASE,
)

CSV_FIELDS = [
    "Enum",
    "Port",
    "Protocol",
    "State",
    "Service",
    "Version",
    "Hypothesis",
    "Notes",
    "Loot",
]


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
                "Enum": "N",
                "Port": port,
                "Protocol": proto,
                "State": state,
                "Service": service,
                "Version": version,
                "Hypothesis": "",
                "Notes": "",
                "Loot": "",
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
                start_new_session=True,
                close_fds=True,
            )
    except FileNotFoundError:
        print("Warning: 'Tablecruncher' not found in PATH; CSV written but not opened.", file=sys.stderr)
    except Exception as e:
        print(f"Warning: failed to launch Tablecruncher: {e}", file=sys.stderr)


def _prompt_overwrite_choice(path: Path) -> str:
    while True:
        choice = input(f"Output file exists: {path}\nOverwrite? (y/n/o): ").strip().lower()
        if choice in {"y", "n", "o"}:
            return choice
        print("Invalid choice. Enter 'y' (overwrite), 'n' (cancel), or 'o' (other name).")


def _prompt_alt_filename(enum_dir: Path) -> Path:
    while True:
        name = input("Enter alternative filename (will be saved under ./enum/): ").strip()

        # Basic sanity: non-empty, no path traversal.
        if not name:
            print("Filename cannot be empty.")
            continue

        p = Path(name)
        if p.is_absolute() or ".." in p.parts or len(p.parts) != 1:
            print("Invalid filename. Provide a simple filename only (no directories).")
            continue

        if not name.lower().endswith(".csv"):
            name += ".csv"

        out = enum_dir / name
        return out


def resolve_output_path(out_path: Path) -> Optional[Path]:
    """
    Returns:
      - Path to write to, or
      - None if user cancels.
    """
    if not out_path.exists():
        return out_path

    choice = _prompt_overwrite_choice(out_path)
    if choice == "y":
        return out_path
    if choice == "n":
        return None

    # choice == "o"
    ENUM_DIR.mkdir(parents=True, exist_ok=True)
    alt = _prompt_alt_filename(ENUM_DIR)

    # If alternative also exists, loop the same logic on that path.
    return resolve_output_path(alt)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Convert plain-text Nmap output to CSV (Enum..Loot)."
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
        candidate_out: Path = args.output
    else:
        candidate_out = DEFAULT_OUT if no_cli_args else in_path.with_suffix(in_path.suffix + ".csv")

    if not in_path.is_file():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    # Ensure candidate output directory exists (even before prompting for overwrite).
    candidate_out.parent.mkdir(parents=True, exist_ok=True)

    out_path = resolve_output_path(candidate_out)
    if out_path is None:
        print("Cancelled; output file not written.", file=sys.stderr)
        return 1

    # Ensure final output directory exists (in case user chose alternative name).
    out_path.parent.mkdir(parents=True, exist_ok=True)

    text_lines = in_path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = parse_nmap_lines(text_lines, only_open=not args.include_non_open)

    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)

    open_with_tablecruncher(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
