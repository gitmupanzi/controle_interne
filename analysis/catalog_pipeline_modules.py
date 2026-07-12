from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    *sorted((ROOT / "credit_app" / "colonne_valeur").glob("*.py")),
    *sorted((ROOT / "credit_app" / "compilation").glob("*.py")),
]


def function_record(path: Path, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, object]:
    source = ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""
    parameters = [argument.arg for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)]
    broad_exceptions = sum(
        1
        for child in ast.walk(node)
        if isinstance(child, ast.ExceptHandler) and (child.type is None or isinstance(child.type, ast.Name) and child.type.id == "Exception")
    )
    return {
        "module": str(path.relative_to(ROOT)).replace("\\", "/"),
        "function": node.name,
        "line_start": node.lineno,
        "line_end": node.end_lineno,
        "parameters": parameters,
        "returns_annotation": ast.unparse(node.returns) if node.returns else None,
        "has_docstring": bool(ast.get_docstring(node)),
        "broad_exception_handlers": broad_exceptions,
        "uses_inplace": "inplace=True" in source.replace(" ", ""),
        "writes_files": any(token in source for token in ("to_excel(", "to_csv(", "write_text(", "open(")),
    }


def main() -> None:
    records: list[dict[str, object]] = []
    for path in TARGETS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                records.append(function_record(path, node))

    call_sites: dict[str, list[dict[str, object]]] = {record["function"]: [] for record in records}
    for path in [ROOT / "controle_interne.py", *sorted((ROOT / "credit_app").rglob("*.py")), *sorted((ROOT / "tests").rglob("*.py"))]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called_name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else None
            if called_name in call_sites:
                call_sites[called_name].append(
                    {"file": str(path.relative_to(ROOT)).replace("\\", "/"), "line": node.lineno}
                )
    for record in records:
        record["call_sites"] = call_sites[str(record["function"])]

    output = ROOT / "reports" / "module_function_catalog.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"functions={len(records)}; output={output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
