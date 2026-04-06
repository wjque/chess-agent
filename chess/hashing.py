"""置换表与循环判定使用的哈希工具"""

from __future__ import annotations

import random
from typing import Dict, Tuple

from chess.constants import BLACK, RED


PIECES = "KABNRCPkabnrcp"


class Hasher:
    def __init__(self, seed: int = 20260405) -> None:
        rng = random.Random(seed)
        self._zobrist: Dict[Tuple[int, int, str], int] = {}
        for r in range(10):
            for c in range(9):
                for p in PIECES:
                    self._zobrist[(r, c, p)] = rng.getrandbits(64)
        self._side_key = {RED: rng.getrandbits(64), BLACK: rng.getrandbits(64)}

    def position_hash(self, board: tuple[str, ...], side_to_move: str) -> int:
        h = 0
        for r, row in enumerate(board):
            for c, piece in enumerate(row):
                if piece != ".":
                    h ^= self._zobrist[(r, c, piece)]
        h ^= self._side_key[side_to_move]
        return h

    def position_key(self, board: tuple[str, ...], side_to_move: str) -> str:
        # 字符串键更直观，便于调试和开局库索引
        return f"{''.join(board)}:{side_to_move}"


DEFAULT_HASHER = Hasher()
