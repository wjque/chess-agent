"""Small local opening book."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Optional

from chess.move import Move
from chess.state import GameState


class OpeningBook:
    def __init__(self, path: Optional[Path] = None, seed: int = 20260405) -> None:
        if path is None:
            path = Path(__file__).with_name("openings.json")
        self._rng = random.Random(seed)
        self._table: dict[str, list[str]] = {}
        self._load(path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            self._table = {}
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            self._table = {}
            return
        table: dict[str, list[str]] = {}
        for line in data:
            if not isinstance(line, list):
                continue
            state = GameState.initial()
            for move_text in line:
                if not isinstance(move_text, str):
                    break
                legal = state.generate_legal_moves()
                move = _find_move_by_text(legal, move_text)
                if move is None:
                    break
                key = state.position_key()
                table.setdefault(key, []).append(move.as_uci())
                state = state.apply_move(move)
        self._table = table

    def query_opening(self, state: GameState) -> Optional[Move]:
        candidates = self._table.get(state.position_key(), [])
        if not candidates:
            return None
        text = self._rng.choice(candidates)
        return _find_move_by_text(state.generate_legal_moves(), text)


def _find_move_by_text(legal_moves: list[Move], text: str) -> Optional[Move]:
    for mv in legal_moves:
        if mv.as_uci() == text:
            return mv
    return None
