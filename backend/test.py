from .scrabble import *


def test_scrabble():
    word_list = WordList.load_word_list()

    p1 = Player()
    p2 = Player()
    b = Board(players=[p1, p2], tile_bag=create_tile_bag())
    b.initialize(word_list)

    # 1. Invalid: First move does NOT cover center square
    p1.word_bank.hand = [Tile(letter="H"), Tile(letter="I")]
    try:
        b.make_move([Tile(letter="H", x=3, y=3), Tile(letter="I", x=4, y=3)], p1)
        assert False, "Should have raised error for first move not on center"
    except ValueError as e:
        assert "center square" in str(e)

    # 2. Valid: First move covers center (horizontal)
    p1.word_bank.hand = [
        Tile(letter="H"),
        Tile(letter="E"),
        Tile(letter="L"),
        Tile(letter="L"),
        Tile(letter="O"),
    ]
    b.make_move(
        [
            Tile(letter="H", x=5, y=7),
            Tile(letter="E", x=6, y=7),
            Tile(letter="L", x=7, y=7),  # center
            Tile(letter="L", x=8, y=7),
            Tile(letter="O", x=9, y=7),
        ],
        p1,
    )
    # After this move, p1's hand should be empty or refilled, and "HELLO" on the board
    assert b.board[7][5].letter == "H"
    assert b.board[7][9].letter == "O"
    assert b.turn == 1

    # 3. Invalid: Try to play on top of an existing tile
    b.current_player.word_bank.hand = [Tile(letter="I"), Tile(letter="T")]
    try:
        b.make_move(
            [
                Tile(letter="I", x=7, y=7),  # already occupied by 'L'
                Tile(letter="T", x=10, y=7),
            ],
            b.current_player,
        )
        assert False, "Should have raised error for overlapping tile"
    except ValueError as e:
        assert "occupied square" in str(e)

    # 4. Invalid: Move uses a tile NOT in hand
    b.current_player.word_bank.hand = [Tile(letter="A"), Tile(letter="B")]
    try:
        b.make_move(
            [Tile(letter="T", x=10, y=7), Tile(letter="O", x=11, y=7)], b.current_player
        )
        assert False, "Should have raised error for missing tile"
    except ValueError as e:
        assert "don't have the tile" in str(e)

    # 5. Invalid: Move is NOT straight (diagonal)
    b.current_player.word_bank.hand = [Tile(letter="N"), Tile(letter="O")]
    try:
        b.make_move(
            [Tile(letter="N", x=2, y=3), Tile(letter="O", x=3, y=4)], b.current_player
        )
        assert False, "Should have raised error for not a straight line"
    except ValueError as e:
        assert "same column or row" in str(e)

    # 6. Valid: Second player plays vertical word that touches an existing tile
    b.current_player.word_bank.hand = [Tile(letter="I"), Tile(letter="T")]
    b.make_move(
        [Tile(letter="I", x=7, y=8), Tile(letter="T", x=7, y=9)], b.current_player
    )
    # Now there should be 'I' at (7,8) and 'T' at (7,9)
    assert b.board[8][7].letter == "I"
    assert b.board[9][7].letter == "T"
    assert b.turn == 2

    # 7. Invalid: Second turn, word does NOT touch any tile
    b.current_player.word_bank.hand = [Tile(letter="O"), Tile(letter="N")]
    try:
        b.make_move(
            [Tile(letter="O", x=1, y=1), Tile(letter="N", x=2, y=1)], b.current_player
        )
        assert False, "Should have raised error for disconnected move"
    except ValueError as e:
        assert "touch an existing tile" in str(e)

    # 8. Invalid: Move forms a word not in dictionary
    b.current_player.word_bank.hand = [Tile(letter="X"), Tile(letter="Y")]
    try:
        b.make_move(
            [Tile(letter="X", x=6, y=8), Tile(letter="Y", x=6, y=9)], b.current_player
        )
        assert False, "Should have raised error for invalid dictionary word"
    except ValueError as e:
        assert "not in the dictionary" in str(e)

    # 9. Valid: Play a two-letter word
    b.current_player.word_bank.hand = [Tile(letter="T"), Tile(letter="O")]
    b.make_move(
        [
            Tile(letter="T", x=9, y=6),
            Tile(letter="O", x=9, y=7),  # touches existing 'O'
        ],
        b.current_player,
    )
    # Confirm letters were placed
    assert b.board[6][9].letter == "T"
    assert b.board[7][9].letter == "O"
    assert b.turn == 3

    b.tile_bag = []
    b.current_player = b.players[0]
    b.turn = 10
    b.players[0].word_bank.hand = [Tile(letter="O"), Tile(letter="N")]
    b.players[1].word_bank.hand = [Tile(letter="B"), Tile(letter="C")]
    try:
        b.make_move(
            [Tile(letter="O", x=9, y=8), Tile(letter="N", x=9, y=9)], b.current_player
        )
    except Exception as e:
        assert False, f"Unexpected error: {e}"
    # Check game is over
    assert b.is_game_over, "Game should be over"
    # Player 1's hand should be empty
    assert len(b.players[0].word_bank.hand) == 0
    # Player 2's hand not empty
    assert len(b.players[1].word_bank.hand) == 2
    # Player 2's score penalized, Player 1 gets their points

    previous_score = b.players[1].score

    penalty = sum(t.points for t in b.players[1].word_bank.hand)
    penalty = sum(t.points for t in b.players[1].word_bank.hand)
    assert b.players[1].score == previous_score - penalty

    assert b.players[0].score >= penalty

    p1 = Player()
    p2 = Player()
    b = Board(players=[p1, p2], tile_bag=create_tile_bag())
    b.initialize(word_list)

    # Manually set hands so no one can play
    b.players[0].word_bank.hand = []
    b.players[1].word_bank.hand = []

    # Simulate 4 passes (2 passes each for 2 players)
    for i in range(4):
        current_player = b.current_player
        b.make_move([], current_player)
        if i < 3:
            assert not b.is_game_over, "Game should not be over yet"
        else:
            assert b.is_game_over, "Game should be over after 4 consecutive passes"

    p1 = Player()
    p2 = Player()
    b = Board(players=[p1, p2], tile_bag=create_tile_bag())
    b.initialize(word_list)

    b.make_move([], p1)  # Pass turn

    b.current_player.word_bank.hand = [Tile(letter="H"), Tile(letter="I")]
    try:
        b.make_move([Tile(letter="H", x=3, y=3), Tile(letter="I", x=4, y=3)], b.current_player)
        assert False, "Should have raised error for first move not on center after pass"
    except ValueError as e:
        assert "center square" in str(e)

    b.current_player.word_bank.hand = [
        Tile(letter="H"),
        Tile(letter="E"),
        Tile(letter="L"),
        Tile(letter="L"),
        Tile(letter="O"),
    ]
    b.make_move(
        [
            Tile(letter="H", x=5, y=7),
            Tile(letter="E", x=6, y=7),
            Tile(letter="L", x=7, y=7),  # center!
            Tile(letter="L", x=8, y=7),
            Tile(letter="O", x=9, y=7),
        ],
        b.current_player,
    )
    assert b.board[7][7].letter == "L"
    assert b.turn == 2
    
    print("All asserts passed for Scrabble tests.")


if __name__ == "__main__":
    test_scrabble()
