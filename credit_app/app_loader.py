from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd


LINE_LIST_DIR = Path("line_list")
SUPPORTED_DATA_SUFFIXES = {".xlsx", ".xls", ".csv"}


def get_excel_sheet_names(file_bytes: bytes) -> list[str]:
    with pd.ExcelFile(BytesIO(file_bytes)) as workbook:
        return workbook.sheet_names


def get_excel_sheet_names_from_path(file_path: str | Path) -> list[str]:
    with pd.ExcelFile(Path(file_path)) as workbook:
        return workbook.sheet_names


def load_dataframe_from_bytes(
    file_bytes: bytes,
    filename: str,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    lower_name = filename.lower()
    buffer = BytesIO(file_bytes)

    if lower_name.endswith(".csv"):
        return pd.read_csv(buffer)

    if lower_name.endswith((".xlsx", ".xls")):
        return pd.read_excel(buffer, sheet_name=sheet_name)

    raise ValueError(f"Format non supporte : {filename}")


def load_dataframe_from_path(
    file_path: str | Path,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    path = Path(file_path)
    lower_name = path.name.lower()

    if lower_name.endswith(".csv"):
        return pd.read_csv(path)

    if lower_name.endswith((".xlsx", ".xls")):
        return pd.read_excel(path, sheet_name=sheet_name)

    raise ValueError(f"Format non supporte : {path.name}")


def list_available_line_list_files() -> list[Path]:
    if not LINE_LIST_DIR.exists():
        return []
    return sorted(
        [path for path in LINE_LIST_DIR.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_DATA_SUFFIXES],
        key=lambda item: item.name.lower(),
    )
