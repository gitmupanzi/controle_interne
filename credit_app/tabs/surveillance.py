from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.core import format_currency
from credit_app.cycles import get_cycle_analysis_preset, get_cycle_spec
from credit_app.domain import (
    build_activity_table,
    build_cycle_priority_actions,
    build_cycle_watchlist,
    build_epargne_dormancy_table,
    build_epargne_multi_account_clients,
    build_epargne_multi_account_table,
    build_operational_snapshot,
    build_provenance_summary_table,
    build_summary_metrics,
    get_first_existing_column,
)
from credit_app.ui import (
    render_panel_title,
    render_summary_box,
    st_plot,
    style_standard_horizontal_bar,
    style_standard_vertical_bar,
)

COLUMN_LABELS = {
    "agence": "agences",
    "type_produit": "produits",
    "agent_credit": "agents de crédit",
    "nom_groupe": "groupes",
    "type_operation": "types d'opération",
    "statut_compte": "statuts de compte",
    "caissier": "caissiers",
    "banque": "banques",
    "compte_bancaire": "comptes bancaires",
    "journal": "journaux",
    "compte_comptable": "comptes comptables",
    "fonction": "fonctions",
    "statut_agent": "statuts d'agent",
    "application_source": "applications",
    "profil_acces": "profils d'accès",
    "type_sauvegarde": "types de sauvegarde",
    "support_sauvegarde": "supports",
    "operateur": "opérateurs",
    "tresorier": "trésoriers",
}


def _group_title(column: str) -> str:
    return f"Top {COLUMN_LABELS.get(column, column.replace('_', ' '))} actives"


def _build_watchlist_reason_table(watchlist: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if watchlist.empty or "motif_alerte" not in watchlist.columns:
        return pd.DataFrame(columns=["motif_alerte", "nombre_lignes"])

    motifs = (
        watchlist["motif_alerte"]
        .dropna()
        .astype("string")
        .str.split("; ")
        .explode()
        .dropna()
        .astype("string")
        .str.strip()
    )
    motifs = motifs[motifs.ne("")]
    if motifs.empty:
        return pd.DataFrame(columns=["motif_alerte", "nombre_lignes"])

    reason_df = motifs.value_counts().head(top_n).rename_axis("motif_alerte").reset_index(name="nombre_lignes")
    return reason_df


def _render_epargne_surveillance_block(df: pd.DataFrame, watchlist: pd.DataFrame) -> None:
    dormancy_df = build_epargne_dormancy_table(df)
    multi_account_df = build_epargne_multi_account_table(df)
    multi_clients_df = build_epargne_multi_account_clients(df, top_n=15)
    provenance_df = build_provenance_summary_table(df)
    watchlist_reasons_df = _build_watchlist_reason_table(watchlist)

    top_left, top_right = st.columns((1, 1))

    with top_left:
        if not dormancy_df.empty:
            render_panel_title("Dormance sous surveillance")
            fig = px.bar(
                dormancy_df,
                x="classe_inactivite",
                y="nombre_lignes",
                color_discrete_sequence=["#2b74ca"],
            )
            style_standard_vertical_bar(fig, height=320, tickangle=-20)
            st_plot(fig, key="surveillance_epargne_dormancy", height=320)
        else:
            st.info("La dormance n'est pas disponible sur le périmètre actif.")

    with top_right:
        if not multi_account_df.empty:
            render_panel_title("Clients multi-comptes")
            fig = px.bar(
                multi_account_df,
                x="classe_comptes",
                y="nombre_clients",
                color_discrete_sequence=["#4b84d7"],
            )
            style_standard_vertical_bar(fig, height=320, tickangle=-20)
            st_plot(fig, key="surveillance_epargne_multi_accounts", height=320)
        else:
            st.info("Aucune distribution multi-comptes n'est disponible sur le périmètre actif.")

    mid_left, mid_right = st.columns((1, 1))

    with mid_left:
        render_panel_title("Top clients multi-comptes")
        if multi_clients_df.empty:
            st.info("Aucun client multi-comptes n'a été détecté.")
        else:
            st.dataframe(multi_clients_df, width="stretch", hide_index=True)

    with mid_right:
        if not provenance_df.empty and len(provenance_df) > 1:
            render_panel_title("Comparaison des extractions")
            st.dataframe(provenance_df, width="stretch", hide_index=True)
        else:
            st.info("Une seule extraction est disponible sur le périmètre actif.")

    if not watchlist_reasons_df.empty:
        render_panel_title("Répartition des motifs de vigilance")
        fig = px.bar(
            watchlist_reasons_df,
            x="nombre_lignes",
            y="motif_alerte",
            orientation="h",
            color_discrete_sequence=["#2b74ca"],
        )
        style_standard_horizontal_bar(fig, height=360)
        fig.update_layout(yaxis=dict(categoryorder="total ascending"))
        st_plot(fig, key="surveillance_epargne_watchlist_reasons", height=360)

    if not watchlist.empty:
        high_attention_count = len(watchlist)
        render_summary_box(
            "Lecture de vigilance épargne",
            [
                f"{high_attention_count:,}".replace(",", " ")
                + " compte(s) sont actuellement signalés dans la watchlist active.",
                "Les blocs ci-dessus aident à prioriser la dormance, les multi-comptes et les écarts entre extractions.",
            ],
        )


def render_surveillance_tab(df: pd.DataFrame, cycle_key: str = "credit") -> None:
    if df.empty:
        st.warning("Aucune ligne ne correspond aux filtres sélectionnés.")
        return

    cycle_spec = get_cycle_spec(cycle_key)
    preset = get_cycle_analysis_preset(cycle_key)
    snapshot = build_operational_snapshot(df)
    metrics = build_summary_metrics(df)
    watchlist = build_cycle_watchlist(df, cycle_key)
    group_columns = [column for column in preset.get("group_columns", []) if column in df.columns]
    primary_group = group_columns[0] if group_columns else None
    secondary_group = group_columns[1] if len(group_columns) > 1 else None

    render_panel_title("Surveillance opérationnelle")
    render_summary_box(
        "Lecture de surveillance",
        [
            f"Cet onglet regroupe les actions prioritaires et les classements opérationnels du {cycle_spec['label']}.",
            "La synthèse du haut reste réservée aux KPI standard et aux graphiques standard.",
            f"{len(watchlist):,}".replace(",", " ")
            + f" élément(s) sont actuellement signalés dans les {preset['record_label'].lower()}.",
        ],
    )

    action_col, snapshot_col = st.columns((1.2, 1))

    with action_col:
        render_panel_title("Actions prioritaires")
        render_summary_box("Focus de gestion", build_cycle_priority_actions(df, cycle_key))

    with snapshot_col:
        top_dimension = primary_group or get_first_existing_column(df, ["agence", "type_operation", "banque", "journal"])
        top_message = "Aucune dimension principale n'est disponible."
        if top_dimension:
            top_value_series = df[top_dimension].dropna().astype("string").str.strip()
            if not top_value_series.empty:
                top_value = top_value_series.value_counts().index[0]
                top_message = f"Le périmètre `{top_dimension}` le plus actif est **{top_value}**."

        montant_reference = next(
            (
                value
                for value in [
                    metrics.get("montant_demande_total"),
                    metrics.get("montant_accorde_total"),
                ]
                if value is not None
            ),
            None,
        )
        render_panel_title("Bloc de surveillance")
        render_summary_box(
            "Points de contrôle immédiats",
            [
                top_message,
                "Volume financier observé : " + format_currency(montant_reference) + ".",
                f"{snapshot['high_risk_count']:,}".replace(",", " ") + " ligne(s) portent un risque élevé documenté.",
            ],
        )

    ranking_left, ranking_right = st.columns((1.1, 1))
    amount_columns = preset.get("amount_columns", [])

    with ranking_left:
        if primary_group:
            ranking_df = build_activity_table(
                df,
                primary_group,
                amount_columns=amount_columns,
                alert_index=watchlist.index if not watchlist.empty else None,
                top_n=8,
            )
            if not ranking_df.empty:
                render_panel_title(_group_title(primary_group))
                st.dataframe(ranking_df, width="stretch", hide_index=True)
            else:
                st.info("Aucun classement principal n'est disponible sur le périmètre courant.")
        else:
            st.info("Aucune dimension principale n'est disponible pour ce cycle.")

    with ranking_right:
        if secondary_group:
            ranking_df = build_activity_table(
                df,
                secondary_group,
                amount_columns=amount_columns,
                alert_index=watchlist.index if not watchlist.empty else None,
                top_n=8,
            )
            if not ranking_df.empty:
                render_panel_title(_group_title(secondary_group))
                st.dataframe(ranking_df, width="stretch", hide_index=True)
            else:
                st.info("Aucun classement secondaire n'est disponible sur le périmètre courant.")
        else:
            st.info("Aucune seconde dimension n'est disponible pour ce cycle.")

    if cycle_key == "epargne":
        _render_epargne_surveillance_block(df, watchlist)

    render_panel_title("Éléments à suivre en priorité")
    if not watchlist.empty:
        st.dataframe(watchlist.head(50), width="stretch", hide_index=True)
    else:
        st.success("Aucun élément prioritaire n'a été détecté avec les règles de surveillance actuelles.")

    render_panel_title("Aperçu des données filtrées")
    preview_columns = [column for column in df.columns if column not in {"mois_demande"}]
    st.dataframe(df[preview_columns].head(200), width="stretch", hide_index=True)
