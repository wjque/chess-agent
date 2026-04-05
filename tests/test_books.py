from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agents.mcts_agent import MCTSAgent
from agents.minimax_agent import MinimaxAgent
from chess.endgame import EndgameBook
from chess.opening import OpeningBook
from chess.state import GameState


class OpeningEndgameBookTests(unittest.TestCase):
    def test_opening_book_supports_structured_schema(self) -> None:
        payload = {
            "lines": [
                {"moves": ["7174", "2724"], "weight": 3},
                {"moves": ["9172", "0122"], "weight": 1},
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "openings.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            book = OpeningBook(path=path, seed=1)
            mv = book.query_opening(GameState.initial())
            self.assertIsNotNone(mv)
            self.assertIn(mv.as_uci(), {"7174", "9172"})

    def test_endgame_book_exact_entry_hit(self) -> None:
        rows = [
            "....k....",
            "....R....",
            ".........",
            ".........",
            ".........",
            ".........",
            ".........",
            ".........",
            ".........",
            "....K....",
        ]
        state = GameState.from_rows(rows, side_to_move="r")
        book = EndgameBook(seed=1)
        mv = book.query_endgame(state)
        self.assertIsNotNone(mv)
        self.assertEqual(mv.as_uci(), "1404")

    def test_endgame_book_policy_finds_immediate_win(self) -> None:
        rows = [
            "....k....",
            ".........",
            "....R....",
            ".........",
            ".........",
            ".........",
            ".........",
            ".........",
            ".........",
            "....K....",
        ]
        state = GameState.from_rows(rows, side_to_move="r")
        book = EndgameBook(seed=1)
        mv = book.query_endgame(state)
        self.assertIsNotNone(mv)
        self.assertEqual(mv.as_uci(), "2404")

    def test_minimax_and_mcts_use_endgame_book(self) -> None:
        rows = [
            "....k....",
            ".........",
            "....R....",
            ".........",
            ".........",
            ".........",
            ".........",
            ".........",
            ".........",
            "....K....",
        ]
        state = GameState.from_rows(rows, side_to_move="r")
        minimax = MinimaxAgent(
            side="r",
            max_depth=2,
            seed=1,
            use_opening_book=False,
            use_endgame_book=True,
        )
        mcts = MCTSAgent(
            side="r",
            seed=1,
            use_opening_book=False,
            use_endgame_book=True,
        )
        mv1 = minimax.select_move(state, time_limit_ms=50)
        mv2 = mcts.select_move(state, time_limit_ms=50)
        self.assertIsNotNone(mv1)
        self.assertIsNotNone(mv2)
        self.assertEqual(mv1.as_uci(), "2404")
        self.assertEqual(mv2.as_uci(), "2404")


if __name__ == "__main__":
    unittest.main()
