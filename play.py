"""Entry point for Xiangqi GUI and CLI play/evaluation."""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional

from agents import AGENT_NAMES, create_agent
from chess.constants import BLACK, COLS, EMPTY, PIECE_DISPLAY, RED, ROWS
from chess.move import Move
from chess.state import GameState


HUMAN = "human"


def side_name(side: str) -> str:
    return "Red" if side == RED else "Black"


def piece_side(piece: str) -> Optional[str]:
    if piece == EMPTY:
        return None
    return RED if piece.isupper() else BLACK


def format_result(result: Optional[dict]) -> str:
    if not result:
        return "Unknown"
    winner = result.get("winner")
    reason = result.get("reason", "unknown")
    winner_text = "Draw" if winner is None else side_name(winner)
    return f"Winner: {winner_text} ({reason})"


@dataclass
class CliGameStats:
    winner: Optional[str]
    reason: str
    plies: int
    red_times: list[float]
    black_times: list[float]


def run_cli_game(
    red_agent_name: str,
    black_agent_name: str,
    time_limit_ms: int,
    max_plies: int,
    seed: int,
    use_opening_book: bool = True,
    use_endgame_book: bool = True,
    mcts_exploration: float = 1.0,
    mcts_rollout_depth: int = 48,
    mcts_draw_threshold: int = 80,
    mcts_rollout_check_samples: int = 8,
) -> CliGameStats:
    state = GameState.initial()
    red_agent = create_agent(
        red_agent_name,
        RED,
        seed=seed + 1,
        use_opening_book=use_opening_book,
        use_endgame_book=use_endgame_book,
        mcts_exploration=mcts_exploration,
        mcts_rollout_depth=mcts_rollout_depth,
        mcts_draw_threshold=mcts_draw_threshold,
        mcts_rollout_check_samples=mcts_rollout_check_samples,
    )
    black_agent = create_agent(
        black_agent_name,
        BLACK,
        seed=seed + 2,
        use_opening_book=use_opening_book,
        use_endgame_book=use_endgame_book,
        mcts_exploration=mcts_exploration,
        mcts_rollout_depth=mcts_rollout_depth,
        mcts_draw_threshold=mcts_draw_threshold,
        mcts_rollout_check_samples=mcts_rollout_check_samples,
    )
    red_times: list[float] = []
    black_times: list[float] = []

    for ply in range(max_plies):
        terminal, result = state.is_terminal()
        if terminal:
            return CliGameStats(
                winner=result.get("winner") if result else None,
                reason=result.get("reason", "terminal") if result else "terminal",
                plies=ply,
                red_times=red_times,
                black_times=black_times,
            )

        side = state.side_to_move
        agent = red_agent if side == RED else black_agent
        t0 = time.perf_counter()
        move = agent.select_move(state, time_limit_ms=time_limit_ms)
        elapsed = (time.perf_counter() - t0) * 1000.0
        if side == RED:
            red_times.append(elapsed)
        else:
            black_times.append(elapsed)

        if move is None:
            # Defensive fallback if agent cannot return move.
            result = {"winner": BLACK if side == RED else RED, "reason": "agent_no_move"}
            return CliGameStats(
                winner=result["winner"],
                reason=result["reason"],
                plies=ply,
                red_times=red_times,
                black_times=black_times,
            )
        state = state.apply_move(move)

    return CliGameStats(
        winner=None,
        reason="move_limit",
        plies=max_plies,
        red_times=red_times,
        black_times=black_times,
    )


def run_cli(args: argparse.Namespace) -> int:
    games = args.games
    results: list[CliGameStats] = []
    for idx in range(games):
        stats = run_cli_game(
            red_agent_name=args.red_agent,
            black_agent_name=args.black_agent,
            time_limit_ms=args.time_limit_ms,
            max_plies=args.max_plies,
            seed=args.seed + idx * 97,
            use_opening_book=not args.disable_opening_book,
            use_endgame_book=not args.disable_endgame_book,
            mcts_exploration=args.mcts_exploration,
            mcts_rollout_depth=args.mcts_rollout_depth,
            mcts_draw_threshold=args.mcts_draw_threshold,
            mcts_rollout_check_samples=args.mcts_rollout_check_samples,
        )
        results.append(stats)
        print(
            f"Game {idx + 1:02d}/{games}: winner={stats.winner}, "
            f"reason={stats.reason}, plies={stats.plies}"
        )

    red_wins = sum(1 for r in results if r.winner == RED)
    black_wins = sum(1 for r in results if r.winner == BLACK)
    draws = games - red_wins - black_wins
    all_red_times = [t for r in results for t in r.red_times]
    all_black_times = [t for r in results for t in r.black_times]
    print("\n=== Summary ===")
    print(f"Red agent  ({args.red_agent}) wins : {red_wins}")
    print(f"Black agent({args.black_agent}) wins: {black_wins}")
    print(f"Draws                           : {draws}")
    if all_red_times:
        print(f"Avg red move time (ms)          : {statistics.mean(all_red_times):.2f}")
    if all_black_times:
        print(f"Avg black move time (ms)        : {statistics.mean(all_black_times):.2f}")
    return 0


def run_gui(args: argparse.Namespace) -> int:
    try:
        from PyQt6.QtCore import QTimer, Qt
        from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
        from PyQt6.QtWidgets import (
            QApplication,
            QHBoxLayout,
            QLabel,
            QMainWindow,
            QMessageBox,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )
    except ImportError:
        print("PyQt6 is required for GUI mode. Install with: pip install PyQt6")
        return 1

    class BoardWidget(QWidget):
        margin = 32
        cell = 56

        def __init__(self, owner: "XiangqiWindow") -> None:
            super().__init__()
            self.owner = owner
            self.setMinimumSize(self.margin * 2 + self.cell * 8 + 1, self.margin * 2 + self.cell * 9 + 1)

        def _board_to_view(self, row: int, col: int) -> tuple[int, int]:
            if self.owner.bottom_side == RED:
                return row, col
            return ROWS - 1 - row, COLS - 1 - col

        def _view_to_board(self, row: int, col: int) -> tuple[int, int]:
            if self.owner.bottom_side == RED:
                return row, col
            return ROWS - 1 - row, COLS - 1 - col

        def paintEvent(self, event) -> None:  # noqa: N802
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.fillRect(self.rect(), QColor("#f4d9a8"))
            board = self.owner.state.board

            x0 = self.margin
            y0 = self.margin

            grid_pen = QPen(QColor("#3f2f1e"))
            grid_pen.setWidth(2)
            painter.setPen(grid_pen)
            for c in range(COLS):
                x = x0 + c * self.cell
                painter.drawLine(x, y0, x, y0 + 4 * self.cell)
                painter.drawLine(x, y0 + 5 * self.cell, x, y0 + 9 * self.cell)
            for r in range(ROWS):
                y = y0 + r * self.cell
                painter.drawLine(x0, y, x0 + 8 * self.cell, y)

            # Palace lines.
            painter.drawLine(x0 + 3 * self.cell, y0, x0 + 5 * self.cell, y0 + 2 * self.cell)
            painter.drawLine(x0 + 5 * self.cell, y0, x0 + 3 * self.cell, y0 + 2 * self.cell)
            painter.drawLine(x0 + 3 * self.cell, y0 + 7 * self.cell, x0 + 5 * self.cell, y0 + 9 * self.cell)
            painter.drawLine(x0 + 5 * self.cell, y0 + 7 * self.cell, x0 + 3 * self.cell, y0 + 9 * self.cell)

            # River labels.
            painter.setPen(QPen(QColor("#5d4730")))
            river_font = painter.font()
            river_font.setPointSize(16)
            river_font.setFamily("Microsoft YaHei UI")
            painter.setFont(river_font)
            painter.drawText(x0 + self.cell * 1, y0 + self.cell * 4 + 38, "楚河")
            painter.drawText(x0 + self.cell * 5, y0 + self.cell * 4 + 38, "汉界")

            # Highlights.
            if self.owner.selected is not None:
                sr, sc = self.owner.selected
                vr, vc = self._board_to_view(sr, sc)
                self._draw_marker(painter, vr, vc, QColor(255, 210, 50, 180))
            for tr, tc in self.owner.legal_targets:
                vr, vc = self._board_to_view(tr, tc)
                self._draw_marker(painter, vr, vc, QColor(50, 170, 255, 160))
            if self.owner.checked_king is not None:
                kr, kc = self.owner.checked_king
                vr, vc = self._board_to_view(kr, kc)
                self._draw_check_ring(painter, vr, vc)

            # Pieces.
            for r in range(ROWS):
                for c in range(COLS):
                    piece = board[r][c]
                    if piece == EMPTY:
                        continue
                    vr, vc = self._board_to_view(r, c)
                    px = x0 + vc * self.cell
                    py = y0 + vr * self.cell
                    is_red = piece.isupper()
                    fill = QColor("#f8eee0") if is_red else QColor("#f0f0f0")
                    text = QColor("#b5301a") if is_red else QColor("#1f1f1f")
                    painter.setBrush(QBrush(fill))
                    painter.setPen(QPen(QColor("#5a4025"), 2))
                    radius = 21
                    painter.drawEllipse(px - radius, py - radius, radius * 2, radius * 2)
                    piece_font = painter.font()
                    piece_font.setPointSize(14)
                    piece_font.setBold(True)
                    piece_font.setFamily("Microsoft YaHei UI")
                    painter.setFont(piece_font)
                    painter.setPen(QPen(text))
                    painter.drawText(
                        px - radius,
                        py - radius,
                        radius * 2,
                        radius * 2,
                        int(Qt.AlignmentFlag.AlignCenter),
                        PIECE_DISPLAY[piece],
                    )

        def _draw_marker(self, painter: QPainter, row: int, col: int, color: QColor) -> None:
            x = self.margin + col * self.cell
            y = self.margin + row * self.cell
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color))
            painter.drawEllipse(x - 8, y - 8, 16, 16)

        def _draw_check_ring(self, painter: QPainter, row: int, col: int) -> None:
            x = self.margin + col * self.cell
            y = self.margin + row * self.cell
            pen = QPen(QColor("#cc1f1f"))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(x - 25, y - 25, 50, 50)

        def mousePressEvent(self, event) -> None:  # noqa: N802
            x = event.position().x()
            y = event.position().y()
            col = round((x - self.margin) / self.cell)
            row = round((y - self.margin) / self.cell)
            if not (0 <= row < ROWS and 0 <= col < COLS):
                return
            board_row, board_col = self._view_to_board(row, col)
            self.owner.on_board_click(board_row, board_col)

    class XiangqiWindow(QMainWindow):
        def __init__(
            self,
            red_agent_name: str,
            black_agent_name: str,
            time_limit_ms: int,
            use_opening_book: bool,
            use_endgame_book: bool,
            mcts_exploration: float,
            mcts_rollout_depth: int,
            mcts_draw_threshold: int,
            mcts_rollout_check_samples: int,
        ) -> None:
            super().__init__()
            self.setWindowTitle("Xiangqi Search Agent")
            self.state = GameState.initial()
            self.time_limit_ms = time_limit_ms
            self.red_agent_name = red_agent_name
            self.black_agent_name = black_agent_name
            self.checked_king: Optional[tuple[int, int]] = None
            self.red_agent = (
                None
                if red_agent_name == HUMAN
                else create_agent(
                    red_agent_name,
                    RED,
                    use_opening_book=use_opening_book,
                    use_endgame_book=use_endgame_book,
                    mcts_exploration=mcts_exploration,
                    mcts_rollout_depth=mcts_rollout_depth,
                    mcts_draw_threshold=mcts_draw_threshold,
                    mcts_rollout_check_samples=mcts_rollout_check_samples,
                )
            )
            self.black_agent = (
                None
                if black_agent_name == HUMAN
                else create_agent(
                    black_agent_name,
                    BLACK,
                    use_opening_book=use_opening_book,
                    use_endgame_book=use_endgame_book,
                    mcts_exploration=mcts_exploration,
                    mcts_rollout_depth=mcts_rollout_depth,
                    mcts_draw_threshold=mcts_draw_threshold,
                    mcts_rollout_check_samples=mcts_rollout_check_samples,
                )
            )
            human_side = self.human_side()
            self.bottom_side = human_side if human_side is not None else RED
            self.selected: Optional[tuple[int, int]] = None
            self.legal_targets: set[tuple[int, int]] = set()
            self._state_stack: list[GameState] = [self.state]
            self._executor = ThreadPoolExecutor(max_workers=1)
            self._pending: Optional[tuple[str, Future]] = None
            self._alert_token = 0

            root = QWidget()
            self.setCentralWidget(root)
            layout = QVBoxLayout(root)

            top = QHBoxLayout()
            self.status_label = QLabel("")
            self.alert_label = QLabel("")
            self.alert_label.setStyleSheet("color: #b22222; font-weight: 700;")
            self.undo_button = QPushButton("Undo")
            self.undo_button.clicked.connect(self.on_undo)
            self.restart_button = QPushButton("Restart")
            self.restart_button.clicked.connect(self.on_restart)
            top.addWidget(self.status_label)
            top.addWidget(self.alert_label)
            top.addStretch()
            top.addWidget(self.undo_button)
            top.addWidget(self.restart_button)
            layout.addLayout(top)

            self.board_widget = BoardWidget(self)
            layout.addWidget(self.board_widget)

            self.poll_timer = QTimer()
            self.poll_timer.setInterval(40)
            self.poll_timer.timeout.connect(self.on_poll_ai)

            self.refresh_status()
            self.try_start_ai_turn()

        def closeEvent(self, event) -> None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            super().closeEvent(event)

        def current_agent(self):
            return self.red_agent if self.state.side_to_move == RED else self.black_agent

        def human_side(self) -> Optional[str]:
            red_human = self.red_agent is None
            black_human = self.black_agent is None
            if red_human and not black_human:
                return RED
            if black_human and not red_human:
                return BLACK
            return None

        def on_restart(self) -> None:
            self.state = GameState.initial()
            self.selected = None
            self.legal_targets.clear()
            self._state_stack = [self.state]
            if self._pending is not None:
                _, future = self._pending
                future.cancel()
            self._pending = None
            self.poll_timer.stop()
            self._dismiss_alert()
            self.refresh_status()
            self.board_widget.update()
            self.try_start_ai_turn()

        def refresh_status(self) -> None:
            self.checked_king = self._checked_king_position()
            terminal, result = self.state.is_terminal()
            if terminal:
                self.status_label.setText(f"Game Over, Winner: {format_result(result)}")
                self.undo_button.setEnabled(len(self._state_stack) > 1)
                return
            turn = side_name(self.state.side_to_move)
            side_agent = self.current_agent()
            if side_agent is None:
                status = f"{turn} to move (Human)"
            else:
                status = f"{turn} to move ({side_agent.name}, time limit: {self.time_limit_ms} ms)"
            if self.checked_king is not None:
                status = f"{status} | Check!"
            self.status_label.setText(status)
            self.undo_button.setEnabled(len(self._state_stack) > 1)

        def on_undo(self) -> None:
            if len(self._state_stack) <= 1:
                return
            self.selected = None
            self.legal_targets.clear()
            if self._pending is not None:
                _, future = self._pending
                future.cancel()
            self._pending = None
            self.poll_timer.stop()
            self._dismiss_alert()

            # Single-human games undo back to the human's turn.
            self._pop_one_state()
            if self.human_side() is not None:
                while len(self._state_stack) > 1 and self.current_agent() is not None:
                    self._pop_one_state()

            self.refresh_status()
            self.board_widget.update()
            self.try_start_ai_turn()

        def _pop_one_state(self) -> None:
            if len(self._state_stack) <= 1:
                return
            self._state_stack.pop()
            self.state = self._state_stack[-1]

        def _checked_king_position(self) -> Optional[tuple[int, int]]:
            checked_side = self.state.side_to_move
            if not self.state.is_in_check(checked_side):
                return None
            king_piece = "K" if checked_side == RED else "k"
            for row_idx, row in enumerate(self.state.board):
                col_idx = row.find(king_piece)
                if col_idx != -1:
                    return (row_idx, col_idx)
            return None

        def _dismiss_alert(self) -> None:
            self._alert_token += 1
            self.alert_label.setText("")

        def _show_temporary_alert(self, text: str, duration_ms: int = 1400) -> None:
            self._alert_token += 1
            token = self._alert_token
            self.alert_label.setText(text)
            QTimer.singleShot(duration_ms, lambda: self._clear_alert_if_fresh(token))

        def _clear_alert_if_fresh(self, token: int) -> None:
            if token != self._alert_token:
                return
            self.alert_label.setText("")

        def _apply_move(self, move: Move) -> None:
            self.state = self.state.apply_move(move)
            self._state_stack.append(self.state)
            self.selected = None
            self.legal_targets.clear()
            self.refresh_status()
            terminal, _ = self.state.is_terminal()
            if not terminal and self.checked_king is not None:
                self._show_temporary_alert(f"Check! {side_name(self.state.side_to_move)} king is in danger.")
            self.board_widget.update()
            self._maybe_show_game_over()

        def on_board_click(self, row: int, col: int) -> None:
            if self.current_agent() is not None:
                return
            terminal, _ = self.state.is_terminal()
            if terminal:
                return
            piece = self.state.board[row][col]
            side = self.state.side_to_move

            if self.selected is None:
                if piece != EMPTY and piece_side(piece) == side:
                    self.selected = (row, col)
                    self._refresh_legal_targets()
                    self.board_widget.update()
                return

            if piece != EMPTY and piece_side(piece) == side:
                self.selected = (row, col)
                self._refresh_legal_targets()
                self.board_widget.update()
                return

            if (row, col) not in self.legal_targets:
                return

            move = self._find_selected_move(row, col)
            if move is None:
                return
            self._apply_move(move)
            self.try_start_ai_turn()

        def _find_selected_move(self, row: int, col: int) -> Optional[Move]:
            if self.selected is None:
                return None
            sr, sc = self.selected
            for mv in self.state.generate_legal_moves():
                if mv.from_row == sr and mv.from_col == sc and mv.to_row == row and mv.to_col == col:
                    return mv
            return None

        def _refresh_legal_targets(self) -> None:
            self.legal_targets.clear()
            if self.selected is None:
                return
            sr, sc = self.selected
            for mv in self.state.generate_legal_moves():
                if mv.from_row == sr and mv.from_col == sc:
                    self.legal_targets.add((mv.to_row, mv.to_col))

        def _maybe_show_game_over(self) -> None:
            terminal, result = self.state.is_terminal()
            if not terminal:
                return
            QMessageBox.information(self, "Game Over", format_result(result))

        def try_start_ai_turn(self) -> None:
            if self._pending is not None:
                return
            terminal, _ = self.state.is_terminal()
            if terminal:
                return
            agent = self.current_agent()
            if agent is None:
                return
            token = self.state.position_key()
            future = self._executor.submit(agent.select_move, self.state, self.time_limit_ms)
            self._pending = (token, future)
            self.poll_timer.start()
            self.refresh_status()

        def on_poll_ai(self) -> None:
            if self._pending is None:
                self.poll_timer.stop()
                return
            token, future = self._pending
            if not future.done():
                return
            self._pending = None
            self.poll_timer.stop()

            if self.state.position_key() != token:
                return
            try:
                move = future.result()
            except Exception as exc:
                QMessageBox.critical(self, "AI Error", str(exc))
                return
            if move is None:
                self.refresh_status()
                self._maybe_show_game_over()
                return
            self._apply_move(move)
            self.try_start_ai_turn()

    app = QApplication(sys.argv)
    window = XiangqiWindow(
        args.red_agent,
        args.black_agent,
        args.time_limit_ms,
        not args.disable_opening_book,
        not args.disable_endgame_book,
        args.mcts_exploration,
        args.mcts_rollout_depth,
        args.mcts_draw_threshold,
        args.mcts_rollout_check_samples,
    )
    window.show()
    return app.exec()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Xiangqi search-agent project")
    parser.add_argument("--mode", choices=("gui", "cli"), default="gui")
    parser.add_argument("--time-limit-ms", type=int, default=1500, help="Per-move search budget")
    parser.add_argument("--max-plies", type=int, default=300, help="Move limit for CLI games")
    parser.add_argument("--games", type=int, default=1, help="Number of CLI games")
    parser.add_argument("--seed", type=int, default=20260405)
    parser.add_argument(
        "--disable-opening-book",
        action="store_true",
        help="Disable opening book for all AI agents",
    )
    parser.add_argument(
        "--disable-endgame-book",
        action="store_true",
        help="Disable endgame book/tablebase policy for all AI agents",
    )
    parser.add_argument(
        "--red-agent",
        type=str,
        default="human",
        choices=(HUMAN, *sorted(AGENT_NAMES)),
    )
    parser.add_argument(
        "--black-agent",
        type=str,
        default="minimax",
        choices=(HUMAN, *sorted(AGENT_NAMES)),
    )
    parser.add_argument(
        "--mcts-exploration",
        type=float,
        default=1.0,
        help="UCT exploration constant for MCTS",
    )
    parser.add_argument(
        "--mcts-rollout-depth",
        type=int,
        default=48,
        help="Max rollout plies for each MCTS simulation",
    )
    parser.add_argument(
        "--mcts-draw-threshold",
        type=int,
        default=80,
        help="Static-eval absolute threshold to treat truncated rollout as draw",
    )
    parser.add_argument(
        "--mcts-rollout-check-samples",
        type=int,
        default=8,
        help="How many rollout moves to sample when searching for checking moves",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.mcts_rollout_depth <= 0:
        parser.error("--mcts-rollout-depth must be > 0")
    if args.mcts_rollout_check_samples <= 0:
        parser.error("--mcts-rollout-check-samples must be > 0")
    if args.mcts_draw_threshold < 0:
        parser.error("--mcts-draw-threshold must be >= 0")
    if args.mcts_exploration < 0:
        parser.error("--mcts-exploration must be >= 0")

    if args.mode == "cli":
        if args.red_agent == HUMAN or args.black_agent == HUMAN:
            parser.error("CLI mode requires both sides to be AI agents.")
        return run_cli(args)
    return run_gui(args)


if __name__ == "__main__":
    raise SystemExit(main())
