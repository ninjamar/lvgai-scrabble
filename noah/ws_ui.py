import argparse
import asyncio
import json
import os

import httpx
import websockets

# Parse required --team argument
parser = argparse.ArgumentParser(description="ASCII UI for Scrabble")
parser.add_argument("--team", required=True, help="Team number (e.g., 4)")
args = parser.parse_args()
team_number = int(args.team)
team_number_str = f"{team_number:02d}"

# Build URLs
WEBSOCKET_URL = f"ws://ai.thewcl.com:87{team_number_str}"
BASE_URL = "http://localhost:8000"


def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")


def format_cell(cell_value, index):
    if isinstance(cell_value, str) and len(cell_value) == 1 and cell_value.isalpha():
        return cell_value.upper()
    elif isinstance(cell_value, str):
        return cell_value
    else:
        return "."


async def get_state(client: httpx.AsyncClient):
    response = await client.get(f"{BASE_URL}/state")
    if response.status_code != 200:
        return None
    return response.json()


async def start_game(client: httpx.AsyncClient):
    """Start a new game with 2 players."""
    response = await client.post(f"{BASE_URL}/start_game", json={"num_players": 2})
    return response.json()


async def get_hand(client: httpx.AsyncClient, player_index: int):
    response = await client.get(f"{BASE_URL}/hand", params={"player": player_index})
    if response.status_code != 200:
        return []
    return response.json()["hand"]


def print_board(board):
    print("   " + " ".join(f"{i:2}" for i in range(len(board[0]))))
    print("  +" + "---" * len(board[0]) + "+")
    for y, row in enumerate(board):
        line = f"{y:2}|"
        for cell in row:
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
                positions = data.get("positions")
                if "board" in data:
                    clear_terminal()
                    print_board(data["board"])
                elif (
                    isinstance(positions, list)
                    and len(positions) == 15
                    and all(
                        isinstance(row, list) and len(row) == 15 for row in positions
                    )
                ):
                    clear_terminal()
                    print_board(positions)
                else:
                    print("Invalid board data received.")
            except json.JSONDecodeError:
                print("Received non-JSON message.")


async def main():
    async with httpx.AsyncClient() as client:
        # Try to get current state, if no game exists, start a new one
        state = await get_state(client)
        if state is None:
            print("No game found, starting a new game...")
            await start_game(client)
            state = await get_state(client)

        if state is None:
            print("Failed to start game. Exiting.")
            return

        current_player = 0

        while True:
            clear_terminal()

            # Show board
            state = await get_state(client)
            if state is None:
                print("Game state unavailable. Exiting.")
                break
            await print_board(state["board"])

            # Show current player's hand
            hand = await get_hand(client, current_player)
            print(
                f"\nPlayer {current_player}'s tiles:",
                " ".join(tile["letter"].upper() for tile in hand),
            )

            print("\nMake a move (or type 'exit' to quit)")
            word = input("Enter a word: ").strip()
            if word.lower() == "exit":
                break

            x = int(input("Start x (0-14): "))
            y = int(input("Start y (0-14): "))
            direction = input("Direction (horizontal/vertical): ").strip().lower()

            tiles = []
            for i, letter in enumerate(word):
                tx, ty = (x + i, y) if direction == "horizontal" else (x, y + i)
                tiles.append({"letter": letter, "x": tx, "y": ty, "is_blank": False})

            payload = {"locations": tiles, "player_index": current_player}

            response = await client.post(f"{BASE_URL}/make_move", json=payload)

            if response.status_code != 200 or not response.json().get("success", False):
                print(
                    "❌ Invalid move:", response.json().get("message", "Unknown error")
                )
                input("Press Enter to try again...")
            else:
                print("✅ Move accepted!")
                current_player = (current_player + 1) % 2  # Alternate players
                input("Press Enter to continue...")


if __name__ == "__main__":
    asyncio.run(main())
