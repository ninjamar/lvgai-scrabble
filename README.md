# Scrabble

## Running

Make sure `.env` has OpenAI proxy auth. If this isn't provided, the `--ai MODEL` flag won't work.

Inside `client.py`, make sure that `WS_BASE_URL` has a websocket echo server.

Also make sure the Redis DB supports JSON.


Run the server:
```bash
uvicorn backend.server:app --reload
```

Run the users:
```
python -m frontend.client --reset NUM_PLAYERS
python -m frontend.client --player N
```

Run the UI:
```bash
python -m frontend.ui
```