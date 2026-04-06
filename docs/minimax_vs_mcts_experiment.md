# Minimax vs MCTS 实验方案与分析方案

## 1. 实验目标

1. 对比 `minimax` 与 `mcts` 在不同时间预算下的对弈强度
2. 区分“搜索算法能力”与“先验知识库（开局库/残局库）”带来的收益
3. 给出可复现、可统计检验的结论，而不是单次对局观察

## 2. 控制变量

- 棋规实现、评估函数、终局判定保持一致（同一代码版本）
- 每组实验固定 `--max-plies`，避免超长对局拉高偶然性
- 每组实验做“换边”：
  - 组 A: `minimax` 执红, `mcts` 执黑
  - 组 B: `mcts` 执红, `minimax` 执黑
- 使用多个随机种子，避免单 seed 偏差

## 3. 实验矩阵

建议三层时间预算，各层至少 40 局（红黑各 20 局）：

- 低预算: `--time-limit-ms 300`
- 中预算: `--time-limit-ms 800`
- 高预算: `--time-limit-ms 1500`

每层再做两种知识配置：

1. 纯搜索（禁用知识库）
2. 搜索 + 开局库 + 残局库（默认）

总计建议局数：`3(时间) * 2(知识配置) * 40 = 240` 局

## 4. 命令模板

## 4.1 纯搜索（禁用开局/残局库）

```bash
python play.py --mode cli --red-agent minimax --black-agent mcts --games 20 --time-limit-ms 800 --max-plies 300 --seed 20260405 --disable-opening-book --disable-endgame-book
python play.py --mode cli --red-agent mcts --black-agent minimax --games 20 --time-limit-ms 800 --max-plies 300 --seed 20260505 --disable-opening-book --disable-endgame-book
```

## 4.2 启用知识库（默认）

```bash
python play.py --mode cli --red-agent minimax --black-agent mcts --games 20 --time-limit-ms 800 --max-plies 300 --seed 20260405
python play.py --mode cli --red-agent mcts --black-agent minimax --games 20 --time-limit-ms 800 --max-plies 300 --seed 20260505
```

将 `800` 分别替换成 `300`、`1500`，即可跑完整矩阵

## 5. 记录指标

从 `play.py` CLI 输出汇总以下指标：

1. 胜率类:
   - `minimax` 胜率
   - `mcts` 胜率
   - 和棋率
2. 效率类:
   - 红方平均用时
   - 黑方平均用时
   - 平均回合数（plies）
3. 对局结束原因分布:
   - `king_captured`
   - `no_legal_moves`
   - `long_check`
   - `long_chase`
   - `move_limit`

## 6. 统计分析方案

## 6.1 主指标与置信区间

- 主指标: `score = (win + 0.5 * draw) / total`
- 对每组配置计算 95% 置信区间（Wilson 区间或 bootstrap 均可）

## 6.2 显著性检验

- 比较 `minimax` 与 `mcts` 的 score 差异，使用两比例检验或置换检验
- 比较“开残局库开/关”对同一算法的影响，检验是否显著提升

## 6.3 强度解释（可选）

- 将 score 转换为近似 Elo 差：
  - `elo_diff ≈ -400 * log10(1 / score - 1)`
- 仅用于解释量级，不替代显著性检验

## 7. 结果解读模板

建议每个时间预算都回答以下问题：

1. 纯搜索时谁更强？差距在统计上是否显著？
2. 开残局库后，双方提升幅度是否一致？
3. 低时限与高时限下，哪种算法扩展性更好？
4. 终局原因是否变化（例如 `move_limit` 是否明显下降）？
5. 平均用时是否逼近上限（判断是否存在“算力瓶颈”）？

## 8. 常见风险与规避

1. 只跑单方向对局（不换边）会引入先手偏差，必须换边
2. 局数太少导致高方差，建议每个配置至少 40 局
3. 混用不同代码版本会污染结论，实验前固定 commit
4. 若 `move_limit` 占比过高，可将 `--max-plies` 从 300 提高到 400 再复测
