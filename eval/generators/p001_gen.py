"""
p001 Pixie VM 参数化用例生成器（防背题 PoC）。

给定随机种子，生成全新的、可终止的 Pixie 程序。expected 由参考答案
(reference/p001/solution.py) 当 oracle 计算——因此用例永不固定，
即使旧的隐藏用例泄露，也能即时再生一批 AI 从未见过的实例。

为保证确定性与终止性，仅生成直线程序（无跳转），并规避除零：
使用 SET/MOV/ADD/SUB/MUL/SHUF/STORE/LOAD/SCAN/CMP 子集。
"""
import random


def gen_program(rng: random.Random) -> str:
    regs = [f"r{i}" for i in range(8)]
    lines = []
    # 先给所有寄存器随机初值，保证后续操作有意义
    for r in regs:
        lines.append(f"SET {r} {rng.randint(0, 50)}")

    n_ops = rng.randint(6, 14)
    arith = ["ADD", "SUB", "MUL", "SHUF", "MOV", "CMP"]
    for _ in range(n_ops):
        op = rng.choice(arith + ["STORE", "LOAD", "SCAN"])
        if op == "SHUF":
            lines.append(f"SHUF {rng.choice(regs)} {rng.choice(regs)} {rng.choice(regs)}")
        elif op in ("ADD", "SUB", "MUL", "MOV", "CMP"):
            lines.append(f"{op} {rng.choice(regs)} {rng.choice(regs)}")
        elif op == "STORE":
            # 地址寄存器先夹到 0..255 范围：用一个含小值的寄存器
            addr = rng.choice(regs)
            lines.append(f"SET {addr} {rng.randint(0, 20)}")
            lines.append(f"STORE {rng.choice(regs)} {addr}")
        elif op == "LOAD":
            addr = rng.choice(regs)
            lines.append(f"SET {addr} {rng.randint(0, 20)}")
            lines.append(f"LOAD {rng.choice(regs)} {addr}")
        elif op == "SCAN":
            lo = rng.choice(regs); hi = rng.choice(regs)
            lines.append(f"SET {lo} {rng.randint(0, 10)}")
            lines.append(f"SET {hi} {rng.randint(10, 30)}")
            lines.append(f"SCAN {rng.choice(regs)} {lo} {hi}")
    lines.append("HALT")
    return "\n".join(lines) + "\n"


def generate(seed: int, n: int) -> list[str]:
    rng = random.Random(seed)
    return [gen_program(rng) for _ in range(n)]
