"""Heuristic evaluation for Xiangqi search."""

from __future__ import annotations

from chess.constants import BLACK, PIECE_VALUES, RED
from chess import rules


MATE_SCORE = 1_000_000


def _mirror_row_for_black(row: int) -> int:
    return 9 - row


def _piece_square_bonus(piece: str, row: int, col: int) -> int:
    p = piece.upper()
    is_red = piece.isupper()
    rr = row if is_red else _mirror_row_for_black(row)

    # Modest handcrafted tables to keep eval cheap.
    if p == "P":
        advance = (9 - rr) * 6
        center = 6 - abs(4 - col) * 2
        crossed_river = 14 if rr <= 4 else 0
        return advance + center + crossed_river
    if p == "N":
        return 12 - (abs(4 - col) + abs(5 - rr)) * 2
    if p == "R":
        return 8 - abs(4 - col)
    if p == "C":
        return 10 - abs(4 - col)
    if p == "B":
        return 4 if rr in (5, 7, 9) else 0
    if p == "A":
        return 3 if col == 4 else 0
    if p == "K":
        # Encourage king to stay central inside palace.
        return 6 - abs(4 - col) * 2
    return 0


def evaluate_state(state: "GameState") -> int:
    """
    Returns score from RED's perspective:
    positive -> RED better, negative -> BLACK better.
    """
    material = 0
    positional = 0
    for r, row in enumerate(state.board):
        for c, piece in enumerate(row):
            if piece == ".":
                continue
            sign = 1 if piece.isupper() else -1
            material += sign * PIECE_VALUES[piece]
            positional += sign * _piece_square_bonus(piece, r, c)

    # Mobility with pseudo-legal moves is a cheap proxy.
    red_mob = len(rules.generate_pseudo_legal_moves(state, side=RED))
    black_mob = len(rules.generate_pseudo_legal_moves(state, side=BLACK))
    mobility = (red_mob - black_mob) * 2

    king_safety = 0
    if state.is_in_check(RED):
        king_safety -= 120
    if state.is_in_check(BLACK):
        king_safety += 120

    pressure = 0
    if state.side_to_move == RED and state.is_in_check(BLACK):
        pressure += 30
    if state.side_to_move == BLACK and state.is_in_check(RED):
        pressure -= 30

    return material + positional + mobility + king_safety + pressure
