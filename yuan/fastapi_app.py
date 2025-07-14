from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from scrabble.engine import ScrabbleGame  

app = FastAPI(title="Scrabble Game API", version="0.1.0")


class StartGameRequest(BaseModel):
    players: List[str]


class PlayWordRequest(BaseModel):
    word: str
    start_row: int
    start_col: int
    direction: str  # "horizontal" or "vertical"


# A single (global) game instance for simplicity. For multi-game support, switch
# to a dict keyed by a game_id.
_game: Optional[ScrabbleGame] = None


def _assert_game_exists() -> ScrabbleGame:
    if _game is None:
        raise HTTPException(status_code=400, detail="Game has not been started.")
    return _game


@app.post("/start_game")
def start_game(req: StartGameRequest):
    """Initialise a new Scrabble game with the provided players."""
    global _game
    _game = ScrabbleGame(req.players)
    _game.start_game()
    return {
        "message": "Game started",
        "players": req.players,
        "current_player": _game.players[_game.current_player_idx],
    }


@app.post("/play_word")
def play_word(req: PlayWordRequest):
    """Place a word on the board and automatically switch the turn."""
    game = _assert_game_exists()
    try:
        gained = game.play_word(
            req.word, req.start_row, req.start_col, req.direction.lower()
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # After a successful move, switch turn
    game.switch_turn()
    return {
        "message": "Word accepted",
        "points_gained": gained,
        "board": game.board,
        "scores": game.scores,
        "next_player": game.players[game.current_player_idx],
    }


@app.get("/board")
def get_board():
    """Return the current board matrix (15×15). Empty squares are spaces."""
    game = _assert_game_exists()
    return {"board": game.board}


@app.get("/rack/{player}")
def get_rack(player: str):
    """Return the rack letters for the specified player (sorted string)."""
    game = _assert_game_exists()
    try:
        rack = game.get_player_rack(player)
    except KeyError:
        raise HTTPException(status_code=404, detail="Player not found")
    return {"player": player, "rack": rack}


@app.post("/switch_turn")
def switch_turn():
    """Manually advance to the next player's turn."""
    game = _assert_game_exists()
    game.switch_turn()
    return {"current_player": game.players[game.current_player_idx]}


@app.get("/status")
def status():
    """Return general game status information."""
    game = _assert_game_exists()
    return {
        "current_player": game.players[game.current_player_idx],
        "scores": game.scores,
        "remaining_tiles": len(game.tile_bag),
    }


@app.post("/end_game")
def end_game():
    """End the current game and return final scores."""
    game = _assert_game_exists()
    scores = game.end_game()
    return {"scores": scores}
