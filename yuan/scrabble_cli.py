import random
import string
from collections import Counter
from typing import List, Dict


BOARD_SIZE = 15  # Standard Scrabble board size
RACK_SIZE = 7

# Very small English word list for demo purposes
SAMPLE_DICTIONARY = {
    "HELLO", "WORLD", "PYTHON", "SCRABBLE", "TEST", "WORDS", "PLAYER",
    "GAME", "CODE", "AI", "CHAT", "OPENAI", "BOARD", "TILES",
}

# Standard Scrabble letter values
LETTER_SCORES = {
    **{ltr: 1 for ltr in "EAIONRTLSU"},
    **{ltr: 2 for ltr in "DG"},
    **{ltr: 3 for ltr in "BCMP"},
    **{ltr: 4 for ltr in "FHVWY"},
    "K": 5,
    **{ltr: 8 for ltr in "JX"},
    **{ltr: 10 for ltr in "QZ"},
}


class ScrabbleGame:
    """A **minimal** Scrabble backend implementing the required interface.

    The rules are heavily simplified so that the UI works out-of-the-box.
    Replace individual methods with a full implementation when desired.
    """

    def __init__(self, players: List[str]):
        self.players = players
        self.scores: Dict[str, int] = {p: 0 for p in players}
        self.current_player_idx = 0
        self.board = [[" " for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.tile_bag = self._generate_tile_bag()
        self.racks: Dict[str, List[str]] = {p: [] for p in players}
        self.game_over = False

    # ---------------- Public API ---------------- #
    def start_game(self):
        """Initialises board, tiles & racks."""
        for player in self.players:
            self.draw_tiles(player, RACK_SIZE)

    def play_word(self, word: str, start_row: int, start_col: int, direction: str):
        """Places a word on the board if possible and updates score & rack."""
        if not self.is_valid_word(word):
            raise ValueError(f"'{word}' is not a valid dictionary word.")

        word = word.upper()
        dr, dc = (0, 1) if direction == "horizontal" else (1, 0)
        row, col = start_row, start_col
        letters_needed = []

        # Check board boundaries and gather required letters
        for ch in word:
            if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
                raise ValueError("Word does not fit on the board.")
            if self.board[row][col] == " ":
                letters_needed.append(ch)
            elif self.board[row][col] != ch:
                raise ValueError("Cannot overwrite existing tiles with different letters.")
            row += dr
            col += dc

        current_player = self._current_player()
        rack_counter = Counter(self.racks[current_player])
        needed_counter = Counter(letters_needed)
        if not needed_counter <= rack_counter:
            raise ValueError("You do not have the necessary tiles to play this word.")

        # Place the letters
        row, col = start_row, start_col
        for ch in word:
            self.board[row][col] = ch
            row += dr
            col += dc

        # Update rack & score
        for ch in letters_needed:
            self.racks[current_player].remove(ch)
        self.draw_tiles(current_player, len(letters_needed))
        score = self.calculate_word_score(word, start_row, start_col, direction)
        self.scores[current_player] += score
        return score

    def is_valid_word(self, word: str):
        return word.upper() in SAMPLE_DICTIONARY

    def calculate_word_score(self, word: str, start_row: int, start_col: int, direction: str):
        # Simplified: sum of letter points (no board bonuses)
        return sum(LETTER_SCORES.get(ch, 0) for ch in word.upper())

    def switch_turn(self):
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)

    # -------- Helper Methods -------- #
    def draw_tiles(self, player: str, count: int):
        for _ in range(min(count, len(self.tile_bag))):
            self.racks[player].append(self.tile_bag.pop())

    def get_player_rack(self, player: str):
        return "".join(sorted(self.racks[player]))

    def end_game(self):
        self.game_over = True
        return self.scores

    # -------------- Internal -------------- #
    def _generate_tile_bag(self):
        # Extremely simplified: 98 random uppercase letters
        bag = [random.choice(string.ascii_uppercase) for _ in range(98)]
        random.shuffle(bag)
        return bag

    def _current_player(self):
        return self.players[self.current_player_idx]


# ----------------------- Terminal UI ----------------------- #

def print_board(board):
    """Renders the board in ASCII."""
    header = "   " + " ".join(f"{i:2d}" for i in range(BOARD_SIZE))
    print(header)
    for idx, row in enumerate(board):
        row_str = " ".join(ch if ch != " " else "." for ch in row)
        print(f"{idx:2d} {row_str}")


def main():
    print("Welcome to Terminal Scrabble!\n")
    players = [input("Enter Player 1 name: ").strip() or "Player1",
               input("Enter Player 2 name: ").strip() or "Player2"]
    game = ScrabbleGame(players)
    game.start_game()

    while not game.game_over:
        player = game._current_player()
        print("\n" + "=" * 60)
        print(f"It is {player}'s turn. Current score: {game.scores[player]}")
        print_board(game.board)
        print(f"Your rack: {game.get_player_rack(player)}")
        print("Commands: play <WORD> <ROW> <COL> <H|V> | pass | quit")
        cmd = input("> ").strip().split()
        if not cmd:
            continue
        action = cmd[0].lower()

        try:
            if action == "play" and len(cmd) == 5:
                word, r, c, d = cmd[1], int(cmd[2]), int(cmd[3]), cmd[4].lower()
                d = "horizontal" if d.startswith("h") else "vertical"
                gained = game.play_word(word, r, c, d)
                print(f"Word accepted! You gained {gained} points.")
                game.switch_turn()
            elif action == "pass":
                print(f"{player} passes the turn.")
                game.switch_turn()
            elif action == "quit":
                break
            else:
                print("Invalid command or parameters.")
        except Exception as e:
            print(f"Error: {e}")

    # Game over summary
    scores = game.end_game()
    print("\nGame Over! Final Scores:")
    for p, s in scores.items():
        print(f"{p}: {s} points")
    winner = max(scores, key=scores.get)
    print(f"Winner: {winner}! Congratulations!")


if __name__ == "__main__":
    main()
