from __future__ import annotations

import csv
from io import BytesIO
from pathlib import Path

import pandas as pd


LINE_LIST_DIR = Path("line_list")
SUPPORTED_DATA_SUFFIXES = {".xlsx", ".xls", ".csv"}


def _detect_csv_separator(sample_text: str) -> str:
    first_line = sample_text.splitlines()[0] if sample_text.splitlines() else sample_text
    semicolon_count = first_line.count(";")
    comma_count = first_line.count(",")
    tab_count = first_line.count("\t")
    if semicolon_count >= comma_count and semicolon_count >= tab_count and semicolon_count > 0:
        return ";"
    if tab_count > comma_count and tab_count > 0:
        return "\t"
    try:
        dialect = csv.Sniffer().sniff(sample_text[:4000], delimiters=";,\t|")
        return str(dialect.delimiter)
    except Exception:
        return ","


def _read_csv_flexible_from_bytes(file_bytes: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin1", "cp1252"):
        try:
            sample_text = file_bytes[:4096].decode(encoding)
            separator = _detect_csv_separator(sample_text)
            return pd.read_csv(
                BytesIO(file_bytes),
                sep=separator,
                encoding=encoding,
                low_memory=False,
            )
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError("Lecture CSV impossible.")


def _read_csv_flexible_from_path(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin1", "cp1252"):
        try:
            sample_text = path.read_text(encoding=encoding)[:4096]
            separator = _detect_csv_separator(sample_text)
            return pd.read_csv(
                path,
                sep=separator,
                encoding=encoding,
                low_memory=False,
            )
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise ValueError(f"Lecture CSV impossible : {path.name}")


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
        return _read_csv_flexible_from_bytes(file_bytes)

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
        return _read_csv_flexible_from_path(path)

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
