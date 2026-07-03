from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.domain import build_epargne_kyc_completeness_table
from credit_app.ui import (
    render_kpi_cards,
    render_panel_title,
    render_summary_box,
    st_plot,
    style_standard_donut,
    style_standard_vertical_bar,
)


def render_quality_tab(
    raw_df: pd.DataFrame,
    standardized_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    missing_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    cycle_key: str = "credit",
) -> None:
    total_anomalies = int(quality_df["nombre_lignes"].sum()) if not quality_df.empty else 0
    missing_critical = (
        int((missing_df["taux_manquant"] >= 0.3).sum())
        if not missing_df.empty and "taux_manquant" in missing_df.columns
        else 0
    )
    renamed_columns = (
        int((mapping_df["colonne_source"] != mapping_df["colonne_standard"]).sum())
        if not mapping_df.empty
        else 0
    )
    standardized_rate = (renamed_columns / len(mapping_df)) if len(mapping_df) else 0.0

    render_panel_title("Qualité et standardisation")
    render_kpi_cards(
        [
            ("Colonnes source", str(raw_df.shape[1]), "Avant standardisation", "blue"),
            ("Colonnes standard", str(standardized_df.shape[1]), "Après harmonisation", "navy"),
            ("Anomalies", f"{total_anomalies:,}".replace(",", " "), "Somme des contrôles", "red"),
            ("Colonnes critiques", str(missing_critical), "Missing >= 30%", "orange"),
            ("Colonnes reconnues", str(renamed_columns), "Renommage automatique", "green"),
            ("Taux de mapping", f"{standardized_rate * 100:.1f}%", "Couverture des aliases", "slate"),
        ]
    )
    render_summary_box(
        "Lecture qualité",
        [
            "Cet onglet consolide les anomalies, les valeurs manquantes et le mapping des colonnes source.",
            f"{missing_critical} colonne(s) présentent au moins 30% de valeurs manquantes.",
            "Le mapping combine les alias internes et la référence externe data/Rename_columns.xlsx.",
        ],
    )

    if not quality_df.empty:
        render_panel_title("Contrôles qualité")
        st.dataframe(quality_df, width="stretch", hide_index=True)

        fig = px.bar(
            quality_df,
            x="controle",
            y="nombre_lignes",
            color="nombre_lignes",
            color_continuous_scale=["#d9a441", "#c05621", "#9b2c2c"],
        )
        fig.update_layout(coloraxis_showscale=False)
        style_standard_vertical_bar(fig, height=360, tickangle=-25)
        st_plot(fig, key="quality_anomalies_bar", height=360)

    chart_left, chart_right = st.columns(2)

    with chart_left:
        if not missing_df.empty:
            render_panel_title("Colonnes les plus incomplètes")
            missing_top = missing_df.head(12).copy()
            fig = px.bar(
                missing_top,
                x="colonne",
                y="taux_manquant",
                color="taux_manquant",
                color_continuous_scale=["#dbe8f9", "#f09b39", "#b9353f"],
            )
            fig.update_layout(coloraxis_showscale=False)
            style_standard_vertical_bar(fig, height=360, tickangle=-25)
            fig.update_yaxes(tickformat=".0%")
            st_plot(fig, key="quality_missing_bar", height=360)

    with chart_right:
        if not mapping_df.empty:
            render_panel_title("Couverture du mapping")
            mapping_status = pd.DataFrame(
                {
                    "statut_mapping": ["Colonnes reconnues", "Colonnes conservées"],
                    "nombre_colonnes": [
                        renamed_columns,
                        max(len(mapping_df) - renamed_columns, 0),
                    ],
                }
            )
            fig = px.pie(
                mapping_status,
                names="statut_mapping",
                values="nombre_colonnes",
                hole=0.5,
                color="statut_mapping",
                color_discrete_map={
                    "Colonnes reconnues": "#1f7a5c",
                    "Colonnes conservées": "#7b8794",
                },
            )
            style_standard_donut(fig, height=360)
            st_plot(fig, key="quality_mapping_pie", height=360)

    left, right = st.columns(2)

    with left:
        render_panel_title("Valeurs manquantes")
        st.dataframe(missing_df.head(25), width="stretch", hide_index=True)

    with right:
        render_panel_title("Mapping des colonnes")
        st.dataframe(mapping_df, width="stretch", hide_index=True)

    if cycle_key == "epargne":
        kyc_df = build_epargne_kyc_completeness_table(standardized_df)
        render_panel_title("Complétude KYC")
        if kyc_df.empty:
            st.info("La complétude KYC n'a pas pu être calculée sur le périmètre actif.")
        else:
            kyc_left, kyc_right = st.columns((1, 1))
            with kyc_left:
                fig = px.bar(
                    kyc_df,
                    x="classe_completude",
                    y="nombre_lignes",
                    color_discrete_sequence=["#d77a0f"],
                )
                style_standard_vertical_bar(fig, height=340, tickangle=-20)
                st_plot(fig, key="quality_epargne_kyc", height=340)
            with kyc_right:
                st.dataframe(kyc_df, width="stretch", hide_index=True)
