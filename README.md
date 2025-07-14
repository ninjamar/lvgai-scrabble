# Game Capstone Starter Template

Welcome to the Game Capstone Starter Template! This repository provides a robust foundation for you to build your own multiplayer or AI-driven game as a capstone project. It includes essential tools, a sample game engine, a simple ASCII UI, and clear patterns for extending your project.

## Features

* Modular Python codebase for rapid prototyping
* Async support for networking and game logic
* Redis integration for state management
* Command-line interfaces for flexible control
* Easily customizable for your own game rules and logic

## Getting Started

### Prerequisites

* Python 3.10+
* Redis server (local or remote)
* (Optional) Virtual environment tool (e.g., `venv` or `conda`)

### Installation

1. Clone this repository:

   ```sh
   git clone <your-repo-url>
   cd capstone-to-fork
   ```
2. Set up your environment using [`uv`](https://github.com/astral-sh/uv):

   ```sh
   uv venv
   source .venv/bin/activate
   uv sync
   ```

### Configuration

* Set your Redis password as an environment variable:

  ```sh
  export WCL_REDIS_PASSWORD=your_redis_password
  ```
* Choose a team number (used as Redis DB and WebSocket port suffix).

## Usage

### Running the Game Engine

The game engine script connects to Redis and manages your game state. Example usage:

```sh
python game_engine.py --player x --team 01
```

### Running the ASCII UI

The ASCII UI provides a simple terminal-based interface for interacting with your game:

```sh
python ascii_ui.py --team 01
```

### Running Each Player

Each player connects to the game engine with a unique role:

```sh
python player.py --team 01 --player x
python player.py --team 01 --player o
```

## Project Structure

```
capstone-to-fork/
├── teammate-1/      # Personal dev folder for teammate 1
├── teammate-2/      # Personal dev folder for teammate 2
├── teammate-3/      # Personal dev folder for teammate 3
├── teammate-4/      # Personal dev folder for teammate 4
├── ascii_ui.py      # Terminal UI for the game
├── game_engine.py   # Main game engine logic (if present)
├── game_board.py    # Game board logic and models
├── player.py        # Player logic (extend as needed)
├── README.md        # This file
```

## Customization & Extension

* **Game Logic:** Modify `game_board.py` and `player.py` to implement your own rules.
* **Networking:** Use the async patterns to add new features or endpoints.
* **UI:** Replace or expand `ascii_ui.py` with a graphical or web-based interface.

---

Happy coding and good luck with your game capstone!
