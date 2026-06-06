"""
评测器自测。验证评测器本身可信：比对逻辑、计分、泛化差距、以及沙箱隔离。
运行:  python eval/selftest.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from runner import norm, run_once, evaluate, build_argv

PASS = "PASS"; FAIL = "FAIL"
results = []


def check(name, cond, detail=""):
    results.append((name, cond))
    print(f"  [{PASS if cond else FAIL}] {name}" + (f"  ({detail})" if detail and not cond else ""))


def write_tmp(suffix, content):
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(content); f.close()
    return f.name


# ---------- 1. norm() 规范化 ----------
check("norm: 去尾随空白与空行", norm("a  \nb\n\n\n") == "a\nb")
check("norm: 空串", norm("\n\n") == "")

# ---------- 2. 正确解法应满分 ----------
r = evaluate("p001", str(Path(__file__).parent.parent / "reference/p001/solution.py"),
             show_hidden=True)
check("正确解法 p001 满分", r["score"] == 100.0 and r["passed"] == r["total"])
check("正确解法泛化差距为 0", r["generalization_gap"] == 0.0,
      f"gap={r['generalization_gap']}")

# ---------- 3. 全错解法应 0 分 ----------
empty = write_tmp(".py", "import sys\nsys.stdin.read()\n")  # 啥也不输出
r0 = evaluate("p001", empty, show_hidden=True)
check("空输出解法 0 分", r0["score"] == 0.0)

# ---------- 4. 泛化差距：只背公开样例的作弊解法 ----------
# 读取 p001 公开样例的输入->输出，硬编码成查表，模拟"背题"
from runner import load_problem
prob = load_problem("p001")
table = {c["input"]: str(c["expected"]) for c in prob["public_cases"]}
cheat_src = (
    "import sys\n"
    f"TABLE = {table!r}\n"
    "data = sys.stdin.read()\n"
    "sys.stdout.write(TABLE.get(data, 'WRONG'))\n"
)
cheat = write_tmp(".py", cheat_src)
rc = evaluate("p001", cheat, show_hidden=True)
check("作弊解法公开全过", rc["pub_passed"] == rc["pub_total"])
check("作弊解法隐藏全挂", rc["hidden_passed"] == 0)
check("作弊解法泛化差距=1.0（背题信号）", rc["generalization_gap"] == 1.0,
      f"gap={rc['generalization_gap']}")

# ---------- 5. 沙箱：敏感环境变量被剥离 ----------
os.environ["SUPER_SECRET_TOKEN"] = "leak-me-if-you-can"
leak = write_tmp(".py",
    "import os\nprint(os.environ.get('SUPER_SECRET_TOKEN', 'STRIPPED'))\n")
out, _, _ = run_once(build_argv(leak, None), "", timeout=10)
check("沙箱剥离敏感环境变量", out.strip() == "STRIPPED", f"got={out.strip()!r}")

# ---------- 6. 沙箱：写文件被限制在临时目录（仓库不被污染）----------
repo_root = Path(__file__).resolve().parent.parent
pwn = repo_root / "PWNED_BY_SOLUTION.txt"
if pwn.exists():
    pwn.unlink()
writer = write_tmp(".py", "open('PWNED_BY_SOLUTION.txt','w').write('x')\n")
run_once(build_argv(writer, None), "", timeout=10)
check("沙箱限制相对路径写入（仓库未被污染）", not pwn.exists())

# ---------- 7. 沙箱：超时触发 ----------
spin = write_tmp(".py", "while True:\n    pass\n")
out, _, code = run_once(build_argv(spin, None), "", timeout=2)
check("沙箱超时触发", out == "__TIMEOUT__" and code == 124)

# ---------- 汇总 ----------
total = len(results); passed = sum(1 for _, c in results if c)
print(f"\n自测结果: {passed}/{total} 通过")
sys.exit(0 if passed == total else 1)
