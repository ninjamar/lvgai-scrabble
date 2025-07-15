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
[ ] TODO: Test code
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
        
        if not self.is_contiguous(move):
            raise ValueError("Move is not contiguous")
        
        if self.turn > 0 and not self.touches_existing_tile(move, is_first_turn=False):
            raise ValueError("Move must touch an existing tile")
        """
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
        """
        # 1 – lay tiles on a temporary board
        temp_board = copy.deepcopy(self.board)
        for tile in move:
            temp_board[tile.y][tile.x] = Tile.from_another(tile)

        # 2 – build all words just formed
        words = self.extract_words(move, temp_board)

        # 3 – validate each word
        for word, _tiles in words:
            if len(word) < 2:
                raise ValueError("Every word must be at least two letters")
            if not self.word_list.is_valid_word(word):
                raise ValueError(f"‘{word}’ is not in the dictionary")

        # 4 – everything passed → commit the temp board
        self.board = temp_board
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

    def is_contiguous(self, move: list[Tile]):
        """
        1. If move is empty → output False.

        2. Decide orientation
        a. If every tile has the same X coordinate → orientation = vertical, fixed_column = that X.
        b. Else-if every tile has the same Y coordinate → orientation = horizontal, fixed_row = that Y.
        c. Otherwise → output False.   // not a single row or column

        3. Let low and high be the minimum and maximum indices
        • If vertical → indices are the Y values of move tiles.
        • If horizontal → indices are the X values of move tiles.

        4. For each index i from low to high (inclusive):
            If orientation is vertical:
                Check square (fixed_column, i).
            Else:  // horizontal
                Check square (i, fixed_row).

            A square is “occupied” if
                – it contains a newly placed tile, OR
                – the board already holds a letter there.

            If any square between low and high is not occupied → output False.

        5. All squares were occupied → output True.
        """
        if not move:
            return False

        xs = [t.x for t in move]
        ys = [t.y for t in move]
        new_positions = {(t.x, t.y) for t in move}

        # Vertical line
        if len(set(xs)) == 1:
            x = xs[0]
            for y in range(min(ys), max(ys) + 1):
                if (x, y) not in new_positions and not self.board[y][x].letter:
                    return False
            return True

        # Horizontal line
        if len(set(ys)) == 1:
            y = ys[0]
            for x in range(min(xs), max(xs) + 1):
                if (x, y) not in new_positions and not self.board[y][x].letter:
                    return False
            return True

        return False
    
    def touches_existing_tile(self, move: list[Tile], is_first_turn):
        if is_first_turn:
            return False
        
        positions = {(t.x, t.y) for t in move}
        for tile in move:
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                x, y = tile.x + dx, tile.y + dy
                if 0 <= x < 15 and 0 <= y < 15:
                    # If not a just-placed tile and has a letter
                    if (x, y) not in positions and self.board[y][x].letter:
                        return True
        return False
    
    def extract_words(self, move: list[Tile], board_post_move: list):
        words = []
        new_pos = {(t.x, t.y): t for t in move}

        vertical = len({t.x for t in move}) == 1
        primary_axis = 'y' if vertical else 'x'

        # --- build main word ---
        if vertical:
            x = move[0].x
            all_ys = [t.y for t in move]
            y_start = min(all_ys)
            # walk upward to first letter
            while y_start > 0 and board_post_move[y_start - 1][x].letter:
                y_start -= 1
            tiles = []
            y = y_start
            while y < 15 and (board_post_move[y][x].letter or (x, y) in new_pos):
                tiles.append(new_pos.get((x, y), board_post_move[y][x]))
                y += 1
        else:
            y = move[0].y
            all_xs = [t.x for t in move]
            x_start = min(all_xs)
            while x_start > 0 and board_post_move[y][x_start - 1].letter:
                x_start -= 1
            tiles = []
            x = x_start
            while x < 15 and (board_post_move[y][x].letter or (x, y) in new_pos):
                tiles.append(new_pos.get((x, y), board_post_move[y][x]))
                x += 1

        word = ''.join(t.letter for t in tiles)
        words.append((word, tiles))

        # --- build cross words ---
        for t in move:
            if vertical:   # cross words are horizontal
                horiz_tiles = list(self._scan(t.x, t.y, -1, 0))[::-1] + [t] + list(self._scan(t.x, t.y, 1, 0))
                if len(horiz_tiles) > 1:
                    words.append((''.join(tt.letter for tt in horiz_tiles), horiz_tiles))
            else:          # cross words are vertical
                vert_tiles = list(self._scan(t.x, t.y, 0, -1))[::-1] + [t] + list(self._scan(t.x, t.y, 0, 1))
                if len(vert_tiles) > 1:
                    words.append((''.join(tt.letter for tt in vert_tiles), vert_tiles))

        return words
    
    def _scan(self, start_x, start_y, dx, dy):
        x, y = start_x + dx, start_y + dy
        while 0 <= x < 15 and 0 <= y < 15 and self.board[y][x].letter:
            yield self.board[y][x]
            x += dx
            y += dy
    
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
        return json.dumps(self.to_save_dict())

    async def save_to_redis(self):
        return await rd.json().set(REDIS_KEY, ROOT_PATH, self.to_save_dict())

    @classmethod
    async def load_from_redis(cls, word_list: WordList):
        data = await rd.json().get(REDIS_KEY)
        obj = Board.from_save_dict(data, word_list)
        return obj

