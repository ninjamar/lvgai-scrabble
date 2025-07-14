from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from typing import List, Optional

# Import game logic from ram directory (adjust the path if necessary)
from ram.scrabble import Board, Player, PWordBank, Tile, MLocation, Move

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
    players = [Player(hand=PWordBank(all_tiles=[], hand=[])) for _ in req.players]
    _board = Board(players=players)  # type: ignore[arg-type]
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
