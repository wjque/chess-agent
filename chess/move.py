"""Move representation for Xiangqi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


Coordinate = Tuple[int, int]


@dataclass(frozen=True)
class Move:
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    moved_piece: Optional[str] = None
    captured_piece: Optional[str] = None

    @property
    def from_pos(self) -> Coordinate:
        return (self.from_row, self.from_col)

    @property
    def to_pos(self) -> Coordinate:
        return (self.to_row, self.to_col)

    def as_uci(self) -> str:
        # Compact internal notation: frfctrtc
        return f"{self.from_row}{self.from_col}{self.to_row}{self.to_col}"

    @classmethod
    def from_uci(cls, text: str) -> "Move":
        if len(text) != 4 or not text.isdigit():
            raise ValueError(f"Bad move notation: {text}")
        return cls(
            from_row=int(text[0]),
            from_col=int(text[1]),
            to_row=int(text[2]),
            to_col=int(text[3]),
        )

    def key(self) -> tuple[int, int, int, int]:
        return (self.from_row, self.from_col, self.to_row, self.to_col)

    def __str__(self) -> str:
        return self.as_uci()
