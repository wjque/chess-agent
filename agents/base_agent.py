"""Base agent protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from chess.move import Move
from chess.state import GameState


class Agent(Protocol):
    side: str
    name: str

    def select_move(self, state: GameState, time_limit_ms: int) -> Optional[Move]:
        ...


@dataclass
class AgentConfig:
    side: str
    time_limit_ms: int = 1500
