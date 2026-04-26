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
import shutil
import sys
import time

import periscopic as p


#--UI Headers--------------------------------------------------------------------------

BLUE = "\033[94m"
LIGHT_BLUE = "\033[38;5;117m"
WHITE = "\033[97m"
DIM_BLUE = "\033[34m"
DIM_GREY = "\033[38;5;240m"
RESET = "\033[0m"

MIN_BOX_WIDTH = 70
MAX_BOX_WIDTH = 120

BANNER = [
    " ____   ____  ____   ___   ____   ___    ___   ____  ____   ___ ",
    "|  _ \\ | ___||  _ \\ |_ _| / ___| / __|  / _ \\ |  _ \\|_  _| / __|",
    "| |_) || __| | |_) | | |  \\___ \\| |    | | | || |_) | | | | |   ",
    "|  __/ |___||  _ <  | |   ___) || |__  | |_| ||  __/  | | | |__ ",
    "|_|         |_| \\_\\|___| |____/  \\___|  \\___/ |_|    |___| \\___|",
]

MOTIF = [
    "    [A]- - - - - -[B]",
    "      \\   . - .   /  ",
    "       \\ ( MPC ) /   ",
    "        \\ `- -' /    ",
    "         \\  |  /     ",
    "          \\ | /      ",
    "           [C]       ",
]


def _visible_len(s):
    out, i = 0, 0
    while i < len(s):
        if s[i] == "\033":
            while i < len(s) and s[i] != "m":
                i += 1
            i += 1
        else:
            out += 1
            i += 1
    return out


def _box_line(content, border, width):
    pad = width - 2 - _visible_len(content)
    if pad < 0:
        pad = 0
    return f"{border}│{RESET if border else ''}{content}{' ' * pad}{border}│{RESET if border else ''}"


def _center(content, width):
    pad = width - 2 - _visible_len(content)
    left = pad // 2
    right = pad - left
    return f"{' ' * left}{content}{' ' * right}"


def _print_welcome():
    use_color = sys.stdout.isatty()
    border = BLUE if use_color else ""
    accent = WHITE if use_color else ""
    dim = DIM_BLUE if use_color else ""
    reset = RESET if use_color else ""

    term_width = shutil.get_terminal_size((80, 24)).columns
    width = max(MIN_BOX_WIDTH, min(MAX_BOX_WIDTH, term_width - 2))

    top = f"{border}╭{'─' * (width - 2)}╮{reset}"
    bottom = f"{border}╰{'─' * (width - 2)}╯{reset}"

    print(top)
    print(_box_line("", border, width))
    for line in BANNER:
        colored = f"{accent}{line}{reset}"
        print(_box_line(_center(colored, width), border, width))
    print(_box_line("", border, width))
    for line in MOTIF:
        print(_box_line(_center(line, width), border, width))
    print(_box_line("", border, width))
    print(_box_line(
        _center("Privacy-preserving SQL query transformation", width),
        border, width,
    ))
    print(_box_line(
        _center(f"v{p.__version__}  •  type /help or /quit", width),
        border, width,
    ))
    print(_box_line("", border, width))
    print(bottom)

    print()
    print(f"  ? for shortcuts{reset}")
    print()
    grey = DIM_GREY if use_color else ""
    print(f"{grey}{'─' * term_width}{reset}")
    print()


def _repl():
    _print_welcome()
    last_interrupt = 0.0
    while True:
        try:
            line = input("periscopic> ")
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
        _repl()
        return

    handlers = {
        "orq": _cmd_orq,
        "shrinkwrap": _cmd_shrinkwrap,
        "periscopic": _cmd_periscopic,
        "transform": _cmd_transform,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
