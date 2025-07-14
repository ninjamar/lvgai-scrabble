import argparse
import asyncio
import json
import httpx
import redis.asyncio as aioredis
import websockets
import os

redisPubSubKey = "ttt_game_state_changed"

# FastAPI base URL
BASE_URL = "http://localhost:8000"

# CLI argument parsing
parser = argparse.ArgumentParser(description="Tic Tac Toe Game Client")
parser.add_argument(
    "--player", choices=["x", "o"], required=True, help="Which player are you?"
)
parser.add_argument(
    "--reset", action="store_true", help="Reset the board before starting the game."
)
parser.add_argument("--team", required=True, help="Your team number (used as Redis DB number)")
args = parser.parse_args()

i_am_playing = args.player
team_number = int(args.team)
team_number_str = f"{team_number:02d}"
WS_URL = f"ws://ai.thewcl.com:87{team_number_str}"
print(f"Connecting to WebSocket server at {WS_URL}")

# Redis Pub/Sub setup
r = aioredis.Redis(
    host="ai.thewcl.com", port=6379, db=team_number, password=os.getenv("WCL_REDIS_PASSWORD"), decode_responses=True
)
redisPubSubKey = "ttt_game_state_changed"

# FastAPI base URL
BASE_URL = "http://localhost:8000"


async def reset_board():
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BASE_URL}/reset")
        print("Game reset:", response.json())


async def get_board():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/state")
        return response.json()


async def post_move(player, index):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/move", json={"player": player, "index": index}
        )
        return response


async def send_positions_over_websocket(websocket):
    board = await get_board()
    positions = board.get("positions")
    if isinstance(positions, list) and len(positions) == 9:
        await websocket.send(json.dumps({"positions": positions}))


async def handle_board_state(websocket):
    board = await get_board()

    print(json.dumps(board, indent=2))

    if board["state"] != "is_playing":
        print("Game over.")
        return

    if board["player_turn"] == i_am_playing:
        move = input("Your turn! Which square do you want to play? (0-8): ")
        if move.isdigit():
            index = int(move)
            response = await post_move(i_am_playing, index)
            if response.status_code == 200:
                print(response.json()["message"])
                await r.publish(redisPubSubKey, "update")
            else:
                print("Error:", response.json()["detail"])
        else:
            print("Please enter a valid number.")
    else:
        print("Waiting for the other player...")

    await send_positions_over_websocket(websocket)


async def listen_for_updates(websocket):
    pubsub = r.pubsub()
    await pubsub.subscribe(redisPubSubKey)
    print(f"Subscribed to {redisPubSubKey}. Waiting for updates...\n")
    await handle_board_state(websocket)

    async for message in pubsub.listen():
        if message["type"] == "message":
            print("\nReceived update!")
            await handle_board_state(websocket)


async def main():
    if args.reset:
        await reset_board()
        return

    async with websockets.connect(WS_URL) as websocket:
        await listen_for_updates(websocket)


if __name__ == "__main__":
    asyncio.run(main())
