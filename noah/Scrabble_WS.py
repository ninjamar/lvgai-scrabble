import asyncio
import websockets
import json
import os
import argparse

# Parse required --team argument
parser = argparse.ArgumentParser(description="ASCII UI for Scrabble")
parser.add_argument("--team", required=True, help="Team number")
args = parser.parse_args()
team_number = int(args.team)
team_number_str = f"{team_number:02d}"

# Build the WebSocket URL dynamically
WEBSOCKET_URL = "ws://ai.thewcl.com:8704"

def clear_terminal():
    os.system("cls" if os.name == "nt" else "clear")

def format_cell(cell_value, index):
    """
    cell_value: str or None — the letter placed or a bonus marker like 'TW'
    index: tuple — (row, col), not used here but kept for compatibility
    """
    if isinstance(cell_value, str) and len(cell_value) == 1 and cell_value.isalpha():
        return cell_value.upper()  # A placed letter
    elif isinstance(cell_value, str):
        return cell_value  # Bonus like 'TW', 'DL', etc.
    else:
        return '.'  # Empty cell

def render_board(board):
    """
    board: a 15x15 2D list where each cell holds a letter, a bonus marker like 'DL', or None
    """
    size = 15
    # Print column headers: A B C D ...
    column_labels = "   " + " ".join([chr(ord('A') + i) for i in range(size)])
    print(column_labels)

    for row_index in range(size):
        row_cells = []
        for col_index in range(size):
            cell_value = board[row_index][col_index]
            row_cells.append(format_cell(cell_value, (row_index, col_index)))
        print(f"{str(row_index + 1).rjust(2)} " + " ".join(row_cells))

async def listen_for_updates():
    async with websockets.connect(WEBSOCKET_URL) as ws:
        print(f"Connected to {WEBSOCKET_URL}")
        async for message in ws:
            try:
                data = json.loads(message)
                positions = data.get("positions")

                if (
                    isinstance(positions, list) and 
                    len(positions) == 15 and 
                    all(isinstance(row, list) and len(row) == 15 for row in positions)
                ):
                    clear_terminal()
                    render_board(positions)
                else:
                    print("Invalid board data received.")
            except json.JSONDecodeError:
                print("Received non-JSON message.")

if __name__ == "__main__":
    asyncio.run(listen_for_updates())
