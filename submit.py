#!/usr/bin/env python3
"""
提交一份解法进行评测（语言无关）。

用法:
  python submit.py <problem_id> <solution_file> [--show-hidden] [--cmd "<run cmd>"]

示例:
  python submit.py p001 reference/p001/solution.py
  python submit.py p001 reference/p001/solution.py --show-hidden
  python submit.py p001 mysol.js --cmd "node {file}"
"""
import sys
import json
from pathlib import Path

# 强制 UTF-8 控制台输出，规避 Windows GBK 代码页乱码
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).parent / "eval"))
from runner import evaluate, print_report, load_problem, PROBLEMS_DIR
import yaml


def list_problems():
    print("可用题目:")
    for p in sorted(PROBLEMS_DIR.glob("*/problem.yaml")):
        m = yaml.safe_load(p.read_text(encoding="utf-8"))
        print(f"  {m['id']:6s} [{m['difficulty']:6s} w={m.get('weight',1)}] {m['title']}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_hidden = "--show-hidden" in sys.argv
    cmd_override = None
    if "--cmd" in sys.argv:
        i = sys.argv.index("--cmd")
        if i + 1 < len(sys.argv):
            cmd_override = sys.argv[i + 1]
            args = [a for a in args if a != cmd_override]

    if len(args) < 2:
        print(__doc__)
        list_problems()
        sys.exit(1)

    problem_id, solution_file = args[0], args[1]
    result = evaluate(problem_id, solution_file, cmd_override, show_hidden)
    print_report(result)

    out = Path(f"{problem_id}_{Path(solution_file).stem}_result.json")
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  结果已保存: {out}")


if __name__ == "__main__":
    main()
