import asyncio
import json
import os

import websockets

from rich import print


# Build the WebSocket URL dynamically
WEBSOCKET_URL = "ws://ai.thewcl.com:8708"


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


MULTIPLIER_INFO = {
    "DLS": ("#8cb7d2", "!"),
    "TLS": ("#057ec3", "@"),
    "DWS": ("#dd8194", "#"),
    "TWS": ("#d03040", "$")
}
def wrap_tag(tag, text):
    return f"[{tag}]{text}[/{tag}]"

def get_format_for_multiplier(multiplier):
    
    item = MULTIPLIER_INFO[multiplier]
    return wrap_tag(item[0], item[1])

def print_board(board):
    print("   " + " ".join(f"{i:2}" for i in range(len(board[0]))))
    print("  +" + "---" * len(board[0]) + "+")
    for y, row in enumerate(board):
        line = f"{y:2}|"
        for cell in row:
            if cell[0] == "" and cell[2] != 0 and not cell[1]: # cell[2] = board multiplier, cell[1] = is_blank
                letter = get_format_for_multiplier(cell[2])
            else:
                letter = cell[0] if cell[0] else "."
            
            line += f" {letter} "
        line += "|"
        print(line)
    print("  +" + "---" * len(board[0]) + "+")

    key = "  " # Two spaces to match above
    for multiplier, (color, symbol) in MULTIPLIER_INFO.items():
        key += f"{multiplier}:{wrap_tag(color, symbol)} "
    print(key)


async def listen_for_updates():
    async with websockets.connect(WEBSOCKET_URL) as ws:
        print(f"Connected to {WEBSOCKET_URL}")
        async for message in ws:
            try:
                data = json.loads(message)
                board = data.get("board")

                if isinstance(board, list):
                    clear_terminal()
                    print_board(board)
                else:
                    print("Invalid board data received.")
            except json.JSONDecodeError:
                print("Received non-JSON message.")


if __name__ == "__main__":
    asyncio.run(listen_for_updates())
