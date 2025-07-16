import argparse
import asyncio
import json
import os

import httpx
import redis.asyncio as aredis
import websockets

"""
This file implements the user client.
Usage:
    python -m noah.user --init 4
        4 players
    python -m noah.user --player 0
    python -m noah.user --reset
"""


rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")
REDIS_KEY = "scrabble:game_state"
ROOT_PATH = "."

WS_BASE_URL = "ws://ai.thewcl.com:8708"
BASE_URL = "http://localhost:8000"
PUB_SUB_KEY = "scrabble:pubsub"


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


def ensure_input(prompt: str, allowed: list, t: type = str):
    ipt = t(input(prompt))
    while ipt not in allowed:
        try:
            ipt = t(input(prompt))
        except:
            continue
    return ipt


async def start_game(client: httpx.AsyncClient, num_players: int):
    if not (2 <= num_players <= 4):
        print("NUM_PLAYERS must be between 2 and 4 inclusive")
        return
    payload = {"num_players": num_players}
    response = await client.post(f"{BASE_URL}/start", json=payload)
    return response.json()


async def make_move(
    client: httpx.AsyncClient, locations: list, player_index: int = None
):
    payload = {"locations": locations}
    if player_index is not None:
        payload["player_index"] = player_index

    response = await client.post(f"{BASE_URL}/make_move", json=payload)
    return response.json()


async def get_state(client: httpx.AsyncClient):
    response = await client.get(f"{BASE_URL}/state")
    return response.json()

async def handle_board_state(ws, client: httpx.AsyncClient, i_am_playing: int):
    # Fetch the current board state
    state = await get_state(client)
    # print("DEBUG", state)
    # Print the board nicely
    if state.get("detail") is not None:
        print("Game has not been started.")
        exit()

    print_board(state["board"])

    # Show current scores
    for idx, player in enumerate(state["players"]):
        print(f"Player {idx}: {player['score']} points")

    # Check if game is over
    if state.get("is_game_over", False):
        print("Game Over! Final scores:")
        for idx, player in enumerate(state["players"]):
            print(f"Player {idx}: {player['score']} points")
        return True  # Signal caller to exit

    # If it's your turn
    current_player = state["current_player"]
    if current_player == i_am_playing:
        print(f"It’s your turn (Player {current_player})")

        # Show your hand
        # TODO: Get from state
        hand_data = state["players"][i_am_playing]["hand"]

        # hand_data["hand"] is a list of (letter, is_blank) pairs
        hand_letters = " ".join(
            "_" if tile[1] else tile[0].upper() for tile in hand_data
        )
        print(f"Your tiles: {hand_letters}")

        # Number of blanks in hand
        num_blanks = sum(1 for tile in hand_data if tile[1])

        while True:  # Retry until a move succeeds
            # Prompt for move details
            word = input("Enter the word to place: ").strip().upper()
            x = int(input("Start x (0-14): "))
            y = int(input("Start y (0-14): "))
            direction = input("Direction: (h)orizontal/(v)ertical: ").strip().lower()

            if num_blanks == 0:
                # Build locations list
                locations = []
                for i, letter in enumerate(word):
                    tx, ty = (x + i, y) if direction == "h" else (x, y + i)
                    locations.append(
                        {"letter": letter, "x": tx, "y": ty, "is_blank": False}
                    )
            else:
                # Prompt for which letters in the word use blanks
                # Allow for multiple blanks
                blank_positions = set()
                blank_map = {}  # position -> letter
                remaining_blanks = num_blanks

                print(
                    f"You have {num_blanks} blank tile{'s' if num_blanks > 1 else ''}."
                )
                print("If you use any blank(s), specify their position in your word.")

                while remaining_blanks > 0:
                    use_blank = (
                        input(f"Do you want to use a blank tile? (y/n): ")
                        .strip()
                        .lower()
                    )
                    if use_blank != "y":
                        break
                    pos = int(
                        input(
                            "Which position in the word should be blank? (1 = first letter, etc): "
                        )
                    )
                    if pos < 1 or pos > len(word):
                        print("Invalid position, try again.")
                        continue
                    if (pos - 1) in blank_positions:
                        print("You already marked that letter as blank.")
                        continue
                    blank_positions.add(pos - 1)
                    blank_map[pos - 1] = word[pos - 1]
                    remaining_blanks -= 1

                # Now build locations, marking blanks
                locations = []
                for i, letter in enumerate(word):
                    tx, ty = (x + i, y) if direction == "h" else (x, y + i)
                    is_blank = i in blank_positions
                    locations.append(
                        {"letter": letter, "x": tx, "y": ty, "is_blank": is_blank}
                    )
            # print("DEBUG", locations)
            # Send move to API
            response = await make_move(client, locations, int(i_am_playing))
            print(response["message"])

            if response.get("success", False):
                print("Move accepted")
                break  # Exit retry loop
            else:
                print("Invalid move. Try again.")

        # Notify others via websocket and Redis
        await send_to_ws(ws, {"event": "move_made", "player": i_am_playing})
        await rd.publish(PUB_SUB_KEY, f"Player {i_am_playing} made a move")
    else:
        print(f"Waiting for Player {current_player}'s turn...")

    return False  # Signal caller to keep listening


async def listen_for_updates(
    ws: websockets.ClientConnection, client: httpx.AsyncClient, i_am_playing: int
):
    pubsub = rd.pubsub()
    await pubsub.subscribe(PUB_SUB_KEY)

    try:
        result = await handle_board_state(ws, client, i_am_playing)

        print("Waiting for other player...")

        async for message in pubsub.listen():
            if message["type"] == "message":
                result = await handle_board_state(ws, client, i_am_playing)
                if result:
                    return
                print("Waiting for other player...")

    finally:
        await pubsub.aclose()
        await ws.close()


async def send_to_ws(websocket, message):
    await websocket.send(json.dumps(message))


async def main(args):
    async with (
        websockets.connect(
            f"{WS_BASE_URL}/ws", ping_interval=10, ping_timeout=5, close_timeout=10
        ) as ws,
        httpx.AsyncClient() as client,
    ):
        if args.reset:
            await start_game(client, args.reset)
            return
        await listen_for_updates(ws, client, args.player)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrabble user client")

    # EG: Cannot use --init and --playerf
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--player",
        type=int,
        metavar="PLAYER_INDEX",
        help="Join the game as PLAYER_INDEX (0-based)",
    )
    group.add_argument(
        "--reset",
        type=int,
        metavar="NUM_PLAYERS",  # label in help message
        help="Reset the current game with NUM_PLAYERS (2-4)",
    )

    args = parser.parse_args()
    asyncio.run(main(args))
