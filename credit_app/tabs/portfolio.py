from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.core import format_currency, format_percent
from credit_app.domain import (
    build_group_summary_table,
    build_grouped_amounts,
    build_operational_snapshot,
    build_status_flow_table,
    build_watchlist,
)
from credit_app.ui import render_kpi_cards, render_panel_title, render_summary_box, st_plot


def render_portfolio_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Aucune donnee disponible pour cet onglet.")
        return

    snapshot = build_operational_snapshot(df)
    agency_count = int(df["agence"].dropna().nunique()) if "agence" in df.columns else 0
    product_count = int(df["type_produit"].dropna().nunique()) if "type_produit" in df.columns else 0
    agent_count = int(df["agent_credit"].dropna().nunique()) if "agent_credit" in df.columns else 0

    render_panel_title("Portefeuille et production")
    render_kpi_cards(
        [
            ("Agences", f"{agency_count:,}".replace(",", " "), "Couverture active", "blue"),
            ("Produits", f"{product_count:,}".replace(",", " "), "Gammes presentes", "navy"),
            ("Agents", f"{agent_count:,}".replace(",", " "), "Acteurs visibles", "green"),
            (
                "Montant demande",
                format_currency(snapshot["montant_demande_total"]),
                "Perimetre courant",
                "orange",
            ),
            (
                "Montant accorde",
                format_currency(snapshot["montant_accorde_total"]),
                "Production engagee",
                "green",
            ),
            (
                "Approbation",
                format_percent(snapshot["taux_approbation"]),
                "Conversion du pipeline",
                "blue",
            ),
        ]
    )
    render_summary_box(
        "Lecture portefeuille",
        [
            "Cet espace met en avant la production par produit, agent et agence.",
            f"L'agence la plus active est {snapshot['top_agence']} et le produit dominant est {snapshot['top_produit']}.",
        ],
    )

    col1, col2 = st.columns(2)

    with col1:
        product_amounts = build_grouped_amounts(df, "type_produit")
        if not product_amounts.empty:
            render_panel_title("Montant demande par produit")
            fig = px.bar(
                product_amounts,
                x="type_produit",
                y="montant_demande",
                color="montant_demande",
                color_continuous_scale=["#d9a441", "#1f7a5c", "#102a43"],
            )
            fig.update_layout(height=360, coloraxis_showscale=False)
            st_plot(fig, key="portfolio_product_amounts", height=360)
        else:
            st.info("La colonne `type_produit` n'est pas disponible.")

    with col2:
        agent_amounts = build_grouped_amounts(df, "agent_credit")
        if not agent_amounts.empty:
            render_panel_title("Top agents par montant demande")
            fig = px.bar(
                agent_amounts,
                x="agent_credit",
                y="montant_demande",
                color="montant_demande",
                color_continuous_scale=["#d9a441", "#1f7a5c", "#102a43"],
            )
            fig.update_layout(height=360, coloraxis_showscale=False)
            st_plot(fig, key="portfolio_agent_amounts", height=360)
        else:
            st.info("La colonne `agent_credit` n'est pas disponible.")

    lower_left, lower_right = st.columns((1, 1.15))

    with lower_left:
        flow_df = build_status_flow_table(df)
        if not flow_df.empty:
            render_panel_title("Flux des statuts de dossier")
            fig = px.bar(
                flow_df,
                x="statut_dossier",
                y="nombre_dossiers",
                color="nombre_dossiers",
                color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
            )
            fig.update_layout(height=340, coloraxis_showscale=False)
            st_plot(fig, key="portfolio_status_flow", height=340)

    with lower_right:
        agency_summary = build_group_summary_table(df, "agence", top_n=8)
        if not agency_summary.empty:
            render_panel_title("Top agences actives")
            st.dataframe(agency_summary, width="stretch", hide_index=True)

    product_summary = build_group_summary_table(df, "type_produit", top_n=8)
    if not product_summary.empty:
        render_panel_title("Top produits actifs")
        st.dataframe(product_summary, width="stretch", hide_index=True)

    if {"agence", "statut_dossier", "montant_demande"}.issubset(df.columns):
        pivot = pd.pivot_table(
            df,
            index="agence",
            columns="statut_dossier",
            values="montant_demande",
            aggfunc="sum",
            fill_value=0,
        )
        render_panel_title("Lecture croisee agence x statut")
        st.dataframe(pivot, width="stretch")

    watchlist = build_watchlist(df)
    render_panel_title("Dossiers sensibles a suivre")
    if watchlist.empty:
        st.success("Aucun dossier sensible n'a ete detecte selon les regles actuelles.")
    else:
        st.dataframe(watchlist.head(200), width="stretch", hide_index=True)
