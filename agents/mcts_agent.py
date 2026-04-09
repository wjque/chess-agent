"""MCTS agent with UCT selection and tactical rollout policy."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Optional

from chess import rules
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
        # Select child by UCT = exploitation + exploration.
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
    rollout_topk: int = 3
    rollout_hanging_penalty_ratio: float = 1.5
    seed: int = 20260405
    use_opening_book: bool = True
    use_endgame_book: bool = True

    def __post_init__(self) -> None:
        # 固定随机数种子保证可复现性
        self._rng = random.Random(self.seed)
        self._opening_book = OpeningBook(seed=self.seed + 37) if self.use_opening_book else None
        self._endgame_book = EndgameBook(seed=self.seed + 41) if self.use_endgame_book else None

    def select_move(self, state: GameState, time_limit_ms: int = 1500) -> Optional[Move]:
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

        # Search time limit
        deadline = time.monotonic() + max(0.05, time_limit_ms / 1000.0)
        root = MCTSNode(state=state, untried_moves=legal_moves.copy())
        while time.monotonic() < deadline:
            node = root
            sim_state = state

            # 1) Selection: follow UCT-best path until expandable node.
            while not node.untried_moves and node.children:
                node = node.best_uct_child(self.exploration)
                if node.move is None:
                    break
                sim_state = sim_state.apply_move(node.move)

            # 2) Expansion: expand one untried move.
            if node.untried_moves:
                # Use tactical rollout policy for expansion 
                # To improve search efficiency
                mv, next_state = self._select_rollout_move(sim_state, node.untried_moves)
                node.untried_moves.remove(mv)
                sim_state = next_state
                child = MCTSNode(
                    state=sim_state,
                    parent=node,
                    move=mv,
                    untried_moves=sim_state.generate_legal_moves(),
                )
                node.children.append(child)
                node = child

            # 3) Simulation: run tactical rollout.
            winner = self._rollout(sim_state, deadline)

            # 4) Backpropagation.
            while node is not None:
                node.visits += 1
                if winner is None:
                    node.value += 0.5
                elif winner == node.state.side_to_move:
                    node.value += 1.0
                node = node.parent

        # If search is too shallow, fallback to tactical policy on root legal moves.
        # This avoids random-looking choices when only a few simulations finished.
        if root.visits <= max(4, len(legal_moves) // 4):
            fallback = self._select_rollout_move(state, legal_moves)
            if fallback is not None:
                return fallback[0]
        best_mcts_move = max(
            root.children,
            key=lambda c: (c.visits, c.value / c.visits if c.visits else 0.0),
        ).move
        if best_mcts_move is None:
            return self._rng.choice(legal_moves)
        return best_mcts_move

    def _rollout(self, state: GameState, deadline: float) -> Optional[str]:
        sim = state
        for _ in range(self.rollout_depth):
            if time.monotonic() >= deadline:
                break
            # Long-chase / Long-check
            violation = sim.evaluate_repetition_violation()
            if violation is not None:
                loser = violation["loser"]
                return BLACK if loser == RED else RED
            # Generate all posible moves
            legal = sim.generate_legal_moves()
            if not legal:
                return BLACK if sim.side_to_move == RED else RED
            _, sim = self._select_rollout_move(sim, legal)

        # Depth/time cutoff: fallback to static evaluation sign.
        score = evaluate_state(sim)
        if abs(score) <= self.draw_eval_threshold:
            return None
        return RED if score > 0 else BLACK

    def _select_rollout_move(
        self,
        state: GameState,
        moves: list[Move],
    ) -> Optional[tuple[Move, GameState]]:
        scored_moves: list[tuple[tuple[int, int, float, int], Move, GameState, bool]] = []
        side = state.side_to_move

        for move in moves:
            next_state = state.apply_move(move)
            
            # 是否能将军
            gives_check = next_state.is_in_check(next_state.side_to_move)
            
            # 待走子状态
            moved_piece = move.moved_piece or state.board[move.from_row][move.from_col]
            moved_piece_value = PIECE_VALUES.get(moved_piece, 0)
            
            # 评估当前状态的危险程度
            escape_score = 0
            if rules.is_square_attacked(
                state,
                move.from_row,
                move.from_col,
                by_side=next_state.side_to_move,
            ):
                escape_score = moved_piece_value
            
            # 评估下一步的攻势
            attacked_targets = rules.attacked_targets_by_piece(
                next_state,
                move.to_row,
                move.to_col,
                side,
            )
            attack_score = 0
            for p in attacked_targets:
                if p[2].upper()=="K":
                    # 将军只用 give_check 控制
                    continue
                attack_score += PIECE_VALUES.get(p[2], 0)
            net_attack = escape_score + 0.3 * attack_score # hard code
            
            # 评估下一步的收益
            capture_score = PIECE_VALUES.get(move.captured_piece or ".", 0)
            net_capture = float(escape_score + capture_score)
            
            # 评估下一步的危险程度
            if rules.is_square_attacked(
                next_state,
                move.to_row,
                move.to_col,
                by_side=next_state.side_to_move,
            ):
                gives_check = False
                net_capture -= self.rollout_hanging_penalty_ratio * moved_piece_value
                net_attack  -= self.rollout_hanging_penalty_ratio * moved_piece_value
            
            net_capture = max(0, net_capture)

            # 分数排序：将军>吃子净价值>估计进攻价值
            score = (
                1 if gives_check else 0,
                net_capture,
                net_attack,
            )
            scored_moves.append((score, move, next_state))

        scored_moves.sort(key=lambda item: item[0], reverse=True)
        topk = max(1, min(self.rollout_topk, len(scored_moves)))
        top_choices = scored_moves[:topk]

        if len(top_choices) == 1:
            _, best_move, best_next_state = top_choices[0]
            return best_move, best_next_state

        # 按照排序顺序给出随机选择的权重
        weights = list(range(topk, 0, -1))
        choice_idx = self._rng.choices(range(topk), weights=weights, k=1)[0]
        _, selected_move, selected_next_state = top_choices[choice_idx]
        return selected_move, selected_next_state
