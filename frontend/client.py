import argparse
import asyncio
import json
import os
from io import StringIO

import httpx
import redis.asyncio as aredis
import websockets
from dotenv import load_dotenv
from rich import print

from .render import write_board

"""
This file implements the user client.
Usage:
    python -m noah.user --init 4
        4 players
    python -m noah.user --player 0
    python -m noah.user --reset
"""


load_dotenv()

rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")
REDIS_KEY = "scrabble:game_state"
ROOT_PATH = "."

WS_BASE_URL = "ws://ai.thewcl.com:8708"
BASE_URL = "http://localhost:8000"
PUB_SUB_KEY = "scrabble:pubsub"

OPENAI_PROXY_URL = "http://ai.thewcl.com:6502"
OPENAI_PROXY_AUTH = os.environ["OPENAI_PROXY_AUTH"]

SYSTEM_PROMPT = """
You are playing Scrabble. You will receive the current board state and your hand of tiles as JSON input.

* The **"board"** key contains a 15x15 grid showing the current board. Letters represent tiles already played; symbols represent special squares:

  * `$` = Triple Word Score (TWS)
  * `#` = Double Word Score (DWS)
  * `@` = Triple Letter Score (TLS)
  * `!` = Double Letter Score (DLS)
  * `.` = Empty square
* The **"hand"** key contains the tiles you can play. Blanks (wildcards) are shown as underscores (`"_"`). You may use blanks to represent any letter.
* If you use one or more blanks, you **must** specify each blank’s position in your word using 1-based indexing (e.g., if the blank is the second letter of the word, include `2` in the "blanks" array).
* All words formed must be valid English words. The new word must be placed in a legal Scrabble position, connected to existing words (if the board is not empty).

**Your task:**
Decide on the highest-scoring or strongest valid move using the current hand. Place the word on the board according to Scrabble rules, using at least one letter from your hand. Output your move as a JSON object using this schema:

```json
{
  "word": "<WORD IN UPPERCASE>",
  "start": [x, y],
  "direction": "h" or "v",
  "blanks": [positions]
}
```

* `"word"`: The word you will play, in uppercase.
* `"start"`: The starting position (column, row) of your word (0-based indices).
* `"direction"`: `"h"` for horizontal (left-to-right), `"v"` for vertical (top-to-bottom).
* `"blanks"`: A list of positions (1-based index) in the word where you used a blank, or `[]` if no blanks.

**Only output the JSON object. Do not add any extra text or explanation.**

Here is your input:
"""


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


async def get_ai(client: httpx.AsyncClient, board, hand_data):

    # Write board to string
    stream = StringIO()
    write_board(board, color=False, output=stream)
    data = stream.getvalue()

    user_prompt = {
        "hand": hand_data,
        "board": data
    }

    response = await client.post(
        f"{OPENAI_PROXY_URL}/chat",
        params={"json": True},
        json={
            "model": "gpt-4.1-nano",
            "system_prompt": SYSTEM_PROMPT,
            "user_prompt": json.dumps(user_prompt),
        },
        headers={"Authorization": f"Bearer {OPENAI_PROXY_AUTH}"},
    )
    data = response.json()
    print(data)
    return json.loads(data["output"][0]["content"][0]["text"])


async def create_locations_from_ai(client, board, hand_letters, i_am_playing):
    # Get AI move suggestion
    ai_response = await get_ai(client, board, hand_letters)
    print("[AI] Response:", ai_response)

    # Default to passing if the AI gives no move or word is null
    if not ai_response or ai_response.get("word") is None:
        print("[AI] No valid moves. Passing turn.")
        locations = []
    else:
        word = ai_response["word"]
        start_x, start_y = ai_response["start"]
        direction = ai_response["direction"]
        blanks = ai_response["blanks"]

        # Set increments for direction
        dx, dy = (1, 0) if direction == "h" else (0, 1)

        # Build move locations
        locations = []
        for i, letter in enumerate(word):
            x = start_x + dx * i
            y = start_y + dy * i
            # Blanks is a list of 1-based positions
            is_blank = (i + 1) in blanks
            locations.append(
                {"letter": letter, "x": x, "y": y, "is_blank": is_blank}
            )

    # Send the move to the backend
    response = await make_move(client, locations, int(i_am_playing))
    # print(response["message"])

    if response.get("success"):
        print("Move accepted")
    else:
        print("Invalid move from AI.")

    return locations

async def user_do_action(client, hand_data, state, i_am_playing):
    # Number of blanks in hand
    num_blanks = sum(1 for tile in hand_data if tile[1])

        # Prompt for move details
    word = input("Enter the word to place: ").strip().upper()
    locations = []
    if not word:
        return []

    x = int(input("Start x (0-14): "))
    y = int(input("Start y (0-14): "))
    direction = (
        input("Direction: (h)orizontal/(v)ertical: ").strip().lower()
    )

    #if num_blanks == 0:
    #    pass
        # # Build locations list
        # locations = []
        # for i, letter in enumerate(word):
        #     tx, ty = (x + i, y) if direction == "h" else (x, y + i)
        #     locations.append(
        #         {"letter": letter, "x": tx, "y": ty, "is_blank": False}
        #     )
    if num_blanks > 0:
        # Prompt for which letters in the word use blanks
        # Allow for multiple blanks
        blank_positions = set()
        blank_map = {}  # position -> letter
        remaining_blanks = num_blanks

        print(
            f"You have {num_blanks} blank tile{'s' if num_blanks > 1 else ''}."
        )
        print(
            "If you use any blank(s), specify their position in your word."
        )

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

        # # Now build locations, marking blanks
        # locations = []
        # for i, letter in enumerate(word):
        #     tx, ty = (x + i, y) if direction == "h" else (x, y + i)
        #     is_blank = i in blank_positions
        #     locations.append(
        #         {
        #             "letter": letter,
        #             "x": tx,
        #             "y": ty,
        #             "is_blank": is_blank,
        #         }
        #     )
    board = state["board"]

    locations = []
    for i, letter in enumerate(word):
        tx, ty = (x + i, y) if direction == "h" else (x, y + i)
        board_letter = board[ty][tx][0]
        is_blank = False
        if num_blanks > 0:
            is_blank = i in blank_positions  # blank_positions is already set above if used

        if board_letter.upper() != letter.upper():
            locations.append(
                {
                    "letter": letter,
                    "x": tx,
                    "y": ty,
                    "is_blank": is_blank,
                }
            )
    return locations

async def handle_board_state(
    ws, client: httpx.AsyncClient, i_am_playing: int, is_ai: bool
):

    # Fetch the current board state
    state = await get_state(client)
    # print("DEBUG", state)
    # Print the board nicely
    if state.get("detail") is not None:
        print("Game has not been started.")
        exit()

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
        
        while True:
            if is_ai:
                locations = await create_locations_from_ai(client, state["board"], hand_letters, i_am_playing)
            else:
                locations = await user_do_action(client, hand_data, state, i_am_playing)

            response = await make_move(client, locations, int(i_am_playing))
            
            # print(response["message"])

            if response.get("success", False):
                print("Move accepted")
                break  # Exit retry loop
            else:
                print("Invalid move. Try again.")
                

        # Notify others via websocket and Redis
        # await send_to_ws(ws, state)
        await send_state(ws, client)
        await rd.publish(PUB_SUB_KEY, f"Player {i_am_playing} made a move")
    else:
        print(f"Waiting for Player {current_player}'s turn...")

    return False  # Signal caller to keep listening


async def send_state(ws, client):
    state = await get_state(client)

    await send_to_ws(ws, state)


async def listen_for_updates(
    ws: websockets.ClientConnection,
    client: httpx.AsyncClient,
    i_am_playing: int,
    is_ai: bool,
):
    pubsub = rd.pubsub()
    await pubsub.subscribe(PUB_SUB_KEY)

    await send_state(ws, client)
    try:
        result = await handle_board_state(ws, client, i_am_playing, is_ai)

        print("Waiting for other player...")

        async for message in pubsub.listen():
            if message["type"] == "message":
                result = await handle_board_state(ws, client, i_am_playing, is_ai)
                if result:
                    return
                print("Waiting for other player...")

    finally:
        await pubsub.aclose()
        await ws.close()


async def send_to_ws(websocket, message):
    await websocket.send(json.dumps(message))


async def main(args):
    while True:
        try:
            async with (
                websockets.connect(f"{WS_BASE_URL}/ws") as ws,
                httpx.AsyncClient() as client,
            ):
                if args.reset:
                    await start_game(client, args.reset)
                    return
                await listen_for_updates(ws, client, args.player, args.ai)

        except websockets.ConnectionClosedError:
            print("Websocket connection error. Retrying in 500ms")
            await asyncio.sleep(0.5)


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

    # Not mutually exclusives
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Play the current player as AI",
    )

    args = parser.parse_args()
    if args.player and args.player is None:
        parser.error("--ai requires player to be specified")
    asyncio.run(main(args))
