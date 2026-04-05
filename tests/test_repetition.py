from __future__ import annotations

import unittest

from chess.move import Move
from chess.state import GameState, MoveRecord


def _base_state(side_to_move: str) -> GameState:
    rows = ["........." for _ in range(10)]
    rows[0] = "....k...."
    rows[9] = "....K...."
    rows[4] = "....P...."
    return GameState.from_rows(rows, side_to_move=side_to_move)


class RepetitionTests(unittest.TestCase):
    def test_long_check_violation(self) -> None:
        state = _base_state(side_to_move="b")
        key = state.position_key()
        red_move = Move(5, 4, 5, 5, moved_piece="R")
        black_move = Move(0, 3, 0, 4, moved_piece="k")
        history = (
            MoveRecord(key, red_move, True, "R", "k", "r", (0, 4)),
            MoveRecord("x1", black_move, False, "k", None, "b", None),
            MoveRecord(key, red_move, True, "R", "k", "r", (0, 4)),
            MoveRecord("x2", black_move, False, "k", None, "b", None),
            MoveRecord(key, red_move, True, "R", "k", "r", (0, 4)),
            MoveRecord("x3", black_move, False, "k", None, "b", None),
            MoveRecord(key, red_move, True, "R", "k", "r", (0, 4)),
        )
        state = GameState(board=state.board, side_to_move=state.side_to_move, history=history)
        violation = state.evaluate_repetition_violation()
        self.assertIsNotNone(violation)
        self.assertEqual(violation["loser"], "r")
        self.assertEqual(violation["reason"], "long_check")

    def test_long_chase_violation(self) -> None:
        state = _base_state(side_to_move="b")
        key = state.position_key()
        red_move = Move(6, 4, 6, 5, moved_piece="R")
        black_move = Move(0, 3, 0, 4, moved_piece="k")
        history = (
            MoveRecord(key, red_move, False, "R", "n", "r", (2, 2)),
            MoveRecord("x1", black_move, False, "k", None, "b", None),
            MoveRecord(key, red_move, False, "R", "n", "r", (2, 2)),
            MoveRecord("x2", black_move, False, "k", None, "b", None),
            MoveRecord(key, red_move, False, "R", "n", "r", (2, 2)),
            MoveRecord("x3", black_move, False, "k", None, "b", None),
            MoveRecord(key, red_move, False, "R", "n", "r", (2, 2)),
        )
        state = GameState(board=state.board, side_to_move=state.side_to_move, history=history)
        violation = state.evaluate_repetition_violation()
        self.assertIsNotNone(violation)
        self.assertEqual(violation["loser"], "r")
        self.assertEqual(violation["reason"], "long_chase")


if __name__ == "__main__":
    unittest.main()
