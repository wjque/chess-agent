"""象棋局面状态表示"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from chess.constants import (
    BLACK,
    COLS,
    EMPTY,
    INITIAL_BOARD,
    PIECE_VALUES,
    RED,
    ROWS,
)
from chess.hashing import DEFAULT_HASHER
from chess.move import Move
from chess import rules


@dataclass(frozen=True)
class MoveRecord:
    """用于长打/长将判定的历史走子记录"""

    position_hash: str
    move: Move
    is_check: bool
    moved_piece: str
    target_piece: Optional[str]
    side_moved: str
    chase_target: Optional[tuple[int, int]]


@dataclass(frozen=True)
class GameState:
    """不可变游戏状态对象，负责派发规则与裁判逻辑"""

    board: tuple[str, ...]
    side_to_move: str
    history: tuple[MoveRecord, ...] = ()

    @classmethod
    def initial(cls) -> GameState:
        return cls(board=INITIAL_BOARD, side_to_move=RED, history=())

    @classmethod
    def from_rows(cls, rows: list[str], side_to_move: str = RED) -> GameState:
        if len(rows) != ROWS:
            raise ValueError("board rows must be 10")
        for row in rows:
            if len(row) != COLS:
                raise ValueError("board columns must be 9")
        return cls(board=tuple(rows), side_to_move=side_to_move, history=())

    def position_hash(self) -> int:
        return DEFAULT_HASHER.position_hash(self.board, self.side_to_move)

    def position_key(self) -> str:
        return DEFAULT_HASHER.position_key(self.board, self.side_to_move)

    def generate_legal_moves(self) -> list[Move]:
        return rules.generate_legal_moves(self)

    def generate_pseudo_legal_moves(self, captures_only: bool = False) -> list[Move]:
        return rules.generate_pseudo_legal_moves(self, captures_only=captures_only)

    def is_in_check(self, side: Optional[str] = None) -> bool:
        target_side = self.side_to_move if side is None else side
        return rules.is_in_check(self, target_side)

    def apply_move(self, move: Move) -> GameState:
        fr, fc = move.from_row, move.from_col
        tr, tc = move.to_row, move.to_col
        if not (0 <= fr < ROWS and 0 <= fc < COLS and 0 <= tr < ROWS and 0 <= tc < COLS):
            raise ValueError(f"Move out of board: {move}")
        moved_piece = self.board[fr][fc]
        if moved_piece == EMPTY:
            raise ValueError(f"No piece at source square: {move}")
        moved_side = RED if moved_piece.isupper() else BLACK
        if moved_side != self.side_to_move:
            raise ValueError(f"Wrong side to move for move: {move}")

        board_list = [list(row) for row in self.board]
        captured_piece = board_list[tr][tc]
        board_list[tr][tc] = moved_piece
        board_list[fr][fc] = EMPTY
        new_board = tuple("".join(row) for row in board_list)
        next_side = BLACK if self.side_to_move == RED else RED

        base_next_state = GameState(new_board, next_side, self.history)
        gives_check = base_next_state.is_in_check(next_side)

        # 追打标记，判定长捉 / 长将
        target_piece: Optional[str] = None
        chase_target: Optional[tuple[int, int]] = None
        if captured_piece != EMPTY:
            target_piece = captured_piece
        else:
            targets = rules.attacked_targets_by_piece(
                base_next_state,
                tr,
                tc,
                moved_side,
            )
            if targets:
                targets.sort(key=lambda x: PIECE_VALUES.get(x[2], 0), reverse=True)
                chase_target = (targets[0][0], targets[0][1])
                target_piece = targets[0][2]

        normalized_move = Move(
            from_row=fr,
            from_col=fc,
            to_row=tr,
            to_col=tc,
            moved_piece=moved_piece,
            captured_piece=captured_piece if captured_piece != EMPTY else None,
        )
        record = MoveRecord(
            position_hash=base_next_state.position_key(),
            move=normalized_move,
            is_check=gives_check,
            moved_piece=moved_piece,
            target_piece=target_piece,
            side_moved=moved_side,
            chase_target=chase_target,
        )
        new_history = self.history + (record,)
        return GameState(new_board, next_side, new_history)

    def evaluate_repetition_violation(self) -> Optional[dict]:
        from chess.judge import evaluate_repetition_violation

        return evaluate_repetition_violation(self)

    def is_terminal(self) -> tuple[bool, Optional[dict]]:
        from chess.judge import is_terminal

        return is_terminal(self)
