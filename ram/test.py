from scrabble import *

def print_turn_info(b):
    print_board_from_save_dict(b.to_save_dict())
    for idx, player in enumerate(b.players):
        hand = "".join([t.letter for t in player.word_bank.hand])
        print(f"Player {idx+1} hand: {hand}")
    print(f"Current turn: Player {b.players.index(b.current_player)+1}")
    print("-"*40)

if __name__ == "__main__":
    word_list = WordList.load_word_list()
    p1 = Player()
    p2 = Player()
    b = Board(players=[p1, p2], tile_bag=create_tile_bag())
    b.initialize(word_list)

    print("---- Initial State ----")
    print_turn_info(b)

    # 1. Invalid: First move does NOT cover center square
    print("Test 1: Invalid first move not on center")
    p1.word_bank.hand = [Tile(letter='H'), Tile(letter='I')]
    try:
        b.make_move([
            Tile(letter='H', x=3, y=3),
            Tile(letter='I', x=4, y=3)
        ], p1)
    except ValueError as e:
        print("Expected error:", e)
    print_turn_info(b)

    # 2. Valid: First move covers center (horizontal)
    print("Test 2: Valid first move covers center")
    p1.word_bank.hand = [Tile(letter='H'), Tile(letter='E'), Tile(letter='L'), Tile(letter='L'), Tile(letter='O')]
    try:
        b.make_move([
            Tile(letter='H', x=5, y=7),
            Tile(letter='E', x=6, y=7),
            Tile(letter='L', x=7, y=7),  # center
            Tile(letter='L', x=8, y=7),
            Tile(letter='O', x=9, y=7)
        ], p1)
    except Exception as e:
        print("Unexpected error:", e)
    print_turn_info(b)

    # 3. Invalid: Try to play on top of an existing tile
    print("Test 3: Invalid overlapping tile")
    b.current_player.word_bank.hand = [Tile(letter='I'), Tile(letter='T')]
    try:
        b.make_move([
            Tile(letter='I', x=7, y=7),  # already occupied by 'L'
            Tile(letter='T', x=10, y=7)
        ], b.current_player)
    except ValueError as e:
        print("Expected error:", e)
    print_turn_info(b)

    # 4. Invalid: Move uses a tile NOT in hand
    print("Test 4: Tile not in hand")
    b.current_player.word_bank.hand = [Tile(letter='A'), Tile(letter='B')]
    try:
        b.make_move([
            Tile(letter='T', x=10, y=7),
            Tile(letter='O', x=11, y=7)
        ], b.current_player)
    except ValueError as e:
        print("Expected error:", e)
    print_turn_info(b)

    # 5. Invalid: Move is NOT straight (diagonal)
    print("Test 5: Not a straight line")
    b.current_player.word_bank.hand = [Tile(letter='N'), Tile(letter='O')]
    try:
        b.make_move([
            Tile(letter='N', x=2, y=3),
            Tile(letter='O', x=3, y=4)
        ], b.current_player)
    except ValueError as e:
        print("Expected error:", e)
    print_turn_info(b)

    # 6. Valid: Second player plays vertical word that touches an existing tile
    print("Test 6: Valid move touching existing word")
    b.current_player.word_bank.hand = [Tile(letter='I'), Tile(letter='T')]
    try:
        b.make_move([
            Tile(letter='I', x=7, y=8),
            Tile(letter='T', x=7, y=9)
        ], b.current_player)
    except Exception as e:
        print("Unexpected error:", e)
    print_turn_info(b)

    # 7. Invalid: Second turn, word does NOT touch any tile
    print("Test 7: Second turn disconnected move")
    b.current_player.word_bank.hand = [Tile(letter='O'), Tile(letter='N')]
    try:
        b.make_move([
            Tile(letter='O', x=1, y=1),
            Tile(letter='N', x=2, y=1)
        ], b.current_player)
    except ValueError as e:
        print("Expected error:", e)
    print_turn_info(b)

    # 8. Invalid: Move forms a word not in dictionary
    print("Test 8: Formed word not in dictionary")
    b.current_player.word_bank.hand = [Tile(letter='X'), Tile(letter='Y')]
    try:
        b.make_move([
            Tile(letter='X', x=6, y=8),
            Tile(letter='Y', x=6, y=9)
        ], b.current_player)
    except ValueError as e:
        print("Expected error:", e)
    print_turn_info(b)

    # 9. Valid: Play a two-letter word
    print("Test 9: Play valid two-letter word")
    b.current_player.word_bank.hand = [Tile(letter='T'), Tile(letter='O')]
    try:
        b.make_move([
            Tile(letter='T', x=9, y=6),
            Tile(letter='O', x=9, y=7)  # touches existing 'O'
        ], b.current_player)
    except Exception as e:
        print("Unexpected error:", e)
    print_turn_info(b)

    print("All step-by-step test cases executed.")
