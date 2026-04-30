"""UI header art and welcome banner for the PrivQ CLI."""

import shutil
import sys

import PrivQ as p

COLORS = {
    "BLUE": "\033[94m",
    "LIGHT_BLUE": "\033[38;5;117m",
    "WHITE": "\033[97m",
    "DIM_BLUE": "\033[34m",
    "DIM_GREY": "\033[38;5;240m",
    "RESET": "\033[0m",
}

BOX_DIMENSIONS = {
    "MIN_BOX_WIDTH": 70,
    "MAX_BOX_WIDTH": 120,
}

BANNER = [
    " ____   ____  ___ __     __ ___  ",
    "|  _ \\ |  _ \\|_ _|\\ \\   / // _ \\ ",
    "| |_) || |_) || |  \\ \\ / /| | | |",
    "|  __/ |  _ < | |   \\ V / | |_| |",
    "|_|    |_| \\_\\___|   \\_/   \\__\\_\\",
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
    return f"{border}│{COLORS['RESET'] if border else ''}{content}{' ' * pad}{border}│{COLORS['RESET'] if border else ''}"


def _center(content, width):
    pad = width - 2 - _visible_len(content)
    left = pad // 2
    right = pad - left
    return f"{' ' * left}{content}{' ' * right}"


def print_welcome():
    use_color = sys.stdout.isatty()
    border = COLORS["BLUE"] if use_color else ""
    accent = COLORS["WHITE"] if use_color else ""
    reset = COLORS["RESET"] if use_color else ""

    term_width = shutil.get_terminal_size((80, 24)).columns
    width = max(BOX_DIMENSIONS["MIN_BOX_WIDTH"], min(BOX_DIMENSIONS["MAX_BOX_WIDTH"], term_width - 2))

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
    grey = COLORS["DIM_GREY"] if use_color else ""
    print(f"{grey}{'─' * term_width}{reset}")
    print()
