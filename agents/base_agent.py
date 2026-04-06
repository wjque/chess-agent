"""智能体基础协议定义"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from chess.move import Move
from chess.state import GameState


class Agent(Protocol):
    """所有对弈智能体都需要实现的最小接口"""

    side: str
    name: str

    def select_move(self, state: GameState, time_limit_ms: int) -> Optional[Move]:
        ...


@dataclass
class AgentConfig:
    """统一的智能体配置容器"""

    side: str
    time_limit_ms: int = 1500
