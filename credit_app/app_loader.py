from __future__ import annotations

import csv
from io import BytesIO
from pathlib import Path

import pandas as pd

from credit_app.data_schema import (
    DataSchema,
    normalize_dataframe_headers,
    validate_dataframe_schema,
)


LINE_LIST_DIR = Path("line_list")
SUPPORTED_DATA_SUFFIXES = {".xlsx", ".xls", ".csv"}


class DataLoadError(ValueError):
    """A safe, user-facing error raised while loading a local data file."""


def _validate_loaded_frame(
    dataframe: pd.DataFrame,
    *,
    source: str,
    schema: DataSchema | None,
    reject_empty: bool,
) -> pd.DataFrame:
    if not isinstance(dataframe, pd.DataFrame):
        raise DataLoadError(f"{source} : la feuille sélectionnée ne contient pas un tableau exploitable.")
    if reject_empty and (dataframe.empty or len(dataframe.columns) == 0):
        raise DataLoadError(f"{source} : le fichier est vide ou ne contient aucune ligne de données.")
    if schema is None:
        return dataframe
    normalized = normalize_dataframe_headers(dataframe, schema)
    validate_dataframe_schema(normalized, schema, source, raise_on_missing=True)
    return normalized


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
        raise DataLoadError(f"Lecture CSV impossible : {last_error}") from last_error
    raise DataLoadError("Lecture CSV impossible.")


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
        raise DataLoadError(f"Lecture CSV impossible pour {path.name} : {last_error}") from last_error
    raise DataLoadError(f"Lecture CSV impossible : {path.name}")


def get_excel_sheet_names(file_bytes: bytes) -> list[str]:
    try:
        with pd.ExcelFile(BytesIO(file_bytes)) as workbook:
            return workbook.sheet_names
    except Exception as exc:
        raise DataLoadError(f"Impossible de lire les feuilles du fichier Excel : {exc}") from exc


def get_excel_sheet_names_from_path(file_path: str | Path) -> list[str]:
    path = Path(file_path)
    try:
        with pd.ExcelFile(path) as workbook:
            return workbook.sheet_names
    except Exception as exc:
        raise DataLoadError(f"Impossible de lire les feuilles de {path.name} : {exc}") from exc


def load_dataframe_from_bytes(
    file_bytes: bytes,
    filename: str,
    sheet_name: str | None = None,
    *,
    schema: DataSchema | None = None,
    reject_empty: bool = False,
) -> pd.DataFrame:
    lower_name = filename.lower()
    buffer = BytesIO(file_bytes)

    if lower_name.endswith(".csv"):
        frame = _read_csv_flexible_from_bytes(file_bytes)
        return _validate_loaded_frame(frame, source=filename, schema=schema, reject_empty=reject_empty)

    if lower_name.endswith((".xlsx", ".xls")):
        try:
            frame = pd.read_excel(buffer, sheet_name=0 if sheet_name is None else sheet_name)
        except Exception as exc:
            raise DataLoadError(f"Impossible de lire {filename} : {exc}") from exc
        return _validate_loaded_frame(frame, source=filename, schema=schema, reject_empty=reject_empty)

    raise DataLoadError(f"Format non supporté : {filename}")


def load_dataframe_from_path(
    file_path: str | Path,
    sheet_name: str | None = None,
    *,
    schema: DataSchema | None = None,
    reject_empty: bool = False,
) -> pd.DataFrame:
    path = Path(file_path)
    lower_name = path.name.lower()

    if lower_name.endswith(".csv"):
        frame = _read_csv_flexible_from_path(path)
        return _validate_loaded_frame(frame, source=path.name, schema=schema, reject_empty=reject_empty)

    if lower_name.endswith((".xlsx", ".xls")):
        try:
            frame = pd.read_excel(path, sheet_name=0 if sheet_name is None else sheet_name)
        except Exception as exc:
            raise DataLoadError(f"Impossible de lire {path.name} : {exc}") from exc
        return _validate_loaded_frame(frame, source=path.name, schema=schema, reject_empty=reject_empty)

    raise DataLoadError(f"Format non supporté : {path.name}")


def list_available_line_list_files() -> list[Path]:
    if not LINE_LIST_DIR.exists():
        return []
    return sorted(
        [path for path in LINE_LIST_DIR.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_DATA_SUFFIXES],
        key=lambda item: item.name.lower(),
    )
