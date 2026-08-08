from __future__ import annotations

import ast
from pathlib import Path


def test_all_streamlit_date_inputs_use_french_format() -> None:
    project_root = Path(__file__).resolve().parents[1]
    python_files = [project_root / "controle_interne.py", *list((project_root / "credit_app").rglob("*.py"))]
    missing_format: list[str] = []

    for path in python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "date_input":
                continue
            format_keyword = next((keyword for keyword in node.keywords if keyword.arg == "format"), None)
            if (
                format_keyword is None
                or not isinstance(format_keyword.value, ast.Constant)
                or format_keyword.value.value != "DD/MM/YYYY"
            ):
                missing_format.append(f"{path.relative_to(project_root)}:{node.lineno}")

    assert missing_format == []
