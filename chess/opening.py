"""本地开局库（统一结构化 JSON 格式）"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from chess.move import Move
from chess.state import GameState


@dataclass(frozen=True)
class _OpeningChoice:
    move: str
    weight: int = 1


class OpeningBook:
    def __init__(self, path: Optional[Path] = None, seed: int = 20260405) -> None:
        if path is None:
            path = Path(__file__).with_name("openings.json")
        self._rng = random.Random(seed)
        self._table: dict[str, list[_OpeningChoice]] = {}
        self._load(path)

    def _load(self, path: Path) -> None:
        self._table = {}
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            self._table = {}
            return

        raw_lines = raw.get("lines", [])
        if not isinstance(raw_lines, list):
            return
        lines: list[tuple[list[str], int]] = []
        for line in raw_lines:
            if not isinstance(line, dict):
                continue
            moves = line.get("moves")
            if not isinstance(moves, list):
                continue
            clean_moves = [mv for mv in moves if isinstance(mv, str)]
            if not clean_moves:
                continue
            weight = line.get("weight", 1)
            if not isinstance(weight, int) or weight <= 0:
                weight = 1
            lines.append((clean_moves, weight))

        table: dict[str, list[_OpeningChoice]] = {}
        for line, line_weight in lines:
            state = GameState.initial()
            for move_text in line:
                legal = state.generate_legal_moves()
                move = _find_move_by_text(legal, move_text)
                if move is None:
                    break
                key = state.position_key()
                table.setdefault(key, []).append(
                    _OpeningChoice(move=move.as_uci(), weight=line_weight)
                )
                state = state.apply_move(move)
        self._table = table

    def query_opening(self, state: GameState) -> Optional[Move]:
        candidates = self._table.get(state.position_key(), [])
        if not candidates:
            return None
        total = sum(max(1, c.weight) for c in candidates)
        pick = self._rng.randint(1, total)
        text = candidates[0].move
        rolling = 0
        for choice in candidates:
            rolling += max(1, choice.weight)
            if pick <= rolling:
                text = choice.move
                break
        return _find_move_by_text(state.generate_legal_moves(), text)


def _find_move_by_text(legal_moves: list[Move], text: str) -> Optional[Move]:
    for mv in legal_moves:
        if mv.as_uci() == text:
            return mv
    return None
