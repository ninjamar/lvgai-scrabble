import asyncio
import json
import os

import websockets

from rich import print


# Build the WebSocket URL dynamically
WEBSOCKET_URL = "ws://ai.thewcl.com:8708"


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def get_format_for_multiplier(multiplier):

    wrap_tag = lambda tag, text: f"[{tag}]{text}[/{tag}]"
    match multiplier:
        case "DLS":
            #8cb7d2
            return wrap_tag("#8cb7d2", "!")
        case "TLS":
            #057ec3
            return wrap_tag("#057ec3", "@")
        case "DWS":
            #dd8194
            return wrap_tag("#dd8194", "#")
        case "TWS":
            #d03040
            return wrap_tag("#d03040", "$")

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
