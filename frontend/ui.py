import asyncio
import json

import websockets

from .render import clear_terminal, write_board

# Build the WebSocket URL dynamically
WEBSOCKET_URL = "ws://ai.thewcl.com:8708"


async def listen_for_updates():

    async with websockets.connect(WEBSOCKET_URL) as ws:
        print(f"Connected to {WEBSOCKET_URL}")
        async for message in ws:
            try:
                data = json.loads(message)
                board = data.get("board")

                if isinstance(board, list):
                    clear_terminal()

                    write_board(board)
                else:
                    print("Invalid board data received.")
            except json.JSONDecodeError:
                print("Received non-JSON message.")


if __name__ == "__main__":
    asyncio.run(listen_for_updates())
