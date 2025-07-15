import sys
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dataclasses as _dc, importlib as _il
from ram.scrabble import Board, Player, WordList,TileBank, create_tile_bag, Tile
WORD_LIST = WordList.load_word_list()

import redis.asyncio as aredis
_rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")

if not hasattr(Board, "_patched_save"):
    async def _save_root(self):
        return await _rd.json().set("scrabble:game_state", "$", self.to_save_dict())
    Board.save_to_redis = _save_root      # type: ignore[attr-defined]
    Board._patched_save = True

from ram.scrabble import TileBank
# Patch TileBank.__init__ to make `hand` optional
app = FastAPI(title="Scrabble Board API", version="0.2.0")


class StartGameRequest(BaseModel):
    players: List[str] = Field(..., min_items=1)


class Location(BaseModel):
    letter: str
    x: int
    y: int
    is_blank: bool = False  # Corresponds to Tile.is_blank field

class MakeMoveRequest(BaseModel):
    locations: List[Location]


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

    players = [Player() for _ in req.players]
    tile_bag = create_tile_bag()

    _board  = Board(players=players, tile_bag=tile_bag)
    _board.initialize(WORD_LIST)

    return {"message": "Game started", "turn": _board.turn}
    


@app.post("/make_move")
def make_move(req: MakeMoveRequest):
    """Apply a move consisting of multiple tile placements."""
    board = _assert_board_exists()
    try:
        tiles = [Tile(letter=loc.letter, x=loc.x, y=loc.y, multiplier=0, is_blank=loc.is_blank) for loc in req.locations]
        board.make_move(tiles)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Move applied", "turn": board.turn}


@app.get("/board")
def get_board():
    board = _assert_board_exists()
    # Convert BTile objects to dict with letter & multiplier for ease of front-end use.
    simple_board = [[{"letter": getattr(cell, "letter", ""), "mult": getattr(cell, "multiplier", 0)} for cell in row] for row in board.board]
    return {"board": simple_board, "turn": board.turn}


@app.get("/validate")
def validate():
    board = _assert_board_exists()
    try:
        board.validate_words()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "All words valid"}


@app.get("/status")
def status():
    board = _assert_board_exists()
    return {
        "turn": board.turn,
        "current_player_index": board.turn % len(board.players) if board.players else None,
    }

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
        raise HTTPException(status_code=400, detail="player index out of range")

    raw_hand = save_dict["players"][idx]["hand"]           # list of (letter, is_blank)
    hand = [{"letter": l, "is_blank": b} for l, b in raw_hand]

    return {"player_index": idx, "hand": hand}

@app.post("/save")
async def save_board():
    """Persist the current board state to Redis."""
    board = _assert_board_exists()
    await board.save_to_redis()
    return {"message": "Board saved to Redis"}


@app.get("/load")
async def load_board():
    """Load the board state from Redis into memory."""
    global _board
    _board = await Board.load_from_redis(WORD_LIST)
    return {"message": "Board loaded", "turn": _board.turn}


@app.post("/end_game")
def end_game():
    global _board
    _board = None
    return {"message": "Game reset"}
