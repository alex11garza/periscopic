"""
PrivQ CLI — command-line interface to the PrivQ pipeline.

Usage:
    python -m PrivQ <command> [options]
    PrivQ <command> [options]        (after pip install)

Commands:
    orq         Sort SELECT columns alphabetically
    shrinkwrap  Apply structural padding to a SQL query
    privq-join  Compute DP join order from a table catalog
    transform   Run the full three-stage pipeline
"""

import argparse
import importlib.util
import json
import os
import sys
import time

import PrivQ as p

# UIX/UI imports and helpers
_helpers_dir = os.path.join(os.path.dirname(__file__), "CLI-Helpers")

_ui_path = os.path.join(_helpers_dir, "UI.py")
_spec = importlib.util.spec_from_file_location("privq_ui", _ui_path)
_ui = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ui)
print_welcome = _ui.print_welcome
DIM_GREY = _ui.COLORS["DIM_GREY"]
RESET = _ui.COLORS["RESET"]
COLORS = _ui.COLORS

_server_path = os.path.join(_helpers_dir, "Server.py")
_server_spec = importlib.util.spec_from_file_location("privq_server", _server_path)
_server_mod = importlib.util.module_from_spec(_server_spec)
_server_spec.loader.exec_module(_server_mod)
Server = _server_mod.Server


def _repl():
    print_welcome()
    last_interrupt = 0.0
    while True:
        try:
            line = input("PrivQ> ")
        except EOFError:
            print()
            return
        except KeyboardInterrupt:
            now = time.monotonic()
            if now - last_interrupt < 2.0:
                print()
                return
            last_interrupt = now
            print(f"\n\n{DIM_GREY}(press Ctrl+C again to exit){RESET}\n")
            continue
        last_interrupt = 0.0
        if not line.strip():
            continue
        print(line)



# -- command handlers ----------------------------------------------------------

def _read_sql(args):
    """Return SQL from --sql flag or stdin."""
    if args.sql:
        return args.sql
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    print("error: provide SQL via --sql or pipe to stdin", file=sys.stderr)
    sys.exit(1)


# -- subcommand handlers -----------------------------------------------------

def _cmd_orq(args):
    sql = _read_sql(args)
    print(p.orq(sql))


def _cmd_shrinkwrap(args):
    sql = _read_sql(args)
    print(p.shrinkwrap(sql, padding=True, pad_level=args.pad_level))


def _cmd_privq_join(args):
    catalog = [tuple(pair) for pair in json.loads(args.catalog)]
    result = p.privq_join(args.tables, catalog, epsilon=args.epsilon)
    print(json.dumps(result))


def _cmd_transform(args):
    sql = _read_sql(args)
    catalog = None
    if args.catalog:
        catalog = [tuple(pair) for pair in json.loads(args.catalog)]
    result = p.transform(
        sql,
        catalog=catalog,
        epsilon=args.epsilon,
        padding=not args.no_padding,
        pad_level=args.pad_level,
    )
    print(json.dumps(result, indent=2))


# -- argument parser ----------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="PrivQ",
        description="Privacy-preserving SQL query transformation tool.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {p.__version__}"
    )
    sub = parser.add_subparsers(dest="command")

    # orq
    orq = sub.add_parser("orq", help="Sort SELECT columns alphabetically")
    orq.add_argument("--sql", help="SQL query string (or pipe via stdin)")

    # shrinkwrap
    sw = sub.add_parser("shrinkwrap", help="Apply structural padding")
    sw.add_argument("--sql", help="SQL query string (or pipe via stdin)")
    sw.add_argument(
        "--pad-level", type=int, default=2, choices=[1, 2, 3],
        help="Padding level: 1=comment, 2=structural (default), 3=+dummy JOIN",
    )

    # privq-join
    dp = sub.add_parser("privq-join", help="Compute DP join order")
    dp.add_argument(
        "tables", nargs="+", help="Table names from the FROM/JOIN clause",
    )
    dp.add_argument(
        "--catalog", required=True,
        help='JSON array of [name, rows] pairs, e.g. \'[["users",100],["orders",200]]\'',
    )
    dp.add_argument(
        "--epsilon", type=float, default=0.5, help="Privacy budget (default 0.5)",
    )

    # transform
    tf = sub.add_parser("transform", help="Run the full pipeline")
    tf.add_argument("--sql", help="SQL query string (or pipe via stdin)")
    tf.add_argument(
        "--catalog",
        help='JSON array of [name, rows] pairs (optional)',
    )
    tf.add_argument(
        "--epsilon", type=float, default=0.5, help="Privacy budget (default 0.5)",
    )
    tf.add_argument(
        "--no-padding", action="store_true", help="Skip ShrinkWrap padding",
    )
    tf.add_argument(
        "--pad-level", type=int, default=2, choices=[1, 2, 3],
        help="Padding level: 1=comment, 2=structural (default), 3=+dummy JOIN",
    )

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        _repl()
        return

    handlers = {
        "orq": _cmd_orq,
        "shrinkwrap": _cmd_shrinkwrap,
        "privq-join": _cmd_privq_join,
        "transform": _cmd_transform,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
