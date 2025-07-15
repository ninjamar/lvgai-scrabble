"""
      0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  <- x
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 0 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 1 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 2 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 3 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 4 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 5 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 6 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 7 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 8 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 9 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
10 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
11 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
12 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
13 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
14 | T | T | T | T | T | T | T | T | T | T | T | T | T | T | T |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
^y
"""
"""
[ ] TODO: Implement move validation
[ ] TODO: Implement scoring
"""

import json
import dataclasses
import redis.asyncio as aredis
import copy
import random

from typing import ClassVar


rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")
REDIS_KEY = "scrabble:game_state"
ROOT_PATH = "."

# https://stackoverflow.com/q/8421337
rotate_list = lambda x: list(zip(*x[::-1]))


@dataclasses.dataclass
class WordList:
    """Contains a list of valid words"""

    word_list: list[str] = None
    
    @classmethod
    def load_word_list(cls):
        # TODO: Use abs path
        with open("words.txt", "r") as f:
            return cls(word_list=f.read().splitlines())

    def is_valid_word(self, word):
        return word in self.word_list


@dataclasses.dataclass
class Tile:
    """
    A singular tile
    """

    letter: str = None
    multiplier: int = 0
    x: int = None
    y: int = None

    is_blank: bool = False

    def __eq__(self, other):
        if not isinstance(other, Tile):
            return False
        return (self.letter, self.x, self.y, self.is_blank) == (
            other.letter,
            other.x,
            other.y,
            other.is_blank,
        )

    def __hash__(self):
        return hash((self.letter, self.x, self.y, self.is_blank))

    @classmethod
    def from_another(cls, obj: "Tile"):
        return cls(
            letter=obj.letter,
            multiplier=obj.multiplier,
            x=obj.x,
            y=obj.y,
            is_blank=obj.is_blank
        )



def create_tile_bag():
    # TODO: Points
    # {letter: (count, value)}
    tile_counts = {
        "E": (12, 1),
        "A": (9, 1),
        "I": (9, 1),
        "O": (8, 1),
        "N": (6, 1),
        "R": (6, 1),
        "T": (6, 1),
        "L": (4, 1),
        "S": (4, 1),
        "U": (4, 1),
        "D": (4, 2),
        "G": (3, 2),
        "B": (2, 3),
        "C": (2, 3),
        "M": (2, 3),
        "P": (2, 3),
        "F": (2, 4),
        "H": (2, 4),
        "V": (2, 4),
        "W": (2, 4),
        "Y": (2, 4),
        "K": (1, 5),
        "J": (1, 8),
        "X": (1, 8),
        "Q": (1, 10),
        "Z": (1, 10),
        "": (2, 0),  # Blanks as ''
    }
    bag = []
    for letter, (count, points) in tile_counts.items():
        for _ in range(count):
            # x/y will be set when placed on board
            if letter == "":
                bag.append(
                    Tile(letter=letter, multiplier=0, x=None, y=None, is_blank=True)
                )
            else:
                bag.append(Tile(letter=letter, multiplier=0, x=None, y=None))
    return bag


def from_dict(cls, d: dict):
    kwargs = {}
    for f in dataclasses.fields(cls):
        if not f.init: # init=False
            continue

        value = d.get(f.name)
        if dataclasses.is_dataclass(f.type):
            if isinstance(value, dict):
                kwargs[f.name] = from_dict(f.type, value)
            elif isinstance(value, list):
                kwargs[f.name] = [from_dict(f.type, v) if isinstance(v, dict) else v for v in value]
            else:
                kwargs[f.name] = value
        elif (isinstance(value, list) and
              hasattr(f.type, "__origin__") and
              f.type.__origin__ is list and
              dataclasses.is_dataclass(f.type.__args__[0])):
            # For list of dataclasses
            item_type = f.type.__args__[0]
            kwargs[f.name] = [from_dict(item_type, item) if isinstance(item, dict) else item for item in value]
        else:
            kwargs[f.name] = value
    return cls(**kwargs)



@dataclasses.dataclass
class TileBank:
    """
    The hand for a player
    """

    hand: list[Tile] = dataclasses.field(default_factory=list)

    def get_new_hand(self, tile_bag):
        to_add = 7 - len(self.hand)
        for _ in range(min(to_add, len(tile_bag))):
            tile = tile_bag.pop(random.randrange(len(tile_bag)))
            self.hand.append(tile)

    def remove_tiles(self, tiles: list[Tile]):
        for tile in tiles:
            self.hand.remove(tile)

    def __contains__(self, item):
        return item in self.hand


@dataclasses.dataclass
class Player:
    word_bank: TileBank = dataclasses.field(default_factory=TileBank)


@dataclasses.dataclass
class Board:
    players: list[Player]

    tile_bag: list[Tile]

    @classmethod
    def initialize_board(cls):
        # TODO: Initialize multipliers
        return [
            [Tile(letter="", x=cell, y=row) for cell in range(15)] for row in range(15)
        ]
    # TODO: Single line
    board: list[list] = dataclasses.field(default_factory=lambda: Board.initialize_board())
    # Word list needs to stay client side -- so do not make as dict work on this
    word_list: WordList = dataclasses.field(default=None, repr=False, compare=False, init=False)

    turn: int = 0
    current_player: Player = None

    def initialize(self, word_list):
        self.word_list = word_list
        # Can't use post init because this depends on word list
        self.current_player = self.players[0]
        for player in self.players:
            player.word_bank.get_new_hand(self.tile_bag)

    def make_move(self, move: list[Tile]):
        # https://playscrabble.com/news-blog/scrabble-rules-official-scrabble-web-games-rules-play-scrabble
        # [x] If it is the first move, it must be on the center square
        # [x] Validate all values -- they must all be in the word bank
        # [x] All moves must be in the same column or row
        # [ ] There should be no incomplete words at the end of the turn
        # [ ] Word must be two letters
        # [ ] Words can be horizontal or vertical

        # locations: [(letter, x, y), ...]
        # If it is the first move, it must be on the center square
        if self.turn == 0:
            if move[0].x != 7 or move[0].y != 7:
                raise ValueError("First move must be on the center square")

        if not all(loc in self.current_player.word_bank for loc in move):
            raise ValueError("All tiles must be in the word bank")

        # https://stackoverflow.com/a/433161
        # Check if same column or check if same row
        if bool(all(loc.x == move[0].x for loc in move)) != bool(
            all(loc.y == move[0].y for loc in move)
        ):
            raise ValueError("All moves must be in the same column or row")

        # ... make the moves
        to_remove = []
        new_board = copy.deepcopy(self.board)

        for idx, loc in enumerate(move):
            if not new_board[loc.y][loc.x].letter:
                # Spot alerady occupied
                return False
            if new_board[loc.y][loc.x].is_blank:
                to_remove.append(idx)
            loc.multiplier = new_board[loc.y][loc.x].multiplier
            new_board[loc.y][loc.x] = Tile.from_another(loc)

        for idx in to_remove:
            del move[idx]
        # TODO: Validate moves here
        # Make sure you can only add to prexisting words
        if not self.validate_words():
            return False

        self.board = new_board

        self.current_player.word_bank.remove_tiles(move)  # TODO: Implement
        self.turn += 1
        self.current_player = self.players[self.turn % len(self.players)]

        self.current_player.word_bank.get_new_hand(self.tile_bag)

    def validate_words(self):
        """Validate all words on the board"""
        # Words can be row or column
        for row in self.board:
            for col in row:

                if col.letter == "":
                    return False
                word = "".join(col.letter for col in row)
                if not self.word_list.is_valid_word(word):
                    return False

        for row in rotate_list(self.board):
            for col in row:
                if col.letter == "":
                    return False
                word = "".join(col.letter for col in row)
                if not self.word_list.is_valid_word(word):
                    return False
        return True

    def to_dict(self):
        return dataclasses.asdict(self)
    
    def to_save_dict(self):
        return {
            "players": [
                {
                    "hand": [(t.letter, t.is_blank) for t in player.word_bank.hand]
                }
                for player in self.players
            ],
            "tile_bag": [(t.letter, t.is_blank) for t in self.tile_bag],
            "board": [[(t.letter, t.is_blank) for t in row] for row in self.board],
            "turn": self.turn,
            "current_player": self.players.index(self.current_player),
        }
    @classmethod
    def from_save_dict(cls, data, word_list):
        # Reconstruct player hands
        players = [
            Player(
                word_bank=TileBank(
                    hand=[Tile(letter=l, is_blank=b) for (l, b) in player_data["hand"]]
                )
            )
            for player_data in data["players"]
        ]
        # Reconstruct tile bag
        tile_bag = [Tile(letter=l, is_blank=b) for (l, b) in data["tile_bag"]]
        # Reconstruct board
        board = [
            [Tile(letter=l, is_blank=b, x=x, y=y) for x, (l, b) in enumerate(row)]
            for y, row in enumerate(data["board"])
        ]
        # Create Board instance
        board_obj = cls(
            players=players,
            tile_bag=tile_bag,
            board=board,
            turn=data["turn"],
            current_player=players[data["current_player"]],
        )
        board_obj.word_list = word_list  # inject client word list
        return board_obj


    def serialize(self):
        return json.dumps(self.to_dict())

    async def save_to_redis(self):
        return await rd.json().set(REDIS_KEY, ROOT_PATH, self.to_save_dict())

    @classmethod
    async def load_from_redis(cls, word_list: WordList):
        data = await rd.json().get(REDIS_KEY)
        obj = Board.from_save_dict(data, word_list)
        return obj
