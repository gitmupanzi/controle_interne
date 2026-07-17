from __future__ import annotations

from dataclasses import replace
from datetime import time
import hashlib
from io import BytesIO
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.services.mpesa_analysis import (
    CURRENT_SAVINGS_REQUIRED_COLUMNS,
    CUSTOMER_STATEMENT_FOCUS_OPERATION_TYPES,
    CUSTOMER_STATEMENT_COLUMNS,
    CUSTOMERS_REQUIRED_COLUMNS,
    DEFAULT_DAT_ANNUAL_INTEREST_RATE_PCT,
    DEFAULT_DAT_REPAYMENT_PREPARATION_HORIZON_DAYS,
    FIXED_SAVINGS_REQUIRED_COLUMNS,
    G2_CLASSIFIED_TRANSACTION_COLUMNS,
    G2_TRANSACTION_REQUIRED_COLUMNS,
    LOAN_USEFUL_COLUMNS,
    PERFECT_CLIENTS_REQUIRED_COLUMNS,
    TRANSACTION_REQUIRED_COLUMNS,
    MpesaPreparedData,
    build_diagnostics,
    build_large_dat_summary,
    build_g2_daily_savings_report,
    build_g2_dat_crosscheck,
    build_g2_retention_report,
    build_g2_transaction_time_analysis,
    build_turbo_only_g2_transactions,
    build_load_report,
    build_mpesa_accounting_analysis,
    build_mpesa_dat_maturity_analysis,
    build_loan_savings_reconciliation,
    build_mpesa_management_dashboard,
    build_mpesa_statement,
    build_savings_accounts_reconciliation,
    build_customer_transaction_analysis,
    build_customer_statement_filename,
    build_customer_statement_view,
    build_perfect_client_crosscheck,
    create_excel_export,
    create_customer_statement_pdf,
    create_customer_statement_word,
    create_g2_dat_word,
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


@st.cache_data(show_spinner=False, max_entries=8)
def _create_excel_export_cached(export_report: dict[str, Any]) -> bytes:
    return create_excel_export(export_report)


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
) -> dict[str, pd.DataFrame]:
    return build_customer_transaction_analysis(
        prepared,
        customer_id,
        currency=currency,
        operation_types=operation_types,
        date_start=date_start,
        date_end=date_end,
        reference_query=reference_query,
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
    max_entries=8,
    hash_funcs={MpesaPreparedData: _prepared_data_cache_key},
)
def _build_mpesa_management_dashboard_cached(
    prepared: MpesaPreparedData,
    dat_annual_interest_rate_pct: float,
    analysis_date: object,
) -> dict[str, Any]:
    scoped_prepared = _prepared_data_as_of(prepared, analysis_date)
    return build_mpesa_management_dashboard(
        scoped_prepared,
        as_of_date=analysis_date,
        dat_annual_interest_rate_pct=dat_annual_interest_rate_pct,
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
    widgets = st.columns(min(3, max(1, len(available_columns))))
    for index, column in enumerate(available_columns):
        options = _filter_value_options(df[column])
        if not options:
            continue
        with widgets[index % len(widgets)]:
            selected_values = st.multiselect(
                column,
                options=options,
                default=[],
                key=f"{key_prefix}_{column}",
                placeholder="Choose options",
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
    st.dataframe(report, width="stretch", hide_index=True)
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
                ("Transactions [Turbo]", _format_count(len(prepared.transactions)), "Lignes M-PESA_Turbo importees", "blue"),
                (
                    "Clients distincts [Transactions_Turbo]",
                    _format_count(clients),
                    "Identifiants observes dans Transactions M-PESA_Turbo",
                    "navy",
                ),
                ("Periode", _period_label(prepared.transactions), "Transactions Turbo", "green"),
                ("Devises", currencies, "Codes detectes Turbo", "orange"),
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
            f"{missing_summary} dans le meme emplacement Savings Account [Turbo]."
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
                "Composition de Savings Account [Turbo]"
                if source_complete_available
                else "Compatibilite des syntheses d'epargne [Turbo]"
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
                "Savings Account est la source Turbo autonome des comptes courants et des DAT; "
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
            st.warning(reconciliation_message)
        savings_gaps = savings_reconciliation.get("ecarts", pd.DataFrame())
        if not savings_gaps.empty:
            with st.expander("Afficher les ecarts Savings Account / DAT", expanded=False):
                st.dataframe(savings_gaps, width="stretch", hide_index=True)
    unnamed_count = sum(
        int(frame.columns.astype(str).str.match(r"^Unnamed(:|$)", na=False).sum())
        for frame in [prepared.transactions, prepared.current_savings, prepared.fixed_savings, prepared.loans]
        if not frame.empty
    )
    st.caption(f"Colonnes `Unnamed` restantes apres nettoyage : {unnamed_count}.")


def _filter_statement(
    statement: pd.DataFrame,
    *,
    key_prefix: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    context: dict[str, Any] = {
        "currency": "Toutes",
        "operation_types": [],
        "date_start": None,
        "date_end": None,
        "reference_query": "",
    }
    if statement.empty:
        return statement, context
    filtered = statement.copy()
    first_row, second_row = st.columns(2)
    currencies = _currency_options(filtered)
    selected_currency = "Toutes"
    if currencies:
        selected_currency = first_row.selectbox("Devise", ["Toutes"] + currencies, key=f"{key_prefix}_currency")
        context["currency"] = selected_currency
        if selected_currency != "Toutes":
            filtered = filtered.loc[filtered["currency_code"].eq(selected_currency)]
    operation_types = sorted(filtered["type_operation"].dropna().astype(str).unique()) if "type_operation" in filtered.columns else []
    if operation_types:
        default_operation_types = [
            operation_type
            for operation_type in operation_types
            if operation_type in CUSTOMER_STATEMENT_FOCUS_OPERATION_TYPES
        ]
        selected_types = second_row.multiselect(
            "Type d'operation",
            operation_types,
            default=default_operation_types,
            key=f"{key_prefix}_{selected_currency}_type",
            placeholder="Choose options",
            help=(
                "Par defaut : depots, retraits vers M-PESA, decaissements de credit et remboursements de credit. "
                "Aucune option choisie = tous les types d'operation."
            ),
        )
        context["operation_types"] = selected_types
        if selected_types:
            filtered = filtered.loc[filtered["type_operation"].isin(selected_types)]
    if "created_at" in filtered.columns:
        dates = pd.to_datetime(filtered["created_at"], errors="coerce").dropna()
        if not dates.empty:
            date_key = f"{key_prefix}_{selected_currency}_{dates.min():%Y%m%d}_{dates.max():%Y%m%d}"
            date_range = first_row.date_input(
                "Periode",
                value=(dates.min().date(), dates.max().date()),
                min_value=dates.min().date(),
                max_value=dates.max().date(),
                key=f"{date_key}_dates",
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                context["date_start"] = start
                context["date_end"] = end
                filtered = filtered.loc[
                    pd.to_datetime(filtered["created_at"], errors="coerce").between(
                        pd.Timestamp(start),
                        pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1),
                    )
                ]
    ref_query = second_row.text_input("Reference M-PESA_Turbo, DAT ou credit", key=f"{key_prefix}_reference").strip()
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
        balance_available = pd.notna(row.get("solde_mpesa_final"))
        render_panel_title(f"Devise {currency}")
        render_kpi_cards(
            [
                ("Operations [Turbo]", _format_count(row.get("nombre_operations_mpesa")), f"Devise {currency}", "blue"),
                ("Entrees [Turbo]", _format_amount(row.get("total_entrees_mpesa")), f"Devise {currency}", "green"),
                ("Sorties [Turbo]", _format_amount(row.get("total_sorties_mpesa")), f"Devise {currency}", "orange"),
                ("Net [Turbo]", _format_amount(row.get("mouvement_net")), f"Devise {currency}", "navy"),
                (
                    "Solde M-PESA_Turbo final",
                    _format_amount(row.get("solde_mpesa_final")),
                    "Solde reel" if balance_available else "Solde d'ouverture non fourni",
                    "slate",
                ),
                ("Epargne finale", _format_amount(row.get("epargne_courante_finale")), f"Devise {currency}", "green"),
                ("DAT final", _format_amount(row.get("dat_final")), f"Devise {currency}", "navy"),
                ("Credits", _format_count(row.get("nombre_credits")), f"Solde {_format_amount(row.get('solde_credit_total'))}", "red"),
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
    chart_df["jour"] = chart_df["created_at"].dt.date
    left, right = st.columns(2)
    with left:
        render_panel_title("Mouvement net [Turbo]")
        fig = px.line(chart_df, x="created_at", y="mouvement_net_mpesa", color="currency_code", markers=True)
        style_standard_line(fig, height=330, tickangle=-20)
        st_plot(fig, key="mpesa_net_movement", height=330)
    with right:
        render_panel_title("Entrees et sorties par jour [Turbo]")
        daily = chart_df.groupby(["jour", "currency_code"], as_index=False).agg(entrees=("entree_mpesa", "sum"), sorties=("sortie_mpesa", "sum"))
        long_daily = daily.melt(id_vars=["jour", "currency_code"], value_vars=["entrees", "sorties"], var_name="sens", value_name="montant")
        fig = px.bar(long_daily, x="jour", y="montant", color="sens", facet_col="currency_code")
        style_standard_vertical_bar(fig, height=330, tickangle=-20)
        st_plot(fig, key="mpesa_daily_in_out", height=330)
    with st.expander("Afficher les graphiques complementaires", expanded=False):
        left, right = st.columns(2)
        with left:
            if "solde_mpesa_apres" in chart_df.columns and chart_df["solde_mpesa_apres"].notna().any():
                render_panel_title("Solde M-PESA_Turbo")
                fig = px.line(chart_df.dropna(subset=["solde_mpesa_apres"]), x="created_at", y="solde_mpesa_apres", color="currency_code", markers=True)
                style_standard_line(fig, height=330, tickangle=-20)
                st_plot(fig, key="mpesa_balance", height=330)
            else:
                st.warning("Le solde d'ouverture M-PESA_Turbo n'a pas ete fourni. Le graphique de solde reel n'est pas affiche.")
        with right:
            render_panel_title("Operations par type [Turbo]")
            type_df = chart_df.groupby("type_operation", as_index=False).size().rename(columns={"size": "nombre"})
            fig = px.pie(type_df, names="type_operation", values="nombre", hole=0.48)
            style_standard_donut(fig, height=330)
            st_plot(fig, key="mpesa_operation_types", height=330)
        left, right = st.columns(2)
        with left:
            if "solde_dat_total_au_moment" in chart_df.columns:
                render_panel_title("DAT total au moment [Turbo]")
                fig = px.line(chart_df, x="created_at", y="solde_dat_total_au_moment", color="currency_code", markers=True)
                style_standard_line(fig, height=330, tickangle=-20)
                st_plot(fig, key="mpesa_dat_total", height=330)
        with right:
            if "solde_epargne_au_moment" in chart_df.columns:
                render_panel_title("Epargne courante au moment [Turbo]")
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
        render_panel_title(f"Comportement observe [Turbo] - {currency}")
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
        render_panel_title("Jalons du parcours financier [Turbo]")
        st.caption(
            "Une ligne par devise et type d'operation. Les montants CDF et USD restent toujours separes."
        )
        st.dataframe(
            _format_customer_analysis_dates(milestones),
            width="stretch",
            hide_index=True,
        )
    if not path.empty:
        with st.expander("Afficher la chronologie complete [Turbo]", expanded=False):
            st.dataframe(
                _format_customer_analysis_dates(path),
                width="stretch",
                hide_index=True,
            )


def _render_customer_credit_and_positions(analysis: dict[str, pd.DataFrame]) -> None:
    credit_summary = analysis.get("credit_turbo_synthese_client", pd.DataFrame())
    credit_detail = analysis.get("credit_turbo_detail_client", pd.DataFrame())
    positions = analysis.get("positions_turbo", pd.DataFrame())
    internal = analysis.get("mouvements_internes_turbo", pd.DataFrame())

    if credit_summary.empty:
        st.info("Aucun decaissement ou remboursement de credit ne correspond aux filtres actifs.")
    else:
        st.caption(
            "Les interets et penalites ci-dessous sont des montants comptabilises observes dans Transactions M-PESA_Turbo. "
            "Ils ne constituent ni un taux annuel contractuel ni une rentabilite nette du client."
        )
        for _, row in credit_summary.iterrows():
            currency = str(row.get("currency_code", ""))
            render_panel_title(f"Credit et remboursements observes [Turbo] - {currency}")
            render_kpi_cards(
                [
                    (
                        "Decaissements",
                        _format_count(row.get("nombre_decaissements")),
                        f"Verse au client : {_format_amount(row.get('montant_decaisse_client'))} {currency}",
                        "blue",
                    ),
                    (
                        "Dette creee observee",
                        _format_amount(row.get("dette_creee_observee")),
                        currency,
                        "navy",
                    ),
                    (
                        "Interet observe",
                        _format_amount(row.get("interet_observe")),
                        f"Ratio / decaissement : {_format_percent(row.get('ratio_interet_decaissement_pct'))}",
                        "green",
                    ),
                    (
                        "Remboursements",
                        _format_count(row.get("nombre_remboursements")),
                        f"Principal : {_format_amount(row.get('principal_rembourse'))} {currency}",
                        "orange",
                    ),
                    (
                        "Avec penalite",
                        _format_count(row.get("remboursements_avec_penalite")),
                        f"Penalite observee : {_format_amount(row.get('penalite_observee'))} {currency}",
                        "red",
                    ),
                    (
                        "Avec epargne / DAT",
                        _format_count(row.get("remboursements_avec_epargne_dat")),
                        "Ecritures associees observees",
                        "slate",
                    ),
                ]
            )
        if not credit_detail.empty:
            with st.expander("Afficher la ventilation des operations de credit [Turbo]", expanded=False):
                st.dataframe(
                    _format_customer_analysis_dates(credit_detail),
                    width="stretch",
                    hide_index=True,
                )

    render_panel_title("Positions observees par produit [Turbo]")
    if positions.empty:
        st.info("Aucun solde de produit n'est disponible pour ce client et ce perimetre.")
    else:
        st.caption(
            "`solde_transactions_observe` est le dernier `bal_after` exploitable dans Transactions M-PESA_Turbo. "
            "Il n'est qualifie de conforme que lorsqu'un fichier Epargne, DAT ou Credits_Turbo charge confirme le meme montant."
        )
        st.dataframe(
            _format_customer_analysis_dates(positions),
            width="stretch",
            hide_index=True,
        )

    if not internal.empty:
        with st.expander("Afficher les mouvements internes epargne / DAT [Turbo]", expanded=False):
            st.caption(
                "Ces transferts n'ont pas toujours de ligne `MPESA ACCOUNT`. Ils sont presentes separement et ne sont pas "
                "ajoutes aux entrees ou sorties M-PESA de l'extrait officiel."
            )
            st.dataframe(
                _format_customer_analysis_dates(internal),
                width="stretch",
                hide_index=True,
            )


def _render_customer_turbo_controls(analysis: dict[str, pd.DataFrame]) -> None:
    controls = analysis.get("controles_client_turbo", pd.DataFrame())
    if controls.empty:
        st.info("Aucun controle Turbo disponible pour le perimetre filtre.")
        return
    review_mask = controls.get(
        "statut_controle_turbo", pd.Series("", index=controls.index)
    ).astype("string").eq("A verifier")
    review = controls.loc[review_mask].copy()
    render_kpi_cards(
        [
            ("Operations controlees [Turbo]", _format_count(len(controls)), "Perimetre filtre", "blue"),
            ("Montants miroirs conformes", _format_count(controls["controle_montant_operation"].eq("Conforme").sum()), "Paires metier", "green"),
            ("Operations a verifier", _format_count(len(review)), "Controle Turbo", "orange"),
        ]
    )
    if review.empty:
        st.success("Aucun ecart metier Turbo n'a ete detecte dans les operations filtrees.")
    else:
        st.warning(
            "Les lignes ci-dessous sont des points de revue. Elles ne constituent pas automatiquement une erreur ou une fraude."
        )
        st.dataframe(
            _format_customer_analysis_dates(review),
            width="stretch",
            hide_index=True,
        )
    with st.expander("Afficher tous les controles et les debits/credits techniques", expanded=False):
        st.caption(
            "L'ecart debit/credit global est informatif : certaines operations Turbo contiennent des comptes de collecte "
            "ou de revenu dont la semantique n'est pas celle du seul compte client."
        )
        st.dataframe(
            _format_customer_analysis_dates(controls),
            width="stretch",
            hide_index=True,
        )


def _display_text(value: Any, fallback: str = "Non disponible") -> str:
    if value is None or pd.isna(value) or str(value).strip() in {"", "<NA>", "nan", "None"}:
        return fallback
    return str(value).strip()


def _render_customer_statement_preview(
    statement: pd.DataFrame,
    *,
    customer_id: str,
    customer_name: str,
    telephone: str,
    entry_account_number: str,
    output_account_number: str,
    filter_context: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    previews: dict[str, dict[str, Any]] = {}
    if statement.empty:
        st.info("Aucune operation ne correspond aux filtres. L'extrait Word ne peut pas etre genere.")
        return previews

    currencies = _currency_options(statement)
    for currency in currencies:
        currency_statement = statement.loc[statement["currency_code"].eq(currency)].copy()
        view = build_customer_statement_view(
            currency_statement,
            entry_account_number=entry_account_number,
            output_account_number=output_account_number,
        )
        previews[currency] = view
        dates = pd.to_datetime(currency_statement.get("created_at"), errors="coerce").dropna()
        date_start = filter_context.get("date_start")
        date_end = filter_context.get("date_end")
        if date_start is None and not dates.empty:
            date_start = dates.min().date()
        if date_end is None and not dates.empty:
            date_end = dates.max().date()

        st.markdown(f"#### Extrait de compte [Turbo] - {telephone} - {customer_name} - {currency}")
        render_summary_box(
            "Criteres du releve",
            [
                f"Date du : {pd.Timestamp(date_start):%d/%m/%Y}" if date_start is not None else "Date du : Non disponible",
                f"Au : {pd.Timestamp(date_end):%d/%m/%Y}" if date_end is not None else "Au : Non disponible",
                f"Numero du client : {customer_id}",
                f"Telephone : {telephone}",
                f"Devise : {currency}",
            ],
        )
        balance_prefix = "Solde" if view["balance_is_real"] else "Cumul"
        render_kpi_cards(
            [
                (f"{balance_prefix} initial", _format_amount(view["opening_amount"]), currency, "slate"),
                ("Total entrees [Turbo]", _format_amount(view["total_entries"]), currency, "green"),
                ("Total sorties [Turbo]", _format_amount(view["total_outputs"]), currency, "orange"),
                (f"{balance_prefix} final", _format_amount(view["closing_amount"]), currency, "navy"),
            ]
        )
        if not view["balance_is_real"]:
            st.warning(
                "Le solde d'ouverture n'est pas renseigne pour cette devise. "
                "La colonne affiche un cumul net relatif et non le solde reel du compte."
            )

        display = view["transactions"][CUSTOMER_STATEMENT_COLUMNS].copy()
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
                "receipt_no": "Receipt No",
                "devise": "Devise",
                "description": "Description",
                "entree": "Entree",
                "sortie": "Sortie",
                "solde": view["balance_label"],
            }
        )
        st.dataframe(display, width="stretch", hide_index=True)
    return previews


@st.fragment
def _render_customer_extract(prepared: MpesaPreparedData) -> dict[str, Any] | None:
    if prepared.transactions.empty:
        st.info("Chargez au minimum le fichier Transactions M-PESA_Turbo pour construire un extrait client Turbo.")
        return None

    if prepared.g2_transactions.empty:
        st.info(
            "Mode Turbo seul : l'extrait client, la recherche, les soldes reconstruits et les exports "
            "fonctionnent sans Transactions M-PESA_G2. Le nom G2 et le controle croise restent simplement indisponibles."
        )
    else:
        st.caption(
            "Transactions M-PESA_Turbo reste la source des mouvements de l'extrait. "
            "Transactions M-PESA_G2 sert uniquement a completer le nom du client et a verifier les operations rapprochees."
        )

    has_g2_names = (
        not prepared.g2_transactions.empty
        and "Nom_client" in prepared.g2_transactions.columns
        and prepared.g2_transactions["Nom_client"].notna().any()
    )
    search_help = (
        "La recherche accepte un customer_id, un numero de telephone ou un nom client issu du fichier G2."
        if has_g2_names
        else "La recherche accepte un customer_id ou un numero de telephone. Chargez G2 pour rechercher aussi par nom."
    )
    render_panel_title("1. Rechercher et selectionner un client")
    st.caption(search_help)
    query_label = "Customer ID, telephone ou nom" if has_g2_names else "Customer ID ou telephone"
    query = st.text_input(query_label, key="mpesa_customer_query")
    if not query.strip():
        st.info("Saisissez une valeur de recherche pour commencer l'analyse du client.")
        return None

    matches = search_customers(query, prepared)
    if matches.empty:
        st.warning("Aucun client trouve.")
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
        st.success(f"Client unique trouve : {candidate_labels[selected_customer]}")
    else:
        selected_customer = st.selectbox(
            "Client a analyser",
            match_options,
            format_func=lambda customer_id: candidate_labels.get(str(customer_id), str(customer_id)),
            key="mpesa_selected_customer",
        )
    with st.expander(f"Voir les {len(candidates)} client(s) correspondant(s)", expanded=False):
        st.dataframe(candidates, width="stretch", hide_index=True)

    identity = candidates.loc[candidates["customer_id"].astype(str).eq(selected_customer)].iloc[0]
    render_panel_title("2. Identite et parametres du client")
    render_summary_box(
        "Client selectionne",
        [
            f"Customer ID : {selected_customer}",
            f"Nom : {identity['Nom_client'] or 'Non disponible'}",
            f"Telephone : {identity['telephone'] or 'Non disponible'}",
            f"Sources retrouvees : {identity['sources'] or 'Non disponible'}",
        ],
    )

    account_columns = st.columns(2)
    entry_account_number = account_columns[0].text_input(
        "Compte des entrees",
        value="1441",
        key=f"mpesa_statement_entry_account_{selected_customer}",
        help="Compte G2 des entrees : depots et remboursements de credit.",
    ).strip()
    output_account_number = account_columns[1].text_input(
        "Compte des sorties",
        value="15558",
        key=f"mpesa_statement_output_account_{selected_customer}",
        help="Compte G2 des sorties : decaissements de credit et autres sorties retenues.",
    ).strip()

    currencies = _currency_options(prepared.transactions.loc[prepared.transactions["customer_id"].astype(str).eq(selected_customer)])
    opening_balances: dict[str, float | None] = {}
    with st.expander("Optionnel - renseigner les soldes d'ouverture M-PESA_Turbo", expanded=False):
        st.caption("Activez uniquement les devises dont le solde d'ouverture est connu et fiable.")
        opening_cols = st.columns(max(len(currencies), 1))
        for index, currency in enumerate(currencies or ["CDF", "USD"]):
            with opening_cols[index % len(opening_cols)]:
                use_value = st.checkbox(
                    f"Solde {currency} connu",
                    value=False,
                    key=f"mpesa_use_opening_{selected_customer}_{currency}",
                )
                value = st.number_input(
                    f"Solde d'ouverture {currency}",
                    min_value=0.0,
                    value=0.0,
                    step=1.0 if currency == "USD" else 1000.0,
                    key=f"mpesa_opening_{selected_customer}_{currency}",
                    disabled=not use_value,
                )
                opening_balances[currency] = value if use_value else None

    try:
        report = _build_mpesa_statement_cached(
            prepared,
            selected_customer,
            tuple(sorted(opening_balances.items())),
        )
    except ValueError as exc:
        st.warning(str(exc))
        return None

    st.caption(f"Mode de source : {report.get('mode_source_extrait', 'Turbo seul')}.")

    statement = report["extrait"]
    summary = report["synthese"]
    render_panel_title("3. Situation financiere par devise [Turbo]")
    _render_customer_kpis(summary)
    if statement["solde_mpesa_apres"].isna().all():
        st.warning(
            "Le solde d'ouverture M-PESA_Turbo n'a pas ete fourni. Le resultat affiche est un cumul relatif et non le solde reel du portefeuille."
        )

    render_panel_title("4. Filtrer les mouvements")
    filtered_statement, filter_context = _filter_statement(
        statement,
        key_prefix=f"mpesa_statement_{selected_customer}",
    )
    st.caption(f"{len(filtered_statement)} operation(s) retenue(s) sur {len(statement)} pour le client.")
    filtered_report = dict(report)
    filtered_report["extrait"] = filtered_statement
    filtered_report["synthese"] = report["synthese"]
    filtered_analysis = _build_customer_transaction_analysis_cached(
        prepared,
        selected_customer,
        str(filter_context.get("currency", "Toutes")),
        tuple(str(value) for value in filter_context.get("operation_types", [])),
        filter_context.get("date_start"),
        filter_context.get("date_end"),
        str(filter_context.get("reference_query", "")),
    )
    filtered_report.update(filtered_analysis)

    customer_name = _display_text(identity["Nom_client"])
    customer_phone = _display_text(identity["telephone"])
    render_panel_title("5. Apercu de l'extrait de compte")
    previews = _render_customer_statement_preview(
        filtered_statement,
        customer_id=selected_customer,
        customer_name=customer_name,
        telephone=customer_phone,
        entry_account_number=entry_account_number,
        output_account_number=output_account_number,
        filter_context=filter_context,
    )

    render_panel_title("6. Parcours financier du client [Turbo]")
    _render_customer_journey_analysis(filtered_analysis)

    render_panel_title("7. Credit, remboursements et positions observees [Turbo]")
    _render_customer_credit_and_positions(filtered_analysis)

    render_panel_title("8. Analyses et controles complementaires")
    with st.expander("Afficher les graphiques", expanded=False):
        _render_statement_charts(filtered_statement)
    with st.expander("Afficher les controles metier [Turbo]", expanded=False):
        _render_customer_turbo_controls(filtered_analysis)
    with st.expander("Afficher la verification facultative [G2]", expanded=False):
        g2_control = report.get("g2_dat", pd.DataFrame())
        if not report.get("controle_g2_disponible", False):
            st.info(
                "Transactions M-PESA_G2 n'est pas charge. L'extrait Turbo reste complet; "
                "ce bloc de verification est facultatif."
            )
        elif not isinstance(g2_control, pd.DataFrame) or g2_control.empty:
            st.warning(
                "Le fichier G2 est charge, mais aucune transaction G2 n'a pu etre rattachee "
                "au client Turbo selectionne."
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
                    ("Transactions [G2] liees", _format_count(len(g2_control)), "Client Turbo selectionne", "blue"),
                    ("Rapprochements exacts", _format_count(exact_count), "G2 contre Turbo", "green"),
                    ("Anomalies [G2]", _format_count(anomaly_count), "Dont ecarts de date > 60 minutes", "orange"),
                ]
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
            st.dataframe(
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
            "solde_mpesa_avant",
            "solde_mpesa_apres",
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
                "solde_mpesa_avant": "solde_mpesa_turbo_avant",
                "solde_mpesa_apres": "solde_mpesa_turbo_apres",
            }
        )
        st.dataframe(technical_display, width="stretch", hide_index=True)
        st.caption("Vue complete des colonnes disponibles")
        full_display = filtered_statement.rename(
            columns={
                "entree_mpesa": "entree_mpesa_turbo",
                "sortie_mpesa": "sortie_mpesa_turbo",
                "mouvement_net_mpesa": "mouvement_net_mpesa_turbo",
                "solde_mpesa_avant": "solde_mpesa_turbo_avant",
                "solde_mpesa_apres": "solde_mpesa_turbo_apres",
            }
        )
        st.dataframe(full_display, width="stretch", hide_index=True)

    render_panel_title("9. Export")
    st.caption(
        "Les exports Word et PDF reprennent exactement le client, la periode, la devise, les types d'operation et les references filtres. "
        "Les boutons CDF et USD produisent un document par devise; ALL les reunit dans un seul document "
        "avec des totaux et cumuls toujours separes par devise."
    )
    if previews:
        export_targets = list(previews)
        if len(export_targets) > 1:
            export_targets.append("ALL")
        # Garder des actions compactes meme lorsqu'une seule devise est disponible.
        # Trois colonnes donnent une largeur maximale d'environ un tiers sur ordinateur.
        word_columns = st.columns(3)
        for index, currency in enumerate(export_targets):
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
            try:
                word_bytes = _create_customer_statement_word_cached(
                    target_statement,
                    filtered_analysis,
                    selected_customer,
                    customer_name,
                    customer_phone,
                    currency,
                    entry_account_number,
                    output_account_number,
                    date_start,
                    date_end,
                )
            except (RuntimeError, ValueError) as exc:
                word_columns[index % len(word_columns)].error(str(exc))
                continue
            file_name = build_customer_statement_filename(
                customer_id=selected_customer,
                customer_name=customer_name,
                telephone=customer_phone,
                currency=currency,
                period_start=date_start,
                period_end=date_end,
                g2_available=not prepared.g2_transactions.empty,
            )
            start_token = f"{pd.Timestamp(date_start):%Y%m%d}" if date_start is not None else "debut"
            end_token = f"{pd.Timestamp(date_end):%Y%m%d}" if date_end is not None else "fin"
            word_columns[index % len(word_columns)].download_button(
                f"Telecharger l'extrait Word {currency}",
                data=word_bytes,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
                key=f"mpesa_customer_word_{selected_customer}_{currency}_{start_token}_{end_token}",
            )
        pdf_columns = st.columns(3)
        for index, currency in enumerate(export_targets):
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
            try:
                pdf_bytes = _create_customer_statement_pdf_cached(
                    target_statement,
                    filtered_analysis,
                    selected_customer,
                    customer_name,
                    customer_phone,
                    currency,
                    entry_account_number,
                    output_account_number,
                    date_start,
                    date_end,
                )
            except (RuntimeError, ValueError) as exc:
                pdf_columns[index % len(pdf_columns)].error(str(exc))
                continue
            pdf_file_name = build_customer_statement_filename(
                customer_id=selected_customer,
                customer_name=customer_name,
                telephone=customer_phone,
                currency=currency,
                period_start=date_start,
                period_end=date_end,
                g2_available=not prepared.g2_transactions.empty,
            ).removesuffix(".docx") + ".pdf"
            start_token = f"{pd.Timestamp(date_start):%Y%m%d}" if date_start is not None else "debut"
            end_token = f"{pd.Timestamp(date_end):%Y%m%d}" if date_end is not None else "fin"
            pdf_columns[index % len(pdf_columns)].download_button(
                f"Telecharger l'extrait PDF {currency}",
                data=pdf_bytes,
                file_name=pdf_file_name,
                mime="application/pdf",
                width="stretch",
                key=f"mpesa_customer_pdf_{selected_customer}_{currency}_{start_token}_{end_token}",
            )

    st.caption(
        "La feuille `Extrait_Turbo` reprend les filtres appliques a l'etape 4. "
        "Le classeur ajoute uniquement les analyses client utiles : parcours, credit, positions, comportement et controles Turbo."
    )
    customer_export = {
        key: filtered_report.get(key, pd.DataFrame())
        for key in [
            "synthese",
            "extrait",
            "parcours_turbo",
            "credit_turbo_detail_client",
            "positions_turbo",
            "comportement_turbo",
            "mouvements_internes_turbo",
            "controles_client_turbo",
            "dat_final",
            "credits",
            "g2_dat",
            "diagnostics",
        ]
    }
    export_bytes = _create_excel_export_cached(customer_export)
    excel_column = st.columns(3)[0]
    excel_column.download_button(
        "Telecharger le rapport complet du client [Turbo]",
        data=export_bytes,
        file_name=f"extrait_turbo_dat_client_{selected_customer}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    return filtered_report


def _render_dat_repayment_schedule(prepared: MpesaPreparedData) -> None:
    render_panel_title("Echeances et remboursements DAT [Turbo]")
    if prepared.fixed_savings.empty:
        st.info("Chargez Savings Account [Turbo] pour identifier les DAT echus ou proches de leur terme.")
        return

    controls = st.columns(2, gap="medium")
    with controls[0]:
        analysis_date = st.date_input(
            "Date de situation DAT",
            value=pd.Timestamp.now().date(),
            key="mpesa_dat_repayment_analysis_date",
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
        render_panel_title(f"Remboursements DAT a preparer [Turbo] - {currency}")
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
    st.dataframe(
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
            "status": st.column_config.TextColumn("Statut Turbo"),
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
    export_bytes = _create_excel_export_cached(
        {"dat_echeances_detail": filtered_actionable}
    )
    st.download_button(
        "Telecharger les remboursements DAT a preparer [Turbo]",
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

    render_panel_title("Synthese des clients avec de forts DAT [Turbo]")
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
        render_panel_title(f"Forts DAT [Turbo] - {currency}")
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
    render_panel_title("Tableau fusionne des forts DAT [Turbo] - CDF et USD")
    combined_view = _apply_local_multiselect_filters(
        combined_strong_clients,
        ["currency_code", "produits_dat", "Nom_client", "customer_id"],
        key_prefix="mpesa_large_dat_combined_filter",
    )
    st.caption(f"{len(combined_view)} client(s) affiche(s), toutes devises confondues sans addition des montants.")
    st.dataframe(combined_view[display_columns], width="stretch", hide_index=True)

    export_bytes = _create_excel_export_cached(
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
    _render_dat_repayment_schedule(prepared)
    _render_large_dat_summary(prepared)
    if report is not None:
        render_panel_title("DAT final du client [Turbo]")
        dat_view = _apply_local_multiselect_filters(
            report["dat_final"],
            ["currency_code", "product_name", "account_type", "statut_dat"],
            key_prefix="mpesa_dat_final_filter",
        )
        st.caption(f"{len(dat_view)} ligne(s) DAT affichee(s).")
        st.dataframe(dat_view, width="stretch", hide_index=True)
        render_panel_title("Mouvements DAT reconstruits [Turbo]")
        dat_movements_view = _apply_local_multiselect_filters(
            report["mouvements_dat"],
            ["currency_code", "references", "descriptions"],
            key_prefix="mpesa_dat_movements_filter",
        )
        st.dataframe(dat_movements_view, width="stretch", hide_index=True)
    elif not prepared.fixed_savings.empty:
        render_panel_title("DAT importes [Turbo]")
        dat_view = _apply_local_multiselect_filters(
            prepared.fixed_savings,
            ["currency_code", "product_name", "account_type"],
            key_prefix="mpesa_dat_import_filter",
        )
        st.caption(f"{len(dat_view)} ligne(s) DAT affichee(s).")
        st.dataframe(dat_view.head(500), width="stretch", hide_index=True)
    else:
        st.info("Aucun DAT trouve dans Savings Account [Turbo].")
    st.caption(
        "Les comptes DAT proviennent de Savings Account [Turbo]. Les interets et montants de remboursement affiches sont des estimations de preparation."
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
    report_bytes = _create_excel_export_cached(export_report)
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
        "Le Word reprend le tableau Transactions dans le meme ordre sur une page paysage; "
        "l'Excel conserve uniquement les syntheses, comptages, details et controles indispensables."
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
            "operations comptabilisees Turbo, une occurrence par operation analytique."
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
        daily_tab, weekday_tab, hourly_tab, day_hour_tab = st.tabs(
            ["Par jour", "Par jour de semaine", "Par heure", "Jour x heure"]
        )
        with daily_tab:
            st.dataframe(par_jour, width="stretch", hide_index=True)
        with weekday_tab:
            st.dataframe(par_jour_semaine, width="stretch", hide_index=True)
        with hourly_tab:
            st.dataframe(par_heure, width="stretch", hide_index=True)
        with day_hour_tab:
            st.caption("Detail des heures effectivement actives; les heures sans transaction ne sont pas repetees.")
            st.dataframe(jour_heure, width="stretch", hide_index=True)


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
    st.dataframe(monthly[monthly_columns], width="stretch", hide_index=True)

    with st.expander("Afficher la fidelisation par type d'operation", expanded=False):
        st.caption(
            "Un client ayant plusieurs types d'operation pendant un meme mois figure dans chaque segment concerne; "
            "les segments ne doivent donc pas etre additionnes."
        )
        st.dataframe(retention_report.get("operations", pd.DataFrame()), width="stretch", hide_index=True)
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
        st.dataframe(detail[detail_columns], width="stretch", hide_index=True)
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
                "Chargez Transactions M-PESA_Turbo ou Transactions M-PESA_G2 pour alimenter ce sous-onglet."
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
            "Mode Turbo seul : le rapport est construit sans fichier Transactions M-PESA_G2. "
            "Les operations sont deduites de `ref_no`, `account_type`, `description`, `dr`, `cr` et `created_at`. "
            "Les noms, statuts, soldes et delais G2 ainsi que les controles croises G2-Turbo ne sont pas disponibles."
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
        date_columns = st.columns(2)
        with date_columns[0]:
            date_start = st.date_input(
                f"{source_date_label} - date de debut",
                value=default_completion_date,
                min_value=completion_times.min().date(),
                max_value=completion_times.max().date(),
                key=f"mpesa_g2_completion_start_{completion_key}",
            )
            time_start = st.time_input(
                "Heure de debut",
                value=time(0, 0, 0),
                step=60,
                key=f"mpesa_g2_completion_start_time_{completion_key}",
            )
        with date_columns[1]:
            date_end = st.date_input(
                f"{source_date_label} - date de fin",
                value=default_completion_date,
                min_value=completion_times.min().date(),
                max_value=completion_times.max().date(),
                key=f"mpesa_g2_completion_end_{completion_key}",
            )
            time_end = st.time_input(
                "Heure de fin",
                value=time(23, 59, 59),
                step=60,
                key=f"mpesa_g2_completion_end_time_{completion_key}",
            )
        if default_completion_date < completion_times.max().date():
            st.caption(
                "La derniere journee complete est proposee; la journee la plus "
                "recente semble encore partielle."
            )
        period_start = pd.Timestamp.combine(date_start, time_start)
        period_end = pd.Timestamp.combine(date_end, time_end)
        if period_start > period_end:
            st.warning("La date et l'heure de debut doivent etre anterieures ou egales a la date et l'heure de fin.")
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
            ("Operations analytiques [Turbo]", _format_count(len(daily_detail)), "Une occurrence par operation", "blue"),
            ("Operations comptabilisees [Turbo]", _format_count(completed_count), "Incluses dans les analyses", "green"),
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
            st.dataframe(status_view, width="stretch", hide_index=True)
            if source_label == "Turbo":
                st.caption(
                    "Les operations comptabilisees dans Turbo alimentent les analyses. Aucun statut G2 n'est deduit."
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
            "`created_at` fournit la date et l'heure de l'operation. Les operations Turbo chargees sont considerees comptabilisees.",
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
        st.dataframe(flow_view, width="stretch", hide_index=True)
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
            st.dataframe(classified_summary, width="stretch", hide_index=True)

        with st.expander("Afficher la synthese detaillee en colonnes", expanded=False):
            st.dataframe(daily_pivot, width="stretch", hide_index=True)

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
        st.dataframe(daily_view[detail_columns], width="stretch", hide_index=True)

    if daily_anomalies.empty:
        if source_label == "Turbo":
            st.success("Aucune anomalie interne Turbo detectee dans le perimetre analyse.")
        else:
            st.success("Aucune anomalie de rapprochement detectee dans le perimetre analyse.")
    else:
        st.warning(
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
            st.dataframe(daily_anomalies[anomaly_columns], width="stretch", hide_index=True)

    turbo_only = source_label == "Turbo"
    render_panel_title(
        "6. Controle Turbo / DAT" if turbo_only else "6. Controle de rapprochement G2 / DAT"
    )
    if turbo_only:
        control_rules = [
            "Les depots sont regroupes par `ref_no` dans Transactions M-PESA_Turbo afin de ne pas compter deux fois les ecritures miroir.",
            "`NORMAL SAVINGS` + `Epargne depot` constitue un depot normal; `FIXED SAVINGS` + `Depot Bloque` constitue un DAT.",
            "Les sorties `Retrait Vers M-Pesa` sont regroupees par `reference_id` et `created_at`.",
            "Les dates utilisent `created_at` Turbo. Les controles independants G2/Turbo, le statut G2 et le nom issu de `Opposite Party` sont non applicables sans fichier G2.",
            "Si un fichier Transactions M-PESA_G2 est charge, il redevient automatiquement la source principale du rapport.",
        ]
    else:
        control_rules = [
            "`Receipt No.` G2 est rapproche en priorite avec `ref_no` du fichier Transactions M-PESA_Turbo.",
            "Pour une sortie `BisouBisouB2C` sans `ref_no`, le repli exige le meme telephone, la meme devise, le meme montant, une heure proche et le libelle Turbo `Retrait Vers M-Pesa`.",
            "Le telephone extrait de `Opposite Party`, la devise et le montant servent de controles independants.",
            "La date de creation compare `Initiation Time` G2 a `created_at` Turbo; `Completion Time` mesure la finalisation et le delai de traitement.",
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
                    f"{excluded_control_count} operation(s) Turbo exclue(s) du controle selon le perimetre analytique."
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
            date_start=date_start,
            date_end=date_end,
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
            ("Operations Turbo", _format_count(len(g2_dat)), "Entrees analysees", "blue"),
            ("DAT operation", _format_count(dat_operation_count), "Lignes FIXED SAVINGS via ref_no", "green"),
            ("Mode Turbo seul", _format_count(len(g2_dat)), "Controles G2/Turbo non applicables", "navy"),
            ("Anomalies internes", _format_count(anomaly_count), "Coherence des donnees Turbo/DAT", "orange"),
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
        "Afficher le detail du controle Turbo / DAT"
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
        st.dataframe(filtered_display, width="stretch", hide_index=True)

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
        date_start=date_start,
        date_end=date_end,
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
            "La population regroupe les telephones observes dans le dataset unifie Turbo + G2; une ligne de synthese correspond a un telephone client.",
            "`Phone_Prefixe` est la cle de rapprochement avec le fichier Clients_Perfect (export 122).",
            "La vue G2 utilise uniquement les clients observes dans Transactions M-PESA_G2.",
            "Les trois vues montrent Clients_Perfect dans G2, Clients_Perfect dans Turbo, puis l'intersection Clients_Perfect + Turbo + G2.",
            "Les operations proviennent de Turbo/G2 : Clients_Perfect contient l'identite du client, pas ses operations financieres.",
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
        st.info("Chargez au moins un fichier Turbo ou Transactions M-PESA_G2 pour constituer la population Turbo + G2 a rechercher dans Perfect.")
        return
    if prepared.perfect_clients.empty:
        st.warning(
            "Le fichier Clients_Perfect n'est pas charge. La population Turbo + G2 reste visible, mais aucune correspondance avec Clients_Perfect ne peut etre confirmee."
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
                "Clients [Clients_Perfect x Turbo]",
                _format_count(perfect_identity_count(clients_perfect_dans_turbo)),
                f"{len(clients_perfect_dans_turbo)} telephone(s) Clients_Perfect/Turbo",
                "green",
            ),
            (
                "Clients [Clients_Perfect x Turbo x G2]",
                _format_count(perfect_identity_count(clients_perfect_dans_turbo_et_mpesa)),
                f"{len(clients_perfect_dans_turbo_et_mpesa)} telephone(s) dans les 3 systemes",
                "navy",
            ),
        ]
    )
    st.caption(
        f"Qualite du rapprochement : {not_found} telephone(s) Turbo/G2 non trouve(s) dans Clients_Perfect, "
        f"{ambiguous} numero(s) partage(s) et {invalid_phone} telephone(s) inexploitable(s)."
    )

    render_panel_title("1. Fiches Clients_Perfect retrouvees dans G2 et Turbo")
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
    cohort_tabs = st.tabs(
        ["Clients_Perfect x G2", "Clients_Perfect x Turbo", "Clients_Perfect x Turbo x G2"]
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
            "Fiches Clients_Perfect dont le Phone_Prefixe est observe dans au moins une source Turbo.",
        ),
        (
            cohort_tabs[2],
            clients_perfect_dans_turbo_et_mpesa,
            "Fiches Clients_Perfect dont le Phone_Prefixe est observe a la fois dans G2 et Turbo.",
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
                st.dataframe(cohort_display, width="stretch", hide_index=True)

    render_panel_title("2. Clients transactionnels [Turbo + G2] recherches dans Clients_Perfect")
    search_value = st.text_input(
        "Rechercher par telephone, Customer ID ou nom",
        key="mpesa_perfect_client_search",
        placeholder="Ex. 243..., Customer ID, nom Turbo/G2 ou nom Perfect",
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
    st.dataframe(summary_display, width="stretch", hide_index=True)
    st.caption(
        "Une correspondance multiple signifie que le meme Phone_Prefixe est rattache a plusieurs fiches Perfect; "
        "toutes les identites restent visibles dans la ligne."
    )

    render_panel_title("3. Operations observees dans Turbo et G2")
    if operations.empty:
        st.info("Aucune operation Turbo/G2 exploitable n'est disponible.")
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
                "noms_clients_mpesa": "Nom_client_Turbo_G2",
                "noms_clients_perfect": "Nom_client_Clients_Perfect",
                "customer_ids_turbo": "Customer_ID_Turbo",
                "ids_clients_perfect": "ID_client_Clients_Perfect",
                "codes_clients_perfect": "Code_client_Clients_Perfect",
            }
        )
        st.caption(f"{len(operation_view)} operation(s) affichee(s). Les montants restent separes par source et par devise.")
        st.dataframe(operation_display, width="stretch", hide_index=True)

    render_panel_title("4. Export")
    export_bytes = _create_excel_export_cached(
        {
            "clients_perfect_dans_mpesa": clients_perfect_dans_mpesa,
            "clients_perfect_dans_turbo": clients_perfect_dans_turbo,
            "clients_perfect_dans_turbo_et_mpesa": clients_perfect_dans_turbo_et_mpesa,
        }
    )
    st.download_button(
        "Telecharger le rapprochement Turbo + G2 / Clients_Perfect",
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
            filtered[key] = value.loc[value["currency_code"].astype("string").isin(currencies)].reset_index(drop=True)
        else:
            filtered[key] = value
    return filtered


@st.fragment
def _render_management_dashboard(prepared: MpesaPreparedData) -> None:
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
        st.info("Chargez Transactions M-PESA_Turbo ou Transactions M-PESA_G2 pour construire le cockpit.")
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
            "Transformer les fichiers G2, Turbo, Credits, DAT et Perfect en controles directement actionnables.",
            "Chaque indicateur porte le suffixe [Turbo], [G2] ou [Turbo + G2] selon les transactions utilisees.",
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

    overview_tab, credit_tab, clients_tab, risk_tab = st.tabs(
        ["Vue direction", "Credit et liquidite", "Clients et epargne", "Risques et qualite"]
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
                ("Clients actifs 30j [Turbo + G2]", _format_count(active_clients), "Telephones distincts", "green"),
                ("Credits en retard 30j+ [Turbo]", _format_count(overdue_credits), "Dossiers a traiter", "red"),
                ("DAT echus ou a 30j [Turbo]", _format_count(dat_due_30), "Comptes a anticiper", "orange"),
                ("Alertes transactions [G2]", _format_count(len(alerts)), "Controle ou comportement", "navy"),
                ("Clients_Perfect actifs 30j [Turbo + G2]", _format_count(perfect_active), "Adoption consolidee", "blue"),
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
            st.dataframe(pd.DataFrame(priority_rows), width="stretch", hide_index=True)
        else:
            st.success("Aucune priorite credit/DAT calculable dans les fichiers charges.")

    with credit_tab:
        render_panel_title("1. Performance et risque des credits [Turbo]")
        credit_summary = report_view.get("credit_synthese", pd.DataFrame())
        credit_detail = report_view.get("credit_detail", pd.DataFrame())
        if credit_summary.empty:
            st.info("Chargez le fichier Credits Turbo pour calculer l'encours, les retards et le PAR.")
        else:
            st.dataframe(credit_summary, width="stretch", hide_index=True)
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
                    st.dataframe(credit_view, width="stretch", hide_index=True)

        render_panel_title("2. Liquidite [G2]")
        liquidity_summary = report_view.get("liquidite_synthese", pd.DataFrame())
        liquidity_daily = report_view.get("liquidite_journaliere", pd.DataFrame())
        if liquidity_summary.empty:
            st.info("Chargez Transactions G2 avec Completion Time et montants pour analyser la liquidite.")
        else:
            st.dataframe(liquidity_summary, width="stretch", hide_index=True)
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
                    st.dataframe(liquidity_daily, width="stretch", hide_index=True)

    with clients_tab:
        render_panel_title("1. Activite, dormance et reactivation [Turbo + G2]")
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
                st.dataframe(activity_view, width="stretch", hide_index=True)

        render_panel_title("2. Conversion depot normal vers DAT [G2]")
        conversion_summary = report_view.get("conversion_synthese", pd.DataFrame())
        conversion_clients = report_view.get("conversion_clients", pd.DataFrame())
        if conversion_summary.empty:
            st.info("La conversion exige des operations G2 classees Depot normal et DAT.")
        else:
            st.dataframe(conversion_summary, width="stretch", hide_index=True)
            st.caption("La conversion est observee dans la periode chargee; elle ne prouve pas l'affectation exacte d'un depot a un DAT.")
            with st.expander("Afficher le detail client de la conversion", expanded=False):
                st.dataframe(conversion_clients, width="stretch", hide_index=True)

        render_panel_title("3. Adoption globale [Turbo + G2] des Clients_Perfect")
        perfect_summary = report_view.get("perfect_adoption_synthese", pd.DataFrame())
        perfect_statuses = report_view.get("perfect_adoption_statuts", pd.DataFrame())
        perfect_detail = report_view.get("perfect_adoption_detail", pd.DataFrame())
        if perfect_summary.empty:
            st.info("Chargez Clients_Perfect pour mesurer l'adoption Turbo + G2 sur les Phone_Prefixe valides.")
        else:
            perfect_summary_display = perfect_summary.rename(
                columns={
                    "clients_perfect_dans_mpesa": "clients_perfect_dans_turbo_g2",
                    "taux_adoption_mpesa_pct": "taux_adoption_turbo_g2_pct",
                }
            )
            st.dataframe(perfect_summary_display, width="stretch", hide_index=True)
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
                st.dataframe(perfect_detail_display, width="stretch", hide_index=True)

    with risk_tab:
        render_panel_title("1. Concentration des transactions [G2]")
        concentration_summary = report_view.get("concentration_synthese", pd.DataFrame())
        concentration_clients = report_view.get("concentration_clients", pd.DataFrame())
        if concentration_summary.empty:
            st.info("Aucun telephone G2 valide ne permet de mesurer la concentration.")
        else:
            st.dataframe(concentration_summary, width="stretch", hide_index=True)
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
                st.dataframe(concentration_clients, width="stretch", hide_index=True)

        render_panel_title("2. Qualite et alertes transactions [G2]")
        quality_summary = report_view.get("qualite_synthese", pd.DataFrame())
        alerts = report_view.get("alertes_transactions", pd.DataFrame())
        if quality_summary.empty:
            st.info("Chargez Transactions G2 pour calculer les taux de succes, d'anomalie et de qualite.")
        else:
            st.dataframe(quality_summary, width="stretch", hide_index=True)
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
                st.caption("Une alerte comportementale est un signal de revue, pas une preuve de fraude.")
                st.dataframe(behavioral_alerts, width="stretch", hide_index=True)

        render_panel_title("3. Echeancier DAT - risque d'echeance [Turbo]")
        dat_summary = report_view.get("dat_echeances_synthese", pd.DataFrame())
        dat_detail = report_view.get("dat_echeances_detail", pd.DataFrame())
        if dat_summary.empty:
            st.info("Chargez Savings Account [Turbo] avec maturity_date pour construire l'echeancier.")
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
                st.dataframe(dat_detail, width="stretch", hide_index=True)

    render_panel_title("Export cible du cockpit [Turbo + G2]")
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
            export_bytes = _create_excel_export_cached(export_report)
        st.download_button(
            "Telecharger le cockpit Turbo + G2",
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
    if report is not None:
        render_panel_title("Credits du client [Turbo]")
        credits_view = _apply_local_multiselect_filters(
            report["credits"],
            ["currency_code", "status_name", "loan_id"],
            key_prefix="mpesa_client_loans_filter",
        )
        st.caption(f"{len(credits_view)} credit(s) affiche(s).")
        st.dataframe(credits_view, width="stretch", hide_index=True)
        return
    if prepared.loans.empty:
        st.info("Le fichier Credits est facultatif. Chargez-le pour enrichir l'extrait avec les informations LN.")
        return

    reconciliation = _build_loan_savings_reconciliation_cached(prepared)
    summary = reconciliation.get("synthese", pd.DataFrame())
    clients = reconciliation.get("clients", pd.DataFrame())
    loan_detail = reconciliation.get("detail", pd.DataFrame())
    controls = reconciliation.get("controles", pd.DataFrame())
    sources = reconciliation.get("sources", pd.DataFrame())
    source_row = sources.iloc[0] if not sources.empty else pd.Series(dtype="object")
    current_available = bool(source_row.get("savings_account_courant_disponible", False))
    fixed_available = bool(source_row.get("dat_disponible", False))
    source_complete = bool(source_row.get("source_savings_account_complete", False))

    render_panel_title("Vue consolidee credit et epargne [Turbo]")
    render_summary_box(
        "Perimetre du rapprochement",
        [
            "Le grain de la vue est customer_id x devise; CDF et USD restent strictement separes.",
            "Une liaison directe utilise savings_account_id lorsqu'il retrouve id ou savings_id dans le compte courant.",
            "Sinon, savings_id est deduit seulement lorsqu'un compte courant unique partage le client et la devise.",
            "Les positions d'epargne, de DAT et de credit sont juxtaposees; elles ne sont jamais compensees comptablement.",
        ],
    )
    if not current_available:
        st.info(
            "Chargez Savings Account [Turbo] avec Loans Account [Turbo] pour rapprocher les credits "
            "des comptes courants. Le fichier Loans reste exploitable ci-dessous sans ce controle."
        )
    else:
        if not source_complete:
            st.warning(
                "Le rapprochement utilise les syntheses Current/Fixed en mode de compatibilite. "
                "Les comptes a solde nul et l'historique exhaustif ne sont pas disponibles."
            )
        if not fixed_available:
            st.info(
                "Aucun DAT n'est disponible : la vue consolidee presente le credit et l'epargne "
                "courante; les colonnes DAT restent a zero."
            )
        direct_ids = int(source_row.get("savings_account_id_renseignes", 0))
        if direct_ids == 0:
            st.caption(
                "Dans Loans Account, savings_account_id n'est pas renseigne. Les correspondances conformes "
                "affichees comme deduites reposent sur customer_id + devise et un compte courant unique."
            )

    currency_options = (
        sorted(summary["currency_code"].dropna().astype(str).unique())
        if not summary.empty and "currency_code" in summary.columns
        else []
    )
    selected_currencies = st.multiselect(
        "Devises affichees dans la vue consolidee",
        options=currency_options,
        default=currency_options,
        key="mpesa_loan_savings_currencies",
        help="Une selection vide conserve toutes les devises. Les montants ne sont jamais additionnes entre devises.",
    )
    active_currencies = selected_currencies or currency_options
    summary_view = (
        summary.loc[summary["currency_code"].astype(str).isin(active_currencies)].copy()
        if active_currencies and not summary.empty
        else summary.copy()
    )
    clients_view = (
        clients.loc[clients["currency_code"].astype(str).isin(active_currencies)].copy()
        if active_currencies and not clients.empty
        else clients.copy()
    )
    controls_view = (
        controls.loc[controls["currency_code"].astype(str).isin(active_currencies)].copy()
        if active_currencies and not controls.empty
        else controls.copy()
    )
    detail_view = (
        loan_detail.loc[loan_detail["currency_code"].astype(str).isin(active_currencies)].copy()
        if active_currencies and not loan_detail.empty
        else loan_detail.copy()
    )

    if current_available and not summary_view.empty:
        for _, row in summary_view.sort_values("currency_code").iterrows():
            currency = str(row.get("currency_code", "")) or "NON RENSEIGNEE"
            render_panel_title(f"Position consolidee {currency} [Turbo]")
            match_rate = pd.to_numeric(
                pd.Series([row.get("taux_rapprochement_pct")]), errors="coerce"
            ).iloc[0]
            render_kpi_cards(
                [
                    (
                        "Credits rapproches [Turbo]",
                        f"{_format_count(row.get('credits_rapproches', 0))} / {_format_count(row.get('nombre_credits', 0))}",
                        "Correspondances directes ou deduites conformes",
                        "green",
                    ),
                    (
                        "Taux de rapprochement [Turbo]",
                        f"{float(match_rate):.2f}%" if pd.notna(match_rate) else "Non calculable",
                        "Denominateur : credits de la devise",
                        "blue",
                    ),
                    (
                        "Encours credit [Turbo]",
                        f"{_format_amount(row.get('encours_credit', 0))} {currency}",
                        "Loans Account",
                        "navy",
                    ),
                    (
                        "Epargne courante clients credites [Turbo]",
                        f"{_format_amount(row.get('solde_epargne_courante_clients_credit', 0))} {currency}",
                        "Comptee une fois par client et devise",
                        "orange",
                    ),
                    (
                        "DAT positifs clients credites [Turbo]",
                        f"{_format_amount(row.get('solde_dat_clients_credit', 0))} {currency}",
                        "Position observee, sans compensation",
                        "red",
                    ),
                ]
            )
        st.dataframe(
            summary_view,
            width="stretch",
            hide_index=True,
            column_config={
                "currency_code": st.column_config.TextColumn("Devise", pinned=True),
                "taux_rapprochement_pct": st.column_config.NumberColumn(
                    "Taux de rapprochement", format="%.2f%%"
                ),
                "montant_credits": st.column_config.NumberColumn(format="%.2f"),
                "montant_rembourse": st.column_config.NumberColumn(format="%.2f"),
                "encours_credit": st.column_config.NumberColumn(format="%.2f"),
                "solde_epargne_courante_clients_credit": st.column_config.NumberColumn(format="%.2f"),
                "solde_dat_clients_credit": st.column_config.NumberColumn(format="%.2f"),
                "epargne_totale_clients_credit": st.column_config.NumberColumn(format="%.2f"),
                "interpretation": None,
            },
        )

        render_panel_title("Positions par client et devise [Turbo]")
        filter_left, filter_right = st.columns([1, 2], gap="medium")
        with filter_left:
            status_options = sorted(
                clients_view.get("statut_rapprochement", pd.Series(dtype="string"))
                .dropna()
                .astype(str)
                .unique()
            )
            selected_statuses = st.multiselect(
                "Statuts de rapprochement",
                options=status_options,
                default=status_options,
                key="mpesa_loan_savings_statuses",
            )
        with filter_right:
            client_query = st.text_input(
                "Rechercher un client, telephone, nom ou savings_id",
                key="mpesa_loan_savings_client_query",
                placeholder="Ex. customer_id, 243..., nom ou SAV-...",
            ).strip()
        if selected_statuses:
            clients_view = clients_view.loc[
                clients_view["statut_rapprochement"].astype(str).isin(selected_statuses)
            ].copy()
        if client_query:
            searchable_columns = [
                column
                for column in [
                    "customer_id",
                    "Nom_client",
                    "customer",
                    "telephone_credit",
                    "telephone_epargne",
                    "savings_id_correspondant",
                    "loan_ids",
                ]
                if column in clients_view.columns
            ]
            search_mask = pd.Series(False, index=clients_view.index)
            for column in searchable_columns:
                search_mask |= clients_view[column].astype("string").str.contains(
                    client_query, case=False, na=False, regex=False
                )
            clients_view = clients_view.loc[search_mask].copy()
        client_columns = [
            "customer_id",
            "Nom_client",
            "customer",
            "telephone_credit",
            "currency_code",
            "nombre_credits",
            "loan_ids",
            "statuts_credit",
            "montant_credits",
            "montant_rembourse",
            "encours_credit",
            "principal_restant",
            "interets_restants",
            "penalites_restantes",
            "savings_id_correspondant",
            "solde_epargne_courante",
            "nb_dat_positifs",
            "solde_dat_positif",
            "epargne_totale_observee",
            "statut_rapprochement",
            "motifs_controle",
        ]
        client_columns = [column for column in client_columns if column in clients_view.columns]
        st.caption(
            f"{len(clients_view)} position(s) client x devise affichee(s). "
            "Epargne totale observee = epargne courante + DAT positifs de la meme devise."
        )
        st.dataframe(
            clients_view[client_columns],
            width="stretch",
            height=500,
            hide_index=True,
            column_config={
                "customer_id": st.column_config.TextColumn("Client", pinned=True),
                "currency_code": st.column_config.TextColumn("Devise", pinned=True),
                "montant_credits": st.column_config.NumberColumn(format="%.2f"),
                "montant_rembourse": st.column_config.NumberColumn(format="%.2f"),
                "encours_credit": st.column_config.NumberColumn(format="%.2f"),
                "principal_restant": st.column_config.NumberColumn(format="%.2f"),
                "interets_restants": st.column_config.NumberColumn(format="%.2f"),
                "penalites_restantes": st.column_config.NumberColumn(format="%.2f"),
                "solde_epargne_courante": st.column_config.NumberColumn(format="%.2f"),
                "solde_dat_positif": st.column_config.NumberColumn(format="%.2f"),
                "epargne_totale_observee": st.column_config.NumberColumn(format="%.2f"),
            },
        )

        render_panel_title("Controles credit / epargne [Turbo]")
        if controls_view.empty:
            st.success("Aucune correspondance credit / compte courant a revoir dans les devises affichees.")
        else:
            st.warning(
                f"{len(controls_view)} credit(s) a revoir : absence ou ambiguite du compte courant, "
                "identifiant direct non retrouve, ou ecart de telephone/client/devise."
            )
            control_columns = [
                "loan_id",
                "customer_id",
                "telephone_credit",
                "currency_code",
                "encours_credit",
                "savings_account_id_source",
                "savings_id_correspondant",
                "telephone_epargne",
                "nb_comptes_courants_candidats",
                "methode_rapprochement_epargne",
                "motif_controle",
            ]
            control_columns = [column for column in control_columns if column in controls_view.columns]
            st.dataframe(
                controls_view[control_columns],
                width="stretch",
                hide_index=True,
                column_config={
                    "loan_id": st.column_config.TextColumn("Credit", pinned=True),
                    "currency_code": st.column_config.TextColumn("Devise", pinned=True),
                    "encours_credit": st.column_config.NumberColumn(format="%.2f"),
                },
            )

        export_report = {
            "loan_savings_summary": summary_view,
            "loan_savings_clients": clients_view,
            "loan_savings_detail": detail_view,
            "loan_savings_controls": controls_view,
        }
        if st.button(
            "Preparer l'export credit / epargne",
            key="mpesa_prepare_loan_savings_export",
            width="content",
        ):
            with st.spinner("Preparation des positions et controles..."):
                export_bytes = _create_excel_export_cached(export_report)
            st.download_button(
                "Telecharger le controle credit / epargne",
                data=export_bytes,
                file_name="controle_credit_epargne_turbo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="mpesa_download_loan_savings_export",
                width="content",
            )

    with st.expander("Afficher les credits importes [Turbo]", expanded=not current_available):
        columns = [column for column in LOAN_USEFUL_COLUMNS if column in prepared.loans.columns]
        loans_base = prepared.loans[columns] if columns else prepared.loans
        loans_view = _apply_local_multiselect_filters(
            loans_base,
            ["currency_code", "status_name", "customer_id"],
            key_prefix="mpesa_import_loans_filter",
        )
        st.caption(f"{len(loans_view)} credit(s) affiche(s); le tableau est limite aux 500 premieres lignes.")
        st.dataframe(loans_view.head(500), width="stretch", hide_index=True)


@st.fragment
def _render_accounting_tab(prepared: MpesaPreparedData) -> None:
    if prepared.transactions.empty or "created_at" not in prepared.transactions.columns:
        st.info(
            "Chargez Transactions M-PESA_Turbo pour construire la balance auxiliaire et les analyses comptables."
        )
        return

    transaction_dates = pd.to_datetime(prepared.transactions["created_at"], errors="coerce").dropna()
    if transaction_dates.empty:
        st.warning("Aucune date Turbo exploitable pour construire la periode comptable.")
        return
    minimum_date = transaction_dates.min().date()
    maximum_date = transaction_dates.max().date()
    default_date = maximum_date
    if minimum_date < maximum_date and transaction_dates.max().hour < 18:
        previous_date = (pd.Timestamp(maximum_date) - pd.Timedelta(days=1)).date()
        if previous_date >= minimum_date:
            default_date = previous_date

    render_panel_title("Comptabilité financière observée [Turbo]")
    render_summary_box(
        "Perimetre et methode",
        [
            "Transactions M-PESA_Turbo fournit toutes les ecritures, les montants et les soldes observes.",
            "G2 complete le nom du client et mesure le rapprochement Receipt No = ref_no; ses montants ne remplacent jamais Turbo.",
            "La balance auxiliaire retient NORMAL SAVINGS, FIXED SAVINGS et PRINCIPLE. Les comptes techniques restent dans la balance des mouvements.",
            "CDF et USD sont calcules et presentes separement.",
        ],
    )
    selected_period = st.date_input(
        "Periode comptable [Turbo]",
        value=(default_date, default_date),
        min_value=minimum_date,
        max_value=maximum_date,
        key="mpesa_accounting_period",
        help=(
            "La derniere journee complete connue est proposee lorsque le fichier contient "
            "une journee d'extraction encore partielle."
        ),
    )
    if isinstance(selected_period, (tuple, list)) and len(selected_period) == 2:
        date_start, date_end = selected_period
    elif isinstance(selected_period, (tuple, list)) and len(selected_period) == 1:
        date_start = date_end = selected_period[0]
    else:
        date_start = date_end = selected_period

    report = _build_mpesa_accounting_analysis_cached(prepared, date_start, date_end)
    summary = report["synthese"]
    if summary.empty:
        st.info("Aucune ecriture Turbo sur la periode selectionnee.")
        return

    st.warning(
        "Cette restitution est une balance observee des sous-registres Turbo. Elle ne remplace pas "
        "la balance generale officielle de Perfect Vision : le plan comptable complet et les soldes "
        "d'ouverture certifies ne figurent pas dans cet export."
    )
    for _, row in summary.iterrows():
        currency = str(row["currency_code"])
        render_panel_title(f"Synthese comptable [Turbo] - {currency}")
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
                ("Total debit", _format_amount(row["total_debit"]), "Mouvements bruts Turbo", "slate"),
                ("Total credit", _format_amount(row["total_credit"]), "Mouvements bruts Turbo", "slate"),
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

    render_panel_title("Balance par client [Turbo]")
    st.caption(
        "Les debits et credits couvrent toutes les lignes Turbo du client. Les colonnes de position "
        "reprennent uniquement les derniers soldes observes des comptes produits actifs dans la periode."
    )
    balance_clients = report["balance_clients"]
    client_view = _apply_local_multiselect_filters(
        balance_clients,
        ["currency_code", "Nom_client", "customer_id"],
        key_prefix="mpesa_accounting_client_balance_filter",
    )
    client_columns = [
        "customer_id", "Nom_client", "telephone", "currency_code", "nombre_operations",
        "nombre_lignes", "total_debit", "total_credit", "solde_debiteur_mouvement",
        "solde_crediteur_mouvement", "solde_epargne_courante_observe", "solde_dat_observe",
        "avoirs_epargne_observes", "encours_principal_observe", "operations_a_verifier",
        "premiere_ecriture", "derniere_ecriture",
    ]
    client_columns = [column for column in client_columns if column in client_view.columns]
    st.caption(f"{len(client_view)} ligne(s) client x devise affichee(s).")
    st.dataframe(client_view[client_columns], width="stretch", hide_index=True)

    with st.expander("Afficher la balance auxiliaire detaillee par produit [Turbo]", expanded=False):
        auxiliary = report["balance_auxiliaire_clients"]
        if auxiliary.empty:
            st.info("Aucun compte produit actif sur la periode.")
        else:
            auxiliary_view = _apply_local_multiselect_filters(
                auxiliary,
                ["currency_code", "famille_position", "nature_comptable_indicative", "customer_id"],
                key_prefix="mpesa_accounting_auxiliary_filter",
            )
            st.dataframe(auxiliary_view, width="stretch", hide_index=True)

    render_panel_title("Balance des mouvements par type de compte [Turbo]")
    st.caption(
        "Ce tableau conserve tous les sous-registres Turbo. Les soldes debiteur et crediteur sont des "
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
                "account_type": "Type de compte Turbo",
                "montant": f"Montant ({currency})",
                "sens_comptable": "Mouvement",
            },
        )
        style_standard_vertical_bar(fig, height=390, tickangle=-35)
        st_plot(fig, key=f"mpesa_account_balance_{currency}", height=390)
    st.dataframe(account_balance, width="stretch", hide_index=True)

    render_panel_title("Flux et produits financiers observes [Turbo]")
    flow_column, products_column = st.columns(2, gap="small")
    with flow_column:
        st.markdown("**Flux du compte MPESA ACCOUNT**")
        st.caption(
            "Dans la restitution Bisou Bisou, le debit technique du MPESA ACCOUNT devient une entree "
            "et le credit technique une sortie."
        )
        st.dataframe(report["flux_mpesa"], width="stretch", hide_index=True)
    with products_column:
        st.markdown("**Produits et repartitions observes**")
        st.caption(
            "Les lignes Interets, Penalites, Part Bisou et Part Voda sont presentees separement; "
            "elles ne sont pas additionnees pour eviter de compter deux fois une meme ventilation."
        )
        st.dataframe(report["produits_financiers"], width="stretch", hide_index=True)

    render_panel_title("Positions de portefeuille des fichiers de reference [Turbo]")
    portfolio = report["positions_portefeuille"]
    if portfolio.empty:
        st.info("Chargez Epargne courante, DAT et Credits pour comparer les positions de portefeuille.")
    else:
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
        st.dataframe(portfolio, width="stretch", hide_index=True)

    render_panel_title("Controle secondaire Transactions M-PESA_G2")
    g2_control = report["controle_g2"]
    if prepared.g2_transactions.empty:
        st.info("G2 n'est pas charge. Les balances et mouvements Turbo restent disponibles sans nom ni controle G2.")
    else:
        st.caption(
            "Le taux de rapprochement compare uniquement les transactions G2 terminees de la periode "
            "avec ref_no Turbo. Un fichier G2 limite au compte 1441 ne couvre pas les sorties 15558."
        )
        st.dataframe(g2_control, width="stretch", hide_index=True)

    render_panel_title("Journal et controles comptables [Turbo]")
    control_count = len(report["controles_operations"]) + len(report["controles_soldes"])
    render_kpi_cards(
        [
            ("Operations a verifier", _format_count(len(report["controles_operations"])), "Symetrie debit / credit", "orange"),
            ("Variations a verifier", _format_count(len(report["controles_soldes"])), "bal_before / bal_after", "orange"),
            ("Total signaux", _format_count(control_count), "Signaux de revue, pas preuves d'erreur", "slate"),
        ]
    )
    with st.expander("Afficher le journal des operations [Turbo]", expanded=False):
        operation_view = _apply_local_multiselect_filters(
            report["journal_operations"],
            ["currency_code", "statut_controle_operation", "customer_id"],
            key_prefix="mpesa_accounting_operation_journal_filter",
        )
        st.dataframe(operation_view, width="stretch", hide_index=True)
    with st.expander("Afficher les operations a verifier [Turbo]", expanded=False):
        st.dataframe(report["controles_operations"], width="stretch", hide_index=True)
    with st.expander("Afficher les variations de solde a verifier [Turbo]", expanded=False):
        st.dataframe(report["controles_soldes"], width="stretch", hide_index=True)
    with st.expander("Afficher le journal brut des ecritures [Turbo]", expanded=False):
        st.dataframe(report["journal_ecritures"], width="stretch", hide_index=True)

    render_panel_title("Export comptable [Turbo]")
    export_report = {
        "accounting_summary": report["synthese"],
        "accounting_client_balances": report["balance_clients"],
        "accounting_client_positions": report["balance_auxiliaire_clients"],
        "accounting_account_balance": report["balance_comptes"],
        "accounting_operation_journal": report["journal_operations"],
        "accounting_entry_journal": report["journal_ecritures"],
        "accounting_operation_controls": report["controles_operations"],
        "accounting_balance_controls": report["controles_soldes"],
        "accounting_cash_flow": report["flux_mpesa"],
        "accounting_financial_products": report["produits_financiers"],
        "accounting_portfolio_positions": report["positions_portefeuille"],
        "accounting_g2_controls": report["controle_g2"],
    }
    export_bytes = _create_excel_export_cached(export_report)
    start_token = pd.Timestamp(date_start).strftime("%Y%m%d")
    end_token = pd.Timestamp(date_end).strftime("%Y%m%d")
    st.download_button(
        "Telecharger les analyses comptables Turbo",
        data=export_bytes,
        file_name=f"analyses_comptables_turbo_{start_token}_{end_token}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="content",
        key=f"mpesa_accounting_export_{start_token}_{end_token}",
    )


@st.fragment
def _render_diagnostics_tab(prepared: MpesaPreparedData, report: dict[str, Any] | None) -> None:
    diagnostics = report["diagnostics"] if report is not None else build_diagnostics(prepared)
    diagnostics_view = _apply_local_multiselect_filters(
        diagnostics,
        ["statut", "controle"],
        key_prefix="mpesa_diagnostics_filter",
    )
    st.dataframe(diagnostics_view, width="stretch", hide_index=True)
    if not prepared.transactions.empty:
        tx = prepared.transactions
        anomaly_mask = pd.Series(False, index=tx.index)
        if "customer_id" in tx.columns:
            anomaly_mask = anomaly_mask | tx["customer_id"].astype("string").fillna("").eq("")
        if "currency_code" in tx.columns:
            anomaly_mask = anomaly_mask | tx["currency_code"].astype("string").fillna("").eq("")
        if {"dr", "cr"}.issubset(tx.columns):
            anomaly_mask = anomaly_mask | (
                pd.to_numeric(tx["dr"], errors="coerce").fillna(0).eq(0)
                & pd.to_numeric(tx["cr"], errors="coerce").fillna(0).eq(0)
            )
            anomaly_mask = anomaly_mask | (
                pd.to_numeric(tx["dr"], errors="coerce").fillna(0).gt(0)
                & pd.to_numeric(tx["cr"], errors="coerce").fillna(0).gt(0)
            )
        anomalies = tx.loc[anomaly_mask].head(1000)
        render_panel_title("Anomalies Transactions [Turbo]")
        st.dataframe(anomalies, width="stretch", hide_index=True)


def render_solution_mpesa_tab() -> None:
    render_panel_title("Solution M-PESA")
    render_summary_box(
        "Module independant",
        [
            "Cette solution M-PESA n'est pas encore connectee a Perfect Vision.",
            "Les analyses reposent uniquement sur les fichiers Excel televerses dans cet onglet.",
            "Les devises CDF et USD ne sont jamais additionnees dans l'extrait client.",
        ],
    )

    render_panel_title("Sources Turbo principales (4)")
    st.caption(
        "Transactions, Savings Account, Loans Account et Customers suffisent au parcours Turbo. "
        "Tous les emplacements acceptent plusieurs fichiers."
    )
    turbo_left, turbo_right = st.columns(2, gap="medium")
    with turbo_left:
        with st.container(border=True):
            transactions_file = st.file_uploader(
                "Transactions [Turbo]",
                type=["xlsx", "xls"],
                key="mpesa_transactions_file",
                accept_multiple_files=True,
                help="Chargez une ou plusieurs périodes. Les écritures sont dédupliquées par id; dr et cr conservent leur logique comptable Turbo.",
            )
        with st.container(border=True):
            savings_file = st.file_uploader(
                "Savings Account [Turbo]",
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
                "Loans Account [Turbo]",
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
                "Customers [Turbo]",
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
                "Transactions [G2] (facultatif)",
                type=["xlsx", "xls"],
                key="mpesa_g2_file",
                accept_multiple_files=True,
                help=(
                    "Chargez ensemble les relevés d'entrées 1441 et de sorties 15558. Sans G2, "
                    "les analyses encore démontrables utilisent uniquement Transactions Turbo."
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
        expected_transactions, expected_savings, expected_customers = st.columns(3, gap="small")
        with expected_transactions:
            st.markdown("**Transactions [Turbo]**")
            st.code(", ".join(sorted(TRANSACTION_REQUIRED_COLUMNS)), language="text")
            st.markdown("**Transactions [G2] (facultatif)**")
            st.code(", ".join(sorted(G2_TRANSACTION_REQUIRED_COLUMNS)), language="text")
        with expected_savings:
            st.markdown("**Savings Account [Turbo]**")
            st.code(
                "savings_id, customer_id, msisdn1, product_name, product_description, "
                "balance, currency_code, date_approved, maturity_date, created_at, updated_at",
                language="text",
            )
            st.caption(
                "Alternative compatible : sélectionner ensemble les exports résumés Customers with Current "
                "Savings Account et Customers with Fixed Savings Account. Cette alternative ne contient que "
                "les comptes à solde positif."
            )
        with expected_customers:
            st.markdown("**Loans Account [Turbo]**")
            st.code(
                "customer_id, loan_id, savings_account_id, msisdn1, currency_code, loan_amount, "
                "loan_balance, amount_paid, outstanding_principle, outstanding_interest, "
                "outstanding_penalty_fees, status_name, due_date",
                language="text",
            )
            st.markdown("**Customers [Turbo]**")
            st.code(", ".join(sorted(CUSTOMERS_REQUIRED_COLUMNS)), language="text")
            st.markdown("**Clients_Perfect**")
            st.code(", ".join(sorted(PERFECT_CLIENTS_REQUIRED_COLUMNS)), language="text")

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
    sub_tab_names = [
        "Importation",
        "Pilotage Turbo + G2",
        "Comptabilité Turbo",
        "Extrait client",
        "DAT",
        "G2 / DAT",
        "Perfect_client",
        "Detail des credits",
        "Controle des donnees",
    ]
    tabs_container_key = "mpesa_solution_tabs"
    inject_professional_tabs_css(container_key=tabs_container_key)
    tabs_container = st.container(key=tabs_container_key)
    sub_tabs = tabs_container.tabs(format_professional_tab_labels(sub_tab_names))
    with sub_tabs[0]:
        _render_import_tab(prepared, missing)
    with sub_tabs[1]:
        _render_management_dashboard(prepared)
    with sub_tabs[2]:
        _render_accounting_tab(prepared)
    with sub_tabs[3]:
        _render_customer_extract(prepared)
    with sub_tabs[4]:
        _render_dat_tab(None, prepared)
    with sub_tabs[5]:
        _render_g2_dat_tab(None, prepared)
    with sub_tabs[6]:
        _render_perfect_client_tab(prepared)
    with sub_tabs[7]:
        _render_loans_tab(None, prepared)
    with sub_tabs[8]:
        _render_diagnostics_tab(prepared, None)
