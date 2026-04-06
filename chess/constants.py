"""象棋引擎使用的常量与静态表"""

from __future__ import annotations

ROWS = 10
COLS = 9
EMPTY = "."

RED = "r"
BLACK = "b"

RED_PIECES = set("KABNRCP")
BLACK_PIECES = set("kabnrcp")

PIECE_VALUES = {
    "K": 10_000,
    "A": 110,
    "B": 110,
    "N": 320,
    "R": 600,
    "C": 350,
    "P": 70,
    "k": 10_000,
    "a": 110,
    "b": 110,
    "n": 320,
    "r": 600,
    "c": 350,
    "p": 70,
}

# 初始棋盘：黑方在上，红方在下
INITIAL_BOARD = (
    "rnbakabnr",
    ".........",
    ".c.....c.",
    "p.p.p.p.p",
    ".........",
    ".........",
    "P.P.P.P.P",
    ".C.....C.",
    ".........",
    "RNBAKABNR",
)

RED_PALACE_ROWS = {7, 8, 9}
BLACK_PALACE_ROWS = {0, 1, 2}
PALACE_COLS = {3, 4, 5}

# 楚河汉界位于第 4 行与第 5 行之间
RIVER_TOP = 4
RIVER_BOTTOM = 5

PIECE_DISPLAY = {
    "K": "帅",
    "A": "仕",
    "B": "相",
    "N": "马",
    "R": "车",
    "C": "炮",
    "P": "兵",
    "k": "将",
    "a": "士",
    "b": "象",
    "n": "马",
    "r": "车",
    "c": "炮",
    "p": "卒",
    EMPTY: "",
}
