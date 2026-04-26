"""
periscopic CLI — command-line interface to the Periscopic pipeline.

Usage:
    python -m periscopic <command> [options]
    periscopic <command> [options]        (after pip install)

Commands:
    orq         Sort SELECT columns alphabetically
    shrinkwrap  Apply structural padding to a SQL query
    periscopic  Compute DP join order from a table catalog
    transform   Run the full three-stage pipeline
"""

import argparse
import json
import sys

import periscopic as p


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


def _cmd_periscopic(args):
    catalog = [tuple(pair) for pair in json.loads(args.catalog)]
    result = p.periscopic(args.tables, catalog, epsilon=args.epsilon)
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
        prog="periscopic",
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

    # periscopic
    dp = sub.add_parser("periscopic", help="Compute DP join order")
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
        parser.print_help()
        sys.exit(1)

    handlers = {
        "orq": _cmd_orq,
        "shrinkwrap": _cmd_shrinkwrap,
        "periscopic": _cmd_periscopic,
        "transform": _cmd_transform,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
