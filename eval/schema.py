"""题目 YAML 的 schema 校验。无第三方依赖，纯手写规则。"""
from pathlib import Path
import yaml

REQUIRED = ["schema_version", "id", "title", "category", "difficulty",
            "weight", "prompt", "public_cases"]
DIFFICULTIES = {"easy", "medium", "hard", "expert"}


def validate_problem(path: Path) -> list[str]:
    """返回错误列表；空列表表示通过。"""
    errs = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"YAML 解析失败: {e}"]
    if not isinstance(data, dict):
        return ["顶层必须是映射(dict)"]

    for k in REQUIRED:
        if k not in data:
            errs.append(f"缺少必填字段: {k}")

    if data.get("difficulty") not in DIFFICULTIES:
        errs.append(f"difficulty 须为 {DIFFICULTIES}，实际 {data.get('difficulty')!r}")
    if not isinstance(data.get("weight"), (int, float)) or data.get("weight", 0) <= 0:
        errs.append(f"weight 须为正数，实际 {data.get('weight')!r}")

    cases = data.get("public_cases", [])
    if not isinstance(cases, list) or not cases:
        errs.append("public_cases 须为非空列表")
    else:
        for i, c in enumerate(cases):
            if "input" not in c or "expected" not in c:
                errs.append(f"public_cases[{i}] 缺少 input 或 expected")

    # 目录名应与 id 前缀一致
    folder = path.parent.name
    if data.get("id") and not folder.startswith(str(data["id"])):
        errs.append(f"目录名 {folder!r} 与 id {data.get('id')!r} 不一致")
    return errs


def validate_private(path: Path, problem_id: str) -> list[str]:
    errs = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return [f"YAML 解析失败: {e}"]
    if data.get("id") != problem_id:
        errs.append(f"私有用例 id {data.get('id')!r} 与题目 {problem_id!r} 不一致")
    hc = data.get("hidden_cases", [])
    if not isinstance(hc, list) or not hc:
        errs.append("hidden_cases 须为非空列表")
    else:
        for i, c in enumerate(hc):
            if "input" not in c or "expected" not in c:
                errs.append(f"hidden_cases[{i}] 缺少 input 或 expected")
    return errs


def validate_all(root: Path) -> dict:
    """校验全部题目，返回 {problem_id: [errors]}。"""
    report = {}
    for pf in sorted((root / "problems").glob("*/problem.yaml")):
        errs = validate_problem(pf)
        data = yaml.safe_load(pf.read_text(encoding="utf-8")) or {}
        pid = data.get("id", pf.parent.name)
        priv = root / "private-tests" / str(pid) / "tests.yaml"
        if priv.exists():
            errs += validate_private(priv, pid)
        else:
            errs.append(f"[WARN] 缺少私有判分用例 private-tests/{pid}/tests.yaml")
        report[pid] = errs
    return report


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    root = Path(__file__).resolve().parent.parent
    rep = validate_all(root)
    ok = True
    for pid, errs in rep.items():
        hard = [e for e in errs if not e.startswith("[WARN]")]
        if not errs:
            print(f"  [OK]   {pid}")
        else:
            if hard:
                ok = False
            for e in errs:
                lvl = "WARN" if e.startswith("[WARN]") else "FAIL"
                print(f"  [{lvl}] {pid}: {e}")
    print("\nschema 校验:", "全部通过" if ok else "存在错误")
    sys.exit(0 if ok else 1)
