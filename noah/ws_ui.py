import websockets
import json
import os
import argparse
import httpx
import asyncio

# Parse required --team argument
parser = argparse.ArgumentParser(description="ASCII UI for Scrabble")
parser.add_argument("--team", required=True, help="Team 4")
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
    return response.json()

async def reset_board(client: httpx.AsyncClient):
    response = await client.post(f"{BASE_URL}/reset")
    return response.json()

async def render_board(board):
    size = 15
    column_labels = "   " + " ".join([chr(ord("A") + i) for i in range(size)])
    print(column_labels)
    for row_index in range(size):
        row_cells = []
        for col_index in range(size):
            cell_value = board[row_index][col_index]
            row_cells.append(format_cell(cell_value, (row_index, col_index)))
        print(f"{str(row_index + 1).rjust(2)} " + " ".join(row_cells))

async def print_board_from_save_dict(save_dict):
    board = save_dict["board"]
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
                    await print_board_from_save_dict(data)
                elif isinstance(positions, list) and len(positions) == 15 and all(isinstance(row, list) and len(row) == 15 for row in positions):
                    clear_terminal()
                    await render_board(positions)
                else:
                    print("Invalid board data received.")
            except json.JSONDecodeError:
                print("Received non-JSON message.")

async def main():
    async with httpx.AsyncClient() as client:
        await reset_board(client)

        while True:
            clear_terminal()

            # Show board
            state = await get_state(client)
            await print_board_from_save_dict(state)

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
                tiles.append({
                    "letter": letter,
                    "x": tx,
                    "y": ty,
                    "is_blank": False
                })

            payload = {
                "locations": tiles,
                "player_index": 0  # You can change this to support turn switching
            }

            response = await client.post(f"{BASE_URL}/make_move", json=payload)

            if response.status_code != 200:
                print("❌ Invalid move:", response.json()["detail"])
                input("Press Enter to try again...")
            else:
                print("✅ Move accepted!")
                input("Press Enter to continue...")

if __name__ == "__main__":
    asyncio.run(main())
