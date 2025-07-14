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
class BTile:
    """
    A singular tile
    """
    letter: str
    multiplier: int

# TODO: Implement
@dataclasses.dataclass
class PWordBank:
    """
    The hand for a player
    """
    all_tiles: list[BTile]
    hand: list[BTile]
    
    def get_new_hand(self):
        return random.sample(self.all_tiles, 7)
    
    def remove_tiles(self, tiles: list[BTile]):
        for tile in tiles:
            self.hand.remove(tile)

@dataclasses.dataclass
class Player:
    hand: PWordBank

@dataclasses.dataclass
class MLocation:
    letter: str
    x: int
    y: int
    
@dataclasses.dataclass
class Move:
    locations: list[MLocation]

@dataclasses.dataclass
class Board:
    @classmethod
    def initialize_board(cls):
        return [[BTile() for cell in range(15)] for row in range(15)]
    
    turn: int = 0
    current_player: Player
    players: list[Player]

    board = dataclasses.field(default_factory=initialize_board)
    word_list = dataclasses.field(default_factory=WordList)
    
    def __post_init__(self):
        self.current_player = self.players[0]
    
    def make_move(self, move: list[Move]):
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
            
        if not all(loc in self.word_bank.hand for loc in move.locations):
            raise ValueError("All tiles must be in the word bank")
        
        # https://stackoverflow.com/a/433161
        # Check if same column or check if same row
        if bool(all(loc.x == move.locations[0].x for loc in move.locations)) != bool(all(loc.y == move.locations[0].y for loc in move)):
            raise ValueError("All moves must be in the same column or row")

        #... make the moves
        new_board = copy.deepcopy(self.board)
        for loc in move.locations:
            new_board[loc.y][loc.x] = loc

        self.board = new_board

        self.current_player.hand.remove_tiles() # TODO: Implement
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
