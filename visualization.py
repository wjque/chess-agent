from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

# 设置全局样式
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['axes.unicode_minus'] = False

AGENTS: tuple[str, ...] = ("minimax", "mcts", "random")
AGENT_ORDER = {name: idx for idx, name in enumerate(AGENTS)}
MATCHUPS: tuple[tuple[str, str], ...] = (
    ("minimax", "mcts"),
    ("minimax", "random"),
    ("mcts", "random"),
)
MATCHUPS_SET = {tuple(sorted(pair, key=lambda x: AGENT_ORDER[x])) for pair in MATCHUPS}
FILENAME_RE = re.compile(
    r"^red_(?P<red>\w+)_vs_black_(?P<black>\w+)_(?P<time>\d+)ms_opening_(?P<opening>\w+)\.csv$"
)

# 现代配色方案
COLORS = {
    "win": "#52be80",    # 柔和绿
    "draw": "#bdc3c7",   # 银灰色
    "loss": "#ec7063",   # 柔和红
    "minimax": "#2e86de", # 蓝色
    "mcts": "#e67e22",    # 橙色
    "random": "#27ae60",   # 绿色
    "model-1": "#f2a3b6",
    "model-2": "#2a5c98",
}

@dataclass(frozen=True)
class GameRecord:
    red_agent: str
    black_agent: str
    time_limit_ms: int
    opening_tag: str
    winner: str
    reason: str
    plies: int
    red_total_time_ms: float
    black_total_time_ms: float

def canonical_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b), key=lambda x: AGENT_ORDER.get(x, math.inf)))

def parse_csv_records(input_dir: Path, opening_tag: str | None) -> list[GameRecord]:
    records: list[GameRecord] = []
    for csv_path in sorted(input_dir.glob("*.csv")):
        match = FILENAME_RE.match(csv_path.name)
        if not match: continue
        
        red_agent, black_agent = match.group("red"), match.group("black")
        time_limit_ms, tag = int(match.group("time")), match.group("opening")
        
        if opening_tag is not None and tag != opening_tag: continue
        if canonical_pair(red_agent, black_agent) not in MATCHUPS_SET: continue

        with csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(GameRecord(
                    red_agent=red_agent, black_agent=black_agent,
                    time_limit_ms=time_limit_ms, opening_tag=tag,
                    winner=row["winner"].strip(), reason=row["reason"].strip(),
                    plies=int(row["plies"]),
                    red_total_time_ms=float(row["red_total_time_ms"]),
                    black_total_time_ms=float(row["black_total_time_ms"]),
                ))
    return records

def build_stacked_bar_stats(records: list[GameRecord]):
    stats = defaultdict(lambda: defaultdict(Counter))
    for r in records:
        pair = canonical_pair(r.red_agent, r.black_agent)
        key = (r.time_limit_ms, pair)
        if r.winner == "Draw":
            for model in pair: stats[key][model]["draw"] += 1
        else:
            winner_model = r.red_agent if r.winner == "Red" else r.black_agent
            loser_model = r.black_agent if r.winner == "Red" else r.red_agent
            stats[key][winner_model]["win"] += 1
            stats[key][loser_model]["loss"] += 1
    return stats

def plot_stacked_bars(bar_stats, times, output_path):
    fig, axes = plt.subplots(len(times), len(MATCHUPS), figsize=(16, 4 * len(times)), sharey=True)
    if len(times) == 1: axes = [axes]

    for row, time_limit in enumerate(times):
        for col, matchup in enumerate(MATCHUPS):
            ax = axes[row][col]
            pair = canonical_pair(*matchup)
            data = bar_stats.get((time_limit, pair), {})
            models = [pair[0], pair[1]]
            
            wins = [data.get(m, {}).get("win", 0) for m in models]
            draws = [data.get(m, {}).get("draw", 0) for m in models]
            losses = [data.get(m, {}).get("loss", 0) for m in models]
            
            x = [m.upper() for m in models]
            ax.bar(x, wins, color=COLORS["win"], label="Wins", width=0.6, edgecolor='white', linewidth=0.5)
            ax.bar(x, draws, bottom=wins, color=COLORS["draw"], label="Draws", width=0.6, edgecolor='white', linewidth=0.5)
            bottoms = [wins[i] + draws[i] for i in range(len(models))]
            ax.bar(x, losses, bottom=bottoms, color=COLORS["loss"], label="Losses", width=0.6, edgecolor='white', linewidth=0.5)

            for i, total in enumerate([wins[i]+draws[i]+losses[i] for i in range(2)]):
                ax.text(i, total + 0.5, str(total), ha="center", fontsize=9, fontweight='bold', color='#2c3e50')

            ax.set_title(f"Time: {time_limit}ms | {pair[0]} vs {pair[1]}", fontsize=11, pad=10)
            sns.despine(ax=ax, left=True)
            if col == 0: ax.set_ylabel("Number of Games", fontsize=10)

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.98), fontsize=12)
    fig.suptitle("Performance Comparison across Matchups", y=1.02, fontsize=16, fontweight='bold')
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

def plot_loss_reason_pies(loss_reasons, times, output_path):
    fig, axes = plt.subplots(len(times), len(AGENTS), figsize=(16, 5 * len(times)))
    if len(times) == 1: axes = [axes]

    unique_reasons = sorted({reason for ctr in loss_reasons.values() for reason in ctr})
    reason_colors = dict(zip(unique_reasons, sns.color_palette("Pastel1", len(unique_reasons))))

    target_a, target_b = "long_chase", "long_check"
    if target_a in reason_colors and target_b in reason_colors:
        reason_colors[target_a], reason_colors[target_b] = reason_colors[target_b], reason_colors[target_a]

    for row, time_limit in enumerate(times):
        for col, model in enumerate(AGENTS):
            ax = axes[row][col]
            reason_counter = loss_reasons.get((time_limit, model), Counter())
            total_losses = sum(reason_counter.values())
            
            if total_losses == 0:
                ax.text(0.5, 0.5, "No Losses", ha="center", va="center", fontsize=14, color='gray')
                ax.axis("off")
                continue

            labels, sizes = zip(*reason_counter.items())
            colors = [reason_colors[l] for l in labels]
            
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, autopct='%1.1f%%', startangle=140,
                colors=colors, pctdistance=0.85, 
                textprops={'fontsize': 9}, wedgeprops={'width': 0.4, 'edgecolor': 'w'}
            )
            plt.setp(autotexts, size=8, weight="bold", color="darkslategrey")
            ax.set_title(f"{model.upper()} Failure Reasons\n(Limit: {time_limit}ms, n={total_losses})", fontsize=11, fontweight='bold')

    fig.suptitle("Failure Reason Analysis (Failure Decomposition)", y=0.99, fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

def plot_avg_step_time(avg_step_time, times, output_path):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for model in AGENTS:
        ys = [avg_step_time.get((t, model), float("nan")) for t in times]
        ax.plot(times, ys, marker="o", linewidth=2.5, markersize=8, 
                label=model.upper(), color=COLORS.get(model),
                markerfacecolor='white', markeredgewidth=2)

    ax.set_xlabel("Time Limit (ms)", fontsize=11, fontweight='bold')
    ax.set_ylabel("Avg Time per Move (ms)", fontsize=11, fontweight='bold')
    ax.set_title("Search Efficiency: Average Single-Step Time vs Time Limit", fontsize=14, pad=15, fontweight='bold')
    
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)
    sns.despine(ax=ax)
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)

def build_opening_compare_stats(
    records: list[GameRecord],
    compare_time_ms: int = 800,
    opening_tags: tuple[str, str] = ("on", "off"),
) -> dict[tuple[tuple[str, str], str], Counter[str]]:
    stats: dict[tuple[tuple[str, str], str], Counter[str]] = defaultdict(Counter)
    opening_set = set(opening_tags)
    for r in records:
        if r.time_limit_ms != compare_time_ms:
            continue
        if r.opening_tag not in opening_set:
            continue
        pair = canonical_pair(r.red_agent, r.black_agent)
        if pair not in MATCHUPS_SET:
            continue

        key = (pair, r.opening_tag)
        if r.winner == "Draw":
            stats[key]["draw"] += 1
        elif r.winner == "Red":
            if r.red_agent == pair[0]:
                stats[key]["model_a_win"] += 1
            else:
                stats[key]["model_b_win"] += 1
        elif r.winner == "Black":
            if r.black_agent == pair[0]:
                stats[key]["model_a_win"] += 1
            else:
                stats[key]["model_b_win"] += 1
    return stats

def plot_opening_compare_bar(
    opening_stats: dict[tuple[tuple[str, str], str], Counter[str]],
    output_path: Path,
    compare_time_ms: int = 800,
    opening_tags: tuple[str, str] = ("on", "off"),
) -> bool:
    available_bars = sum(1 for pair in MATCHUPS for tag in opening_tags if opening_stats.get((canonical_pair(*pair), tag)))
    if available_bars == 0:
        return False

    fig, ax = plt.subplots(figsize=(13, 7))
    group_x = list(range(len(MATCHUPS)))
    width = 0.34

    seg_colors = {
        "model_a_win": COLORS["model-1"],
        "draw": COLORS["draw"],
        "model_b_win": COLORS["model-2"],
    }
    hatches = {
        "on": "",
        "off": "//",
    }

    for i, tag in enumerate(opening_tags):
        xs = [x + (i - 0.5) * width for x in group_x]
        a_wins = []
        draws = []
        b_wins = []

        for matchup in MATCHUPS:
            pair = canonical_pair(*matchup)
            ctr = opening_stats.get((pair, tag), Counter())
            a_wins.append(ctr.get("model_a_win", 0))
            draws.append(ctr.get("draw", 0))
            b_wins.append(ctr.get("model_b_win", 0))

        ax.bar(
            xs, a_wins, width=width, color=seg_colors["model_a_win"],
            edgecolor="white", linewidth=0.6, hatch=hatches.get(tag, ""),
        )
        ax.bar(
            xs, draws, width=width, bottom=a_wins, color=seg_colors["draw"],
            edgecolor="white", linewidth=0.6, hatch=hatches.get(tag, ""),
        )
        bottoms = [a_wins[j] + draws[j] for j in range(len(MATCHUPS))]
        ax.bar(
            xs, b_wins, width=width, bottom=bottoms, color=seg_colors["model_b_win"],
            edgecolor="white", linewidth=0.6, hatch=hatches.get(tag, ""),
        )

        totals = [a_wins[j] + draws[j] + b_wins[j] for j in range(len(MATCHUPS))]
        for x, total in zip(xs, totals):
            if total > 0:
                ax.text(x, total + 0.6, str(total), ha="center", va="bottom", fontsize=8)

    # --- 关键修改部分：调整标题 padding 和图例位置 ---
    ax.set_title(
        f"Opening_on vs Opening_off (at {compare_time_ms}ms)\n"
        "Stack meaning: model-1 wins / draws / model-2 wins (model order follows x-label: model-1 vs model-2)",
        fontsize=12,
        fontweight="bold",
        pad=50  # 增加标题与图表的间距，为图例腾出空间
    )

    from matplotlib.patches import Patch
    legend_items = [
        Patch(facecolor=seg_colors["model_a_win"], edgecolor="white", label="Model-1 Wins"),
        Patch(facecolor=seg_colors["draw"], edgecolor="white", label="Draws"),
        Patch(facecolor=seg_colors["model_b_win"], edgecolor="white", label="Model-2 Wins"),
        Patch(facecolor="white", edgecolor="gray", hatch=hatches.get("on", ""), label="opening_on"),
        Patch(facecolor="white", edgecolor="gray", hatch=hatches.get("off", "//"), label="opening_off"),
    ]
    
    # 使用 loc="lower center" 并将 bbox_to_anchor 设置在坐标轴正上方 (1.02)
    ax.legend(
        handles=legend_items, 
        ncol=5, 
        loc="lower center", 
        bbox_to_anchor=(0.5, 1.02), 
        frameon=False,
        borderaxespad=0.
    )
    # ----------------------------------------------

    ax.set_xticks(group_x, [f"{a.upper()} vs {b.upper()}" for a, b in MATCHUPS])
    ax.set_ylim(0, 44)
    ax.axhline(40, linestyle="--", linewidth=0.9, color="gray", alpha=0.6)
    ax.set_ylabel("Number of Games")
    ax.set_xlabel("Matchup")
    ax.grid(axis="y", linestyle="--", alpha=0.35)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return True

def build_loss_reason_stats(records: list[GameRecord]) -> dict[tuple[int, str], Counter[str]]:
    loss_reasons: dict[tuple[int, str], Counter[str]] = defaultdict(Counter)
    for r in records:
        if r.winner == "Draw": continue
        loser_model = r.black_agent if r.winner == "Red" else r.red_agent
        loss_reasons[(r.time_limit_ms, loser_model)][r.reason] += 1
    return loss_reasons

def build_avg_step_time(records: list[GameRecord]) -> dict[tuple[int, str], float]:
    total_time_ms: dict[tuple[int, str], float] = defaultdict(float)
    total_moves: dict[tuple[int, str], int] = defaultdict(int)
    for r in records:
        red_moves = (r.plies + 1) // 2
        black_moves = r.plies // 2
        total_time_ms[(r.time_limit_ms, r.red_agent)] += r.red_total_time_ms
        total_time_ms[(r.time_limit_ms, r.black_agent)] += r.black_total_time_ms
        total_moves[(r.time_limit_ms, r.red_agent)] += red_moves
        total_moves[(r.time_limit_ms, r.black_agent)] += black_moves
    avg: dict[tuple[int, str], float] = {}
    for key, t_ms in total_time_ms.items():
        moves = total_moves.get(key, 0)
        avg[key] = t_ms / moves if moves > 0 else float("nan")
    return avg

def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize chess-agent experiment CSV outputs.")
    parser.add_argument("--input-dir", type=Path, default=Path(__file__).resolve().parent / "outputs")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "outputs" / "figures")
    parser.add_argument("--opening-tag", type=str, default="on")
    parser.add_argument("--compare-time-ms", type=int, default=800)
    args = parser.parse_args()

    opening_tag = None if args.opening_tag.lower() == "all" else args.opening_tag
    records = parse_csv_records(args.input_dir, opening_tag)
    if not records:
        raise SystemExit(f"No matching records found in {args.input_dir}.")

    times = sorted({r.time_limit_ms for r in records})
    args.output_dir.mkdir(parents=True, exist_ok=True)

    bar_stats = build_stacked_bar_stats(records)
    loss_reasons = build_loss_reason_stats(records)
    avg_step_time = build_avg_step_time(records)

    plot_stacked_bars(bar_stats, times, args.output_dir / "stacked_results_3x3.png")
    plot_loss_reason_pies(loss_reasons, times, args.output_dir / "failure_reasons_3x3.png")
    plot_avg_step_time(avg_step_time, times, args.output_dir / "avg_step_time_line.png")

    all_records = parse_csv_records(args.input_dir, opening_tag=None)
    opening_stats = build_opening_compare_stats(all_records, compare_time_ms=args.compare_time_ms)
    plot_opening_compare_bar(opening_stats, args.output_dir / "opening_on_off_compare_800ms.png", compare_time_ms=args.compare_time_ms)

if __name__ == "__main__":
    main()