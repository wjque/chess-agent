"""Agent factory and exports."""

from __future__ import annotations

from agents.mcts_agent import MCTSAgent
from agents.minimax_agent import MinimaxAgent
from agents.random_agent import RandomAgent

AGENT_NAMES = {"random", "minimax", "mcts"}


def create_agent(
    name: str,
    side: str,
    seed: int = 20260405,
    use_opening_book: bool = True,
    use_endgame_book: bool = True,
    mcts_exploration: float = 1.0,
    mcts_rollout_depth: int = 48,
    mcts_draw_threshold: int = 80,
    mcts_rollout_check_samples: int = 8,
):
    lname = name.lower()
    if lname == "random":
        return RandomAgent(
            side=side,
            seed=seed,
            use_opening_book=use_opening_book,
            use_endgame_book=use_endgame_book,
        )
    if lname == "minimax":
        return MinimaxAgent(
            side=side,
            seed=seed,
            use_opening_book=use_opening_book,
            use_endgame_book=use_endgame_book,
        )
    if lname == "mcts":
        return MCTSAgent(
            side=side,
            seed=seed,
            use_opening_book=use_opening_book,
            use_endgame_book=use_endgame_book,
            exploration=mcts_exploration,
            rollout_depth=mcts_rollout_depth,
            draw_eval_threshold=mcts_draw_threshold,
            rollout_check_samples=mcts_rollout_check_samples,
        )
    raise ValueError(f"Unknown agent: {name}")


__all__ = [
    "AGENT_NAMES",
    "create_agent",
    "RandomAgent",
    "MinimaxAgent",
    "MCTSAgent",
]
