# 象棋智能体

本项目实现了一个可对弈的中国象棋引擎与多种智能体，包括：

- 完整的 9x10 棋盘规则框架
- `Random` 随机基线智能体
- `Minimax` 智能体（迭代加深 + Alpha-Beta + 着法排序 + 置换表）
- `MCTS` 智能体（UCT + 启发式 rollout）
- 支持人机 / 机机对弈的 `PyQt6` 图形界面
- 用于智能体对比实验的 CLI 批量模式

## 功能说明

### 规则引擎

- 棋盘表示：9x10 象棋标准棋盘与子集
- 棋子走法与吃子规则：
  - 马腿别脚
  - 象眼阻挡 + 不能过河
  - 炮架规则
  - 将/士九宫限制
  - 将帅照面（飞将）合法性处理
- 通过“是否自将”过滤非法着法
- 终局检测：
  - 将/帅被吃
  - 无合法着法
- 其他规则：
  - 长将判负（`long_check`）
  - 长捉判负（`long_chase`）

### 搜索

- 共享评估函数：
  - 子力
  - 位置分
  - 机动性
  - 将帅安全
  - 将军压力
- Minimax：
  - 迭代加深
  - Alpha-Beta 剪枝
  - 置换表（TT）
  - Killer / History 启发
- MCTS：
  - UCT 选择
  - rollout 深度限制
  - 偏向吃子/将军的 rollout 策略

#### 开局库

- 本地 JSON 开局线：`chess/openings.json`
- 通过局面键检索候选着法
- 未命中时自动回退到搜索

#### 残局库

- 本地残局条目：`chess/endgames.json`
- 已知战术残局支持精确命中
- 小子力残局（<= 配置阈值）时启用回退策略，优先：
  - 直接取胜手段
  - 将军 / 吃子
  - 压缩对方将帅机动空间

## 项目结构

- `chess/`：引擎核心模块（`state`、`rules`、`judge`、`evaluate`、`opening`、`endgame` 等）
- `agents/`：智能体实现
- `play.py`：GUI/CLI 统一入口

## 运行要求

- Python 3.10+
- GUI 可选依赖：`PyQt6`

安装 GUI 依赖：

```bash
pip install PyQt6
```

## 使用方式

### GUI（默认）

```bash
python play.py --mode gui --red-agent human --black-agent minimax --time-limit-ms 1500
```

其他 GUI 示例：

```bash
python play.py --mode gui --red-agent human --black-agent mcts
python play.py --mode gui --red-agent minimax --black-agent mcts
```

### CLI 自对弈 / 对比实验

```bash
python play.py --mode cli --red-agent minimax --black-agent mcts --games 50 --time-limit-ms 1500
```

常用参数：

- `--max-plies 300`：单局最大步数上限
- `--seed 20260405`：固定随机种子，便于复现
- `--mcts-exploration 1.0`：UCT 探索常数
- `--mcts-rollout-depth 48`：单次模拟 rollout 深度上限
- `--mcts-draw-threshold 80`：rollout 截断时判和阈值（基于评估分）
- `--mcts-rollout-check-samples 8`：rollout 中将军偏置采样数
- `--disable-opening-book`：为所有智能体关闭开局库
- `--disable-endgame-book`：为所有智能体关闭残局库

