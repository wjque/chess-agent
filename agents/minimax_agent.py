"""Alpha-beta minimax agent (iterative deepening)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from chess.constants import PIECE_VALUES, RED
from chess.evaluate import MATE_SCORE, evaluate_state
from chess.move import Move
from chess.opening import OpeningBook
from chess.state import GameState


class SearchTimeout(Exception):
    pass


@dataclass
class TTEntry:
    depth: int
    score: int
    flag: str  # EXACT / LOWER / UPPER
    best_move: Optional[str]


@dataclass
class MinimaxAgent:
    side: str
    name: str = "minimax"
    max_depth: int = 5
    seed: int = 20260405

    def __post_init__(self) -> None:
        self._tt: dict[str, TTEntry] = {}
        self._history: dict[str, int] = {}
        self._killer: dict[int, list[str]] = {}
        self._book = OpeningBook(seed=self.seed + 17)

    def select_move(self, state: GameState, time_limit_ms: int = 1500) -> Optional[Move]:
        opening_move = self._book.query_opening(state)
        if opening_move is not None:
            return opening_move

        legal_moves = state.generate_legal_moves()
        if not legal_moves:
            return None

        deadline = time.monotonic() + max(0.05, time_limit_ms / 1000.0)
        best_move = legal_moves[0]
        best_score = -10**18

        for depth in range(1, self.max_depth + 1):
            try:
                score, move = self._negamax_root(state, depth, deadline)
            except SearchTimeout:
                break
            if move is not None:
                best_move = move
                best_score = score
        _ = best_score  # retained for optional debug hooks
        return best_move

    def _check_timeout(self, deadline: float) -> None:
        if time.monotonic() >= deadline:
            raise SearchTimeout

    def _negamax_root(
        self, state: GameState, depth: int, deadline: float
    ) -> tuple[int, Optional[Move]]:
        alpha = -10**18
        beta = 10**18
        best_score = -10**18
        best_move: Optional[Move] = None

        legal_moves = state.generate_legal_moves()
        ordered = self._order_moves(state, legal_moves, depth, tt_move_key=None)
        for move in ordered:
            self._check_timeout(deadline)
            child = state.apply_move(move)
            score = -self._negamax(
                child,
                depth - 1,
                -beta,
                -alpha,
                ply=1,
                deadline=deadline,
            )
            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score

        return best_score, best_move

    def _negamax(
        self,
        state: GameState,
        depth: int,
        alpha: int,
        beta: int,
        ply: int,
        deadline: float,
    ) -> int:
        self._check_timeout(deadline)
        alpha_orig = alpha

        terminal, result = state.is_terminal()
        if terminal:
            winner = result.get("winner") if result else None
            if winner is None:
                return 0
            if winner == state.side_to_move:
                return MATE_SCORE - ply
            return -MATE_SCORE + ply

        if depth == 0:
            return self._static_eval_from_current_side(state)

        key = state.position_key()
        tt_entry = self._tt.get(key)
        tt_move_key: Optional[str] = None
        if tt_entry is not None:
            tt_move_key = tt_entry.best_move
            if tt_entry.depth >= depth:
                if tt_entry.flag == "EXACT":
                    return tt_entry.score
                if tt_entry.flag == "LOWER":
                    alpha = max(alpha, tt_entry.score)
                elif tt_entry.flag == "UPPER":
                    beta = min(beta, tt_entry.score)
                if alpha >= beta:
                    return tt_entry.score

        best_score = -10**18
        best_move_key: Optional[str] = None
        legal_moves = state.generate_legal_moves()
        if not legal_moves:
            return -MATE_SCORE + ply

        ordered = self._order_moves(state, legal_moves, ply, tt_move_key)
        for move in ordered:
            child = state.apply_move(move)
            score = -self._negamax(child, depth - 1, -beta, -alpha, ply + 1, deadline)
            if score > best_score:
                best_score = score
                best_move_key = move.as_uci()
            alpha = max(alpha, score)
            if alpha >= beta:
                self._on_beta_cutoff(move, ply, depth)
                break

        flag = "EXACT"
        if best_score <= alpha_orig:
            flag = "UPPER"
        elif best_score >= beta:
            flag = "LOWER"
        self._tt[key] = TTEntry(depth=depth, score=best_score, flag=flag, best_move=best_move_key)
        return best_score

    def _static_eval_from_current_side(self, state: GameState) -> int:
        eval_red = evaluate_state(state)
        return eval_red if state.side_to_move == RED else -eval_red

    def _on_beta_cutoff(self, move: Move, ply: int, depth: int) -> None:
        if move.captured_piece is None:
            killers = self._killer.setdefault(ply, [])
            mv_key = move.as_uci()
            if mv_key not in killers:
                killers.insert(0, mv_key)
                del killers[2:]
            self._history[mv_key] = self._history.get(mv_key, 0) + depth * depth

    def _order_moves(
        self, state: GameState, moves: list[Move], ply: int, tt_move_key: Optional[str]
    ) -> list[Move]:
        def move_score(mv: Move) -> int:
            score = 0
            mv_key = mv.as_uci()
            if tt_move_key is not None and mv_key == tt_move_key:
                score += 5_000_000
            if mv.captured_piece is not None:
                captured_val = PIECE_VALUES.get(mv.captured_piece, 0)
                score += 1_000_000 + captured_val
            killers = self._killer.get(ply, [])
            if mv_key in killers:
                score += 100_000
            score += self._history.get(mv_key, 0)
            # Lightweight check-priority.
            next_state = state.apply_move(mv)
            if next_state.is_in_check(next_state.side_to_move):
                score += 50_000
            return score

        return sorted(moves, key=move_score, reverse=True)

