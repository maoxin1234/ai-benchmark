#!/usr/bin/env python3
"""
参数化评测（防背题）：用随机种子生成全新用例，以参考答案为 oracle 计算 expected，
再评测目标解法。用例从不固定 —— 背题无效。

用法
  python gen_eval.py <problem_id> <solution_file> [--seed N] [--n K] [--cmd "..."]

示例
  python gen_eval.py p001 reference/p001/solution.py --seed 42 --n 50
  python gen_eval.py p001 solutions/cheater_demo/p001.py --seed 42 --n 50
"""
import sys
import importlib.util
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "eval"))
from runner import run_once, build_argv, norm


def load_generator(problem_id: str):
    gen_path = ROOT / "eval" / "generators" / f"{problem_id}_gen.py"
    if not gen_path.exists():
        raise FileNotFoundError(f"题目 {problem_id} 暂无参数化生成器 ({gen_path.name})")
    spec = importlib.util.spec_from_file_location(f"{problem_id}_gen", gen_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__); sys.exit(1)
    problem_id, solution_file = args[0], args[1]

    def opt(flag, default, cast=str):
        if flag in sys.argv:
            return cast(sys.argv[sys.argv.index(flag) + 1])
        return default
    seed = opt("--seed", 0, int)
    n = opt("--n", 30, int)
    cmd = opt("--cmd", None)

    gen = load_generator(problem_id)
    inputs = gen.generate(seed, n)

    oracle = ROOT / "reference" / problem_id / "solution.py"
    if not oracle.exists():
        print(f"缺少 oracle 参考答案: {oracle}"); sys.exit(1)
    oracle_argv = build_argv(str(oracle), None)
    cand_argv = build_argv(solution_file, cmd)

    passed = 0
    first_fail = None
    for i, inp in enumerate(inputs):
        exp, _, _ = run_once(oracle_argv, inp, timeout=10)
        got, _, _ = run_once(cand_argv, inp, timeout=10)
        ok = (exp != "__TIMEOUT__" and got != "__TIMEOUT__"
              and norm(exp) == norm(got))
        passed += ok
        if not ok and first_fail is None:
            first_fail = (inp, norm(exp), norm(got))

    print(f"参数化评测  题目={problem_id}  seed={seed}  样本数={n}")
    print(f"解法: {solution_file}")
    print(f"通过: {passed}/{n}  ({passed/n:.0%})")
    if first_fail:
        inp, exp, got = first_fail
        print("\n首个失败样例（随机生成，AI 不可能预先见过）:")
        print("  输入(首3行):", " / ".join(inp.splitlines()[:3]), "...")
        print("  oracle期望(首行):", exp.splitlines()[0] if exp else "(空)")
        print("  解法实际(首行):", got.splitlines()[0] if got else "(空)")


if __name__ == "__main__":
    main()
