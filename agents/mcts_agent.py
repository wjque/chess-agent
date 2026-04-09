"""采用 UCT 策略的 MCTS 智能体"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from chess.constants import BLACK, PIECE_VALUES, RED
from chess.endgame import EndgameBook
from chess.evaluate import evaluate_state
from chess.move import Move
from chess.opening import OpeningBook
from chess.state import GameState


@dataclass
class MCTSNode:
    state: GameState
    parent: Optional["MCTSNode"] = None
    move: Optional[Move] = None
    children: list["MCTSNode"] = field(default_factory=list)
    untried_moves: list[Move] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0

    def best_uct_child(self, exploration: float) -> "MCTSNode":
        # 选择 UCT 分数最高的子节点：利用 + 探索
        best = None
        best_score = -10**18
        for child in self.children:
            if child.visits == 0:
                score = float("inf")
            else:
                exploit = child.value / child.visits
                explore = exploration * math.sqrt(math.log(self.visits + 1) / child.visits)
                score = exploit + explore
            if score > best_score:
                best_score = score
                best = child
        if best is None:
            raise RuntimeError("best_uct_child called with no children")
        return best


@dataclass
class MCTSAgent:
    side: str
    name: str = "mcts"
    exploration: float = 1.0
    rollout_depth: int = 48
    draw_eval_threshold: int = 80
    rollout_check_samples: int = 8
    seed: int = 20260405
    use_opening_book: bool = True
    use_endgame_book: bool = True

    def __post_init__(self) -> None:
        # 固定随机源，确保实验可复现
        self._rng = random.Random(self.seed)
        self._opening_book = OpeningBook(seed=self.seed + 37) if self.use_opening_book else None
        self._endgame_book = EndgameBook(seed=self.seed + 41) if self.use_endgame_book else None

    def select_move(self, state: GameState, time_limit_ms: int = 1500) -> Optional[Move]:
        # 与其他智能体一致：优先使用开局库和残局库
        if self._opening_book is not None:
            opening_move = self._opening_book.query_opening(state)
            if opening_move is not None:
                return opening_move
        if self._endgame_book is not None:
            endgame_move = self._endgame_book.query_endgame(state)
            if endgame_move is not None:
                return endgame_move

        legal_moves = state.generate_legal_moves()
        if not legal_moves:
            return None

        deadline = time.monotonic() + max(0.05, time_limit_ms / 1000.0)
        root = MCTSNode(state=state, untried_moves=legal_moves.copy())
        while time.monotonic() < deadline:
            node = root
            sim_state = state

            # 1) Selection：沿 UCT 最优路径向下走到叶子附近
            while not node.untried_moves and node.children:
                node = node.best_uct_child(self.exploration)
                if node.move is None:
                    break
                sim_state = sim_state.apply_move(node.move)

            # 2) Expansion：从未尝试着法中扩展一个新节点
            if node.untried_moves:
                mv = self._rng.choice(node.untried_moves)
                node.untried_moves.remove(mv)
                sim_state = sim_state.apply_move(mv)
                child = MCTSNode(
                    state=sim_state,
                    parent=node,
                    move=mv,
                    untried_moves=sim_state.generate_legal_moves(),
                )
                node.children.append(child)
                node = child

            # 3) Simulation：执行快速 rollout 估值
            winner = self._rollout(sim_state, deadline)

            # 4) Backpropagation：将结果回传至根节点
            while node is not None:
                node.visits += 1
                # 节点价值按“刚走子的一方”记分，轮换回合时可直接最大化
                player_just_moved = BLACK if node.state.side_to_move == RED else RED 
                if winner is None:
                    node.value += 0.5
                elif winner == player_just_moved:
                    node.value += 1.0
                node = node.parent

        if not root.children:
            return self._rng.choice(legal_moves)
        return max(
            root.children,
            key=lambda c: (c.visits, c.value / c.visits if c.visits else 0.0),
        ).move

    def _rollout(self, state: GameState, deadline: float) -> Optional[str]:
        sim = state
        for _ in range(self.rollout_depth):
            if time.monotonic() >= deadline:
                break
            terminal, result = sim.is_terminal()
            if terminal:
                return result.get("winner") if result else None
            legal = sim.generate_legal_moves()
            if not legal:
                terminal, result = sim.is_terminal()
                return result.get("winner") if result else None
            move = self._select_rollout_move(sim, legal)
            sim = sim.apply_move(move)

        # 深度/时间截断时，回退到静态评估符号判断优势方
        score = evaluate_state(sim)
        if abs(score) < self.draw_eval_threshold:
            return None
        return RED if score > 0 else BLACK

    def _select_rollout_move(self, state: GameState, moves: list[Move]) -> Move:
        # 吃子优先：先抓高价值子，提升 rollout 信号强度
        captures = [m for m in moves if m.captured_piece is not None]
        if captures:
            captures.sort(key=lambda m: PIECE_VALUES.get(m.captured_piece or ".", 0), reverse=True)
            top_value = PIECE_VALUES.get(captures[0].captured_piece or ".", 0)
            top_choices = [
                m
                for m in captures
                if PIECE_VALUES.get(m.captured_piece or ".", 0) == top_value
            ]
            return self._rng.choice(top_choices)

        # 其次偏好将军着法
        checking_moves: list[Move] = []
        sample_size = min(self.rollout_check_samples, len(moves))
        sampled = self._rng.sample(moves, sample_size)
        for m in sampled:
            ns = state.apply_move(m)
            if ns.is_in_check(ns.side_to_move):
                checking_moves.append(m)
        if checking_moves:
            return self._rng.choice(checking_moves)

        return self._rng.choice(moves)
