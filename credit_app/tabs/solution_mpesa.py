from __future__ import annotations

from dataclasses import replace
from datetime import time
import hashlib
from io import BytesIO
import re
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.display_columns import (
    prepare_dataframe_with_user_columns,
    resolve_user_column_mapping,
    translate_column_config_for_user_columns,
)
from credit_app.services.mpesa_analysis import (
    CURRENT_SAVINGS_REQUIRED_COLUMNS,
    CUSTOMER_STATEMENT_FOCUS_OPERATION_TYPES,
    CUSTOMER_STATEMENT_COLUMNS,
    CUSTOMERS_REQUIRED_COLUMNS,
    DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT,
    DEFAULT_DAT_REPAYMENT_PREPARATION_HORIZON_DAYS,
    DEFAULT_MPESA_COMPARISON_PERIOD,
    DEFAULT_MPESA_YEAR_SCOPE_MODE,
    FIXED_SAVINGS_REQUIRED_COLUMNS,
    G2_CLASSIFIED_TRANSACTION_COLUMNS,
    G2_TRANSACTION_REQUIRED_COLUMNS,
    LOAN_USEFUL_COLUMNS,
    MPESA_COMPARISON_PERIOD_OPTIONS,
    MPESA_FORECAST_CONFIDENCE_OPTIONS,
    MPESA_FORECAST_HORIZON_OPTIONS,
    MPESA_YEAR_SCOPE_MODES,
    PERFECT_CLIENTS_REQUIRED_COLUMNS,
    TRANSACTION_REQUIRED_COLUMNS,
    TRANSACTION_ANOMALY_CONTROL_NAMES,
    MpesaPreparedData,
    build_diagnostics,
    build_transaction_anomalies,
    build_large_dat_summary,
    build_g2_daily_savings_report,
    build_g2_dat_crosscheck,
    build_g2_retention_report,
    build_g2_transaction_time_analysis,
    build_turbo_only_g2_transactions,
    build_load_report,
    build_mpesa_accounting_analysis,
    build_mpesa_clients_report,
    build_mpesa_dat_maturity_analysis,
    build_mpesa_savings_cockpit,
    build_loan_savings_reconciliation,
    build_mpesa_credit_cockpit,
    build_mpesa_management_dashboard,
    build_mpesa_forecast_report,
    build_mpesa_statistics_report,
    build_mpesa_weekly_comparison,
    build_turbo_operation_events,
    build_mpesa_statement,
    build_savings_accounts_reconciliation,
    build_customer_transaction_analysis,
    build_customer_statement_filename,
    build_customer_statement_financial_summary,
    build_customer_statement_detail_with_covered_operations,
    build_customer_statement_detail_with_opening_balance,
    build_customer_statement_view,
    build_filtered_turbo_deposit_withdrawal_pivot_report,
    build_filtered_turbo_balance_report,
    build_perfect_client_crosscheck,
    create_excel_export,
    create_mpesa_statistics_word,
    create_customer_client_statement_pdf,
    create_customer_client_statement_word,
    create_customer_statement_pdf,
    create_customer_statement_word,
    create_g2_dat_word,
    create_turbo_balance_pdf,
    create_turbo_balance_word,
    count_mpesa_loaded_customers,
    enrich_transactions_with_g2_customer_names,
    enrich_turbo_with_g2_customer_names,
    filter_g2_transactions_by_completion_time,
    filter_g2_transactions_by_direction,
    numeric_column,
    prepare_customers,
    prepare_g2_transactions,
    prepare_loans,
    prepare_perfect_clients,
    prepare_savings_accounts,
    prepare_transactions,
    promote_g2_statement_header,
    search_customers,
    scope_mpesa_prepared_data_by_year,
    validate_required_columns,
)
from credit_app.ui import (
    format_professional_tab_labels,
    inject_professional_tabs_css,
    render_kpi_cards,
    render_panel_title,
    render_summary_box,
    st_plot,
    style_standard_donut,
    style_standard_horizontal_bar,
    style_standard_line,
    style_standard_vertical_bar,
)


MPESA_FINANCE_TURBO_TAB_LABELS = (
    "Vue direction",
    "Flux et activité",
    "Crédit, épargne et DAT",
    "Balances et journaux",
    "Risques et contrôles",
    "Export",
)

MPESA_SOLUTION_TAB_LABELS = (
    "Importation et contrôle",
    "Extraits clients",
    "Finance et comptabilité",
    "Clients",
    "Épargnes",
    "Crédits",
    "Solution Numérique / M-Pesa",
    "Perfect Client",
    "Statistiques",
    "Projections",
)


def _format_amount(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if pd.isna(number):
        return "-"
    return f"{number:,.2f}".replace(",", " ")


def _format_count(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "-"


def _format_percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if pd.isna(number):
        return "-"
    return f"{number:.1f}%"


def _selected_mpesa_comparison_period() -> str:
    selected = str(
        st.session_state.get(
            "mpesa_comparison_period",
            DEFAULT_MPESA_COMPARISON_PERIOD,
        )
        or DEFAULT_MPESA_COMPARISON_PERIOD
    )
    return (
        selected
        if selected in MPESA_COMPARISON_PERIOD_OPTIONS
        else DEFAULT_MPESA_COMPARISON_PERIOD
    )


def _selected_mpesa_year_scope() -> tuple[str, int | None, int | None]:
    mode = str(
        st.session_state.get(
            "mpesa_year_scope_mode",
            DEFAULT_MPESA_YEAR_SCOPE_MODE,
        )
        or DEFAULT_MPESA_YEAR_SCOPE_MODE
    )
    if mode not in MPESA_YEAR_SCOPE_MODES:
        mode = DEFAULT_MPESA_YEAR_SCOPE_MODE
    if mode == "Année unique":
        selected_year = int(
            st.session_state.get("mpesa_year_scope_single", pd.Timestamp.now().year)
        )
        return mode, selected_year, selected_year
    if mode == "Plage d'années":
        current_year = int(pd.Timestamp.now().year)
        return (
            mode,
            int(st.session_state.get("mpesa_year_scope_start", current_year - 1)),
            int(st.session_state.get("mpesa_year_scope_end", current_year)),
        )
    return DEFAULT_MPESA_YEAR_SCOPE_MODE, None, None


def _render_weekly_comparison(
    comparison: pd.DataFrame,
    *,
    blocks: list[str] | None = None,
    indicator_keys: list[str] | None = None,
    selected_currencies: list[str] | None = None,
    title: str = "Comparaison avec la période précédente",
) -> None:
    """Affiche des cartes KPI comparant deux périodes consécutives."""
    if not isinstance(comparison, pd.DataFrame) or comparison.empty:
        st.info("La comparaison avec la période précédente n'est pas calculable.")
        return

    view = comparison.copy()
    if blocks:
        view = view.loc[view["bloc"].astype(str).isin(blocks)]
    if indicator_keys:
        view = view.loc[view["indicator_key"].astype(str).isin(indicator_keys)]
    if selected_currencies:
        currency = view.get(
            "currency_code", pd.Series("", index=view.index)
        ).astype("string").fillna("")
        view = view.loc[currency.eq("") | currency.isin(selected_currencies)]
    if view.empty:
        return

    current_start = pd.to_datetime(
        view.iloc[0].get("date_debut_semaine_courante"), errors="coerce"
    )
    current_end = pd.to_datetime(
        view.iloc[0].get("date_fin_semaine_courante"), errors="coerce"
    )
    previous_start = pd.to_datetime(
        view.iloc[0].get("date_debut_semaine_precedente"), errors="coerce"
    )
    previous_end = pd.to_datetime(
        view.iloc[0].get("date_fin_semaine_precedente"), errors="coerce"
    )
    comparison_label = str(
        view.iloc[0].get(
            "periode_comparaison",
            DEFAULT_MPESA_COMPARISON_PERIOD,
        )
        or DEFAULT_MPESA_COMPARISON_PERIOD
    )
    render_panel_title(title)
    if all(pd.notna(value) for value in [current_start, current_end, previous_start, previous_end]):
        st.caption(
            f"Mode : {comparison_label} | Période analysée : "
            f"{current_start:%d/%m/%Y} au {current_end:%d/%m/%Y} | "
            f"Période de référence : {previous_start:%d/%m/%Y} au {previous_end:%d/%m/%Y}. "
            "Une hausse porte un signe +; une baisse porte un signe -."
        )

    block_order = list(dict.fromkeys(view["bloc"].astype(str).tolist()))
    for block in block_order:
        block_view = view.loc[view["bloc"].astype(str).eq(block)]
        if len(block_order) > 1:
            st.markdown(f"**{block}**")
        records = block_view.to_dict("records")
        for offset in range(0, len(records), 4):
            chunk = records[offset : offset + 4]
            columns = st.columns(len(chunk), gap="small")
            for column, row in zip(columns, chunk):
                coverage = str(row.get("couverture", "")).strip()
                current_value = pd.to_numeric(
                    row.get("valeur_semaine_courante"), errors="coerce"
                )
                previous_value = pd.to_numeric(
                    row.get("valeur_semaine_precedente"), errors="coerce"
                )
                evolution = pd.to_numeric(row.get("evolution_pct"), errors="coerce")
                currency = str(row.get("currency_code", "") or "").strip().upper()
                unit = str(row.get("unite", "") or "")
                label = str(row.get("indicateur", "") or "Indicateur")
                if currency:
                    label = f"{label} [{currency}]"

                if coverage == "Non calculable" or pd.isna(current_value):
                    display_value = "-"
                    delta_text = "Référence indisponible"
                    delta_color = "off"
                else:
                    if unit == "nombre":
                        display_value = _format_count(current_value)
                    elif unit == "pourcentage":
                        display_value = _format_percent(current_value)
                    else:
                        display_value = f"{_format_amount(current_value)} {currency}".strip()
                    if pd.isna(previous_value):
                        delta_text = "Référence indisponible"
                        delta_color = "off"
                    elif unit == "pourcentage":
                        point_delta = pd.to_numeric(
                            row.get("ecart_absolu"),
                            errors="coerce",
                        )
                        delta_text = (
                            "Référence indisponible"
                            if pd.isna(point_delta)
                            else f"{float(point_delta):+.1f} point(s) vs période précédente"
                        )
                        delta_color = "off" if pd.isna(point_delta) else "normal"
                    elif float(previous_value) == 0 and float(current_value) > 0:
                        delta_text = "Nouvelle activité vs période précédente"
                        delta_color = "normal"
                    elif pd.isna(evolution):
                        delta_text = "Référence indisponible"
                        delta_color = "off"
                    else:
                        delta_text = f"{float(evolution):+.1f}% vs période précédente"
                        delta_color = "normal"

                if pd.isna(previous_value):
                    previous_display = "-"
                elif unit == "nombre":
                    previous_display = _format_count(previous_value)
                elif unit == "pourcentage":
                    previous_display = _format_percent(previous_value)
                else:
                    previous_display = f"{_format_amount(previous_value)} {currency}".strip()
                help_text = (
                    f"Valeur de la période précédente : {previous_display}. "
                    f"Source : {row.get('source', 'Solution Numérique')}. "
                    f"Couverture temporelle : {coverage or 'Non renseignée'}."
                )
                with column:
                    st.metric(
                        label,
                        display_value,
                        delta_text,
                        delta_color=delta_color,
                        border=True,
                        help=help_text,
                    )


def _render_year_over_year_charts(
    comparison: pd.DataFrame,
    *,
    block: str,
    selected_currencies: list[str] | None = None,
) -> None:
    """Affiche des histogrammes N/N-1 sans mélanger unités ni devises."""
    if not isinstance(comparison, pd.DataFrame) or comparison.empty:
        return
    view = comparison.loc[
        comparison["bloc"].astype(str).eq(block)
    ].copy()
    if selected_currencies:
        currencies = view.get(
            "currency_code",
            pd.Series("", index=view.index),
        ).astype("string").fillna("")
        view = view.loc[
            currencies.eq("") | currencies.isin(selected_currencies)
        ].copy()
    if view.empty:
        return

    current_start = pd.to_datetime(
        view.iloc[0].get("date_debut_semaine_courante"),
        errors="coerce",
    )
    current_end = pd.to_datetime(
        view.iloc[0].get("date_fin_semaine_courante"),
        errors="coerce",
    )
    previous_start = pd.to_datetime(
        view.iloc[0].get("date_debut_semaine_precedente"),
        errors="coerce",
    )
    previous_end = pd.to_datetime(
        view.iloc[0].get("date_fin_semaine_precedente"),
        errors="coerce",
    )
    current_label = (
        f"{current_start:%d/%m/%Y} - {current_end:%d/%m/%Y}"
        if pd.notna(current_start) and pd.notna(current_end)
        else "Période analysée"
    )
    previous_label = (
        f"{previous_start:%d/%m/%Y} - {previous_end:%d/%m/%Y}"
        if pd.notna(previous_start) and pd.notna(previous_end)
        else "Même période N-1"
    )

    complete = view.loc[
        view.get("couverture", pd.Series("", index=view.index))
        .astype(str)
        .eq("Complete")
    ].copy()
    if complete.empty:
        st.info(
            "L'historique de l'année précédente est absent ou incomplet pour "
            "construire un graphique annuel comparable."
        )
        return
    if len(complete) < len(view):
        st.caption(
            "Le graphique conserve uniquement les indicateurs dont les deux "
            "périodes sont entièrement couvertes."
        )

    def _draw(frame: pd.DataFrame, *, unit: str, currency: str = "") -> None:
        if frame.empty:
            return
        chart_rows: list[dict[str, Any]] = []
        for _, row in frame.iterrows():
            for period_label, value_column in [
                (current_label, "valeur_semaine_courante"),
                (previous_label, "valeur_semaine_precedente"),
            ]:
                value = pd.to_numeric(row.get(value_column), errors="coerce")
                if pd.isna(value):
                    continue
                chart_rows.append(
                    {
                        "Indicateur": str(row.get("indicateur", "")),
                        "Période": period_label,
                        "Valeur": float(value),
                    }
                )
        chart_data = pd.DataFrame(chart_rows)
        if chart_data.empty:
            return
        figure = px.bar(
            chart_data,
            x="Indicateur",
            y="Valeur",
            color="Période",
            barmode="group",
            labels={"Valeur": "Nombre" if unit == "nombre" else "Montant"},
        )
        style_standard_vertical_bar(figure, height=390, tickangle=-18)
        suffix = f" [{currency}]" if currency else ""
        chart_title = f"Comparaison annuelle des {block.lower()}{suffix}"
        st.markdown(f"**{chart_title}**")
        st.caption(
            "Période analysée et mêmes dates de l'année précédente."
        )
        st_plot(
            figure,
            key=(
                f"mpesa_statistics_yoy_{re.sub(r'[^0-9A-Za-z]+', '_', block).strip('_').lower()}_"
                f"{unit}_{currency or 'global'}"
            ),
            height=390,
            source_note=(
                "Source : Solution Numérique uniquement. Les montants sont présentés "
                "séparément par devise."
            ),
        )

    count_rows = complete.loc[complete["unite"].astype(str).eq("nombre")]
    _draw(count_rows, unit="nombre")

    amount_rows = complete.loc[complete["unite"].astype(str).eq("montant")]
    for currency in sorted(
        amount_rows.get(
            "currency_code",
            pd.Series(dtype="string"),
        )
        .dropna()
        .astype(str)
        .loc[lambda series: series.str.strip().ne("")]
        .unique()
    ):
        _draw(
            amount_rows.loc[
                amount_rows["currency_code"].astype(str).eq(currency)
            ],
            unit="montant",
            currency=currency,
        )


def _latest_complete_turbo_date(prepared: MpesaPreparedData) -> pd.Timestamp:
    """Propose la derniere journee complete pour une comparaison hebdomadaire."""
    candidates: list[pd.Series] = []
    for frame, date_columns in [
        (prepared.transactions, ["created_at"]),
        (prepared.loans, ["created_at"]),
        (prepared.fixed_savings, ["date_activated", "date_approved", "created_at"]),
        (prepared.current_savings, ["date_activated", "date_approved", "created_at"]),
        (prepared.customers, ["created_at"]),
    ]:
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        dates = pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
        for column in date_columns:
            if column in frame.columns:
                dates = dates.combine_first(pd.to_datetime(frame[column], errors="coerce"))
        dates = dates.dropna()
        if not dates.empty:
            candidates.append(dates)
    if not candidates:
        return pd.Timestamp.now().normalize()
    dates = pd.concat(candidates, ignore_index=True)
    latest = pd.Timestamp(dates.max())
    result = latest.normalize()
    if dates.min().normalize() < result and latest.hour < 18:
        result -= pd.Timedelta(days=1)
    return result


def _render_alert_banner(message: str) -> None:
    """Affiche un signal rouge natif et accessible au-dessus d'un tableau de revue."""
    st.error(message, icon=":material/error:")


def _prepared_data_cache_key(prepared: MpesaPreparedData) -> str:
    return prepared.cache_fingerprint or f"session-object:{id(prepared)}"


def _prepared_data_as_of(
    prepared: MpesaPreparedData,
    analysis_date: object,
) -> MpesaPreparedData:
    """Conserve l'historique disponible jusqu'a la date d'analyse incluse."""
    period_end = pd.Timestamp(analysis_date).normalize() + pd.Timedelta(days=1)

    def before(frame: pd.DataFrame, *date_columns: str) -> pd.DataFrame:
        if frame.empty:
            return frame
        dates = pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns]")
        for column in date_columns:
            if column in frame.columns:
                dates = dates.combine_first(
                    pd.to_datetime(frame[column], errors="coerce")
                )
        return frame.loc[dates.isna() | dates.lt(period_end)].copy()

    return replace(
        prepared,
        transactions=before(prepared.transactions, "created_at"),
        current_savings=before(prepared.current_savings, "created_at", "updated_at"),
        fixed_savings=before(prepared.fixed_savings, "date_approved", "created_at"),
        fixed_savings_control=before(
            prepared.fixed_savings_control, "date_approved", "created_at"
        ),
        loans=before(prepared.loans, "created_at", "updated_at"),
        g2_transactions=before(
            prepared.g2_transactions, "completion_time", "initiation_time"
        ),
        customers=before(prepared.customers, "created_at"),
        cache_fingerprint=(
            f"{_prepared_data_cache_key(prepared)}|asof:"
            f"{pd.Timestamp(analysis_date):%Y-%m-%d}"
        ),
    )


@st.cache_data(show_spinner=False, max_entries=24)
def _read_excel_bytes(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    if not file_bytes:
        return pd.DataFrame()
    try:
        return pd.read_excel(BytesIO(file_bytes), engine="calamine")
    except ImportError:
        try:
            return pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
        except Exception as exc:
            raise ValueError(f"Impossible de lire `{file_name}` : {exc}") from exc
    except Exception as calamine_exc:
        try:
            return pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
        except Exception as openpyxl_exc:
            raise ValueError(
                f"Impossible de lire `{file_name}` : {openpyxl_exc} "
                f"(lecture rapide : {calamine_exc})"
            ) from openpyxl_exc


def _uploaded_dataframe(uploaded_file: Any) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    return _read_excel_bytes(uploaded_file.getvalue(), uploaded_file.name)


def _uploaded_dataframes(
    uploaded_files: Any,
    *,
    source_column: str,
) -> pd.DataFrame:
    """Fusionne plusieurs exports d'une source en conservant leur provenance."""
    if not uploaded_files:
        return pd.DataFrame()
    files = uploaded_files if isinstance(uploaded_files, (list, tuple)) else [uploaded_files]
    frames: list[pd.DataFrame] = []
    for file_order, uploaded_file in enumerate(files):
        frame = _uploaded_dataframe(uploaded_file)
        if frame.empty:
            continue
        frame = frame.copy()
        frame[source_column] = uploaded_file.name
        frame["ordre_fichier_import"] = file_order
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def _uploaded_g2_dataframes(uploaded_files: Any) -> pd.DataFrame:
    raw = _uploaded_dataframes(uploaded_files, source_column="fichier_source_g2")
    return promote_g2_statement_header(raw)


def _uploaded_files_fingerprint(**sources: Any) -> str:
    """Construire une clé de cache compacte sans hacher les DataFrames préparés."""
    digest = hashlib.blake2b(digest_size=20)
    for source_name, uploaded_files in sorted(sources.items()):
        digest.update(source_name.encode("utf-8"))
        files = (
            uploaded_files
            if isinstance(uploaded_files, (list, tuple))
            else ([uploaded_files] if uploaded_files is not None else [])
        )
        for file_order, uploaded_file in enumerate(files):
            payload = uploaded_file.getvalue()
            digest.update(str(file_order).encode("ascii"))
            digest.update(str(uploaded_file.name).encode("utf-8", errors="replace"))
            digest.update(len(payload).to_bytes(8, "little", signed=False))
            digest.update(payload)
    return digest.hexdigest()


def _mpesa_user_column_rename_enabled() -> bool:
    """Mirror the global sidebar option without recalculating business DataFrames."""

    return bool(st.session_state.get("credit_standardize_columns", True))


def _mpesa_dataframe(
    data: Any,
    *args: Any,
    column_config: dict[Any, Any] | None = None,
    **kwargs: Any,
) -> Any:
    """Render a Solution Numérique table with optional user-facing column names."""

    if isinstance(data, pd.DataFrame) and _mpesa_user_column_rename_enabled():
        data, column_mapping = prepare_dataframe_with_user_columns(data, enabled=True)
        column_config = translate_column_config_for_user_columns(column_config, column_mapping)  # type: ignore[assignment]
    return st.dataframe(data, *args, column_config=column_config, **kwargs)


@st.cache_data(show_spinner=False, max_entries=8)
def _create_excel_export_cached(
    export_report: dict[str, Any],
    print_orientation: str | None = None,
    rename_user_columns: bool = False,
) -> bytes:
    return create_excel_export(
        export_report,
        print_orientation=print_orientation,
        rename_user_columns=rename_user_columns,
    )


def _create_excel_export_current_sidebar(
    export_report: dict[str, Any],
    print_orientation: str | None = None,
) -> bytes:
    return _create_excel_export_cached(
        export_report,
        print_orientation=print_orientation,
        rename_user_columns=_mpesa_user_column_rename_enabled(),
    )


@st.cache_data(show_spinner=False, max_entries=12)
def _create_g2_dat_word_cached(
    word_report: dict[str, Any],
    period_text: str,
    direction_label: str,
) -> bytes:
    return create_g2_dat_word(
        word_report,
        period_text=period_text,
        direction_label=direction_label,
    )


@st.cache_data(show_spinner=False, max_entries=12)
def _create_customer_statement_word_cached(
    statement: pd.DataFrame,
    analysis_report: dict[str, pd.DataFrame],
    customer_id: str,
    customer_name: str,
    telephone: str,
    currency: str,
    entry_account_number: str,
    output_account_number: str,
    period_start: object | None,
    period_end: object | None,
    minimal: bool = False,
) -> bytes:
    return create_customer_statement_word(
        statement,
        analysis_report=analysis_report,
        customer_id=customer_id,
        customer_name=customer_name,
        telephone=telephone,
        currency=currency,
        entry_account_number=entry_account_number,
        output_account_number=output_account_number,
        period_start=period_start,
        period_end=period_end,
        minimal=minimal,
    )


@st.cache_data(show_spinner=False, max_entries=12)
def _create_customer_statement_pdf_cached(
    statement: pd.DataFrame,
    analysis_report: dict[str, pd.DataFrame],
    customer_id: str,
    customer_name: str,
    telephone: str,
    currency: str,
    entry_account_number: str,
    output_account_number: str,
    period_start: object | None,
    period_end: object | None,
    minimal: bool = False,
) -> bytes:
    return create_customer_statement_pdf(
        statement,
        analysis_report=analysis_report,
        customer_id=customer_id,
        customer_name=customer_name,
        telephone=telephone,
        currency=currency,
        entry_account_number=entry_account_number,
        output_account_number=output_account_number,
        period_start=period_start,
        period_end=period_end,
        minimal=minimal,
    )


@st.cache_data(show_spinner=False, max_entries=12)
def _create_customer_client_statement_word_cached(
    statement: pd.DataFrame,
    analysis_report: dict[str, pd.DataFrame],
    customer_id: str,
    customer_name: str,
    telephone: str,
    currency: str,
    entry_account_number: str,
    output_account_number: str,
    period_start: object | None,
    period_end: object | None,
    minimal: bool = False,
) -> bytes:
    return create_customer_client_statement_word(
        statement,
        analysis_report=analysis_report,
        customer_id=customer_id,
        customer_name=customer_name,
        telephone=telephone,
        currency=currency,
        entry_account_number=entry_account_number,
        output_account_number=output_account_number,
        period_start=period_start,
        period_end=period_end,
        minimal=minimal,
    )


@st.cache_data(show_spinner=False, max_entries=12)
def _create_customer_client_statement_pdf_cached(
    statement: pd.DataFrame,
    analysis_report: dict[str, pd.DataFrame],
    customer_id: str,
    customer_name: str,
    telephone: str,
    currency: str,
    entry_account_number: str,
    output_account_number: str,
    period_start: object | None,
    period_end: object | None,
    minimal: bool = False,
) -> bytes:
    return create_customer_client_statement_pdf(
        statement,
        analysis_report=analysis_report,
        customer_id=customer_id,
        customer_name=customer_name,
        telephone=telephone,
        currency=currency,
        entry_account_number=entry_account_number,
        output_account_number=output_account_number,
        period_start=period_start,
        period_end=period_end,
        minimal=minimal,
    )


@st.cache_data(show_spinner=False, max_entries=12)
def _create_turbo_balance_word_cached(
    report: dict[str, pd.DataFrame],
    period_start: object | None,
    period_end: object | None,
) -> bytes:
    return create_turbo_balance_word(
        report,
        period_start=period_start,
        period_end=period_end,
    )


@st.cache_data(show_spinner=False, max_entries=12)
def _create_turbo_balance_pdf_cached(
    report: dict[str, pd.DataFrame],
    period_start: object | None,
    period_end: object | None,
) -> bytes:
    return create_turbo_balance_pdf(
        report,
        period_start=period_start,
        period_end=period_end,
    )


@st.cache_data(show_spinner=False, max_entries=12)
def _create_turbo_deposit_withdrawal_pivot_word_cached(
    report: dict[str, pd.DataFrame],
    period_start: object | None,
    period_end: object | None,
) -> bytes:
    return create_turbo_balance_word(
        report,
        period_start=period_start,
        period_end=period_end,
        balance_by_date=True,
    )


@st.cache_data(
    show_spinner=False,
    max_entries=24,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_customer_transaction_analysis_cached(
    prepared: MpesaPreparedData,
    customer_id: str,
    currency: str,
    operation_types: tuple[str, ...],
    date_start: object | None,
    date_end: object | None,
    reference_query: str,
    annual_interest_rate_pct: float,
) -> dict[str, pd.DataFrame]:
    return build_customer_transaction_analysis(
        prepared,
        customer_id,
        currency=currency,
        operation_types=operation_types,
        date_start=date_start,
        date_end=date_end,
        reference_query=reference_query,
        annual_interest_rate_pct=annual_interest_rate_pct,
    )


@st.cache_data(
    show_spinner=False,
    max_entries=12,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_statement_cached(
    prepared: MpesaPreparedData,
    customer_id: str,
    opening_balances: tuple[tuple[str, float | None], ...],
) -> dict[str, Any]:
    return build_mpesa_statement(
        prepared,
        customer_id,
        opening_balances=dict(opening_balances),
    )


@st.cache_data(
    show_spinner=False,
    max_entries=12,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_g2_daily_savings_report_cached(
    prepared: MpesaPreparedData,
) -> dict[str, pd.DataFrame]:
    return build_g2_daily_savings_report(prepared)


@st.cache_data(
    show_spinner=False,
    max_entries=4,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_turbo_operation_events_cached(
    prepared: MpesaPreparedData,
) -> dict[str, pd.DataFrame]:
    """Consolide les fichiers de la Solution Numérique une seule fois par jeu de televersements."""
    return build_turbo_operation_events(prepared.transactions)


@st.cache_data(
    show_spinner=False,
    max_entries=16,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_weekly_comparison_cached(
    prepared: MpesaPreparedData,
    as_of_date: object,
    comparison_period: str = DEFAULT_MPESA_COMPARISON_PERIOD,
    date_start: object | None = None,
) -> pd.DataFrame:
    """Compare deux périodes en réutilisant le journal consolidé en cache."""
    operation_journal = _build_turbo_operation_events_cached(prepared)
    scoped_prepared = _prepared_data_as_of(prepared, as_of_date)
    return build_mpesa_weekly_comparison(
        scoped_prepared,
        as_of_date=as_of_date,
        date_start=date_start,
        comparison_period=comparison_period,
        turbo_events=operation_journal["events"],
        turbo_transaction_lines=operation_journal["lines"],
    )


@st.cache_data(
    show_spinner=False,
    max_entries=8,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_management_dashboard_cached(
    prepared: MpesaPreparedData,
    dat_annual_interest_rate_pct: float,
    date_start: object,
    date_end: object,
    frequency: str,
    fractionation_cdf: float,
    fractionation_usd: float,
    important_cdf: float,
    important_usd: float,
) -> dict[str, Any]:
    operation_journal = _build_turbo_operation_events_cached(prepared)
    scoped_prepared = _prepared_data_as_of(prepared, date_end)
    return build_mpesa_management_dashboard(
        scoped_prepared,
        date_start=date_start,
        as_of_date=date_end,
        frequency=frequency,
        dat_annual_interest_rate_pct=dat_annual_interest_rate_pct,
        fractionation_thresholds={"CDF": fractionation_cdf, "USD": fractionation_usd},
        large_transaction_thresholds={"CDF": important_cdf, "USD": important_usd},
        turbo_events=operation_journal["events"],
        turbo_transaction_lines=operation_journal["lines"],
    )


@st.cache_data(
    show_spinner=False,
    max_entries=8,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_statistics_report_cached(
    prepared: MpesaPreparedData,
    historical_prepared: MpesaPreparedData,
    date_start: object,
    date_end: object,
    frequency: str,
    comparison_period: str,
) -> dict[str, Any]:
    operation_journal = _build_turbo_operation_events_cached(prepared)
    historical_operation_journal = _build_turbo_operation_events_cached(
        historical_prepared
    )
    scoped_prepared = _prepared_data_as_of(prepared, date_end)
    scoped_historical_prepared = _prepared_data_as_of(
        historical_prepared,
        date_end,
    )
    total_loaded_clients = count_mpesa_loaded_customers(prepared)
    return build_mpesa_statistics_report(
        scoped_prepared,
        date_start=date_start,
        date_end=date_end,
        frequency=frequency,
        comparison_period=comparison_period,
        turbo_events=operation_journal["events"],
        turbo_transaction_lines=operation_journal["lines"],
        historical_prepared=scoped_historical_prepared,
        historical_turbo_events=historical_operation_journal["events"],
        historical_turbo_transaction_lines=historical_operation_journal["lines"],
        total_loaded_clients_override=total_loaded_clients,
    )


@st.cache_data(
    show_spinner=False,
    max_entries=8,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_clients_report_cached(
    prepared: MpesaPreparedData,
    date_start: object,
    date_end: object,
    frequency: str,
    inactivity_threshold_days: int,
    occasional_max_operations: int,
) -> dict[str, Any]:
    operation_journal = _build_turbo_operation_events_cached(prepared)
    scoped_prepared = _prepared_data_as_of(prepared, date_end)
    return build_mpesa_clients_report(
        scoped_prepared,
        date_start=date_start,
        date_end=date_end,
        frequency=frequency,
        inactivity_threshold_days=inactivity_threshold_days,
        occasional_max_operations=occasional_max_operations,
        turbo_events=operation_journal["events"],
        turbo_transaction_lines=operation_journal["lines"],
    )


@st.cache_data(
    show_spinner=False,
    max_entries=12,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_forecast_report_cached(
    prepared: MpesaPreparedData,
    reference_date: object,
    horizon_days: int,
    confidence_level: int,
    annual_interest_rate_pct: float,
) -> dict[str, Any]:
    operation_journal = _build_turbo_operation_events_cached(prepared)
    scoped_prepared = _prepared_data_as_of(prepared, reference_date)
    return build_mpesa_forecast_report(
        scoped_prepared,
        reference_date=reference_date,
        horizon_days=horizon_days,
        confidence_level=confidence_level,
        annual_interest_rate_pct=annual_interest_rate_pct,
        turbo_events=operation_journal["events"],
    )


@st.cache_data(
    show_spinner=False,
    max_entries=16,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_dat_maturity_analysis_cached(
    prepared: MpesaPreparedData,
    analysis_date: object,
    annual_interest_rate_pct: float,
    preparation_horizon_days: int,
) -> dict[str, pd.DataFrame]:
    return build_mpesa_dat_maturity_analysis(
        prepared.fixed_savings,
        as_of_date=analysis_date,
        annual_interest_rate_pct=annual_interest_rate_pct,
        preparation_horizon_days=preparation_horizon_days,
    )


@st.cache_data(
    show_spinner=False,
    max_entries=8,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_savings_cockpit_cached(
    prepared: MpesaPreparedData,
    date_start: object,
    date_end: object,
    frequency: str,
    annual_interest_rate_pct: float,
    inactivity_threshold_days: int,
    maturity_horizon_days: int,
    large_savings_usd: float,
    large_savings_cdf: float,
) -> dict[str, Any]:
    scoped_prepared = _prepared_data_as_of(prepared, date_end)
    return build_mpesa_savings_cockpit(
        scoped_prepared,
        date_start=date_start,
        date_end=date_end,
        frequency=frequency,
        annual_interest_rate_pct=annual_interest_rate_pct,
        inactivity_threshold_days=inactivity_threshold_days,
        maturity_horizon_days=maturity_horizon_days,
        large_savings_thresholds={"USD": large_savings_usd, "CDF": large_savings_cdf},
    )


@st.cache_data(
    show_spinner=False,
    max_entries=12,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_loan_savings_reconciliation_cached(
    prepared: MpesaPreparedData,
) -> dict[str, pd.DataFrame]:
    return build_loan_savings_reconciliation(
        prepared.loans,
        prepared.current_savings,
        prepared.fixed_savings,
    )


@st.cache_data(
    show_spinner=False,
    max_entries=8,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_credit_cockpit_cached(
    prepared: MpesaPreparedData,
    date_start: object,
    date_end: object,
    frequency: str,
    dat_annual_interest_rate_pct: float,
    high_exposure_top_n: int,
) -> dict[str, Any]:
    operation_journal = _build_turbo_operation_events_cached(prepared)
    scoped_prepared = _prepared_data_as_of(prepared, date_end)
    return build_mpesa_credit_cockpit(
        scoped_prepared,
        date_start=date_start,
        date_end=date_end,
        frequency=frequency,
        dat_annual_interest_rate_pct=dat_annual_interest_rate_pct,
        high_exposure_top_n=high_exposure_top_n,
        turbo_events=operation_journal["events"],
        turbo_transaction_lines=operation_journal["lines"],
    )


@st.cache_data(
    show_spinner=False,
    max_entries=12,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_accounting_analysis_cached(
    prepared: MpesaPreparedData,
    date_start: object,
    date_end: object,
) -> dict[str, pd.DataFrame]:
    return build_mpesa_accounting_analysis(
        prepared,
        date_start=date_start,
        date_end=date_end,
    )


@st.cache_data(show_spinner=False, max_entries=4)
def _build_prepared_data(
    upload_fingerprint: str,
    _transactions_raw: pd.DataFrame,
    _savings_raw: pd.DataFrame,
    _loans_raw: pd.DataFrame,
    _g2_raw: pd.DataFrame,
    _customers_raw: pd.DataFrame,
    _perfect_raw: pd.DataFrame,
) -> tuple[MpesaPreparedData, dict[str, list[str]]]:
    transactions = prepare_transactions(_transactions_raw) if _transactions_raw is not None and not _transactions_raw.empty else pd.DataFrame()
    savings_accounts = prepare_savings_accounts(_savings_raw)
    account_types = savings_accounts.get(
        "account_type", pd.Series("", index=savings_accounts.index)
    )
    current = savings_accounts.loc[account_types.eq("NORMAL SAVINGS")].copy()
    fixed = savings_accounts.loc[account_types.eq("FIXED SAVINGS")].copy()
    fixed_control = pd.DataFrame()
    loans = prepare_loans(_loans_raw)
    g2_transactions = prepare_g2_transactions(_g2_raw)
    customers = prepare_customers(_customers_raw)
    perfect_clients = prepare_perfect_clients(_perfect_raw)
    missing = {
        "Transactions M-PESA_Turbo": validate_required_columns(transactions, TRANSACTION_REQUIRED_COLUMNS, "Transactions M-PESA_Turbo")
        if not transactions.empty
        else sorted(TRANSACTION_REQUIRED_COLUMNS),
        "Epargne courante_Turbo": validate_required_columns(current, CURRENT_SAVINGS_REQUIRED_COLUMNS, "Epargne courante")
        if not current.empty
        else [],
        "DAT_Turbo": validate_required_columns(fixed, FIXED_SAVINGS_REQUIRED_COLUMNS, "DAT")
        if not fixed.empty
        else [],
        "Credits_Turbo": validate_required_columns(loans, {"loan_id", "customer_id"}, "Credits") if not loans.empty else [],
        "Transactions M-PESA_G2": validate_required_columns(g2_transactions, G2_TRANSACTION_REQUIRED_COLUMNS, "Transactions M-PESA_G2") if not g2_transactions.empty else [],
        "Clients_Turbo": validate_required_columns(customers, CUSTOMERS_REQUIRED_COLUMNS, "Clients_Turbo") if not customers.empty else [],
        "Clients_Perfect": validate_required_columns(perfect_clients, PERFECT_CLIENTS_REQUIRED_COLUMNS, "Clients_Perfect") if not perfect_clients.empty else [],
    }
    transactions = enrich_transactions_with_g2_customer_names(transactions, g2_transactions)
    current = enrich_turbo_with_g2_customer_names(current, g2_transactions, phone_column="msisdn")
    fixed = enrich_turbo_with_g2_customer_names(fixed, g2_transactions, phone_column="msisdn")
    loans = enrich_turbo_with_g2_customer_names(loans, g2_transactions, phone_column="msisdn1")
    customers = enrich_turbo_with_g2_customer_names(customers, g2_transactions, phone_column="msisdn1")
    load_report = build_load_report(
        {
            "Transactions M-PESA_Turbo": transactions,
            "Epargne courante_Turbo": current,
            "DAT_Turbo": fixed,
            "Credits_Turbo": loans,
            "Transactions M-PESA_G2": g2_transactions,
            "Clients_Turbo": customers,
            "Clients_Perfect": perfect_clients,
        },
        missing,
    )
    return MpesaPreparedData(
        transactions=transactions,
        current_savings=current,
        fixed_savings=fixed,
        loans=loans,
        load_report=load_report,
        g2_transactions=g2_transactions,
        customers=customers,
        perfect_clients=perfect_clients,
        cache_fingerprint=upload_fingerprint,
        fixed_savings_control=fixed_control,
    ), missing


def _period_label(transactions: pd.DataFrame) -> str:
    if transactions.empty or "created_at" not in transactions.columns:
        return "-"
    dates = pd.to_datetime(transactions["created_at"], errors="coerce").dropna()
    if dates.empty:
        return "-"
    return f"{dates.min():%Y-%m-%d %H:%M} -> {dates.max():%Y-%m-%d %H:%M}"


def _currency_options(df: pd.DataFrame) -> list[str]:
    if df.empty or "currency_code" not in df.columns:
        return []
    return sorted(value for value in df["currency_code"].dropna().astype(str).unique() if value.strip())


def _filter_value_options(series: pd.Series) -> list[str]:
    if series is None:
        return []
    cleaned = (
        series.astype("string")
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
    )
    return sorted(cleaned.tolist(), key=lambda value: str(value).casefold())


def _apply_local_multiselect_filters(
    df: pd.DataFrame,
    filter_columns: list[str],
    *,
    key_prefix: str,
) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    available_columns = [column for column in filter_columns if column in df.columns]
    if not available_columns:
        return df.copy()

    active_filters: dict[str, list[str]] = {}
    visible_column_names = (
        resolve_user_column_mapping(pd.Index(available_columns))
        if _mpesa_user_column_rename_enabled()
        else {}
    )
    widgets = st.columns(min(3, max(1, len(available_columns))))
    for index, column in enumerate(available_columns):
        options = _filter_value_options(df[column])
        if not options:
            continue
        with widgets[index % len(widgets)]:
            selected_values = st.multiselect(
                visible_column_names.get(column, column),
                options=options,
                default=[],
                key=f"{key_prefix}_{column}",
                placeholder="Choisir une ou plusieurs valeurs",
                help="Aucune valeur selectionnee = toutes les valeurs.",
            )
        if selected_values:
            active_filters[column] = [str(value).strip() for value in selected_values]

    filtered = df.copy()
    for column, selected_values in active_filters.items():
        filtered = filtered.loc[filtered[column].astype("string").str.strip().isin(selected_values)].copy()
    return filtered.reset_index(drop=True)


@st.fragment
def _render_import_tab(prepared: MpesaPreparedData, missing: dict[str, list[str]]) -> None:
    render_panel_title("Controle de chargement")
    report = prepared.load_report
    if report.empty:
        st.info("Aucun fichier n'a encore ete charge.")
        return
    _mpesa_dataframe(report, width="stretch", hide_index=True)
    prepared_frames = {
        "Transactions M-PESA_Turbo": prepared.transactions,
        "Epargne courante_Turbo": prepared.current_savings,
        "DAT_Turbo": prepared.fixed_savings,
        "Credits_Turbo": prepared.loans,
        "Transactions M-PESA_G2": prepared.g2_transactions,
        "Clients_Turbo": prepared.customers,
        "Clients_Perfect": prepared.perfect_clients,
    }
    for label, columns in missing.items():
        if columns:
            frame = prepared_frames.get(label, pd.DataFrame())
            available = ", ".join(map(str, frame.columns)) or "aucune"
            st.warning(
                f"{label} : colonnes obligatoires manquantes : {', '.join(columns)}. "
                f"Colonnes disponibles : {available}."
            )
    if not prepared.transactions.empty:
        clients = prepared.transactions["customer_id"].dropna().astype(str).nunique() if "customer_id" in prepared.transactions.columns else 0
        currencies = ", ".join(_currency_options(prepared.transactions)) or "-"
        render_kpi_cards(
            [
                ("Transactions [Solution Numérique]", _format_count(len(prepared.transactions)), "Lignes importees", "blue"),
                (
                    "Clients distincts",
                    _format_count(clients),
                    "Identifiants observes dans les transactions",
                    "navy",
                ),
                ("Periode", _period_label(prepared.transactions), "Transactions", "green"),
                ("Devises", currencies, "Codes detectes", "orange"),
            ]
        )
    savings_frames = [prepared.current_savings, prepared.fixed_savings]
    has_savings_data = any(not frame.empty for frame in savings_frames)
    source_complete_available_in_data = any(
        not frame.empty
        and "source_savings_account_complete" in frame.columns
        and bool(frame["source_savings_account_complete"].fillna(False).astype(bool).any())
        for frame in savings_frames
    )
    if (
        has_savings_data
        and not source_complete_available_in_data
        and (prepared.current_savings.empty or prepared.fixed_savings.empty)
    ):
        missing_summary = (
            "Customers with Current Savings Account"
            if prepared.current_savings.empty
            else "Customers with Fixed Savings Account"
        )
        st.warning(
            "Mode de compatibilite incomplet : chargez aussi "
            f"{missing_summary} dans le meme emplacement Savings Account."
        )

    savings_reconciliation = build_savings_accounts_reconciliation(prepared)
    savings_summary = savings_reconciliation.get("synthese", pd.DataFrame())
    if not savings_summary.empty:
        savings_row = savings_summary.iloc[0]
        source_complete_available = bool(
            savings_row.get("source_savings_account_complete_disponible", False)
        )
        has_dat_control = int(savings_row.get("dat_export_resume", 0)) > 0
        render_panel_title(
            "Rapprochement Savings Account / DAT"
            if has_dat_control
            else (
                "Composition de Savings Account"
                if source_complete_available
                else "Compatibilite des syntheses d'epargne"
            )
        )
        render_kpi_cards(
            [
                (
                    (
                        "Comptes courants [Savings Account]"
                        if source_complete_available
                        else "Comptes courants positifs [synthese]"
                    ),
                    _format_count(savings_row.get("comptes_courants", 0)),
                    (
                        "Produits Open Savings / Current account"
                        if source_complete_available
                        else "Vue Customers with Current Savings Account"
                    ),
                    "blue",
                ),
                (
                    (
                        "DAT historiques [Savings Account]"
                        if source_complete_available
                        else "DAT positifs [synthese]"
                    ),
                    _format_count(savings_row.get("dat_total_source_complete", 0)),
                    (
                        "Soldes positifs et soldes nuls conserves"
                        if source_complete_available
                        else "Vue Customers with Fixed Savings Account"
                    ),
                    "navy",
                ),
                (
                    "DAT a solde positif",
                    _format_count(savings_row.get("dat_solde_positif", 0)),
                    "DAT avec encours observe",
                    "green",
                ),
                (
                    (
                        "DAT soldes / historiques"
                        if source_complete_available
                        else "DAT a solde nul disponibles"
                    ),
                    _format_count(savings_row.get("dat_solde_nul", 0)),
                    (
                        "DAT a solde nul conserves"
                        if source_complete_available
                        else "Indisponibles dans les vues resumees"
                    ),
                    "orange",
                ),
            ]
        )
        reconciliation_status = str(savings_row.get("statut_rapprochement", ""))
        if has_dat_control:
            reconciliation_message = (
                f"Export DAT resume : {_format_count(savings_row.get('dat_export_resume', 0))} ligne(s); "
                f"retrouvees dans Savings Account : {_format_count(savings_row.get('dat_export_retrouves', 0))}. "
                f"Statut : {reconciliation_status}."
            )
        else:
            reconciliation_message = (
                "Savings Account est la source autonome des comptes courants et des DAT; "
                "aucun export Current Savings ou Fixed Savings supplementaire n'est requis."
                if source_complete_available
                else (
                    "Mode de compatibilite actif : les syntheses Current Savings et Fixed Savings couvrent "
                    "les comptes a solde positif, mais pas les comptes a solde nul ni tout l'historique; "
                    "chargez Savings Account pour l'analyse exhaustive."
                    if int(savings_row.get("comptes_courants", 0)) > 0
                    else (
                        "Mode de compatibilite incomplet : la synthese Fixed Savings est exploitee, mais la "
                        "synthese Current Savings manque. Les comptes a solde nul et l'historique exhaustif "
                        "restent indisponibles."
                    )
                )
            )
        if reconciliation_status in {"Concordance exacte", "Source autonome"}:
            st.success(reconciliation_message)
        else:
            _render_alert_banner(reconciliation_message)
        savings_gaps = savings_reconciliation.get("ecarts", pd.DataFrame())
        if not savings_gaps.empty:
            with st.expander("Afficher les ecarts Savings Account / DAT", expanded=False):
                _mpesa_dataframe(
                    savings_gaps,
                    width="stretch",
                    hide_index=True,
                )
    unnamed_count = sum(
        int(frame.columns.astype(str).str.match(r"^Unnamed(:|$)", na=False).sum())
        for frame in [prepared.transactions, prepared.current_savings, prepared.fixed_savings, prepared.loans]
        if not frame.empty
    )
    st.caption(f"Colonnes `Unnamed` restantes apres nettoyage : {unnamed_count}.")
    render_panel_title("Controle des donnees")
    st.caption(
        "Les controles techniques et les anomalies Transactions sont maintenant integres a l'importation."
    )
    _render_diagnostics_content(prepared, None)


def _filter_statement(
    statement: pd.DataFrame,
    *,
    key_prefix: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    context: dict[str, Any] = {
        "currency": "Toutes",
        "currencies": [],
        "operation_types": [],
        "date_start": None,
        "date_end": None,
        "reference_query": "",
    }
    if statement.empty:
        return statement, context
    filtered = statement.copy()
    with st.container(border=True):
        st.caption(
            "Définissez le périmètre du relevé. Les mêmes filtres alimentent l'aperçu, le Word, le PDF et l'Excel client."
        )
        first_row, second_row = st.columns(2)
        currencies = _currency_options(filtered)
        selected_currency = "Toutes"
        selected_currencies: list[str] = []
        if currencies:
            selected_currencies = first_row.multiselect(
                "Devise",
                currencies,
                default=currencies,
                key=f"{key_prefix}_currency",
                placeholder="Sélectionner les devises",
                help=(
                    "Choisissez une ou plusieurs devises pour limiter le relevé. "
                    "Aucune devise choisie = toutes les devises disponibles; les montants "
                    "et les soldes restent présentés séparément par devise."
                ),
            )
            selected_currencies = [str(value).strip() for value in selected_currencies if str(value).strip()]
            if selected_currencies:
                filtered = filtered.loc[filtered["currency_code"].astype(str).isin(selected_currencies)]
            selected_currency = (
                selected_currencies[0]
                if len(selected_currencies) == 1
                else "Toutes"
            )
            context["currency"] = selected_currency
            context["currencies"] = selected_currencies
        currency_key_token = "_".join(selected_currencies) if selected_currencies else "Toutes"
        operation_types = sorted(filtered["type_operation"].dropna().astype(str).unique()) if "type_operation" in filtered.columns else []
        if operation_types:
            default_operation_types = [
                operation_type
                for operation_type in operation_types
                if operation_type in CUSTOMER_STATEMENT_FOCUS_OPERATION_TYPES
            ]
            selected_types = second_row.multiselect(
                "Type d'opération",
                operation_types,
                default=default_operation_types,
                key=f"{key_prefix}_{currency_key_token}_type",
                placeholder="Sélectionner les opérations",
                help=(
                    "Par défaut : dépôts, retraits vers M-PESA, décaissements de crédit et remboursements de crédit. "
                    "Aucune option choisie = tous les types d'opération."
                ),
            )
            context["operation_types"] = selected_types
            if selected_types:
                filtered = filtered.loc[filtered["type_operation"].isin(selected_types)]
        if "created_at" in filtered.columns:
            dates = pd.to_datetime(filtered["created_at"], errors="coerce").dropna()
            if not dates.empty:
                date_key = f"{key_prefix}_{currency_key_token}_{dates.min():%Y%m%d}_{dates.max():%Y%m%d}"
                start_column, end_column = st.columns(2)
                start = start_column.date_input(
                    "Date de début",
                    value=dates.min().date(),
                    min_value=dates.min().date(),
                    max_value=dates.max().date(),
                    key=f"{date_key}_start_date",
                    format="DD/MM/YYYY",
                    help="Première journée incluse dans l'extrait client.",
                )
                end = end_column.date_input(
                    "Date de fin",
                    value=dates.max().date(),
                    min_value=dates.min().date(),
                    max_value=dates.max().date(),
                    key=f"{date_key}_end_date",
                    format="DD/MM/YYYY",
                    help="Dernière journée incluse dans l'extrait client.",
                )
                context["date_start"] = start
                context["date_end"] = end
                if start > end:
                    st.error(
                        "La date de début doit être antérieure ou égale à la date de fin.",
                        icon=":material/error:",
                    )
                    return filtered.iloc[0:0].copy(), context
                filtered = filtered.loc[
                    pd.to_datetime(filtered["created_at"], errors="coerce").between(
                        pd.Timestamp(start),
                        pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1),
                    )
                ]
        ref_query = st.text_input(
            "Référence, DAT ou crédit",
            key=f"{key_prefix}_reference",
            help=(
                "Filtre facultatif permettant de retrouver une opération à partir "
                "de tout ou partie de sa référence, de la référence du DAT "
                "ou de celle du crédit. Laissez vide pour conserver toutes les "
                "références."
            ),
        ).strip()
    context["reference_query"] = ref_query
    if ref_query:
        ref_columns = ["operation_reference", "reference_dat_operation", "reference_credit_operation", "references_internes"]
        mask = pd.Series(False, index=filtered.index)
        for column in ref_columns:
            if column in filtered.columns:
                mask = mask | filtered[column].astype("string").str.contains(ref_query, case=False, regex=False, na=False)
        filtered = filtered.loc[mask]
    return filtered.reset_index(drop=True), context


def _render_customer_kpis(summary: pd.DataFrame) -> None:
    if summary.empty:
        st.info("Aucune synthese client disponible.")
        return
    for _, row in summary.iterrows():
        currency = row.get("devise", "")
        render_panel_title(f"Devise {currency}")
        render_kpi_cards(
            [
                ("Operations", _format_count(row.get("nombre_operations_mpesa")), f"Devise {currency}", "blue"),
                ("Entrees", _format_amount(row.get("total_entrees_mpesa")), f"Devise {currency}", "green"),
                ("Sorties", _format_amount(row.get("total_sorties_mpesa")), f"Devise {currency}", "orange"),
                ("Net", _format_amount(row.get("mouvement_net")), f"Devise {currency}", "navy"),
            ]
        )


def _render_statement_charts(statement: pd.DataFrame) -> None:
    if statement.empty:
        st.info("Aucune donnee filtree pour les graphiques.")
        return
    chart_df = statement.copy()
    chart_df["created_at"] = pd.to_datetime(chart_df["created_at"], errors="coerce")
    chart_df = chart_df.dropna(subset=["created_at"])
    if chart_df.empty:
        st.info("Aucune date valide pour construire les graphiques.")
        return
    chart_df = chart_df.sort_values(["currency_code", "created_at"]).reset_index(drop=True)
    chart_df["cumul_net_flux_bisou"] = (
        pd.to_numeric(chart_df["mouvement_net_mpesa"], errors="coerce")
        .fillna(0.0)
        .groupby(chart_df["currency_code"], dropna=False)
        .cumsum()
    )
    chart_df["jour"] = chart_df["created_at"].dt.date
    left, right = st.columns(2)
    with left:
        render_panel_title("Mouvement net")
        fig = px.line(chart_df, x="created_at", y="mouvement_net_mpesa", color="currency_code", markers=True)
        style_standard_line(fig, height=330, tickangle=-20)
        st_plot(fig, key="mpesa_net_movement", height=330)
    with right:
        render_panel_title("Entrees et sorties par jour")
        daily = chart_df.groupby(["jour", "currency_code"], as_index=False).agg(entrees=("entree_mpesa", "sum"), sorties=("sortie_mpesa", "sum"))
        long_daily = daily.melt(id_vars=["jour", "currency_code"], value_vars=["entrees", "sorties"], var_name="sens", value_name="montant")
        fig = px.bar(long_daily, x="jour", y="montant", color="sens", facet_col="currency_code")
        style_standard_vertical_bar(fig, height=330, tickangle=-20)
        st_plot(fig, key="mpesa_daily_in_out", height=330)
    with st.expander("Afficher les graphiques complementaires", expanded=False):
        left, right = st.columns(2)
        with left:
            render_panel_title("Cumul net des flux")
            fig = px.line(
                chart_df,
                x="created_at",
                y="cumul_net_flux_bisou",
                color="currency_code",
                markers=True,
            )
            style_standard_line(fig, height=330, tickangle=-20)
            st_plot(fig, key="mpesa_bisou_flow_cumulative", height=330)
        with right:
            render_panel_title("Operations par type")
            type_df = chart_df.groupby("type_operation", as_index=False).size().rename(columns={"size": "nombre"})
            fig = px.pie(type_df, names="type_operation", values="nombre", hole=0.48)
            style_standard_donut(fig, height=330)
            st_plot(fig, key="mpesa_operation_types", height=330)
        left, right = st.columns(2)
        with left:
            if "solde_dat_total_au_moment" in chart_df.columns:
                render_panel_title("DAT total au moment")
                fig = px.line(chart_df, x="created_at", y="solde_dat_total_au_moment", color="currency_code", markers=True)
                style_standard_line(fig, height=330, tickangle=-20)
                st_plot(fig, key="mpesa_dat_total", height=330)
        with right:
            if "solde_epargne_au_moment" in chart_df.columns:
                render_panel_title("Epargne courante au moment")
                fig = px.line(chart_df, x="created_at", y="solde_epargne_au_moment", color="currency_code", markers=True)
                style_standard_line(fig, height=330, tickangle=-20)
                st_plot(fig, key="mpesa_savings_balance", height=330)


def _format_customer_analysis_dates(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.copy()
    for column in display.columns:
        if "date" in str(column).lower() or column in {"created_at", "premiere_operation", "derniere_operation"}:
            parsed = pd.to_datetime(display[column], errors="coerce")
            if parsed.notna().any():
                display[column] = parsed.dt.strftime("%d/%m/%Y %H:%M:%S")
    return display


def _render_customer_journey_analysis(analysis: dict[str, pd.DataFrame]) -> None:
    behavior = analysis.get("comportement_turbo", pd.DataFrame())
    milestones = analysis.get("jalons_turbo", pd.DataFrame())
    path = analysis.get("parcours_turbo", pd.DataFrame())
    if behavior.empty and milestones.empty and path.empty:
        st.info("Aucun parcours financier ne correspond aux filtres actifs.")
        return

    for _, row in behavior.iterrows():
        currency = str(row.get("currency_code", ""))
        render_panel_title(f"Comportement observe - {currency}")
        render_kpi_cards(
            [
                ("Jours actifs", _format_count(row.get("jours_actifs")), f"Devise {currency}", "blue"),
                (
                    "Operations / jour actif",
                    _format_amount(row.get("operations_par_jour_actif")),
                    "Frequence observee",
                    "navy",
                ),
                ("Montant median", _format_amount(row.get("montant_median")), currency, "green"),
                ("Plus forte operation", _format_amount(row.get("plus_forte_operation")), currency, "orange"),
                (
                    "Moment frequent",
                    f"{row.get('jour_semaine_frequent', '-')} - {row.get('heure_frequente', '-')}",
                    "Sur le perimetre filtre",
                    "slate",
                ),
                (
                    "Plus longue inactivite",
                    _format_amount(row.get("plus_longue_inactivite_jours")),
                    "Jours entre deux operations",
                    "red",
                ),
            ]
        )
        first = pd.to_datetime(row.get("premiere_operation"), errors="coerce")
        last = pd.to_datetime(row.get("derniere_operation"), errors="coerce")
        render_summary_box(
            f"Lecture du parcours {currency}",
            [
                f"Premiere operation : {first:%d/%m/%Y %H:%M}" if pd.notna(first) else "Premiere operation : -",
                f"Derniere operation : {last:%d/%m/%Y %H:%M}" if pd.notna(last) else "Derniere operation : -",
                f"Type le plus frequent : {row.get('type_operation_frequent', '-')}",
                (
                    f"Intervalle median : {_format_amount(row.get('intervalle_median_heures'))} heure(s)"
                    if pd.notna(row.get("intervalle_median_heures"))
                    else "Intervalle median : non calculable avec une seule operation"
                ),
            ],
        )

    if not milestones.empty:
        render_panel_title("Jalons du parcours financier")
        st.caption(
            "Une ligne par devise et type d'operation. Les montants CDF et USD restent toujours separes."
        )
        _mpesa_dataframe(
            _format_customer_analysis_dates(milestones),
            width="stretch",
            hide_index=True,
        )
    if not path.empty:
        with st.expander("Afficher la chronologie complete", expanded=False):
            _mpesa_dataframe(
                _format_customer_analysis_dates(path),
                width="stretch",
                hide_index=True,
            )


def _render_customer_repayments(analysis: dict[str, pd.DataFrame]) -> None:
    repayment_summary = analysis.get("remboursements_turbo_synthese_client", pd.DataFrame())
    repayment_detail = analysis.get("remboursements_turbo_detail_client", pd.DataFrame())

    if repayment_summary.empty:
        st.info("Aucun remboursement ne correspond aux mouvements et aux filtres actifs.")
        return

    st.caption(
        "Les montants ci-dessous proviennent exclusivement des écritures de remboursement observées "
        "dans les transactions. Les décaissements et les positions de crédit ne sont pas affichés."
    )
    for _, row in repayment_summary.iterrows():
        currency = str(row.get("currency_code", ""))
        render_panel_title(f"Remboursements observés - {currency}")
        render_kpi_cards(
            [
                (
                    "Remboursements",
                    _format_count(row.get("nombre_remboursements")),
                    f"Devise {currency}",
                    "blue",
                ),
                (
                    "Montant payé",
                    _format_amount(row.get("montant_paye_observe")),
                    currency,
                    "navy",
                ),
                (
                    "Intérêts observés",
                    _format_amount(row.get("interet_observe")),
                    currency,
                    "green",
                ),
                (
                    "Pénalités observées",
                    _format_amount(row.get("penalite_observee")),
                    currency,
                    "red",
                ),
            ]
        )

    if repayment_detail.empty:
        return
    display_columns = [
        "created_at",
        "event_reference",
        "currency_code",
        "montant_paye_observe",
        "interet_observe",
        "origine_remboursement_observee",
        "penalite_observee",
    ]
    display_columns = [column for column in display_columns if column in repayment_detail.columns]
    _mpesa_dataframe(
        repayment_detail[display_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "created_at": st.column_config.DatetimeColumn("Date", format="DD/MM/YYYY HH:mm"),
            "event_reference": st.column_config.TextColumn("Référence", pinned=True),
            "currency_code": st.column_config.TextColumn("Devise"),
            "montant_paye_observe": st.column_config.NumberColumn("Montant payé"),
            "interet_observe": st.column_config.NumberColumn("Intérêts"),
            "origine_remboursement_observee": st.column_config.TextColumn("Origine du paiement"),
            "penalite_observee": st.column_config.NumberColumn("Pénalités"),
        },
    )


def _render_customer_turbo_controls(analysis: dict[str, pd.DataFrame]) -> None:
    controls = analysis.get("controles_client_turbo", pd.DataFrame())
    if controls.empty:
        st.info("Aucun controle disponible pour le perimetre filtre.")
        return
    review_mask = controls.get(
        "statut_controle_turbo", pd.Series("", index=controls.index)
    ).astype("string").eq("A verifier")
    review = controls.loc[review_mask].copy()
    render_kpi_cards(
        [
            ("Operations controlees", _format_count(len(controls)), "Perimetre filtre", "blue"),
            ("Montants miroirs conformes", _format_count(controls["controle_montant_operation"].eq("Conforme").sum()), "Paires metier", "green"),
            ("Operations a verifier", _format_count(len(review)), "Controle", "orange"),
        ]
    )
    if review.empty:
        st.success("Aucun ecart metier n'a ete detecte dans les operations filtrees.")
    else:
        _render_alert_banner(
            "Les lignes ci-dessous sont des points de revue. Elles ne constituent pas automatiquement une erreur ou une fraude."
        )
        _mpesa_dataframe(
            _format_customer_analysis_dates(review),
            width="stretch",
            hide_index=True,
        )
    with st.expander("Afficher tous les controles et les debits/credits techniques", expanded=False):
        st.caption(
            "L'ecart debit/credit global est informatif : certaines operations contiennent des comptes de collecte "
            "ou de revenu dont la semantique n'est pas celle du seul compte client."
        )
        _mpesa_dataframe(
            _format_customer_analysis_dates(controls),
            width="stretch",
            hide_index=True,
        )


def _display_text(value: Any, fallback: str = "Non disponible") -> str:
    if value is None or pd.isna(value) or str(value).strip() in {"", "<NA>", "nan", "None"}:
        return fallback
    return str(value).strip()


def _render_customer_statement_elements_preview(
    analysis_report: dict[str, Any],
    *,
    currency: str,
) -> None:
    elements = analysis_report.get("elements_extrait_client_synthese", pd.DataFrame())
    if not isinstance(elements, pd.DataFrame) or elements.empty:
        return
    display = elements.copy()
    if "currency_code" in display.columns:
        display = display.loc[
            display["currency_code"].astype("string").str.upper().eq(str(currency).upper())
        ].copy()
    if display.empty:
        return
    columns = [
        "type_element_extrait",
        "currency_code",
        "nombre_operations",
        "montant_total_observe",
        "statut_periode",
    ]
    columns = [column for column in columns if column in display.columns]
    if not columns:
        return
    if "montant_total_observe" in display.columns:
        display["montant_total_observe"] = display["montant_total_observe"].map(
            _format_amount
        )
    display = display[columns].rename(
        columns={
            "type_element_extrait": "Élément couvert",
            "currency_code": "Devise",
            "nombre_operations": "Opérations",
            "montant_total_observe": "Montant observé",
            "statut_periode": "Situation sur la période",
        }
    )
    st.markdown("##### Éléments couverts par l'extrait")
    _mpesa_dataframe(display, width="stretch", hide_index=True)


def _render_customer_dat_returns_preview(
    analysis_report: dict[str, Any],
    *,
    currency: str,
) -> None:
    returns = analysis_report.get("mouvements_internes_turbo", pd.DataFrame())
    if not isinstance(returns, pd.DataFrame) or returns.empty:
        return
    display = returns.copy()
    if "currency_code" in display.columns:
        display = display.loc[
            display["currency_code"]
            .astype("string")
            .str.upper()
            .eq(str(currency).upper())
        ].copy()
    columns = [
        "date_creation_dat",
        "date_fin_dat",
        "event_reference",
        "currency_code",
        "transfert_dat_sortie",
        "transfert_epargne_entree",
        "descriptions",
    ]
    columns = [column for column in columns if column in display.columns]
    if display.empty or not columns:
        return
    number_format = "%.0f" if str(currency).upper() == "CDF" else "%.2f"
    st.markdown("##### Retours du capital mis en DAT")
    _mpesa_dataframe(
        display[columns],
        width="stretch",
        hide_index=True,
        column_config={
            "date_creation_dat": st.column_config.DatetimeColumn(
                "Date et heure de création du DAT",
                format="DD/MM/YYYY HH:mm",
            ),
            "date_fin_dat": st.column_config.DatetimeColumn(
                "Date et heure de fin du DAT",
                format="DD/MM/YYYY HH:mm",
            ),
            "event_reference": st.column_config.TextColumn(
                "Référence",
                pinned=True,
            ),
            "currency_code": st.column_config.TextColumn("Devise"),
            "transfert_dat_sortie": st.column_config.NumberColumn(
                "Capital DAT restitué",
                format=number_format,
            ),
            "transfert_epargne_entree": st.column_config.NumberColumn(
                "Entrée compte ouvert",
                format=number_format,
            ),
            "descriptions": st.column_config.TextColumn("Description"),
        },
    )


def _render_customer_statement_preview(
    statement: pd.DataFrame,
    *,
    customer_id: str,
    customer_name: str,
    telephone: str,
    entry_account_number: str,
    output_account_number: str,
    filter_context: dict[str, Any],
    analysis_report: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    previews: dict[str, dict[str, Any]] = {}
    if statement.empty:
        st.info("Aucune operation ne correspond aux filtres. L'extrait Word ne peut pas etre genere.")
        return previews

    currencies = _currency_options(statement)
    analysis_report = analysis_report or {}
    for currency in currencies:
        currency_statement = statement.loc[statement["currency_code"].eq(currency)].copy()
        view = build_customer_statement_view(
            currency_statement,
            entry_account_number=entry_account_number,
            output_account_number=output_account_number,
        )
        enriched_detail = build_customer_statement_detail_with_covered_operations(
            view["detail_transactions"],
            analysis_report,
            customer_id=customer_id,
            currency=currency,
            entry_account_number=entry_account_number,
        )
        view = dict(view)
        view["detail_transactions"] = enriched_detail
        previews[currency] = view
        dates = pd.to_datetime(currency_statement.get("created_at"), errors="coerce").dropna()
        date_start = filter_context.get("date_start")
        date_end = filter_context.get("date_end")
        if date_start is None and not dates.empty:
            date_start = dates.min().date()
        if date_end is None and not dates.empty:
            date_end = dates.max().date()
        active_dat = analysis_report.get("dat_en_cours_client", pd.DataFrame())
        rate = DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT
        if isinstance(active_dat, pd.DataFrame) and not active_dat.empty:
            scoped_dat = active_dat.copy()
            if "customer_id" in scoped_dat.columns:
                scoped_dat = scoped_dat.loc[
                    scoped_dat["customer_id"].astype("string").eq(str(customer_id))
                ].copy()
            if "currency_code" in scoped_dat.columns:
                scoped_dat = scoped_dat.loc[
                    scoped_dat["currency_code"].astype("string").str.upper().eq(currency)
                ].copy()
            observed_rates = pd.to_numeric(
                scoped_dat.get(
                    "taux_interet_annuel_pct",
                    pd.Series(dtype="float64"),
                ),
                errors="coerce",
            ).dropna()
            if not observed_rates.empty:
                rate = float(observed_rates.iloc[0])

        title_parts = ["Aperçu du relevé client", telephone]
        customer_name_key = str(customer_name or "").strip().lower()
        if customer_name_key not in {"", "non disponible", "nom non disponible"}:
            title_parts.append(customer_name)
        title_parts.append(currency)
        st.markdown(f"#### {' - '.join(title_parts)}")
        render_summary_box(
            "Critères du relevé",
            [
                f"Date du : {pd.Timestamp(date_start):%d/%m/%Y}" if date_start is not None else "Date du : Non disponible",
                f"Au : {pd.Timestamp(date_end):%d/%m/%Y}" if date_end is not None else "Au : Non disponible",
                f"Numéro du client : {customer_id}",
                f"Téléphone : {telephone}",
                f"Devise : {currency}",
                f"Taux annuel DAT : {rate:.1f}%",
            ],
        )
        financial_summary = build_customer_statement_financial_summary(
            view,
            analysis_report,
            customer_id=customer_id,
            currency=currency,
        )
        view["detail_transactions"] = build_customer_statement_detail_with_opening_balance(
            view["detail_transactions"],
            financial_summary,
        )
        if not financial_summary.empty:
            financial_display = financial_summary.copy()
            for column in [
                "opening_amount",
                "total_entries",
                "total_outputs",
                "closing_amount",
                "compte_ouvert",
                "compte_bloque",
            ]:
                financial_display[column] = financial_display[column].map(
                    _format_amount
                )
            financial_display = financial_display[
                [
                    "currency_code",
                    "opening_amount",
                    "total_entries",
                    "total_outputs",
                    "closing_amount",
                    "compte_ouvert",
                    "compte_bloque",
                ]
            ]
            financial_display = financial_display.rename(
                columns={
                    "currency_code": "Devise",
                    "opening_amount": "Ouverture",
                    "total_entries": "Entrée",
                    "total_outputs": "Sorties",
                    "closing_amount": "Cloture",
                    "compte_ouvert": "Compte ouvert",
                    "compte_bloque": "Compte bloqué",
                }
            )
            _mpesa_dataframe(
                financial_display,
                width="stretch",
                hide_index=True,
            )
        _render_customer_statement_elements_preview(
            analysis_report,
            currency=currency,
        )
        _render_customer_dat_returns_preview(
            analysis_report,
            currency=currency,
        )

        display = view["detail_transactions"][CUSTOMER_STATEMENT_COLUMNS].copy()
        display["date"] = pd.to_datetime(display["date"], errors="coerce").dt.strftime("%d/%m/%Y")
        for column in ["entree", "sortie"]:
            display[column] = display[column].map(
                lambda value: "" if pd.isna(value) or float(value) == 0 else _format_amount(value)
            )
        display["solde"] = display["solde"].map(_format_amount)
        display = display.rename(
            columns={
                "date": "Date",
                "compte": "Compte",
                "receipt_no": "Référence",
                "devise": "Devise",
                "description": "Description",
                "entree": "Entrées",
                "sortie": "Sorties",
                "solde": "Solde",
            }
        )
        _mpesa_dataframe(display, width="stretch", hide_index=True)
    return previews


def _render_customer_active_dat_positions(analysis_report: dict[str, pd.DataFrame]) -> None:
    active_dat = analysis_report.get("dat_en_cours_client", pd.DataFrame())
    if not isinstance(active_dat, pd.DataFrame) or active_dat.empty:
        st.info("Aucun DAT à solde positif n'est disponible pour ce client dans Savings Account.")
        return

    situation_dates = pd.to_datetime(active_dat.get("date_situation"), errors="coerce").dropna()
    situation_label = (
        f"Situation au {situation_dates.max():%d/%m/%Y}. "
        if not situation_dates.empty
        else "Situation à la date disponible. "
    )
    st.caption(
        situation_label
        + "Les intérêts sont des estimations de préparation calculées au taux DAT paramétré; "
        "ils ne constituent pas encore une écriture comptable."
    )
    for currency, currency_entries in active_dat.groupby(
        "currency_code", sort=True, dropna=False
    ):
        currency_text = str(currency or "SANS DEVISE")
        capital = pd.to_numeric(currency_entries["balance"], errors="coerce").sum()
        estimated_interest = pd.to_numeric(
            currency_entries["interet_estime_echeance"], errors="coerce"
        ).sum(min_count=1)
        estimated_total = pd.to_numeric(
            currency_entries["capital_plus_interet_estime"], errors="coerce"
        ).sum(min_count=1)
        urgent_count = int(
            currency_entries["situation_dat_client"]
            .isin(["Échu à rembourser", "Échéance aujourd'hui", "Échéance proche"])
            .sum()
        )
        render_kpi_cards(
            [
                ("DAT en cours", _format_count(len(currency_entries)), currency_text, "blue"),
                ("Capital bloqué", _format_amount(capital), currency_text, "navy"),
                ("Intérêt estimé", _format_amount(estimated_interest), currency_text, "green"),
                ("Capital + intérêt estimé", _format_amount(estimated_total), currency_text, "orange"),
                ("À préparer", _format_count(urgent_count), "Échu ou à 30 jours", "red"),
            ]
        )
        display_columns = [
            "savings_id",
            "date_approved",
            "maturity_date",
            "jours_avant_echeance",
            "currency_code",
            "balance",
            "situation_dat_client",
            "capital_plus_interet_estime",
        ]
        display_columns = [
            column for column in display_columns if column in currency_entries.columns
        ]
        number_format = "%.0f" if currency_text == "CDF" else "%.2f"
        _mpesa_dataframe(
            currency_entries[display_columns],
            width="stretch",
            hide_index=True,
            column_config={
                "savings_id": st.column_config.TextColumn("DAT", pinned=True),
                "date_approved": st.column_config.DateColumn("Souscription", format="DD/MM/YYYY"),
                "maturity_date": st.column_config.DatetimeColumn(
                    "Échéance", format="DD/MM/YYYY"
                ),
                "jours_avant_echeance": st.column_config.NumberColumn("Jours restants", format="%d"),
                "currency_code": st.column_config.TextColumn("Devise"),
                "balance": st.column_config.NumberColumn(
                    "Capital bloqué", format=number_format
                ),
                "capital_plus_interet_estime": st.column_config.NumberColumn(
                    "Capital + intérêt estimé", format=number_format
                ),
                "situation_dat_client": st.column_config.TextColumn("Situation"),
            },
        )


@st.fragment
def _render_customer_extract(prepared: MpesaPreparedData) -> dict[str, Any] | None:
    if prepared.transactions.empty:
        st.info("Chargez au minimum le fichier Transactions pour construire un extrait client.")
        return None

    if prepared.g2_transactions.empty:
        st.info(
            "Source financière : Solution Numérique. L'extrait client, la recherche, les soldes reconstruits et les exports "
            "fonctionnent sans G2; seuls le nom enrichi et le contrôle externe sont alors indisponibles."
        )
    else:
        st.info(
            "Source financière principale : Solution Numérique. G2 complète uniquement le nom du client et vérifie les écritures "
            "rapprochées; ses montants, dates et soldes ne remplacent jamais ceux de la Solution Numérique."
        )

    has_g2_names = (
        not prepared.g2_transactions.empty
        and "Nom_client" in prepared.g2_transactions.columns
        and prepared.g2_transactions["Nom_client"].notna().any()
    )
    search_help = (
        "La recherche accepte un customer_id, un numéro de téléphone ou un nom client issu du fichier G2."
        if has_g2_names
        else "La recherche accepte un customer_id ou un numéro de téléphone. Chargez G2 pour rechercher aussi par nom."
    )
    render_panel_title("1. Rechercher et sélectionner un client")
    st.caption(search_help)
    query_label = "Customer ID, téléphone ou nom" if has_g2_names else "Customer ID ou téléphone"
    query = st.text_input(
        query_label,
        key="mpesa_customer_query",
        help=search_help,
    )
    if not query.strip():
        st.info("Saisissez une valeur de recherche pour commencer l'analyse du client.")
        return None

    matches = search_customers(query, prepared)
    if matches.empty:
        st.warning("Aucun client trouvé.")
        return None

    def join_candidates(values: pd.Series) -> str:
        unique_values = [
            str(value).strip()
            for value in values
            if pd.notna(value) and str(value).strip() not in {"", "<NA>", "nan"}
        ]
        return " | ".join(dict.fromkeys(unique_values))

    candidates = (
        matches.groupby("customer_id", as_index=False, dropna=False)
        .agg(
            Nom_client=("Nom_client", join_candidates),
            telephone=("telephone", join_candidates),
            sources=("source", join_candidates),
        )
        .sort_values("customer_id")
        .reset_index(drop=True)
    )
    match_options = candidates["customer_id"].dropna().astype(str).tolist()
    if not match_options:
        st.warning("Aucun identifiant client exploitable dans les correspondances.")
        return None

    candidate_labels = {
        str(row["customer_id"]): " | ".join(
            value for value in [str(row["customer_id"]), str(row["Nom_client"]), str(row["telephone"])] if value.strip()
        )
        for _, row in candidates.iterrows()
    }
    if len(match_options) == 1:
        selected_customer = match_options[0]
        st.success(f"Client unique trouvé : {candidate_labels[selected_customer]}")
    else:
        selected_customer = st.selectbox(
            "Client à analyser",
            match_options,
            format_func=lambda customer_id: candidate_labels.get(str(customer_id), str(customer_id)),
            key="mpesa_selected_customer",
            help=(
                "Plusieurs clients correspondent à la recherche. Sélectionnez la "
                "fiche exacte à utiliser pour l'aperçu, les contrôles et tous les "
                "exports de l'extrait."
            ),
        )
    with st.expander(f"Voir les {len(candidates)} client(s) correspondant(s)", expanded=False):
        _mpesa_dataframe(candidates, width="stretch", hide_index=True)

    identity = candidates.loc[candidates["customer_id"].astype(str).eq(selected_customer)].iloc[0]
    render_panel_title("2. Client et critères de restitution")
    render_summary_box(
        "Client sélectionné",
        [
            f"Customer ID : {selected_customer}",
            f"Nom : {identity['Nom_client'] or 'Non disponible'}",
            f"Téléphone : {identity['telephone'] or 'Non disponible'}",
            f"Sources retrouvées : {identity['sources'] or 'Non disponible'}",
        ],
    )

    account_columns = st.columns(2)
    entry_account_number = account_columns[0].text_input(
        "Compte des entrées",
        value="1441",
        key=f"mpesa_statement_entry_account_{selected_customer}",
        help="Compte de restitution des entrées, notamment les dépôts et remboursements observés.",
    ).strip()
    output_account_number = account_columns[1].text_input(
        "Compte des sorties",
        value="15558",
        key=f"mpesa_statement_output_account_{selected_customer}",
        help="Compte de restitution des sorties observées.",
    ).strip()

    selected_transactions = prepared.transactions.copy()
    if "customer_id" in selected_transactions.columns:
        selected_transactions = selected_transactions.loc[
            selected_transactions["customer_id"].astype("string").eq(str(selected_customer))
        ].copy()
    opening_currencies = _currency_options(selected_transactions)
    opening_balances: dict[str, float | None] = {}
    if opening_currencies:
        with st.container(border=True):
            st.caption(
                "Solde d'ouverture par devise. Laissez 0 si vous voulez un extrait basé uniquement sur les mouvements filtrés."
            )
            opening_columns = st.columns(min(3, max(1, len(opening_currencies))))
            for index, currency_code in enumerate(opening_currencies):
                decimals_format = "%.0f" if str(currency_code).upper() == "CDF" else "%.2f"
                opening_balances[str(currency_code)] = opening_columns[
                    index % len(opening_columns)
                ].number_input(
                    f"Solde d'ouverture {currency_code}",
                    value=0.0,
                    step=100.0 if str(currency_code).upper() == "CDF" else 1.0,
                    format=decimals_format,
                    key=f"mpesa_statement_opening_balance_{selected_customer}_{currency_code}",
                    help=(
                        "Saisissez le solde réel du compte ouvert juste avant la "
                        "date de début du relevé. Il sert à calculer le solde après "
                        "chaque mouvement et le solde de clôture; il ne crée aucune "
                        "transaction. Laissez 0 si ce solde n'est pas disponible."
                    ),
                )

    try:
        report = _build_mpesa_statement_cached(
            prepared,
            selected_customer,
            tuple(sorted(opening_balances.items())),
        )
    except ValueError as exc:
        st.warning(str(exc))
        return None

    st.caption(f"Mode de source : {report.get('mode_source_extrait', 'Solution Numérique seule')}.")

    statement = report["extrait"]
    summary = report["synthese"]
    render_panel_title("3. Situation financière par devise")
    _render_customer_kpis(summary)

    render_panel_title("4. Critères et filtres de l'extrait")
    filtered_statement, filter_context = _filter_statement(
        statement,
        key_prefix=f"mpesa_statement_{selected_customer}",
    )
    st.caption(f"{len(filtered_statement)} opération(s) retenue(s) sur {len(statement)} pour le client.")
    filtered_report = dict(report)
    filtered_report["extrait"] = filtered_statement
    filtered_report["synthese"] = report["synthese"]
    dat_interest_rate = float(
        st.session_state.get(
            "mpesa_dat_annual_interest_rate_pct",
            DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT,
        )
    )
    filtered_analysis = _build_customer_transaction_analysis_cached(
        prepared,
        selected_customer,
        str(filter_context.get("currency", "Toutes")),
        tuple(str(value) for value in filter_context.get("operation_types", [])),
        filter_context.get("date_start"),
        filter_context.get("date_end"),
        str(filter_context.get("reference_query", "")),
        dat_interest_rate,
    )
    filtered_report.update(filtered_analysis)

    customer_name = _display_text(identity["Nom_client"])
    customer_phone = _display_text(identity["telephone"])
    render_panel_title("5. Aperçu du relevé client")
    previews = _render_customer_statement_preview(
        filtered_statement,
        customer_id=selected_customer,
        customer_name=customer_name,
        telephone=customer_phone,
        entry_account_number=entry_account_number,
        output_account_number=output_account_number,
        filter_context=filter_context,
        analysis_report=filtered_report,
    )

    render_panel_title("6. DAT en cours et échéances à venir")
    _render_customer_active_dat_positions(filtered_analysis)

    render_panel_title("7. Parcours financier du client")
    _render_customer_journey_analysis(filtered_analysis)

    render_panel_title("8. Remboursements observés")
    _render_customer_repayments(filtered_analysis)

    render_panel_title("9. Contrôles et informations complémentaires")
    with st.expander("Afficher les graphiques", expanded=False):
        _render_statement_charts(filtered_statement)
    with st.expander("Afficher les contrôles métier", expanded=False):
        _render_customer_turbo_controls(filtered_analysis)
    with st.expander("Afficher la vérification facultative [G2]", expanded=False):
        g2_control = report.get("g2_dat", pd.DataFrame())
        if not report.get("controle_g2_disponible", False):
            st.info(
                "Transactions M-PESA_G2 n'est pas charge. L'extrait reste complet; "
                "ce bloc de verification est facultatif."
            )
        elif not isinstance(g2_control, pd.DataFrame) or g2_control.empty:
            st.warning(
                "Le fichier G2 est charge, mais aucune transaction G2 n'a pu etre rattachee "
                "au client selectionne."
            )
        else:
            reference_status = g2_control.get(
                "statut_rapprochement", pd.Series("", index=g2_control.index)
            ).astype("string").fillna("")
            exact_count = int(reference_status.eq("Rapproche exact").sum())
            anomaly_count = int(
                g2_control.get("est_anomalie", pd.Series(False, index=g2_control.index))
                .fillna(False)
                .astype(bool)
                .sum()
            )
            render_kpi_cards(
                [
                    ("Transactions [G2] liées", _format_count(len(g2_control)), "Client sélectionné", "blue"),
                    ("Rapprochements exacts", _format_count(exact_count), "G2 contre Solution Numérique", "green"),
                    ("Anomalies [G2]", _format_count(anomaly_count), "Dont écarts de date > 60 minutes", "orange"),
                ]
            )
            if anomaly_count:
                _render_alert_banner(
                    f"{anomaly_count} anomalie(s) G2 nécessitent une vérification."
                )
            verification_columns = [
                "receipt_no",
                "initiation_time",
                "completion_time",
                "currency_code",
                "transaction_amount_numeric",
                "opposite_party",
                "Nom_client",
                "ref_no_portal",
                "methode_rapprochement_turbo",
                "controle_telephone",
                "controle_devise",
                "controle_montant",
                "date_creation_g2",
                "date_creation_turbo",
                "ecart_creation_minutes",
                "controle_date_creation",
                "Observation",
                "statut_rapprochement",
                "motif_anomalie",
            ]
            verification_columns = [
                column for column in verification_columns if column in g2_control.columns
            ]
            _mpesa_dataframe(
                g2_control[verification_columns],
                width="stretch",
                hide_index=True,
            )
    with st.expander("Afficher les colonnes techniques", expanded=False):
        statement_columns = [
            "created_at",
            "operation_reference",
            "currency_code",
            "type_operation",
            "Nom_client",
            "telephone",
            "entree_mpesa",
            "sortie_mpesa",
            "mouvement_net_mpesa",
            "solde_epargne_au_moment",
            "solde_dat_total_au_moment",
            "reference_dat_operation",
            "reference_credit_operation",
            "description_turbo",
            "descriptions",
            "controle_mouvement",
        ]
        statement_columns = [column for column in statement_columns if column in filtered_statement.columns]
        technical_display = filtered_statement[statement_columns].rename(
            columns={
                "entree_mpesa": "entree_mpesa_turbo",
                "sortie_mpesa": "sortie_mpesa_turbo",
                "mouvement_net_mpesa": "mouvement_net_mpesa_turbo",
            }
        )
        _mpesa_dataframe(technical_display, width="stretch", hide_index=True)
        st.caption("Vue complète des colonnes disponibles")
        full_display = filtered_statement.rename(
            columns={
                "entree_mpesa": "entree_mpesa_turbo",
                "sortie_mpesa": "sortie_mpesa_turbo",
                "mouvement_net_mpesa": "mouvement_net_mpesa_turbo",
            }
        )
        _mpesa_dataframe(full_display, width="stretch", hide_index=True)

    render_panel_title("10. Exports")
    st.caption(
        "Les exports Word et PDF produisent un relevé bancaire standard centré sur le compte ouvert. "
        "Le détail transactionnel reprend exactement le client, la période, "
        "la devise, les types d'opération et les références filtrés. "
        "Les boutons CDF et USD produisent un document par devise; ALL les reunit dans un seul document "
        "avec des totaux et cumuls toujours separes par devise. Les DAT en cours reprennent la dernière situation "
        "disponible dans Savings Account, indépendamment de la période transactionnelle. Les remboursements "
        "reprennent uniquement les écritures correspondant aux filtres actifs."
    )
    if previews:
        export_targets = list(previews)
        if len(export_targets) > 1:
            export_targets.append("ALL")
        def export_context(currency: str) -> tuple[pd.DataFrame, object | None, object | None, str, str, str]:
            target_statement = (
                filtered_statement.copy()
                if currency == "ALL"
                else filtered_statement.loc[
                    filtered_statement["currency_code"].eq(currency)
                ].copy()
            )
            dates = pd.to_datetime(target_statement.get("created_at"), errors="coerce").dropna()
            date_start = filter_context.get("date_start")
            date_end = filter_context.get("date_end")
            if date_start is None and not dates.empty:
                date_start = dates.min().date()
            if date_end is None and not dates.empty:
                date_end = dates.max().date()
            base_file_name = build_customer_statement_filename(
                customer_id=selected_customer,
                customer_name=customer_name,
                telephone=customer_phone,
                currency=currency,
                period_start=date_start,
                period_end=date_end,
                g2_available=not prepared.g2_transactions.empty,
            ).removesuffix(".docx")
            start_token = f"{pd.Timestamp(date_start):%Y%m%d}" if date_start is not None else "debut"
            end_token = f"{pd.Timestamp(date_end):%Y%m%d}" if date_end is not None else "fin"
            return target_statement, date_start, date_end, start_token, end_token, base_file_name

        for currency in export_targets:
            if len(export_targets) > 1:
                st.caption(f"Devise {currency}")
            target_statement, date_start, date_end, start_token, end_token, base_file_name = export_context(currency)
            export_columns = st.columns(4)
            try:
                word_bytes = _create_customer_statement_word_cached(
                    target_statement,
                    filtered_report,
                    selected_customer,
                    customer_name,
                    customer_phone,
                    currency,
                    entry_account_number,
                    output_account_number,
                    date_start,
                    date_end,
                )
                word_minimal_bytes = _create_customer_statement_word_cached(
                    target_statement,
                    filtered_report,
                    selected_customer,
                    customer_name,
                    customer_phone,
                    currency,
                    entry_account_number,
                    output_account_number,
                    date_start,
                    date_end,
                    True,
                )
                pdf_bytes = _create_customer_statement_pdf_cached(
                    target_statement,
                    filtered_report,
                    selected_customer,
                    customer_name,
                    customer_phone,
                    currency,
                    entry_account_number,
                    output_account_number,
                    date_start,
                    date_end,
                )
                minimal_pdf_bytes = _create_customer_statement_pdf_cached(
                    target_statement,
                    filtered_report,
                    selected_customer,
                    customer_name,
                    customer_phone,
                    currency,
                    entry_account_number,
                    output_account_number,
                    date_start,
                    date_end,
                    True,
                )
            except (RuntimeError, ValueError) as exc:
                export_columns[0].error(str(exc))
                continue
            export_columns[0].download_button(
                f"Word global {currency}",
                data=word_bytes,
                file_name=f"{base_file_name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
                key=f"mpesa_customer_word_{selected_customer}_{currency}_{start_token}_{end_token}",
            )
            export_columns[1].download_button(
                f"PDF global {currency}",
                data=pdf_bytes,
                file_name=f"{base_file_name}.pdf",
                mime="application/pdf",
                width="stretch",
                key=f"mpesa_customer_pdf_{selected_customer}_{currency}_{start_token}_{end_token}",
            )
            export_columns[2].download_button(
                f"Word minimal {currency}",
                data=word_minimal_bytes,
                file_name=f"{base_file_name}_minimal.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
                key=f"mpesa_customer_word_minimal_{selected_customer}_{currency}_{start_token}_{end_token}",
            )
            export_columns[3].download_button(
                f"PDF minimal {currency}",
                data=minimal_pdf_bytes,
                file_name=f"{base_file_name}_minimal.pdf",
                mime="application/pdf",
                width="stretch",
                key=f"mpesa_customer_pdf_minimal_{selected_customer}_{currency}_{start_token}_{end_token}",
            )

    st.caption(
        "La feuille `Extrait` reprend les filtres appliques a l'etape 4. "
        "Le classeur ajoute les DAT en cours, les remboursements observés, le parcours et les contrôles utiles."
    )
    export_summary = filtered_report.get("synthese", pd.DataFrame()).drop(
        columns=["nombre_credits", "solde_credit_total"],
        errors="ignore",
    )
    customer_export = {
        key: filtered_report.get(key, pd.DataFrame())
        for key in [
            "extrait",
            "parcours_turbo",
            "dat_en_cours_client",
            "remboursements_turbo_detail_client",
            "prochains_remboursements_client",
            "elements_extrait_client_turbo",
            "interets_dat_credites_client",
            "comportement_turbo",
            "mouvements_internes_turbo",
            "controles_client_turbo",
            "dat_final",
            "g2_dat",
            "diagnostics",
        ]
    }
    customer_export = {"synthese": export_summary, **customer_export}
    export_bytes = _create_excel_export_current_sidebar(customer_export)
    excel_column = st.columns(3)[0]
    excel_column.download_button(
        "Telecharger le rapport complet du client",
        data=export_bytes,
        file_name=f"extrait_turbo_dat_client_{selected_customer}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    return filtered_report


def _render_dat_repayment_schedule(prepared: MpesaPreparedData) -> None:
    render_panel_title("Echeances et remboursements DAT")
    if prepared.fixed_savings.empty:
        st.info("Chargez Savings Account pour identifier les DAT echus ou proches de leur terme.")
        return

    default_analysis_date = _latest_complete_turbo_date(prepared)
    if prepared.year_scope_end is not None:
        default_analysis_date = min(default_analysis_date, prepared.year_scope_end)
    scope_token = re.sub(r"[^0-9A-Za-z]+", "_", prepared.year_scope_label).strip("_")
    analysis_date_key = f"mpesa_dat_repayment_analysis_date_{scope_token or 'all'}"

    controls = st.columns(2, gap="medium")
    with controls[0]:
        analysis_date = st.date_input(
            "Date de situation DAT",
            value=default_analysis_date.date(),
            key=analysis_date_key,
            format="DD/MM/YYYY",
            help="Les DAT deja echus et ceux arrivant a terme apres cette date sont classes separement.",
        )
    with controls[1]:
        preparation_horizon_days = st.slider(
            "Horizon de preparation du remboursement (jours)",
            min_value=1,
            max_value=90,
            value=DEFAULT_DAT_REPAYMENT_PREPARATION_HORIZON_DAYS,
            step=1,
            key="mpesa_dat_repayment_horizon_days",
            help="30 jours permet de preparer les remboursements du mois a venir; les DAT deja echus sont toujours inclus.",
        )

    try:
        annual_interest_rate_pct = float(
            st.session_state.get(
                "mpesa_dat_annual_interest_rate_pct",
                DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT,
            )
        )
    except (TypeError, ValueError):
        annual_interest_rate_pct = DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT

    weekly_analysis_date = min(
        pd.Timestamp(analysis_date).normalize(),
        _latest_complete_turbo_date(prepared),
    )
    dat_weekly_comparison = _build_mpesa_weekly_comparison_cached(
        prepared,
        weekly_analysis_date,
        _selected_mpesa_comparison_period(),
    )
    _render_weekly_comparison(
        dat_weekly_comparison,
        blocks=["Comptes"],
        indicator_keys=["nouveaux_dat", "depots_dat"],
        title="Évolution comparative des DAT",
    )

    maturity_report = _build_mpesa_dat_maturity_analysis_cached(
        prepared,
        analysis_date,
        annual_interest_rate_pct,
        preparation_horizon_days,
    )
    detail = maturity_report.get("detail", pd.DataFrame())
    if detail.empty:
        st.info("Aucun DAT avec un solde positif et une echeance exploitable n'a ete trouve.")
        return

    actionable_mask = detail.get(
        "a_preparer_remboursement", pd.Series(False, index=detail.index)
    ).fillna(False).astype(bool)
    actionable = detail.loc[actionable_mask].copy()
    render_summary_box(
        "Regle de preparation",
        [
            f"La liste inclut tous les DAT echus et ceux arrivant a terme dans les {preparation_horizon_days} prochains jours.",
            f"L'interet simple est estime au taux annuel de {annual_interest_rate_pct:.2f}% defini dans la barre laterale.",
            "Le solde DAT est utilise comme capital; le montant capital + interet reste une estimation de preparation et non une ecriture comptable officielle.",
        ],
    )

    if actionable.empty:
        st.success(
            f"Aucun DAT echu ou arrivant a terme dans les {preparation_horizon_days} prochains jours."
        )
        return

    for currency in sorted(
        value
        for value in actionable["currency_code"].dropna().astype(str).unique()
        if value.strip()
    ):
        currency_data = actionable.loc[
            actionable["currency_code"].astype(str).eq(currency)
        ].copy()
        days_to_maturity = pd.to_numeric(
            currency_data["jours_avant_echeance"], errors="coerce"
        )
        expired = currency_data.loc[days_to_maturity.lt(0)]
        upcoming = currency_data.loc[days_to_maturity.ge(0)]
        estimated_interest = pd.to_numeric(
            currency_data["interet_estime_echeance"], errors="coerce"
        ).sum(min_count=1)
        estimated_repayment = pd.to_numeric(
            currency_data["montant_estime_a_rembourser"], errors="coerce"
        ).sum(min_count=1)
        render_panel_title(f"Remboursements DAT a preparer - {currency}")
        render_kpi_cards(
            [
                (
                    "DAT echus",
                    _format_count(len(expired)),
                    f"{_format_amount(pd.to_numeric(expired['balance'], errors='coerce').sum())} {currency} de capital",
                    "orange",
                ),
                (
                    "Echeances a venir",
                    _format_count(len(upcoming)),
                    f"Sous {preparation_horizon_days} jours",
                    "blue",
                ),
                (
                    "Capital a rembourser",
                    _format_amount(pd.to_numeric(currency_data["balance"], errors="coerce").sum()),
                    f"Devise {currency}",
                    "navy",
                ),
                (
                    "Interets estimes",
                    _format_amount(estimated_interest),
                    f"Taux annuel {annual_interest_rate_pct:.2f}%",
                    "green",
                ),
                (
                    "Capital + interets",
                    _format_amount(estimated_repayment),
                    f"Decaissement estime {currency}",
                    "navy",
                ),
            ]
        )

    filtered_actionable = _apply_local_multiselect_filters(
        actionable,
        [
            "currency_code",
            "statut_preparation_remboursement",
            "product_name",
            "Nom_client",
        ],
        key_prefix="mpesa_dat_repayment_filter",
    )
    display_columns = [
        "savings_id",
        "customer_id",
        "Nom_client",
        "msisdn",
        "currency_code",
        "product_name",
        "status",
        "balance",
        "date_approved",
        "maturity_date",
        "duree_contractuelle_mois_estimee",
        "jours_avant_echeance",
        "statut_preparation_remboursement",
        "taux_interet_annuel_pct",
        "interet_estime_echeance",
        "montant_estime_a_rembourser",
    ]
    display_columns = [
        column for column in display_columns if column in filtered_actionable.columns
    ]
    st.caption(
        f"{len(filtered_actionable)} compte(s) DAT a preparer. Les montants restent separes par devise."
    )
    _mpesa_dataframe(
        filtered_actionable[display_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "savings_id": st.column_config.TextColumn("Compte DAT", pinned=True),
            "customer_id": st.column_config.TextColumn("Client"),
            "Nom_client": st.column_config.TextColumn("Nom client"),
            "msisdn": st.column_config.TextColumn("Telephone"),
            "currency_code": st.column_config.TextColumn("Devise"),
            "product_name": st.column_config.TextColumn("Produit / duree"),
            "status": st.column_config.TextColumn("Statut"),
            "balance": st.column_config.NumberColumn("Capital DAT", format="%.2f"),
            "date_approved": st.column_config.DateColumn("Date d'approbation", format="DD/MM/YYYY"),
            "maturity_date": st.column_config.DateColumn("Date d'echeance", format="DD/MM/YYYY"),
            "duree_contractuelle_mois_estimee": st.column_config.NumberColumn(
                "Duree estimee (mois)", format="%.1f"
            ),
            "jours_avant_echeance": st.column_config.NumberColumn(
                "Jours avant echeance", format="%d"
            ),
            "statut_preparation_remboursement": st.column_config.TextColumn(
                "Action remboursement"
            ),
            "taux_interet_annuel_pct": st.column_config.NumberColumn(
                "Taux annuel", format="%.2f %%"
            ),
            "interet_estime_echeance": st.column_config.NumberColumn(
                "Interet estime", format="%.2f"
            ),
            "montant_estime_a_rembourser": st.column_config.NumberColumn(
                "Capital + interet estime", format="%.2f"
            ),
        },
    )
    export_bytes = _create_excel_export_current_sidebar(
        {"dat_echeances_detail": filtered_actionable}
    )
    st.download_button(
        "Telecharger les remboursements DAT a preparer",
        data=export_bytes,
        file_name=(
            f"remboursements_dat_a_preparer_{pd.Timestamp(analysis_date):%Y%m%d}_"
            f"{preparation_horizon_days}j.xlsx"
        ),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        key=(
            f"mpesa_dat_repayment_export_{pd.Timestamp(analysis_date):%Y%m%d}_"
            f"{preparation_horizon_days}j"
        ),
    )


def _render_large_dat_summary(prepared: MpesaPreparedData) -> None:
    if prepared.fixed_savings.empty:
        return

    render_panel_title("Synthese des clients avec de forts DAT")
    percentile = st.slider(
        "Seuil des forts DAT (percentile, calcule separement par devise)",
        min_value=50,
        max_value=99,
        value=90,
        step=1,
        key="mpesa_large_dat_percentile",
        help="90 signifie que les clients dont le DAT total se situe dans les 10 % les plus eleves de leur devise sont retenus.",
    )
    summary = build_large_dat_summary(prepared.fixed_savings, percentile=percentile / 100)
    clients = summary["clients"]
    portefeuille = summary["portefeuille"]
    if clients.empty or portefeuille.empty:
        st.info("Aucun DAT positif exploitable pour construire la synthese.")
        return

    render_summary_box(
        "Lecture",
        [
            "Le seuil est calcule sur le DAT total par client, independamment pour chaque devise.",
            "Le nom client provient de G2 lorsqu'il est disponible; le customer_id et le telephone restent affiches pour le controle.",
            "Les DAT echus et les echeances dans les 30 prochains jours permettent de prioriser le suivi.",
        ],
    )

    display_columns = [
        "rang_devise",
        "customer_id",
        "Nom_client",
        "telephone",
        "currency_code",
        "nb_comptes_dat",
        "solde_dat_total",
        "plus_fort_dat",
        "part_portefeuille_pct",
        "part_cumulee_pct",
        "produits_dat",
        "date_premier_dat",
        "date_dernier_dat",
        "prochaine_echeance",
        "nb_dat_echus",
        "solde_dat_echu",
        "nb_echeances_30j",
        "solde_echeance_30j",
    ]

    for currency in portefeuille["currency_code"].astype(str).tolist():
        portfolio_row = portefeuille.loc[portefeuille["currency_code"].astype(str).eq(currency)].iloc[0]
        currency_clients = clients.loc[clients["currency_code"].astype(str).eq(currency)].copy()
        strong_clients = currency_clients.loc[currency_clients["est_fort_dat"]].copy()
        render_panel_title(f"Forts DAT - {currency}")
        render_kpi_cards(
            [
                ("DAT total", _format_amount(portfolio_row["total_dat"]), f"Devise {currency}", "navy"),
                ("Clients DAT", _format_count(portfolio_row["nb_clients_dat"]), "Clients avec solde positif", "blue"),
                ("Seuil fort DAT", _format_amount(portfolio_row["seuil_fort_dat"]), f"Percentile {percentile}", "orange"),
                ("Clients forts", _format_count(portfolio_row["nb_clients_forts"]), "Au-dessus du seuil", "green"),
                (
                    "Concentration",
                    f"{float(portfolio_row['concentration_clients_forts_pct']):.1f} %",
                    "Part du DAT detenue par ces clients",
                    "navy",
                ),
                (
                    "Echeance sous 30 j",
                    _format_amount(portfolio_row["solde_echeance_30j"]),
                    f"Devise {currency}",
                    "orange",
                ),
            ]
        )

        chart_data = strong_clients.head(15).copy()
        if not chart_data.empty:
            chart_data["client"] = chart_data["Nom_client"].astype("string").fillna("").str.strip()
            chart_data["client"] = chart_data["client"].where(chart_data["client"].ne(""), chart_data["customer_id"])
            chart_data["client"] = chart_data["client"] + " | " + chart_data["customer_id"].astype(str)
            chart_data = chart_data.sort_values("solde_dat_total", ascending=True)
            fig = px.bar(
                chart_data,
                x="solde_dat_total",
                y="client",
                orientation="h",
                color_discrete_sequence=["#1f77b4"],
                labels={"solde_dat_total": f"DAT total ({currency})", "client": "Client"},
                hover_data=["nb_comptes_dat", "part_portefeuille_pct", "prochaine_echeance"],
            )
            style_standard_horizontal_bar(fig, height=max(340, 34 * len(chart_data)))
            st_plot(fig, key=f"mpesa_large_dat_{currency}", height=max(340, 34 * len(chart_data)))

    combined_strong_clients = (
        clients.loc[clients["est_fort_dat"]]
        .sort_values(["currency_code", "rang_devise", "customer_id"])
        .reset_index(drop=True)
    )
    render_panel_title("Tableau fusionne des forts DAT - CDF et USD")
    combined_view = _apply_local_multiselect_filters(
        combined_strong_clients,
        ["currency_code", "produits_dat", "Nom_client", "customer_id"],
        key_prefix="mpesa_large_dat_combined_filter",
    )
    st.caption(f"{len(combined_view)} client(s) affiche(s), toutes devises confondues sans addition des montants.")
    _mpesa_dataframe(combined_view[display_columns], width="stretch", hide_index=True)

    export_bytes = _create_excel_export_current_sidebar(
        {"forts_dat": combined_strong_clients, "portefeuille_dat": portefeuille}
    )
    st.download_button(
        "Telecharger la synthese des forts DAT",
        data=export_bytes,
        file_name="synthese_clients_forts_dat.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )


@st.fragment
def _render_dat_tab(report: dict[str, Any] | None, prepared: MpesaPreparedData) -> None:
    del report
    if prepared.current_savings.empty and prepared.fixed_savings.empty:
        st.info("Chargez Savings Account pour construire le cockpit Epargnes.")
        return

    render_panel_title("Cockpit Epargnes")
    default_end = _latest_complete_turbo_date(prepared)
    if prepared.year_scope_end is not None:
        default_end = min(default_end, prepared.year_scope_end)
    transaction_dates = (
        pd.to_datetime(prepared.transactions["created_at"], errors="coerce").dropna()
        if not prepared.transactions.empty and "created_at" in prepared.transactions.columns
        else pd.Series(dtype="datetime64[ns]")
    )
    default_start = (
        pd.Timestamp(transaction_dates.min()).normalize()
        if not transaction_dates.empty
        else default_end
    )
    if prepared.year_scope_start is not None:
        default_start = max(default_start, prepared.year_scope_start)
    scope_token = re.sub(r"[^0-9A-Za-z]+", "_", prepared.year_scope_label).strip("_") or "all"
    controls = st.columns(4, gap="medium")
    with controls[0]:
        date_start = st.date_input(
            "Date de debut",
            value=default_start.date(),
            key=f"mpesa_savings_date_start_{scope_token}",
            format="DD/MM/YYYY",
            help="Debut inclusif de la periode utilisee pour les flux observes dans Transactions.",
        )
    with controls[1]:
        date_end = st.date_input(
            "Date de fin",
            value=default_end.date(),
            key=f"mpesa_savings_date_end_{scope_token}",
            format="DD/MM/YYYY",
            help="Fin inclusive de la periode. La position Savings Account reste une photographie a cette date.",
        )
    with controls[2]:
        frequency = st.selectbox(
            "Frequence",
            ["Jour", "Semaine", "Mois"],
            index=2,
            key="mpesa_savings_frequency",
            help="Regroupement des courbes de flux : jour, semaine ou mois.",
        )
    with controls[3]:
        maturity_horizon_days = st.slider(
            "Horizon echeances DAT",
            min_value=1,
            max_value=90,
            value=DEFAULT_DAT_REPAYMENT_PREPARATION_HORIZON_DAYS,
            step=1,
            key="mpesa_savings_maturity_horizon_days",
            help="Nombre de jours a regarder en avant pour preparer les remboursements DAT.",
        )

    settings = st.columns(3, gap="medium")
    with settings[0]:
        annual_interest_rate_pct = st.number_input(
            "Taux d'interet annuel DAT (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(
                st.session_state.get(
                    "mpesa_dat_annual_interest_rate_pct",
                    DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT,
                )
            ),
            step=0.25,
            key="mpesa_savings_dat_annual_interest_rate_pct",
            help="11 % est la valeur Bisou Bisou par defaut. Mettre 0 pour desactiver l'estimation.",
        )
    with settings[1]:
        inactivity_threshold_days = st.slider(
            "Seuil d'inactivite observee",
            min_value=7,
            max_value=365,
            value=30,
            step=1,
            key="mpesa_savings_inactivity_threshold_days",
            help="Seuil analytique base sur la derniere operation observee; ce n'est pas une dormance reglementaire.",
        )
    with settings[2]:
        large_savings_usd = st.number_input(
            "Seuil forte epargne USD",
            min_value=0.0,
            value=100.0,
            step=10.0,
            key="mpesa_savings_large_usd",
            help="Seuil expose pour identifier les clients a analyser commercialement, sans conclure a leur eligibilite.",
        )
    large_savings_cdf = st.number_input(
        "Seuil forte epargne CDF",
        min_value=0.0,
        value=500_000.0,
        step=50_000.0,
        key="mpesa_savings_large_cdf",
        help="Seuil CDF expose pour les opportunites commerciales; les devises restent separees.",
    )

    if pd.Timestamp(date_start) > pd.Timestamp(date_end):
        st.warning("La date de debut est posterieure a la date de fin; l'analyse inverse automatiquement les bornes.")

    weekly_date = min(pd.Timestamp(date_end).normalize(), _latest_complete_turbo_date(prepared))
    _render_weekly_comparison(
        _build_mpesa_weekly_comparison_cached(
            prepared,
            weekly_date,
            _selected_mpesa_comparison_period(),
        ),
        blocks=["Comptes"],
        indicator_keys=["clients_epargnants", "nouveaux_comptes_ouverts", "nouveaux_dat", "depots_epargne", "depots_dat"],
        title="Evolution comparative de l'epargne",
    )

    cockpit = _build_mpesa_savings_cockpit_cached(
        prepared,
        date_start,
        date_end,
        frequency,
        float(annual_interest_rate_pct),
        int(inactivity_threshold_days),
        int(maturity_horizon_days),
        float(large_savings_usd),
        float(large_savings_cdf),
    )
    quality = cockpit.get("qualite_donnees", pd.DataFrame())
    warning_count = int(quality.get("statut", pd.Series(dtype=str)).astype(str).eq("A verifier").sum()) if not quality.empty else 0
    if warning_count:
        _render_alert_banner(f"{warning_count} controle(s) Epargnes necessitent une verification.")

    render_summary_box(
        "Regles de lecture",
        [
            "Savings Account est la source de stock actuel : comptes ouverts, DAT, soldes, statuts et echeances.",
            "Transactions est la source des flux de periode : depots, retraits, transferts DAT et remboursements depuis compte ouvert.",
            "G2 sert uniquement au controle et a l'identite; il ne modifie pas les montants d'epargne.",
            "Les montants sont toujours lus devise par devise; aucun total CDF + USD n'est produit.",
        ],
    )

    tab_key = "mpesa_savings_cockpit_tabs"
    inject_professional_tabs_css(container_key=tab_key)
    sub_tabs = st.container(key=tab_key).tabs(
        format_professional_tab_labels(
            (
                "Vue d'ensemble",
                "Collecte et flux",
                "Portefeuille actuel",
                "Clients et comptes",
                "Activite observee",
                "Produits",
                "Concentration",
                "DAT",
                "Echeances DAT",
                "Opportunites",
                "Controles et anomalies",
            )
        )
    )

    with sub_tabs[0]:
        overview = cockpit.get("vue_ensemble", pd.DataFrame())
        if overview.empty:
            st.info("Aucun indicateur de synthese disponible.")
        else:
            for currency in sorted(overview["currency_code"].dropna().astype(str).unique()):
                currency_view = overview.loc[overview["currency_code"].astype(str).eq(currency)].copy()
                cards = []
                for _, row in currency_view.head(10).iterrows():
                    unit = str(row.get("unite", ""))
                    value = row.get("valeur", 0)
                    formatted = _format_amount(value) if unit == "montant" else _format_count(value)
                    cards.append(
                        (
                            str(row.get("indicateur", "")).replace("_", " ").title(),
                            formatted,
                            f"Devise {currency} - {row.get('bloc', '')}",
                            "navy" if unit == "montant" else "blue",
                        )
                    )
                render_panel_title(f"Synthese - {currency}")
                render_kpi_cards(cards)
            _mpesa_dataframe(overview, width="stretch", hide_index=True)

    with sub_tabs[1]:
        flux = cockpit.get("flux_synthese", pd.DataFrame())
        evolution = cockpit.get("flux_evolution", pd.DataFrame())
        render_panel_title("Flux de periode")
        flux_view = _apply_local_multiselect_filters(
            flux,
            ["currency_code"],
            key_prefix="mpesa_savings_flux_filter",
        )
        _mpesa_dataframe(flux_view, width="stretch", hide_index=True)
        if not evolution.empty:
            for currency in sorted(evolution["currency_code"].dropna().astype(str).unique()):
                chart_data = evolution.loc[evolution["currency_code"].astype(str).eq(currency)].copy()
                chart_long = chart_data.melt(
                    id_vars=["periode", "currency_code"],
                    value_vars=[
                        column
                        for column in [
                            "montant_depots_compte_ouvert",
                            "montant_depots_dat",
                            "montant_retraits",
                            "montant_remboursements_depuis_compte_ouvert",
                        ]
                        if column in chart_data.columns
                    ],
                    var_name="indicateur",
                    value_name="montant",
                )
                if chart_long.empty:
                    continue
                st.markdown(f"**Evolution des flux - {currency}**")
                fig = px.line(
                    chart_long,
                    x="periode",
                    y="montant",
                    color="indicateur",
                    markers=True,
                    labels={"periode": "Periode", "montant": f"Montant ({currency})", "indicateur": "Indicateur"},
                )
                style_standard_line(fig, height=390)
                st_plot(fig, key=f"mpesa_savings_flux_{currency}", height=390)

    with sub_tabs[2]:
        portfolio = cockpit.get("portefeuille_synthese", pd.DataFrame())
        detail = cockpit.get("portefeuille_detail", pd.DataFrame())
        render_panel_title("Portefeuille actuel")
        portfolio_view = _apply_local_multiselect_filters(
            portfolio,
            ["currency_code", "famille_epargne"],
            key_prefix="mpesa_savings_portfolio_filter",
        )
        _mpesa_dataframe(portfolio_view, width="stretch", hide_index=True)
        with st.expander("Afficher le detail des comptes", expanded=False):
            detail_view = _apply_local_multiselect_filters(
                detail,
                ["currency_code", "famille_epargne", "product_name", "status"],
                key_prefix="mpesa_savings_portfolio_detail_filter",
            )
            columns = [
                column
                for column in [
                    "savings_id", "customer_id", "Nom_client", "msisdn", "currency_code",
                    "famille_epargne", "product_name", "status", "balance",
                    "date_creation_compte", "date_approved", "date_activated",
                    "maturity_date", "is_interest_calculated",
                    "last_interest_calculation_date", "next_interest_calculation_date",
                    "interest_earned", "fees_due", "source_position",
                ]
                if column in detail_view.columns
            ]
            _mpesa_dataframe(detail_view[columns].head(1000), width="stretch", hide_index=True)

    with sub_tabs[3]:
        new_accounts = cockpit.get("nouveaux_comptes", pd.DataFrame())
        activity = cockpit.get("activite_comptes", pd.DataFrame())
        render_panel_title("Clients et comptes")
        _mpesa_dataframe(new_accounts, width="stretch", hide_index=True)
        if not activity.empty:
            summary = (
                activity.groupby(["currency_code", "famille_epargne", "statut_activite_observee"], as_index=False, dropna=False)
                .agg(nombre_comptes=("savings_id", "nunique"), nombre_clients=("customer_id", "nunique"), encours_actuel=("balance", "sum"))
                .sort_values(["currency_code", "famille_epargne", "statut_activite_observee"])
            )
            _mpesa_dataframe(summary, width="stretch", hide_index=True)

    with sub_tabs[4]:
        activity = cockpit.get("activite_comptes", pd.DataFrame())
        render_panel_title("Activite observee")
        activity_view = _apply_local_multiselect_filters(
            activity,
            ["currency_code", "famille_epargne", "statut_activite_observee", "product_name"],
            key_prefix="mpesa_savings_activity_filter",
        )
        _mpesa_dataframe(activity_view.head(1000), width="stretch", hide_index=True)

    with sub_tabs[5]:
        products = cockpit.get("produits_synthese", pd.DataFrame())
        render_panel_title("Produits d'epargne")
        product_view = _apply_local_multiselect_filters(
            products,
            ["currency_code", "famille_epargne", "product_name"],
            key_prefix="mpesa_savings_products_filter",
        )
        _mpesa_dataframe(product_view, width="stretch", hide_index=True)

    with sub_tabs[6]:
        concentration = cockpit.get("concentration_synthese", pd.DataFrame())
        clients = cockpit.get("concentration_clients", pd.DataFrame())
        render_panel_title("Concentration")
        _mpesa_dataframe(concentration, width="stretch", hide_index=True)
        clients_view = _apply_local_multiselect_filters(
            clients,
            ["currency_code", "famille_epargne", "Nom_client", "customer_id"],
            key_prefix="mpesa_savings_concentration_clients_filter",
        )
        _mpesa_dataframe(clients_view.head(200), width="stretch", hide_index=True)

    with sub_tabs[7]:
        dat_summary = cockpit.get("dat_synthese", pd.DataFrame())
        dat_detail = cockpit.get("dat_detail", pd.DataFrame())
        render_panel_title("DAT - position actuelle")
        _mpesa_dataframe(dat_summary, width="stretch", hide_index=True)
        dat_view = _apply_local_multiselect_filters(
            dat_detail,
            ["currency_code", "product_name", "status", "tranche_echeance"],
            key_prefix="mpesa_savings_dat_filter",
        )
        dat_columns = [
            column
            for column in [
                "savings_id", "customer_id", "Nom_client", "msisdn", "product_name",
                "currency_code", "status", "balance", "date_approved",
                "maturity_date", "jours_avant_echeance", "interest_earned",
                "interet_estime", "capital_plus_interet_estime", "tranche_echeance",
            ]
            if column in dat_view.columns
        ]
        _mpesa_dataframe(dat_view[dat_columns].head(1000), width="stretch", hide_index=True)
        st.caption(
            f"Estimation DAT : taux annuel {float(annual_interest_rate_pct):.2f} %. "
            "Cette valeur sert a la preparation, pas a la comptabilisation officielle."
        )

    with sub_tabs[8]:
        render_panel_title("Echeances DAT")
        maturity_summary = cockpit.get("dat_echeances_synthese", pd.DataFrame())
        maturity_detail = cockpit.get("dat_echeances_detail", pd.DataFrame())
        _mpesa_dataframe(maturity_summary, width="stretch", hide_index=True)
        maturity_view = _apply_local_multiselect_filters(
            maturity_detail,
            ["currency_code", "tranche_echeance", "statut_preparation_remboursement", "product_name"],
            key_prefix="mpesa_savings_maturity_filter",
        )
        _mpesa_dataframe(maturity_view.head(1000), width="stretch", hide_index=True)

    with sub_tabs[9]:
        render_panel_title("Opportunites commerciales prudentes")
        opportunities = cockpit.get("opportunites", pd.DataFrame())
        if opportunities.empty:
            st.info("Aucune opportunite analytique selon les seuils actuels.")
        else:
            opportunity_view = _apply_local_multiselect_filters(
                opportunities,
                ["currency_code", "opportunite", "Nom_client", "customer_id"],
                key_prefix="mpesa_savings_opportunity_filter",
            )
            _mpesa_dataframe(opportunity_view.head(1000), width="stretch", hide_index=True)
        render_summary_box(
            "Prudence metier",
            [
                "DAT sans credit actif et forte epargne sans credit sont des pistes commerciales.",
                "Ces listes ne constituent pas une decision d'eligibilite credit.",
                "Les seuils USD/CDF sont visibles dans les filtres pour eviter une regle cachee.",
            ],
        )

    with sub_tabs[10]:
        render_panel_title("Controles et anomalies")
        quality_view = _apply_local_multiselect_filters(
            quality,
            ["statut", "controle"],
            key_prefix="mpesa_savings_quality_filter",
        )
        _mpesa_dataframe(quality_view, width="stretch", hide_index=True)
        catalogue = cockpit.get("catalogue_kpi", pd.DataFrame())
        with st.expander("Catalogue KPI et limites", expanded=False):
            _mpesa_dataframe(catalogue, width="stretch", hide_index=True)
        for list_key, frame in cockpit.get("listes_action", {}).items():
            if not isinstance(frame, pd.DataFrame) or frame.empty:
                continue
            with st.expander(list_key.replace("_", " ").title(), expanded=False):
                _mpesa_dataframe(frame.head(1000), width="stretch", hide_index=True)

    export_report: dict[str, Any] = {
        "epargne_vue_ensemble": cockpit.get("vue_ensemble", pd.DataFrame()),
        "epargne_portefeuille_synthese": cockpit.get("portefeuille_synthese", pd.DataFrame()),
        "epargne_portefeuille_detail": cockpit.get("portefeuille_detail", pd.DataFrame()),
        "epargne_flux_synthese": cockpit.get("flux_synthese", pd.DataFrame()),
        "epargne_flux_evolution": cockpit.get("flux_evolution", pd.DataFrame()),
        "epargne_activite_comptes": cockpit.get("activite_comptes", pd.DataFrame()),
        "epargne_produits_synthese": cockpit.get("produits_synthese", pd.DataFrame()),
        "epargne_concentration_synthese": cockpit.get("concentration_synthese", pd.DataFrame()),
        "epargne_concentration_clients": cockpit.get("concentration_clients", pd.DataFrame()),
        "epargne_dat_detail": cockpit.get("dat_detail", pd.DataFrame()),
        "epargne_dat_echeances": cockpit.get("dat_echeances_detail", pd.DataFrame()),
        "epargne_opportunites": cockpit.get("opportunites", pd.DataFrame()),
        "epargne_qualite_donnees": cockpit.get("qualite_donnees", pd.DataFrame()),
        "epargne_catalogue_kpi": cockpit.get("catalogue_kpi", pd.DataFrame()),
    }
    for name, frame in cockpit.get("listes_action", {}).items():
        export_report[f"epargne_liste_{name}"] = frame
    export_bytes = _create_excel_export_current_sidebar(export_report)
    st.download_button(
        "Telecharger le cockpit Epargnes",
        data=export_bytes,
        file_name=f"cockpit_epargnes_{pd.Timestamp(date_start):%Y%m%d}_{pd.Timestamp(date_end):%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
        key=f"mpesa_savings_cockpit_export_{pd.Timestamp(date_start):%Y%m%d}_{pd.Timestamp(date_end):%Y%m%d}",
    )


def _render_g2_report_export(
    *,
    daily_pivot: pd.DataFrame,
    daily_comptages: pd.DataFrame,
    daily_synthese: pd.DataFrame,
    daily_statuts: pd.DataFrame,
    daily_detail: pd.DataFrame,
    daily_anomalies: pd.DataFrame,
    g2_dat: pd.DataFrame,
    retention_report: dict[str, pd.DataFrame],
    transaction_time_report: dict[str, pd.DataFrame],
    date_start: Any | None,
    date_end: Any | None,
    direction_suffix: str,
    period_text: str,
    direction_label: str,
    source_label: str = "G2",
) -> None:
    render_panel_title(f"7. Export du rapport [{source_label}]")
    turbo_only = source_label == "Turbo"
    export_report = {
        "rapport_journalier_comptages": daily_comptages,
        "rapport_journalier_synthese": daily_synthese,
        "rapport_journalier_detail": daily_detail,
        "transactions_par_jour": transaction_time_report.get("par_jour", pd.DataFrame()),
        "transactions_par_jour_semaine": transaction_time_report.get("par_jour_semaine", pd.DataFrame()),
        "transactions_par_heure": transaction_time_report.get("par_heure", pd.DataFrame()),
        "transactions_jour_heure": transaction_time_report.get("jour_heure", pd.DataFrame()),
        "retention_mensuelle": retention_report.get("mensuelle", pd.DataFrame()),
        "retention_detail": retention_report.get("detail_clients", pd.DataFrame()),
    }
    if turbo_only:
        export_report.update(
            {
                "statuts_turbo": daily_statuts,
                "rapport_turbo_anomalies": daily_anomalies,
                "turbo_dat": g2_dat,
            }
        )
    else:
        export_report.update(
            {
                "statuts_g2": daily_statuts,
                "rapport_journalier_anomalies": daily_anomalies,
                "g2_dat": g2_dat,
            }
        )
    report_bytes = _create_excel_export_current_sidebar(export_report, print_orientation="portrait")
    word_report = dict(export_report)
    word_report["statuts_g2"] = daily_statuts
    word_report["rapport_journalier_anomalies"] = daily_anomalies
    word_report["g2_dat"] = g2_dat
    word_report["rapport_journalier_pivot"] = daily_pivot
    word_report["analysis_date_start"] = date_start
    word_report["analysis_date_end"] = date_end
    word_report["analysis_source_label"] = source_label
    period_suffix = f"{date_start:%Y%m%d}_{date_end:%Y%m%d}" if date_start is not None and date_end is not None else "complet"
    file_source = "turbo_dat" if turbo_only else "g2_dat"
    excel_column, word_column = st.columns(2)
    with excel_column:
        st.download_button(
            "Telecharger le rapport Excel",
            data=report_bytes,
            file_name=f"rapport_{file_source}_{period_suffix}_{direction_suffix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with word_column:
        try:
            word_bytes = _create_g2_dat_word_cached(word_report, period_text, direction_label)
        except RuntimeError as exc:
            st.warning(str(exc))
        else:
            st.download_button(
                "Telecharger le rapport Word",
                data=word_bytes,
                file_name=f"rapport_{file_source}_{period_suffix}_{direction_suffix}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
            )
    st.caption(
        "Le Word est entierement en A4 portrait, annexe Transactions comprise; "
        "l'Excel conserve uniquement les syntheses, comptages, details et controles indispensables "
        "avec une mise en page d'impression en portrait."
    )


def _render_g2_transaction_time_analysis(
    time_report: dict[str, pd.DataFrame], source_label: str = "G2"
) -> None:
    render_panel_title(f"3. Transactions par jour et par heure [{source_label}]")
    par_jour = time_report.get("par_jour", pd.DataFrame())
    par_jour_semaine = time_report.get("par_jour_semaine", pd.DataFrame())
    par_heure = time_report.get("par_heure", pd.DataFrame())
    jour_heure = time_report.get("jour_heure", pd.DataFrame())
    if par_jour.empty or par_heure.empty:
        st.info("Aucune transaction terminee avec une date et une heure valides dans le perimetre analyse.")
        return

    daily_totals = par_jour.groupby("date_transaction", as_index=False)["nombre_transactions"].sum()
    weekday_totals = par_jour_semaine.groupby(
        ["jour_semaine_num", "jour_semaine"], as_index=False
    )["nombre_transactions"].sum()
    hourly_totals = par_heure.groupby(["heure_num", "heure"], as_index=False)["nombre_transactions"].sum()
    total_transactions = int(daily_totals["nombre_transactions"].sum())
    number_of_days = max(int(daily_totals["date_transaction"].nunique()), 1)
    busiest_day = daily_totals.loc[daily_totals["nombre_transactions"].idxmax()]
    busiest_weekday = weekday_totals.loc[weekday_totals["nombre_transactions"].idxmax()]
    busiest_hour = hourly_totals.loc[hourly_totals["nombre_transactions"].idxmax()]
    render_kpi_cards(
        [
            (
                f"Transactions [{source_label}]",
                _format_count(total_transactions),
                "Operations comptabilisees" if source_label == "Turbo" else "Operations terminees",
                "blue",
            ),
            (
                f"Moyenne par jour [{source_label}]",
                _format_amount(total_transactions / number_of_days),
                f"Sur {number_of_days} jour(s) calendaire(s)",
                "green",
            ),
            (
                f"Jour le plus actif [{source_label}]",
                _format_count(busiest_day["nombre_transactions"]),
                pd.Timestamp(busiest_day["date_transaction"]).strftime("%d/%m/%Y"),
                "navy",
            ),
            (
                f"Jour de semaine le plus actif [{source_label}]",
                str(busiest_weekday["jour_semaine"]),
                f"{_format_count(busiest_weekday['nombre_transactions'])} transaction(s)",
                "slate",
            ),
            (
                f"Heure la plus active [{source_label}]",
                _format_count(busiest_hour["nombre_transactions"]),
                str(busiest_hour["heure"]),
                "orange",
            ),
        ]
    )
    st.caption(
        "Les compteurs utilisent le meme perimetre que la synthese G2/DAT : filtres de date, d'heure et de sens, "
        + (
            "operations comptabilisees, une occurrence par operation analytique."
            if source_label == "Turbo"
            else "transactions terminees seulement, une occurrence par Receipt No."
        )
    )

    daily_chart = px.line(
        par_jour,
        x="date_transaction",
        y="nombre_transactions",
        color="sens_flux",
        facet_col="currency_code",
        facet_col_wrap=2,
        markers=True,
        labels={
            "date_transaction": "Date",
            "nombre_transactions": "Nombre de transactions",
            "sens_flux": "Sens",
            "currency_code": "Devise",
        },
        category_orders={"sens_flux": ["Entree", "Sortie", "Indetermine"]},
    )
    daily_chart.update_yaxes(rangemode="tozero")
    style_standard_line(daily_chart, height=380, tickangle=-20)
    st_plot(daily_chart, key="mpesa_g2_transactions_daily", height=380)

    hourly_chart = px.bar(
        par_heure,
        x="heure",
        y="nombre_transactions",
        color="sens_flux",
        facet_col="currency_code",
        facet_col_wrap=2,
        barmode="group",
        labels={
            "heure": "Heure de la journee",
            "nombre_transactions": "Nombre de transactions",
            "sens_flux": "Sens",
            "currency_code": "Devise",
        },
        category_orders={
            "heure": [f"{hour:02d}h" for hour in range(24)],
            "sens_flux": ["Entree", "Sortie", "Indetermine"],
        },
    )
    hourly_chart.update_yaxes(rangemode="tozero")
    style_standard_vertical_bar(hourly_chart, height=400, tickangle=-45)
    st_plot(hourly_chart, key="mpesa_g2_transactions_hourly", height=400)

    with st.expander("Afficher les tableaux de volumes par jour et par heure", expanded=False):
        temporal_tab_labels = [
            "Par jour",
            "Par jour de semaine",
            "Par heure",
            "Jour x heure",
        ]
        temporal_tabs_key = "mpesa_g2_temporal_detail_tabs"
        inject_professional_tabs_css(container_key=temporal_tabs_key)
        temporal_tabs_container = st.container(key=temporal_tabs_key)
        daily_tab, weekday_tab, hourly_tab, day_hour_tab = temporal_tabs_container.tabs(
            format_professional_tab_labels(temporal_tab_labels)
        )
        with daily_tab:
            _mpesa_dataframe(par_jour, width="stretch", hide_index=True)
        with weekday_tab:
            _mpesa_dataframe(par_jour_semaine, width="stretch", hide_index=True)
        with hourly_tab:
            _mpesa_dataframe(par_heure, width="stretch", hide_index=True)
        with day_hour_tab:
            st.caption("Detail des heures effectivement actives; les heures sans transaction ne sont pas repetees.")
            _mpesa_dataframe(jour_heure, width="stretch", hide_index=True)


def _render_g2_retention_report(
    retention_report: dict[str, pd.DataFrame], source_label: str = "G2"
) -> None:
    render_panel_title(f"4. Fidelisation des clients [{source_label}]")
    render_summary_box(
        "Definitions du rapport",
        [
            f"La base mensuelle correspond aux telephones clients distincts ayant une operation {source_label} eligible, par devise.",
            "Retention M+1 : part de cette base revenue pendant le mois civil suivant.",
            "Retention 90 jours : part de cette base revenue dans les 90 jours suivant la fin du mois de base.",
            "Les operations internes, les telephones invalides et les statuts explicitement en echec ou annules sont exclus.",
            "Un taux reste vide tant que toute sa fenetre d'observation n'est pas disponible.",
        ],
    )
    monthly = retention_report.get("mensuelle", pd.DataFrame())
    if monthly.empty:
        st.info("Aucune activite client eligible ne permet de construire le rapport de fidelisation.")
        return

    observation_start = pd.to_datetime(monthly["debut_observation"], errors="coerce").min()
    observation_end = pd.to_datetime(monthly["fin_observation"], errors="coerce").max()
    if pd.notna(observation_start) and pd.notna(observation_end):
        st.caption(
            f"Fenetre d'observation : du {observation_start:%d/%m/%Y} au {observation_end:%d/%m/%Y}. "
            "Les devises sont calculees et presentees separement."
        )

    for currency, currency_frame in monthly.groupby("currency_code", dropna=False):
        latest_base = currency_frame.sort_values("periode").iloc[-1]
        m1_rows = currency_frame.dropna(subset=["retention_m1_pct"]).sort_values("periode")
        day90_rows = currency_frame.dropna(subset=["retention_90j_pct"]).sort_values("periode")
        latest_m1 = m1_rows.iloc[-1] if not m1_rows.empty else None
        latest_90 = day90_rows.iloc[-1] if not day90_rows.empty else None
        render_panel_title(f"Devise {currency}")
        render_kpi_cards(
            [
                (
                    f"Clients actifs [{source_label}]",
                    _format_count(latest_base.get("clients_actifs_mois_base")),
                    f"Mois {latest_base.get('mois', '-')}",
                    "blue",
                ),
                (
                    f"Retention M+1 [{source_label}]",
                    _format_percent(latest_m1.get("retention_m1_pct")) if latest_m1 is not None else "-",
                    f"Mois {latest_m1.get('mois')}" if latest_m1 is not None else "Fenetre incomplete",
                    "green",
                ),
                (
                    f"Retention 90 jours [{source_label}]",
                    _format_percent(latest_90.get("retention_90j_pct")) if latest_90 is not None else "-",
                    f"Mois {latest_90.get('mois')}" if latest_90 is not None else "Fenetre incomplete",
                    "navy",
                ),
            ]
        )

    chart_data = monthly.melt(
        id_vars=["periode", "currency_code"],
        value_vars=["retention_m1_pct", "retention_90j_pct"],
        var_name="indicateur",
        value_name="taux",
    ).dropna(subset=["taux"])
    if not chart_data.empty:
        chart_data["indicateur"] = chart_data["indicateur"].map(
            {
                "retention_m1_pct": "Retention M+1",
                "retention_90j_pct": "Retention 90 jours",
            }
        )
        fig = px.line(
            chart_data,
            x="periode",
            y="taux",
            color="indicateur",
            facet_col="currency_code",
            markers=True,
            labels={"periode": "Mois de base", "taux": "Taux", "indicateur": "Indicateur"},
        )
        fig.update_yaxes(range=[0, 100], ticksuffix="%")
        style_standard_line(fig, height=380, tickangle=-20)
        st_plot(fig, key="mpesa_g2_retention_trend", height=380)
    else:
        st.warning(
            "La periode chargee est trop courte pour calculer un taux complet. "
            "Le rapport sera alimente automatiquement lorsque les mois suivants seront disponibles."
        )

    trailing_count = int(
        (~monthly["eligible_retention_m1"].astype(bool) | ~monthly["eligible_retention_90j"].astype(bool)).sum()
    )
    if trailing_count:
        st.caption(
            f"{trailing_count} ligne(s) mensuelle(s) recente(s) ont au moins une fenetre encore incomplete; "
            "leurs taux concernes restent vides."
        )

    monthly_columns = [
        "mois",
        "currency_code",
        "clients_actifs_mois_base",
        "clients_retenus_m1",
        "retention_m1_pct",
        "clients_retenus_90j",
        "retention_90j_pct",
        "eligible_retention_m1",
        "eligible_retention_90j",
    ]
    _mpesa_dataframe(monthly[monthly_columns], width="stretch", hide_index=True)

    with st.expander("Afficher la fidelisation par type d'operation", expanded=False):
        st.caption(
            "Un client ayant plusieurs types d'operation pendant un meme mois figure dans chaque segment concerne; "
            "les segments ne doivent donc pas etre additionnes."
        )
        _mpesa_dataframe(retention_report.get("operations", pd.DataFrame()), width="stretch", hide_index=True)
    with st.expander("Afficher le detail client de la fidelisation", expanded=False):
        detail = retention_report.get("detail_clients", pd.DataFrame())
        detail_columns = [
            "mois",
            "currency_code",
            "phone_prefixe",
            "Nom_client",
            "types_operations",
            "nombre_operations_mois_base",
            "montant_entrees_mois_base",
            "montant_sorties_mois_base",
            "premier_retour",
            "delai_premier_retour_jours",
            "retenu_m1",
            "retenu_90j",
        ]
        detail_columns = [column for column in detail_columns if column in detail.columns]
        _mpesa_dataframe(detail[detail_columns], width="stretch", hide_index=True)
    if source_label == "Turbo":
        st.caption(
            "Sans fichier G2, les noms Opposite Party, statuts G2, soldes G2 et delais de finalisation G2 ne sont pas estimes."
        )
    else:
        st.caption(
            "Les dimensions Agence, Groupe produit et Renouvellement de credit du PDF source ne sont pas presentes dans G2; "
            "elles ne sont pas estimees."
        )


@st.fragment
def _render_g2_dat_tab(report: dict[str, Any] | None, prepared: MpesaPreparedData) -> None:
    source_label = "G2"
    source_date_label = "Completion Time"
    analysis_prepared = prepared
    if prepared.g2_transactions.empty:
        turbo_proxy = build_turbo_only_g2_transactions(prepared.transactions)
        if turbo_proxy.empty:
            st.info(
                "Chargez Transactions Solution Numérique ou les rapports G2 M-Pesa pour alimenter ce sous-onglet."
            )
            return
        source_label = "Turbo"
        source_date_label = "created_at"
        analysis_prepared = replace(
            prepared,
            g2_transactions=turbo_proxy,
            cache_fingerprint=f"{_prepared_data_cache_key(prepared)}|g2:turbo-proxy",
        )
        st.info(
            "Mode Solution Numérique seule : le rapport est construit sans rapport G2 M-Pesa. "
            "Les operations sont deduites de `ref_no`, `account_type`, `description`, `dr`, `cr` et `created_at`. "
            "Les noms, statuts, soldes et delais du rapport G2 ainsi que les controles croises G2/Solution Numérique ne sont pas disponibles."
        )

    completion_source = analysis_prepared.g2_transactions.get(
        "completion_time",
        pd.Series(pd.NaT, index=analysis_prepared.g2_transactions.index),
    )
    completion_times = pd.to_datetime(completion_source, errors="coerce").dropna()
    filtered_g2 = analysis_prepared.g2_transactions.copy()
    date_start = None
    date_end = None
    time_start = None
    time_end = None
    period_start = None
    period_end = None
    render_panel_title(f"1. Periode analysee ({source_date_label}) [{source_label}]")
    if not completion_times.empty:
        completion_key = f"{completion_times.min():%Y%m%d}_{completion_times.max():%Y%m%d}_{len(completion_times)}"
        default_completion_date = completion_times.max().date()
        if (
            completion_times.min().date() < completion_times.max().date()
            and completion_times.max().hour < 18
        ):
            default_completion_date = (
                completion_times.max().normalize() - pd.Timedelta(days=1)
            ).date()
        st.caption(f"Champ temporel analysé : {source_date_label}.")
        date_columns = st.columns(2)
        with date_columns[0]:
            date_start = st.date_input(
                "Date de début",
                value=default_completion_date,
                min_value=completion_times.min().date(),
                max_value=completion_times.max().date(),
                key=f"mpesa_g2_completion_start_{completion_key}",
                format="DD/MM/YYYY",
                help=f"Première journée incluse selon {source_date_label}.",
            )
            time_start = st.time_input(
                "Heure de debut",
                value=time(0, 0, 0),
                step=60,
                key=f"mpesa_g2_completion_start_time_{completion_key}",
                help=(
                    "Première heure incluse le jour de début. `00:00:00` "
                    "conserve la journée depuis son commencement."
                ),
            )
        with date_columns[1]:
            date_end = st.date_input(
                "Date de fin",
                value=default_completion_date,
                min_value=completion_times.min().date(),
                max_value=completion_times.max().date(),
                key=f"mpesa_g2_completion_end_{completion_key}",
                format="DD/MM/YYYY",
                help=f"Dernière journée incluse selon {source_date_label}.",
            )
            time_end = st.time_input(
                "Heure de fin",
                value=time(23, 59, 59),
                step=60,
                key=f"mpesa_g2_completion_end_time_{completion_key}",
                help=(
                    "Dernière heure incluse le jour de fin. `23:59:59` conserve "
                    "la journée entière."
                ),
            )
        if default_completion_date < completion_times.max().date():
            st.caption(
                "La derniere journee complete est proposee; la journee la plus "
                "recente semble encore partielle."
            )
        period_start = pd.Timestamp.combine(date_start, time_start)
        period_end = pd.Timestamp.combine(date_end, time_end)
        if period_start > period_end:
            st.error(
                "La date et l'heure de début doivent être antérieures ou égales à la date et l'heure de fin.",
                icon=":material/error:",
            )
            return
        filtered_g2 = filter_g2_transactions_by_completion_time(
            filtered_g2,
            date_start,
            date_end,
            time_start,
            time_end,
        )
    else:
        st.caption(
            f"{source_date_label} n'est pas disponible; l'ensemble de la source {source_label} est analyse."
        )

    direction_options = ["Entrées", "Sorties"]
    selected_direction_labels = st.multiselect(
        "Sens des flux",
        options=direction_options,
        default=[],
        key="mpesa_g2_direction_filter",
        placeholder="Tous",
        help="Aucune sélection = tous les sens. Le filtre s'applique à la synthèse, au détail et à l'export.",
    )
    if not selected_direction_labels or len(selected_direction_labels) == len(direction_options):
        selected_directions = None
        direction_suffix = "tous_flux"
        direction_label = "Tous"
    elif selected_direction_labels == ["Entrées"]:
        selected_directions = ["Entree"]
        direction_suffix = "entrees"
        direction_label = "Entrées"
    else:
        selected_directions = ["Sortie"]
        direction_suffix = "sorties"
        direction_label = "Sorties"
    filtered_g2 = filter_g2_transactions_by_direction(filtered_g2, selected_directions)
    period_text = (
        f"du {date_start:%d/%m/%Y} à {time_start:%H:%M:%S} "
        f"au {date_end:%d/%m/%Y} à {time_end:%H:%M:%S}"
        if date_start is not None and date_end is not None and time_start is not None and time_end is not None
        else "sur toute la periode disponible"
    )
    st.caption(
        f"{len(filtered_g2)} operation(s) [{source_label}] dans le perimetre "
        f"{period_text} - {direction_label.lower()}."
    )
    latest_complete_turbo_date = _latest_complete_turbo_date(prepared)
    weekly_g2_dat_end = (
        min(pd.Timestamp(date_end).normalize(), latest_complete_turbo_date)
        if date_end is not None
        else latest_complete_turbo_date
    )
    g2_dat_weekly_comparison = _build_mpesa_weekly_comparison_cached(
        prepared,
        weekly_g2_dat_end,
        _selected_mpesa_comparison_period(),
        date_start,
    )
    _render_weekly_comparison(
        g2_dat_weekly_comparison,
        blocks=["Comptes", "Transactions"],
        indicator_keys=["nouveaux_dat", "depots_dat", "operations_turbo", "volume_transactions"],
        title="Comparaison temporelle utile au contrôle G2 / DAT",
    )
    if filtered_g2.empty:
        st.warning(
            f"Aucune operation {source_label} ne correspond a la periode et au sens selectionnes."
        )
        return
    filtered_prepared = replace(
        analysis_prepared,
        g2_transactions=filtered_g2,
        cache_fingerprint=(
            f"{_prepared_data_cache_key(analysis_prepared)}|g2-filter:"
            f"{period_text}|{direction_suffix}|{len(filtered_g2)}"
        ),
    )

    daily_report = _build_g2_daily_savings_report_cached(filtered_prepared)
    daily_detail = daily_report.get("detail", pd.DataFrame())
    daily_pivot = daily_report.get("pivot", pd.DataFrame())
    daily_synthese = daily_report.get("synthese", pd.DataFrame())
    daily_comptages = daily_report.get("comptages", pd.DataFrame())
    daily_statuts = daily_report.get("statuts", pd.DataFrame())
    daily_anomalies = daily_report.get("anomalies", pd.DataFrame())
    transaction_time_report = build_g2_transaction_time_analysis(daily_detail)
    retention_report = build_g2_retention_report(filtered_prepared, daily_detail=daily_detail)

    completed_count = int(
        daily_detail.get("incluse_synthese", pd.Series(False, index=daily_detail.index))
        .astype("boolean")
        .fillna(False)
        .sum()
    )
    control_only_count = int(len(daily_detail) - completed_count)
    if source_label == "Turbo":
        kpi_rows = [
            ("Operations analytiques", _format_count(len(daily_detail)), "Une occurrence par operation", "blue"),
            ("Operations comptabilisees", _format_count(completed_count), "Incluses dans les analyses", "green"),
            ("Operations exclues", _format_count(control_only_count), "Controle uniquement", "orange"),
        ]
    else:
        kpi_rows = [
            ("Transactions chargees [G2]", _format_count(len(daily_detail)), "Tous les statuts G2", "blue"),
            ("Transactions Completed [G2]", _format_count(completed_count), "Incluses dans les analyses", "green"),
            ("Autres statuts [G2]", _format_count(control_only_count), "Conserves pour controle uniquement", "orange"),
        ]
    render_kpi_cards(kpi_rows)
    with st.expander(
        f"Afficher la repartition des statuts [{source_label}]",
        expanded=control_only_count > 0,
    ):
        if daily_statuts.empty:
            st.info("Aucun statut de transaction n'est disponible.")
        else:
            status_view = daily_statuts.rename(
                columns={
                    "currency_code": "Devise",
                    "fichier_source_g2": f"Fichier source {source_label}",
                    "statut_transaction_g2": "Statut normalise",
                    "transaction_status_source": f"Statut source {source_label}",
                    "nombre_transactions": "Nombre de transactions",
                    "part_transactions_pct": "Part dans la devise (%)",
                    "prise_en_compte_analyse": "Incluse dans les analyses",
                }
            )
            _mpesa_dataframe(status_view, width="stretch", hide_index=True)
            if source_label == "Turbo":
                st.caption(
                    "Les operations comptabilisees dans la Solution Numérique alimentent les analyses. Aucun statut G2 n'est deduit."
                )
            else:
                st.caption(
                    "Completed alimente les montants, tendances, fidelisation et controles DAT. "
                    "Declined, Cancelled, Expired, Pending et les statuts non renseignes restent tracables sans modifier les resultats."
                )

    reading_rules = (
        [
            "Les entrees sont agregees par `ref_no`; les lignes comptables miroir ne sont comptees qu'une fois.",
            "`NORMAL SAVINGS` + `Epargne depot` = depot normal; `FIXED SAVINGS` + `Depot Bloque` = DAT; les comptes de pret = remboursement.",
            "Les sorties `Retrait Vers M-Pesa` sont agregees par `reference_id + created_at` et classees en paiement client B2C.",
            "`created_at` fournit la date et l'heure de l'operation. Les operations chargees sont considerees comptabilisees.",
            "Les noms, statuts, soldes, Initiation Time et Completion Time G2 ne sont ni inventes ni controles.",
            "Les nombres, montants d'entree, montants de sortie et soldes nets restent separes par devise.",
        ]
        if source_label == "Turbo"
        else [
            "Le sens repose sur les colonnes du releve : `Paid In` = entree et `Withdrawn` = sortie.",
            "Une seule ligne analytique est conservee par `Receipt No.` afin de ne pas compter deux fois une operation.",
            "Seules les transactions au statut `Completed` alimentent les syntheses; les autres statuts sont conserves pour le controle.",
            "La classification utilise d'abord `Receipt No. = ref_no`, puis `account_type` et `description` du portail; la regle G2 sert de repli.",
            "Les nombres, montants d'entree, montants de sortie et soldes nets sont presentes separement pour chaque devise.",
            "Le telephone, la devise, le montant et la date sont controles sans additionner les ecritures techniques du portail.",
        ]
    )
    render_summary_box(
        "Lecture unique du sous-onglet",
        reading_rules,
    )

    render_panel_title(f"2. Synthese des flux {source_label} par devise")
    if daily_pivot.empty:
        st.info("Aucune synthese disponible pour la periode selectionnee.")
    else:
        flow_columns = [
            "currency_code",
            "nombre_entrees",
            "montant_total_entrees",
            "nombre_sorties",
            "montant_total_sorties",
            "solde_net_flux",
            "nombre_total",
            "montant_total",
        ]
        flow_columns = [column for column in flow_columns if column in daily_pivot.columns]
        flow_view = daily_pivot[flow_columns].rename(
            columns={
                "currency_code": "Devise",
                "nombre_entrees": "Nombre d'entrees",
                "montant_total_entrees": f"Montant total des entrees [{source_label}]",
                "nombre_sorties": "Nombre de sorties",
                "montant_total_sorties": f"Montant total des sorties [{source_label}]",
                "solde_net_flux": "Solde net des flux",
                "nombre_total": "Nombre total",
                "montant_total": "Volume total entrees + sorties",
            }
        )
        _mpesa_dataframe(flow_view, width="stretch", hide_index=True)
        st.caption("Solde net des flux = entrees - sorties. Les devises ne sont jamais additionnees entre elles.")

        classified_summary = daily_synthese.loc[
            ~daily_synthese.get("details_rapport", pd.Series("", index=daily_synthese.index))
            .astype("string")
            .str.startswith("Total ", na=False)
        ].copy()
        if not classified_summary.empty:
            render_panel_title(f"Repartition par type d'operation [{source_label}]")
            classified_summary = classified_summary.rename(
                columns={
                    "currency_code": "Devise",
                    "sens_flux": "Sens",
                    "details_rapport": "Type d'operation",
                    "nombre": "Nombre",
                    "montant": "Montant",
                }
            )
            _mpesa_dataframe(classified_summary, width="stretch", hide_index=True)

        with st.expander("Afficher la synthese detaillee en colonnes", expanded=False):
            _mpesa_dataframe(daily_pivot, width="stretch", hide_index=True)

    _render_g2_transaction_time_analysis(transaction_time_report, source_label)

    _render_g2_retention_report(retention_report, source_label)

    render_panel_title(f"5. Transactions [{source_label}]")
    with st.expander(f"Afficher le detail des transactions {source_label}", expanded=False):
        daily_view = _apply_local_multiselect_filters(
            daily_detail,
            [
                "currency_code",
                "sens_flux",
                "details_rapport",
                "reason_type",
                "duree",
                "dat_match_rule",
                "transaction_status",
                "statut_rapprochement",
                "methode_rapprochement_turbo",
                "operation_turbo_confirmee",
                "controle_telephone",
                "controle_devise",
                "controle_montant",
                "controle_date_creation",
                "controle_date_finalisation",
                "controle_date",
            ],
            key_prefix="mpesa_daily_g2_report_filter",
        )
        st.caption(f"{len(daily_view)} ligne(s) affichee(s).")
        detail_columns = list(G2_CLASSIFIED_TRANSACTION_COLUMNS)
        receipt_position = detail_columns.index("receipt_no") + 1
        detail_columns[receipt_position:receipt_position] = [
            "fichier_source_analyse" if source_label == "Turbo" else "fichier_source_g2",
            "transaction_status",
            "traitement_statut_g2",
        ]
        operation_position = detail_columns.index("details_rapport") + 1
        detail_columns[operation_position:operation_position] = [
            "operation_turbo_confirmee"
        ]
        detail_columns = [column for column in detail_columns if column in daily_view.columns]
        _mpesa_dataframe(daily_view[detail_columns], width="stretch", hide_index=True)

    if daily_anomalies.empty:
        if source_label == "Turbo":
            st.success("Aucune anomalie interne detectee dans le perimetre analyse.")
        else:
            st.success("Aucune anomalie de rapprochement detectee dans le perimetre analyse.")
    else:
        _render_alert_banner(
            f"{len(daily_anomalies)} operation(s) necessitent une verification. "
            f"Elles sont conservees dans le detail et dans l'onglet Anomalies_{source_label} de l'export Excel."
        )
        with st.expander(f"Afficher les anomalies [{source_label}]", expanded=False):
            anomaly_columns = [
                "receipt_no",
                "fichier_source_g2",
                "initiation_time",
                "completion_time",
                "currency_code",
                "transaction_amount_numeric",
                "opposite_party",
                "nombre_lignes_g2_reference",
                "devises_g2_reference",
                "statuts_g2_reference",
                "montants_g2_reference",
                "nombre_ecritures_portal",
                "reference_sortie_turbo",
                "cle_sortie_turbo",
                "methode_rapprochement_turbo",
                "nombre_candidats_sortie_turbo",
                "operation_turbo_confirmee",
                "statut_rapprochement",
                "controle_telephone",
                "controle_devise",
                "controle_montant",
                "date_creation_g2",
                "source_date_creation_g2",
                "date_creation_turbo",
                "ecart_creation_minutes",
                "controle_date_creation",
                "date_finalisation_g2",
                "delai_traitement_g2_minutes",
                "ecart_finalisation_minutes",
                "controle_date_finalisation",
                "controle_date",
                "Observation",
                "motif_anomalie",
            ]
            anomaly_columns = [column for column in anomaly_columns if column in daily_anomalies.columns]
            _mpesa_dataframe(
                daily_anomalies[anomaly_columns],
                width="stretch",
                hide_index=True,
            )

    turbo_only = source_label == "Turbo"
    render_panel_title(
        "6. Controle Solution Numérique / DAT" if turbo_only else "6. Controle de rapprochement G2 / DAT"
    )
    if turbo_only:
        control_rules = [
            "Les depots sont regroupes par `ref_no` dans les transactions afin de ne pas compter deux fois les ecritures miroir.",
            "`NORMAL SAVINGS` + `Epargne depot` constitue un depot normal; `FIXED SAVINGS` + `Depot Bloque` constitue un DAT.",
            "Les sorties `Retrait Vers M-Pesa` sont regroupees par `reference_id` et `created_at`.",
            "Les dates utilisent `created_at`. Les controles independants G2/Solution Numérique, le statut G2 et le nom issu de `Opposite Party` sont non applicables sans fichier G2.",
            "Si un fichier Transactions M-PESA_G2 est charge, il redevient automatiquement la source principale du rapport.",
        ]
    else:
        control_rules = [
            "`Receipt No.` G2 est rapproche en priorite avec `ref_no` du fichier Transactions.",
            "Pour une sortie `BisouBisouB2C` sans `ref_no`, le repli exige le meme telephone, la meme devise, le meme montant, une heure proche et le libelle `Retrait Vers M-Pesa`.",
            "Le telephone extrait de `Opposite Party`, la devise et le montant servent de controles independants.",
            "La date de creation compare `Initiation Time` G2 a `created_at`; `Completion Time` mesure la finalisation et le delai de traitement.",
            "Les lignes non rapprochees et les ecarts restent visibles pour verification et export.",
        ]
    render_summary_box("Role du controle", control_rules)

    if report is not None and not turbo_only:
        g2_dat = report.get("g2_dat", pd.DataFrame())
        if date_start is not None or date_end is not None:
            g2_dat = filter_g2_transactions_by_completion_time(
                g2_dat,
                date_start,
                date_end,
                time_start,
                time_end,
            )
        g2_dat = filter_g2_transactions_by_direction(g2_dat, selected_directions)
        st.caption("Controle limite au client selectionne dans l'onglet Extrait client.")
    else:
        g2_dat = build_g2_dat_crosscheck(filtered_prepared)

    if not g2_dat.empty and "incluse_synthese" in g2_dat.columns:
        eligible_control = (
            g2_dat["incluse_synthese"].astype("boolean").fillna(False).astype(bool)
        )
        excluded_control_count = int((~eligible_control).sum())
        g2_dat = g2_dat.loc[eligible_control].reset_index(drop=True)
        if excluded_control_count:
            if turbo_only:
                st.caption(
                    f"{excluded_control_count} operation(s) exclue(s) du controle selon le perimetre analytique."
                )
            else:
                st.caption(
                    f"{excluded_control_count} transaction(s) non Completed exclue(s) du rapprochement DAT; "
                    "elles restent disponibles dans la repartition des statuts, le detail et les anomalies."
                )

    if not g2_dat.empty and "sens_flux" in g2_dat.columns:
        g2_dat = g2_dat.loc[g2_dat["sens_flux"].astype("string").eq("Entree")].reset_index(drop=True)
        st.caption(
            "Le controle DAT porte uniquement sur les entrees; les sorties restent dans l'analyse des flux ci-dessus."
        )

    if g2_dat.empty:
        st.info(
            f"Le controle {source_label} / DAT ne contient aucune entree dans le perimetre courant. "
            "La synthese et l'export des sorties restent disponibles."
        )
        _render_g2_report_export(
            daily_pivot=daily_pivot,
            daily_comptages=daily_comptages,
            daily_synthese=daily_synthese,
            daily_statuts=daily_statuts,
            daily_detail=daily_detail,
            daily_anomalies=daily_anomalies,
            g2_dat=g2_dat,
            retention_report=retention_report,
            transaction_time_report=transaction_time_report,
            date_start=period_start,
            date_end=period_end,
            direction_suffix=direction_suffix,
            period_text=period_text,
            direction_label=direction_label,
            source_label=source_label,
        )
        return

    if "statut_rapprochement" in g2_dat.columns:
        reference_status = g2_dat["statut_rapprochement"].astype("string").fillna("")
        matched = int(reference_status.str.startswith("Rapproche", na=False).sum())
        exact_matches = int(reference_status.eq("Rapproche exact").sum())
    else:
        matched = int(g2_dat["customer_id_dat"].astype("string").fillna("").ne("").sum()) if "customer_id_dat" in g2_dat.columns else 0
        exact_matches = matched
    anomaly_count = int(
        g2_dat.get("est_anomalie", pd.Series(False, index=g2_dat.index)).fillna(False).astype(bool).sum()
    )
    dat_operation_count = (
        int(g2_dat["reference_dat_operation"].astype("string").fillna("").ne("").sum())
        if "reference_dat_operation" in g2_dat.columns
        else 0
    )
    if turbo_only:
        control_cards = [
            ("Operations Solution Numérique", _format_count(len(g2_dat)), "Entrees analysees", "blue"),
            ("DAT operation", _format_count(dat_operation_count), "Lignes FIXED SAVINGS via ref_no", "green"),
            ("Mode Solution Numérique seule", _format_count(len(g2_dat)), "Controles G2/Solution Numérique non applicables", "navy"),
            ("Anomalies internes", _format_count(anomaly_count), "Coherence des donnees Solution Numérique/DAT", "orange"),
        ]
    else:
        control_cards = [
            ("Transactions G2", _format_count(len(g2_dat)), "Lignes analysees", "blue"),
            ("DAT operation", _format_count(dat_operation_count), "Lignes FIXED SAVINGS via ref_no", "green"),
            ("Rapprochements exacts", _format_count(exact_matches), "Cle principale ou repli sortie, controles conformes", "navy"),
            ("Anomalies", _format_count(anomaly_count), f"Dont {len(g2_dat) - matched} non rapproche(s)", "orange"),
        ]
    render_kpi_cards(control_cards)

    control_detail_title = (
        "Afficher le detail du controle Solution Numérique / DAT"
        if turbo_only
        else "Afficher le detail du controle de rapprochement G2 / DAT"
    )
    with st.expander(control_detail_title, expanded=False):
        filtered = _apply_local_multiselect_filters(
            g2_dat,
            [
                "currency_code",
                "statut_rapprochement",
                "methode_rapprochement_turbo",
                "operation_turbo_confirmee",
                "controle_telephone",
                "controle_devise",
                "controle_montant",
                "controle_date_creation",
                "controle_date_finalisation",
                "controle_date",
                "mode_rapprochement",
                "statut_rapprochement_dat",
                "transaction_status",
                "customer_id_dat",
                "phone_prefixe",
            ],
            key_prefix="mpesa_g2_dat_filter",
        )
        control_columns = [
            "receipt_no",
            "initiation_time",
            "completion_time",
            "currency_code",
            "transaction_amount",
            "opposite_party",
            "nombre_lignes_g2_reference",
            "nombre_ecritures_portal",
            "ref_no_portal",
            "reference_sortie_turbo",
            "cle_sortie_turbo",
            "cle_rapprochement_turbo",
            "methode_rapprochement_turbo",
            "nombre_candidats_sortie_turbo",
            "operation_turbo_confirmee",
            "account_types_portal",
            "descriptions_portal",
            "statut_rapprochement",
            "controle_telephone",
            "controle_devise",
            "montant_portal_controle",
            "ecart_montant",
            "controle_montant",
            "date_creation_g2",
            "source_date_creation_g2",
            "date_creation_turbo",
            "ecart_creation_minutes",
            "controle_date_creation",
            "date_finalisation_g2",
            "delai_traitement_g2_minutes",
            "ecart_finalisation_minutes",
            "controle_date_finalisation",
            "ecart_date_minutes",
            "controle_date",
            "Observation",
            "customer_id_ref_no",
            "dat_operation",
            "solde_dat_operation",
            "dat_final",
            "produits_dat",
            "maturites_dat",
            "mode_rapprochement",
            "statut_rapprochement_dat",
            "motif_anomalie",
        ]
        control_columns = [column for column in control_columns if column in filtered.columns]
        filtered_display = filtered[control_columns].copy() if control_columns else filtered
        st.caption(f"{len(filtered)} ligne(s) de controle affichee(s).")
        _mpesa_dataframe(
            filtered_display,
            width="stretch",
            hide_index=True,
        )

    _render_g2_report_export(
        daily_pivot=daily_pivot,
        daily_comptages=daily_comptages,
        daily_synthese=daily_synthese,
        daily_statuts=daily_statuts,
        daily_detail=daily_detail,
        daily_anomalies=daily_anomalies,
        g2_dat=g2_dat,
        retention_report=retention_report,
        transaction_time_report=transaction_time_report,
        date_start=period_start,
        date_end=period_end,
        direction_suffix=direction_suffix,
        period_text=period_text,
        direction_label=direction_label,
        source_label=source_label,
    )


@st.fragment
def _render_perfect_client_tab(prepared: MpesaPreparedData) -> None:
    render_summary_box(
        "Lecture du rapprochement",
        [
            "La population regroupe les telephones observes dans le dataset unifie Solution Numérique + G2; une ligne de synthese correspond a un telephone client.",
            "`Phone_Prefixe` est la cle de rapprochement avec le fichier Clients_Perfect (export 122).",
            "La vue G2 utilise uniquement les clients observes dans Transactions M-PESA_G2.",
            "Les trois vues montrent Clients_Perfect dans G2, Clients_Perfect dans la Solution Numérique, puis l'intersection Clients_Perfect + Solution Numérique + G2.",
            "Les operations proviennent de la Solution Numérique/G2 : Clients_Perfect contient l'identite du client, pas ses operations financieres.",
        ],
    )
    report = build_perfect_client_crosscheck(prepared)
    summary = report.get("synthese", pd.DataFrame())
    operations = report.get("operations", pd.DataFrame())
    clients_perfect_dans_mpesa = report.get("clients_perfect_dans_mpesa", pd.DataFrame())
    clients_perfect_dans_turbo = report.get("clients_perfect_dans_turbo", pd.DataFrame())
    clients_perfect_dans_turbo_et_mpesa = report.get(
        "clients_perfect_dans_turbo_et_mpesa", pd.DataFrame()
    )

    if summary.empty:
        st.info("Chargez au moins un fichier de la Solution Numérique ou Transactions M-PESA_G2 pour constituer la population Solution Numérique + G2 a rechercher dans Perfect.")
        return
    if prepared.perfect_clients.empty:
        st.warning(
            "Le fichier Clients_Perfect n'est pas charge. La population Solution Numérique + G2 reste visible, mais aucune correspondance avec Clients_Perfect ne peut etre confirmee."
        )
    else:
        valid_perfect = int(prepared.perfect_clients.get("phone_prefixe", pd.Series(dtype="string")).notna().sum())
        invalid_perfect = int(len(prepared.perfect_clients) - valid_perfect)
        st.caption(
            f"Clients_Perfect : {len(prepared.perfect_clients)} ligne(s), {valid_perfect} telephone(s) exploitable(s), "
            f"{invalid_perfect} ligne(s) sans cle telephone valide."
        )

    ambiguous = int(summary["nb_clients_perfect"].gt(1).sum())
    invalid_phone = int(summary["phone_prefixe"].isna().sum())
    not_found = int(summary["statut_rapprochement_perfect"].eq("Non trouve dans Perfect").sum())

    def perfect_identity_count(frame: pd.DataFrame) -> int:
        return int(numeric_column(frame, "nb_clients_perfect").sum()) if not frame.empty else 0

    render_kpi_cards(
        [
            (
                "Clients [Clients_Perfect x G2]",
                _format_count(perfect_identity_count(clients_perfect_dans_mpesa)),
                f"{len(clients_perfect_dans_mpesa)} telephone(s) Clients_Perfect/G2",
                "blue",
            ),
            (
                "Clients [Clients_Perfect x Solution Numérique]",
                _format_count(perfect_identity_count(clients_perfect_dans_turbo)),
                f"{len(clients_perfect_dans_turbo)} telephone(s) Clients_Perfect/Solution Numérique",
                "green",
            ),
            (
                "Clients [Clients_Perfect x Solution Numérique x G2]",
                _format_count(perfect_identity_count(clients_perfect_dans_turbo_et_mpesa)),
                f"{len(clients_perfect_dans_turbo_et_mpesa)} telephone(s) dans les 3 systemes",
                "navy",
            ),
        ]
    )
    st.caption(
        f"Qualite du rapprochement : {not_found} telephone(s) Solution Numérique/G2 non trouve(s) dans Clients_Perfect, "
        f"{ambiguous} numero(s) partage(s) et {invalid_phone} telephone(s) inexploitable(s)."
    )

    render_panel_title("1. Fiches Clients_Perfect retrouvees dans G2 et Solution Numérique")
    cohort_columns = [
        "phone_prefixe",
        "customer_ids_turbo",
        "noms_clients_mpesa",
        "noms_clients_perfect",
        "types_operations_mpesa",
        "nombre_operations_turbo",
        "nombre_operations_g2",
        "ids_clients_perfect",
        "codes_clients_perfect",
        "nb_clients_perfect",
        "types_clients_perfect",
        "categories_clients_perfect",
        "gestionnaires_perfect",
        "collecteurs_perfect",
        "premiere_operation",
        "derniere_operation",
        "statut_presence_systemes",
    ]
    cohort_tab_labels = [
        "Clients_Perfect x G2",
        "Clients_Perfect x Solution Numérique",
        "Clients_Perfect x Solution Numérique x G2",
    ]
    cohort_tabs_key = "mpesa_perfect_client_cohort_tabs"
    inject_professional_tabs_css(container_key=cohort_tabs_key)
    cohort_tabs_container = st.container(key=cohort_tabs_key)
    cohort_tabs = cohort_tabs_container.tabs(
        format_professional_tab_labels(cohort_tab_labels)
    )
    cohorts = [
        (
            cohort_tabs[0],
            clients_perfect_dans_mpesa,
            "Fiches Clients_Perfect dont le Phone_Prefixe est observe dans les transactions G2.",
        ),
        (
            cohort_tabs[1],
            clients_perfect_dans_turbo,
            "Fiches Clients_Perfect dont le Phone_Prefixe est observe dans au moins une source Solution Numérique.",
        ),
        (
            cohort_tabs[2],
            clients_perfect_dans_turbo_et_mpesa,
            "Fiches Clients_Perfect dont le Phone_Prefixe est observe a la fois dans G2 et la Solution Numérique.",
        ),
    ]
    for tab, cohort, description in cohorts:
        with tab:
            st.caption(description)
            if cohort.empty:
                st.info("Aucun client ne correspond a cette population dans les fichiers charges.")
            else:
                visible_columns = [column for column in cohort_columns if column in cohort.columns]
                st.caption(
                    f"{perfect_identity_count(cohort)} fiche(s) Perfect sur {len(cohort)} telephone(s) distinct(s)."
                )
                cohort_display = cohort[visible_columns].rename(
                    columns={
                        "noms_clients_mpesa": "noms_clients_turbo_g2",
                        "types_operations_mpesa": "types_operations_turbo_g2",
                    }
                )
                _mpesa_dataframe(cohort_display, width="stretch", hide_index=True)

    render_panel_title("2. Clients transactionnels [Solution Numérique + G2] recherches dans Clients_Perfect")
    search_value = st.text_input(
        "Rechercher par telephone, Customer ID ou nom",
        key="mpesa_perfect_client_search",
        placeholder="Ex. 243..., Customer ID, nom Solution Numérique/G2 ou nom Perfect",
        help=(
            "Recherche dans les téléphones normalisés, les identifiants Solution Numérique "
            "et Perfect ainsi que les noms disponibles. Ce filtre facilite la "
            "consultation et ne modifie aucun montant."
        ),
    ).strip()
    summary_view = _apply_local_multiselect_filters(
        summary,
        ["statut_presence_systemes", "statut_rapprochement_perfect", "systemes_mpesa", "types_operations_mpesa"],
        key_prefix="mpesa_perfect_summary_filter",
    )
    if search_value:
        search_columns = [
            "phone_prefixe", "customer_ids_turbo", "noms_clients_mpesa",
            "ids_clients_perfect", "codes_clients_perfect", "noms_clients_perfect",
        ]
        search_mask = pd.Series(False, index=summary_view.index)
        for column in search_columns:
            if column in summary_view.columns:
                search_mask |= summary_view[column].astype("string").str.contains(
                    search_value, case=False, regex=False, na=False
                )
        summary_view = summary_view.loc[search_mask].reset_index(drop=True)

    summary_columns = [
        "phone_prefixe",
        "customer_ids_turbo",
        "noms_clients_mpesa",
        "systemes_mpesa",
        "present_dans_turbo",
        "present_dans_g2",
        "present_dans_perfect",
        "present_dans_les_3_systemes",
        "statut_presence_systemes",
        "types_operations_mpesa",
        "nombre_operations_turbo",
        "nombre_operations_g2",
        "statut_rapprochement_perfect",
        "nb_clients_perfect",
        "ids_clients_perfect",
        "codes_clients_perfect",
        "noms_clients_perfect",
        "statuts_phone_perfect",
        "types_clients_perfect",
        "categories_clients_perfect",
        "gestionnaires_perfect",
        "collecteurs_perfect",
        "premiere_operation",
        "derniere_operation",
    ]
    summary_columns = [column for column in summary_columns if column in summary_view.columns]
    st.caption(f"{len(summary_view)} ligne(s) client affichee(s).")
    summary_display = summary_view[summary_columns].rename(
        columns={
            "noms_clients_mpesa": "noms_clients_turbo_g2",
            "systemes_mpesa": "systemes_turbo_g2",
            "types_operations_mpesa": "types_operations_turbo_g2",
        }
    )
    _mpesa_dataframe(summary_display, width="stretch", hide_index=True)
    st.caption(
        "Une correspondance multiple signifie que le meme Phone_Prefixe est rattache a plusieurs fiches Perfect; "
        "toutes les identites restent visibles dans la ligne."
    )

    render_panel_title("3. Operations observees dans la Solution Numérique et G2")
    if operations.empty:
        st.info("Aucune operation Solution Numérique/G2 exploitable n'est disponible.")
    else:
        operation_view = _apply_local_multiselect_filters(
            operations,
            ["source_operation", "currency_code", "type_operation", "statut_rapprochement_perfect"],
            key_prefix="mpesa_perfect_operations_filter",
        )
        operation_display = operation_view.copy()
        if "noms_clients_perfect" not in operation_display.columns:
            operation_display["noms_clients_perfect"] = pd.NA
        operation_columns = [
            "date_operation",
            "source_operation",
            "operation_reference",
            "type_operation",
            "sens_operation",
            "currency_code",
            "montant_operation",
            "phone_prefixe",
            "customer_ids_turbo",
            "noms_clients_mpesa",
            "noms_clients_perfect",
            "statut_rapprochement_perfect",
            "nb_clients_perfect",
            "ids_clients_perfect",
            "codes_clients_perfect",
            "description_operation",
            "statut_operation",
        ]
        operation_columns = [column for column in operation_columns if column in operation_display.columns]
        operation_display = operation_display[operation_columns].rename(
            columns={
                "noms_clients_mpesa": "Nom_client_Solution_G2",
                "noms_clients_perfect": "Nom_client_Clients_Perfect",
                "customer_ids_turbo": "Customer_ID_Solution",
                "ids_clients_perfect": "ID_client_Clients_Perfect",
                "codes_clients_perfect": "Code_client_Clients_Perfect",
            }
        )
        st.caption(f"{len(operation_view)} operation(s) affichee(s). Les montants restent separes par source et par devise.")
        _mpesa_dataframe(operation_display, width="stretch", hide_index=True)

    render_panel_title("4. Export")
    export_bytes = _create_excel_export_current_sidebar(
        {
            "clients_perfect_dans_mpesa": clients_perfect_dans_mpesa,
            "clients_perfect_dans_turbo": clients_perfect_dans_turbo,
            "clients_perfect_dans_turbo_et_mpesa": clients_perfect_dans_turbo_et_mpesa,
        }
    )
    st.download_button(
        "Telecharger le rapprochement Solution Numérique + G2 / Clients_Perfect",
        data=export_bytes,
        file_name="rapprochement_turbo_g2_clients_perfect.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )


def _filter_pilotage_currencies(report: dict[str, Any], currencies: list[str]) -> dict[str, Any]:
    if not currencies:
        return report
    filtered: dict[str, Any] = {}
    for key, value in report.items():
        if isinstance(value, pd.DataFrame) and "currency_code" in value.columns:
            currency = value["currency_code"].astype("string").fillna("")
            currency_mask = currency.isin(currencies)
            if key in {
                "comparaison_hebdomadaire",
                "comparaison_annee_precedente",
            }:
                currency_mask |= currency.eq("")
            filtered[key] = value.loc[currency_mask].reset_index(drop=True)
        else:
            filtered[key] = value
    return filtered


@st.fragment
def _render_management_dashboard_legacy(prepared: MpesaPreparedData) -> None:
    operational_dates: list[pd.Series] = []
    if not prepared.transactions.empty and "created_at" in prepared.transactions.columns:
        operational_dates.append(
            pd.to_datetime(prepared.transactions["created_at"], errors="coerce").dropna()
        )
    if not prepared.g2_transactions.empty:
        g2_dates = pd.to_datetime(
            prepared.g2_transactions.get(
                "completion_time",
                pd.Series(pd.NaT, index=prepared.g2_transactions.index),
            ),
            errors="coerce",
        ).dropna()
        if not g2_dates.empty:
            operational_dates.append(g2_dates)
    available_dates = (
        pd.concat(operational_dates, ignore_index=True)
        if operational_dates
        else pd.Series(dtype="datetime64[ns]")
    )
    if available_dates.empty:
        st.info("Chargez Transactions ou Transactions M-PESA_G2 pour construire le cockpit.")
        return
    minimum_date = available_dates.min().date()
    maximum_date = available_dates.max().date()
    default_date = maximum_date
    if minimum_date < maximum_date and available_dates.max().hour < 18:
        previous_date = (pd.Timestamp(maximum_date) - pd.Timedelta(days=1)).date()
        if previous_date >= minimum_date:
            default_date = previous_date
    analysis_date = st.date_input(
        "Date d'analyse du cockpit",
        value=default_date,
        min_value=minimum_date,
        max_value=maximum_date,
        key=(
            f"mpesa_management_analysis_date_{minimum_date:%Y%m%d}_"
            f"{maximum_date:%Y%m%d}_{len(available_dates)}"
        ),
        format="DD/MM/YYYY",
        help=(
            "La derniere journee complete est proposee lorsque la journee la plus "
            "recente semble encore partielle. L'historique ulterieur est exclu."
        ),
    )
    dat_interest_rate = float(
        st.session_state.get(
            "mpesa_dat_annual_interest_rate_pct",
            DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT,
        )
    )
    report = _build_mpesa_management_dashboard_cached(
        prepared, dat_interest_rate, analysis_date
    )
    report_analysis_date = report.get("date_analyse")
    render_summary_box(
        "Objectif du cockpit",
        [
            "Transformer les fichiers G2, Solution Numérique, Credits, DAT et Perfect en controles directement actionnables.",
            "Chaque indicateur precise sa source lorsque G2 ou Perfect intervient dans l'analyse.",
            "Les montants CDF et USD restent toujours separes; seuls les nombres de clients ou d'alertes peuvent etre consolides.",
            "Le PAR utilise exclusivement les echeances et encours du fichier Credits. Une donnee absente reste non calculable.",
            "La projection de liquidite a sept jours est mecanique et n'est affichee qu'avec un solde G2 et au moins sept jours d'historique.",
        ],
    )
    if pd.notna(report_analysis_date):
        st.caption(
            f"Date d'analyse retenue : {pd.Timestamp(report_analysis_date):%d/%m/%Y}. "
            "Les donnees ulterieures ne sont pas integrees au cockpit."
        )

    currency_options: set[str] = set()
    for value in report.values():
        if isinstance(value, pd.DataFrame) and not value.empty and "currency_code" in value.columns:
            currency_options.update(
                item for item in value["currency_code"].dropna().astype(str).unique() if item.strip()
            )
    currency_options_sorted = sorted(currency_options)
    selected_currencies = st.multiselect(
        "Devises affichees",
        options=currency_options_sorted,
        default=currency_options_sorted,
        key="mpesa_pilotage_currencies",
        help="Une selection vide conserve toutes les devises.",
    )
    report_view = _filter_pilotage_currencies(report, selected_currencies)

    sources = report_view.get("sources", pd.DataFrame())
    if not sources.empty and {"source", "disponible"}.issubset(sources.columns):
        missing_sources = sources.loc[
            ~sources["disponible"].astype("boolean").fillna(False).astype(bool), "source"
        ].astype(str).tolist()
        if missing_sources:
            st.info(
                "Sources facultatives non chargees : "
                + ", ".join(missing_sources)
                + ". Consultez Importation pour le detail technique."
            )

    legacy_dashboard_tab_labels = [
        "Vue direction",
        "Credit et liquidite",
        "Clients et epargne",
        "Risques et qualite",
    ]
    legacy_dashboard_tabs_key = "mpesa_legacy_dashboard_inner_tabs"
    inject_professional_tabs_css(container_key=legacy_dashboard_tabs_key)
    legacy_dashboard_tabs_container = st.container(key=legacy_dashboard_tabs_key)
    overview_tab, credit_tab, clients_tab, risk_tab = legacy_dashboard_tabs_container.tabs(
        format_professional_tab_labels(legacy_dashboard_tab_labels)
    )

    with overview_tab:
        activity_clients = report_view.get("activite_clients", pd.DataFrame())
        alerts = report_view.get("alertes_transactions", pd.DataFrame())
        credit_detail = report_view.get("credit_detail", pd.DataFrame())
        dat_detail = report_view.get("dat_echeances_detail", pd.DataFrame())
        perfect_summary = report_view.get("perfect_adoption_synthese", pd.DataFrame())
        active_clients = (
            int(activity_clients.loc[activity_clients["statut_activite"].eq("Actif 30 jours"), "phone_prefixe"].nunique())
            if not activity_clients.empty and {"statut_activite", "phone_prefixe"}.issubset(activity_clients.columns)
            else 0
        )
        overdue_credits = (
            int(credit_detail["jours_retard"].ge(30).sum())
            if not credit_detail.empty and "jours_retard" in credit_detail.columns
            else 0
        )
        dat_due_30 = (
            int(dat_detail["tranche_echeance"].isin(["Echu", "0 a 7 jours", "8 a 30 jours"]).sum())
            if not dat_detail.empty and "tranche_echeance" in dat_detail.columns
            else 0
        )
        perfect_active = (
            int(perfect_summary.iloc[0].get("clients_perfect_actifs_30j", 0))
            if not perfect_summary.empty
            else 0
        )
        render_kpi_cards(
            [
                ("Clients actifs 30j [Solution Numérique + G2]", _format_count(active_clients), "Telephones distincts", "green"),
                ("Credits en retard 30j+", _format_count(overdue_credits), "Dossiers a traiter", "red"),
                ("DAT echus ou a 30j", _format_count(dat_due_30), "Comptes a anticiper", "orange"),
                ("Alertes transactions [G2]", _format_count(len(alerts)), "Controle ou comportement", "navy"),
                ("Clients_Perfect actifs 30j [Solution Numérique + G2]", _format_count(perfect_active), "Adoption consolidee", "blue"),
            ]
        )
        st.caption("Ces cartes sont des volumes de dossiers ou de clients; aucun montant multidevise n'est additionne.")

        render_panel_title("Priorites de suivi")
        priority_rows: list[dict[str, Any]] = []
        if not credit_detail.empty:
            for currency, group in credit_detail.loc[credit_detail["jours_retard"].ge(30)].groupby("currency_code"):
                priority_rows.append(
                    {"priorite": "Credits en retard 30 jours et plus", "devise": currency, "dossiers": len(group), "montant": group["encours_total"].sum()}
                )
        if not dat_detail.empty:
            due_mask = dat_detail["tranche_echeance"].isin(["Echu", "0 a 7 jours", "8 a 30 jours"])
            for currency, group in dat_detail.loc[due_mask].groupby("currency_code"):
                priority_rows.append(
                    {"priorite": "DAT echus ou a echeance sous 30 jours", "devise": currency, "dossiers": len(group), "montant": group["balance"].sum()}
                )
        if priority_rows:
            priority_table = pd.DataFrame(priority_rows)
            _render_alert_banner(
                f"{len(priority_table)} priorite(s) necessitent l'attention du lecteur."
            )
            _mpesa_dataframe(
                priority_table,
                width="stretch",
                hide_index=True,
            )
        else:
            st.success("Aucune priorite credit/DAT calculable dans les fichiers charges.")

    with credit_tab:
        render_panel_title("1. Performance et risque des credits")
        credit_summary = report_view.get("credit_synthese", pd.DataFrame())
        credit_detail = report_view.get("credit_detail", pd.DataFrame())
        if credit_summary.empty:
            st.info("Chargez le fichier Credits pour calculer l'encours, les retards et le PAR.")
        else:
            _mpesa_dataframe(credit_summary, width="stretch", hide_index=True)
            if not credit_detail.empty:
                risk_chart = (
                    credit_detail.groupby(["currency_code", "statut_risque"], as_index=False)
                    .agg(nombre_credits=("loan_id", "nunique"), encours_total=("encours_total", "sum"))
                )
                fig = px.bar(
                    risk_chart,
                    x="statut_risque",
                    y="nombre_credits",
                    color="statut_risque",
                    facet_col="currency_code",
                    facet_col_wrap=2,
                    labels={"statut_risque": "Statut", "nombre_credits": "Nombre de credits", "currency_code": "Devise"},
                )
                style_standard_vertical_bar(fig, height=390, tickangle=-25)
                st_plot(fig, key="mpesa_pilotage_credit_risk", height=390)
                with st.expander("Afficher les credits a suivre", expanded=False):
                    credit_view = _apply_local_multiselect_filters(
                        credit_detail,
                        ["currency_code", "statut_risque", "status_name", "customer_id"],
                        key_prefix="mpesa_pilotage_credit_filter",
                    )
                    _mpesa_dataframe(credit_view, width="stretch", hide_index=True)

        render_panel_title("2. Liquidite [G2]")
        liquidity_summary = report_view.get("liquidite_synthese", pd.DataFrame())
        liquidity_daily = report_view.get("liquidite_journaliere", pd.DataFrame())
        if liquidity_summary.empty:
            st.info("Chargez Transactions G2 avec Completion Time et montants pour analyser la liquidite.")
        else:
            _mpesa_dataframe(liquidity_summary, width="stretch", hide_index=True)
            if not liquidity_daily.empty:
                chart_data = liquidity_daily.melt(
                    id_vars=["date_transaction", "currency_code"],
                    value_vars=["montant_entrees", "montant_sorties"],
                    var_name="flux",
                    value_name="montant",
                )
                chart_data["flux"] = chart_data["flux"].map(
                    {"montant_entrees": "Entrees", "montant_sorties": "Sorties"}
                )
                fig = px.line(
                    chart_data,
                    x="date_transaction",
                    y="montant",
                    color="flux",
                    facet_col="currency_code",
                    facet_col_wrap=2,
                    markers=True,
                    labels={"date_transaction": "Date", "montant": "Montant", "flux": "Flux", "currency_code": "Devise"},
                )
                style_standard_line(fig, height=390, tickangle=-20)
                st_plot(fig, key="mpesa_pilotage_liquidity", height=390)
                with st.expander("Afficher les flux journaliers de liquidite", expanded=False):
                    _mpesa_dataframe(liquidity_daily, width="stretch", hide_index=True)

    with clients_tab:
        render_panel_title("1. Activite, dormance et reactivation [Solution Numérique + G2]")
        activity_summary = report_view.get("activite_synthese", pd.DataFrame())
        activity_clients = report_view.get("activite_clients", pd.DataFrame())
        if activity_summary.empty:
            st.info("Aucune operation avec telephone et date valides ne permet de segmenter les clients.")
        else:
            fig = px.bar(
                activity_summary,
                x="statut_activite",
                y="nombre_clients",
                color="statut_activite",
                facet_col="currency_code",
                facet_col_wrap=2,
                labels={"statut_activite": "Activite", "nombre_clients": "Clients", "currency_code": "Devise"},
            )
            style_standard_vertical_bar(fig, height=390, tickangle=-25)
            st_plot(fig, key="mpesa_pilotage_activity", height=390)
            with st.expander("Afficher les clients actifs, dormants et reactives", expanded=False):
                activity_view = _apply_local_multiselect_filters(
                    activity_clients,
                    ["currency_code", "statut_activite", "est_nouveau_30j", "est_reactive_30j"],
                    key_prefix="mpesa_pilotage_activity_filter",
                )
                _mpesa_dataframe(activity_view, width="stretch", hide_index=True)

        render_panel_title("2. Conversion depot normal vers DAT [G2]")
        conversion_summary = report_view.get("conversion_synthese", pd.DataFrame())
        conversion_clients = report_view.get("conversion_clients", pd.DataFrame())
        if conversion_summary.empty:
            st.info("La conversion exige des operations G2 classees Depot normal et DAT.")
        else:
            _mpesa_dataframe(conversion_summary, width="stretch", hide_index=True)
            st.caption("La conversion est observee dans la periode chargee; elle ne prouve pas l'affectation exacte d'un depot a un DAT.")
            with st.expander("Afficher le detail client de la conversion", expanded=False):
                _mpesa_dataframe(conversion_clients, width="stretch", hide_index=True)

        render_panel_title("3. Adoption globale [Solution Numérique + G2] des Clients_Perfect")
        perfect_summary = report_view.get("perfect_adoption_synthese", pd.DataFrame())
        perfect_statuses = report_view.get("perfect_adoption_statuts", pd.DataFrame())
        perfect_detail = report_view.get("perfect_adoption_detail", pd.DataFrame())
        if perfect_summary.empty:
            st.info("Chargez Clients_Perfect pour mesurer l'adoption Solution Numérique + G2 sur les Phone_Prefixe valides.")
        else:
            perfect_summary_display = perfect_summary.rename(
                columns={
                    "clients_perfect_dans_mpesa": "clients_perfect_dans_turbo_g2",
                    "taux_adoption_mpesa_pct": "taux_adoption_turbo_g2_pct",
                }
            )
            _mpesa_dataframe(perfect_summary_display, width="stretch", hide_index=True)
            if not perfect_statuses.empty:
                fig = px.bar(
                    perfect_statuses,
                    x="statut_adoption",
                    y="nombre_clients",
                    color="statut_adoption",
                    labels={"statut_adoption": "Statut d'adoption", "nombre_clients": "Telephones [Clients_Perfect]"},
                )
                style_standard_vertical_bar(fig, height=360, tickangle=-25)
                st_plot(fig, key="mpesa_pilotage_perfect_adoption", height=360)
            with st.expander("Afficher les Clients_Perfect par statut d'adoption", expanded=False):
                perfect_detail_display = perfect_detail.rename(
                    columns={
                        "present_dans_mpesa": "present_dans_turbo_g2",
                        "devises_mpesa": "devises_turbo_g2",
                        "types_operations_mpesa": "types_operations_turbo_g2",
                    }
                )
                _mpesa_dataframe(perfect_detail_display, width="stretch", hide_index=True)

    with risk_tab:
        render_panel_title("1. Concentration des transactions [G2]")
        concentration_summary = report_view.get("concentration_synthese", pd.DataFrame())
        concentration_clients = report_view.get("concentration_clients", pd.DataFrame())
        if concentration_summary.empty:
            st.info("Aucun telephone G2 valide ne permet de mesurer la concentration.")
        else:
            _mpesa_dataframe(concentration_summary, width="stretch", hide_index=True)
            top_clients = concentration_clients.loc[concentration_clients["rang_volume"].le(10)].copy()
            if not top_clients.empty:
                fig = px.bar(
                    top_clients.sort_values("volume_total"),
                    x="volume_total",
                    y="phone_prefixe",
                    color="currency_code",
                    facet_col="currency_code",
                    facet_col_wrap=2,
                    orientation="h",
                    labels={"volume_total": "Volume entrees + sorties", "phone_prefixe": "Telephone", "currency_code": "Devise"},
                )
                style_standard_horizontal_bar(fig, height=max(380, 30 * len(top_clients)))
                st_plot(fig, key="mpesa_pilotage_concentration", height=max(380, 30 * len(top_clients)))
            with st.expander("Afficher le classement complet des clients", expanded=False):
                _mpesa_dataframe(concentration_clients, width="stretch", hide_index=True)

        render_panel_title("2. Qualite et alertes transactions [G2]")
        quality_summary = report_view.get("qualite_synthese", pd.DataFrame())
        alerts = report_view.get("alertes_transactions", pd.DataFrame())
        if quality_summary.empty:
            st.info("Chargez Transactions G2 pour calculer les taux de succes, d'anomalie et de qualite.")
        else:
            _mpesa_dataframe(quality_summary, width="stretch", hide_index=True)
            alert_reason = alerts.get(
                "motif_alerte_comportement", pd.Series("", index=alerts.index)
            ).astype("string").fillna("")
            operational_mask = alert_reason.str.startswith("Anomalie de controle")
            behavioral_alerts = alerts.loc[~operational_mask].copy()
            operational_count = int(operational_mask.sum())
            if operational_count:
                st.caption(
                    f"{operational_count} anomalie(s) de rapprochement : le detail est centralise dans G2 / DAT."
                )
            with st.expander(
                f"Afficher les {len(behavioral_alerts)} signal(aux) comportemental(aux)",
                expanded=False,
            ):
                if not behavioral_alerts.empty:
                    _render_alert_banner(
                        "Une alerte comportementale est un signal de revue, pas une preuve de fraude."
                    )
                _mpesa_dataframe(
                    behavioral_alerts,
                    width="stretch",
                    hide_index=True,
                )

        render_panel_title("3. Echeancier DAT - risque d'echeance")
        dat_summary = report_view.get("dat_echeances_synthese", pd.DataFrame())
        dat_detail = report_view.get("dat_echeances_detail", pd.DataFrame())
        if dat_summary.empty:
            st.info("Chargez Savings Account avec maturity_date pour construire l'echeancier.")
        else:
            if dat_interest_rate > 0:
                st.caption(
                    f"Interet simple estime avec le taux annuel DAT de {dat_interest_rate:.2f}% defini dans "
                    "Reference et stockage. Le solde DAT est utilise comme capital de calcul."
                )
            else:
                st.caption(
                    "L'estimation des interets est desactivee. Renseignez un taux annuel DAT superieur a 0 "
                    "dans Reference et stockage avant le chargement."
                )
            fig = px.bar(
                dat_summary,
                x="tranche_echeance",
                y="montant_dat",
                color="currency_code",
                facet_col="currency_code",
                facet_col_wrap=2,
                labels={"tranche_echeance": "Echeance", "montant_dat": "Montant DAT", "currency_code": "Devise"},
                category_orders={
                    "tranche_echeance": ["Echu", "0 a 7 jours", "8 a 30 jours", "31 a 60 jours", "61 a 90 jours", "Plus de 90 jours", "Date manquante"]
                },
            )
            style_standard_vertical_bar(fig, height=390, tickangle=-25)
            st_plot(fig, key="mpesa_pilotage_dat_maturity", height=390)
            with st.expander("Afficher les DAT et leurs echeances", expanded=False):
                _mpesa_dataframe(dat_detail, width="stretch", hide_index=True)

    render_panel_title("Export cible du cockpit [Solution Numérique + G2]")
    export_keys = [
        "credit_synthese", "credit_detail", "liquidite_synthese", "liquidite_journaliere",
        "activite_clients", "conversion_clients", "concentration_clients", "qualite_synthese",
        "alertes_transactions", "dat_echeances_detail", "perfect_adoption_detail",
    ]
    export_report = {
        key: report_view[key]
        for key in export_keys
        if key in report_view and isinstance(report_view[key], pd.DataFrame) and not report_view[key].empty
    }
    if st.button("Preparer l'export Excel du cockpit", key="mpesa_prepare_pilotage_export", width="stretch"):
        with st.spinner("Preparation des feuilles importantes..."):
            export_bytes = _create_excel_export_current_sidebar(export_report)
        st.download_button(
            "Telecharger le cockpit Solution Numérique + G2",
            data=export_bytes,
            file_name=f"pilotage_turbo_g2_{pd.Timestamp(report_analysis_date):%Y%m%d}.xlsx" if pd.notna(report_analysis_date) else "pilotage_turbo_g2.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    st.caption(
        "L'Excel est genere uniquement sur demande et contient les syntheses et listes d'action du cockpit; "
        "aucun PDF n'est genere."
    )


@st.fragment
def _render_loans_tab(report: dict[str, Any] | None, prepared: MpesaPreparedData) -> None:
    loans_weekly_comparison = _build_mpesa_weekly_comparison_cached(
        prepared,
        _latest_complete_turbo_date(prepared),
        _selected_mpesa_comparison_period(),
    )
    _render_weekly_comparison(
        loans_weekly_comparison,
        blocks=["Credits"],
        indicator_keys=[
            "nouveaux_credits",
            "montant_nouveaux_credits",
            "remboursements_credits",
        ],
        title="Evolution comparative des credits",
    )
    if report is not None:
        render_panel_title("Credits du client")
        credits_view = _apply_local_multiselect_filters(
            report["credits"],
            ["currency_code", "status_name", "loan_id"],
            key_prefix="mpesa_client_loans_filter",
        )
        st.caption(f"{len(credits_view)} credit(s) affiche(s).")
        _mpesa_dataframe(credits_view, width="stretch", hide_index=True)
        return

    date_candidates: list[pd.Series] = []
    if not prepared.transactions.empty and "created_at" in prepared.transactions.columns:
        date_candidates.append(pd.to_datetime(prepared.transactions["created_at"], errors="coerce").dropna())
    if not prepared.loans.empty:
        for column in ["created_at", "updated_at", "due_date"]:
            if column in prepared.loans.columns:
                date_candidates.append(pd.to_datetime(prepared.loans[column], errors="coerce").dropna())
    combined_dates = (
        pd.concat(date_candidates, ignore_index=True).dropna()
        if date_candidates
        else pd.Series(dtype="datetime64[ns]")
    )
    if combined_dates.empty:
        st.info("Chargez Transactions ou Loans Account avec des dates exploitables pour construire le cockpit Credits.")
        return

    minimum_date = combined_dates.min().date()
    maximum_date = combined_dates.max().date()
    default_end = maximum_date
    default_start = max(minimum_date, (pd.Timestamp(default_end) - pd.Timedelta(days=90)).date())

    render_summary_box(
        "Cockpit Credits - Solution Numerique",
        [
            "Loans Account est lu comme un instantane actuel du portefeuille credit.",
            "Transactions fournit les flux observes de production et de remboursement sur la periode.",
            "Le PAR affiche est simplifie depuis due_date; il ne remplace pas un PAR reglementaire issu d'un plan d'amortissement detaille.",
            "L'epargne est juxtaposee au credit pour analyse; elle n'est jamais compensee ni appelee garantie sans preuve contractuelle.",
        ],
    )

    with st.container(border=True):
        filter_cols = st.columns(5)
        with filter_cols[0]:
            date_start = st.date_input(
                "Date de debut",
                value=default_start,
                min_value=minimum_date,
                max_value=maximum_date,
                key="mpesa_credit_date_start",
                format="DD/MM/YYYY",
                help="Premiere date incluse pour les flux de production et de remboursement. Les positions Loans Account restent des instantanes.",
            )
        with filter_cols[1]:
            date_end = st.date_input(
                "Date de fin",
                value=default_end,
                min_value=minimum_date,
                max_value=maximum_date,
                key="mpesa_credit_date_end",
                format="DD/MM/YYYY",
                help="Derniere date incluse. Le risque simplifie et les echeances sont lus a cette date d'analyse.",
            )
        with filter_cols[2]:
            frequency = st.selectbox(
                "Frequence",
                options=["Jour", "Semaine", "Mois"],
                index=2,
                key="mpesa_credit_frequency",
                help="Regroupe uniquement les tendances de flux. Ce choix ne modifie ni les totaux ni l'instantane Loans Account.",
            )
        with filter_cols[3]:
            high_exposure_top_n = st.number_input(
                "Top expositions",
                min_value=5,
                max_value=100,
                value=20,
                step=5,
                key="mpesa_credit_top_exposure",
                help="Nombre maximal de gros prets conserves dans les listes de concentration et d'action.",
            )
        with filter_cols[4]:
            dat_rate = st.number_input(
                "Taux DAT (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT),
                step=0.25,
                key="mpesa_credit_dat_rate",
                help="Taux utilise uniquement pour les analyses DAT partagees; il ne modifie aucun montant de credit.",
            )

    cockpit = _build_mpesa_credit_cockpit_cached(
        prepared,
        date_start,
        date_end,
        frequency,
        float(dat_rate),
        int(high_exposure_top_n),
    )

    overview = cockpit.get("vue_ensemble", pd.DataFrame())
    portfolio_summary = cockpit.get("portefeuille_synthese", pd.DataFrame())
    portfolio_detail = cockpit.get("portefeuille_detail", pd.DataFrame())
    status_summary = cockpit.get("statuts_portefeuille", pd.DataFrame())
    production_summary = cockpit.get("production_synthese", pd.DataFrame())
    production_detail = cockpit.get("production_detail", pd.DataFrame())
    repayment_summary = cockpit.get("remboursements_synthese", pd.DataFrame())
    repayment_detail = cockpit.get("remboursements_detail", pd.DataFrame())
    risk_summary = cockpit.get("risque_synthese", pd.DataFrame())
    risk_detail = cockpit.get("risque_detail", pd.DataFrame())
    maturity_summary = cockpit.get("echeances_synthese", pd.DataFrame())
    maturity_detail = cockpit.get("echeances_detail", pd.DataFrame())
    concentration_loans = cockpit.get("concentration_prets", pd.DataFrame())
    concentration_clients = cockpit.get("concentration_clients", pd.DataFrame())
    concentration_summary = cockpit.get("concentration_synthese", pd.DataFrame())
    concentration_products = cockpit.get("concentration_produits", pd.DataFrame())
    concentration_bands = cockpit.get("concentration_tranches", pd.DataFrame())
    credit_savings_clients = cockpit.get("credit_epargne_clients", pd.DataFrame())
    credit_savings_summary = cockpit.get("credit_epargne_synthese", pd.DataFrame())
    credit_savings_controls = cockpit.get("credit_epargne_controles", pd.DataFrame())
    cohorts = cockpit.get("cohortes_a_date", pd.DataFrame())
    action_lists = cockpit.get("listes_action", {})
    data_quality = cockpit.get("qualite_donnees", pd.DataFrame())
    kpi_catalog = cockpit.get("catalogue_kpi", pd.DataFrame())

    tabs_key = "mpesa_credit_cockpit_tabs"
    inject_professional_tabs_css(container_key=tabs_key)
    tabs_container = st.container(key=tabs_key)
    (
        overview_tab,
        production_tab,
        portfolio_tab,
        repayment_tab,
        risk_tab,
        maturity_tab,
        concentration_tab,
        savings_tab,
        cohort_tab,
        actions_tab,
        quality_tab,
    ) = tabs_container.tabs(
        format_professional_tab_labels(
            [
                "Vue d'ensemble",
                "Production",
                "Portefeuille actuel",
                "Remboursements",
                "Risque simplifie",
                "Echeances",
                "Concentration",
                "Credit et epargne",
                "Cohortes a date",
                "Listes d'action",
                "Qualite des donnees",
            ]
        )
    )

    def _currency_filter(frame: pd.DataFrame, *, key_prefix: str) -> pd.DataFrame:
        return _apply_local_multiselect_filters(
            frame,
            ["currency_code"],
            key_prefix=key_prefix,
        )

    with overview_tab:
        render_panel_title("Vue d'ensemble du portefeuille credit")
        st.caption(
            "Les montants sont presentes par devise. Les nombres de prets ou clients peuvent etre lus globalement, mais les CDF et USD ne sont jamais additionnes."
        )
        if overview.empty:
            st.info("Aucun indicateur credit calculable avec les sources chargees.")
        else:
            for currency in sorted(overview["currency_code"].dropna().astype(str).unique()):
                scoped = overview.loc[overview["currency_code"].astype(str).eq(currency)]
                def val(indicator: str) -> Any:
                    rows = scoped.loc[scoped["indicateur"].eq(indicator)]
                    return rows.iloc[0]["valeur"] if not rows.empty else None
                render_panel_title(f"Devise {currency}")
                render_kpi_cards(
                    [
                        ("Prets actifs", _format_count(val("prets_actifs")), "Encours positif dans Loans Account", "blue"),
                        ("Emprunteurs actifs", _format_count(val("emprunteurs_actifs")), "Clients avec encours positif", "slate"),
                        ("Encours actuel", f"{_format_amount(val('encours_credit'))} {currency}", "Instantane Loans Account", "navy"),
                        ("Montant decaisse", f"{_format_amount(val('montant_decaisse'))} {currency}", "Flux observe sur la periode", "green"),
                        ("Montant rembourse", f"{_format_amount(val('montant_rembourse_observe'))} {currency}", "Remboursements observes", "orange"),
                        ("PAR simplifie 30j", _format_percent(val("par_simplifie_30j_pct")), "Depuis due_date", "red"),
                    ]
                )
            _mpesa_dataframe(overview, width="stretch", hide_index=True)

    with production_tab:
        render_panel_title("Production de credit sur la periode")
        if production_summary.empty and production_detail.empty:
            st.info("Aucun decaissement de credit observe sur la periode filtree.")
        else:
            _mpesa_dataframe(_currency_filter(production_summary, key_prefix="mpesa_credit_production_summary"), width="stretch", hide_index=True)
            if not production_detail.empty:
                production_view = _apply_local_multiselect_filters(
                    production_detail,
                    ["currency_code", "customer_id", "type_operation", "statut_controle_turbo"],
                    key_prefix="mpesa_credit_production_detail",
                )
                _mpesa_dataframe(production_view, width="stretch", height=420, hide_index=True)

    with portfolio_tab:
        render_panel_title("Portefeuille actuel depuis Loans Account")
        if portfolio_summary.empty:
            st.info("Chargez Loans Account pour obtenir la position actuelle du portefeuille.")
        else:
            _mpesa_dataframe(_currency_filter(portfolio_summary, key_prefix="mpesa_credit_portfolio_summary"), width="stretch", hide_index=True)
            detail_view = _apply_local_multiselect_filters(
                portfolio_detail,
                ["currency_code", "status_name", "defaulted", "is_rollover", "is_grace_period", "loan_product_id", "customer_id", "msisdn1"],
                key_prefix="mpesa_credit_portfolio_detail",
            )
            _mpesa_dataframe(detail_view, width="stretch", height=520, hide_index=True)
            with st.expander("Statuts et qualite du portefeuille", expanded=False):
                status_view = _apply_local_multiselect_filters(
                    status_summary,
                    ["currency_code", "famille_statut", "valeur_statut"],
                    key_prefix="mpesa_credit_status_summary",
                )
                _mpesa_dataframe(status_view, width="stretch", hide_index=True)

    with repayment_tab:
        render_panel_title("Remboursements observes")
        if repayment_summary.empty and repayment_detail.empty:
            st.info("Aucun remboursement observe sur la periode filtree.")
        else:
            _mpesa_dataframe(_currency_filter(repayment_summary, key_prefix="mpesa_credit_repayment_summary"), width="stretch", hide_index=True)
            repayment_view = _apply_local_multiselect_filters(
                repayment_detail,
                ["currency_code", "customer_id", "type_operation", "origine_remboursement", "statut_controle_turbo"],
                key_prefix="mpesa_credit_repayment_detail",
            )
            _mpesa_dataframe(repayment_view, width="stretch", height=440, hide_index=True)

    with risk_tab:
        render_panel_title("Risque simplifie")
        st.info(
            "Indicateur simplifie construit depuis la date d'echeance disponible dans Loans Account. Il ne remplace pas un PAR issu d'un plan d'amortissement detaille."
        )
        if risk_summary.empty:
            st.info("Aucun risque credit calculable sans Loans Account exploitable.")
        else:
            _mpesa_dataframe(_currency_filter(risk_summary, key_prefix="mpesa_credit_risk_summary"), width="stretch", hide_index=True)
            risk_view = _apply_local_multiselect_filters(
                risk_detail,
                ["currency_code", "statut_risque", "status_name", "customer_id"],
                key_prefix="mpesa_credit_risk_detail",
            )
            _mpesa_dataframe(risk_view, width="stretch", height=460, hide_index=True)

    with maturity_tab:
        render_panel_title("Echeances et maturite des prets")
        st.caption("Vue construite depuis due_date. Elle indique la maturite du pret, pas un echeancier detaille de mensualites.")
        if maturity_summary.empty:
            st.info("Aucune due_date exploitable dans Loans Account.")
        else:
            maturity_view = _apply_local_multiselect_filters(
                maturity_summary,
                ["currency_code", "tranche_echeance"],
                key_prefix="mpesa_credit_maturity_summary",
            )
            _mpesa_dataframe(maturity_view, width="stretch", hide_index=True)
            maturity_detail_view = _apply_local_multiselect_filters(
                maturity_detail,
                ["currency_code", "tranche_echeance", "status_name", "customer_id", "msisdn1"],
                key_prefix="mpesa_credit_maturity_detail",
            )
            _mpesa_dataframe(maturity_detail_view, width="stretch", height=460, hide_index=True)

    with concentration_tab:
        render_panel_title("Concentration du portefeuille")
        if concentration_loans.empty and concentration_clients.empty:
            st.info("Aucune concentration calculable sans encours credit positif.")
        else:
            with st.expander("Synthese de concentration", expanded=True):
                _mpesa_dataframe(_currency_filter(concentration_summary, key_prefix="mpesa_credit_concentration_summary"), width="stretch", hide_index=True)
            with st.expander("Top prets par encours", expanded=True):
                top_loans_view = _apply_local_multiselect_filters(
                    concentration_loans,
                    ["currency_code", "loan_product_id", "customer_id", "msisdn1"],
                    key_prefix="mpesa_credit_top_loans",
                )
                _mpesa_dataframe(top_loans_view, width="stretch", height=420, hide_index=True)
            with st.expander("Top clients, produits et tranches", expanded=False):
                _mpesa_dataframe(_currency_filter(concentration_clients, key_prefix="mpesa_credit_top_clients"), width="stretch", hide_index=True)
                _mpesa_dataframe(_currency_filter(concentration_products, key_prefix="mpesa_credit_products"), width="stretch", hide_index=True)
                _mpesa_dataframe(_currency_filter(concentration_bands, key_prefix="mpesa_credit_bands"), width="stretch", hide_index=True)

    with savings_tab:
        render_panel_title("Credit et epargne observee")
        st.caption(
            "Cette vue juxtapose encours credit, compte ouvert et DAT au grain client x devise. Elle ne compense pas comptablement credit et epargne."
        )
        if credit_savings_summary.empty and credit_savings_clients.empty:
            st.info("Chargez Savings Account avec Loans Account pour obtenir le rapprochement credit/epargne.")
        else:
            _mpesa_dataframe(_currency_filter(credit_savings_summary, key_prefix="mpesa_credit_savings_summary"), width="stretch", hide_index=True)
            savings_view = _apply_local_multiselect_filters(
                credit_savings_clients,
                ["currency_code", "statut_rapprochement", "customer_id", "telephone_credit"],
                key_prefix="mpesa_credit_savings_clients",
            )
            _mpesa_dataframe(savings_view, width="stretch", height=480, hide_index=True)
            if credit_savings_controls.empty:
                st.success("Aucune ambiguite credit/epargne a revoir dans les sources chargees.")
            else:
                _render_alert_banner(f"{len(credit_savings_controls)} rapprochement(s) credit/epargne necessitent une verification.")
                controls_view = _apply_local_multiselect_filters(
                    credit_savings_controls,
                    ["currency_code", "customer_id", "telephone_credit", "methode_rapprochement_epargne"],
                    key_prefix="mpesa_credit_savings_controls",
                )
                _mpesa_dataframe(controls_view, width="stretch", hide_index=True)

    with cohort_tab:
        render_panel_title("Cohortes a date de situation")
        st.caption("Analyse par mois de creation du pret. Ce n'est pas une courbe vintage historique complete.")
        if cohorts.empty:
            st.info("Aucune cohorte calculable sans created_at dans Loans Account.")
        else:
            cohort_view = _apply_local_multiselect_filters(
                cohorts,
                ["currency_code", "cohorte_creation"],
                key_prefix="mpesa_credit_cohorts",
            )
            _mpesa_dataframe(cohort_view, width="stretch", hide_index=True)

    with actions_tab:
        render_panel_title("Listes d'action credit")
        if not isinstance(action_lists, dict) or not action_lists:
            st.info("Aucune liste d'action credit disponible.")
        else:
            names = list(action_lists.keys())
            selected_lists = st.multiselect(
                "Listes a afficher",
                options=names,
                default=names[:2],
                format_func=lambda value: str(value).replace("_", " ").title(),
                key="mpesa_credit_action_lists",
                help="Selection multiple pour comparer plusieurs listes de suivi credit. Une selection vide masque les listes a l'ecran, mais pas l'export.",
            )
            if not selected_lists:
                st.info("Selectionnez au moins une liste d'action.")
            for name in selected_lists:
                frame = action_lists.get(name, pd.DataFrame())
                st.markdown(f"**{str(name).replace('_', ' ').title()}**")
                if isinstance(frame, pd.DataFrame) and not frame.empty:
                    frame = _apply_local_multiselect_filters(
                        frame,
                        ["currency_code", "status_name", "customer_id", "msisdn1", "loan_product_id", "tranche_echeance"],
                        key_prefix=f"mpesa_credit_action_{name}",
                    )
                _mpesa_dataframe(frame, width="stretch", height=360, hide_index=True)

    with quality_tab:
        render_panel_title("Qualite des donnees et KPI non calculables")
        if data_quality.empty:
            st.success("Aucun controle qualite credit a signaler.")
        else:
            alerts = data_quality.loc[data_quality.get("statut", pd.Series(dtype=str)).astype(str).eq("A verifier")]
            if alerts.empty:
                st.success("Aucun controle credit bloquant; certaines limites restent documentees.")
            else:
                _render_alert_banner(f"{len(alerts)} controle(s) credit necessitent une verification.")
            _mpesa_dataframe(data_quality, width="stretch", hide_index=True)
        st.markdown("**Catalogue KPI credit et data gaps**")
        _mpesa_dataframe(kpi_catalog, width="stretch", hide_index=True)

    export_report = {
        "credit_vue_ensemble": overview,
        "credit_portefeuille_synthese": portfolio_summary,
        "credit_portefeuille_detail": portfolio_detail,
        "credit_statuts_portefeuille": status_summary,
        "credit_production_synthese": production_summary,
        "credit_production_detail": production_detail,
        "credit_remboursements_synthese": repayment_summary,
        "credit_remboursements_detail": repayment_detail,
        "credit_risque_synthese": risk_summary,
        "credit_risque_detail": risk_detail,
        "credit_echeances_synthese": maturity_summary,
        "credit_echeances_detail": maturity_detail,
        "credit_concentration_prets": concentration_loans,
        "credit_concentration_clients": concentration_clients,
        "credit_concentration_synthese": concentration_summary,
        "credit_concentration_produits": concentration_products,
        "credit_concentration_tranches": concentration_bands,
        "credit_epargne_clients": credit_savings_clients,
        "credit_epargne_synthese": credit_savings_summary,
        "credit_epargne_controles": credit_savings_controls,
        "credit_cohortes_a_date": cohorts,
        "credit_qualite_donnees": data_quality,
        "credit_catalogue_kpi": kpi_catalog,
        **{f"credit_liste_{key}": value for key, value in action_lists.items()},
    }
    st.download_button(
        "Telecharger le cockpit Credits Excel",
        data=lambda: _create_excel_export_current_sidebar(export_report),
        file_name=f"cockpit_credits_solution_numerique_{pd.Timestamp(date_start):%Y%m%d}_{pd.Timestamp(date_end):%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
        width="content",
        help="Export Excel des syntheses, details et listes d'action credit du perimetre filtre.",
    )


@st.fragment
def _render_finance_turbo_tab(prepared: MpesaPreparedData) -> None:
    """Affiche le pilotage et la comptabilite observes depuis la source numérique."""
    if prepared.transactions.empty or "created_at" not in prepared.transactions.columns:
        st.info(
            "Chargez Transactions pour construire le pilotage financier. "
            "G2 ne remplace jamais cette source."
        )
        return

    transaction_dates = pd.to_datetime(
        prepared.transactions["created_at"], errors="coerce"
    ).dropna()
    if transaction_dates.empty:
        st.warning("Aucune date exploitable pour definir la periode d'analyse.")
        return

    minimum_date = transaction_dates.min().date()
    maximum_date = transaction_dates.max().date()
    default_end = maximum_date
    latest_timestamp = transaction_dates.max()
    if minimum_date < maximum_date and latest_timestamp.hour < 18:
        previous_date = (pd.Timestamp(maximum_date) - pd.Timedelta(days=1)).date()
        if previous_date >= minimum_date:
            default_end = previous_date
    default_start = max(
        minimum_date,
        (pd.Timestamp(default_end) - pd.Timedelta(days=30)).date(),
    )

    render_summary_box(
        "Finance et comptabilité — Solution Numérique",
        [
            "La Solution Numérique constitue la source operationnelle principale de la Solution M_PESA.",
            "Les rapports G2 M-Pesa enrichissent l'identite du client et fournissent une preuve de rapprochement des ecritures, sans intervenir dans le calcul des montants, des soldes, des DAT ou des remboursements.",
            "Les flux sont calcules au grain de l'evenement Solution Numérique consolide; les positions Credits, Epargne et DAT sont des instantanes du portail.",
            "CDF et USD restent toujours separes. Aucun total monetaire multidevise n'est produit.",
            "Tous les volets ci-dessous sont calcules une fois et conserves en cache; changer d'onglet ne relance pas l'analyse.",
        ],
    )

    with st.form("mpesa_finance_turbo_filters"):
        start_col, end_col, frequency_col = st.columns([1.0, 1.0, 1.0])
        with start_col:
            selected_start_date = st.date_input(
                "Date de début",
                value=default_start,
                min_value=minimum_date,
                max_value=maximum_date,
                key=(
                    f"mpesa_finance_turbo_start_{minimum_date:%Y%m%d}_"
                    f"{maximum_date:%Y%m%d}_{len(transaction_dates)}"
                ),
                help="Première journée incluse dans les analyses Finance et comptabilité.",
                format="DD/MM/YYYY",
            )
        with end_col:
            selected_end_date = st.date_input(
                "Date de fin",
                value=default_end,
                min_value=minimum_date,
                max_value=maximum_date,
                key=(
                    f"mpesa_finance_turbo_end_{minimum_date:%Y%m%d}_"
                    f"{maximum_date:%Y%m%d}_{len(transaction_dates)}"
                ),
                help="Dernière journée incluse. La dernière journée complète est proposée par défaut.",
                format="DD/MM/YYYY",
            )
        with frequency_col:
            frequency = st.selectbox(
                "Frequence d'evolution",
                ["Jour", "Semaine", "Mois"],
                key="mpesa_finance_turbo_frequency",
                help=(
                    "Regroupe les mouvements dans les graphiques par jour, semaine "
                    "ou mois. Ce choix ne change pas la période analysée ni les "
                    "totaux; il modifie seulement le niveau de détail temporel."
                ),
            )
        st.caption(
            "Seuils de controle proposes depuis les analyses prioritaires Perfect Vision; ils restent propres a chaque devise."
        )
        threshold_columns = st.columns(4)
        fractionation_cdf = threshold_columns[0].number_input(
            "Fractionnement CDF",
            min_value=0.0,
            value=14_000_000.0,
            step=100_000.0,
            key="mpesa_fractionation_cdf",
            help=(
                "Seuil de contrôle en CDF. Une alerte apparaît lorsqu'un même "
                "client réalise, le même jour, au moins deux opérations qui sont "
                "chacune sous ce seuil mais dont le cumul atteint ou dépasse le "
                "seuil. L'alerte demande une vérification; elle ne prouve pas une fraude."
            ),
        )
        fractionation_usd = threshold_columns[1].number_input(
            "Fractionnement USD",
            min_value=0.0,
            value=5_000.0,
            step=100.0,
            key="mpesa_fractionation_usd",
            help=(
                "Même contrôle que `Fractionnement CDF`, appliqué uniquement aux "
                "opérations USD du même client et du même jour."
            ),
        )
        important_cdf = threshold_columns[2].number_input(
            "Transaction importante CDF",
            min_value=0.0,
            value=28_000_000.0,
            step=100_000.0,
            key="mpesa_important_cdf",
            help=(
                "Montant à partir duquel une opération individuelle en CDF est "
                "signalée comme importante pour revue. Le signal n'annule pas "
                "l'opération et ne signifie pas qu'elle est incorrecte."
            ),
        )
        important_usd = threshold_columns[3].number_input(
            "Transaction importante USD",
            min_value=0.0,
            value=10_000.0,
            step=100.0,
            key="mpesa_important_usd",
            help=(
                "Montant à partir duquel une opération individuelle en USD est "
                "signalée comme importante pour revue."
            ),
        )
        st.form_submit_button("Actualiser l'analyse", type="primary")

    date_start = selected_start_date
    date_end = selected_end_date
    if date_start > date_end:
        st.error(
            "La date de début doit être antérieure ou égale à la date de fin.",
            icon=":material/error:",
        )
        return

    dat_interest_rate = float(
        st.session_state.get(
            "mpesa_dat_annual_interest_rate_pct",
            DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT,
        )
    )
    with st.spinner("Consolidation des evenements et analyses financieres et comptables..."):
        report = _build_mpesa_management_dashboard_cached(
            prepared,
            dat_interest_rate,
            date_start,
            date_end,
            frequency,
            float(fractionation_cdf),
            float(fractionation_usd),
            float(important_cdf),
            float(important_usd),
        )
        accounting_report = _build_mpesa_accounting_analysis_cached(
            prepared,
            date_start,
            date_end,
        )
        weekly_comparison = _build_mpesa_weekly_comparison_cached(
            prepared,
            date_end,
            _selected_mpesa_comparison_period(),
            date_start,
        )

    currency_options: set[str] = set()
    for current_report in (report, accounting_report):
        for value in current_report.values():
            if isinstance(value, pd.DataFrame) and not value.empty and "currency_code" in value.columns:
                currency_options.update(
                    item
                    for item in value["currency_code"].dropna().astype(str).unique()
                    if item.strip()
                )
    currency_options_sorted = sorted(currency_options)
    selected_currencies = st.multiselect(
        "Devises affichees",
        options=currency_options_sorted,
        default=currency_options_sorted,
        key="mpesa_finance_turbo_currencies",
        help="Une selection vide conserve toutes les devises.",
    )
    report_view = _filter_pilotage_currencies(report, selected_currencies)
    accounting_view = _filter_pilotage_currencies(
        accounting_report,
        selected_currencies,
    )

    st.caption(
        f"Periode analysee : {pd.Timestamp(date_start):%d/%m/%Y} au "
        f"{pd.Timestamp(date_end):%d/%m/%Y} | Frequence : {frequency}. "
        "Les positions de portefeuille restent des instantanes de la Solution Numérique."
    )
    _render_weekly_comparison(
        weekly_comparison,
        blocks=["Clients", "Comptes", "Credits", "Transactions"],
        selected_currencies=selected_currencies,
    )
    sources = report_view.get("sources", pd.DataFrame())
    if not sources.empty:
        missing_main_sources = sources.loc[
            sources["source"].isin(
                [
                    "Transactions M-PESA_Turbo",
                    "Savings Account",
                    "Loans Account",
                    "Customers",
                ]
            )
            & ~sources["disponible"].astype("boolean").fillna(False).astype(bool),
            "source",
        ].astype(str).tolist()
        if missing_main_sources:
            st.warning(
                "Sources principales non chargees : " + ", ".join(missing_main_sources)
            )

    financial_tabs_key = "mpesa_finance_turbo_inner_tabs"
    inject_professional_tabs_css(container_key=financial_tabs_key)
    financial_tabs_container = st.container(key=financial_tabs_key)
    overview_tab, flows_tab, portfolio_tab, accounting_tab, risks_tab, export_tab = (
        financial_tabs_container.tabs(
            format_professional_tab_labels(MPESA_FINANCE_TURBO_TAB_LABELS)
        )
    )

    with overview_tab:
        flow_summary = report_view.get("flux_synthese", pd.DataFrame())
        credit_summary = report_view.get("credit_synthese", pd.DataFrame())
        alerts = report_view.get("alertes_transactions", pd.DataFrame())
        dat_detail = report_view.get("dat_echeances_detail", pd.DataFrame())
        currencies = sorted(
            set(flow_summary.get("currency_code", pd.Series(dtype=str)).dropna().astype(str))
            | set(credit_summary.get("currency_code", pd.Series(dtype=str)).dropna().astype(str))
        )
        if not currencies:
            st.info("Aucun indicateur monetaire n'est calculable sur la periode.")
        for currency in currencies:
            st.markdown(f"#### {currency}")
            flow_row = (
                flow_summary.loc[flow_summary["currency_code"].eq(currency)]
                if "currency_code" in flow_summary.columns
                else pd.DataFrame()
            )
            credit_row = (
                credit_summary.loc[credit_summary["currency_code"].eq(currency)]
                if "currency_code" in credit_summary.columns
                else pd.DataFrame()
            )
            entries = float(flow_row.iloc[0].get("montant_entrees", 0)) if not flow_row.empty else 0.0
            exits = float(flow_row.iloc[0].get("montant_sorties", 0)) if not flow_row.empty else 0.0
            repayments = float(flow_row.iloc[0].get("remboursements_observes", 0)) if not flow_row.empty else 0.0
            new_credit = float(flow_row.iloc[0].get("nouveaux_credits_decaissements", 0)) if not flow_row.empty else 0.0
            outstanding = float(credit_row.iloc[0].get("encours_total", 0)) if not credit_row.empty else 0.0
            par_30 = credit_row.iloc[0].get("par_30j_pct", pd.NA) if not credit_row.empty else pd.NA
            render_kpi_cards(
                [
                    (f"Entrees [{currency}]", _format_amount(entries), "Depots et remboursements", "green"),
                    (f"Sorties [{currency}]", _format_amount(exits), "Retraits et decaissements", "orange"),
                    (f"Remboursements [{currency}]", _format_amount(repayments), "Observes dans Transactions", "blue"),
                    (f"Nouveaux credits [{currency}]", _format_amount(new_credit), "Decaissements observes", "navy"),
                    (f"Encours / PAR30 [{currency}]", f"{_format_amount(outstanding)} / {_format_percent(par_30)}", "Position Loans Account", "red"),
                ]
            )

        render_panel_title("Priorites de suivi")
        priority_rows: list[dict[str, Any]] = []
        if not alerts.empty:
            for (currency, alert_type), group in alerts.groupby(["currency_code", "alerte"]):
                priority_rows.append(
                    {
                        "priorite": alert_type,
                        "currency_code": currency,
                        "dossiers": len(group),
                        "montant_concerne": group["montant"].sum(),
                    }
                )
        if not dat_detail.empty and "tranche_echeance" in dat_detail.columns:
            due_mask = dat_detail["tranche_echeance"].isin(
                ["Echu", "0 a 7 jours", "8 a 30 jours"]
            )
            for currency, group in dat_detail.loc[due_mask].groupby("currency_code"):
                priority_rows.append(
                    {
                        "priorite": "DAT echus ou a echeance sous 30 jours",
                        "currency_code": currency,
                        "dossiers": len(group),
                        "montant_concerne": group["balance"].sum(),
                    }
                )
        if priority_rows:
            priority_table = pd.DataFrame(priority_rows)
            _render_alert_banner(
                f"{len(priority_table)} priorite(s) necessitent l'attention du lecteur."
            )
            _mpesa_dataframe(priority_table, width="stretch", hide_index=True)
        else:
            st.success("Aucune priorite calculee sur la periode selectionnee.")

        _render_accounting_summary(accounting_view)

    with flows_tab:
        render_panel_title("Evolution des depots, retraits, credits et remboursements")
        evolution = report_view.get("flux_evolution", pd.DataFrame())
        if evolution.empty:
            st.info("Aucun evenement dans la periode selectionnee.")
        else:
            chart_columns = [
                "depots_epargne_courante",
                "depots_dat",
                "retraits_epargne",
                "nouveaux_credits_decaissements",
                "remboursements_observes",
            ]
            chart_data = evolution.melt(
                id_vars=["periode_analyse", "currency_code"],
                value_vars=chart_columns,
                var_name="flux",
                value_name="montant",
            )
            chart_data["flux"] = chart_data["flux"].map(
                {
                    "depots_epargne_courante": "Depots epargne",
                    "depots_dat": "Depots DAT",
                    "retraits_epargne": "Retraits epargne",
                    "nouveaux_credits_decaissements": "Nouveaux credits",
                    "remboursements_observes": "Remboursements",
                }
            )
            fig = px.line(
                chart_data,
                x="periode_analyse",
                y="montant",
                color="flux",
                facet_col="currency_code",
                facet_col_wrap=2,
                markers=True,
                labels={
                    "periode_analyse": "Periode",
                    "montant": "Montant",
                    "flux": "Flux",
                    "currency_code": "Devise",
                },
            )
            style_standard_line(fig, height=430, tickangle=-20)
            st_plot(fig, key="mpesa_turbo_financial_evolution", height=430)
            _mpesa_dataframe(evolution, width="stretch", hide_index=True)

        render_panel_title("Remboursements de credit observes")
        repayments_summary = report_view.get("remboursements_synthese", pd.DataFrame())
        repayments_detail = report_view.get("remboursements_detail", pd.DataFrame())
        if repayments_summary.empty:
            st.info("Aucun remboursement classe dans la periode.")
        else:
            _mpesa_dataframe(repayments_summary, width="stretch", hide_index=True)
            with st.expander("Afficher le detail des remboursements", expanded=False):
                repayment_view = _apply_local_multiselect_filters(
                    repayments_detail,
                    ["currency_code", "mode_remboursement_observe", "statut_controle_turbo"],
                    key_prefix="mpesa_turbo_repayment_filter",
                )
                _mpesa_dataframe(repayment_view.head(1000), width="stretch", hide_index=True)

        _render_accounting_flows(accounting_view)

    with portfolio_tab:
        render_panel_title("Nouveaux credits et decaissements de la periode")
        new_credit_summary = report_view.get("nouveaux_credits_synthese", pd.DataFrame())
        if new_credit_summary.empty:
            st.info("Aucun nouveau compte ou decaissement de credit dans la periode.")
        else:
            _mpesa_dataframe(new_credit_summary, width="stretch", hide_index=True)
            st.caption(
                "L'ecart rapproche les decaissements observes dans Transactions et les comptes crees dans Loans Account. "
                "Il s'agit d'un controle global par devise, pas d'une preuve d'affectation ligne a ligne."
            )

        render_panel_title("Encours, retards et PAR [Loans Account]")
        credit_summary = report_view.get("credit_synthese", pd.DataFrame())
        credit_detail = report_view.get("credit_detail", pd.DataFrame())
        if credit_summary.empty:
            st.info("Chargez Loans Account pour calculer l'encours et le PAR.")
        else:
            _mpesa_dataframe(credit_summary, width="stretch", hide_index=True)
            if not credit_detail.empty:
                risk_chart = (
                    credit_detail.groupby(["currency_code", "statut_risque"], as_index=False)
                    .agg(nombre_credits=("loan_id", "nunique"), encours_total=("encours_total", "sum"))
                )
                fig = px.bar(
                    risk_chart,
                    x="statut_risque",
                    y="encours_total",
                    color="statut_risque",
                    facet_col="currency_code",
                    facet_col_wrap=2,
                    labels={"statut_risque": "Risque", "encours_total": "Encours", "currency_code": "Devise"},
                )
                style_standard_vertical_bar(fig, height=400, tickangle=-25)
                st_plot(fig, key="mpesa_turbo_credit_risk", height=400)

        concentration = report_view.get("concentration_credit_synthese", pd.DataFrame())
        par_bands = report_view.get("par_tranches_montant", pd.DataFrame())
        render_panel_title("Concentration du portefeuille et PAR par tranche")
        if not concentration.empty:
            _mpesa_dataframe(concentration, width="stretch", hide_index=True)
        if not par_bands.empty:
            _mpesa_dataframe(par_bands, width="stretch", hide_index=True)
        with st.expander("Afficher les credits a suivre", expanded=False):
            credit_view = _apply_local_multiselect_filters(
                credit_detail,
                ["currency_code", "statut_risque", "status_name", "customer_id"],
                key_prefix="mpesa_turbo_credit_filter",
            ) if not credit_detail.empty else credit_detail
            _mpesa_dataframe(credit_view.head(1000), width="stretch", hide_index=True)

    with portfolio_tab:
        render_panel_title("Activite d'epargne par client [Transactions]")
        savings_activity = report_view.get("activite_epargne_clients", pd.DataFrame())
        if savings_activity.empty:
            st.info("Aucun depot, retrait ou mouvement DAT dans la periode.")
        else:
            top_savings = (
                savings_activity.sort_values("flux_net_epargne", ascending=False)
                .groupby("currency_code", as_index=False, group_keys=False)
                .head(15)
            )
            fig = px.bar(
                top_savings.sort_values("flux_net_epargne"),
                x="flux_net_epargne",
                y="customer_id",
                color="currency_code",
                facet_col="currency_code",
                facet_col_wrap=2,
                labels={"flux_net_epargne": "Flux net epargne", "customer_id": "Client", "currency_code": "Devise"},
            )
            style_standard_horizontal_bar(fig, height=430)
            st_plot(fig, key="mpesa_turbo_savings_clients", height=430)
            with st.expander("Afficher l'activite epargne client", expanded=False):
                _mpesa_dataframe(savings_activity.head(1000), width="stretch", hide_index=True)

        frequent = report_view.get("depots_frequents_hebdo", pd.DataFrame())
        deposit_bands = report_view.get("tranches_depots", pd.DataFrame())
        render_panel_title("Frequence et tranches de depots")
        if not deposit_bands.empty:
            _mpesa_dataframe(deposit_bands, width="stretch", hide_index=True)
        if not frequent.empty:
            frequent_only = frequent.loc[frequent["deposant_frequent_3_plus"]].copy()
            with st.expander("Afficher les clients avec au moins trois depots par semaine", expanded=False):
                _mpesa_dataframe(frequent_only.head(1000), width="stretch", hide_index=True)

        render_panel_title("DAT a preparer et DAT sans credit actif")
        dat_summary = report_view.get("dat_echeances_synthese", pd.DataFrame())
        dat_without_credit = report_view.get("dat_sans_credit_actif", pd.DataFrame())
        if not dat_summary.empty:
            _mpesa_dataframe(dat_summary, width="stretch", hide_index=True)
        with st.expander("Afficher les DAT positifs sans credit actif dans la meme devise", expanded=False):
            _mpesa_dataframe(dat_without_credit.head(1000), width="stretch", hide_index=True)

        render_panel_title("Credits et epargne disponible, sans compensation")
        credit_savings = report_view.get("credits_epargne_disponible", pd.DataFrame())
        if credit_savings.empty:
            st.info("Aucune position credit/epargne consolidable.")
        else:
            _mpesa_dataframe(credit_savings.head(1000), width="stretch", hide_index=True)

        _render_accounting_portfolio(accounting_view)

    with accounting_tab:
        _render_accounting_balances_and_journals(
            accounting_view,
            date_start=date_start,
            date_end=date_end,
        )

    with risks_tab:
        render_panel_title("Concentration des transactions")
        concentration_summary = report_view.get(
            "concentration_transactions_synthese", pd.DataFrame()
        )
        concentration_clients = report_view.get(
            "concentration_transactions_clients", pd.DataFrame()
        )
        if concentration_summary.empty:
            st.info("Aucune operation dans la periode.")
        else:
            _mpesa_dataframe(concentration_summary, width="stretch", hide_index=True)
            top_clients = concentration_clients.loc[
                concentration_clients["rang_volume"].le(10)
            ].copy()
            if not top_clients.empty:
                fig = px.bar(
                    top_clients.sort_values("volume_total"),
                    x="volume_total",
                    y="customer_id",
                    color="currency_code",
                    facet_col="currency_code",
                    facet_col_wrap=2,
                    labels={"volume_total": "Volume", "customer_id": "Client", "currency_code": "Devise"},
                )
                style_standard_horizontal_bar(fig, height=420)
                st_plot(fig, key="mpesa_turbo_transaction_concentration", height=420)

        render_panel_title("Alertes et controles prioritaires")
        alerts = report_view.get("alertes_transactions", pd.DataFrame())
        if alerts.empty:
            st.success("Aucune alerte calculee avec les seuils selectionnes.")
        else:
            alert_view = _apply_local_multiselect_filters(
                alerts,
                ["currency_code", "alerte", "customer_id"],
                key_prefix="mpesa_turbo_alert_filter",
            )
            _render_alert_banner(
                f"{len(alert_view)} alerte(s) necessitent une verification."
            )
            _mpesa_dataframe(
                alert_view.head(1500),
                width="stretch",
                hide_index=True,
            )

        inactive = report_view.get("mouvements_comptes_inactifs", pd.DataFrame())
        client_quality = report_view.get("qualite_clients_synthese", pd.DataFrame())
        render_panel_title("Mouvements sur comptes inactifs et qualite clients")
        if inactive.empty:
            st.success("Aucun mouvement rattache a un compte epargne/DAT inactif sur la periode.")
        else:
            _render_alert_banner(
                f"{len(inactive)} mouvement(s) sur compte inactif necessitent une verification."
            )
            _mpesa_dataframe(
                inactive.head(1000),
                width="stretch",
                hide_index=True,
            )
        if not client_quality.empty:
            _mpesa_dataframe(
                client_quality,
                width="stretch",
                hide_index=True,
            )

        _render_accounting_controls(prepared, accounting_view)

    with export_tab:
        render_panel_title("Export cible du pilotage financier")
        st.caption(
            "Le classeur reprend uniquement les analyses du cockpit. G2 n'y fournit aucun montant."
        )
        export_keys = [
            "flux_synthese",
            "flux_evolution",
            "remboursements_synthese",
            "remboursements_detail",
            "nouveaux_credits_synthese",
            "nouveaux_credits_detail",
            "credit_synthese",
            "credit_detail",
            "par_tranches_montant",
            "concentration_credit_synthese",
            "activite_epargne_clients",
            "depots_frequents_hebdo",
            "tranches_depots",
            "concentration_transactions_synthese",
            "alertes_transactions",
            "mouvements_comptes_inactifs",
            "dat_sans_credit_actif",
            "credits_epargne_disponible",
            "dat_echeances_detail",
            "qualite_clients_detail",
            "definitions",
            "sources",
        ]
        export_report = {
            key: report_view[key]
            for key in export_keys
            if key in report_view and isinstance(report_view[key], pd.DataFrame)
        }
        if st.button(
            "Preparer l'export Pilotage financier",
            key="mpesa_prepare_turbo_financial_export",
            width="content",
        ):
            with st.spinner("Preparation du classeur..."):
                export_bytes = _create_excel_export_current_sidebar(export_report)
            st.download_button(
                "Telecharger le pilotage financier",
                data=export_bytes,
                file_name=(
                    f"pilotage_financier_turbo_{pd.Timestamp(date_start):%Y%m%d}_"
                    f"{pd.Timestamp(date_end):%Y%m%d}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="mpesa_download_turbo_financial_export",
                width="content",
            )
        with st.expander("Sources et definitions des indicateurs", expanded=False):
            _mpesa_dataframe(sources, width="stretch", hide_index=True)
            _mpesa_dataframe(report_view.get("definitions", pd.DataFrame()), width="stretch", hide_index=True)

        _render_accounting_export(accounting_view, date_start, date_end)


def _render_accounting_summary(report: dict[str, pd.DataFrame]) -> None:
    """Restitue la synthese comptable dans la vue direction partagee."""
    summary = report.get("synthese", pd.DataFrame())
    if summary.empty:
        st.info("Aucune ecriture sur la periode selectionnee.")
        return

    render_panel_title("Comptabilité financière observée")
    st.warning(
        "Cette restitution est une balance observee des sous-registres de la Solution Numérique. Elle ne remplace pas "
        "la balance generale officielle de Perfect Vision : le plan comptable complet et les soldes "
        "d'ouverture certifies ne figurent pas dans cet export."
    )
    for _, row in summary.iterrows():
        currency = str(row["currency_code"])
        render_panel_title(f"Synthese comptable - {currency}")
        render_kpi_cards(
            [
                ("Ecritures", _format_count(row["nombre_lignes"]), f"Devise {currency}", "navy"),
                ("Clients", _format_count(row["nombre_clients"]), "Customer ID distincts", "blue"),
                ("Operations", _format_count(row["nombre_operations"]), "Regroupees au bon grain", "green"),
                (
                    "Operations symetriques",
                    _format_percent(row["taux_operations_symetriques_pct"]),
                    "Debit = credit dans l'export",
                    "green" if float(row["taux_operations_symetriques_pct"]) >= 95 else "orange",
                ),
                ("Total debit", _format_amount(row["total_debit"]), "Mouvements bruts", "slate"),
                ("Total credit", _format_amount(row["total_credit"]), "Mouvements bruts", "slate"),
                (
                    "Variation de solde conforme",
                    _format_percent(row["taux_variation_solde_conforme_pct"]),
                    "Amplitude bal_before / bal_after",
                    "green" if float(row["taux_variation_solde_conforme_pct"]) >= 95 else "orange",
                ),
                (
                    "Clients nommes [G2]",
                    _format_percent(row.get("taux_clients_nommes_g2_pct")),
                    "Identification secondaire",
                    "blue",
                ),
            ]
        )


def _render_accounting_balances_and_journals(
    report: dict[str, pd.DataFrame],
    *,
    date_start: object,
    date_end: object,
) -> None:
    """Restitue les balances auxiliaires et les journaux."""
    if report.get("synthese", pd.DataFrame()).empty:
        st.info("Aucune ecriture sur la periode selectionnee.")
        return

    render_summary_box(
        "Perimetre comptable observe",
        [
            "Transactions fournit toutes les ecritures, les montants et les soldes observes.",
            "La balance auxiliaire retient NORMAL SAVINGS, FIXED SAVINGS et PRINCIPLE; les comptes techniques restent dans la balance des mouvements.",
            "G2 complete le nom du client et rapproche Receipt No avec ref_no, sans remplacer les montants de la Solution Numérique.",
            "CDF et USD sont calcules et presentes separement.",
        ],
    )
    render_panel_title("Balance par client")
    st.caption(
        "Les debits et credits couvrent toutes les lignes du client. Les colonnes de position "
        "reprennent uniquement les derniers soldes observes des comptes produits actifs dans la periode."
    )
    balance_clients = report["balance_clients"]
    client_view = _apply_local_multiselect_filters(
        balance_clients,
        ["currency_code", "Nom_client", "telephone", "customer_id"],
        key_prefix="mpesa_accounting_client_balance_filter",
    )
    client_columns = [
        "customer_id", "Nom_client", "telephone", "currency_code", "nombre_operations",
        "nombre_lignes", "depots_epargne_observes", "retraits_epargne_observes",
        "mouvement_net_epargne_observe", "total_debit", "total_credit", "solde_debiteur_mouvement",
        "solde_crediteur_mouvement", "solde_epargne_courante_observe", "solde_dat_observe",
        "avoirs_epargne_observes", "encours_principal_observe", "operations_a_verifier",
        "premiere_ecriture", "derniere_ecriture",
    ]
    client_columns = [column for column in client_columns if column in client_view.columns]
    st.caption(f"{len(client_view)} ligne(s) client x devise affichee(s).")
    _mpesa_dataframe(client_view[client_columns], width="stretch", hide_index=True)

    with st.expander("Afficher la balance auxiliaire detaillee par produit", expanded=False):
        auxiliary = report["balance_auxiliaire_clients"]
        if auxiliary.empty:
            st.info("Aucun compte produit actif sur la periode.")
        else:
            auxiliary_view = _apply_local_multiselect_filters(
                auxiliary,
                ["currency_code", "famille_position", "nature_comptable_indicative", "customer_id"],
                key_prefix="mpesa_accounting_auxiliary_filter",
            )
            _mpesa_dataframe(auxiliary_view, width="stretch", hide_index=True)

    render_panel_title("Balance des mouvements par type de compte")
    st.caption(
        "Ce tableau conserve tous les sous-registres de la Solution Numérique. Les soldes debiteur et crediteur sont des "
        "soldes de mouvements de la periode, pas des soldes de cloture officiels."
    )
    account_balance = report["balance_comptes"]
    for currency in account_balance["currency_code"].astype(str).unique():
        currency_accounts = account_balance.loc[
            account_balance["currency_code"].astype(str).eq(currency)
        ].copy()
        chart_data = currency_accounts.melt(
            id_vars=["account_type"],
            value_vars=["total_debit", "total_credit"],
            var_name="sens_comptable",
            value_name="montant",
        )
        fig = px.bar(
            chart_data,
            x="account_type",
            y="montant",
            color="sens_comptable",
            barmode="group",
            color_discrete_map={"total_debit": "#1553a1", "total_credit": "#e94b5f"},
            labels={
                "account_type": "Type de compte",
                "montant": f"Montant ({currency})",
                "sens_comptable": "Mouvement",
            },
        )
        style_standard_vertical_bar(fig, height=390, tickangle=-35)
        st_plot(fig, key=f"mpesa_account_balance_{currency}", height=390)
    _mpesa_dataframe(account_balance, width="stretch", hide_index=True)

    render_panel_title("Journaux comptables observes")
    with st.expander("Afficher le journal des operations", expanded=False):
        operation_view = _apply_local_multiselect_filters(
            report.get("journal_operations", pd.DataFrame()),
            ["currency_code", "statut_controle_operation", "customer_id"],
            key_prefix="mpesa_accounting_operation_journal_filter",
        )
        _mpesa_dataframe(operation_view, width="stretch", hide_index=True)
    with st.expander("Afficher le journal brut des ecritures", expanded=False):
        _mpesa_dataframe(report.get("journal_ecritures", pd.DataFrame()), width="stretch", hide_index=True)

    render_panel_title("Export de la balance observée")
    st.caption(
        "Les documents reprennent exactement les clients et devises conservés par les filtres de "
        "Balance par client ci-dessus. Les montants proviennent uniquement de Transactions "
        "Transactions et G2 ne complète que le nom du client."
    )
    export_report = build_filtered_turbo_balance_report(report, client_view)
    start_token = pd.Timestamp(date_start).strftime("%Y%m%d")
    end_token = pd.Timestamp(date_end).strftime("%Y%m%d")
    selection_frame = client_view[
        [column for column in ["customer_id", "currency_code"] if column in client_view.columns]
    ]
    selection_token = hashlib.sha256(
        pd.util.hash_pandas_object(selection_frame, index=False).values.tobytes()
    ).hexdigest()[:10]
    st.caption(
        f"Périmètre exporté : {len(client_view)} ligne(s) client × devise, "
        f"{client_view['customer_id'].astype('string').nunique() if not client_view.empty else 0} client(s)."
    )
    with st.container(horizontal=True, gap="small"):
        st.download_button(
            "Télécharger Word",
            data=lambda: _create_turbo_balance_word_cached(
                export_report,
                date_start,
                date_end,
            ),
            file_name=f"balance_observee_turbo_{start_token}_{end_token}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            icon=":material/download:",
            on_click="ignore",
            width="content",
            disabled=client_view.empty,
            key=f"mpesa_turbo_balance_word_{start_token}_{end_token}_{selection_token}",
        )
        st.download_button(
            "Télécharger PDF",
            data=lambda: _create_turbo_balance_pdf_cached(
                export_report,
                date_start,
                date_end,
            ),
            file_name=f"balance_observee_turbo_{start_token}_{end_token}.pdf",
            mime="application/pdf",
            icon=":material/download:",
            on_click="ignore",
            width="content",
            disabled=client_view.empty,
            key=f"mpesa_turbo_balance_pdf_{start_token}_{end_token}_{selection_token}",
        )

    render_panel_title("Suivi des dépôts et retraits par client")
    st.caption(
        "Cette restitution reprend l'esprit de l'état des mouvements Vodacom : "
        "une ligne Dépôt et une ligne Retrait par client et par devise, avec une "
        "colonne par jour de la période filtrée. Le score indique le nombre "
        "d'opérations observées rapporté au nombre de jours couverts."
    )
    pivot_export_report = build_filtered_turbo_deposit_withdrawal_pivot_report(
        report,
        client_view,
    )
    deposit_withdrawal_pivot = pivot_export_report.get(
        "suivi_depots_retraits_pivot",
        pd.DataFrame(),
    )
    pivot_day_count = (
        int(
            pd.to_numeric(
                deposit_withdrawal_pivot["nombre_jours_periode"],
                errors="coerce",
            )
            .fillna(0)
            .max()
        )
        if not deposit_withdrawal_pivot.empty
        and "nombre_jours_periode" in deposit_withdrawal_pivot.columns
        else 0
    )
    st.caption(
        f"Périmètre exporté : {len(deposit_withdrawal_pivot)} ligne(s) client × opération × devise, "
        f"sur {pivot_day_count} jour(s)."
    )
    with st.expander(
        "Afficher le tableau croisé dépôts/retraits",
        expanded=False,
    ):
        hidden_columns = {
            "customer_id",
            "Nom_client",
            "telephone",
            "nombre_operations_suivi",
            "nombre_jours_periode",
            "score_pct",
        }
        pivot_columns = [
            column
            for column in deposit_withdrawal_pivot.columns
            if column not in hidden_columns
        ]
        _mpesa_dataframe(
            deposit_withdrawal_pivot[pivot_columns],
            width="stretch",
            hide_index=True,
            column_config={
                "client": st.column_config.TextColumn("Client"),
                "operation": st.column_config.TextColumn("Opération"),
                "currency_code": st.column_config.TextColumn("Devise"),
                "total": st.column_config.NumberColumn("Total"),
                "solde": st.column_config.NumberColumn("Solde"),
                "score": st.column_config.TextColumn("Score"),
            },
        )
    with st.container(horizontal=True, gap="small"):
        st.download_button(
            "Télécharger Word dépôts/retraits",
            data=lambda: _create_turbo_deposit_withdrawal_pivot_word_cached(
                pivot_export_report,
                date_start,
                date_end,
            ),
            file_name=(
                f"suivi_depots_retraits_turbo_{start_token}_{end_token}.docx"
            ),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            icon=":material/download:",
            on_click="ignore",
            width="content",
            disabled=deposit_withdrawal_pivot.empty,
            key=(
                f"mpesa_turbo_deposit_withdrawal_word_{start_token}_"
                f"{end_token}_{selection_token}"
            ),
        )
        st.download_button(
            "Télécharger Excel dépôts/retraits",
            data=lambda: _create_excel_export_current_sidebar(
                pivot_export_report,
                print_orientation="landscape",
            ),
            file_name=(
                f"suivi_depots_retraits_turbo_{start_token}_{end_token}.xlsx"
            ),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
            on_click="ignore",
            width="content",
            disabled=deposit_withdrawal_pivot.empty,
            key=(
                f"mpesa_turbo_deposit_withdrawal_excel_{start_token}_"
                f"{end_token}_{selection_token}"
            ),
        )


def _render_accounting_flows(report: dict[str, pd.DataFrame]) -> None:
    """Ajoute les flux et produits comptables au volet d'activite."""
    render_panel_title("Flux et produits financiers observes")
    flow_column, products_column = st.columns(2, gap="small")
    with flow_column:
        st.markdown("**Flux du compte MPESA ACCOUNT**")
        st.caption(
            "Dans la restitution Bisou Bisou, le debit technique du MPESA ACCOUNT devient une entree "
            "et le credit technique une sortie."
        )
        _mpesa_dataframe(report.get("flux_mpesa", pd.DataFrame()), width="stretch", hide_index=True)
    with products_column:
        st.markdown("**Produits et repartitions observes**")
        st.caption(
            "Les lignes Interets, Penalites, Part Bisou et Part Voda sont presentees separement; "
            "elles ne sont pas additionnees pour eviter de compter deux fois une meme ventilation."
        )
        _mpesa_dataframe(report.get("produits_financiers", pd.DataFrame()), width="stretch", hide_index=True)
        product_detail = report.get("produits_financiers_detail", pd.DataFrame())
        if not product_detail.empty:
            with st.expander("Afficher le detail des produits financiers", expanded=False):
                product_detail_view = _apply_local_multiselect_filters(
                    product_detail,
                    ["currency_code", "account_type"],
                    key_prefix="mpesa_turbo_financial_product_filter",
                )
                _mpesa_dataframe(
                    product_detail_view.head(2000),
                    width="stretch",
                    hide_index=True,
                )


def _render_accounting_portfolio(report: dict[str, pd.DataFrame]) -> None:
    """Ajoute les positions comptables de portefeuille au volet produits."""
    render_panel_title("Positions de portefeuille des fichiers de reference")
    portfolio = report.get("positions_portefeuille", pd.DataFrame())
    if portfolio.empty:
        st.info("Chargez Epargne courante, DAT et Credits pour comparer les positions de portefeuille.")
        return

    st.caption(
        "Ces positions proviennent des instantanes Current Savings, Fixed Savings et Loans. "
        "Elles peuvent etre posterieures a la periode du journal et ne sont donc pas forcees dans la balance journaliere."
    )
    for _, row in portfolio.iterrows():
        currency = str(row["currency_code"])
        render_kpi_cards(
            [
                ("Epargne courante", _format_amount(row["solde_epargne_courante_reference"]), currency, "blue"),
                ("DAT", _format_amount(row["solde_dat_reference"]), currency, "navy"),
                ("Depots clients", _format_amount(row["depots_clients_reference"]), currency, "green"),
                ("Encours credit", _format_amount(row["encours_credit_reference"]), currency, "orange"),
                ("Credits / depots", _format_percent(row["ratio_credits_depots_pct"]), f"Devise {currency}", "slate"),
            ]
        )
    _mpesa_dataframe(portfolio, width="stretch", hide_index=True)


def _render_accounting_controls(
    prepared: MpesaPreparedData,
    report: dict[str, pd.DataFrame],
) -> None:
    """Restitue les signaux comptables et le rapprochement secondaire G2."""
    render_panel_title("Controle secondaire Transactions M-PESA_G2")
    g2_control = report.get("controle_g2", pd.DataFrame())
    if prepared.g2_transactions.empty:
        st.info("G2 n'est pas charge. Les balances et mouvements restent disponibles sans nom ni controle G2.")
    else:
        st.caption(
            "Le taux de rapprochement compare uniquement les transactions G2 terminees de la periode "
            "avec ref_no. Un fichier G2 limite au compte 1441 ne couvre pas les sorties 15558."
        )
        _mpesa_dataframe(
            g2_control,
            width="stretch",
            hide_index=True,
        )

    render_panel_title("Controles comptables observes")
    operation_controls = report.get("controles_operations", pd.DataFrame())
    balance_controls = report.get("controles_soldes", pd.DataFrame())
    control_count = len(operation_controls) + len(balance_controls)
    render_kpi_cards(
        [
            ("Operations a verifier", _format_count(len(operation_controls)), "Symetrie debit / credit", "orange"),
            ("Variations a verifier", _format_count(len(balance_controls)), "bal_before / bal_after", "orange"),
            ("Total signaux", _format_count(control_count), "Signaux de revue, pas preuves d'erreur", "slate"),
        ]
    )
    if control_count:
        _render_alert_banner(
            f"{control_count} signal(aux) comptable(s) necessitent une verification."
        )
    with st.expander("Afficher les operations a verifier", expanded=False):
        _mpesa_dataframe(
            operation_controls,
            width="stretch",
            hide_index=True,
        )
    with st.expander("Afficher les variations de solde a verifier", expanded=False):
        _mpesa_dataframe(
            balance_controls,
            width="stretch",
            hide_index=True,
        )


def _render_accounting_export(
    report: dict[str, pd.DataFrame],
    date_start: object,
    date_end: object,
) -> None:
    """Conserve le contrat d'export comptable a douze feuilles."""
    render_panel_title("Export comptable")
    st.caption(
        "Le classeur comptable reste distinct du classeur de pilotage et conserve ses douze feuilles contractuelles."
    )

    export_report = {
        "accounting_summary": report.get("synthese", pd.DataFrame()),
        "accounting_client_balances": report.get("balance_clients", pd.DataFrame()),
        "accounting_client_positions": report.get("balance_auxiliaire_clients", pd.DataFrame()),
        "accounting_account_balance": report.get("balance_comptes", pd.DataFrame()),
        "accounting_operation_journal": report.get("journal_operations", pd.DataFrame()),
        "accounting_entry_journal": report.get("journal_ecritures", pd.DataFrame()),
        "accounting_operation_controls": report.get("controles_operations", pd.DataFrame()),
        "accounting_balance_controls": report.get("controles_soldes", pd.DataFrame()),
        "accounting_cash_flow": report.get("flux_mpesa", pd.DataFrame()),
        "accounting_financial_products": report.get("produits_financiers", pd.DataFrame()),
        "accounting_portfolio_positions": report.get("positions_portefeuille", pd.DataFrame()),
        "accounting_g2_controls": report.get("controle_g2", pd.DataFrame()),
    }
    start_token = pd.Timestamp(date_start).strftime("%Y%m%d")
    end_token = pd.Timestamp(date_end).strftime("%Y%m%d")
    if st.button(
        "Preparer l'export comptable",
        key=f"mpesa_prepare_accounting_export_{start_token}_{end_token}",
        width="content",
    ):
        with st.spinner("Preparation du classeur comptable..."):
            export_bytes = _create_excel_export_current_sidebar(export_report)
        st.download_button(
            "Telecharger les analyses comptables",
            data=export_bytes,
            file_name=f"analyses_comptables_turbo_{start_token}_{end_token}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="content",
            key=f"mpesa_accounting_export_{start_token}_{end_token}",
        )


def _render_diagnostics_content(prepared: MpesaPreparedData, report: dict[str, Any] | None) -> None:
    diagnostics = report["diagnostics"] if report is not None else build_diagnostics(prepared)
    diagnostics_view = _apply_local_multiselect_filters(
        diagnostics,
        ["statut", "controle"],
        key_prefix="mpesa_diagnostics_filter",
    )
    diagnostic_status = diagnostics_view.get(
        "statut", pd.Series("", index=diagnostics_view.index)
    ).astype("string").fillna("")
    diagnostic_alert_mask = ~diagnostic_status.str.lower().isin(
        {"", "ok", "conforme", "disponible", "information"}
    )
    diagnostic_alert_count = int(diagnostic_alert_mask.sum())
    if diagnostic_alert_count:
        _render_alert_banner(
            f"{diagnostic_alert_count} type(s) de controle de donnees necessitent une verification."
        )
    _mpesa_dataframe(
        diagnostics_view,
        width="stretch",
        hide_index=True,
    )
    if not prepared.transactions.empty:
        selected_diagnostic_controls = diagnostics_view.loc[
            diagnostic_alert_mask,
            "controle",
        ] if "controle" in diagnostics_view.columns else pd.Series(dtype="string")
        selected_diagnostic_controls = selected_diagnostic_controls.astype(
            "string"
        ).dropna().tolist()
        detailed_control_count = len(
            set(selected_diagnostic_controls).intersection(
                TRANSACTION_ANOMALY_CONTROL_NAMES
            )
        )
        anomalies = build_transaction_anomalies(
            prepared.transactions,
            selected_controls=selected_diagnostic_controls,
        )
        render_panel_title("Anomalies Transactions")
        if anomalies.empty:
            st.success(
                "Aucune anomalie Transactions ne correspond aux filtres statut et controle."
            )
        else:
            _render_alert_banner(
                f"{len(anomalies)} ligne(s) Transactions distincte(s) necessitent une verification "
                f"pour {detailed_control_count} controle(s) transactionnel(s) filtre(s)."
            )
            st.caption(
                "La banniere de synthese compte les types de controles. La valeur de chaque controle "
                "correspond aux lignes detaillees; la liste fusionne les lignes communes. "
                "Sans filtre de controle, une meme ligne peut cumuler plusieurs raisons d'anomalie."
            )
            _mpesa_dataframe(
                anomalies.head(1000),
                width="stretch",
                hide_index=True,
                column_config={
                    "raison_anomalie": st.column_config.TextColumn(
                        "Raison de l'anomalie",
                        pinned=True,
                    ),
                },
            )
            if len(anomalies) > 1000:
                st.caption(
                    "Le tableau est limite aux 1 000 premieres anomalies; "
                    f"{len(anomalies) - 1000} ligne(s) supplementaire(s) ne sont pas affichees."
                )


@st.fragment
def _render_diagnostics_tab(prepared: MpesaPreparedData, report: dict[str, Any] | None) -> None:
    _render_diagnostics_content(prepared, report)


@st.fragment
def _render_clients_tab(prepared: MpesaPreparedData) -> None:
    render_summary_box(
        "Clients 360 - Solution Numérique",
        [
            "Cet onglet mesure le référentiel client, l'activité, l'acquisition, l'activation et les opportunités commerciales.",
            "Customers sert au référentiel téléphone et à la date de création client; Transactions fournit l'activité consolidée.",
            "Les rapports G2 M-Pesa enrichissent le nom et le contrôle, mais ne créent aucun KPI financier ni aucune opération.",
        ],
    )

    date_candidates: list[pd.Series] = []
    if not prepared.transactions.empty and "created_at" in prepared.transactions.columns:
        date_candidates.append(pd.to_datetime(prepared.transactions["created_at"], errors="coerce").dropna())
    if not prepared.customers.empty and "created_at" in prepared.customers.columns:
        date_candidates.append(pd.to_datetime(prepared.customers["created_at"], errors="coerce").dropna())
    combined_dates = (
        pd.concat(date_candidates, ignore_index=True).dropna()
        if date_candidates
        else pd.Series(dtype="datetime64[ns]")
    )
    if combined_dates.empty:
        st.info("Chargez au moins Customers ou Transactions avec une date exploitable pour construire l'onglet Clients.")
        return

    minimum_date = combined_dates.min().date()
    maximum_date = combined_dates.max().date()
    default_end = maximum_date
    default_start = max(minimum_date, (pd.Timestamp(default_end) - pd.Timedelta(days=90)).date())
    with st.container(border=True):
        filter_cols = st.columns(5)
        with filter_cols[0]:
            date_start = st.date_input(
                "Date de début",
                value=default_start,
                min_value=minimum_date,
                max_value=maximum_date,
                key="mpesa_clients_date_start",
                format="DD/MM/YYYY",
                help="Borne incluse pour l'activité client, les nouveaux clients et les listes d'action.",
            )
        with filter_cols[1]:
            date_end = st.date_input(
                "Date de fin",
                value=default_end,
                min_value=minimum_date,
                max_value=maximum_date,
                key="mpesa_clients_date_end",
                format="DD/MM/YYYY",
                help="Borne incluse. Les positions de comptes et de crédits restent des instantanés disponibles à cette date.",
            )
        with filter_cols[2]:
            frequency = st.selectbox(
                "Fréquence",
                options=["Jour", "Semaine", "Mois"],
                index=2,
                key="mpesa_clients_frequency",
                help="Regroupe l'acquisition et l'activité par jour, semaine ou mois sans modifier les sources.",
            )
        with filter_cols[3]:
            inactivity_threshold = st.number_input(
                "Seuil inactivité",
                min_value=7,
                max_value=365,
                value=30,
                step=7,
                key="mpesa_clients_inactivity_threshold",
                help="Nombre de jours sans opération pour classer un client comme inactif observé. Ce n'est pas un statut réglementaire.",
            )
        with filter_cols[4]:
            occasional_threshold = st.number_input(
                "Seuil occasionnel",
                min_value=1,
                max_value=20,
                value=2,
                step=1,
                key="mpesa_clients_occasional_threshold",
                help="Nombre maximal d'opérations sur la période pour classer un client actif comme occasionnel.",
            )

    report = _build_mpesa_clients_report_cached(
        prepared,
        date_start,
        date_end,
        frequency,
        int(inactivity_threshold),
        int(occasional_threshold),
    )
    kpi = report.get("kpi", pd.DataFrame())
    client_360 = report.get("client_360", pd.DataFrame())
    acquisition = report.get("acquisition_activation", pd.DataFrame())
    segments_clients = report.get("segments_clients", pd.DataFrame())
    segments_produits = report.get("segments_produits", pd.DataFrame())
    dat_without_credit = report.get("dat_sans_credit_actif", pd.DataFrame())
    data_quality = report.get("qualite_donnees", pd.DataFrame())
    action_lists = report.get("listes_action", {})

    def kpi_value(indicator: str) -> Any:
        if kpi.empty or "indicateur" not in kpi.columns:
            return None
        rows = kpi.loc[kpi["indicateur"].eq(indicator)]
        return rows.iloc[0]["valeur"] if not rows.empty else None

    cards = [
        ("Clients référentiel", _format_count(kpi_value("clients_referentiel")), "Customers dédupliqué par téléphone", "blue"),
        ("Clients connus", _format_count(kpi_value("clients_connus_solution_numerique")), "Toutes sources Solution Numérique", "slate"),
        ("Clients actifs", _format_count(kpi_value("clients_actifs")), f"Du {pd.Timestamp(date_start):%d/%m/%Y} au {pd.Timestamp(date_end):%d/%m/%Y}", "green"),
        ("Taux actifs", _format_percent(kpi_value("taux_clients_actifs")), "Dénominateur explicite dans la table KPI", "orange"),
        ("Nouveaux clients", _format_count(kpi_value("nouveaux_clients")), "Customers.created_at dans la période", "blue"),
        ("Activation nouveaux", _format_percent(kpi_value("taux_activation_nouveaux_clients")), "Nouveaux clients actifs / nouveaux clients", "green"),
        ("Sans mouvement", _format_count(kpi_value("clients_sans_mouvement")), "Population de référence sans événement", "red"),
    ]
    render_kpi_cards(cards)

    tabs_key = "mpesa_clients_inner_tabs"
    inject_professional_tabs_css(container_key=tabs_key)
    tabs_container = st.container(key=tabs_key)
    (
        overview_tab,
        activity_tab,
        acquisition_tab,
        client_360_tab,
        dat_tab,
        segmentation_tab,
        action_tab,
    ) = tabs_container.tabs(
        format_professional_tab_labels(
            [
                "Vue d'ensemble",
                "Activité",
                "Acquisition et activation",
                "Produits et Client 360",
                "DAT sans crédit",
                "Segmentation",
                "Listes d'action",
            ]
        )
    )

    with overview_tab:
        render_panel_title("Indicateurs et qualité des données")
        _mpesa_dataframe(kpi, width="stretch", hide_index=True)
        if not data_quality.empty:
            alerts = data_quality.loc[data_quality["statut"].astype(str).eq("A verifier")]
            if alerts.empty:
                st.success("Aucun signal de qualité bloquant pour l'onglet Clients.")
            else:
                st.error(f"{len(alerts)} contrôle(s) client nécessitent une vérification.")
            _mpesa_dataframe(data_quality, width="stretch", hide_index=True)

    with activity_tab:
        render_panel_title("Activité et inactivité observées")
        activity_columns = [
            "client_key",
            "customer_id",
            "numero_telephone",
            "nom_client",
            "nombre_operations",
            "nombre_periodes_actives",
            "date_derniere_operation_observee",
            "jours_depuis_derniere_operation",
            "segment_client",
        ]
        if not client_360.empty:
            filtered = _apply_local_multiselect_filters(
                client_360,
                ["numero_telephone", "segment_client", "statut_confiance", "methode_rapprochement"],
                key_prefix="mpesa_clients_activity_filter",
            )
            _mpesa_dataframe(filtered[[column for column in activity_columns if column in filtered.columns]], width="stretch", hide_index=True)
        else:
            st.info("Aucun client à afficher.")

    with acquisition_tab:
        render_panel_title("Acquisition et activation")
        if not acquisition.empty:
            st.caption("Nouveaux clients et nouveaux clients actifs par période. Le taux d'activation reste un ratio, pas un montant.")
            st.line_chart(acquisition, x="periode", y=["nouveaux_clients", "nouveaux_clients_actifs"])
            _mpesa_dataframe(acquisition, width="stretch", hide_index=True)
        else:
            st.info("Aucune création client exploitable sur le périmètre.")

    with client_360_tab:
        render_panel_title("Produits détenus et Client 360")
        display_columns = [
            "client_key",
            "customer_id",
            "numero_telephone",
            "nom_client",
            "date_creation_client",
            "presence_epargne",
            "presence_dat",
            "presence_credit",
            "presence_transaction",
            "nombre_comptes_compte_ouvert",
            "solde_compte_ouvert",
            "comptes_solde_positif_dat",
            "solde_dat",
            "comptes_solde_positif_credit",
            "solde_credit",
            "segment_produit",
            "segment_client",
            "sources_client",
        ]
        if not client_360.empty:
            filtered = _apply_local_multiselect_filters(
                client_360,
                ["numero_telephone", "segment_produit", "segment_client", "statut_confiance"],
                key_prefix="mpesa_clients_360_filter",
            )
            _mpesa_dataframe(filtered[[column for column in display_columns if column in filtered.columns]], width="stretch", hide_index=True)
        else:
            st.info("Aucune vue Client 360 disponible.")

    with dat_tab:
        render_panel_title("Clients DAT sans crédit actif")
        st.caption(
            "Cette liste signale un potentiel commercial crédit. Elle ne constitue pas une décision d'éligibilité."
        )
        if not dat_without_credit.empty:
            filtered = _apply_local_multiselect_filters(
                dat_without_credit,
                ["numero_telephone", "msisdn1", "msisdn", "currency_code", "product_name", "status"],
                key_prefix="mpesa_clients_dat_without_credit_filter",
            )
            _mpesa_dataframe(filtered, width="stretch", hide_index=True)
        else:
            st.success("Aucun DAT positif sans crédit actif détecté avec les sources chargées.")

    with segmentation_tab:
        render_panel_title("Segmentation objective")
        left, right = st.columns(2)
        with left:
            st.markdown("**Segments comportementaux**")
            _mpesa_dataframe(segments_clients, width="stretch", hide_index=True)
        with right:
            st.markdown("**Segments produits**")
            _mpesa_dataframe(segments_produits, width="stretch", hide_index=True)

    with action_tab:
        render_panel_title("Listes d'action")
        if not isinstance(action_lists, dict) or not action_lists:
            st.info("Aucune liste d'action disponible.")
        else:
            list_names = list(action_lists.keys())
            selected_lists = st.multiselect(
                "Listes à afficher",
                options=list_names,
                default=list_names[:1],
                format_func=lambda value: str(value).replace("_", " ").title(),
                key="mpesa_clients_action_lists",
                help="Les listes sont produites depuis Client 360. Les montants restent séparés par devise lorsqu'ils existent.",
            )
            if not selected_lists:
                st.info("Sélectionnez au moins une liste d'action.")
            for selected_list in selected_lists:
                selected_frame = action_lists.get(selected_list, pd.DataFrame())
                st.markdown(f"**{str(selected_list).replace('_', ' ').title()}**")
                if isinstance(selected_frame, pd.DataFrame) and not selected_frame.empty:
                    selected_frame = _apply_local_multiselect_filters(
                        selected_frame,
                        [
                            "numero_telephone",
                            "client_key",
                            "customer_id",
                            "segment_client",
                            "segment_produit",
                            "statut_confiance",
                            "currency_code",
                        ],
                        key_prefix=f"mpesa_clients_action_filter_{selected_list}",
                    )
                _mpesa_dataframe(selected_frame, width="stretch", hide_index=True)
            export_report = {
                "clients_kpi": kpi,
                "clients_360": client_360,
                "clients_acquisition_activation": acquisition,
                "clients_segments": segments_clients,
                "clients_segments_produits": segments_produits,
                "clients_qualite_donnees": data_quality,
                **{f"clients_{key}": value for key, value in action_lists.items()},
            }
            st.download_button(
                "Télécharger les listes Clients Excel",
                data=lambda: _create_excel_export_current_sidebar(export_report),
                file_name=(
                    f"clients_solution_numerique_{pd.Timestamp(date_start):%Y%m%d}_"
                    f"{pd.Timestamp(date_end):%Y%m%d}.xlsx"
                ),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                icon=":material/download:",
                width="content",
            )


@st.fragment
def _render_statistics_tab(
    prepared: MpesaPreparedData,
    historical_prepared: MpesaPreparedData | None = None,
) -> None:
    historical_prepared = historical_prepared or prepared
    render_summary_box(
        "Statistiques Solution Numérique",
        [
            "Les statistiques financieres et commerciales sont calculees depuis les sources Solution Numérique.",
            "Les rapports G2 M-Pesa et Clients_Perfect restent facultatifs : ils enrichissent ou controlent, sans modifier les montants.",
            "Le chiffre d'affaires affiche est observe et non certifie : il reprend les produits financiers detectables, separes par devise.",
            "La tendance annuelle compare automatiquement la periode filtree aux memes dates de l'annee precedente lorsqu'elles sont disponibles; elle n'attribue pas seule une variation a un evenement externe.",
        ],
    )

    date_candidates: list[pd.Series] = []
    if not prepared.transactions.empty and "created_at" in prepared.transactions.columns:
        date_candidates.append(pd.to_datetime(prepared.transactions["created_at"], errors="coerce").dropna())
    if not prepared.customers.empty and "created_at" in prepared.customers.columns:
        date_candidates.append(pd.to_datetime(prepared.customers["created_at"], errors="coerce").dropna())
    combined_dates = (
        pd.concat(date_candidates, ignore_index=True).dropna()
        if date_candidates
        else pd.Series(dtype="datetime64[ns]")
    )
    if combined_dates.empty:
        st.info(
            "Chargez au moins Transactions ou Customers avec une date exploitable pour produire les statistiques."
        )
        source_preview = build_mpesa_statistics_report(prepared).get("priorite_sources", pd.DataFrame())
        if not source_preview.empty:
            _mpesa_dataframe(source_preview, width="stretch", hide_index=True)
        return

    minimum_date = combined_dates.min().date()
    maximum_date = combined_dates.max().date()
    default_end = maximum_date
    latest_statistical_timestamp = pd.Timestamp(combined_dates.max())
    if minimum_date < maximum_date and latest_statistical_timestamp.hour < 18:
        default_end = (
            latest_statistical_timestamp.normalize() - pd.Timedelta(days=1)
        ).date()
    default_start = max(
        minimum_date,
        (pd.Timestamp(default_end) - pd.Timedelta(days=90)).date(),
    )

    filter_scope_key = f"{minimum_date:%Y%m%d}_{maximum_date:%Y%m%d}_{len(combined_dates)}"
    start_widget_key = f"mpesa_statistics_start_widget_{filter_scope_key}"
    end_widget_key = f"mpesa_statistics_end_widget_{filter_scope_key}"
    applied_filters_key = f"mpesa_statistics_applied_filters_{filter_scope_key}"
    applied_at_key = f"mpesa_statistics_applied_at_{filter_scope_key}"
    if start_widget_key not in st.session_state:
        st.session_state[start_widget_key] = default_start
    if end_widget_key not in st.session_state:
        st.session_state[end_widget_key] = default_end
    if st.session_state[start_widget_key] < minimum_date or st.session_state[start_widget_key] > maximum_date:
        st.session_state[start_widget_key] = default_start
    if st.session_state[end_widget_key] < minimum_date or st.session_state[end_widget_key] > maximum_date:
        st.session_state[end_widget_key] = default_end
    st.session_state.setdefault("mpesa_statistics_frequency", "Mois")
    st.session_state.setdefault("mpesa_statistics_top_n_clients", 50)
    st.session_state.setdefault(
        applied_filters_key,
        {
            "date_debut": st.session_state[start_widget_key],
            "date_fin": st.session_state[end_widget_key],
            "frequence": st.session_state["mpesa_statistics_frequency"],
            "top_n_clients": st.session_state["mpesa_statistics_top_n_clients"],
        },
    )

    with st.form("mpesa_statistics_filters"):
        start_col, end_col, frequency_col, top_col = st.columns([1.0, 1.0, 1.0, 1.0])
        with start_col:
            st.date_input(
                "Date de debut",
                min_value=minimum_date,
                max_value=maximum_date,
                key=start_widget_key,
                format="DD/MM/YYYY",
                help=(
                    "Première journée incluse dans les statistiques, les "
                    "comparaisons, les graphiques, les tableaux et le rapport Word."
                ),
            )
        with end_col:
            st.date_input(
                "Date de fin",
                min_value=minimum_date,
                max_value=maximum_date,
                key=end_widget_key,
                format="DD/MM/YYYY",
                help=(
                    "Dernière journée incluse. Lorsque la journée la plus récente "
                    "semble incomplète, la dernière journée complète est proposée."
                ),
            )
        with frequency_col:
            st.selectbox(
                "Frequence",
                ["Jour", "Semaine", "Mois"],
                key="mpesa_statistics_frequency",
                help=(
                    "Regroupe les évolutions par jour, semaine ou mois sans changer "
                    "la période ni les totaux calculés."
                ),
            )
        with top_col:
            st.number_input(
                "Top clients affiches",
                min_value=5,
                max_value=200,
                step=5,
                key="mpesa_statistics_top_n_clients",
                help=(
                    "Nombre maximal de clients conservés dans les classements. "
                    "Ce réglage limite seulement les tableaux et graphiques de "
                    "classement; il ne réduit pas les KPI globaux."
                ),
            )
        statistics_submitted = st.form_submit_button("Actualiser les statistiques", type="primary")

    if statistics_submitted:
        st.session_state[applied_filters_key] = {
            "date_debut": st.session_state[start_widget_key],
            "date_fin": st.session_state[end_widget_key],
            "frequence": st.session_state["mpesa_statistics_frequency"],
            "top_n_clients": st.session_state["mpesa_statistics_top_n_clients"],
        }
        st.session_state[applied_at_key] = pd.Timestamp.now()

    applied_filters = st.session_state.get(applied_filters_key, {})
    selected_start_date = applied_filters.get("date_debut", default_start)
    selected_end_date = applied_filters.get("date_fin", default_end)
    frequency = applied_filters.get("frequence", "Mois")
    top_n_clients = int(applied_filters.get("top_n_clients", 50) or 50)
    comparison_period = _selected_mpesa_comparison_period()

    if selected_start_date > selected_end_date:
        st.error("La date de debut doit etre anterieure ou egale a la date de fin.", icon=":material/error:")
        return

    if statistics_submitted:
        st.success(
            (
                "Statistiques actualisees pour la periode "
                f"{pd.Timestamp(selected_start_date):%d/%m/%Y} - {pd.Timestamp(selected_end_date):%d/%m/%Y}, "
                f"frequence {frequency}, top {top_n_clients} clients, "
                f"comparaison {comparison_period}."
            ),
            icon=":material/check_circle:",
        )
    elif applied_at_key in st.session_state:
        st.caption(
            (
                f"Dernier perimetre applique : {pd.Timestamp(selected_start_date):%d/%m/%Y} - "
                f"{pd.Timestamp(selected_end_date):%d/%m/%Y}, frequence {frequency}, "
                f"top {top_n_clients} clients, comparaison {comparison_period}."
            )
        )
    else:
        st.caption(
            (
                f"Perimetre applique par defaut : {pd.Timestamp(selected_start_date):%d/%m/%Y} - "
                f"{pd.Timestamp(selected_end_date):%d/%m/%Y}, frequence {frequency}, "
                f"top {top_n_clients} clients, comparaison {comparison_period}."
            )
        )
    st.caption(
        "La période principale pilote tous les KPI et tableaux. Les cartes de "
        "comparaison utilisent l'horizon choisi dans la barre latérale; "
        "`Période filtrée` compare exactement Date de début - Date de fin à la "
        "période immédiatement précédente de même durée. Une seconde lecture "
        "compare automatiquement ces dates à la même période de l'année "
        "précédente. Une seule année de référence indique une tendance; elle "
        "ne suffit pas à définir une norme saisonnière ni une causalité."
    )

    with st.spinner("Construction des statistiques..."):
        report = _build_mpesa_statistics_report_cached(
            prepared,
            historical_prepared,
            selected_start_date,
            selected_end_date,
            frequency,
            comparison_period,
        )

    currency_options: set[str] = set()
    for value in report.values():
        if isinstance(value, pd.DataFrame) and not value.empty and "currency_code" in value.columns:
            currency_options.update(
                item
                for item in value["currency_code"].dropna().astype(str).unique()
                if item.strip()
            )
    currency_options_sorted = sorted(currency_options)
    selected_currencies = st.multiselect(
        "Devises affichees",
        options=currency_options_sorted,
        default=currency_options_sorted,
        key="mpesa_statistics_currencies",
        help="Une selection vide conserve toutes les devises.",
    )
    report_view = _filter_pilotage_currencies(report, selected_currencies)

    overview = report_view.get("vue_ensemble", pd.DataFrame())
    client_indicators = report_view.get("clients_indicateurs", pd.DataFrame())
    activity = report_view.get("activite_evolution", pd.DataFrame())
    growth = report_view.get("clients_croissance", pd.DataFrame())
    turnover = report_view.get("chiffre_affaires", pd.DataFrame())
    portfolio = report_view.get("epargne_dat_portefeuille", pd.DataFrame())
    credit_summary = report_view.get("credit_synthese", pd.DataFrame())
    top_clients = report_view.get("clients_volume_top", pd.DataFrame())
    source_priority = report_view.get("priorite_sources", pd.DataFrame())
    weekly_comparison = report_view.get("comparaison_hebdomadaire", pd.DataFrame())
    annual_comparison = report_view.get(
        "comparaison_annee_precedente",
        pd.DataFrame(),
    )
    g2_coverage = report_view.get("g2_couverture", pd.DataFrame())
    g2_quality = report_view.get("g2_qualite_rapprochement", pd.DataFrame())
    g2_statuses = report_view.get("g2_statuts", pd.DataFrame())
    g2_unmatched = report_view.get("g2_non_rapprochees", pd.DataFrame())
    g2_weekly = report_view.get("g2_comparaison_hebdomadaire", pd.DataFrame())

    def _sum_column(frame: pd.DataFrame, column: str) -> float:
        if frame.empty or column not in frame.columns:
            return 0.0
        return float(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum())

    def _scalar_number(value: Any) -> float:
        numeric_value = pd.to_numeric(value, errors="coerce")
        if pd.isna(numeric_value):
            return 0.0
        return float(numeric_value)

    def _safe_rate(numerator: float, denominator: float) -> str:
        if not denominator or pd.isna(denominator):
            return "-"
        return f"{100 * numerator / denominator:.2f}%"

    if not source_priority.empty:
        render_panel_title("Sources et importance")
        _mpesa_dataframe(
            source_priority,
            width="stretch",
            hide_index=True,
            column_config={
                "rang_importance": st.column_config.NumberColumn("Priorite", format="%d"),
                "source": st.column_config.TextColumn("Fichier", pinned=True),
                "niveau_importance": st.column_config.TextColumn("Importance"),
                "disponible": st.column_config.CheckboxColumn("Charge"),
                "nombre_lignes": st.column_config.NumberColumn("Lignes", format="%d"),
                "role_statistique": st.column_config.TextColumn("Role statistique"),
            },
        )

    with st.expander("1. Clients", expanded=True):
        st.caption(
            "Ce bloc mesure la base client : clients connus, clients actifs et evolution des creations."
        )
        _render_weekly_comparison(
            weekly_comparison,
            blocks=["Clients"],
            selected_currencies=selected_currencies,
            title="Comparaison des clients",
        )
        _render_weekly_comparison(
            annual_comparison,
            blocks=["Clients"],
            selected_currencies=selected_currencies,
            title="Tendance annuelle des clients",
        )
        _render_year_over_year_charts(
            annual_comparison,
            block="Clients",
            selected_currencies=selected_currencies,
        )
        first_row = overview.iloc[0] if not overview.empty else pd.Series(dtype=object)
        def _client_indicator_value(label: str, fallback: Any) -> float:
            if (
                isinstance(client_indicators, pd.DataFrame)
                and not client_indicators.empty
                and {"indicateur", "valeur"}.issubset(client_indicators.columns)
            ):
                matches = client_indicators.loc[
                    client_indicators["indicateur"].astype(str).eq(label)
                ]
                if not matches.empty:
                    return _scalar_number(matches.iloc[0].get("valeur", 0))
            return _scalar_number(fallback)

        loaded_clients = _client_indicator_value(
            "Clients du fichier Customers charge",
            first_row.get("clients_turbo_charges", 0),
        )
        known_clients = _client_indicator_value(
            "Clients connus a la date de fin",
            first_row.get("clients_turbo_connus", 0),
        )
        active_clients = _client_indicator_value(
            "Clients actifs sur la periode",
            first_row.get("clients_turbo_actifs", 0),
        )
        render_kpi_cards(
            [
                (
                    "Clients du fichier Customers",
                    _format_count(loaded_clients),
                    "Clients distincts dans Customers avant filtre de date",
                    "navy",
                ),
                (
                    "Clients connus a la date de fin",
                    _format_count(known_clients),
                    "Clients crees avant ou a la date de fin du rapport",
                    "blue",
                ),
                (
                    "Clients actifs",
                    _format_count(active_clients),
                    "Au moins une operation sur la periode",
                    "green",
                ),
                (
                    "Taux d'activite",
                    _safe_rate(active_clients, known_clients),
                    "Clients actifs / clients connus",
                    "red",
                ),
            ]
        )
        if not activity.empty and {"periode_analyse", "currency_code", "nombre_clients"}.issubset(activity.columns):
            clients_chart = px.line(
                activity,
                x="periode_analyse",
                y="nombre_clients",
                color="currency_code",
                markers=True,
                labels={
                    "periode_analyse": "Periode",
                    "nombre_clients": "Clients actifs",
                    "currency_code": "Devise",
                },
            )
            style_standard_line(clients_chart, height=410, tickangle=-20)
            st.markdown("**Clients actifs par periode**")
            st.caption("Clients avec au moins une operation sur la periode filtree.")
            st_plot(
                clients_chart,
                key="mpesa_statistics_active_clients_trend",
                height=410,
            )
        if not growth.empty:
            growth_chart = px.line(
                growth,
                x="periode",
                y="clients_turbo_cumules",
                markers=True,
                labels={"periode": "Periode", "clients_turbo_cumules": "Clients cumules"},
            )
            style_standard_line(growth_chart, height=390, tickangle=-20)
            st.markdown("**Evolution du nombre de clients**")
            st.caption(
                "Base Customers lorsqu'elle est disponible, sinon premiere observation dans les sources de la Solution Numérique."
            )
            st_plot(
                growth_chart,
                key="mpesa_statistics_customer_growth",
                height=390,
            )
            with st.expander("Afficher la table de croissance clients", expanded=False):
                _mpesa_dataframe(growth, width="stretch", hide_index=True)

    with st.expander("2. Comptes ouverts et comptes bloques", expanded=False):
        st.caption(
            "Ce bloc suit les positions d'epargne : comptes ouverts, DAT/comptes bloques, soldes et clients concernes."
        )
        _render_weekly_comparison(
            weekly_comparison,
            blocks=["Comptes"],
            selected_currencies=selected_currencies,
            title="Comparaison des comptes",
        )
        _render_weekly_comparison(
            annual_comparison,
            blocks=["Comptes"],
            selected_currencies=selected_currencies,
            title="Tendance annuelle des comptes",
        )
        _render_year_over_year_charts(
            annual_comparison,
            block="Comptes",
            selected_currencies=selected_currencies,
        )
        if portfolio.empty:
            st.info("Savings Account est requis pour analyser les comptes ouverts et bloques.")
        else:
            family = portfolio.get("famille", pd.Series("", index=portfolio.index)).astype(str)
            open_accounts = portfolio.loc[family.eq("Compte ouvert")]
            fixed_accounts = portfolio.loc[family.eq("DAT")]
            account_cards: list[tuple[str, str, str, str]] = [
                (
                    "Comptes ouverts",
                    _format_count(_sum_column(open_accounts, "nombre_comptes")),
                    "Nombre global de comptes NORMAL SAVINGS",
                    "blue",
                ),
                (
                    "Comptes bloques / DAT",
                    _format_count(_sum_column(fixed_accounts, "nombre_comptes")),
                    "Nombre global de comptes FIXED SAVINGS",
                    "navy",
                ),
            ]
            if "currency_code" in portfolio.columns:
                for currency in sorted(portfolio["currency_code"].dropna().astype(str).unique()):
                    currency_portfolio = portfolio.loc[portfolio["currency_code"].astype(str).eq(currency)]
                    currency_family = currency_portfolio.get("famille", pd.Series("", index=currency_portfolio.index)).astype(str)
                    currency_open = currency_portfolio.loc[currency_family.eq("Compte ouvert")]
                    currency_fixed = currency_portfolio.loc[currency_family.eq("DAT")]
                    account_cards.extend(
                        [
                            (
                                f"Solde comptes ouverts [{currency}]",
                                _format_amount(_sum_column(currency_open, "solde_total")),
                                "NORMAL SAVINGS, sans total multidevise",
                                "green",
                            ),
                            (
                                f"Solde comptes bloques [{currency}]",
                                _format_amount(_sum_column(currency_fixed, "solde_total")),
                                "FIXED SAVINGS / DAT, sans total multidevise",
                                "orange",
                            ),
                        ]
                    )
            render_kpi_cards(account_cards)
            _mpesa_dataframe(
                portfolio,
                width="stretch",
                hide_index=True,
                column_config={
                    "currency_code": st.column_config.TextColumn("Devise", pinned=True),
                    "solde_total": st.column_config.NumberColumn("Solde total", format="%.2f"),
                },
            )

    with st.expander("3. Credits", expanded=False):
        st.caption(
            "Ce bloc suit le portefeuille credit : credits accordes, encours, remboursements et risque observe."
        )
        _render_weekly_comparison(
            weekly_comparison,
            blocks=["Credits"],
            selected_currencies=selected_currencies,
            title="Comparaison des crédits",
        )
        _render_weekly_comparison(
            annual_comparison,
            blocks=["Credits"],
            selected_currencies=selected_currencies,
            title="Tendance annuelle des crédits",
        )
        _render_year_over_year_charts(
            annual_comparison,
            block="Credits",
            selected_currencies=selected_currencies,
        )
        if credit_summary.empty:
            st.info("Loans Account est requis pour analyser les credits.")
        else:
            credit_cards: list[tuple[str, str, str, str]] = [
                (
                    "Credits",
                    _format_count(_sum_column(credit_summary, "nombre_credits")),
                    "Nombre global de credits",
                    "navy",
                )
            ]
            if "currency_code" in credit_summary.columns:
                for _, row in credit_summary.sort_values("currency_code").iterrows():
                    currency = str(row.get("currency_code", "")).strip() or "Devise"
                    encours_total = _scalar_number(row.get("encours_total", 0))
                    encours_retard_30j = _scalar_number(row.get("encours_retard_30j", 0))
                    credit_cards.extend(
                        [
                            (
                                f"Montant accorde [{currency}]",
                                _format_amount(row.get("montant_credits", 0)),
                                "Somme loan_amount, sans total multidevise",
                                "blue",
                            ),
                            (
                                f"Encours credit [{currency}]",
                                _format_amount(encours_total),
                                "Position Loans Account",
                                "orange",
                            ),
                            (
                                f"PAR 30j [{currency}]",
                                _safe_rate(encours_retard_30j, encours_total),
                                "Encours en retard 30j / encours de la devise",
                                "red",
                            ),
                        ]
                    )
            render_kpi_cards(credit_cards)
            _mpesa_dataframe(
                credit_summary,
                width="stretch",
                hide_index=True,
                column_config={
                    "currency_code": st.column_config.TextColumn("Devise", pinned=True),
                },
            )

    with st.expander("4. Transactions", expanded=False):
        st.caption(
            "Ce bloc analyse l'activite transactionnelle : volume, chiffre d'affaires observe, operations et concentration client."
        )
        _render_weekly_comparison(
            weekly_comparison,
            blocks=["Transactions"],
            selected_currencies=selected_currencies,
            title="Comparaison des transactions",
        )
        _render_weekly_comparison(
            annual_comparison,
            blocks=["Transactions"],
            selected_currencies=selected_currencies,
            title="Tendance annuelle des transactions",
        )
        _render_year_over_year_charts(
            annual_comparison,
            block="Transactions",
            selected_currencies=selected_currencies,
        )
        total_operations = _sum_column(overview, "operations")
        transaction_cards: list[tuple[str, str, str, str]] = [
            (
                "Operations",
                _format_count(total_operations),
                "Evenements consolides sur la periode",
                "green",
            )
        ]
        if not overview.empty:
            for _, row in overview.iterrows():
                currency = str(row.get("currency_code", "")).strip() or "Devise"
                transaction_cards.append(
                    (
                        f"Volume total [{currency}]",
                        _format_amount(row.get("volume_total_transactions", 0)),
                        "Entrees + sorties observees",
                        "orange",
                    )
                )
                transaction_cards.append(
                    (
                        f"CA observe [{currency}]",
                        _format_amount(row.get("chiffre_affaires_observe", 0)),
                        "Interets + penalites + part Bisou",
                        "green",
                    )
                )
        render_kpi_cards(transaction_cards)
        if not activity.empty and {"periode_analyse", "currency_code", "volume_total_transactions"}.issubset(activity.columns):
            chart = px.line(
                activity,
                x="periode_analyse",
                y="volume_total_transactions",
                color="currency_code",
                markers=True,
                labels={
                    "periode_analyse": "Periode",
                    "volume_total_transactions": "Volume total",
                    "currency_code": "Devise",
                },
            )
            style_standard_line(chart, height=430, tickangle=-20)
            st.markdown("**Volume total des transactions par periode**")
            st.caption("Entrees + sorties observees dans Transactions, separees par devise.")
            st_plot(
                chart,
                key="mpesa_statistics_activity_trend",
                height=430,
            )
        if not turnover.empty:
            st.markdown("**Chiffre d'affaires observe et volume**")
            st.caption(
                "Le chiffre d'affaires observe est indicatif : interets + penalites + part Bisou detectes dans Transactions."
            )
            _mpesa_dataframe(
                turnover,
                width="stretch",
                hide_index=True,
                column_config={
                    "currency_code": st.column_config.TextColumn("Devise", pinned=True),
                    "volume_total_transactions": st.column_config.NumberColumn("Volume total", format="%.2f"),
                    "chiffre_affaires_observe": st.column_config.NumberColumn("CA observe", format="%.2f"),
                },
            )
        if not top_clients.empty:
            st.markdown("**Top clients par volume de transactions**")
            top_view = top_clients.sort_values(["currency_code", "rang_volume"]).head(
                int(top_n_clients)
            )
            _mpesa_dataframe(
                top_view,
                width="stretch",
                hide_index=True,
                column_config={
                    "currency_code": st.column_config.TextColumn("Devise", pinned=True),
                    "volume_total": st.column_config.NumberColumn("Volume total", format="%.2f"),
                },
            )

        with st.container(border=True):
            render_panel_title("Qualité du rapprochement G2")
            coverage_label = (
                str(g2_coverage.iloc[0].get("couverture_g2", "G2 absent"))
                if isinstance(g2_coverage, pd.DataFrame) and not g2_coverage.empty
                else "G2 absent"
            )
            st.caption(
                f"Couverture : {coverage_label}. "
                "G2 enrichit l'identité du client et contrôle les écritures; "
                "les montants et les KPI financiers restent calculés exclusivement depuis la Solution Numérique."
            )
            if not isinstance(g2_quality, pd.DataFrame) or g2_quality.empty:
                st.info(
                    "Chargez les relevés G2 1441 et 15558 pour mesurer la qualité "
                    "du rapprochement des entrées et des sorties."
                )
            else:
                comparable_categories = [
                    "Entrées et remboursements [1441]",
                    "Sorties B2C [15558]",
                ]
                comparable = g2_quality.loc[
                    g2_quality["categorie"].astype(str).isin(comparable_categories)
                ]
                completed_count = _sum_column(comparable, "operations_terminees")
                matched_count = _sum_column(comparable, "operations_rapprochees")
                entry_quality = comparable.loc[
                    comparable["categorie"].astype(str).eq(
                        "Entrées et remboursements [1441]"
                    )
                ]
                output_quality = comparable.loc[
                    comparable["categorie"].astype(str).eq(
                        "Sorties B2C [15558]"
                    )
                ]
                entry_completed = _sum_column(entry_quality, "operations_terminees")
                entry_matched = _sum_column(entry_quality, "operations_rapprochees")
                output_completed = _sum_column(output_quality, "operations_terminees")
                output_matched = _sum_column(output_quality, "operations_rapprochees")
                loan_requests = _sum_column(
                    g2_quality.loc[
                        g2_quality["categorie"].astype(str).eq(
                            "Versements de prêts [15558]"
                        )
                    ],
                    "operations_terminees",
                )
                render_kpi_cards(
                    [
                        (
                            "Opérations G2 terminées",
                            _format_count(completed_count),
                            "Entrées/remboursements 1441 et sorties B2C 15558 comparables",
                            "navy",
                        ),
                        (
                            "Taux de rapprochement global",
                            _safe_rate(matched_count, completed_count),
                            "Opérations comparables retrouvées dans la Solution Numérique",
                            "green",
                        ),
                        (
                            "Rapprochement des entrées",
                            _safe_rate(entry_matched, entry_completed),
                            "Receipt No. G2 = ref_no",
                            "blue",
                        ),
                        (
                            "Rapprochement des sorties B2C",
                            _safe_rate(output_matched, output_completed),
                            "Téléphone + devise + montant + heure",
                            "orange",
                        ),
                        (
                            "Versements de prêts G2",
                            _format_count(loan_requests),
                            "Contrôle séparé : brut, intérêt observé et net G2",
                            "navy",
                        ),
                    ]
                )
                _render_weekly_comparison(
                    g2_weekly,
                    blocks=["Qualité G2"],
                    selected_currencies=selected_currencies,
                    title="Évolution comparative de la qualité G2",
                )
                st.markdown("**Qualité par circuit et par devise**")
                _mpesa_dataframe(
                    g2_quality,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "categorie": st.column_config.TextColumn(
                            "Circuit G2",
                            pinned=True,
                        ),
                        "currency_code": st.column_config.TextColumn("Devise"),
                        "operations_g2": st.column_config.NumberColumn(
                            "Opérations",
                            format="%d",
                        ),
                        "operations_terminees": st.column_config.NumberColumn(
                            "Terminées",
                            format="%d",
                        ),
                        "operations_rapprochees": st.column_config.NumberColumn(
                            "Rapprochées",
                            format="%d",
                        ),
                        "operations_non_rapprochees": st.column_config.NumberColumn(
                            "Non rapprochées",
                            format="%d",
                        ),
                        "taux_rapprochement_pct": st.column_config.NumberColumn(
                            "Taux de rapprochement",
                            format="%.2f%%",
                        ),
                        "controle_attendu": st.column_config.TextColumn(
                            "Contrôle attendu"
                        ),
                    },
                )
                if isinstance(g2_statuses, pd.DataFrame) and not g2_statuses.empty:
                    st.markdown("**Statuts G2 par devise**")
                    _mpesa_dataframe(
                        g2_statuses,
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "currency_code": st.column_config.TextColumn(
                                "Devise",
                                pinned=True,
                            ),
                            "statut_g2": st.column_config.TextColumn("Statut G2"),
                            "nombre_operations": st.column_config.NumberColumn(
                                "Opérations",
                                format="%d",
                            ),
                            "part_pct": st.column_config.NumberColumn(
                                "Part",
                                format="%.2f%%",
                            ),
                        },
                    )
                if isinstance(g2_unmatched, pd.DataFrame) and not g2_unmatched.empty:
                    _render_alert_banner(
                        f"{len(g2_unmatched)} opération(s) G2 terminée(s) et "
                        "comparable(s) reste(nt) à rapprocher avec la Solution Numérique."
                    )
                    _mpesa_dataframe(
                        g2_unmatched.head(500),
                        width="stretch",
                        hide_index=True,
                        column_config={
                            "date": st.column_config.DatetimeColumn(
                                "Date G2",
                                format="DD/MM/YYYY HH:mm:ss",
                            ),
                            "receipt_no": st.column_config.TextColumn(
                                "Receipt No.",
                                pinned=True,
                            ),
                            "categorie": st.column_config.TextColumn("Circuit"),
                            "currency_code": st.column_config.TextColumn("Devise"),
                            "opposite_party": st.column_config.TextColumn(
                                "Contrepartie"
                            ),
                            "montant": st.column_config.NumberColumn(
                                "Montant G2 de contrôle",
                                format="%.2f",
                            ),
                            "statut_rapprochement": st.column_config.TextColumn(
                                "Statut"
                            ),
                            "methode_rapprochement_turbo": st.column_config.TextColumn(
                                "Méthode"
                            ),
                            "fichier_source_g2": st.column_config.TextColumn(
                                "Fichier G2"
                            ),
                        },
                    )
                else:
                    st.success(
                        "Aucune opération G2 terminée et comparable ne reste "
                        "non rapprochée dans le périmètre filtré.",
                        icon=":material/check_circle:",
                    )

    render_panel_title("Export")
    start_token = pd.Timestamp(selected_start_date).strftime("%Y%m%d")
    end_token = pd.Timestamp(selected_end_date).strftime("%Y%m%d")
    try:
        word_bytes = create_mpesa_statistics_word(report_view)
        st.download_button(
            "Telecharger le rapport statistiques Word",
            data=word_bytes,
            file_name=f"rapport_statistiques_solution_turbo_{start_token}_{end_token}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="content",
            key=f"mpesa_statistics_word_{start_token}_{end_token}",
        )
    except RuntimeError as exc:
        st.warning(str(exc))


def _forecast_period_label(frequency: str) -> str:
    return {
        "Jour": "D",
        "Semaine": "W-SUN",
        "Mois": "MS",
    }.get(frequency, "D")


def _aggregate_forecast_chart(
    history: pd.DataFrame,
    forecast: pd.DataFrame,
    *,
    frequency: str,
    indicator_key: str,
    currency: str,
    reference_date: pd.Timestamp,
    horizon_days: int,
) -> pd.DataFrame:
    history_view = history.loc[
        history["indicator_key"].eq(indicator_key)
        & history["currency_code"].astype(str).eq(currency)
    ].copy()
    forecast_view = forecast.loc[
        forecast["indicator_key"].eq(indicator_key)
        & forecast["currency_code"].astype(str).eq(currency)
    ].copy()
    if history_view.empty and forecast_view.empty:
        return pd.DataFrame()
    history_view["date"] = pd.to_datetime(history_view["date"], errors="coerce")
    forecast_view["date"] = pd.to_datetime(forecast_view["date"], errors="coerce")
    history_start = reference_date - pd.Timedelta(days=max(90, horizon_days * 2))
    history_view = history_view.loc[history_view["date"].ge(history_start)]
    aggregation = "mean" if indicator_key == "clients_actifs" else "sum"
    frequency_code = _forecast_period_label(frequency)

    def aggregate(
        frame: pd.DataFrame,
        value_columns: list[str],
        series_label: str,
    ) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame()
        indexed = frame.set_index("date")[value_columns].sort_index()
        grouped = (
            indexed.resample(frequency_code).mean()
            if aggregation == "mean"
            else indexed.resample(frequency_code).sum()
        )
        grouped = grouped.reset_index()
        grouped["serie"] = series_label
        return grouped

    actual = aggregate(history_view, ["valeur"], "Historique").rename(
        columns={"valeur": "valeur_graphique"}
    )
    predicted = aggregate(
        forecast_view,
        ["prevision", "borne_basse", "borne_haute"],
        "Prévision",
    ).rename(columns={"prevision": "valeur_graphique"})
    return pd.concat([actual, predicted], ignore_index=True, sort=False)


@st.fragment
def _render_forecast_tab(prepared: MpesaPreparedData) -> None:
    render_summary_box(
        "Projections Solution Numérique",
        [
            "Ce module estime l'activité à court terme à partir des historiques Solution Numérique uniquement.",
            "Les montants CDF et USD restent toujours séparés. G2 n'intervient dans aucun calcul de prévision.",
            "Les échéances DAT proviennent des dates contractuelles : il s'agit d'un calendrier certain sous réserve de la qualité des données, pas d'une prédiction.",
        ],
    )
    transaction_dates = (
        pd.to_datetime(prepared.transactions["created_at"], errors="coerce").dropna()
        if not prepared.transactions.empty and "created_at" in prepared.transactions.columns
        else pd.Series(dtype="datetime64[ns]")
    )
    if transaction_dates.empty:
        st.info(
            "Chargez Transactions [Solution Numérique] pour calculer les projections d'activité. "
            "Savings Account et Loans Account complètent ensuite les comptes, les crédits et les échéances DAT."
        )
        return

    minimum_date = transaction_dates.min().date()
    maximum_timestamp = pd.Timestamp(transaction_dates.max())
    maximum_date = maximum_timestamp.normalize().date()
    default_reference = maximum_date
    if minimum_date < maximum_date and maximum_timestamp.hour < 18:
        default_reference = (
            maximum_timestamp.normalize() - pd.Timedelta(days=1)
        ).date()
    scope_key = f"{minimum_date:%Y%m%d}_{maximum_date:%Y%m%d}_{len(transaction_dates)}"
    reference_key = f"mpesa_forecast_reference_{scope_key}"
    applied_key = f"mpesa_forecast_applied_{scope_key}"
    st.session_state.setdefault(reference_key, default_reference)
    st.session_state.setdefault("mpesa_forecast_horizon", 30)
    st.session_state.setdefault("mpesa_forecast_frequency", "Semaine")
    st.session_state.setdefault("mpesa_forecast_confidence", 80)
    st.session_state.setdefault("mpesa_forecast_dat_rate", DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT)
    st.session_state.setdefault(
        applied_key,
        {
            "reference_date": st.session_state[reference_key],
            "horizon_days": st.session_state["mpesa_forecast_horizon"],
            "frequency": st.session_state["mpesa_forecast_frequency"],
            "confidence_level": st.session_state["mpesa_forecast_confidence"],
            "annual_interest_rate_pct": st.session_state["mpesa_forecast_dat_rate"],
        },
    )

    with st.form(f"mpesa_forecast_filters_{scope_key}", border=True):
        reference_col, horizon_col, frequency_col, confidence_col, rate_col = st.columns(
            [1.25, 1.0, 1.0, 1.0, 1.0]
        )
        with reference_col:
            st.date_input(
                "Date de référence",
                min_value=minimum_date,
                max_value=maximum_date,
                key=reference_key,
                format="DD/MM/YYYY",
                help="La prévision commence le lendemain de cette date.",
            )
        with horizon_col:
            st.selectbox(
                "Horizon",
                list(MPESA_FORECAST_HORIZON_OPTIONS),
                format_func=lambda value: f"{value} jours",
                key="mpesa_forecast_horizon",
                help=(
                    "L'horizon indique le nombre de jours à prévoir après la "
                    "date de référence. Par exemple, un horizon de 30 jours "
                    "produit des estimations pour les 30 jours suivants. Une "
                    "prévision courte est généralement plus fiable; plus "
                    "l'horizon s'allonge, plus l'incertitude augmente."
                ),
            )
        with frequency_col:
            st.selectbox(
                "Affichage",
                ["Jour", "Semaine", "Mois"],
                key="mpesa_forecast_frequency",
                help=(
                    "L'affichage détermine uniquement le regroupement des "
                    "résultats dans le graphique : une valeur par jour, par "
                    "semaine ou par mois. Il ne change ni la date de référence, "
                    "ni l'horizon, ni le modèle de prévision. Les nombres sont "
                    "additionnés sur la période; les clients actifs sont "
                    "présentés en moyenne."
                ),
            )
        with confidence_col:
            st.selectbox(
                "Intervalle",
                list(MPESA_FORECAST_CONFIDENCE_OPTIONS),
                format_func=lambda value: f"{value} %",
                key="mpesa_forecast_confidence",
                help=(
                    "L'intervalle de prévision représente la zone d'incertitude "
                    "autour de la valeur prévue. À 80 %, le modèle propose une "
                    "fourchette plus resserrée : dans des conditions historiques "
                    "comparables, environ 8 valeurs réelles sur 10 devraient se "
                    "situer entre la borne basse et la borne haute. À 95 %, la "
                    "fourchette est plus large et plus prudente. Cet intervalle "
                    "n'est pas une garantie, surtout lorsque l'activité change "
                    "brutalement ou que l'historique est insuffisant."
                ),
            )
        with rate_col:
            st.number_input(
                "Taux annuel DAT (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.25,
                key="mpesa_forecast_dat_rate",
                help=(
                    "Taux annuel utilisé pour estimer l'intérêt simple des DAT "
                    "arrivant à échéance. Il est fixé à 11 % par défaut. Ce taux "
                    "alimente uniquement l'échéancier DAT et ne modifie pas le "
                    "modèle de prévision ni les écritures de la Solution Numérique."
                ),
            )
        submitted = st.form_submit_button(
            "Actualiser les prévisions",
            type="primary",
            icon=":material/refresh:",
        )
    if submitted:
        st.session_state[applied_key] = {
            "reference_date": st.session_state[reference_key],
            "horizon_days": st.session_state["mpesa_forecast_horizon"],
            "frequency": st.session_state["mpesa_forecast_frequency"],
            "confidence_level": st.session_state["mpesa_forecast_confidence"],
            "annual_interest_rate_pct": st.session_state["mpesa_forecast_dat_rate"],
        }

    filters = st.session_state[applied_key]
    reference_date = pd.Timestamp(filters["reference_date"]).normalize()
    horizon_days = int(filters["horizon_days"])
    frequency = str(filters["frequency"])
    confidence_level = int(filters["confidence_level"])
    annual_interest_rate_pct = float(filters["annual_interest_rate_pct"])
    if submitted:
        st.success(
            f"Prévisions actualisées du {(reference_date + pd.Timedelta(days=1)):%d/%m/%Y} "
            f"au {(reference_date + pd.Timedelta(days=horizon_days)):%d/%m/%Y}.",
            icon=":material/check_circle:",
        )
    else:
        st.caption(
            f"Périmètre appliqué : référence au {reference_date:%d/%m/%Y}, "
            f"horizon {horizon_days} jours, intervalle {confidence_level} %."
        )

    with st.expander("Mini-cours : comprendre la prévision", expanded=False):
        st.markdown(
            """
**Le machine learning**, ou apprentissage automatique, consiste ici à laisser
l'ordinateur repérer des habitudes dans les données passées. Le modèle observe
notamment le niveau des 28 derniers jours et compare les mêmes jours de la
semaine. Par exemple, il peut apprendre qu'un lundi est habituellement plus
actif qu'un dimanche.

**Une prévision n'est pas une certitude.** La ligne centrale représente le
scénario le plus probable selon l'historique. Les bornes basse et haute
forment un intervalle d'incertitude : plus il est large, plus la prudence est
nécessaire.

**Le test rétrospectif** cache volontairement les derniers jours connus, les
prévoit, puis compare les prévisions aux valeurs réellement observées.

**MAE — Mean Absolute Error**, traduit par **erreur absolue moyenne**, indique
l'écart moyen entre une prévision et la valeur réellement observée. Elle
s'exprime dans la même unité que l'indicateur. Une MAE de 5 signifie donc un
écart moyen de 5 clients, 5 opérations ou 5 unités monétaires selon la série.

**WAPE — Weighted Absolute Percentage Error**, traduit par **erreur absolue
pondérée en pourcentage**, rapporte la somme des écarts absolus à la somme des
valeurs réellement observées. Un WAPE de 20 % signifie que l'erreur cumulée
représente environ 20 % du volume réellement observé. Plus le WAPE est proche
de 0 %, plus la prévision a été précise. Il devient non calculable lorsque le
volume réellement observé est nul.

**L'échéancier DAT n'est pas du machine learning.** Il applique simplement les
dates d'échéance et le taux annuel aux comptes bloqués disponibles.
            """
        )
        st.info(
            "Une tendance aide à préparer une décision; elle ne remplace ni le jugement du gestionnaire, "
            "ni la validation comptable, ni l'analyse d'un événement exceptionnel."
        )

    with st.spinner("Calcul des prévisions et du test rétrospectif..."):
        report = _build_mpesa_forecast_report_cached(
            prepared,
            reference_date,
            horizon_days,
            confidence_level,
            annual_interest_rate_pct,
        )
    history = report.get("historique", pd.DataFrame())
    forecast = report.get("previsions", pd.DataFrame())
    summary = report.get("synthese", pd.DataFrame())
    dat_schedule = report.get("dat_echeancier", pd.DataFrame())
    coverage = report.get("couverture", pd.DataFrame())
    non_calculable = report.get("non_calculable", pd.DataFrame())

    if not coverage.empty:
        alerts = coverage.loc[
            coverage["alerte_couverture"].astype(str).str.strip().ne("")
        ]
        for message in alerts["alerte_couverture"].astype(str).unique():
            st.warning(message, icon=":material/info:")
    if summary.empty:
        st.warning(
            "L'historique disponible est insuffisant pour produire une prévision testable. "
            "Il faut au minimum 28 jours calendaires et plusieurs jours d'activité."
        )
        if not non_calculable.empty:
            _mpesa_dataframe(non_calculable, hide_index=True, width="stretch")
        return

    currency_options = sorted(
        value
        for value in summary["currency_code"].dropna().astype(str).unique()
        if value.strip()
    )
    selected_currencies = st.pills(
        "Devises affichées",
        options=currency_options,
        default=currency_options,
        selection_mode="multi",
        key=f"mpesa_forecast_currencies_{scope_key}",
        help="Les indicateurs monétaires ne sont jamais additionnés entre devises.",
    )
    selected_currency_set = set(selected_currencies or currency_options)
    summary_view = summary.loc[
        summary["currency_code"].astype(str).isin(selected_currency_set)
        | summary["currency_code"].astype(str).eq("")
    ].copy()

    block_order = [
        "Clients et comptes",
        "Crédits et remboursements",
        "Transactions et activité",
    ]
    for block_index, block in enumerate(block_order, start=1):
        block_summary = summary_view.loc[summary_view["bloc"].eq(block)].copy()
        if block_summary.empty:
            continue
        with st.expander(f"{block_index}. {block}", expanded=block_index == 1):
            cards: list[tuple[str, str, str, str]] = []
            for _, row in block_summary.iterrows():
                currency = str(row.get("currency_code", "")).strip()
                unit = str(row.get("unite", ""))
                predicted_value = float(row.get("valeur_prevue_horizon", 0.0))
                value_text = (
                    _format_amount(predicted_value)
                    if unit == "montant"
                    else f"{predicted_value:,.1f}".replace(",", " ")
                )
                label = str(row.get("indicateur", "Indicateur"))
                if currency:
                    label += f" [{currency}]"
                evolution = row.get("evolution_prevue_pct", pd.NA)
                evolution_text = (
                    f"{float(evolution):+.1f} % vs {horizon_days} jours précédents"
                    if pd.notna(evolution)
                    else "Comparaison précédente non calculable"
                )
                cards.append(
                    (
                        label,
                        value_text,
                        f"{evolution_text} · qualité {row.get('qualite_modele', 'Prudence')}",
                        "blue" if unit == "nombre" else "navy",
                    )
                )
            render_kpi_cards(cards)

            chart_options = {
                (
                    str(row["indicator_key"]),
                    str(row["indicateur"]),
                    str(row["currency_code"]),
                )
                for _, row in block_summary.iterrows()
            }
            selected_chart = st.selectbox(
                "Indicateur du graphique",
                options=sorted(chart_options, key=lambda item: (item[1], item[2])),
                format_func=lambda item: f"{item[1]} [{item[2]}]" if item[2] else item[1],
                key=f"mpesa_forecast_chart_{scope_key}_{block_index}",
                help=(
                    "Choisissez la série à visualiser dans ce bloc. Ce contrôle "
                    "change uniquement le graphique affiché; toutes les prévisions "
                    "du bloc restent calculées et disponibles dans le tableau."
                ),
            )
            indicator_key, indicator_label, currency = selected_chart
            chart_data = _aggregate_forecast_chart(
                history,
                forecast,
                frequency=frequency,
                indicator_key=indicator_key,
                currency=currency,
                reference_date=reference_date,
                horizon_days=horizon_days,
            )
            if not chart_data.empty:
                chart_title = (
                    f"{indicator_label}{f' [{currency}]' if currency else ''}"
                )
                st.markdown(f"**{chart_title}**")
                st.caption(
                    f"Historique observé et prévision à {horizon_days} jours. "
                    f"La zone rouge représente l'intervalle de prévision à "
                    f"{confidence_level} %."
                )
                fig = px.line(
                    chart_data,
                    x="date",
                    y="valeur_graphique",
                    color="serie",
                    markers=True,
                    color_discrete_map={
                        "Historique": "#0b4ea2",
                        "Prévision": "#e63946",
                    },
                    labels={
                        "date": "Période",
                        "valeur_graphique": "Valeur",
                        "serie": "Série",
                    },
                )
                fig = style_standard_line(fig, height=350, tickangle=-20)
                prediction_band = chart_data.loc[
                    chart_data["serie"].eq("Prévision")
                    & chart_data["borne_basse"].notna()
                    & chart_data["borne_haute"].notna()
                ].sort_values("date")
                if not prediction_band.empty:
                    fig.add_scatter(
                        x=prediction_band["date"],
                        y=prediction_band["borne_haute"],
                        mode="lines",
                        line={"width": 0},
                        hoverinfo="skip",
                        showlegend=False,
                    )
                    fig.add_scatter(
                        x=prediction_band["date"],
                        y=prediction_band["borne_basse"],
                        mode="lines",
                        line={"width": 0},
                        fill="tonexty",
                        fillcolor="rgba(230, 57, 70, 0.14)",
                        name=f"Intervalle {confidence_level} %",
                        hovertemplate="Borne basse : %{y:,.2f}<extra></extra>",
                    )
                st_plot(
                    fig,
                    key=f"mpesa_forecast_plot_{scope_key}_{block_index}_{indicator_key}_{currency}",
                    source_note=str(block_summary.iloc[0].get("source", "")),
                    annotate_values=False,
                )
            table = block_summary[
                [
                    "indicateur",
                    "currency_code",
                    "valeur_prevue_horizon",
                    "valeur_periode_precedente",
                    "evolution_prevue_pct",
                    "mae",
                    "wape_pct",
                    "qualite_modele",
                    "nombre_jours_historique",
                ]
            ]
            _mpesa_dataframe(
                table,
                hide_index=True,
                width="stretch",
                column_config={
                    "indicateur": st.column_config.TextColumn("Indicateur", pinned=True),
                    "currency_code": st.column_config.TextColumn("Devise"),
                    "valeur_prevue_horizon": st.column_config.NumberColumn(
                        "Prévision sur l'horizon", format="%.2f"
                    ),
                    "valeur_periode_precedente": st.column_config.NumberColumn(
                        "Période précédente", format="%.2f"
                    ),
                    "evolution_prevue_pct": st.column_config.NumberColumn(
                        "Évolution prévue", format="%.1f %%"
                    ),
                    "mae": st.column_config.NumberColumn(
                        "Erreur moyenne (MAE)",
                        format="%.2f",
                        help=(
                            "MAE = Mean Absolute Error, soit erreur absolue moyenne. "
                            "Elle mesure l'écart moyen dans l'unité de l'indicateur."
                        ),
                    ),
                    "wape_pct": st.column_config.NumberColumn(
                        "Erreur pondérée (WAPE)",
                        format="%.1f %%",
                        help=(
                            "WAPE = Weighted Absolute Percentage Error, soit erreur "
                            "absolue pondérée en pourcentage. Plus elle est proche de "
                            "0 %, plus la prévision rétrospective est précise."
                        ),
                    ),
                    "qualite_modele": st.column_config.TextColumn("Lecture"),
                    "nombre_jours_historique": st.column_config.NumberColumn(
                        "Historique (jours)", format="%d"
                    ),
                },
            )

    with st.expander("4. Échéancier prévisionnel DAT", expanded=False):
        st.caption(
            "Ce tableau liste les DAT qui arrivent contractuellement à échéance dans l'horizon choisi. "
            "Il ne dépend pas du modèle prédictif."
        )
        if dat_schedule.empty:
            st.info("Aucun DAT positif n'arrive à échéance dans cet horizon.")
        else:
            dat_view = dat_schedule.loc[
                dat_schedule["currency_code"].astype(str).isin(selected_currency_set)
            ].copy()
            dat_columns = [
                "savings_id",
                "customer_id",
                "currency_code",
                "date_approved",
                "maturity_date",
                "jours_avant_echeance",
                "balance",
                "interet_estime_echeance",
                "capital_plus_interet_estime",
            ]
            _mpesa_dataframe(
                dat_view[[column for column in dat_columns if column in dat_view.columns]],
                hide_index=True,
                width="stretch",
                column_config={
                    "savings_id": st.column_config.TextColumn("DAT", pinned=True),
                    "customer_id": st.column_config.TextColumn("Client"),
                    "currency_code": st.column_config.TextColumn("Devise"),
                    "date_approved": st.column_config.DatetimeColumn(
                        "Souscription", format="DD/MM/YYYY HH:mm"
                    ),
                    "maturity_date": st.column_config.DatetimeColumn(
                        "Échéance", format="DD/MM/YYYY HH:mm"
                    ),
                    "jours_avant_echeance": st.column_config.NumberColumn(
                        "Jours restants", format="%d"
                    ),
                    "balance": st.column_config.NumberColumn(
                        "Capital bloqué", format="%.2f"
                    ),
                    "interet_estime_echeance": st.column_config.NumberColumn(
                        "Intérêt estimé", format="%.2f"
                    ),
                    "capital_plus_interet_estime": st.column_config.NumberColumn(
                        "Capital + intérêt estimé", format="%.2f"
                    ),
                },
            )

    with st.expander("Qualité et limites du modèle", expanded=False):
        st.markdown(
            """
- Le **WAPE — Weighted Absolute Percentage Error**, ou **erreur absolue pondérée en pourcentage**, compare l'erreur cumulée au volume réellement observé.
- Une qualité **Bonne** correspond à un WAPE inférieur ou égal à 20 % sur le test rétrospectif.
- Une qualité **Acceptable** correspond à un WAPE supérieur à 20 % et inférieur ou égal à 35 %.
- **Prudence** signifie que l'erreur dépasse 35 %, que l'activité est très irrégulière ou que la série est peu dense.
- Le modèle ne prévoit pas les soldes futurs d'épargne, l'encours futur des crédits, le défaut individuel ni un chiffre d'affaires certifié à partir d'un seul instantané.
            """
        )
        _mpesa_dataframe(coverage, hide_index=True, width="stretch")
        if not non_calculable.empty:
            st.caption("Indicateurs non calculables avec l'historique actuel")
            _mpesa_dataframe(non_calculable, hide_index=True, width="stretch")


def render_solution_mpesa_tab() -> None:
    render_panel_title("Solution M-PESA")
    render_summary_box(
        "Module independant",
        [
            "La Solution Numérique constitue la source operationnelle principale des montants, soldes, DAT, credits et remboursements.",
            "M-Pesa est le canal metier; les rapports G2 servent a enrichir l'identite et a controler les ecritures sans piloter les montants.",
            "Les analyses reposent uniquement sur les fichiers Excel televerses dans cet onglet, avec separation stricte CDF/USD.",
        ],
    )

    render_panel_title("Sources Solution Numérique principales (4)")
    st.caption(
        "Transactions, Savings Account, Loans Account et Customers suffisent au parcours Solution Numérique. "
        "Tous les emplacements acceptent plusieurs fichiers."
    )
    turbo_left, turbo_right = st.columns(2, gap="medium")
    with turbo_left:
        with st.container(border=True):
            transactions_file = st.file_uploader(
                "Transactions [Solution Numérique]",
                type=["xlsx", "xls"],
                key="mpesa_transactions_file",
                accept_multiple_files=True,
                help="Chargez une ou plusieurs périodes. Les écritures sont dédupliquées par id; dr et cr conservent leur logique comptable de la Solution Numérique.",
            )
        with st.container(border=True):
            savings_file = st.file_uploader(
                "Savings Account [Solution Numérique]",
                type=["xlsx", "xls"],
                key="mpesa_savings_file",
                accept_multiple_files=True,
                help=(
                    "Chargez de préférence le fichier complet Savings Account : les comptes NORMAL SAVINGS "
                    "et FIXED SAVINGS sont séparés automatiquement, soldes positifs ou nuls. À défaut, "
                    "sélectionnez ensemble Customers with Current Savings Account et Customers with Fixed "
                    "Savings Account; ce mode reste limité aux soldes positifs. Si les synthèses et la source "
                    "complète sont chargées ensemble, Savings Account est prioritaire."
                ),
            )
    with turbo_right:
        with st.container(border=True):
            loans_file = st.file_uploader(
                "Loans Account [Solution Numérique]",
                type=["xlsx", "xls"],
                key="mpesa_loans_file",
                accept_multiple_files=True,
                help=(
                    "Les fichiers sont unifiés par loan_id et la version la plus récente du crédit est "
                    "conservée. savings_account_id est utilisé pour la liaison directe avec Savings Account; "
                    "s'il est vide, le contrôle utilise customer_id + devise avec un compte courant unique."
                ),
            )
        with st.container(border=True):
            customers_file = st.file_uploader(
                "Customers [Solution Numérique]",
                type=["xlsx", "xls"],
                key="mpesa_customers_file",
                accept_multiple_files=True,
                help="Les exports clients sont cumulés sans répéter les mêmes fiches.",
            )

    render_panel_title("Sources facultatives de contrôle")
    optional_left, optional_right = st.columns(2, gap="medium")
    with optional_left:
        with st.container(border=True):
            g2_file = st.file_uploader(
                "Rapports G2 [M-Pesa] (facultatif)",
                type=["xlsx", "xls"],
                key="mpesa_g2_file",
                accept_multiple_files=True,
                help=(
                    "Chargez ensemble les rapports M-Pesa d'entrées 1441 et de sorties 15558. Sans rapport G2, "
                    "les analyses encore démontrables utilisent uniquement Transactions Solution Numérique."
                ),
            )
    with optional_right:
        with st.container(border=True):
            perfect_file = st.file_uploader(
                "Clients_Perfect (facultatif)",
                type=["xlsx", "xls"],
                key="mpesa_perfect_clients_file",
                accept_multiple_files=True,
                help="La colonne Phone_Prefixe sert au rapprochement; les fiches sont dédupliquées par identifiant client.",
            )

    with st.expander("Voir les colonnes attendues pour les fichiers", expanded=False):
        st.caption(
            "Cette grille aide à comprendre quels fichiers pilotent le cœur financier de la Solution Numérique "
            "et lesquels servent seulement au contrôle ou à l'analyse complémentaire."
        )
        expected_sources = pd.DataFrame(
            [
                {
                    "Priorité": 1,
                    "Fichier": "Transactions [Solution Numérique]",
                    "Importance": "Indispensable",
                    "Pourquoi": (
                        "Source principale des mouvements, chiffre d'affaires, dépôts, retraits, "
                        "remboursements, crédits décaissés et activité dans le temps."
                    ),
                    "Colonnes attendues": ", ".join(sorted(TRANSACTION_REQUIRED_COLUMNS)),
                },
                {
                    "Priorité": 2,
                    "Fichier": "Savings Account [Solution Numérique]",
                    "Importance": "Indispensable",
                    "Pourquoi": (
                        "Source des comptes ouverts, DAT, soldes d'épargne, comptes actifs/inactifs "
                        "et échéances DAT."
                    ),
                    "Colonnes attendues": (
                        "id, savings_id, customer_id, msisdn1, product_id, product_name, "
                        "product_description, currency_code, balance, status, date_closed, "
                        "date_approved, date_activated, is_interest_calculated, "
                        "last_interest_calculation_date, next_interest_calculation_date, "
                        "maturity_date, interest_earned, voda_interest, fees_due, locked_balance, "
                        "date_locked, created_at, updated_at"
                    ),
                },
                {
                    "Priorité": 3,
                    "Fichier": "Loans Account [Solution Numérique]",
                    "Importance": "Très important",
                    "Pourquoi": (
                        "Source des crédits accordés, encours, impayés, remboursements attendus "
                        "et portefeuille crédit."
                    ),
                    "Colonnes attendues": (
                        "id, loan_id, customer_id, customer, currency_code, loan_product_id, "
                        "savings_account_id, repayment_installments, repayment_period, "
                        "repayment_period_unit, loan_amount, loan_balance, amount_paid, "
                        "outstanding_principle, outstanding_setup_fees, outstanding_interest, "
                        "outstanding_penalty_fees, interest_earned, status_name, defaulted, "
                        "interest_calculated, is_rollover, is_grace_period, due_date, "
                        "last_repayment_date, last_interest_calc_date, created_at, updated_at, msisdn1"
                    ),
                },
                {
                    "Priorité": 4,
                    "Fichier": "Customers [Solution Numérique]",
                    "Importance": "Important",
                    "Pourquoi": (
                        "Permet de mesurer les créations de clients dans le temps et le nombre "
                            "de clients connus dans la Solution Numérique."
                    ),
                    "Colonnes attendues": ", ".join(sorted(CUSTOMERS_REQUIRED_COLUMNS)),
                },
                {
                    "Priorité": 5,
                    "Fichier": "Rapports G2 [M-Pesa]",
                    "Importance": "Facultatif utile",
                    "Pourquoi": (
                        "Sert surtout à enrichir le nom client et contrôler les écritures. "
                        "Ne doit pas piloter les montants."
                    ),
                    "Colonnes attendues": (
                        "Receipt No., Completion Time, Initiation Time, Details, Transaction Status, "
                        "Currency, Paid In, Withdrawn, Balance, Reason Type, Opposite Party, "
                        "Linked Transaction ID"
                    ),
                },
                {
                    "Priorité": 6,
                    "Fichier": "Clients_Perfect",
                    "Importance": "Facultatif analytique",
                    "Pourquoi": (
                        "Utile pour adoption, croisement Perfect/Solution Numérique/M-Pesa, mais pas nécessaire "
                        "au cœur financier M_PESA."
                    ),
                    "Colonnes attendues": ", ".join(sorted(PERFECT_CLIENTS_REQUIRED_COLUMNS)),
                },
            ]
        )
        _mpesa_dataframe(
            expected_sources,
            hide_index=True,
            column_config={
                "Priorité": st.column_config.NumberColumn("Priorité", format="%d"),
                "Fichier": st.column_config.TextColumn("Fichier", pinned=True),
                "Importance": st.column_config.TextColumn("Importance"),
                "Pourquoi": st.column_config.TextColumn("Pourquoi"),
                "Colonnes attendues": st.column_config.TextColumn("Colonnes attendues"),
            },
        )
        st.caption(
            "Alternative compatible pour Savings Account : sélectionner ensemble les exports résumés "
            "Customers with Current Savings Account et Customers with Fixed Savings Account. Cette "
            "alternative ne contient que les comptes à solde positif; la source complète Savings Account "
            "reste prioritaire lorsqu'elle est chargée."
        )

    try:
        transactions_raw = _uploaded_dataframes(
            transactions_file, source_column="fichier_source_transactions_turbo"
        )
        savings_raw = _uploaded_dataframes(
            savings_file, source_column="fichier_source_epargne_turbo"
        )
        customers_raw = _uploaded_dataframes(
            customers_file, source_column="fichier_source_clients_turbo"
        )
        loans_raw = _uploaded_dataframes(
            loans_file, source_column="fichier_source_credits_turbo"
        )
        g2_raw = _uploaded_g2_dataframes(g2_file)
        perfect_raw = _uploaded_dataframes(
            perfect_file, source_column="fichier_source_clients_perfect"
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    upload_fingerprint = _uploaded_files_fingerprint(
        transactions=transactions_file,
        savings_accounts=savings_file,
        loans=loans_file,
        g2=g2_file,
        customers=customers_file,
        perfect=perfect_file,
    )
    prepared, missing = _build_prepared_data(
        upload_fingerprint,
        transactions_raw,
        savings_raw,
        loans_raw,
        g2_raw,
        customers_raw,
        perfect_raw,
    )
    year_scope_mode, year_scope_start, year_scope_end = _selected_mpesa_year_scope()
    analysis_prepared = scope_mpesa_prepared_data_by_year(
        prepared,
        mode=year_scope_mode,
        start_year=year_scope_start,
        end_year=year_scope_end,
    )
    if analysis_prepared.year_scope_start is None:
        st.caption(
            "Périmètre annuel M_PESA : Ensemble des années. "
            "Les analyses utilisent l'intégralité des données chargées."
        )
    else:
        st.caption(
            f"Périmètre annuel M_PESA : {analysis_prepared.year_scope_label}. "
            f"Transactions retenues : {len(analysis_prepared.transactions):,} sur "
            f"{len(prepared.transactions):,}. Les positions Savings, DAT, crédits et clients "
            f"sont conservées jusqu'au {analysis_prepared.year_scope_end:%d/%m/%Y}. "
            "Les fichiers complets restent chargés en mémoire."
        )
    tabs_container_key = "mpesa_solution_tabs"
    inject_professional_tabs_css(container_key=tabs_container_key)
    tabs_container = st.container(key=tabs_container_key)
    sub_tabs = tabs_container.tabs(
        format_professional_tab_labels(MPESA_SOLUTION_TAB_LABELS)
    )
    with sub_tabs[0]:
        _render_import_tab(prepared, missing)
    with sub_tabs[1]:
        _render_customer_extract(analysis_prepared)
    with sub_tabs[2]:
        _render_finance_turbo_tab(analysis_prepared)
    with sub_tabs[3]:
        _render_clients_tab(analysis_prepared)
    with sub_tabs[4]:
        _render_dat_tab(None, analysis_prepared)
    with sub_tabs[5]:
        _render_loans_tab(None, analysis_prepared)
    with sub_tabs[6]:
        _render_g2_dat_tab(None, analysis_prepared)
    with sub_tabs[7]:
        _render_perfect_client_tab(analysis_prepared)
    with sub_tabs[8]:
        _render_statistics_tab(analysis_prepared, historical_prepared=prepared)
    with sub_tabs[9]:
        _render_forecast_tab(analysis_prepared)
