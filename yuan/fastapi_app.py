from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from ram.scrabble import (Board, Player, Tile, TileBank, WordList,
                          create_tile_bag)

WORD_LIST = WordList.load_word_list()


app = FastAPI(title="Scrabble Board API", version="0.2.0")


class StartGameRequest(BaseModel):
    num_players: int = Field(ge=2, le=4)


class Location(BaseModel):
    letter: str
    x: int
    y: int
    is_blank: bool = False


class MakeMoveRequest(BaseModel):
    locations: list[Location]
    player_index: int | None


@app.post("/start")
async def start_game(req: StartGameRequest):

    players = [Player() for _ in range(req.num_players)]
    tile_bag = create_tile_bag()

    board = Board(players=players, tile_bag=tile_bag)
    board.initialize(WORD_LIST)

    await board.save_to_redis()
    return {"message": "Game started/reset", "success": True}


@app.post("/make_move")
async def make_move(req: MakeMoveRequest):
    # Defaults to current player if not passed
    board = await Board.load_from_redis(WORD_LIST)
    # build Tile objects from the payload
    tiles = [
        Tile(
            letter=loc.letter,
            x=loc.x,
            y=loc.y,
            multiplier=0,  # TODO: add multiplier
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
async def status():
    board = await Board.load_from_redis(WORD_LIST)
    # No need to save as to_save_dict() doesn't modify the state of the board -- HACK
    return board.to_save_dict()
