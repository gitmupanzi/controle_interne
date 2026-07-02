from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.core import format_currency, format_percent
from credit_app.domain import (
    build_delay_bucket_table,
    build_operational_snapshot,
    build_priority_actions,
    build_risk_distribution,
    build_risk_group_table,
    build_watchlist,
)
from credit_app.ui import render_kpi_cards, render_panel_title, render_summary_box, st_plot


def render_risk_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Aucune donnée disponible pour cet onglet.")
        return

    snapshot = build_operational_snapshot(df)
    render_panel_title("Risque et remboursement")
    render_kpi_cards(
        [
            ("Risque élevé", f"{snapshot['high_risk_count']:,}".replace(",", " "), "Vigilance maximale", "red"),
            ("Risque moyen", f"{snapshot['medium_risk_count']:,}".replace(",", " "), "À monitorer", "orange"),
            ("Dossiers en retard", f"{snapshot['delayed_count']:,}".replace(",", " "), "Retards identifiés", "navy"),
            ("Retard > 30 j", f"{snapshot['overdue_30_count']:,}".replace(",", " "), "Recouvrement prioritaire", "red"),
            (
                "Endettement moyen",
                format_percent(snapshot["taux_endettement_moyen"]),
                "Charges / revenu",
                "blue",
            ),
            (
                "Montant exposé",
                format_currency(snapshot["montant_accorde_total"]),
                "Encours observe",
                "green",
            ),
        ]
    )
    render_summary_box(
        "Lecture risque",
        [
            "Le niveau de risque calculé combine prioritairement le niveau déclaré, le score, l'endettement puis le retard.",
            *build_priority_actions(df)[:3],
        ],
    )

    left, right = st.columns(2)

    with left:
        risk_df = build_risk_distribution(df)
        if not risk_df.empty:
            render_panel_title("Distribution du risque")
            fig = px.bar(
                risk_df,
                x="niveau_risque_calcule",
                y="nombre_dossiers",
                color="niveau_risque_calcule",
                color_discrete_map={
                    "Faible": "#1f7a5c",
                    "Moyen": "#d9a441",
                    "Élevé": "#c05621",
                    "Non renseigné": "#7b8794",
                },
            )
            fig.update_layout(height=360)
            st_plot(fig, key="risk_distribution", height=360)

    with right:
        if "taux_endettement" in df.columns:
            debt_base = df.dropna(subset=["taux_endettement"]).copy()
            if not debt_base.empty:
                render_panel_title("Distribution du taux d'endettement")
                fig = px.histogram(
                    debt_base,
                    x="taux_endettement",
                    nbins=20,
                    color_discrete_sequence=["#102a43"],
                )
                fig.update_layout(height=360)
                st_plot(fig, key="risk_debt_hist", height=360)
        elif "score_credit" in df.columns:
            score_base = df.dropna(subset=["score_credit"]).copy()
            if not score_base.empty:
                render_panel_title("Distribution du score crédit")
                fig = px.histogram(
                    score_base,
                    x="score_credit",
                    nbins=20,
                    color_discrete_sequence=["#102a43"],
                )
                fig.update_layout(height=360)
                st_plot(fig, key="risk_score_hist", height=360)

    lower_left, lower_right = st.columns(2)

    with lower_left:
        if "statut_remboursement" in df.columns:
            render_panel_title("Statut de remboursement")
            reimbursement_df = (
                df.groupby("statut_remboursement", dropna=False)
                .size()
                .reset_index(name="nombre_dossiers")
                .sort_values("nombre_dossiers", ascending=False)
            )
            fig = px.pie(
                reimbursement_df,
                names="statut_remboursement",
                values="nombre_dossiers",
                hole=0.45,
                color_discrete_sequence=["#1f7a5c", "#d9a441", "#c05621", "#7b8794"],
            )
            fig.update_layout(height=360)
            st_plot(fig, key="risk_reimbursement_pie", height=360)

    with lower_right:
        delay_df = build_delay_bucket_table(df)
        if not delay_df.empty:
            render_panel_title("Classes de retard")
            fig = px.bar(
                delay_df,
                x="classe_retard",
                y="nombre_dossiers",
                color="classe_retard",
                color_discrete_map={
                    "À jour": "#1f7a5c",
                    "1-7 jours": "#d9a441",
                    "8-30 jours": "#e78a1f",
                    "31-90 jours": "#cf4752",
                    "Plus de 90 jours": "#9b2c2c",
                    "Non renseigné": "#7b8794",
                },
            )
            fig.update_layout(height=360, showlegend=False)
            st_plot(fig, key="risk_delay_buckets", height=360)

    agency_risk = build_risk_group_table(df, "agence", top_n=8)
    if not agency_risk.empty:
        render_panel_title("Agences les plus exposées")
        st.dataframe(agency_risk, width="stretch", hide_index=True)

    product_risk = build_risk_group_table(df, "type_produit", top_n=8)
    if not product_risk.empty:
        render_panel_title("Produits les plus exposés")
        st.dataframe(product_risk, width="stretch", hide_index=True)

    render_panel_title("Watchlist risque")
    st.dataframe(build_watchlist(df).head(200), width="stretch", hide_index=True)
