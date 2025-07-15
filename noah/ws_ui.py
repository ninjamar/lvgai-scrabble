from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import traceback

import redis.asyncio as aredis
from ram.scrabble import Board, Player, WordList, create_tile_bag, Tile
import asyncio

async def test_redis():
    r = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")
    try:
        pong = await r.ping()
        print("Redis connection successful:", pong)
    except Exception as e:
        print("Redis error:", e)

asyncio.run(test_redis())


# Load word list and set up Redis
WORD_LIST = WordList.load_word_list()
_rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")

app = FastAPI(title="Scrabble Board API", version="0.2.0")

# Global game board
_board: Optional[Board] = None

# ========== Request Models ==========

class StartGameRequest(BaseModel):
    num_players: int = Field(..., ge=2, le=4)


class Location(BaseModel):
    letter: str
    x: int
    y: int
    is_blank: bool = False


class MakeMoveRequest(BaseModel):
    locations: List[Location]
    player_index: Optional[int] = Field(
        None, ge=0, description="0-based index; defaults to current player"
    )


# ========== Internal Utilities ==========

def _assert_board_exists() -> Board:
    if _board is None:
        raise HTTPException(status_code=400, detail="Game has not been started.")
    return _board


# ========== Routes ==========

@app.post("/start_game")
def start_game(req: StartGameRequest):
    global _board
    players = [Player() for _ in range(req.num_players)]
    tile_bag = create_tile_bag()
    _board = Board(players=players, tile_bag=tile_bag)
    _board.initialize(WORD_LIST)
    return {"message": "Game started", "turn": _board.turn, "success": True}


@app.post("/make_move")
async def make_move(req: MakeMoveRequest):
    board = _assert_board_exists()

    tiles = [
        Tile(
            letter=loc.letter,
            x=loc.x,
            y=loc.y,
            multiplier=0,
            is_blank=loc.is_blank,
        )
        for loc in req.locations
    ]

    if req.player_index is None:
        player_obj = board.current_player
    else:
        if req.player_index >= len(board.players):
            raise HTTPException(status_code=400, detail="player_index out of range")
        player_obj = board.players[req.player_index]

    try:
        board.make_move(tiles, player_obj)
        await board.save_to_redis()
        return {"message": "Move applied", "success": True}
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/state")
def get_state():
    board = _assert_board_exists()
    return board.to_save_dict()


@app.get("/hand")
def get_hand(player: Optional[int] = Query(None, ge=0)):
    board = _assert_board_exists()
    save_dict = board.to_save_dict()

    idx = save_dict["current_player"] if player is None else player
    if idx >= len(save_dict["players"]):
        raise HTTPException(status_code=400, detail="player index out of range")

    raw_hand = save_dict["players"][idx]["hand"]
    # If raw_hand is a list of tuples like ('A', False)
    try:
        hand = [{"letter": item["letter"], "is_blank": item["is_blank"]} for item in raw_hand]
    except Exception:
        # fallback in case it's already in dict format
        hand = raw_hand

    return {"player_index": idx, "hand": hand, "success": True}


@app.post("/save")
async def save_board():
    board = _assert_board_exists()
    await board.save_to_redis()
    return {"message": "Board saved to Redis", "success": True}


@app.get("/load")
async def load_board():
    global _board
    _board = await Board.load_from_redis(WORD_LIST)
    return {"message": "Board loaded", "turn": _board.turn, "success": True}


@app.post("/end_game")
def end_game():
    global _board
    _board = None
    return {"message": "Game reset", "success": True}
