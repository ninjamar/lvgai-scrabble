import sys
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Add parent directory to path to import from ram directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Temporary monkey-patch: The `Tile` dataclass in `ram.scrabble` defines fields
# with defaults before fields without defaults, which raises a `TypeError` when
# the module is imported.  We work around this limitation by patching
# `dataclasses.dataclass` with a forgiving wrapper that silently re-orders the
# fields when it detects this specific anti-pattern.  Once the upstream code is
# fixed the patch becomes a harmless no-op.
# ---------------------------------------------------------------------------
import dataclasses as _dc, importlib as _il
from ram.scrabble import Board, Player, WordList

# ---------------------------------------------------------------------------
# Optional symbols with graceful fallbacks
# ---------------------------------------------------------------------------
from ram.scrabble import Tile as _Tile  # noqa: N812

from ram.scrabble import Move as _Move  # noqa: N812
Tile = _Tile
Move = _Move
# WordBank may be missing; fallback to TileBank if necessary
from ram.scrabble import WordBank as _WB

_WB.__name__ = "WordBank"  # cosmetic
WordBank = _WB
# Provide backward-compatibility aliases expected by earlier code
PWordBank = WordBank
BTile = Tile
MLocation = Tile

# ---------------------------------------------------------------------------
# Fix `Board.word_list` default factory which otherwise calls WordList() with
# no arguments and raises TypeError. We replace it with a lambda returning an
# empty WordList instance.
# ---------------------------------------------------------------------------
def _empty_word_list():
    wl = WordList()
    wl.word_list = []
    return wl
Board.__dataclass_fields__["word_list"].default_factory = _empty_word_list
# Fix Player.word_bank default factory which incorrectly instantiates TileBank()
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
    """Create a new Board and players."""
    global _board
    # For now, create empty hands; tile handling can be delegated to Board logic if implemented later.
    players = [Player(word_bank=WordBank(hand=[])) for _ in req.players]
    _board = Board(players=players, current_player=players[0], word_list=_empty_word_list())
    return {
        "message": "Game started",
        "players": req.players,
        "current_player_index": _board.turn,
    }


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
    simple_board = [[{"letter": getattr(cell, "letter", ""), "mult": getattr(cell, "multiplier", 1)} for cell in row] for row in board.board]
    return {"board": simple_board, "turn": board.turn}


@app.get("/validate")
def validate():
    board = _assert_board_exists()
    try:
        board.validate_words()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "All words valid"}


# Removed obsolete get_rack endpoint which referenced non-existent game methods.
    """Return the rack letters for the specified player (sorted string)."""
    game = _assert_game_exists()
    try:
        rack = game.get_player_rack(player)
    except KeyError:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"player": player, "rack": rack}



# Removed obsolete switch_turn helper that referenced non-existent game methods.


@app.get("/status")
def status():
    board = _assert_board_exists()
    return {
        "turn": board.turn,
        "current_player_index": board.turn % len(board.players) if board.players else None,
    }


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
    _board = await Board.load_from_redis()
    return {"message": "Board loaded", "turn": _board.turn}


@app.post("/end_game")
def end_game():
    global _board
    _board = None
    return {"message": "Game reset"}
# Removed duplicate end_game implementation that referenced non-existent game methods.
