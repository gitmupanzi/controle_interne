from __future__ import annotations

import pandas as pd
import streamlit as st

from credit_app.core import format_currency
from credit_app.domain import (
    build_group_summary_table,
    build_operational_snapshot,
    build_priority_actions,
    build_watchlist,
)
from credit_app.ui import render_panel_title, render_summary_box


def render_surveillance_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Aucune ligne ne correspond aux filtres sélectionnés.")
        return

    snapshot = build_operational_snapshot(df)
    render_panel_title("Surveillance opérationnelle")
    render_summary_box(
        "Lecture de surveillance",
        [
            "Cet onglet regroupe les blocs d'action, les classements actifs et les dossiers à suivre en priorité.",
            "La synthèse du haut reste réservée aux KPI standard et aux graphiques standard.",
            f"{snapshot['high_risk_count']:,}".replace(",", " ")
            + " dossiers sont en risque élevé et "
            + f"{snapshot['overdue_30_count']:,}".replace(",", " ")
            + " dépassent 30 jours de retard.",
        ],
    )

    action_col, snapshot_col = st.columns((1.2, 1))

    with action_col:
        render_panel_title("Actions prioritaires")
        render_summary_box(
            "Focus de gestion",
            build_priority_actions(df),
        )

    with snapshot_col:
        render_panel_title("Bloc de surveillance")
        render_summary_box(
            "Points de contrôle immédiats",
            [
                f"Capacité négative : {snapshot['negative_capacity_count']:,}".replace(",", " ")
                + " dossiers à vérifier rapidement.",
                "Le ticket moyen observe est de " + format_currency(snapshot["montant_moyen_demande"]) + ".",
                "Utilisez les tableaux ci-dessous pour cibler les agences, produits et dossiers qui demandent une revue prioritaire.",
            ],
        )

    ranking_left, ranking_right = st.columns((1.1, 1))

    with ranking_left:
        agency_summary = build_group_summary_table(df, "agence", top_n=8)
        if not agency_summary.empty:
            render_panel_title("Top agences actives")
            st.dataframe(agency_summary, width="stretch", hide_index=True)
        else:
            st.info("Aucune synthèse agence n'est disponible sur le périmètre courant.")

    with ranking_right:
        product_summary = build_group_summary_table(df, "type_produit", top_n=8)
        if not product_summary.empty:
            render_panel_title("Top produits actifs")
            st.dataframe(product_summary, width="stretch", hide_index=True)
        else:
            st.info("Aucune synthèse produit n'est disponible sur le périmètre courant.")

    watchlist = build_watchlist(df)
    render_panel_title("Dossiers à suivre en priorité")
    if not watchlist.empty:
        st.dataframe(watchlist.head(20), width="stretch", hide_index=True)
    else:
        st.info("Aucun dossier prioritaire n'a été détecté avec les règles de surveillance actuelles.")

    render_panel_title("Aperçu des dossiers")
    preview_columns = [column for column in df.columns if column not in {"mois_demande"}]
    st.dataframe(df[preview_columns].head(200), width="stretch", hide_index=True)
