from __future__ import annotations

from dataclasses import replace
from datetime import time
from io import BytesIO
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.services.mpesa_analysis import (
    CURRENT_SAVINGS_REQUIRED_COLUMNS,
    CUSTOMERS_REQUIRED_COLUMNS,
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
    build_load_report,
    build_mpesa_statement,
    build_perfect_client_crosscheck,
    create_excel_export,
    create_g2_dat_word,
    enrich_transactions_with_g2_customer_names,
    enrich_turbo_with_g2_customer_names,
    filter_g2_transactions_by_completion_time,
    filter_g2_transactions_by_direction,
    numeric_column,
    prepare_current_savings,
    prepare_customers,
    prepare_fixed_savings,
    prepare_g2_transactions,
    prepare_loans,
    prepare_perfect_clients,
    prepare_transactions,
    search_customers,
    validate_required_columns,
)
from credit_app.ui import (
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


@st.cache_data(show_spinner=False)
def _read_excel_bytes(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    if not file_bytes:
        return pd.DataFrame()
    try:
        return pd.read_excel(BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Impossible de lire `{file_name}` : {exc}") from exc


def _uploaded_dataframe(uploaded_file: Any) -> pd.DataFrame:
    if uploaded_file is None:
        return pd.DataFrame()
    return _read_excel_bytes(uploaded_file.getvalue(), uploaded_file.name)


@st.cache_data(show_spinner=False)
def _create_excel_export_cached(export_report: dict[str, Any]) -> bytes:
    return create_excel_export(export_report)


@st.cache_data(show_spinner=False)
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


def _render_expected_columns(title: str, columns: set[str]) -> None:
    with st.expander(title, expanded=False):
        st.code(", ".join(sorted(columns)), language="text")


def _build_prepared_data(
    transactions_raw: pd.DataFrame,
    current_raw: pd.DataFrame,
    fixed_raw: pd.DataFrame,
    loans_raw: pd.DataFrame,
    g2_raw: pd.DataFrame,
    customers_raw: pd.DataFrame,
    perfect_raw: pd.DataFrame,
) -> tuple[MpesaPreparedData, dict[str, list[str]]]:
    missing = {
        "Transactions M-PESA_Turbo": validate_required_columns(transactions_raw, TRANSACTION_REQUIRED_COLUMNS, "Transactions M-PESA")
        if not transactions_raw.empty
        else sorted(TRANSACTION_REQUIRED_COLUMNS),
        "Epargne courante_Turbo": validate_required_columns(current_raw, CURRENT_SAVINGS_REQUIRED_COLUMNS, "Epargne courante")
        if not current_raw.empty
        else [],
        "DAT_Turbo": validate_required_columns(fixed_raw, FIXED_SAVINGS_REQUIRED_COLUMNS, "DAT")
        if not fixed_raw.empty
        else [],
        "Credits_Turbo": validate_required_columns(loans_raw, {"loan_id", "customer_id"}, "Credits") if not loans_raw.empty else [],
        "Transactions M-PESA_G2": validate_required_columns(g2_raw, G2_TRANSACTION_REQUIRED_COLUMNS, "Transactions M-PESA_G2") if not g2_raw.empty else [],
        "Clients_Turbo": validate_required_columns(customers_raw, CUSTOMERS_REQUIRED_COLUMNS, "Clients") if not customers_raw.empty else [],
        "Clients_Perfect": validate_required_columns(perfect_raw, PERFECT_CLIENTS_REQUIRED_COLUMNS, "Clients Perfect") if not perfect_raw.empty else [],
    }
    transactions = prepare_transactions(transactions_raw) if transactions_raw is not None and not transactions_raw.empty else pd.DataFrame()
    current = prepare_current_savings(current_raw)
    fixed = prepare_fixed_savings(fixed_raw)
    loans = prepare_loans(loans_raw)
    g2_transactions = prepare_g2_transactions(g2_raw)
    customers = prepare_customers(customers_raw)
    perfect_clients = prepare_perfect_clients(perfect_raw)
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
        transactions,
        current,
        fixed,
        loans,
        load_report,
        g2_transactions,
        customers,
        perfect_clients,
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
                ("Transactions", _format_count(len(prepared.transactions)), "Lignes M-PESA importees", "blue"),
                ("Clients", _format_count(clients), "Clients distincts", "navy"),
                ("Periode", _period_label(prepared.transactions), "Transactions", "green"),
                ("Devises", currencies, "Codes detectes", "orange"),
            ]
        )
    unnamed_count = sum(
        int(frame.columns.astype(str).str.match(r"^Unnamed(:|$)", na=False).sum())
        for frame in [prepared.transactions, prepared.current_savings, prepared.fixed_savings, prepared.loans]
        if not frame.empty
    )
    st.caption(f"Colonnes `Unnamed` restantes apres nettoyage : {unnamed_count}.")


def _filter_statement(statement: pd.DataFrame, *, key_prefix: str) -> pd.DataFrame:
    if statement.empty:
        return statement
    filtered = statement.copy()
    first_row, second_row = st.columns(2)
    currencies = _currency_options(filtered)
    selected_currency = "Toutes"
    if currencies:
        selected_currency = first_row.selectbox("Devise", ["Toutes"] + currencies, key=f"{key_prefix}_currency")
        if selected_currency != "Toutes":
            filtered = filtered.loc[filtered["currency_code"].eq(selected_currency)]
    operation_types = sorted(filtered["type_operation"].dropna().astype(str).unique()) if "type_operation" in filtered.columns else []
    if operation_types:
        selected_types = second_row.multiselect(
            "Type d'operation",
            operation_types,
            default=[],
            key=f"{key_prefix}_{selected_currency}_type",
            placeholder="Choose options",
            help="Aucune option choisie = tous les types d'operation.",
        )
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
                filtered = filtered.loc[
                    pd.to_datetime(filtered["created_at"], errors="coerce").between(
                        pd.Timestamp(start),
                        pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1),
                    )
                ]
    ref_query = second_row.text_input("Reference M-PESA, DAT ou credit", key=f"{key_prefix}_reference").strip()
    if ref_query:
        ref_columns = ["operation_reference", "reference_dat_operation", "reference_credit_operation", "references_internes"]
        mask = pd.Series(False, index=filtered.index)
        for column in ref_columns:
            if column in filtered.columns:
                mask = mask | filtered[column].astype("string").str.contains(ref_query, case=False, regex=False, na=False)
        filtered = filtered.loc[mask]
    return filtered.reset_index(drop=True)


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
                ("Operations", _format_count(row.get("nombre_operations_mpesa")), f"Devise {currency}", "blue"),
                ("Entrees", _format_amount(row.get("total_entrees_mpesa")), f"Devise {currency}", "green"),
                ("Sorties", _format_amount(row.get("total_sorties_mpesa")), f"Devise {currency}", "orange"),
                ("Net", _format_amount(row.get("mouvement_net")), f"Devise {currency}", "navy"),
                (
                    "Solde M-PESA final",
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
        render_panel_title("Mouvement net M-PESA")
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
            if "solde_mpesa_apres" in chart_df.columns and chart_df["solde_mpesa_apres"].notna().any():
                render_panel_title("Solde M-PESA")
                fig = px.line(chart_df.dropna(subset=["solde_mpesa_apres"]), x="created_at", y="solde_mpesa_apres", color="currency_code", markers=True)
                style_standard_line(fig, height=330, tickangle=-20)
                st_plot(fig, key="mpesa_balance", height=330)
            else:
                st.warning("Le solde d'ouverture M-PESA n'a pas ete fourni. Le graphique de solde reel n'est pas affiche.")
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


def _render_customer_extract(prepared: MpesaPreparedData) -> dict[str, Any] | None:
    if prepared.transactions.empty:
        st.info("Chargez au minimum le fichier Transactions M-PESA pour construire un extrait client.")
        return None

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

    currencies = _currency_options(prepared.transactions.loc[prepared.transactions["customer_id"].astype(str).eq(selected_customer)])
    opening_balances: dict[str, float | None] = {}
    with st.expander("Optionnel - renseigner les soldes d'ouverture M-PESA", expanded=False):
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
        report = build_mpesa_statement(prepared, selected_customer, opening_balances=opening_balances)
    except ValueError as exc:
        st.warning(str(exc))
        return None

    statement = report["extrait"]
    summary = report["synthese"]
    render_panel_title("3. Situation financiere par devise")
    _render_customer_kpis(summary)
    if statement["solde_mpesa_apres"].isna().all():
        st.warning(
            "Le solde d'ouverture M-PESA n'a pas ete fourni. Le resultat affiche est un cumul relatif et non le solde reel du portefeuille."
        )

    render_panel_title("4. Filtrer les mouvements")
    filtered_statement = _filter_statement(statement, key_prefix=f"mpesa_statement_{selected_customer}")
    st.caption(f"{len(filtered_statement)} operation(s) retenue(s) sur {len(statement)} pour le client.")
    filtered_report = dict(report)
    filtered_report["extrait"] = filtered_statement
    filtered_report["synthese"] = report["synthese"]

    render_panel_title("5. Evolution des mouvements filtres")
    _render_statement_charts(filtered_statement)

    render_panel_title("6. Extrait client")
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
        "descriptions",
        "controle_mouvement",
    ]
    statement_columns = [column for column in statement_columns if column in filtered_statement.columns]
    st.dataframe(filtered_statement[statement_columns], width="stretch", hide_index=True)
    with st.expander("Afficher toutes les colonnes techniques", expanded=False):
        st.dataframe(filtered_statement, width="stretch", hide_index=True)

    render_panel_title("7. Export")
    st.caption(
        "La feuille `Extrait_MPESA` reprend les filtres appliques a l'etape 4. "
        "Le classeur conserve uniquement la synthese, l'extrait, le DAT final, les credits, le controle G2/DAT et les diagnostics."
    )
    customer_export = {
        key: filtered_report.get(key, pd.DataFrame())
        for key in ["synthese", "extrait", "dat_final", "credits", "g2_dat", "diagnostics"]
    }
    export_bytes = _create_excel_export_cached(customer_export)
    st.download_button(
        "Telecharger le rapport complet du client",
        data=export_bytes,
        file_name=f"extrait_mpesa_dat_client_{selected_customer}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )
    return filtered_report


def _render_overview(prepared: MpesaPreparedData) -> None:
    if prepared.transactions.empty:
        st.info("Chargez le fichier Transactions M-PESA pour afficher la vue d'ensemble.")
        return
    tx = prepared.transactions
    clients = tx["customer_id"].dropna().astype(str).nunique() if "customer_id" in tx.columns else 0
    mpesa = tx.loc[tx["account_type"].eq("MPESA ACCOUNT")] if "account_type" in tx.columns else tx
    total_in = numeric_column(mpesa, "cr").sum()
    total_out = numeric_column(mpesa, "dr").sum()
    render_kpi_cards(
        [
            ("Lignes Transactions", _format_count(len(tx)), "Fichier M-PESA", "blue"),
            ("Clients", _format_count(clients), "Clients distincts", "navy"),
            ("Entrees", _format_amount(total_in), "Toutes devises, lecture brute", "green"),
            ("Sorties", _format_amount(total_out), "Toutes devises, lecture brute", "orange"),
        ]
    )
    render_summary_box(
        "Lecture",
        [
            "Les montants CDF et USD restent separes dans les extraits et KPI client.",
            "Cette vue globale sert uniquement de repere de chargement.",
            f"Periode disponible : {_period_label(tx)}.",
        ],
    )
    if "created_at" in tx.columns and "currency_code" in tx.columns:
        work = tx.copy()
        work["created_at"] = pd.to_datetime(work["created_at"], errors="coerce")
        work = work.dropna(subset=["created_at"])
        work["jour"] = work["created_at"].dt.date
        daily = work.groupby(["jour", "currency_code"], as_index=False).agg(dr=("dr", "sum"), cr=("cr", "sum"))
        long_daily = daily.melt(
            id_vars=["jour", "currency_code"],
            value_vars=["dr", "cr"],
            var_name="sens",
            value_name="montant",
        )
        fig = px.line(long_daily, x="jour", y="montant", color="sens", facet_row="currency_code", markers=True)
        style_standard_line(fig, height=360, tickangle=-20)
        st_plot(fig, key="mpesa_overview_daily", height=360)


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


def _render_dat_tab(report: dict[str, Any] | None, prepared: MpesaPreparedData) -> None:
    _render_large_dat_summary(prepared)
    if report is not None:
        render_panel_title("DAT final du client")
        dat_view = _apply_local_multiselect_filters(
            report["dat_final"],
            ["currency_code", "product_name", "account_type", "statut_dat"],
            key_prefix="mpesa_dat_final_filter",
        )
        st.caption(f"{len(dat_view)} ligne(s) DAT affichee(s).")
        st.dataframe(dat_view, width="stretch", hide_index=True)
        render_panel_title("Mouvements DAT reconstruits")
        dat_movements_view = _apply_local_multiselect_filters(
            report["mouvements_dat"],
            ["currency_code", "references", "descriptions"],
            key_prefix="mpesa_dat_movements_filter",
        )
        st.dataframe(dat_movements_view, width="stretch", hide_index=True)
    elif not prepared.fixed_savings.empty:
        render_panel_title("DAT importes")
        dat_view = _apply_local_multiselect_filters(
            prepared.fixed_savings,
            ["currency_code", "product_name", "account_type"],
            key_prefix="mpesa_dat_import_filter",
        )
        st.caption(f"{len(dat_view)} ligne(s) DAT affichee(s).")
        st.dataframe(dat_view.head(500), width="stretch", hide_index=True)
    else:
        st.info("Aucun fichier DAT charge.")
    st.caption("La reconstruction du DAT total depend de la coherence entre le fichier Transactions et le fichier Fixed Savings.")


def _render_g2_report_export(
    *,
    daily_pivot: pd.DataFrame,
    daily_comptages: pd.DataFrame,
    daily_synthese: pd.DataFrame,
    daily_detail: pd.DataFrame,
    daily_anomalies: pd.DataFrame,
    g2_dat: pd.DataFrame,
    retention_report: dict[str, pd.DataFrame],
    date_start: Any | None,
    date_end: Any | None,
    direction_suffix: str,
    period_text: str,
    direction_label: str,
) -> None:
    render_panel_title("6. Export du rapport")
    export_report = {
        "rapport_journalier_comptages": daily_comptages,
        "rapport_journalier_synthese": daily_synthese,
        "rapport_journalier_detail": daily_detail,
        "rapport_journalier_anomalies": daily_anomalies,
        "g2_dat": g2_dat,
        "retention_mensuelle": retention_report.get("mensuelle", pd.DataFrame()),
        "retention_detail": retention_report.get("detail_clients", pd.DataFrame()),
    }
    report_bytes = _create_excel_export_cached(export_report)
    word_report = dict(export_report)
    word_report["rapport_journalier_pivot"] = daily_pivot
    period_suffix = f"{date_start:%Y%m%d}_{date_end:%Y%m%d}" if date_start is not None and date_end is not None else "complet"
    excel_column, word_column = st.columns(2)
    with excel_column:
        st.download_button(
            "Telecharger le rapport Excel",
            data=report_bytes,
            file_name=f"rapport_g2_dat_{period_suffix}_{direction_suffix}.xlsx",
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
                file_name=f"rapport_g2_dat_{period_suffix}_{direction_suffix}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                width="stretch",
            )
    st.caption(
        "Le Word reprend le tableau Transactions dans le meme ordre sur une page paysage; "
        "l'Excel conserve uniquement les syntheses, comptages, details et controles indispensables."
    )


def _render_g2_retention_report(retention_report: dict[str, pd.DataFrame]) -> None:
    render_panel_title("3. Fidelisation des clients M-PESA")
    render_summary_box(
        "Definitions du rapport",
        [
            "La base mensuelle correspond aux telephones clients distincts ayant une operation G2 eligible, par devise.",
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
                    "Clients actifs",
                    _format_count(latest_base.get("clients_actifs_mois_base")),
                    f"Mois {latest_base.get('mois', '-')}",
                    "blue",
                ),
                (
                    "Retention M+1",
                    _format_percent(latest_m1.get("retention_m1_pct")) if latest_m1 is not None else "-",
                    f"Mois {latest_m1.get('mois')}" if latest_m1 is not None else "Fenetre incomplete",
                    "green",
                ),
                (
                    "Retention 90 jours",
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
    st.caption(
        "Les dimensions Agence, Groupe produit et Renouvellement de credit du PDF source ne sont pas presentes dans G2; "
        "elles ne sont pas estimees."
    )


def _render_g2_dat_tab(report: dict[str, Any] | None, prepared: MpesaPreparedData) -> None:
    if prepared.g2_transactions.empty:
        st.info("Aucun fichier Transactions G2 charge. Chargez `Transaction g2.xlsx` pour rapprocher les telephones G2 avec les DAT.")
        return

    completion_source = prepared.g2_transactions.get(
        "completion_time",
        pd.Series(pd.NaT, index=prepared.g2_transactions.index),
    )
    completion_times = pd.to_datetime(completion_source, errors="coerce").dropna()
    filtered_g2 = prepared.g2_transactions.copy()
    date_start = None
    date_end = None
    time_start = None
    time_end = None
    render_panel_title("1. Période analysée (Completion Time)")
    if not completion_times.empty:
        completion_key = f"{completion_times.min():%Y%m%d}_{completion_times.max():%Y%m%d}_{len(completion_times)}"
        date_columns = st.columns(2)
        with date_columns[0]:
            date_start = st.date_input(
                "Completion Time - date de debut",
                value=completion_times.min().date(),
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
                "Completion Time - date de fin",
                value=completion_times.max().date(),
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
        st.caption("Completion Time n'est pas disponible; l'ensemble du fichier G2 est analyse.")

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
    st.caption(f"{len(filtered_g2)} transaction(s) G2 retenue(s) {period_text} - {direction_label.lower()}.")
    if filtered_g2.empty:
        st.warning("Aucune transaction G2 ne correspond a la periode et au sens selectionnes.")
        return
    filtered_prepared = replace(prepared, g2_transactions=filtered_g2)

    daily_report = build_g2_daily_savings_report(filtered_prepared)
    daily_detail = daily_report.get("detail", pd.DataFrame())
    daily_pivot = daily_report.get("pivot", pd.DataFrame())
    daily_synthese = daily_report.get("synthese", pd.DataFrame())
    daily_comptages = daily_report.get("comptages", pd.DataFrame())
    daily_anomalies = daily_report.get("anomalies", pd.DataFrame())
    retention_report = build_g2_retention_report(filtered_prepared, daily_detail=daily_detail)

    render_summary_box(
        "Lecture unique du sous-onglet",
        [
            "Le sens repose sur les colonnes du releve : `Paid In` = entree et `Withdrawn` = sortie.",
            "Une seule ligne analytique est conservee par `Receipt No.` afin de ne pas compter deux fois une operation.",
            "La classification utilise d'abord `Receipt No. = ref_no`, puis `account_type` et `description` du portail; la regle G2 sert de repli.",
            "Les nombres, montants d'entree, montants de sortie et soldes nets sont presentes separement pour chaque devise.",
            "Le telephone, la devise, le montant et la date sont controles sans additionner les ecritures techniques du portail.",
        ],
    )

    render_panel_title("2. Synthese des flux G2 par devise")
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
                "montant_total_entrees": "Montant total des entrees",
                "nombre_sorties": "Nombre de sorties",
                "montant_total_sorties": "Montant total des sorties",
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
            render_panel_title("Repartition par type d'operation")
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

    _render_g2_retention_report(retention_report)

    render_panel_title("4. Transactions")
    with st.expander("Afficher le detail des transactions G2", expanded=False):
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
                "controle_telephone",
                "controle_devise",
                "controle_montant",
                "controle_date",
            ],
            key_prefix="mpesa_daily_g2_report_filter",
        )
        st.caption(f"{len(daily_view)} ligne(s) affichee(s).")
        detail_columns = G2_CLASSIFIED_TRANSACTION_COLUMNS
        detail_columns = [column for column in detail_columns if column in daily_view.columns]
        st.dataframe(daily_view[detail_columns], width="stretch", hide_index=True)

    if daily_anomalies.empty:
        st.success("Aucune anomalie de rapprochement detectee dans le perimetre analyse.")
    else:
        st.warning(
            f"{len(daily_anomalies)} operation(s) necessitent une verification. "
            "Elles sont conservees dans le detail et dans l'onglet Anomalies_G2 de l'export Excel."
        )
        with st.expander("Afficher les anomalies G2 / Portail", expanded=False):
            anomaly_columns = [
                "receipt_no",
                "completion_time",
                "currency_code",
                "transaction_amount_numeric",
                "opposite_party",
                "nombre_lignes_g2_reference",
                "devises_g2_reference",
                "statuts_g2_reference",
                "montants_g2_reference",
                "nombre_ecritures_portal",
                "statut_rapprochement",
                "controle_telephone",
                "controle_devise",
                "controle_montant",
                "controle_date",
                "motif_anomalie",
            ]
            anomaly_columns = [column for column in anomaly_columns if column in daily_anomalies.columns]
            st.dataframe(daily_anomalies[anomaly_columns], width="stretch", hide_index=True)

    render_panel_title("5. Controle de rapprochement G2 / DAT")
    render_summary_box(
        "Role du controle",
        [
            "`Receipt No.` est rapproche en priorite avec `ref_no` du fichier Transactions M-PESA.",
            "Le telephone extrait de `Opposite Party`, la devise, le montant et la date servent de controles independants.",
            "Les lignes non rapprochees et les ecarts restent visibles pour verification et export.",
        ],
    )

    if report is not None:
        g2_dat = report.get("g2_dat", pd.DataFrame())
        if date_start is not None or date_end is not None:
            g2_dat = filter_g2_transactions_by_completion_time(
                g2_dat,
                date_start,
                date_end,
                time_start,
                time_end,
            )
        st.caption("Controle limite au client selectionne dans l'onglet Extrait client.")
    else:
        g2_dat = build_g2_dat_crosscheck(filtered_prepared)

    if not g2_dat.empty and "sens_flux" in g2_dat.columns:
        g2_dat = g2_dat.loc[g2_dat["sens_flux"].astype("string").eq("Entree")].reset_index(drop=True)
        st.caption("Le controle DAT porte uniquement sur les entrees; les sorties restent dans l'analyse des flux ci-dessus.")

    if g2_dat.empty:
        st.info(
            "Le controle G2 / DAT ne contient aucune entree dans le perimetre courant. "
            "La synthese et l'export des sorties restent disponibles."
        )
        _render_g2_report_export(
            daily_pivot=daily_pivot,
            daily_comptages=daily_comptages,
            daily_synthese=daily_synthese,
            daily_detail=daily_detail,
            daily_anomalies=daily_anomalies,
            g2_dat=g2_dat,
            retention_report=retention_report,
            date_start=date_start,
            date_end=date_end,
            direction_suffix=direction_suffix,
            period_text=period_text,
            direction_label=direction_label,
        )
        return

    if "statut_rapprochement" in g2_dat.columns:
        reference_status = g2_dat["statut_rapprochement"].astype("string").fillna("")
        matched = int((reference_status.ne("") & reference_status.ne("Non rapproche")).sum())
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
    render_kpi_cards(
        [
            ("Transactions G2", _format_count(len(g2_dat)), "Lignes analysees", "blue"),
            ("DAT operation", _format_count(dat_operation_count), "Lignes FIXED SAVINGS via ref_no", "green"),
            ("Rapprochements exacts", _format_count(exact_matches), "Receipt No = ref_no et controles conformes", "navy"),
            ("Anomalies", _format_count(anomaly_count), f"Dont {len(g2_dat) - matched} non rapproche(s)", "orange"),
        ]
    )

    with st.expander("Afficher le detail du controle de rapprochement", expanded=False):
        filtered = _apply_local_multiselect_filters(
            g2_dat,
            [
                "currency_code",
                "statut_rapprochement",
                "controle_telephone",
                "controle_devise",
                "controle_montant",
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
            "completion_time",
            "currency_code",
            "transaction_amount",
            "opposite_party",
            "nombre_lignes_g2_reference",
            "nombre_ecritures_portal",
            "account_types_portal",
            "descriptions_portal",
            "statut_rapprochement",
            "controle_telephone",
            "controle_devise",
            "montant_portal_controle",
            "ecart_montant",
            "controle_montant",
            "ecart_date_minutes",
            "controle_date",
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
        daily_detail=daily_detail,
        daily_anomalies=daily_anomalies,
        g2_dat=g2_dat,
        retention_report=retention_report,
        date_start=date_start,
        date_end=date_end,
        direction_suffix=direction_suffix,
        period_text=period_text,
        direction_label=direction_label,
    )


def _render_perfect_client_tab(prepared: MpesaPreparedData) -> None:
    render_summary_box(
        "Lecture du rapprochement",
        [
            "La population regroupe les telephones observes dans le dataset unifie G2/Turbo; une ligne de synthese correspond a un telephone M-PESA.",
            "`Phone_Prefixe` est la cle de rapprochement avec l'export 122 Perfect.",
            "M_PESA designe ici les clients observes dans les transactions G2.",
            "Les trois vues montrent Perfect dans M_PESA, Perfect dans Turbo, puis l'intersection Perfect + Turbo + M_PESA.",
            "Les operations proviennent de Turbo/G2 : le fichier Perfect fourni contient l'identite du client, pas ses operations financieres.",
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
        st.info("Chargez au moins un fichier Turbo ou Transactions G2 pour constituer la population M-PESA a rechercher dans Perfect.")
        return
    if prepared.perfect_clients.empty:
        st.warning(
            "Le fichier Clients Perfect n'est pas charge. La population M-PESA reste visible, mais aucune correspondance Perfect ne peut etre confirmee."
        )
    else:
        valid_perfect = int(prepared.perfect_clients.get("phone_prefixe", pd.Series(dtype="string")).notna().sum())
        invalid_perfect = int(len(prepared.perfect_clients) - valid_perfect)
        st.caption(
            f"Perfect : {len(prepared.perfect_clients)} ligne(s), {valid_perfect} telephone(s) exploitable(s), "
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
                "Perfect dans M_PESA",
                _format_count(perfect_identity_count(clients_perfect_dans_mpesa)),
                f"{len(clients_perfect_dans_mpesa)} telephone(s) Perfect/G2",
                "blue",
            ),
            (
                "Perfect dans Turbo",
                _format_count(perfect_identity_count(clients_perfect_dans_turbo)),
                f"{len(clients_perfect_dans_turbo)} telephone(s) Perfect/Turbo",
                "green",
            ),
            (
                "Perfect dans Turbo et M_PESA",
                _format_count(perfect_identity_count(clients_perfect_dans_turbo_et_mpesa)),
                f"{len(clients_perfect_dans_turbo_et_mpesa)} telephone(s) dans les 3 systemes",
                "navy",
            ),
        ]
    )
    st.caption(
        f"Qualite du rapprochement : {not_found} telephone(s) M-PESA non trouve(s) dans Perfect, "
        f"{ambiguous} numero(s) partage(s) et {invalid_phone} telephone(s) inexploitable(s)."
    )

    render_panel_title("1. Clients Perfect retrouves dans les systemes M-PESA")
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
        ["Perfect dans M_PESA", "Perfect dans Turbo", "Perfect dans Turbo et M_PESA"]
    )
    cohorts = [
        (
            cohort_tabs[0],
            clients_perfect_dans_mpesa,
            "Clients Perfect dont le Phone_Prefixe est observe dans les transactions G2.",
        ),
        (
            cohort_tabs[1],
            clients_perfect_dans_turbo,
            "Clients Perfect dont le Phone_Prefixe est observe dans au moins une source Turbo.",
        ),
        (
            cohort_tabs[2],
            clients_perfect_dans_turbo_et_mpesa,
            "Clients Perfect dont le Phone_Prefixe est observe a la fois dans G2 et Turbo.",
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
                st.dataframe(cohort[visible_columns], width="stretch", hide_index=True)

    render_panel_title("2. Tous les clients M-PESA recherches dans Perfect")
    search_value = st.text_input(
        "Rechercher par telephone, Customer ID ou nom",
        key="mpesa_perfect_client_search",
        placeholder="Ex. 243..., Customer ID, nom M-PESA ou nom Perfect",
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
    st.dataframe(summary_view[summary_columns], width="stretch", hide_index=True)
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
                "noms_clients_mpesa": "Nom_client_M-PESA",
                "noms_clients_perfect": "Nom_client_Perfect",
                "customer_ids_turbo": "Customer_ID_Turbo",
                "ids_clients_perfect": "ID_client_Perfect",
                "codes_clients_perfect": "Code_client_Perfect",
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
        "Telecharger le rapprochement M-PESA / Perfect",
        data=export_bytes,
        file_name="rapprochement_mpesa_perfect.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )


def _render_loans_tab(report: dict[str, Any] | None, prepared: MpesaPreparedData) -> None:
    if report is not None:
        render_panel_title("Credits du client")
        credits_view = _apply_local_multiselect_filters(
            report["credits"],
            ["currency_code", "status_name", "loan_id"],
            key_prefix="mpesa_client_loans_filter",
        )
        st.caption(f"{len(credits_view)} credit(s) affiche(s).")
        st.dataframe(credits_view, width="stretch", hide_index=True)
    elif not prepared.loans.empty:
        render_panel_title("Credits importes")
        columns = [column for column in LOAN_USEFUL_COLUMNS if column in prepared.loans.columns]
        loans_base = prepared.loans[columns] if columns else prepared.loans
        loans_view = _apply_local_multiselect_filters(
            loans_base,
            ["currency_code", "status_name", "customer_id"],
            key_prefix="mpesa_import_loans_filter",
        )
        st.caption(f"{len(loans_view)} credit(s) affiche(s).")
        st.dataframe(loans_view.head(500), width="stretch", hide_index=True)
    else:
        st.info("Le fichier Credits est facultatif. Chargez-le pour enrichir l'extrait avec les informations LN.")


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
        render_panel_title("Anomalies Transactions")
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

    upload_col1, upload_col2 = st.columns(2)
    with upload_col1:
        transactions_file = st.file_uploader("Transactions M-PESA_Turbo", type=["xlsx", "xls"], key="mpesa_transactions_file")
        current_file = st.file_uploader("Comptes d'epargne courante_Turbo", type=["xlsx", "xls"], key="mpesa_current_file")
        g2_file = st.file_uploader("Transactions M-PESA_G2", type=["xlsx", "xls"], key="mpesa_g2_file")
    with upload_col2:
        fixed_file = st.file_uploader("Comptes DAT_Turbo", type=["xlsx", "xls"], key="mpesa_fixed_file")
        customers_file = st.file_uploader("Clients_Turbo", type=["xlsx", "xls"], key="mpesa_customers_file")
        loans_file = st.file_uploader("Credits_Turbo", type=["xlsx", "xls"], key="mpesa_loans_file")
        perfect_file = st.file_uploader(
            "Clients_Perfect",
            type=["xlsx", "xls"],
            key="mpesa_perfect_clients_file",
            help="La colonne Phone_Prefixe est utilisee pour le rapprochement.",
        )

    _render_expected_columns("Colonnes attendues - Transactions M-PESA_Turbo", TRANSACTION_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - Epargne courante_Turbo", CURRENT_SAVINGS_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - DAT_Turbo", FIXED_SAVINGS_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - Transactions M-PESA_G2", G2_TRANSACTION_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - Clients_Turbo", CUSTOMERS_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - Clients_Perfect", PERFECT_CLIENTS_REQUIRED_COLUMNS)

    try:
        transactions_raw = _uploaded_dataframe(transactions_file)
        current_raw = _uploaded_dataframe(current_file)
        fixed_raw = _uploaded_dataframe(fixed_file)
        customers_raw = _uploaded_dataframe(customers_file)
        loans_raw = _uploaded_dataframe(loans_file)
        g2_raw = _uploaded_dataframe(g2_file)
        perfect_raw = _uploaded_dataframe(perfect_file)
    except ValueError as exc:
        st.error(str(exc))
        return

    prepared, missing = _build_prepared_data(
        transactions_raw,
        current_raw,
        fixed_raw,
        loans_raw,
        g2_raw,
        customers_raw,
        perfect_raw,
    )
    sub_tabs = st.tabs(
        ["Importation", "Vue d'ensemble", "Extrait client", "DAT", "G2 / DAT", "Perfect_client", "Credits", "Controle des donnees"]
    )
    report: dict[str, Any] | None = None
    with sub_tabs[0]:
        _render_import_tab(prepared, missing)
    with sub_tabs[1]:
        _render_overview(prepared)
    with sub_tabs[2]:
        report = _render_customer_extract(prepared)
    with sub_tabs[3]:
        _render_dat_tab(report, prepared)
    with sub_tabs[4]:
        _render_g2_dat_tab(report, prepared)
    with sub_tabs[5]:
        _render_perfect_client_tab(prepared)
    with sub_tabs[6]:
        _render_loans_tab(report, prepared)
    with sub_tabs[7]:
        _render_diagnostics_tab(prepared, report)
