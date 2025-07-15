import sys
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

import asyncio
##sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dataclasses as _dc, importlib as _il
from ram.scrabble import Board, Player, WordList,TileBank, create_tile_bag, Tile
WORD_LIST = WordList.load_word_list()

import redis.asyncio as aredis
_rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")

from ram.scrabble import TileBank
# Patch TileBank.__init__ to make `hand` optional
app = FastAPI(title="Scrabble Board API", version="0.2.0")


class StartGameRequest(BaseModel):
    num_players: int = Field(..., ge=2, le=4)


class Location(BaseModel):
    letter: str
    x: int
    y: int
    is_blank: bool = False  # Corresponds to Tile.is_blank field

class MakeMoveRequest(BaseModel):
    """
    Body for POST /make_move

    • `locations`   list of tiles you want to place  
    • `player_index` (optional) 0-based index of the player making the move.
        – Omit this field to default to the current player whose turn it is.
    """
    locations: List[Location]
    player_index: Optional[int] = Field(
        None, ge=0, description="0-based index; defaults to current player"
    )

# A single (global) game instance for simplicity. For multi-game support, switch
# to a dict keyed by a game_id.
_board: Optional[Board] = None


def _assert_board_exists() -> Board:
    if _board is None:
        raise HTTPException(status_code=400, detail="Game has not been started.")
    return _board


@app.post("/start_game")
def start_game(req: StartGameRequest):
    global _board

    players = [Player() for _ in range(req.num_players)]
    tile_bag = create_tile_bag()

    _board  = Board(players=players, tile_bag=tile_bag)
    _board.initialize(WORD_LIST)

    return {"message": "Game started", "turn": _board.turn, "success": True}
    


@app.post("/make_move")
async def make_move(req: MakeMoveRequest):
    """Apply a move consisting of one or more tile placements."""
    board = _assert_board_exists()

    # build Tile objects from the payload
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

    # pick the acting player
    if req.player_index is None:
        player_obj = board.current_player
    else:
        if req.player_index >= len(board.players):
            raise HTTPException(status_code=400, detail="player_index out of range")
        player_obj = board.players[req.player_index]

    # delegate to backend; it will raise on illegal moves
    try:
        move = board.make_move(tiles, player_obj)
    except Exception as exc:
        return {"message": str(exc), "success": False}
    await board.save_to_redis()
    return {"message": "Move applied", "success": True}


@app.get("/state")
def status():
    board = _assert_board_exists()
    return board.to_save_dict()

@app.get("/hand")
def get_hand(player: Optional[int] = Query(None, ge=0,
                                           description="0-based index; omit for current player")):
    """
    Return the word-bank (hand) for a player.

    * If `player` is absent, we show the current player’s hand.
    * The payload comes straight from `Board.to_save_dict()`, so it stays in sync
      with whatever the backend serialiser produces.
    """
    board = _assert_board_exists()
    save_dict = board.to_save_dict()          # ← single source of truth

    idx = save_dict["current_player"] if player is None else player
    if idx >= len(save_dict["players"]):
        return {"message": "player index out of range", "success": False}

    hand = save_dict["players"][idx]["hand"]           # list of (letter, is_blank)
    return {"player_index": idx, "hand": hand, "success": True}

@app.post("/save") 
async def save_board():
    """Persist the current board state to Redis."""
    board = _assert_board_exists()
    await board.save_to_redis()
    return {"message": "Board saved to Redis", "success": True}


@app.get("/load")
async def load_board():
    """Load the board state from Redis into memory."""
    global _board
    _board = await Board.load_from_redis(WORD_LIST)
    return {"message": "Board loaded", "turn": _board.turn, "success": True}


@app.post("/end_game")
def end_game():
    global _board
    _board = None
    return {"message": "Game reset", "success": True}