"""象棋终局与循环着法判定"""

from __future__ import annotations

from typing import Optional

from chess.constants import BLACK, EMPTY, RED
from chess import rules


def _opponent(side: str) -> str:
    return BLACK if side == RED else RED


def evaluate_repetition_violation(state: "GameState") -> Optional[dict]:
    """
    本项目采用的实用循环判负规则：
    - 长将：同一方在自己连续三个回合都形成将军，且该方回合中当前局面重复达到 3 次及以上
    - 长捉：同一方在自己连续三个回合重复追同一目标，且该方回合中当前局面重复达到 3 次及以上
    """
    history = state.history
    if len(history) < 6:
        return None

    current_key = state.position_key()
    offender = history[-1].side_moved
    offender_records = [rec for rec in history if rec.side_moved == offender]
    repeats = sum(
        1
        for rec in history
        if rec.side_moved == offender and rec.position_hash == current_key
    )
    if repeats < 3 or len(offender_records) < 3:
        return None

    last_three = offender_records[-3:]
    if all(rec.is_check for rec in last_three):
        return {"loser": offender, "reason": "long_check"}

    if any(rec.is_check for rec in last_three):
        return None

    if any(rec.move.captured_piece not in (None, EMPTY) for rec in last_three):
        return None

    same_piece = len({rec.moved_piece for rec in last_three}) == 1
    same_target = (
        None not in {rec.chase_target for rec in last_three}
        and len({rec.chase_target for rec in last_three}) == 1
    )
    same_target_piece = (
        None not in {rec.target_piece for rec in last_three}
        and len({rec.target_piece for rec in last_three}) == 1
    )
    if same_piece and same_target and same_target_piece:
        return {"loser": offender, "reason": "long_chase"}
    return None


def is_terminal(state: "GameState") -> tuple[bool, Optional[dict]]:
    red_king = rules.locate_king(state.board, RED)
    black_king = rules.locate_king(state.board, BLACK)
    if red_king is None:
        return True, {"winner": BLACK, "reason": "king_captured"}
    if black_king is None:
        return True, {"winner": RED, "reason": "king_captured"}

    violation = evaluate_repetition_violation(state)
    if violation is not None:
        loser = violation["loser"]
        return True, {"winner": _opponent(loser), "reason": violation["reason"]}

    legal_moves = state.generate_legal_moves()
    if not legal_moves:
        return True, {"winner": _opponent(state.side_to_move), "reason": "no_legal_moves"}

    return False, None
