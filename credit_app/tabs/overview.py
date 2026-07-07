from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from credit_app.core import format_currency, format_percent
from credit_app.cycles import get_cycle_spec
from credit_app.domain import (
    build_age_bucket_table,
    build_age_sex_pyramid_table,
    build_cycle_period_series,
    build_epargne_agent_portfolio_table,
    build_frequency_table,
    build_grouped_amounts,
    build_operational_snapshot,
    build_sex_distribution,
    build_status_distribution,
    build_summary_metrics,
    get_cycle_primary_date_column,
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

CREDIT_LIKE_CYCLES = {"credit", "likelemba"}

GENERIC_OVERVIEW_CONFIG = {
    "epargne": {
        "record_label": "Comptes d'épargne",
        "record_subtitle": "Comptes analysés",
        "amount_columns": ["solde_compte", "montant_operation"],
        "amount_label": "Encours total",
        "amount_subtitle": "Total des soldes documentés",
        "entity_columns": ["compte_id", "client_id"],
        "entity_label": "Comptes / clients",
        "entity_subtitle": "Base couverte",
        "site_columns": ["agent_credit"],
        "site_label": "Gestionnaires actifs",
        "site_subtitle": "Responsables documentés",
        "primary_columns": ["type_produit", "type_client", "statut_compte"],
        "primary_title": "Distribution des produits d'épargne",
        "secondary_columns": ["type_client", "agent_credit", "sexe"],
        "secondary_title": "Répartition secondaire",
        "group_columns": ["type_produit", "agent_credit"],
        "group_title": "Soldes cumulés par produit",
        "actor_columns": [],
        "actor_label": "Gestionnaires",
        "actor_subtitle": "Acteurs documentés",
        "timeline_title": "Dernière activité par mois",
        "balance_columns": [],
        "balance_label": "Solde moyen",
        "balance_subtitle": "Position observée",
        "alert_columns": ["solde_compte"],
        "alert_label": "Soldes négatifs",
        "alert_subtitle": "Comptes à surveiller",
    },
    "crm_clients": {
        "record_label": "Fiches clients CRM",
        "record_subtitle": "Clients analysés",
        "amount_columns": [],
        "entity_columns": ["client_id", "compte_id"],
        "entity_label": "Clients / comptes",
        "entity_subtitle": "Base client couverte",
        "site_columns": ["agent_credit"],
        "site_label": "Gestionnaires actifs",
        "site_subtitle": "Responsables documentés",
        "primary_columns": ["Origine du Prospect", "zone_geographique", "categorie"],
        "primary_title": "Distribution des origines prospects",
        "secondary_columns": ["agent_credit", "Civilité", "Source de données"],
        "secondary_title": "Répartition secondaire",
        "group_columns": ["agent_credit", "zone_geographique"],
        "group_title": "Répartition par gestionnaire",
        "actor_columns": [],
        "timeline_title": "Dernière activité par mois",
        "balance_columns": [],
        "alert_columns": ["Locked"],
        "alert_label": "Fiches verrouillées",
        "alert_subtitle": "Fiches à débloquer ou vérifier",
    },
    "caisse": {
        "record_label": "Mouvements caisse",
        "record_subtitle": "Lignes analysées",
        "amount_columns": ["montant_operation"],
        "amount_label": "Volume traité",
        "amount_subtitle": "Flux de caisse",
        "entity_columns": ["caissier"],
        "entity_label": "Caissiers actifs",
        "entity_subtitle": "Acteurs couverts",
        "site_columns": ["agence"],
        "site_label": "Agences actives",
        "site_subtitle": "Guichets suivis",
        "primary_columns": ["type_operation"],
        "primary_title": "Distribution des mouvements de caisse",
        "secondary_columns": ["caissier"],
        "secondary_title": "Top caissiers actifs",
        "group_columns": ["agence"],
        "group_title": "Volumes par agence",
        "actor_columns": ["caissier"],
        "actor_label": "Caissiers",
        "actor_subtitle": "Effectif actif",
        "timeline_title": "Évolution mensuelle des mouvements",
        "balance_columns": ["encaisse_fin_jour"],
        "balance_label": "Encaisse moyenne",
        "balance_subtitle": "Fin de journée",
        "alert_columns": ["ecart_caisse"],
        "alert_label": "Écarts détectés",
        "alert_subtitle": "Écarts de caisse non nuls",
    },
    "tresorerie": {
        "record_label": "Mouvements de trésorerie",
        "record_subtitle": "Lignes analysées",
        "amount_columns": ["montant_operation"],
        "amount_label": "Montant traité",
        "amount_subtitle": "Flux suivis",
        "entity_columns": ["compte_bancaire"],
        "entity_label": "Comptes bancaires",
        "entity_subtitle": "Comptes suivis",
        "site_columns": ["banque"],
        "site_label": "Banques actives",
        "site_subtitle": "Relations bancaires",
        "primary_columns": ["banque", "devise"],
        "primary_title": "Distribution des banques / devises",
        "secondary_columns": ["compte_bancaire", "devise"],
        "secondary_title": "Répartition secondaire",
        "group_columns": ["banque"],
        "group_title": "Volumes par banque",
        "actor_columns": [],
        "timeline_title": "Évolution mensuelle de la trésorerie",
        "balance_columns": ["solde_banque"],
        "balance_label": "Solde moyen",
        "balance_subtitle": "Position bancaire",
        "alert_columns": ["ecart_rapprochement"],
        "alert_label": "Écarts de rapprochement",
        "alert_subtitle": "Écarts non nuls",
    },
    "comptable": {
        "record_label": "Écritures",
        "record_subtitle": "Lignes analysées",
        "amount_columns": ["montant_debit", "montant_credit"],
        "amount_label": "Volume comptable",
        "amount_subtitle": "Débit + crédit",
        "entity_columns": ["piece_id"],
        "entity_label": "Pièces",
        "entity_subtitle": "Pièces uniques",
        "site_columns": ["journal"],
        "site_label": "Journaux actifs",
        "site_subtitle": "Journaux couverts",
        "primary_columns": ["journal"],
        "primary_title": "Distribution des journaux",
        "secondary_columns": ["compte_comptable", "centre_cout"],
        "secondary_title": "Comptes les plus actifs",
        "group_columns": ["journal"],
        "group_title": "Volumes par journal",
        "actor_columns": [],
        "timeline_title": "Évolution mensuelle des écritures",
        "balance_columns": [],
        "alert_columns": [],
    },
    "rh_admin": {
        "record_label": "Enregistrements RH",
        "record_subtitle": "Lignes analysées",
        "amount_columns": ["salaire"],
        "amount_label": "Masse salariale",
        "amount_subtitle": "Montant documenté",
        "entity_columns": ["agent_id"],
        "entity_label": "Agents",
        "entity_subtitle": "Agents uniques",
        "site_columns": ["agence"],
        "site_label": "Agences actives",
        "site_subtitle": "Sites couverts",
        "primary_columns": ["fonction", "statut_agent"],
        "primary_title": "Distribution des fonctions",
        "secondary_columns": ["statut_agent", "immobilisation_id"],
        "secondary_title": "Répartition secondaire",
        "group_columns": ["agence"],
        "group_title": "Répartition par agence",
        "actor_columns": [],
        "timeline_title": "Évolution mensuelle des enregistrements RH",
        "balance_columns": [],
        "alert_columns": [],
    },
    "si": {
        "record_label": "Accès et habilitations",
        "record_subtitle": "Lignes analysées",
        "amount_columns": [],
        "entity_columns": ["agent_id"],
        "entity_label": "Agents",
        "entity_subtitle": "Agents couverts",
        "site_columns": ["application_source"],
        "site_label": "Applications",
        "site_subtitle": "Périmètres suivis",
        "primary_columns": ["profil_acces", "niveau_habilitation"],
        "primary_title": "Distribution des profils d'accès",
        "secondary_columns": ["niveau_habilitation", "application_source"],
        "secondary_title": "Répartition secondaire",
        "group_columns": ["application_source"],
        "group_title": "Volumes par application",
        "actor_columns": [],
        "timeline_title": "Évolution mensuelle des habilitations",
        "balance_columns": [],
        "alert_columns": ["date_revocation"],
        "alert_label": "Révocations tracées",
        "alert_subtitle": "Comptes avec date de révocation",
    },
    "continuite": {
        "record_label": "Sauvegardes / tests",
        "record_subtitle": "Lignes analysées",
        "amount_columns": [],
        "entity_columns": ["support_sauvegarde"],
        "entity_label": "Supports",
        "entity_subtitle": "Supports documentés",
        "site_columns": ["type_sauvegarde"],
        "site_label": "Types actifs",
        "site_subtitle": "Catégories suivies",
        "primary_columns": ["type_sauvegarde"],
        "primary_title": "Distribution des sauvegardes",
        "secondary_columns": ["statut_test_reprise", "incident_majeur"],
        "secondary_title": "Répartition des tests / incidents",
        "group_columns": ["support_sauvegarde"],
        "group_title": "Répartition par support",
        "actor_columns": [],
        "timeline_title": "Évolution mensuelle des sauvegardes",
        "balance_columns": [],
        "alert_columns": ["incident_majeur"],
        "alert_label": "Incidents majeurs",
        "alert_subtitle": "Incidents renseignés",
    },
    "money_provider": {
        "record_label": "Transactions",
        "record_subtitle": "Lignes analysées",
        "amount_columns": ["montant_operation"],
        "amount_label": "Volume traité",
        "amount_subtitle": "Cash-in / cash-out / transferts",
        "entity_columns": ["numero_reference", "client_id"],
        "entity_label": "Références / clients",
        "entity_subtitle": "Base couverte",
        "site_columns": ["agence"],
        "site_label": "Agences actives",
        "site_subtitle": "Points de service",
        "primary_columns": ["type_operation"],
        "primary_title": "Distribution des types d'opération",
        "secondary_columns": ["operateur", "tresorier"],
        "secondary_title": "Top opérateurs actifs",
        "group_columns": ["agence"],
        "group_title": "Volumes par agence",
        "actor_columns": ["operateur", "tresorier"],
        "actor_label": "Opérateurs / trésoriers",
        "actor_subtitle": "Acteurs documentés",
        "timeline_title": "Évolution mensuelle des transactions",
        "balance_columns": ["solde_final", "solde_initial"],
        "balance_label": "Solde moyen",
        "balance_subtitle": "Position documentée",
        "alert_columns": ["telephone"],
        "alert_label": "Téléphones renseignés",
        "alert_subtitle": "Transactions avec contact",
    },
    "operations_depot_retrait": {
        "record_label": "Opérations",
        "record_subtitle": "Dépôts et retraits analysés",
        "amount_columns": ["montant_operation"],
        "amount_label": "Volume traité",
        "amount_subtitle": "Montants observés",
        "entity_columns": ["operation_id", "client_id"],
        "entity_label": "Opérations / clients",
        "entity_subtitle": "Base couverte",
        "site_columns": ["agence"],
        "site_label": "Points de service",
        "site_subtitle": "Agences documentées",
        "primary_columns": ["type_mouvement", "source_mouvement", "code_devise"],
        "primary_title": "Distribution des dépôts et retraits",
        "secondary_columns": ["operateur", "agence", "code_devise"],
        "secondary_title": "Répartition secondaire",
        "group_columns": ["agence", "source_mouvement"],
        "group_title": "Volumes par point de service",
        "actor_columns": ["operateur"],
        "actor_label": "Utilisateurs actifs",
        "actor_subtitle": "Acteurs documentés",
        "timeline_title": "Évolution mensuelle des opérations",
        "balance_columns": [],
        "alert_columns": ["annule"],
        "alert_label": "Opérations annulées",
        "alert_subtitle": "Flux à relire",
    },
}


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def _prepare_amount_frame(
    df: pd.DataFrame,
    amount_columns: list[str],
    derived_name: str = "_montant_cycle",
) -> tuple[pd.DataFrame, str | None]:
    present_columns = [column for column in amount_columns if column in df.columns]
    if not present_columns:
        return df, None
    if len(present_columns) == 1:
        return df, present_columns[0]

    amount_frame = df.copy()
    amount_frame[derived_name] = (
        amount_frame[present_columns]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .sum(axis=1)
    )
    return amount_frame, derived_name


def _format_period_span(df: pd.DataFrame, date_column: str | None) -> str:
    if not date_column or date_column not in df.columns:
        return "-"
    dates = pd.to_datetime(df[date_column], errors="coerce").dropna()
    if dates.empty:
        return "-"
    return f"{dates.min():%Y-%m-%d} -> {dates.max():%Y-%m-%d}"


def _top_label(df: pd.DataFrame, candidates: list[str]) -> str:
    column = _first_existing_column(df, candidates)
    if not column:
        return "-"
    freq = build_frequency_table(df, column, top_n=1)
    if freq.empty:
        return "-"
    return str(freq.iloc[0][column])


def _unique_count(df: pd.DataFrame, candidates: list[str]) -> int | None:
    column = _first_existing_column(df, candidates)
    if not column:
        return None
    values = df[column].dropna().astype("string").str.strip()
    values = values[values != ""]
    return int(values.nunique())


def _non_empty_count(df: pd.DataFrame, candidates: list[str]) -> int | None:
    column = _first_existing_column(df, candidates)
    if not column:
        return None
    series = df[column]
    if pd.api.types.is_datetime64_any_dtype(series):
        return int(series.notna().sum())
    if pd.api.types.is_numeric_dtype(series):
        return int(series.notna().sum())
    text_values = series.astype("string").str.strip()
    return int(text_values.fillna("").ne("").sum())


def _non_zero_or_documented_alert_count(df: pd.DataFrame, candidates: list[str]) -> int | None:
    column = _first_existing_column(df, candidates)
    if not column:
        return None
    series = df[column]
    if pd.api.types.is_datetime64_any_dtype(series):
        return int(series.notna().sum())
    numeric_series = pd.to_numeric(series, errors="coerce")
    if numeric_series.notna().any():
        return int(numeric_series.fillna(0).ne(0).sum())
    text_values = series.astype("string").str.strip()
    return int(text_values.fillna("").ne("").sum())


def _mean_numeric_value(df: pd.DataFrame, candidates: list[str]) -> float | None:
    frame, amount_column = _prepare_amount_frame(df, candidates, derived_name="_mean_cycle")
    if not amount_column:
        return None
    values = pd.to_numeric(frame[amount_column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def _sum_numeric_value(df: pd.DataFrame, candidates: list[str]) -> float | None:
    frame, amount_column = _prepare_amount_frame(df, candidates, derived_name="_sum_cycle")
    if not amount_column:
        return None
    values = pd.to_numeric(frame[amount_column], errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.sum())


def _build_credit_like_cards(df: pd.DataFrame, cycle_key: str) -> list[tuple[str, str, str, str]]:
    metrics = build_summary_metrics(df)
    snapshot = build_operational_snapshot(df)
    cards = [
        ("Dossiers", f"{metrics['nombre_dossiers']:,}".replace(",", " "), "Périmètre filtré", "blue"),
        (
            "Montant demandé",
            format_currency(metrics["montant_demande_total"]),
            "Somme des demandes",
            "navy",
        ),
        (
            "Taux d'approbation",
            format_percent(metrics["taux_approbation"]),
            "Décision favorable ou active",
            "green",
        ),
        ("Taux de retard", format_percent(metrics["taux_retard"]), "Dossiers en retard", "orange"),
        (
            "Clients uniques",
            "-" if metrics["nombre_clients"] is None else f"{metrics['nombre_clients']:,}".replace(",", " "),
            "Base client couverte",
            "blue",
        ),
        (
            "Montant accordé",
            format_currency(metrics["montant_accorde_total"]),
            "Montants engagés",
            "green",
        ),
        (
            "Retard moyen",
            "-" if metrics["retard_moyen_jours"] is None else f"{metrics['retard_moyen_jours']:.1f} j",
            "Sur les dossiers documentés",
            "orange",
        ),
        (
            "Endettement moyen",
            format_percent(metrics["taux_endettement_moyen"]),
            "Charges / revenu",
            "slate",
        ),
        (
            "Risque élevé",
            f"{snapshot['high_risk_count']:,}".replace(",", " "),
            "Dossiers à forte vigilance",
            "red",
        ),
        (
            "Capacité négative",
            f"{snapshot['negative_capacity_count']:,}".replace(",", " "),
            "Remboursement potentiellement fragile",
            "orange",
        ),
        (
            "Retard > 30 j",
            f"{snapshot['overdue_30_count']:,}".replace(",", " "),
            "Recouvrement à prioriser",
            "red",
        ),
        (
            "Ticket moyen",
            format_currency(snapshot["montant_moyen_demande"]),
            "Montant demandé moyen",
            "navy",
        ),
    ]
    if cycle_key == "likelemba" and "nom_groupe" in df.columns:
        group_count = _unique_count(df, ["nom_groupe"])
        cards.insert(
            4,
            (
                "Groupes actifs",
                "-" if group_count is None else f"{group_count:,}".replace(",", " "),
                "Groupes solidaires documentés",
                "slate",
            ),
        )
    return cards


def _render_credit_like_overview(df: pd.DataFrame, monthly_df: pd.DataFrame, cycle_key: str) -> None:
    render_kpi_cards(_build_credit_like_cards(df, cycle_key))
    left, right = st.columns((1.1, 1))

    with left:
        status_df = build_status_distribution(df)
        if not status_df.empty:
            render_panel_title("Distribution des statuts de dossier")
            fig = px.bar(
                status_df,
                x="statut_dossier",
                y="nombre_dossiers",
                color_discrete_sequence=["#2b74ca"],
            )
            fig.update_traces(marker_line_color="rgba(255,255,255,0.45)", marker_line_width=1.1)
            fig.update_layout(height=380, showlegend=False)
            st_plot(fig, key=f"overview_status_distribution_{cycle_key}", height=380)

    with right:
        effective_monthly_df = monthly_df if not monthly_df.empty else build_cycle_period_series(df, cycle_key)
        x_column = "mois_demande" if "mois_demande" in effective_monthly_df.columns else "periode"
        if not effective_monthly_df.empty and x_column in effective_monthly_df.columns:
            title = "Évolution mensuelle des demandes"
            if cycle_key == "likelemba":
                title = "Évolution mensuelle des dossiers du groupe"
            render_panel_title(title)
            fig = px.line(
                effective_monthly_df,
                x=x_column,
                y="nombre_lignes" if "nombre_lignes" in effective_monthly_df.columns else "nombre_dossiers",
                markers=True,
            )
            fig.update_traces(
                line_color="#2f855a",
                marker_color="#2f855a",
                line=dict(width=3),
                marker=dict(size=7),
            )
            fig.update_layout(height=380)
            st_plot(fig, key=f"overview_monthly_line_{cycle_key}", height=380)

    risk_left, risk_right = st.columns((1, 1.2))

    with risk_left:
        risk_df = build_frequency_table(df, "niveau_risque_calcule", top_n=6)
        if not risk_df.empty:
            render_panel_title("Distribution des niveaux de risque")
            fig = px.pie(
                risk_df,
                names="niveau_risque_calcule",
                values="nombre_lignes",
                hole=0.5,
                color="niveau_risque_calcule",
                color_discrete_map={
                    "Faible": "#1f7a5c",
                    "Moyen": "#d9a441",
                    "Élevé": "#c05621",
                    "Non renseigné": "#7b8794",
                },
            )
            fig.update_layout(height=340)
            st_plot(fig, key=f"overview_risk_pie_{cycle_key}", height=340)

    with risk_right:
        age_df = build_age_bucket_table(df)
        if not age_df.empty:
            render_panel_title("Tranches d'âge")
            age_order = age_df["tranche_age"].tolist()
            fig = px.bar(
                age_df,
                x="tranche_age",
                y="nombre_lignes",
                color="tranche_age",
                category_orders={"tranche_age": age_order},
                color_discrete_map={label: "#d77a0f" for label in age_df["tranche_age"].tolist()} | {"Non renseigné": "#a7a9ac"},
            )
            fig.update_traces(marker_line_color="rgba(255,255,255,0.55)", marker_line_width=1.2)
            fig.update_layout(height=340, showlegend=False, xaxis_tickangle=-25)
            st_plot(fig, key=f"overview_age_buckets_{cycle_key}", height=340)

    demo_left, demo_right = st.columns((1, 1.2))

    with demo_left:
        sex_df = build_sex_distribution(df)
        if not sex_df.empty:
            render_panel_title("Sexe")
            fig = px.pie(
                sex_df,
                names="sexe",
                values="nombre_lignes",
                hole=0.55,
                color="sexe",
                color_discrete_map={
                    "Masculin": "#1c2333",
                    "Féminin": "#d71920",
                    "Inconnu": "#a7a9ac",
                },
            )
            fig.update_layout(height=360)
            st_plot(fig, key=f"overview_sex_pie_{cycle_key}", height=360)

    with demo_right:
        pyramid_df = build_age_sex_pyramid_table(df)
        if not pyramid_df.empty:
            render_panel_title("Pyramide âge-sexe")
            annotate_values = bool(st.session_state.get("credit_annot_vals", False))
            annotation_threshold = float(st.session_state.get("credit_annot_min", 1))
            male_values = [-float(value) for value in pyramid_df["Masculin"].tolist()]
            female_values = [float(value) for value in pyramid_df["Féminin"].tolist()]
            male_text = [
                f"{int(abs(value))}" if annotate_values and abs(value) >= annotation_threshold else ""
                for value in male_values
            ]
            female_text = [
                f"{int(value)}" if annotate_values and value >= annotation_threshold else ""
                for value in female_values
            ]

            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    y=pyramid_df["tranche_age"],
                    x=male_values,
                    name="Masculin",
                    orientation="h",
                    marker=dict(color="#1c2333"),
                    text=male_text,
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            fig.add_trace(
                go.Bar(
                    y=pyramid_df["tranche_age"],
                    x=female_values,
                    name="Féminin",
                    orientation="h",
                    marker=dict(color="#e11d1d"),
                    text=female_text,
                    textposition="outside",
                    cliponaxis=False,
                )
            )
            max_value = max([abs(value) for value in male_values + female_values] + [0])
            fig.update_layout(
                barmode="relative",
                height=360,
                xaxis=dict(
                    range=[-max_value * 1.15, max_value * 1.15] if max_value else None,
                    tickvals=[-max_value, -max_value / 2, 0, max_value / 2, max_value] if max_value else None,
                    ticktext=[
                        f"{int(max_value)}",
                        f"{int(max_value / 2)}",
                        "0",
                        f"{int(max_value / 2)}",
                        f"{int(max_value)}",
                    ] if max_value else None,
                    title="Nombre de dossiers",
                ),
                yaxis=dict(title="Tranche d'âge", categoryorder="array", categoryarray=pyramid_df["tranche_age"].tolist()),
                legend=dict(orientation="h"),
            )
            st_plot(fig, key=f"overview_age_sex_pyramid_{cycle_key}", height=360, annotate_values=False)


def _build_generic_cycle_cards(df: pd.DataFrame, cycle_key: str) -> list[tuple[str, str, str, str]]:
    config = GENERIC_OVERVIEW_CONFIG.get(cycle_key, GENERIC_OVERVIEW_CONFIG["money_provider"])
    cards: list[tuple[str, str, str, str]] = [
        (
            config["record_label"],
            f"{len(df):,}".replace(",", " "),
            config["record_subtitle"],
            "slate",
        )
    ]

    total_amount = _sum_numeric_value(df, config.get("amount_columns", []))
    if total_amount is not None:
        cards.append(
            (
                config["amount_label"],
                format_currency(total_amount),
                config["amount_subtitle"],
                "slate",
            )
        )

    entity_count = _unique_count(df, config.get("entity_columns", []))
    if entity_count is not None:
        cards.append(
            (
                config["entity_label"],
                f"{entity_count:,}".replace(",", " "),
                config["entity_subtitle"],
                "slate",
            )
        )

    site_count = _unique_count(df, config.get("site_columns", []))
    if site_count is not None:
        cards.append(
            (
                config["site_label"],
                f"{site_count:,}".replace(",", " "),
                config["site_subtitle"],
                "slate",
            )
        )

    primary_top = _top_label(df, config.get("primary_columns", []))
    if primary_top != "-":
        cards.append(("Dominante", primary_top, "Catégorie la plus fréquente", "slate"))

    date_column = get_cycle_primary_date_column(df, cycle_key)
    cards.append(("Période", _format_period_span(df, date_column), "Fenêtre analytique", "slate"))

    mean_amount = _mean_numeric_value(df, config.get("amount_columns", []))
    if mean_amount is not None:
        cards.append(("Montant moyen", format_currency(mean_amount), "Moyenne observée", "slate"))

    actor_columns = config.get("actor_columns", [])
    actor_count = _unique_count(df, actor_columns)
    if actor_columns and actor_count is not None:
        cards.append(
            (
                config.get("actor_label", "Acteurs"),
                f"{actor_count:,}".replace(",", " "),
                config.get("actor_subtitle", "Acteurs documentés"),
                "slate",
            )
        )

    alert_columns = config.get("alert_columns", [])
    alert_count = _non_zero_or_documented_alert_count(df, alert_columns)
    if alert_columns and alert_count is not None:
        cards.append(
            (
                config.get("alert_label", "Alertes"),
                f"{alert_count:,}".replace(",", " "),
                config.get("alert_subtitle", "Lignes concernées"),
                "slate",
            )
        )

    balance_columns = config.get("balance_columns", [])
    mean_balance = _mean_numeric_value(df, balance_columns)
    if balance_columns and mean_balance is not None:
        cards.append(
            (
                config.get("balance_label", "Solde moyen"),
                format_currency(mean_balance),
                config.get("balance_subtitle", "Position observée"),
                "slate",
            )
        )

    return cards[:10]


def _render_frequency_bar(
    df: pd.DataFrame,
    column: str,
    title: str,
    key: str,
    horizontal: bool = False,
) -> None:
    freq_df = build_frequency_table(df, column, top_n=10)
    if freq_df.empty:
        st.info("Aucune distribution exploitable n'est disponible sur ce bloc.")
        return

    render_panel_title(title)
    if horizontal:
        fig = px.bar(
            freq_df.sort_values("nombre_lignes", ascending=True),
            x="nombre_lignes",
            y=column,
            orientation="h",
            color_discrete_sequence=["#2b74ca"],
        )
    else:
        fig = px.bar(
            freq_df,
            x=column,
            y="nombre_lignes",
            color_discrete_sequence=["#2b74ca"],
        )
        fig.update_layout(xaxis_tickangle=-25)
    fig.update_traces(marker_line_color="rgba(255,255,255,0.45)", marker_line_width=1.1)
    fig.update_layout(height=360, showlegend=False)
    st_plot(fig, key=key, height=360)


def _render_generic_cycle_overview(df: pd.DataFrame, cycle_key: str) -> None:
    config = GENERIC_OVERVIEW_CONFIG.get(cycle_key, GENERIC_OVERVIEW_CONFIG["money_provider"])
    cycle_spec = get_cycle_spec(cycle_key)
    render_kpi_cards(_build_generic_cycle_cards(df, cycle_key))

    date_column = get_cycle_primary_date_column(df, cycle_key)
    primary_column = _first_existing_column(df, config.get("primary_columns", []))
    group_column = _first_existing_column(df, config.get("group_columns", []))
    secondary_column = _first_existing_column(
        df,
        [
            column
            for column in config.get("secondary_columns", [])
            if column not in {primary_column, group_column}
        ],
    )
    period_df = build_cycle_period_series(df, cycle_key)
    amount_frame, amount_column = _prepare_amount_frame(df, config.get("amount_columns", []))

    render_summary_box(
        f"À retenir pour {cycle_spec['label']}",
        [
            cycle_spec["summary"],
            cycle_spec["control_objective"],
            f"Date utilisée : `{date_column}`." if date_column else "Aucune date principale n'a été détectée dans les données.",
            f"Champ principal utilisé : `{primary_column}`." if primary_column else "Aucun champ principal exploitable n'a été détecté.",
        ],
    )

    top_left, top_right = st.columns((1.05, 1))

    with top_left:
        if primary_column:
            _render_frequency_bar(
                df,
                primary_column,
                config["primary_title"],
                key=f"overview_primary_{cycle_key}",
            )
        else:
            st.info("Aucun regroupement principal n'est disponible pour ce cycle.")

    with top_right:
        if not period_df.empty:
            render_panel_title(config["timeline_title"])
            fig = px.line(
                period_df,
                x="periode",
                y="nombre_lignes",
                markers=True,
            )
            fig.update_traces(
                line_color="#2b74ca",
                marker_color="#2b74ca",
                line=dict(width=3),
                marker=dict(size=7),
            )
            fig.update_layout(height=360, xaxis_tickangle=-25)
            st_plot(fig, key=f"overview_period_{cycle_key}", height=360)
        else:
            st.info("Aucune évolution dans le temps n'a pu être construite pour ce cycle.")

    mid_left, mid_right = st.columns((1.05, 1))

    with mid_left:
        if group_column and amount_column:
            grouped_df = build_grouped_amounts(amount_frame, group_column, amount_column=amount_column, top_n=10)
            if not grouped_df.empty:
                render_panel_title(config["group_title"])
                fig = px.bar(
                    grouped_df.sort_values(amount_column, ascending=True),
                    x=amount_column,
                    y=group_column,
                    orientation="h",
                    color_discrete_sequence=["#4b84d7"],
                )
                fig.update_traces(marker_line_color="rgba(255,255,255,0.45)", marker_line_width=1.1)
                fig.update_layout(height=360, showlegend=False)
                st_plot(fig, key=f"overview_group_amount_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement par montant n'est disponible pour ce cycle.")
        elif group_column:
            _render_frequency_bar(
                df,
                group_column,
                config["group_title"],
                key=f"overview_group_freq_{cycle_key}",
                horizontal=True,
            )
        else:
            st.info("Aucun regroupement secondaire n'est disponible pour ce cycle.")

    with mid_right:
        if secondary_column:
            _render_frequency_bar(
                df,
                secondary_column,
                config["secondary_title"],
                key=f"overview_secondary_{cycle_key}",
                horizontal=True,
            )
        else:
            render_summary_box(
                "Complément",
                [
                    f"{len(df):,}".replace(",", " ") + " ligne(s) sont actuellement retenues dans ce cycle.",
                    "Ajoutez davantage de champs métier pour enrichir les comparaisons secondaires.",
                ],
            )

    sex_df = build_sex_distribution(df)
    pyramid_df = build_age_sex_pyramid_table(df)
    age_df = build_age_bucket_table(df)
    if not sex_df.empty or not pyramid_df.empty or not age_df.empty:
        demo_left, demo_right = st.columns((1, 1.2))
        with demo_left:
            if not sex_df.empty:
                render_panel_title("Sexe")
                fig = px.pie(
                    sex_df,
                    names="sexe",
                    values="nombre_lignes",
                    hole=0.55,
                    color="sexe",
                    color_discrete_map={
                        "Masculin": "#1c2333",
                        "Féminin": "#d71920",
                        "Inconnu": "#a7a9ac",
                    },
                )
                fig.update_layout(height=360)
                st_plot(fig, key=f"overview_generic_sex_{cycle_key}", height=360)
            elif not age_df.empty:
                render_panel_title("Tranches d'âge")
                fig = px.bar(
                    age_df,
                    x="tranche_age",
                    y="nombre_lignes",
                    color_discrete_sequence=["#d77a0f"],
                )
                fig.update_layout(height=360, showlegend=False, xaxis_tickangle=-25)
                st_plot(fig, key=f"overview_generic_age_{cycle_key}", height=360)

        with demo_right:
            if not pyramid_df.empty:
                render_panel_title("Pyramide âge-sexe")
                annotate_values = bool(st.session_state.get("credit_annot_vals", False))
                annotation_threshold = float(st.session_state.get("credit_annot_min", 1))
                male_values = [-float(value) for value in pyramid_df["Masculin"].tolist()]
                female_values = [float(value) for value in pyramid_df["Féminin"].tolist()]
                male_text = [
                    f"{int(abs(value))}" if annotate_values and abs(value) >= annotation_threshold else ""
                    for value in male_values
                ]
                female_text = [
                    f"{int(value)}" if annotate_values and value >= annotation_threshold else ""
                    for value in female_values
                ]

                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        y=pyramid_df["tranche_age"],
                        x=male_values,
                        name="Masculin",
                        orientation="h",
                        marker=dict(color="#1c2333"),
                        text=male_text,
                        textposition="outside",
                        cliponaxis=False,
                    )
                )
                fig.add_trace(
                    go.Bar(
                        y=pyramid_df["tranche_age"],
                        x=female_values,
                        name="Féminin",
                        orientation="h",
                        marker=dict(color="#e11d1d"),
                        text=female_text,
                        textposition="outside",
                        cliponaxis=False,
                    )
                )
                max_value = max([abs(value) for value in male_values + female_values] + [0])
                fig.update_layout(
                    barmode="relative",
                    height=360,
                    xaxis=dict(
                        range=[-max_value * 1.15, max_value * 1.15] if max_value else None,
                        tickvals=[-max_value, -max_value / 2, 0, max_value / 2, max_value] if max_value else None,
                        ticktext=[
                            f"{int(max_value)}",
                            f"{int(max_value / 2)}",
                            "0",
                            f"{int(max_value / 2)}",
                            f"{int(max_value)}",
                        ] if max_value else None,
                        title="Nombre de lignes",
                    ),
                    yaxis=dict(title="Tranche d'âge", categoryorder="array", categoryarray=pyramid_df["tranche_age"].tolist()),
                    legend=dict(orientation="h"),
                )
                st_plot(
                    fig,
                    key=f"overview_generic_pyramid_{cycle_key}",
                    height=360,
                    annotate_values=False,
                )
            elif not age_df.empty:
                render_panel_title("Tranches d'âge")
                fig = px.bar(
                    age_df,
                    x="tranche_age",
                    y="nombre_lignes",
                    color_discrete_sequence=["#d77a0f"],
                )
                fig.update_layout(height=360, showlegend=False, xaxis_tickangle=-25)
                st_plot(fig, key=f"overview_generic_age_bis_{cycle_key}", height=360)


def _render_epargne_overview_standard(df: pd.DataFrame) -> None:
    config = GENERIC_OVERVIEW_CONFIG["epargne"]
    render_kpi_cards(_build_generic_cycle_cards(df, "epargne"))

    date_column = get_cycle_primary_date_column(df, "epargne")
    period_df = build_cycle_period_series(df, "epargne")
    amount_frame, amount_column = _prepare_amount_frame(df, config.get("amount_columns", []))

    render_summary_box(
        "À retenir pour l'épargne",
        [
            "Cette vue conserve uniquement les graphiques standard utiles pour une lecture rapide du portefeuille d'épargne.",
            f"Date utilisée : `{date_column}`." if date_column else "Aucune date principale n'a été détectée dans les données.",
            "Les analyses de risque, de qualité et de surveillance détaillée sont regroupées dans leurs onglets dédiés.",
        ],
    )

    top_left, top_right = st.columns((1, 1))

    with top_left:
        product_df = build_frequency_table(df, "type_produit", top_n=10)
        if not product_df.empty:
            render_panel_title("Produits d'épargne")
            fig = px.bar(
                product_df,
                x="type_produit",
                y="nombre_lignes",
                color="nombre_lignes",
                color_continuous_scale=["#d8e7fb", "#4b84d7", "#0b4ea2"],
            )
            fig.update_layout(coloraxis_showscale=False)
            style_standard_vertical_bar(fig, height=360, tickangle=-20)
            st_plot(fig, key="overview_epargne_product_distribution", height=360)
        else:
            st.info("Aucune distribution des produits d'épargne n'est disponible.")

    with top_right:
        if not period_df.empty:
            render_panel_title("Activité mensuelle")
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=period_df["periode"],
                    y=period_df["nombre_lignes"],
                    mode="lines+markers",
                    line=dict(color="#2b74ca", width=3),
                    marker=dict(size=7, color="#2b74ca"),
                    fill="tozeroy",
                    fillcolor="rgba(43,116,202,0.12)",
                    hovertemplate="%{x}<br>%{y} compte(s)<extra></extra>",
                )
            )
            style_standard_line(fig, height=360, tickangle=-25)
            st_plot(fig, key="overview_epargne_period", height=360)
        else:
            st.info("Aucune évolution dans le temps n'a pu être construite pour l'épargne.")

    mid_left, mid_right = st.columns((1, 1))

    with mid_left:
        if amount_column:
            grouped_df = build_grouped_amounts(amount_frame, "type_produit", amount_column=amount_column, top_n=10)
            if not grouped_df.empty:
                render_panel_title("Soldes par produit")
                fig = px.bar(
                    grouped_df.sort_values(amount_column, ascending=True),
                    x=amount_column,
                    y="type_produit",
                    orientation="h",
                    color_discrete_sequence=["#4b84d7"],
                )
                style_standard_horizontal_bar(fig, height=360)
                st_plot(fig, key="overview_epargne_group_amount", height=360)
            else:
                st.info("Aucun regroupement de soldes par produit n'est disponible.")

    with mid_right:
        agent_df = build_epargne_agent_portfolio_table(df, top_n=10)
        if not agent_df.empty:
            render_panel_title("Gestionnaires")
            fig = px.bar(
                agent_df.sort_values("solde_total", ascending=True),
                x="solde_total",
                y="agent_credit",
                orientation="h",
                color_discrete_sequence=["#3a9158"],
            )
            style_standard_horizontal_bar(fig, height=360)
            st_plot(fig, key="overview_epargne_agent_portfolio", height=360)
        else:
            st.info("Aucun regroupement par gestionnaire n'est disponible.")

    sex_left, sex_center, sex_right = st.columns((0.18, 0.64, 0.18))

    with sex_center:
        sex_df = build_sex_distribution(df)
        if not sex_df.empty:
            render_panel_title("Sexe")
            fig = px.pie(
                sex_df,
                names="sexe",
                values="nombre_lignes",
                hole=0.55,
                color="sexe",
                color_discrete_map={
                    "Masculin": "#1c2333",
                    "Féminin": "#d71920",
                    "Inconnu": "#a7a9ac",
                },
            )
            style_standard_donut(fig, height=360)
            st_plot(fig, key="overview_epargne_sex", height=360)
        else:
            st.info("La répartition par sexe n'est pas disponible.")


def render_overview_tab(df: pd.DataFrame, monthly_df: pd.DataFrame, cycle_key: str = "credit") -> None:
    if df.empty:
        st.warning("Aucune ligne ne correspond aux filtres choisis.")
        return

    render_panel_title("Vue d'ensemble")
    if cycle_key in CREDIT_LIKE_CYCLES:
        _render_credit_like_overview(df, monthly_df, cycle_key)
        return
    if cycle_key == "epargne":
        _render_epargne_overview_standard(df)
        return
    _render_generic_cycle_overview(df, cycle_key)
