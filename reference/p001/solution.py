"""Pixie VM 参考实现。"""
import sys


def main():
    lines = [l.strip() for l in sys.stdin.read().splitlines()]
    lines = [l for l in lines if l and not l.startswith("--")]

    labels, instructions = {}, []
    for line in lines:
        if line.endswith(":"):
            labels[line[:-1]] = len(instructions)
        else:
            instructions.append(line.split())

    regs = {f"r{i}": 0 for i in range(8)}
    mem = [0] * 256
    flag = pc = steps = 0

    while steps < 10000:
        if pc >= len(instructions):
            break
        tok = instructions[pc]
        op = tok[0]
        steps += 1
        jumped = False

        if op == "HALT":
            break
        elif op == "SET":   regs[tok[1]] = int(tok[2])
        elif op == "MOV":   regs[tok[1]] = regs[tok[2]]
        elif op == "ADD":   regs[tok[1]] += regs[tok[2]]
        elif op == "SUB":   regs[tok[1]] -= regs[tok[2]]
        elif op == "MUL":   regs[tok[1]] *= regs[tok[2]]
        elif op == "DIV":   regs[tok[1]] //= regs[tok[2]]
        elif op == "MOD":   regs[tok[1]] %= regs[tok[2]]
        elif op == "SHUF":
            ry, rz = regs[tok[2]], regs[tok[3]]
            regs[tok[1]] = (ry * rz) ^ (ry + rz)
        elif op == "CMP":
            a, b = regs[tok[1]], regs[tok[2]]
            flag = 0 if a == b else (1 if a > b else -1)
        elif op == "JMP": pc = labels[tok[1]]; jumped = True
        elif op == "JEQ":
            if flag == 0:  pc = labels[tok[1]]; jumped = True
        elif op == "JNE":
            if flag != 0:  pc = labels[tok[1]]; jumped = True
        elif op == "JLT":
            if flag == -1: pc = labels[tok[1]]; jumped = True
        elif op == "JGT":
            if flag == 1:  pc = labels[tok[1]]; jumped = True
        elif op == "STORE": mem[regs[tok[2]]] = regs[tok[1]]
        elif op == "LOAD":  regs[tok[1]] = mem[regs[tok[2]]]
        elif op == "SCAN":
            regs[tok[1]] = next(
                (a for a in range(regs[tok[2]], regs[tok[3]] + 1) if mem[a] != 0),
                -1,
            )

        if not jumped:
            pc += 1
    else:
        print("TIMEOUT")
        return

    for i in range(8):
        print(f"r{i}={regs[f'r{i}']}")


main()
