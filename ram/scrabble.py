"""
    0  1  2  3  4  5  6  7  8  9 10 11 12 13 14
  +---------------------------------------------+
 0| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
 1| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
 2| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
 3| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
 4| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
 5| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
 6| .  .  .  .  .  .  .  .  .  T  .  .  .  .  . |
 7| .  .  .  .  .  H  E  L  L  O  .  .  .  .  . |
 8| .  .  .  .  .  .  .  I  .  .  .  .  .  .  . |
 9| .  .  .  .  .  .  .  T  .  .  .  .  .  .  . |
10| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
11| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
12| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
13| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
14| .  .  .  .  .  .  .  .  .  .  .  .  .  .  . |
  +---------------------------------------------+
"""

"""
[x] TODO: Implement move validation
[x] TODO: Implement scoring
[ ] TODO: Implement game over state (I think running out of tiles)
[x] TODO: Test code
[ ] TODO: In client, enter nothing to pass turn
[ ] TODO: Add UI
[ ] TODO: Fix websocket timeout error and reconnect on error
"""

import copy
import dataclasses
import json
import random
from pathlib import Path

import redis.asyncio as aredis

rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")
REDIS_KEY = "scrabble:game_state"
ROOT_PATH = "."

# {letter: (count, points)}

TILE_INFO = {
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

# https://stackoverflow.com/q/8421337
rotate_list = lambda x: list(zip(*x[::-1]))


def initialize_board():
    return [[Tile(letter="", x=cell, y=row) for cell in range(15)] for row in range(15)]


@dataclasses.dataclass
class WordList:
    """Contains a list of valid words"""

    word_list: set[str] = None

    @classmethod
    def load_word_list(cls):
        with open(Path(__file__).resolve().parent / "words.txt", "r") as f:
            return cls(word_list={word.upper() for word in f.read().splitlines()})

    def is_valid_word(self, word):
        return word.upper() in self.word_list


@dataclasses.dataclass
class Tile:
    """
    A singular tile
    """

    letter: str = None
    points: int = 0

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
        # TODO: Automate
        return cls(
            letter=obj.letter,
            multiplier=obj.multiplier,
            x=obj.x,
            y=obj.y,
            is_blank=obj.is_blank,
            points=obj.points,
        )


def create_tile_bag():
    # TODO: Points
    bag = []
    for letter, (count, points) in TILE_INFO.items():
        for _ in range(count):
            # x/y will be set when placed on board
            if letter == "":
                bag.append(
                    Tile(
                        letter=letter,
                        points=points,
                        multiplier=0,
                        x=None,
                        y=None,
                        is_blank=True,
                    )
                )
            else:
                bag.append(
                    Tile(letter=letter, points=points, multiplier=0, x=None, y=None)
                )
    return bag


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
            for i, hand_tile in enumerate(self.hand):
                if tile.is_blank and hand_tile.is_blank:
                    del self.hand[i]
                    break
                elif (
                    hand_tile.letter == tile.letter
                    and hand_tile.is_blank == tile.is_blank
                ):
                    del self.hand[i]
                    break  # Remove only one instance per tile

    def __contains__(self, item):
        for hand_tile in self.hand:
            if hand_tile.letter == item.letter and hand_tile.is_blank == item.is_blank:
                return True
        return False


@dataclasses.dataclass
class Player:
    word_bank: TileBank = dataclasses.field(default_factory=TileBank)
    score: int = 0


@dataclasses.dataclass
class Board:
    players: list[Player]

    tile_bag: list[Tile]

    # TODO: Single line
    board: list[list] = dataclasses.field(default_factory=initialize_board)
    # Word list needs to stay client side -- so do not make as dict work on this
    word_list: WordList = dataclasses.field(
        default=None, repr=False, compare=False, init=False
    )

    turn: int = 0
    current_player: Player = None

    is_game_over: bool = False

    consecutive_passes: int = 0

    def __post_init__(self):
        if not (2 <= len(self.players) <= 4):
            raise ValueError("Invalid amount of players. Need 2-4 players inclusive.")

    def initialize(self, word_list):
        self.word_list = word_list
        # Can't use post init because this depends on word list
        self.current_player = self.players[0]
        for player in self.players:
            player.word_bank.get_new_hand(self.tile_bag)

    def make_move(self, move: list[Tile], i_am: Player) -> bool:
        # https://playscrabble.com/news-blog/scrabble-rules-official-scrabble-web-games-rules-play-scrabble
        # [x] If it is the first move, it must be on the center square
        # [x] Validate all values -- they must all be in the word bank
        # [x] All moves must be in the same column or row
        # [x] There should be no incomplete words at the end of the turn
        # [x] Words can be horizontal or vertical

        # If move is 0, pass turn
        if len(move) == 0:
            self.consecutive_passes += 1
            
            self.next_turn()

            if self.consecutive_passes >= len(self.players) * 2:
                self.do_game_over()
                
            return True
        else:
            # Reset passes once a valid move has been made
            self.consecutive_passes = 0


        # Correct points
        for tile in move:
            if tile.is_blank:
                tile.points = 0
            else:
                tile.points = TILE_INFO.get(tile.letter.upper())[1]

        if i_am != self.current_player:
            raise ValueError("Incorrect player selected")

        # locations: [(letter, x, y), ...]
        # If it is the first move, it must be on the center square
        if self.turn == 0:
            if not any(tile.x == 7 and tile.y == 7 for tile in move):
                raise ValueError(
                    "First move on first turn must contain a letter on the center square"
                )

        # https://stackoverflow.com/a/433161
        # Check if same column or check if same row
        x_dir = all(loc.x == move[0].x for loc in move)
        y_dir = all(loc.y == move[0].y for loc in move)
        if not (x_dir or y_dir):
            raise ValueError("All moves must be in the same column or row")

        for tile in move:
            spot = self.board[tile.y][tile.x]
            if tile.letter != spot.letter:
                if spot.letter != "":
                    raise ValueError(
                        "Cannot place a tile on an already occupied square"
                    )
                if tile not in self.current_player.word_bank:
                    raise ValueError(
                        f"You don't have the tile {tile.letter} in your word bank"
                    )

        if not self.is_contiguous(move):
            raise ValueError("Move is not contiguous")

        if self.turn > 0 and not self.touches_existing_tile(move, is_first_turn=False):
            raise ValueError("Move must touch an existing tile")

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

        total_score = sum([self.score_word(tiles) for word, tiles in words])

        # Bingo -- use all tiles = increase score by 50s
        if len(move) == 7:
            total_score += 50

        self.current_player.score += total_score

        # 4 – everything passed → commit the temp board
        self.board = temp_board
        # TODO: Do not remove tile already played
        self.current_player.word_bank.remove_tiles(move)  # TODO: Implement

        self.next_turn()
        
    def next_turn(self):
        self.turn += 1
        self.current_player = self.players[self.turn % len(self.players)]

        self.current_player.word_bank.get_new_hand(self.tile_bag)

        self.check_game_over()

    def is_contiguous(self, move: list[Tile]):
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
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
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
        primary_axis = "y" if vertical else "x"

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

        word = "".join(t.letter for t in tiles)
        words.append((word, tiles))

        # --- build cross words ---
        for t in move:
            if vertical:  # cross words are horizontal
                horiz_tiles = (
                    list(self._scan(t.x, t.y, -1, 0))[::-1]
                    + [t]
                    + list(self._scan(t.x, t.y, 1, 0))
                )
                if len(horiz_tiles) > 1:
                    words.append(
                        ("".join(tt.letter for tt in horiz_tiles), horiz_tiles)
                    )
            else:  # cross words are vertical
                vert_tiles = (
                    list(self._scan(t.x, t.y, 0, -1))[::-1]
                    + [t]
                    + list(self._scan(t.x, t.y, 0, 1))
                )
                if len(vert_tiles) > 1:
                    words.append(("".join(tt.letter for tt in vert_tiles), vert_tiles))

        return words

    def _scan(self, start_x, start_y, dx, dy):
        x, y = start_x + dx, start_y + dy
        while 0 <= x < 15 and 0 <= y < 15 and self.board[y][x].letter:
            yield self.board[y][x]
            x += dx
            y += dy

    def to_save_dict(self):
        # HACK: This is done manually. If a field is added to anything, MAKE
        # SURE to add here and to cls.from_save_dict
        return {
            "players": [
                {
                    "hand": [(t.letter, t.is_blank) for t in player.word_bank.hand],
                    "score": player.score,
                }
                for player in self.players
            ],
            "tile_bag": [(t.letter, t.is_blank) for t in self.tile_bag],
            "board": [[(t.letter, t.is_blank) for t in row] for row in self.board],
            "turn": self.turn,
            "current_player": self.players.index(self.current_player),
            "is_game_over": self.is_game_over,
            "consecutive_passes": self.consecutive_passes
        }

    @classmethod
    def from_save_dict(cls, data, word_list):
        # Reconstruct player hands
        players = [
            Player(
                word_bank=TileBank(
                    hand=[Tile(letter=l, is_blank=b) for (l, b) in player_data["hand"]]
                ),
                score=player_data["score"],
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
            is_game_over=data["is_game_over"],
            consecutive_passes=data["consecutive_passes"]
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

    def score_word(self, tiles: list[Tile]) -> int:
        # TODO: Add multiplier
        return sum([0 if tile.is_blank else tile.points for tile in tiles])

    def check_game_over(self):
        # Game is over when both the following are true:
        #   - Tile bag is EMPTY
        #   - Any player has no tiles left
        if len(self.tile_bag) == 0 and any(
            len(player.word_bank.hand) == 0 for player in self.players
        ):
            self.do_game_over()
            return True
        return False
    
    def do_game_over(self):
        self.is_game_over = True
        self.finalize_scores()

    def finalize_scores(self):
        # Figure out who used all the tiles

        out_player = None
        for player in self.players:
            if len(player.word_bank.hand) == 0:
                out_player = player
                break

        # Add a penalty for unused tile values
        for player in self.players:
            # out_player has an empty hand, so no penalty
            penalty = sum(tile.points for tile in player.word_bank.hand)
            player.score -= penalty

        # Award the sum of all penalties to the player who used all the tiles
        if out_player:
            bonus = sum(
                sum(tile.points for tile in player.word_bank.hand)  # player penalty
                for player in self.players
            )
            out_player.score += bonus


def print_board_from_save_dict(save_dict):
    board = save_dict["board"]
    print("   " + " ".join(f"{i:2}" for i in range(len(board[0]))))
    print("  +" + "---" * len(board[0]) + "+")
    for y, row in enumerate(board):
        line = f"{y:2}|"
        for cell in row:
            letter = cell[0] if cell[0] else "."
            line += f" {letter} "
        line += "|"
        print(line)
    print("  +" + "---" * len(board[0]) + "+")


if __name__ == "__main__":
    word_list = WordList.load_word_list()

    p1 = Player()
    p2 = Player()
    b = Board(players=[p1, p2], tile_bag=create_tile_bag())
    b.initialize(word_list)

    p1.word_bank.hand = [
        Tile(letter="H"),
        Tile(letter="E"),
        Tile(letter="L"),
        Tile(letter="L"),
        Tile(letter="O"),
    ]

    print_board_from_save_dict(b.to_save_dict())

    b.make_move(
        [
            Tile(letter="H", x=5, y=7),
            Tile(letter="E", x=6, y=7),
            Tile(letter="L", x=7, y=7),
            Tile(letter="L", x=8, y=7),
            Tile(letter="O", x=9, y=7),
        ],
        p1,
    )

    print_board_from_save_dict(b.to_save_dict())
