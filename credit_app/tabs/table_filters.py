from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
import streamlit as st


def _safe_key(value: object) -> str:
    text = re.sub(r"[^0-9A-Za-z_]+", "_", str(value)).strip("_").lower()
    return text or "table"


def filter_value_options(series: pd.Series, *, max_options: int = 250) -> list[str]:
    if series is None:
        return []
    cleaned = (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
    )
    values = sorted(cleaned.tolist(), key=lambda item: str(item).casefold())
    return values[:max_options]


def pick_filter_columns(
    df: pd.DataFrame,
    preferred_columns: Iterable[str] | None = None,
    *,
    max_columns: int = 5,
    max_unique: int = 80,
) -> list[str]:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return []

    selected: list[str] = []
    for column in preferred_columns or []:
        if column in df.columns and column not in selected:
            selected.append(column)

    for column in df.columns:
        if len(selected) >= max_columns:
            break
        if column in selected:
            continue
        series = df[column]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue
        cleaned = series.astype("string").str.strip().replace("", pd.NA).dropna()
        unique_count = int(cleaned.nunique())
        if 1 < unique_count <= max_unique:
            selected.append(column)

    return selected[:max_columns]


def apply_local_multiselect_filters(
    df: pd.DataFrame,
    filter_columns: Iterable[str],
    *,
    key_prefix: str,
    columns_per_row: int = 3,
) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    available_columns = [column for column in filter_columns if column in df.columns]
    if not available_columns:
        return df.copy()

    active_filters: dict[str, list[str]] = {}
    widgets = st.columns(min(columns_per_row, max(1, len(available_columns))))
    for index, column in enumerate(available_columns):
        options = filter_value_options(df[column])
        if not options:
            continue
        with widgets[index % len(widgets)]:
            selected_values = st.multiselect(
                str(column),
                options=options,
                default=[],
                key=f"{_safe_key(key_prefix)}_{_safe_key(column)}",
                placeholder="Choose options",
                help="Aucune valeur selectionnee = toutes les valeurs.",
            )
        if selected_values:
            active_filters[column] = [str(value).strip() for value in selected_values]

    filtered = df.copy()
    for column, selected_values in active_filters.items():
        filtered = filtered.loc[filtered[column].astype("string").str.strip().isin(selected_values)].copy()
    return filtered.reset_index(drop=True)


def _render_dataframe(
    df: pd.DataFrame,
    *,
    hide_index: bool,
    height: int | str | None,
) -> None:
    kwargs: dict[str, object] = {"width": "stretch", "hide_index": hide_index}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)


def render_filtered_dataframe(
    df: pd.DataFrame,
    *,
    key_prefix: str,
    preferred_columns: Iterable[str] | None = None,
    max_rows: int | None = None,
    height: int | None = None,
    hide_index: bool = True,
) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        _render_dataframe(pd.DataFrame(), hide_index=hide_index, height=height)
        return pd.DataFrame()

    filter_columns = pick_filter_columns(df, preferred_columns)
    filtered = apply_local_multiselect_filters(df, filter_columns, key_prefix=key_prefix)
    shown = filtered.head(max_rows) if max_rows is not None else filtered
    st.caption(
        f"{len(filtered):,}".replace(",", " ")
        + f" ligne(s) apres filtres"
        + (f" | {len(shown):,}".replace(",", " ") + " affichee(s)" if max_rows is not None else "")
        + "."
    )
    _render_dataframe(shown, hide_index=hide_index, height=height)
    return filtered
