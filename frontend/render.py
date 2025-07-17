import os
import sys

from rich import print

MULTIPLIER_INFO = {
    "DLS": ("#8cb7d2", "!"),
    "TLS": ("#057ec3", "@"),
    "DWS": ("#dd8194", "#"),
    "TWS": ("#d03040", "$"),
}


def wrap_tag(tag, text):
    return f"[{tag}]{text}[/{tag}]"


def get_format_for_multiplier(multiplier, color=True):

    item = MULTIPLIER_INFO[multiplier]
    if color:
        return wrap_tag(item[0], item[1])
    else:
        return item[0]


def write_board(board, color=True, output=sys.stdout):
    print("   " + " ".join(f"{i:2}" for i in range(len(board[0]))), file=output)
    print("  +" + "---" * len(board[0]) + "+", file=output)
    for y, row in enumerate(board):
        line = f"{y:2}|"
        for cell in row:
            if (
                cell[0] == "" and cell[2] != 0 and not cell[1]
            ):  # cell[2] = board multiplier, cell[1] = is_blank
                letter = get_format_for_multiplier(cell[2], color)
            else:
                letter = cell[0] if cell[0] else "."

            line += f" {letter} "
        line += "|"
        print(line, file=output)
    print("  +" + "---" * len(board[0]) + "+", file=output)

    key = "  "  # Two spaces to match above
    for multiplier, (color, symbol) in MULTIPLIER_INFO.items():
        key += f"{multiplier}:{wrap_tag(color, symbol)} "
    print(key, file=output)


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")
