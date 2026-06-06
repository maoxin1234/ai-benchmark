"""
评测核心：语言无关地运行一份解法，对照题目公开+私有用例评分。

设计要点
- 公开题面 (problems/<id>/problem.yaml) 与私有判分用例
  (private-tests/<id>/tests.yaml) 物理分离，私有目录不随题库发布。
- 解法语言无关：按扩展名推断运行命令，或用 --cmd 显式指定。
- 沙箱（尽力而为）：隔离临时工作目录 + 最小环境变量 + 超时 + 输出上限；
  POSIX 上额外施加内存/CPU rlimit。强隔离请用 Dockerfile 中的容器方案。
"""
import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROBLEMS_DIR = ROOT / "problems"
PRIVATE_DIR = ROOT / "private-tests"

OUTPUT_CAP = 64 * 1024          # 子进程输出截断上限（字节）
DEFAULT_TIMEOUT = 10

# 扩展名 -> 构造 argv 的函数。{file} 为解法文件绝对路径。
LANG_RUNNERS = {
    ".py": lambda f: [sys.executable, f],
    ".js": lambda f: ["node", f],
    ".mjs": lambda f: ["node", f],
    ".rb": lambda f: ["ruby", f],
    ".go": lambda f: ["go", "run", f],
    ".pl": lambda f: ["perl", f],
    ".lua": lambda f: ["lua", f],
}


# ----------------------------- 加载题目 -----------------------------
def load_problem(problem_id: str) -> dict:
    """合并公开题面与私有判分用例，返回完整题目字典。"""
    matches = sorted(PROBLEMS_DIR.glob(f"{problem_id}*/problem.yaml"))
    if not matches:
        raise FileNotFoundError(f"找不到题目 '{problem_id}' (problems/{problem_id}*/problem.yaml)")
    prob = yaml.safe_load(matches[0].read_text(encoding="utf-8"))

    prob.setdefault("public_cases", [])
    prob.setdefault("hidden_cases", [])

    priv = PRIVATE_DIR / prob["id"] / "tests.yaml"
    if priv.exists():
        pdata = yaml.safe_load(priv.read_text(encoding="utf-8")) or {}
        prob["hidden_cases"] = pdata.get("hidden_cases", [])
        prob["_has_private"] = True
    else:
        prob["_has_private"] = False
    return prob


# ----------------------------- 运行解法 -----------------------------
def build_argv(solution_file: str, cmd_override: str | None) -> list[str]:
    f = str(Path(solution_file).resolve())
    if cmd_override:
        return [tok.replace("{file}", f) for tok in cmd_override.split()]
    ext = Path(solution_file).suffix.lower()
    if ext not in LANG_RUNNERS:
        raise ValueError(
            f"未知扩展名 '{ext}'。受支持: {', '.join(sorted(LANG_RUNNERS))}；"
            f"或用 --cmd 指定运行命令，例如 --cmd 'deno run {{file}}'"
        )
    return LANG_RUNNERS[ext](f)


def _minimal_env() -> dict:
    """最小环境变量白名单：仅保留解释器启动所必需者，剥离密钥等敏感变量。"""
    keep = ["PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME",
            "LANG", "LC_ALL", "PATHEXT", "COMSPEC"]
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env["PYTHONIOENCODING"] = "utf-8"   # 强制子进程 UTF-8 输出，规避平台代码页
    env["PYTHONUTF8"] = "1"
    return env


def _posix_limits(mem_mb: int, cpu_s: int):
    """返回 POSIX preexec_fn 施加资源上限；非 POSIX 返回 None。"""
    try:
        import resource
    except ImportError:
        return None

    def _set():
        b = mem_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (b, b))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    return _set


def run_once(argv: list[str], stdin: str, timeout: int = DEFAULT_TIMEOUT,
             mem_mb: int = 512) -> tuple[str, str, int]:
    """在隔离临时目录、最小环境下运行 argv，喂入 stdin，返回 (stdout, stderr, code)。"""
    workdir = tempfile.mkdtemp(prefix="bench_")
    # 把解法文件复制进沙箱目录（最后一个看似文件路径的参数）
    sandboxed = []
    for a in argv:
        p = Path(a)
        if p.exists() and p.is_file():
            dst = Path(workdir) / p.name
            shutil.copy2(p, dst)
            sandboxed.append(str(dst))
        else:
            sandboxed.append(a)
    try:
        r = subprocess.run(
            sandboxed,
            input=stdin.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            cwd=workdir,
            env=_minimal_env(),
            preexec_fn=_posix_limits(mem_mb, timeout) if os.name == "posix" else None,
        )
        out = r.stdout[:OUTPUT_CAP].decode("utf-8", errors="replace")
        err = r.stderr[:4096].decode("utf-8", errors="replace")
        return out, err, r.returncode
    except subprocess.TimeoutExpired:
        return "__TIMEOUT__", "", 124
    except FileNotFoundError as e:
        return "", f"运行器不存在: {e}", 127
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ----------------------------- 比对与评分 -----------------------------
def norm(s: str) -> str:
    """规范化：逐行去尾随空白，去末尾空行。"""
    return "\n".join(l.rstrip() for l in s.rstrip("\n").splitlines())


def evaluate(problem_id: str, solution_file: str,
             cmd_override: str | None = None, show_hidden: bool = False) -> dict:
    prob = load_problem(problem_id)
    timeout = prob.get("runtime_limit_s", DEFAULT_TIMEOUT)
    argv = build_argv(solution_file, cmd_override)

    cases = ([dict(c, hidden=False) for c in prob["public_cases"]] +
             [dict(c, hidden=True) for c in prob["hidden_cases"]])

    passed = total = pub_passed = pub_total = 0
    case_results = []

    for idx, case in enumerate(cases, 1):
        stdout, stderr, code = run_once(argv, case["input"], timeout)
        if stdout == "__TIMEOUT__":
            actual, timed_out = "", True
        else:
            actual, timed_out = norm(stdout), False
        expected = norm(str(case["expected"]))
        ok = (not timed_out) and actual == expected

        total += 1; passed += ok
        if not case["hidden"]:
            pub_total += 1; pub_passed += ok

        visible = (not case["hidden"]) or show_hidden
        case_results.append({
            "name": case.get("name", f"case_{idx}"),
            "hidden": case["hidden"],
            "passed": bool(ok),
            "timed_out": timed_out,
            "input": case["input"] if visible else "[hidden]",
            "expected": expected if visible else "[hidden]",
            "actual": actual if visible else ("[hidden] PASS" if ok else "[hidden] FAIL"),
            "stderr": stderr[:300] if stderr else "",
        })

    weight = prob.get("weight", 1)
    pub_rate = pub_passed / pub_total if pub_total else 0
    hid_total = total - pub_total
    hid_rate = (passed - pub_passed) / hid_total if hid_total else 0
    # 泛化差距：公开通过率 - 隐藏通过率。>0 越大越疑似只会做样例（背题/过拟合）
    gen_gap = round(pub_rate - hid_rate, 3)
    return {
        "problem_id": prob["id"],
        "problem_title": prob["title"],
        "difficulty": prob.get("difficulty", "?"),
        "weight": weight,
        "has_private": prob["_has_private"],
        "score": round(passed / total * 100, 1) if total else 0,
        "weighted_score": round(passed / total * weight, 3) if total else 0,
        "weighted_max": weight,
        "passed": passed, "total": total,
        "pub_passed": pub_passed, "pub_total": pub_total,
        "hidden_passed": passed - pub_passed,
        "hidden_total": hid_total,
        "generalization_gap": gen_gap,
        "cases": case_results,
    }


# ----------------------------- 文本报告 -----------------------------
def print_report(r: dict) -> None:
    import textwrap
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  {r['problem_id']} [{r['difficulty']}, w={r['weight']}] {r['problem_title']}")
    print(sep)
    if not r["has_private"]:
        print("  [WARN] 未找到私有判分用例，仅以公开样例评分（结论不可靠）")
    print(f"  公开用例 : {r['pub_passed']}/{r['pub_total']}")
    print(f"  隐藏用例 : {r['hidden_passed']}/{r['hidden_total']}")
    print(f"  合计     : {r['passed']}/{r['total']}  (得分 {r['score']}%, "
          f"加权 {r['weighted_score']}/{r['weighted_max']})")
    print()
    for c in r["cases"]:
        icon = "PASS" if c["passed"] else ("TIME" if c["timed_out"] else "FAIL")
        tag = "[隐藏]" if c["hidden"] else "[公开]"
        print(f"  [{icon}] {tag} {c['name']}")
        if not c["passed"] and c["input"] != "[hidden]":
            short = lambda s: textwrap.shorten(s.replace("\n", "/"), 70)
            print(f"      期望: {short(c['expected'])}")
            print(f"      实际: {short(c['actual'])}")
            if c["stderr"]:
                print(f"      err : {short(c['stderr'])}")
    print()
