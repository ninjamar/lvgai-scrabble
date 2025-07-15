import redis.asyncio as aredis
import asyncio
from .scrabble import Board, Player, create_tile_bag, WordList

rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")

async def main():
    word_list = WordList.load_word_list()

    b = Board(players=[Player()], tile_bag=create_tile_bag())
    b.initialize(word_list)

    await b.save_to_redis()
    c = await b.load_from_redis(word_list=word_list)

    assert c == b


if __name__ == "__main__":
    asyncio.run(main())