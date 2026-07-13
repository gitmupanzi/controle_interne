from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.services.mpesa_analysis import (
    CURRENT_SAVINGS_REQUIRED_COLUMNS,
    CUSTOMERS_REQUIRED_COLUMNS,
    FIXED_SAVINGS_REQUIRED_COLUMNS,
    G2_TRANSACTION_REQUIRED_COLUMNS,
    LOAN_USEFUL_COLUMNS,
    TRANSACTION_REQUIRED_COLUMNS,
    MpesaPreparedData,
    build_diagnostics,
    build_g2_daily_savings_report,
    build_g2_entry_report,
    build_g2_dat_crosscheck,
    build_load_report,
    build_mpesa_statement,
    create_excel_export,
    enrich_transactions_with_g2_customer_names,
    enrich_turbo_with_g2_customer_names,
    numeric_column,
    prepare_current_savings,
    prepare_customers,
    prepare_fixed_savings,
    prepare_g2_transactions,
    prepare_loans,
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
    }
    transactions = prepare_transactions(transactions_raw) if transactions_raw is not None and not transactions_raw.empty else pd.DataFrame()
    current = prepare_current_savings(current_raw)
    fixed = prepare_fixed_savings(fixed_raw)
    loans = prepare_loans(loans_raw)
    g2_transactions = prepare_g2_transactions(g2_raw)
    customers = prepare_customers(customers_raw)
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
        },
        missing,
    )
    return MpesaPreparedData(transactions, current, fixed, loans, load_report, g2_transactions, customers), missing


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


def _render_vertical_summary_blocks(summary: pd.DataFrame) -> None:
    if summary is None or not isinstance(summary, pd.DataFrame) or summary.empty:
        return
    table = summary[["currency_code", "details_rapport", "montant"]].copy()
    table.columns = ["Devise", "Synthese sur le Portail BB Digital", "Montant"]
    st.dataframe(table, width="stretch", hide_index=True)


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


def _filter_statement(statement: pd.DataFrame) -> pd.DataFrame:
    if statement.empty:
        return statement
    filtered = statement.copy()
    currencies = _currency_options(filtered)
    if currencies:
        selected_currency = st.selectbox("Devise", ["Toutes"] + currencies, key="mpesa_filter_currency")
        if selected_currency != "Toutes":
            filtered = filtered.loc[filtered["currency_code"].eq(selected_currency)]
    operation_types = sorted(filtered["type_operation"].dropna().astype(str).unique()) if "type_operation" in filtered.columns else []
    if operation_types:
        selected_types = st.multiselect(
            "Type d'operation",
            operation_types,
            default=[],
            key="mpesa_filter_type",
            placeholder="Choose options",
            help="Aucune option choisie = tous les types d'operation.",
        )
        if selected_types:
            filtered = filtered.loc[filtered["type_operation"].isin(selected_types)]
    if "created_at" in filtered.columns:
        dates = pd.to_datetime(filtered["created_at"], errors="coerce").dropna()
        if not dates.empty:
            date_range = st.date_input(
                "Periode",
                value=(dates.min().date(), dates.max().date()),
                min_value=dates.min().date(),
                max_value=dates.max().date(),
                key="mpesa_filter_dates",
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start, end = date_range
                filtered = filtered.loc[
                    pd.to_datetime(filtered["created_at"], errors="coerce").between(
                        pd.Timestamp(start),
                        pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1),
                    )
                ]
    ref_query = st.text_input("Reference M-PESA, DAT ou credit", key="mpesa_filter_reference").strip()
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
    cards: list[tuple[str, str, str, str]] = []
    for _, row in summary.iterrows():
        currency = row.get("devise", "")
        cards.extend(
            [
                ("Operations", _format_count(row.get("nombre_operations_mpesa")), f"Devise {currency}", "blue"),
                ("Entrees", _format_amount(row.get("total_entrees_mpesa")), f"Devise {currency}", "green"),
                ("Sorties", _format_amount(row.get("total_sorties_mpesa")), f"Devise {currency}", "orange"),
                ("Net", _format_amount(row.get("mouvement_net")), f"Devise {currency}", "navy"),
                ("Solde M-PESA final", _format_amount(row.get("solde_mpesa_final")), "Seulement si ouverture fournie", "slate"),
                ("Epargne finale", _format_amount(row.get("epargne_courante_finale")), f"Devise {currency}", "green"),
                ("DAT final", _format_amount(row.get("dat_final")), f"Devise {currency}", "navy"),
                ("Credits", _format_count(row.get("nombre_credits")), f"Solde {_format_amount(row.get('solde_credit_total'))}", "red"),
            ]
        )
    render_kpi_cards(cards[:12])


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
    render_summary_box(
        "Recherche client",
        [
            search_help,
            "Les soldes M-PESA reels ne sont calcules que si le solde d'ouverture est fourni par devise.",
        ],
    )
    query_label = "Customer ID, telephone ou nom" if has_g2_names else "Customer ID ou telephone"
    query = st.text_input(query_label, key="mpesa_customer_query")
    if not query.strip():
        st.info("Saisissez un identifiant client ou un telephone.")
        return None

    matches = search_customers(query, prepared)
    if matches.empty:
        st.warning("Aucun client trouve.")
        return None
    with st.expander("Clients correspondants", expanded=True):
        matches_view = _apply_local_multiselect_filters(
            matches,
            ["source", "Nom_client", "customer_id", "telephone"],
            key_prefix="mpesa_customer_matches",
        )
        st.caption(f"{len(matches_view)} correspondance(s) affichee(s).")
        st.dataframe(matches_view, width="stretch", hide_index=True)
    match_options = sorted(matches_view["customer_id"].dropna().astype(str).unique()) if not matches_view.empty else []
    if not match_options:
        st.warning("Les filtres de correspondance ne laissent aucun client selectable.")
        return None
    selected_customer = st.selectbox("Client trouve", match_options, key="mpesa_selected_customer")

    currencies = _currency_options(prepared.transactions.loc[prepared.transactions["customer_id"].astype(str).eq(selected_customer)])
    opening_balances: dict[str, float | None] = {}
    opening_cols = st.columns(max(len(currencies), 1))
    for index, currency in enumerate(currencies or ["CDF", "USD"]):
        with opening_cols[index % len(opening_cols)]:
            value = st.number_input(
                f"Solde d'ouverture M-PESA {currency}",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                key=f"mpesa_opening_{currency}",
                help="Laissez 0 puis decochez ci-dessous si le solde n'est pas connu.",
            )
            use_value = st.checkbox(f"Utiliser le solde {currency}", value=False, key=f"mpesa_use_opening_{currency}")
            opening_balances[currency] = value if use_value else None

    try:
        report = build_mpesa_statement(prepared, selected_customer, opening_balances=opening_balances)
    except ValueError as exc:
        st.warning(str(exc))
        return None

    statement = report["extrait"]
    summary = report["synthese"]
    if not summary.empty:
        st.write(
            f"Client **{selected_customer}** | Devises : **{', '.join(summary['devise'].astype(str).tolist())}** | "
            f"Operations : **{int(summary['nombre_operations_mpesa'].sum())}**"
        )
    if statement["solde_mpesa_apres"].isna().all():
        st.warning(
            "Le solde d'ouverture M-PESA n'a pas ete fourni. Le resultat affiche est un cumul relatif et non le solde reel du portefeuille."
        )

    filtered_statement = _filter_statement(statement)
    filtered_report = dict(report)
    filtered_report["extrait"] = filtered_statement
    filtered_report["synthese"] = report["synthese"]
    _render_customer_kpis(summary)
    _render_statement_charts(filtered_statement)
    render_panel_title("Extrait client")
    st.dataframe(filtered_statement, width="stretch", hide_index=True)
    export_bytes = create_excel_export(filtered_report)
    st.download_button(
        "Telecharger l'extrait du client",
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


def _render_dat_tab(report: dict[str, Any] | None, prepared: MpesaPreparedData) -> None:
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


def _render_g2_dat_tab(report: dict[str, Any] | None, prepared: MpesaPreparedData) -> None:
    if prepared.g2_transactions.empty:
        st.info("Aucun fichier Transactions G2 charge. Chargez `Transaction g2.xlsx` pour rapprocher les telephones G2 avec les DAT.")
        return

    daily_report = build_g2_daily_savings_report(prepared)
    daily_detail = daily_report.get("detail", pd.DataFrame())
    daily_synthese = daily_report.get("synthese", pd.DataFrame())
    daily_pivot = daily_report.get("pivot", pd.DataFrame())
    daily_vertical_summary = daily_report.get("vertical_summary", pd.DataFrame())
    if not daily_detail.empty:
        render_summary_box(
            "Rapport journalier epargnes normales / DAT",
            [
                "Le telephone extrait de `Opposite Party` est croise avec `msisdn` du fichier Turbo.",
                "`Compte creer` provient du `created_at` de l'epargne courante si le fichier est charge; sinon la date DAT sert de repli.",
                "Les lignes DAT sont affectees par montant/date du DAT; les autres restent en depot normal.",
            ],
        )
        render_panel_title("Synthese journaliere par devise")
        _render_vertical_summary_blocks(daily_vertical_summary)

        render_panel_title("Detail journalier type rapport envoye")
        daily_view = _apply_local_multiselect_filters(
            daily_detail,
            ["currency_code", "details_rapport", "duree", "dat_match_rule", "transaction_status"],
            key_prefix="mpesa_daily_g2_report_filter",
        )
        st.caption(f"{len(daily_view)} ligne(s) du rapport journalier affichee(s).")
        display_columns = [
            "date",
            "receipt_no",
            "currency_code",
            "details_rapport",
            "opposite_party",
            "duree",
            "compte_cree",
            "montant",
        ]
        display_columns = [column for column in display_columns if column in daily_view.columns]
        st.dataframe(daily_view[display_columns], width="stretch", hide_index=True)

        daily_bytes = create_excel_export(
            {
                "rapport_journalier_pivot": daily_pivot,
                "rapport_journalier_vertical": daily_vertical_summary,
                "rapport_journalier_synthese": daily_synthese,
                "rapport_journalier_detail": daily_detail,
            }
        )
        st.download_button(
            "Telecharger le rapport journalier epargnes DAT",
            data=daily_bytes,
            file_name="rapport_journalier_epargnes_dat_g2.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

    render_summary_box(
        "Rapprochement G2 / DAT",
        [
            "`Receipt No.` est rapproche en priorite avec `ref_no` du fichier Transactions M-PESA.",
            "Le telephone extrait depuis `Opposite Party` reste disponible comme controle ou solution de repli.",
            "Le DAT est ensuite retrouve via le client identifie et la devise de la transaction.",
        ],
    )

    if report is not None:
        g2_dat = report.get("g2_dat", pd.DataFrame())
        render_panel_title("Transactions G2 du client selectionne")
    else:
        g2_dat = build_g2_dat_crosscheck(prepared)
        render_panel_title("Rapprochement global G2 / DAT")

    if g2_dat.empty:
        st.warning("Aucun rapprochement G2 / DAT disponible pour le perimetre courant.")
        return

    matched = int(g2_dat["customer_id_dat"].astype("string").fillna("").ne("").sum()) if "customer_id_dat" in g2_dat.columns else 0
    dat_operation_count = (
        int(g2_dat["reference_dat_operation"].astype("string").fillna("").ne("").sum())
        if "reference_dat_operation" in g2_dat.columns
        else 0
    )
    total_dat = float(numeric_column(g2_dat, "dat_final_client_devise").sum())
    render_kpi_cards(
        [
            ("Transactions G2", _format_count(len(g2_dat)), "Lignes analysees", "blue"),
            ("DAT operation", _format_count(dat_operation_count), "Lignes FIXED SAVINGS via ref_no", "green"),
            ("Clients rapproches", _format_count(matched), "Via ref_no ou telephone", "navy"),
            ("Non rapproches", _format_count(len(g2_dat) - matched), "A verifier", "orange"),
            ("DAT total rapproche", _format_amount(total_dat), "Somme par devise source", "navy"),
        ]
    )

    filtered = _apply_local_multiselect_filters(
        g2_dat,
        ["currency_code", "mode_rapprochement", "statut_rapprochement_dat", "transaction_status", "customer_id_dat", "phone_prefixe"],
        key_prefix="mpesa_g2_dat_filter",
    )
    display_columns = [
        "receipt_no",
        "completion_time",
        "currency_code",
        "transaction_amount",
        "opposite_party",
        "customer_id_ref_no",
        "dat_operation",
        "solde_dat_operation",
        "dat_final",
        "produits_dat",
        "maturites_dat",
        "mode_rapprochement",
        "statut_rapprochement_dat",
    ]
    display_columns = [column for column in display_columns if column in filtered.columns]
    filtered_display = filtered[display_columns].copy() if display_columns else filtered
    st.caption(f"{len(filtered)} ligne(s) G2 affichee(s).")
    st.dataframe(filtered_display, width="stretch", hide_index=True)

    if report is None:
        g2_report = build_g2_entry_report(prepared)
        synthese = g2_report.get("synthese", pd.DataFrame())
        detail = g2_report.get("detail", pd.DataFrame())
        pivot = g2_report.get("pivot", pd.DataFrame())
        vertical_summary = g2_report.get("vertical_summary", pd.DataFrame())
        if not synthese.empty:
            render_panel_title("Synthese des encaissements G2")
            _render_vertical_summary_blocks(vertical_summary)
        if not detail.empty:
            render_panel_title("Detail des encaissements G2")
            detail_view = _apply_local_multiselect_filters(
                detail,
                ["currency_code", "details_rapport", "mode_rapprochement", "statut_rapprochement_dat"],
                key_prefix="mpesa_g2_entry_report_filter",
            )
            st.caption(f"{len(detail_view)} ligne(s) du rapport affichee(s).")
            st.dataframe(detail_view, width="stretch", hide_index=True)
        report_bytes = create_excel_export(
            {
                "rapport_g2_pivot": pivot,
                "rapport_g2_vertical": vertical_summary,
                "rapport_g2_synthese": synthese,
                "rapport_g2_detail": detail,
                "g2_dat": g2_dat,
            }
        )
        st.download_button(
            "Telecharger le rapport G2 fusionne",
            data=report_bytes,
            file_name="rapport_encaissements_g2_bisou_bisou.xlsx",
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

    _render_expected_columns("Colonnes attendues - Transactions M-PESA_Turbo", TRANSACTION_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - Epargne courante_Turbo", CURRENT_SAVINGS_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - DAT_Turbo", FIXED_SAVINGS_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - Transactions M-PESA_G2", G2_TRANSACTION_REQUIRED_COLUMNS)
    _render_expected_columns("Colonnes attendues - Clients_Turbo", CUSTOMERS_REQUIRED_COLUMNS)

    try:
        transactions_raw = _uploaded_dataframe(transactions_file)
        current_raw = _uploaded_dataframe(current_file)
        fixed_raw = _uploaded_dataframe(fixed_file)
        customers_raw = _uploaded_dataframe(customers_file)
        loans_raw = _uploaded_dataframe(loans_file)
        g2_raw = _uploaded_dataframe(g2_file)
    except ValueError as exc:
        st.error(str(exc))
        return

    prepared, missing = _build_prepared_data(transactions_raw, current_raw, fixed_raw, loans_raw, g2_raw, customers_raw)
    sub_tabs = st.tabs(["Importation", "Vue d'ensemble", "Extrait client", "DAT", "G2 / DAT", "Credits", "Controle des donnees"])
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
        _render_loans_tab(report, prepared)
    with sub_tabs[6]:
        _render_diagnostics_tab(prepared, report)
