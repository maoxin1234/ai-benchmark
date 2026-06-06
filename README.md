# AI Benchmark — AI IDE 编程能力测评框架

面向 AI IDE / 编码 Agent 的编程能力基准测试。核心目标：**即使 AI 背下题目，也无法直接给出答案**。

## 设计三原则（防背题）

1. **公私分离**：公开题面 (`problems/`) 与私有判分用例 (`private-tests/`) 物理分离，作为两个独立仓库部署——题库可公开，判分集永不发布。
2. **泛化差距**：`公开通过率 − 隐藏通过率`。差距大 = 只会做样例不会泛化 = 疑似背题，排行榜自动 ⚠️ 标记。
3. **参数化生成**：用随机种子即时生成全新用例，以参考答案为 oracle 计算期望。即使隐藏用例泄露，也能无限再生 AI 从未见过的实例。

题目本身用**虚构指令/语言/语义**（Pixie VM、Cascade Log、Runelet），强制 AI 阅读规格而非套用记忆。

## 目录结构

```
ai-benchmark/
├── problems/            # 【公开仓库】题面 + 公开样例
│   └── p00X/problem.yaml
├── private-tests/       # 【私有仓库】隐藏判分用例，不随题库发布
│   └── p00X/tests.yaml
├── reference/           # 参考答案（另一 AI IDE 所写），兼作生成器 oracle
│   └── p00X/solution.py
├── solutions/           # 被测 AI 的提交：solutions/<被测AI>/p00X.*
│   ├── gpt_demo/
│   └── cheater_demo/
├── eval/
│   ├── runner.py        # 评测核心：语言无关运行 + 沙箱 + 计分
│   ├── schema.py        # 题目 YAML 校验
│   ├── selftest.py      # 评测器自测（含沙箱反向验证）
│   ├── generators/      # 参数化用例生成器
│   └── Dockerfile       # 强隔离评测容器
├── submit.py            # 单题评测
├── run_all.py           # 批量评测 + 排行榜
└── gen_eval.py          # 参数化（防背题）评测
```

## 快速开始

```bash
pip install pyyaml

# 单题评测（--show-hidden 显示隐藏用例细节，仅本地调试用）
python submit.py p001 reference/p001/solution.py --show-hidden

# 其他语言：用 --cmd 指定运行命令，{file} 为解法文件
python submit.py p001 mysol.js --cmd "node {file}"

# 批量评测所有解法，生成排行榜
python run_all.py

# 参数化评测：随机种子生成全新用例，背题无效
python gen_eval.py p001 reference/p001/solution.py --seed 42 --n 50

# 题库校验 + 评测器自测
python eval/schema.py
python eval/selftest.py
```

## 评分体系

| 指标 | 含义 |
|------|------|
| 加权总分 | Σ(各题通过率 × 难度权重)。medium=2，hard=3 |
| 隐藏通过率 | 仅看私有用例，反映真实泛化能力 |
| 平均泛化差距 | 公开 − 隐藏通过率；≥0.5 标 ⚠️（疑似背题） |

排行榜示例（`leaderboard.md`）：

| 解法 | 加权总分 | 隐藏通过率 | 平均泛化差距 |
|---|---|---|---|
| reference | 7.00/7 | 100% | 0.00 |
| gpt_demo | 4.00/7 | 100% | 0.00 |
| cheater_demo | 2.42/7 | 0% | 1.00 ⚠️ |

## ⚠️ 安全：执行不可信代码

被测 AI 的代码是**不可信代码**。`runner.py` 提供尽力而为的进程隔离（隔离临时目录、最小环境变量、超时、输出上限；POSIX 额外施加内存/CPU rlimit）。

**但进程隔离不足以防御恶意代码**（尤其 Windows 上更弱）。生产环境评测不可信代码**必须使用容器**：

```bash
docker build -t ai-benchmark-sandbox -f eval/Dockerfile .
docker run --rm --network none --memory 512m --cpus 1 --pids-limit 128 \
  --read-only --tmpfs /tmp -v "$PWD:/work:ro" ai-benchmark-sandbox \
  python submit.py p001 reference/p001/solution.py
```

## 添加新题

1. `problems/pNNN/problem.yaml`：填 meta（含 `weight`/`difficulty`）、`prompt`、`public_cases`
2. `private-tests/pNNN/tests.yaml`：填 `hidden_cases`（覆盖边界）
3. `reference/pNNN/solution.py`：参考答案，跑 `submit.py` 确认 expected 正确
4. （可选）`eval/generators/pNNN_gen.py`：实现 `generate(seed, n)` 返回输入列表，启用参数化防背题
5. `python eval/schema.py` 校验

## 路线图

- [ ] 多次运行取稳定性（应对 AI 输出随机性）
- [ ] 为 p002/p003 补参数化生成器
- [ ] 代码质量维度（可读性、复杂度）评分
- [ ] 多轮对话能力测试（给错误反馈后能否修复）
