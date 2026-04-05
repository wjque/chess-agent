"""Endgame book and lightweight tablebase-style policies."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from chess.constants import BLACK, EMPTY, PIECE_VALUES, RED
from chess.evaluate import evaluate_state
from chess.move import Move
from chess.state import GameState
from chess import rules


def _other_side(side: str) -> str:
    return BLACK if side == RED else RED


def _is_side_piece(piece: str, side: str) -> bool:
    if piece == EMPTY:
        return False
    if side == RED:
        return piece.isupper()
    return piece.islower()


def _find_move_by_text(legal_moves: list[Move], text: str) -> Optional[Move]:
    for mv in legal_moves:
        if mv.as_uci() == text:
            return mv
    return None


@dataclass(frozen=True)
class EndgameEntry:
    moves: tuple[str, ...]
    winner: Optional[str]
    dtm: Optional[int]
    note: str


class EndgameBook:
    """
    Practical endgame helper:
    1) Exact position hits from local JSON (tablebase-style entries)
    2) Small-material fallback policy for <= `max_piece_count` pieces
    """

    def __init__(self, path: Optional[Path] = None, seed: int = 20260405) -> None:
        if path is None:
            path = Path(__file__).with_name("endgames.json")
        self._rng = random.Random(seed)
        self._exact: dict[str, EndgameEntry] = {}
        self.max_piece_count = 6
        self._load(path)

    def _load(self, path: Path) -> None:
        self._exact = {}
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return

        max_piece_count = raw.get("max_piece_count")
        if isinstance(max_piece_count, int) and max_piece_count >= 2:
            self.max_piece_count = max_piece_count

        entries = raw.get("exact_positions", [])
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            side = entry.get("side_to_move")
            rows = entry.get("rows")
            moves = entry.get("best_moves")
            if side not in (RED, BLACK):
                continue
            if not isinstance(rows, list) or len(rows) != 10 or not all(
                isinstance(row, str) and len(row) == 9 for row in rows
            ):
                continue
            if not isinstance(moves, list):
                continue
            clean_moves = tuple(mv for mv in moves if isinstance(mv, str))
            if not clean_moves:
                continue
            try:
                state = GameState.from_rows(rows=rows, side_to_move=side)
            except ValueError:
                continue

            winner = entry.get("winner")
            if winner not in (RED, BLACK, None):
                winner = None
            dtm = entry.get("dtm")
            note = entry.get("note", "")
            key = state.position_key()
            self._exact[key] = EndgameEntry(
                moves=clean_moves,
                winner=winner,
                dtm=dtm if isinstance(dtm, int) and dtm >= 0 else None,
                note=note if isinstance(note, str) else "",
            )

    def query_endgame(self, state: GameState) -> Optional[Move]:
        legal = state.generate_legal_moves()
        if not legal:
            return None

        exact = self._exact.get(state.position_key())
        if exact is not None:
            candidates = [_find_move_by_text(legal, text) for text in exact.moves]
            candidates = [mv for mv in candidates if mv is not None]
            if candidates:
                return self._rng.choice(candidates)

        if not self._is_small_material_endgame(state):
            return None
        return self._policy_move(state, legal)

    def _is_small_material_endgame(self, state: GameState) -> bool:
        pieces = 0
        for row in state.board:
            for piece in row:
                if piece != EMPTY:
                    pieces += 1
        return pieces <= self.max_piece_count

    def _policy_move(self, state: GameState, legal_moves: list[Move]) -> Optional[Move]:
        scorer = _EndgamePolicyScorer(state)
        best_score = -10**18
        best_moves: list[Move] = []
        for mv in legal_moves:
            score = scorer.score(mv)
            if score > best_score:
                best_score = score
                best_moves = [mv]
            elif score == best_score:
                best_moves.append(mv)
        if not best_moves:
            return None
        return self._rng.choice(best_moves)


class _EndgamePolicyScorer:
    def __init__(self, state: GameState) -> None:
        self._state = state
        self._mover = state.side_to_move
        self._opponent = _other_side(self._mover)

    def score(self, move: Move) -> int:
        next_state = self._state.apply_move(move)
        terminal, result = next_state.is_terminal()
        if terminal:
            winner = result.get("winner") if result else None
            if winner == self._mover:
                return 1_000_000_000
            if winner is None:
                return 0
            return -1_000_000_000

        score = 0
        if move.captured_piece is not None:
            score += 30_000 + PIECE_VALUES.get(move.captured_piece, 0) * 40

        # Keep consistency with global eval sign, but make it mover-centric.
        static_eval = evaluate_state(next_state)
        score += static_eval if self._mover == RED else -static_eval

        # In endgames, forcing checks and shrinking enemy mobility matters.
        if next_state.is_in_check(next_state.side_to_move):
            score += 6_000

        enemy_legal = next_state.generate_legal_moves()
        score -= len(enemy_legal) * 180

        # Encourage approaching the enemy king with active pieces.
        enemy_king = rules.locate_king(next_state.board, self._opponent)
        if enemy_king is not None:
            dist = abs(move.to_row - enemy_king[0]) + abs(move.to_col - enemy_king[1])
            score += max(0, 14 - dist) * 140
            if move.moved_piece is not None and move.moved_piece.upper() == "K":
                score += max(0, 7 - dist) * 30

        # Penalize repeating exact position immediately to reduce pointless shuffles.
        if next_state.position_key() == self._state.position_key():
            score -= 8_000
        return score
