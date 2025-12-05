"""Simple COM helper script for quick experiments.

Usage example:
    python src/com_tool.py --prog-id "Your.ProgID" --method "Ping" --args "hello" "world"
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Sequence

import pythoncom
import win32com.client
from dotenv import load_dotenv


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call a method on a COM component.")
    parser.add_argument(
        "--prog-id",
        dest="prog_id",
        default=os.getenv("COM_PROG_ID"),
        help="ProgID or CLSID of the COM component (env: COM_PROG_ID).",
    )
    parser.add_argument(
        "--method",
        required=False,
        help="Method name to invoke on the COM object.",
    )
    parser.add_argument(
        "--args",
        nargs="*",
        default=[],
        help="Positional arguments passed to the COM method.",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        default=os.getenv("COM_VISIBLE") in {"1", "true", "True"},
        help="If the COM object supports a Visible property, set it to True.",
    )
    return parser.parse_args(argv)


def create_com_instance(prog_id: str):
    # CoInitialize/CoUninitialize must be paired; caller handles teardown.
    return win32com.client.Dispatch(prog_id)


def invoke_method(target: Any, method: str | None, args: Sequence[str]) -> Any:
    if not method:
        return None
    if not hasattr(target, method):
        raise AttributeError(f"COM object has no method '{method}'")
    callable_attr = getattr(target, method)
    return callable_attr(*args)


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()
    args = parse_args(argv or sys.argv[1:])

    if not args.prog_id:
        print("Error: --prog-id is required (or set COM_PROG_ID in .env).", file=sys.stderr)
        return 2

    pythoncom.CoInitialize()
    try:
        com_obj = create_com_instance(args.prog_id)
        if args.visible and hasattr(com_obj, "Visible"):
            try:
                com_obj.Visible = True
            except Exception:
                pass  # Some COM servers expose Visible but reject writes.

        result = invoke_method(com_obj, args.method, args.args)
        if args.method:
            print(f"[OK] {args.prog_id}.{args.method} -> {result!r}")
        else:
            print(f"[OK] Connected to {args.prog_id}, no method invoked.")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    sys.exit(main())
