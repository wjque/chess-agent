"""象棋规则引擎：走法生成与将军检测"""

from __future__ import annotations

from typing import Optional

from chess.constants import (
    BLACK,
    BLACK_PALACE_ROWS,
    BLACK_PIECES,
    COLS,
    EMPTY,
    PALACE_COLS,
    RED,
    RED_PALACE_ROWS,
    RED_PIECES,
    ROWS,
)
from chess.move import Move


def in_bounds(row: int, col: int) -> bool:
    return 0 <= row < ROWS and 0 <= col < COLS


def other_side(side: str) -> str:
    return BLACK if side == RED else RED


def side_of_piece(piece: str) -> Optional[str]:
    if piece in RED_PIECES:
        return RED
    if piece in BLACK_PIECES:
        return BLACK
    return None


def is_enemy_piece(piece: str, side: str) -> bool:
    if piece == EMPTY:
        return False
    pside = side_of_piece(piece)
    return pside is not None and pside != side


def is_friend_piece(piece: str, side: str) -> bool:
    if piece == EMPTY:
        return False
    return side_of_piece(piece) == side


def in_palace(row: int, col: int, side: str) -> bool:
    if col not in PALACE_COLS:
        return False
    if side == RED:
        return row in RED_PALACE_ROWS
    return row in BLACK_PALACE_ROWS


def locate_king(board: tuple[str, ...], side: str) -> Optional[tuple[int, int]]:
    target = "K" if side == RED else "k"
    for r, row in enumerate(board):
        for c, piece in enumerate(row):
            if piece == target:
                return (r, c)
    return None


def _append_move(
    moves: list[Move],
    board: tuple[str, ...],
    fr: int,
    fc: int,
    tr: int,
    tc: int,
    side: str,
    captures_only: bool,
) -> None:
    if not in_bounds(tr, tc):
        return
    moved_piece = board[fr][fc]
    target = board[tr][tc]
    if is_friend_piece(target, side):
        return
    if captures_only and target == EMPTY:
        return
    if not captures_only and target != EMPTY and not is_enemy_piece(target, side):
        return
    if target != EMPTY and not is_enemy_piece(target, side):
        return
    moves.append(
        Move(
            from_row=fr,
            from_col=fc,
            to_row=tr,
            to_col=tc,
            moved_piece=moved_piece,
            captured_piece=target if target != EMPTY else None,
        )
    )


def _generate_king_moves(
    board: tuple[str, ...], row: int, col: int, side: str, captures_only: bool
) -> list[Move]:
    moves: list[Move] = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr = row + dr
        nc = col + dc
        if not in_bounds(nr, nc):
            continue
        if not in_palace(nr, nc, side):
            continue
        _append_move(moves, board, row, col, nr, nc, side, captures_only)

    # 将帅照面（飞将）时可直接吃对方将帅
    step = -1 if side == RED else 1
    r = row + step
    while 0 <= r < ROWS:
        p = board[r][col]
        if p != EMPTY:
            enemy_king = "k" if side == RED else "K"
            if p == enemy_king:
                _append_move(moves, board, row, col, r, col, side, captures_only)
            break
        r += step
    return moves


def _generate_advisor_moves(
    board: tuple[str, ...], row: int, col: int, side: str, captures_only: bool
) -> list[Move]:
    moves: list[Move] = []
    for dr, dc in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        nr = row + dr
        nc = col + dc
        if in_bounds(nr, nc) and in_palace(nr, nc, side):
            _append_move(moves, board, row, col, nr, nc, side, captures_only)
    return moves


def _generate_elephant_moves(
    board: tuple[str, ...], row: int, col: int, side: str, captures_only: bool
) -> list[Move]:
    moves: list[Move] = []
    for dr, dc in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
        nr = row + dr
        nc = col + dc
        mr = row + dr // 2
        mc = col + dc // 2
        if not in_bounds(nr, nc):
            continue
        if board[mr][mc] != EMPTY:
            continue
        if side == RED and nr < 5:
            continue
        if side == BLACK and nr > 4:
            continue
        _append_move(moves, board, row, col, nr, nc, side, captures_only)
    return moves


def _generate_horse_moves(
    board: tuple[str, ...], row: int, col: int, side: str, captures_only: bool
) -> list[Move]:
    moves: list[Move] = []
    patterns = (
        (-1, 0, -2, -1),
        (-1, 0, -2, 1),
        (1, 0, 2, -1),
        (1, 0, 2, 1),
        (0, -1, -1, -2),
        (0, -1, 1, -2),
        (0, 1, -1, 2),
        (0, 1, 1, 2),
    )
    for ldr, ldc, dr, dc in patterns:
        leg_r = row + ldr
        leg_c = col + ldc
        if not in_bounds(leg_r, leg_c):
            continue
        if board[leg_r][leg_c] != EMPTY:
            continue
        nr = row + dr
        nc = col + dc
        _append_move(moves, board, row, col, nr, nc, side, captures_only)
    return moves


def _generate_rook_moves(
    board: tuple[str, ...], row: int, col: int, side: str, captures_only: bool
) -> list[Move]:
    moves: list[Move] = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r = row + dr
        c = col + dc
        while in_bounds(r, c):
            p = board[r][c]
            if p == EMPTY:
                if not captures_only:
                    _append_move(moves, board, row, col, r, c, side, captures_only)
                r += dr
                c += dc
                continue
            if is_enemy_piece(p, side):
                _append_move(moves, board, row, col, r, c, side, captures_only)
            break
    return moves


def _generate_cannon_moves(
    board: tuple[str, ...], row: int, col: int, side: str, captures_only: bool
) -> list[Move]:
    moves: list[Move] = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r = row + dr
        c = col + dc
        # 炮架前方的连续空格：仅可平移，不吃子
        while in_bounds(r, c) and board[r][c] == EMPTY:
            if not captures_only:
                _append_move(moves, board, row, col, r, c, side, captures_only)
            r += dr
            c += dc
        # 越过恰好一个炮架后，遇到的第一个棋子若为敌子则可吃
        r += dr
        c += dc
        while in_bounds(r, c):
            p = board[r][c]
            if p != EMPTY:
                if is_enemy_piece(p, side):
                    _append_move(moves, board, row, col, r, c, side, captures_only)
                break
            r += dr
            c += dc
    return moves


def _generate_pawn_moves(
    board: tuple[str, ...], row: int, col: int, side: str, captures_only: bool
) -> list[Move]:
    moves: list[Move] = []
    directions: list[tuple[int, int]] = []
    if side == RED:
        directions.append((-1, 0))
        if row <= 4:
            directions.extend(((0, -1), (0, 1)))
    else:
        directions.append((1, 0))
        if row >= 5:
            directions.extend(((0, -1), (0, 1)))
    for dr, dc in directions:
        nr = row + dr
        nc = col + dc
        _append_move(moves, board, row, col, nr, nc, side, captures_only)
    return moves


def generate_pseudo_legal_moves(
    state: "GameState", side: Optional[str] = None, captures_only: bool = False
) -> list[Move]:
    side = state.side_to_move if side is None else side
    board = state.board
    moves: list[Move] = []
    for r in range(ROWS):
        for c in range(COLS):
            piece = board[r][c]
            if piece == EMPTY or side_of_piece(piece) != side:
                continue
            p = piece.upper()
            if p == "K":
                moves.extend(_generate_king_moves(board, r, c, side, captures_only))
            elif p == "A":
                moves.extend(_generate_advisor_moves(board, r, c, side, captures_only))
            elif p == "B":
                moves.extend(_generate_elephant_moves(board, r, c, side, captures_only))
            elif p == "N":
                moves.extend(_generate_horse_moves(board, r, c, side, captures_only))
            elif p == "R":
                moves.extend(_generate_rook_moves(board, r, c, side, captures_only))
            elif p == "C":
                moves.extend(_generate_cannon_moves(board, r, c, side, captures_only))
            elif p == "P":
                moves.extend(_generate_pawn_moves(board, r, c, side, captures_only))
    return moves


def is_square_attacked(state: "GameState", row: int, col: int, by_side: str) -> bool:
    for move in generate_pseudo_legal_moves(state, side=by_side, captures_only=True):
        if move.to_row == row and move.to_col == col:
            return True
    return False


def is_in_check(state: "GameState", side: str) -> bool:
    king_pos = locate_king(state.board, side)
    if king_pos is None:
        return True
    return is_square_attacked(state, king_pos[0], king_pos[1], by_side=other_side(side))


def generate_legal_moves(state: "GameState", side: Optional[str] = None) -> list[Move]:
    side = state.side_to_move if side is None else side
    legal: list[Move] = []
    for move in generate_pseudo_legal_moves(state, side=side, captures_only=False):
        next_state = state.apply_move(move)
        if not is_in_check(next_state, side):
            legal.append(move)
    return legal


def attacked_targets_by_piece(
    state: "GameState", row: int, col: int, side: str
) -> list[tuple[int, int, str]]:
    targets: list[tuple[int, int, str]] = []
    for mv in generate_pseudo_legal_moves(state, side=side, captures_only=True):
        if mv.from_row != row or mv.from_col != col:
            continue
        captured = state.board[mv.to_row][mv.to_col]
        if captured != EMPTY:
            targets.append((mv.to_row, mv.to_col, captured))
    return targets
