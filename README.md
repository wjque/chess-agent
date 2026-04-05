# Xiangqi Search Agent

This project implements a playable Xiangqi (Chinese chess) engine and agents:

- Full core rule framework on a 9x10 board
- `Random` baseline agent
- `Minimax` agent (iterative deepening + alpha-beta + move ordering + TT)
- `MCTS` agent (UCT + heuristic rollouts)
- PyQt6 GUI for human-vs-AI / AI-vs-AI play
- CLI batch mode for agent comparison experiments

## Features

### Rule Engine

- Board representation: 9x10 with Xiangqi piece set
- Piece movement and captures:
  - horse-leg blocking
  - elephant eye blocking + no river crossing
  - cannon screen rule
  - king/advisor palace limits
  - flying-general legality handling
- Illegal move filtering by self-check
- Terminal checks:
  - king captured
  - no legal moves (checkmate or stalemate-style loss in this project)

### Repetition (Practical Course-Level Implementation)

- Long-check loss detection (`long_check`)
- Long-chase loss detection (`long_chase`)

The implementation uses move history + repeated position keys and practical
continuous-pattern checks to keep behavior reproducible in coursework settings.

### Search

- Shared evaluation:
  - material
  - piece-square bonuses
  - mobility
  - king safety
  - check pressure
- Minimax:
  - iterative deepening
  - alpha-beta pruning
  - transposition table
  - killer/history heuristics
- MCTS:
  - UCT selection
  - rollout depth limit
  - capture/check-biased rollout move policy

### Opening Book

- Local JSON opening lines in `chess/openings.json`
- Book lookup by position key
- Falls back to search when no match

## Project Structure

- `chess/` core engine modules (`state`, `rules`, `judge`, `evaluate`, `opening`, etc.)
- `agents/` agent implementations
- `play.py` unified GUI/CLI entry point
- `tests/` unit tests for rules, repetition, and search agents

## Requirements

- Python 3.10+
- Optional for GUI: `PyQt6`

Install GUI dependency:

```bash
pip install PyQt6
```

## Usage

### GUI (default)

```bash
python play.py --mode gui --red-agent human --black-agent minimax --time-limit-ms 1500
```

Other GUI examples:

```bash
python play.py --mode gui --red-agent human --black-agent mcts
python play.py --mode gui --red-agent minimax --black-agent mcts
```

### CLI Self-Play / Comparison

```bash
python play.py --mode cli --red-agent minimax --black-agent mcts --games 50 --time-limit-ms 1500
```

Useful options:

- `--max-plies 300` move cap per game
- `--seed 20260405` reproducible runs
- `--mcts-exploration 1.0` UCT exploration constant
- `--mcts-rollout-depth 48` rollout depth cap per simulation
- `--mcts-draw-threshold 80` eval threshold for rollout cutoff-as-draw
- `--mcts-rollout-check-samples 8` sampled moves for check-biased rollout

## Tests

Run all tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Coverage includes:

- key movement constraints (horse leg, cannon screen, elephant river)
- flying-general legality
- terminal judgment
- long-check / long-chase detection
- legal-move output for all three agents
