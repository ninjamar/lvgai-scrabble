import asyncio
import time

import redis.asyncio as aredis

from .scrabble import Board, Player, WordList, create_tile_bag

rd = aredis.Redis(host="ai.thewcl.com", port=6379, db=4, password="atmega328")


async def main():
    word_list = WordList.load_word_list()

    b = Board(players=[Player(), Player()], tile_bag=create_tile_bag())
    b.initialize(word_list)

    now = time.time()
    await b.save_to_redis()
    old = time.time() - now
    print("Save:", old)

    now = time.time()
    c = await b.load_from_redis(word_list=word_list)
    old = time.time() - now
    print("Load:", old)

    assert c == b


if __name__ == "__main__":
    asyncio.run(main())
