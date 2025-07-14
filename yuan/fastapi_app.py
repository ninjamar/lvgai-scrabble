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

_orig_dataclass = _dc.dataclass  # Preserve the original decorator


def _forgiving_dataclass(cls=None, **kwargs):
    """A drop-in replacement for `dataclasses.dataclass` that tolerates default
    fields preceding non-default fields by automatically re-ordering them.
    This is **ONLY** intended as a runtime fix-up until the source is cleaned
    up.  It leaves dataclass semantics unchanged for all well-formed classes."""

    # Support usage both with and without parentheses: @dataclass vs @dataclass()
    if cls is None:
        return lambda real_cls: _forgiving_dataclass(real_cls, **kwargs)

    import typing as _t
    ann = dict(getattr(cls, "__annotations__", {}))  # copy to mutate
    names = list(ann.keys())

    # Detect whether we have any default-value field appearing before a
    # non-default field.
    seen_default = False
    needs_fix = False
    for name in names:
        if hasattr(cls, name):
            seen_default = True
        elif seen_default:
            needs_fix = True
            break

    # Also check for missing annotations on dataclasses.fields
    missing_ann = any(isinstance(v, _dc.Field) and k not in ann for k, v in cls.__dict__.items())

    if needs_fix or missing_ann:
        # Ensure every attribute that uses dataclasses.field has a type annotation.
        for attr_name, attr_val in list(cls.__dict__.items()):
            if isinstance(attr_val, _dc.Field) and attr_name not in ann:
                ann[attr_name] = _t.Any
                names.append(attr_name)

        # Re-partition after possibly adding new annotations
        non_defaults = [(n, ann[n]) for n in names if not hasattr(cls, n)]
        defaults = [
            (n, ann[n], getattr(cls, n)) for n in names if hasattr(cls, n)
        ]

        # Temporarily restore original decorator to avoid recursion
        _dc.dataclass = _orig_dataclass
        try:
            cls = _dc.make_dataclass(
                cls.__name__,
                non_defaults + defaults,
                bases=cls.__bases__,
                namespace={k: v for k, v in cls.__dict__.items() if k not in names},
            )
        finally:
            _dc.dataclass = _forgiving_dataclass  # reinstate wrapper
        return cls

    # Fall back to the standard behaviour for well-formed classes
    return _orig_dataclass(cls, **kwargs)

# Activate the patch 
_dc.dataclass = _forgiving_dataclass

# Import scrabble while the forgiving dataclass decorator is in scope
# Import core game classes; include WordList so we can patch its default factory
from ram.scrabble import Board, Player, WordBank, WordList, Tile, Move
# Provide backward-compatibility aliases expected by earlier code
PWordBank = WordBank
BTile = Tile
MLocation = Tile

# ---------------------------------------------------------------------------
# Fix `Board.word_list` default factory which otherwise calls WordList() with
# no arguments and raises TypeError. We replace it with a lambda returning an
# empty WordList instance.
# ---------------------------------------------------------------------------
Board.__dataclass_fields__["word_list"].default_factory = lambda: WordList(word_list=[])

# Restore the original decorator to avoid affecting unrelated code
_dc.dataclass = _orig_dataclass

app = FastAPI(title="Scrabble Board API", version="0.2.0")


class StartGameRequest(BaseModel):
    players: List[str] = Field(..., min_items=1)


class Location(BaseModel):
    letter: str
    x: int
    y: int


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
    players = [Player(word_bank=WordBank(all_tiles=[], hand=[])) for _ in req.players]
    _board = Board(players=players, current_player=players[0], word_list=WordList(word_list=[]))
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
        move_locs = [
            MLocation(letter=loc.letter, x=loc.x, y=loc.y) for loc in req.locations
        ]
        move = Move(locations=move_locs)
        board.make_move(move)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"message": "Move applied", "turn": board.turn}


@app.get("/board")
def get_board():
    board = _assert_board_exists()
    # Convert Tile objects to dict with letter & multiplier for ease of front-end use.
    simple_board = [
        [
            {
                "letter": getattr(cell, "letter", ""),
                "mult": getattr(cell, "multiplier", 1),
            }
            for cell in row
        ]
        for row in board.board
    ]
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
def get_rack(player: str):
    """Return the rack letters for the specified player (sorted string)."""
    game = _assert_game_exists()
    try:
        rack = game.get_player_rack(player)
    except KeyError:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"player": player, "rack": rack}


def switch_turn():
    """Manually advance to the next player's turn."""
    game = _assert_game_exists()
    game.switch_turn()
    return {"current_player": game.players[game.current_player_idx]}


@app.get("/status")
def status():
    board = _assert_board_exists()
    return {
        "turn": board.turn,
        "current_player_index": (
            board.turn % len(board.players) if board.players else None
        ),
    }


@app.post("/end_game")
def end_game():
    global _board
    _board = None
    return {"message": "Game reset"}


def end_game():
    """End the current game and return final scores."""
    game = _assert_game_exists()
    scores = game.end_game()
    return {"scores": scores}
