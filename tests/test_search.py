from __future__ import annotations

import unittest

from agents.mcts_agent import MCTSAgent
from agents.minimax_agent import MinimaxAgent
from agents.random_agent import RandomAgent
from chess.state import GameState


class SearchAgentTests(unittest.TestCase):
    def test_random_returns_legal_move(self) -> None:
        state = GameState.initial()
        agent = RandomAgent(side="r")
        mv = agent.select_move(state, 200)
        legal = {m.key() for m in state.generate_legal_moves()}
        self.assertIsNotNone(mv)
        self.assertIn(mv.key(), legal)

    def test_minimax_returns_legal_move(self) -> None:
        state = GameState.initial()
        agent = MinimaxAgent(side="r", max_depth=3)
        mv = agent.select_move(state, 400)
        legal = {m.key() for m in state.generate_legal_moves()}
        self.assertIsNotNone(mv)
        self.assertIn(mv.key(), legal)

    def test_mcts_returns_legal_move(self) -> None:
        state = GameState.initial()
        agent = MCTSAgent(side="r")
        mv = agent.select_move(state, 300)
        legal = {m.key() for m in state.generate_legal_moves()}
        self.assertIsNotNone(mv)
        self.assertIn(mv.key(), legal)


if __name__ == "__main__":
    unittest.main()
