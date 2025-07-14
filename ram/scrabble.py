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
Great—this is your **best/clearest version so far**!
Here are the validation bullets (no suggestions, no code—just what’s missing, broken, or unclear):

---

## **What Needs To Be Added / Is Missing**

* **Tile Bag Logic:**

  * No single “tile bag” representing all available tiles (i.e., Scrabble’s set of 100 tiles).
  * `all_tiles` is a field of `WordBank`, but each player would have their own, so not shared or depleted as in real Scrabble.
  * Tiles can still be “duplicated” in player hands.

* **Player Hand Replenishment:**

  * After making a move, hands are not refilled (should always be 7 if possible).
  * No check to prevent overfilling a hand (drawing more than 7).

* **Board Initialization:**

  * In `initialize_board`, `Tile(x=cell, y=row)` is missing required arguments for `letter` (should default to `None`/empty) and `multiplier` (defaults to 0, but in real Scrabble, should set proper special squares).
  * Board multipliers (DL, TL, DW, TW) are **not initialized** (all are zero).

* **Move Validation:**

  * No check that all placed tiles are *contiguous* in the row or column (e.g., can’t place scattered tiles in one turn).
  * No check that placed tiles connect to existing words (after first move).
  * No enforcement of minimum two-letter word.
  * Only checks first letter for center square on first move (should check that the whole move passes through center).

* **Word Extraction and Validation:**

  * `validate_words()` attempts to validate every row and every column as a single word, even if there are gaps.
    (In real Scrabble, must check all contiguous sequences of 2+ letters formed this turn and that all new words are valid.)

* **Score Calculation:**

  * No scoring system at all—no point calculation for plays.

* **Game End and Flow:**

  * No handling for game-over, passing, or empty bag.
  * No game state display.

* **Wildcards/Blank Tiles:**

  * No handling for blank (wild) tiles.

---

## **What Doesn’t Work / Is Broken**

* **Default Factory Use:**

  * `board = dataclasses.field(default_factory=lambda: Board.initialize_board())`

    * This will call `initialize_board()` at class creation time (not each instance).
    * Should be `default_factory=Board.initialize_board` (no parens) or wrapped in a lambda: `lambda: Board.initialize_board()`.
* **Word List Default Factory:**

  * `word_list = dataclasses.field(default_factory=WordList)`

    * Will error because `WordList` requires `word_list` argument. Should be something like `lambda: WordList([])` or similar.
* **Location Equality:**

  * Removing/looking up tiles in `WordBank` (by object identity) may not work as intended if tiles are not exactly the same objects as in hand (may fail if two `Tile('A', ...)` objects with same letter/x/y but are different Python objects).
* **Tile Placement:**

  * Board is updated by replacing references to passed-in `Tile` objects; can cause confusion if re-used in different places (mutation risk).
* **Checking for Existing Tile:**

  * You correctly check if `letter is not None`, but if a cell was initialized with `letter = ""` or not set, could have odd behavior.
* **Word Validation:**

  * Only checks if `col.letter != ""`, but `letter` could be `None` (from default) or `""`—be explicit on what counts as empty.

---

## **Unclear / Needs Clarification**

* **How the tile bag is initialized, shared, or depleted between players.**
* **How multipliers are to be represented (since all are zero now).**
* **How you intend to distinguish between a board `Tile` and a hand `Tile` (same class, but are they conceptually different?).**
* **How the word list is loaded and injected (class method to load, but `WordList` instances need a list).**
* **No display/print for game state—so not possible to check what’s on the board or in hands.**

---

## **Summary**

* **Tile and move validation** is improved from previous versions but still missing key Scrabble logic.
* **Game mechanics** (tile bag, scoring, contiguity, hand refills) not implemented.
* **Code structure** for board/hand/wordbank/tile still needs tightening up for correct gameplay.

---

**You’re definitely converging on something workable.
Let me know which area you want to clarify, learn, or implement next!**

"""

import dataclasses
import copy
import random

# https://stackoverflow.com/q/8421337
rotate_list = lambda x: list(zip(*x[::-1]))


@dataclasses.dataclass
class WordList:
    """Contains a list of valid words"""

    word_list: list[str]

    @classmethod
    def load_word_list(cls):
        with open("words.txt", "r") as f:
            cls.word_list = f.read().splitlines()

    def is_valid_word(self, word):
        return word in self.word_list


@dataclasses.dataclass
class Tile:
    """
    A singular tile
    """

    letter: str = None
    multiplier: int = 0
    x: int
    y: int

# TODO: Implement
@dataclasses.dataclass
class WordBank:
    """
    The hand for a player
    """

    all_tiles: list[Tile]
    hand: list[Tile]

    def get_new_hand(self):
        to_add = 7 - len(self.hand)
        self.hand.extend(random.sample(self.all_tiles, to_add))
        self.all_tiles = [tile for tile in self.all_tiles if tile not in self.hand]

    def remove_tiles(self, tiles: list[Tile]):
        for tile in tiles:
            self.hand.remove(tile)

    def __contains__(self, item):
        return item in self.hand


@dataclasses.dataclass
class Player:
    word_bank: WordBank

@dataclasses.dataclass
class Move:
    locations: list[Tile]


@dataclasses.dataclass
class Board:
    @classmethod
    def initialize_board(cls):
        # TODO: Initialize multipliers
        return [[Tile(x=cell, y=row) for cell in range(15)] for row in range(15)]

    turn: int = 0
    current_player: Player
    players: list[Player]

    board = dataclasses.field(default_factory=lambda: Board.initialize_board())
    word_list = dataclasses.field(default_factory=WordList)

    def __post_init__(self):
        self.current_player = self.players[0]

    def make_move(self, move: Move):
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
            if move.locations[0].x != 7 or move.locations[0].y != 7:
                raise ValueError("First move must be on the center square")

        if not all(loc in self.current_player.word_bank for loc in move.locations):
            raise ValueError("All tiles must be in the word bank")

        # https://stackoverflow.com/a/433161
        # Check if same column or check if same row
        if bool(all(loc.x == move.locations[0].x for loc in move.locations)) != bool(
            all(loc.y == move.locations[0].y for loc in move)
        ):
            raise ValueError("All moves must be in the same column or row")

        # ... make the moves
        new_board = copy.deepcopy(self.board)
        for loc in move.locations:
            if new_board[loc.y][loc.x].letter is not None:
                # Spot alerady occupied
                return False
            loc.multiplier = new_board[loc.y][loc.x].multiplier
            new_board[loc.y][loc.x] = loc

        # TODO: Validate moves here
        # Make sure you can only add to prexisting words

        self.board = new_board

        self.current_player.word_bank.remove_tiles(move.locations)  # TODO: Implement
        self.turn += 1
        self.current_player = self.players[self.turn % len(self.players)]

    def validate_words(self):
        """Validate all words on the board"""
        # Words can be row or column
        for row in self.board:
            for col in row:
                if col.letter != "":
                    word = "".join(col.letter for col in row)
                    if not self.word_list.is_valid_word(word):
                        raise ValueError(f"Word {word} is not valid")

        for row in rotate_list(self.board):
            for col in row:
                if col.letter != "":
                    word = "".join(col.letter for col in row)
                    if not self.word_list.is_valid_word(word):
                        raise ValueError(f"Word {word} is not valid")
