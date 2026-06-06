#!/usr/bin/env python3
"""
批量评测：所有解法 × 所有题目，生成排行榜（Markdown + JSON）。

解法布局
  reference/<id>/solution.*           视为名为 "reference" 的解法
  solutions/<solver_name>/<id>.*      每个被测 AI 一个目录，文件名以题目 id 开头

用法
  python run_all.py                   评测全部解法
  python run_all.py reference mysol   仅评测指定解法
"""
import sys
import json
from pathlib import Path
from collections import defaultdict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "eval"))
from runner import evaluate, PROBLEMS_DIR
import yaml


def discover_problems() -> list[str]:
    ids = []
    for pf in sorted(PROBLEMS_DIR.glob("*/problem.yaml")):
        ids.append(yaml.safe_load(pf.read_text(encoding="utf-8"))["id"])
    return ids


def discover_solvers() -> dict[str, dict[str, Path]]:
    """返回 {solver_name: {problem_id: solution_path}}。"""
    solvers: dict[str, dict[str, Path]] = defaultdict(dict)
    # reference
    for sol in sorted((ROOT / "reference").glob("*/solution.*")):
        solvers["reference"][sol.parent.name] = sol
    # solutions/<solver>/<id>.*
    sol_root = ROOT / "solutions"
    if sol_root.exists():
        for solver_dir in sorted(p for p in sol_root.iterdir() if p.is_dir()):
            for f in sorted(solver_dir.iterdir()):
                if f.is_file():
                    pid = f.stem.split("_")[0]
                    solvers[solver_dir.name][pid] = f
    return solvers


def render_markdown(problems, solvers_results, max_weight) -> str:
    lines = ["# AI Benchmark 排行榜", ""]
    header = "| 解法 | " + " | ".join(problems) + " | 加权总分 | 隐藏通过率 | 平均泛化差距 |"
    sep = "|" + "---|" * (len(problems) + 4)
    lines += [header, sep]

    # 按加权总分排序
    ranking = sorted(solvers_results.items(),
                     key=lambda kv: kv[1]["total_weighted"], reverse=True)
    for solver, agg in ranking:
        cells = []
        for pid in problems:
            r = agg["per_problem"].get(pid)
            if r is None:
                cells.append("—")
            else:
                cells.append(f"{r['weighted_score']}/{r['weighted_max']}")
        gap = agg["avg_gap"]
        gap_flag = " ⚠️" if gap >= 0.5 else ""
        row = (f"| **{solver}** | " + " | ".join(cells) +
               f" | {agg['total_weighted']:.2f}/{max_weight} "
               f"| {agg['hidden_rate']:.0%} "
               f"| {gap:.2f}{gap_flag} |")
        lines.append(row)

    lines += ["",
              "- **加权总分**：各题 (通过率 × 难度权重) 之和。",
              "- **隐藏通过率**：仅看私有用例，反映真实泛化能力。",
              "- **平均泛化差距**：公开通过率 − 隐藏通过率；⚠️ 标记 ≥0.5，疑似只会做样例（背题/过拟合）。"]
    return "\n".join(lines)


def main():
    wanted = [a for a in sys.argv[1:] if not a.startswith("--")]
    problems = discover_problems()
    solvers = discover_solvers()
    if wanted:
        solvers = {k: v for k, v in solvers.items() if k in wanted}

    max_weight = 0
    for pid in problems:
        pf = next(PROBLEMS_DIR.glob(f"{pid}*/problem.yaml"))
        max_weight += yaml.safe_load(pf.read_text(encoding="utf-8")).get("weight", 1)

    solvers_results = {}
    for solver, probmap in solvers.items():
        per_problem, total_weighted = {}, 0.0
        hid_pass = hid_total = 0
        gaps = []
        print(f"\n=== 评测解法: {solver} ===")
        for pid in problems:
            if pid not in probmap:
                print(f"  {pid}: (缺失)")
                continue
            r = evaluate(pid, str(probmap[pid]), show_hidden=False)
            per_problem[pid] = r
            total_weighted += r["weighted_score"]
            hid_pass += r["hidden_passed"]; hid_total += r["hidden_total"]
            gaps.append(r["generalization_gap"])
            print(f"  {pid}: {r['passed']}/{r['total']} "
                  f"(加权 {r['weighted_score']}/{r['weighted_max']}, "
                  f"gap {r['generalization_gap']})")
        solvers_results[solver] = {
            "per_problem": per_problem,
            "total_weighted": round(total_weighted, 3),
            "hidden_rate": (hid_pass / hid_total) if hid_total else 0,
            "avg_gap": round(sum(gaps) / len(gaps), 3) if gaps else 0,
        }

    # 输出
    md = render_markdown(problems, solvers_results, max_weight)
    (ROOT / "leaderboard.md").write_text(md, encoding="utf-8")
    # JSON（去掉逐用例细节，保留聚合）
    js = {s: {k: v for k, v in agg.items() if k != "per_problem"} |
             {"per_problem": {p: {kk: vv for kk, vv in r.items() if kk != "cases"}
                              for p, r in agg["per_problem"].items()}}
          for s, agg in solvers_results.items()}
    (ROOT / "leaderboard.json").write_text(
        json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + md)
    print(f"\n排行榜已保存: leaderboard.md / leaderboard.json")


if __name__ == "__main__":
    main()
