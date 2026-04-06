"""随机基线智能体"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from chess.endgame import EndgameBook
from chess.move import Move
from chess.state import GameState
from chess.opening import OpeningBook


@dataclass
class RandomAgent:
    side: str
    name: str = "random"
    seed: int = 20260405
    use_opening_book: bool = True
    use_endgame_book: bool = True

    def __post_init__(self) -> None:
        # 统一随机种子，便于实验复现
        self._rng = random.Random(self.seed)
        # 开局库/残局库可按需关闭，方便做消融实验
        self._opening_book = OpeningBook(seed=self.seed + 7) if self.use_opening_book else None
        self._endgame_book = EndgameBook(seed=self.seed + 11) if self.use_endgame_book else None

    def select_move(self, state: GameState, time_limit_ms: int = 1500) -> Optional[Move]:
        # 优先查询开局库，命中则直接出招
        if self._opening_book is not None:
            opening_move = self._opening_book.query_opening(state)
            if opening_move is not None:
                return opening_move
        # 开局库未命中时，尝试残局库策略
        if self._endgame_book is not None:
            endgame_move = self._endgame_book.query_endgame(state)
            if endgame_move is not None:
                return endgame_move
        legal_moves = state.generate_legal_moves()
        if not legal_moves:
            return None
        # 最后退化为纯随机走子
        return self._rng.choice(legal_moves)
