"""Random baseline agent."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from chess.move import Move
from chess.state import GameState
from chess.opening import OpeningBook


@dataclass
class RandomAgent:
    side: str
    name: str = "random"
    seed: int = 20260405

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        self._book = OpeningBook(seed=self.seed + 7)

    def select_move(self, state: GameState, time_limit_ms: int = 1500) -> Optional[Move]:
        opening_move = self._book.query_opening(state)
        if opening_move is not None:
            return opening_move
        legal_moves = state.generate_legal_moves()
        if not legal_moves:
            return None
        return self._rng.choice(legal_moves)
