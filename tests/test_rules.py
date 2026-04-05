from __future__ import annotations

import unittest

from chess.move import Move
from chess.state import GameState


def _set_piece(rows: list[str], row: int, col: int, piece: str) -> list[str]:
    row_chars = list(rows[row])
    row_chars[col] = piece
    rows[row] = "".join(row_chars)
    return rows


def _empty_board_with_kings() -> list[str]:
    rows = ["........." for _ in range(10)]
    rows = _set_piece(rows, 0, 4, "k")
    rows = _set_piece(rows, 9, 4, "K")
    rows = _set_piece(rows, 4, 4, "P")  # avoid accidental flying-general checks
    return rows


class RuleEngineTests(unittest.TestCase):
    def test_horse_leg_block(self) -> None:
        rows = _empty_board_with_kings()
        rows = _set_piece(rows, 9, 1, "N")
        rows = _set_piece(rows, 8, 1, "P")  # horse leg blocked
        rows = _set_piece(rows, 9, 2, "P")
        state = GameState.from_rows(rows, side_to_move="r")
        pseudo = state.generate_pseudo_legal_moves()
        horse_moves = [m for m in pseudo if (m.from_row, m.from_col) == (9, 1)]
        self.assertEqual(horse_moves, [])

    def test_cannon_needs_screen_for_capture(self) -> None:
        rows = _empty_board_with_kings()
        rows = _set_piece(rows, 5, 4, "C")
        rows = _set_piece(rows, 4, 4, "P")  # screen
        rows = _set_piece(rows, 2, 4, "r")
        state = GameState.from_rows(rows, side_to_move="r")
        pseudo = state.generate_pseudo_legal_moves()
        cannon_captures = [
            m
            for m in pseudo
            if (m.from_row, m.from_col) == (5, 4) and (m.to_row, m.to_col) == (2, 4)
        ]
        self.assertEqual(len(cannon_captures), 1)

    def test_elephant_cannot_cross_river(self) -> None:
        rows = _empty_board_with_kings()
        rows = _set_piece(rows, 5, 2, "B")
        rows = _set_piece(rows, 4, 4, ".")
        state = GameState.from_rows(rows, side_to_move="r")
        pseudo = state.generate_pseudo_legal_moves()
        elephant_targets = {
            (m.to_row, m.to_col) for m in pseudo if (m.from_row, m.from_col) == (5, 2)
        }
        self.assertNotIn((3, 4), elephant_targets)
        self.assertIn((7, 0), elephant_targets)
        self.assertIn((7, 4), elephant_targets)

    def test_cannot_expose_flying_general(self) -> None:
        rows = ["........." for _ in range(10)]
        rows = _set_piece(rows, 0, 4, "k")
        rows = _set_piece(rows, 9, 4, "K")
        rows = _set_piece(rows, 5, 4, "R")
        state = GameState.from_rows(rows, side_to_move="r")
        legal = state.generate_legal_moves()
        illegal = Move(5, 4, 5, 3).key()
        legal_keys = {m.key() for m in legal}
        self.assertNotIn(illegal, legal_keys)

    def test_terminal_when_no_legal_moves(self) -> None:
        rows = ["........." for _ in range(10)]
        rows = _set_piece(rows, 0, 4, "k")
        rows = _set_piece(rows, 9, 4, "K")
        rows = _set_piece(rows, 1, 4, "R")
        rows = _set_piece(rows, 2, 4, "R")
        rows = _set_piece(rows, 1, 3, "R")
        rows = _set_piece(rows, 1, 5, "R")
        state = GameState.from_rows(rows, side_to_move="b")
        terminal, result = state.is_terminal()
        self.assertTrue(terminal)
        self.assertEqual(result["winner"], "r")


if __name__ == "__main__":
    unittest.main()
