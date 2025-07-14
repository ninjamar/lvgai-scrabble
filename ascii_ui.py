import asyncio
import websockets
import json
import os
import argparse

# Parse required --team argument
parser = argparse.ArgumentParser(description="ASCII UI for Tic Tac Toe")
parser.add_argument("--team", required=True, help="Your team number (used as WebSocket port)")
args = parser.parse_args()
team_number = int(args.team)
team_number_str = f"{team_number:02d}"

# Build the WebSocket URL dynamically
WEBSOCKET_URL = f"ws://ai.thewcl.com:87{team_number_str}"


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def format_cell(value, index):
    upper = str(value).upper()
    return upper if upper in ["X", "O"] else str(index)


def render_board(positions):
    def row(start):
        return f" {format_cell(positions[start], start)} | {format_cell(positions[start + 1], start + 1)} | {format_cell(positions[start + 2], start + 2)} "

    line = "---+---+---"
    print(row(0))
    print(line)
    print(row(3))
    print(line)
    print(row(6))
    print()


async def listen_for_updates():
    async with websockets.connect(WEBSOCKET_URL) as ws:
        print(f"Connected to {WEBSOCKET_URL}")
        async for message in ws:
            try:
                data = json.loads(message)
                positions = data.get("positions")
                if isinstance(positions, list) and len(positions) == 9:
                    clear_terminal()
                    render_board(positions)
                else:
                    print("Invalid board data received.")
            except json.JSONDecodeError:
                print("Received non-JSON message.")


if __name__ == "__main__":
    asyncio.run(listen_for_updates())
