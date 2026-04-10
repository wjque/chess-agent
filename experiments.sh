#!/bin/bash

# 设置失败即停止
set -e

# ====================================
# 配置参数
# ====================================
GAMES=20
MCTS_EXPLORATION=0.2
# 将不同的时间限制放在一个数组里
TIME_LIMITS=(300 800 1500)
# 定义想要对比的对局组合 (Red vs Black)
AGENTS=("mcts minimax" "minimax mcts" "minimax random" "random minimax" "mcts random" "random mcts")

# ====================================
# 执行实验
# ====================================
for OPEN_BOOK in "" "--disable-opening-book"; do
    for MS in "${TIME_LIMITS[@]}"; do
        echo "------------------------------------------------"
        echo "正在开始实验 Time Limit = ${MS}ms"
        echo "------------------------------------------------"

        for PAIR in "${AGENTS[@]}"; do
            # 将组合拆分为 red 和 black
            set -- $PAIR
            RED=$1
            BLACK=$2

            echo "[运行中] Red: $RED vs Black: $BLACK (Limit: ${MS}ms)"

            python play.py \
                --mode cli \
                --games $GAMES \
                --red-agent "$RED" \
                --black-agent "$BLACK" \
                --mcts-exploration $MCTS_EXPLORATION \
                --time-limit-ms "$MS" \
                $OPEN_BOOK

            echo "[完成] Red: $RED vs Black: $BLACK"
        done
    done
done

echo "所有实验已完成！"