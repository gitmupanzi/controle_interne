from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from credit_app.core import format_currency, format_percent
from credit_app.domain import (
    build_age_bucket_table,
    build_age_sex_pyramid_table,
    build_frequency_table,
    build_grouped_amounts,
    build_operational_snapshot,
    build_overview_narrative,
    build_sex_distribution,
    build_status_distribution,
    build_summary_metrics,
)
from credit_app.ui import render_kpi_cards, render_panel_title, render_summary_box, st_plot


def render_overview_tab(df: pd.DataFrame, monthly_df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Aucune ligne ne correspond aux filtres sélectionnés.")
        return

    metrics = build_summary_metrics(df)
    snapshot = build_operational_snapshot(df)
    render_panel_title("Vue d'ensemble")
    render_kpi_cards(
        [
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
    )
    render_summary_box(
        "Lecture opérationnelle",
        [
            f"{metrics['nombre_dossiers']:,}".replace(",", " ") + " dossiers sont inclus dans le périmètre courant.",
            "Les graphiques ci-dessous servent à orienter la décision avant lecture détaillée.",
            "Les tableaux de suivi et les listes d'action sont regroupés plus bas dans l'onglet Surveillance.",
        ],
    )

    render_panel_title("Briefing automatique")
    render_summary_box(
        "Narratif standard",
        [build_overview_narrative(df)],
    )

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
            st_plot(fig, key="overview_status_distribution", height=380)

    with right:
        if not monthly_df.empty:
            render_panel_title("Évolution mensuelle des demandes")
            fig = px.line(
                monthly_df,
                x="mois_demande",
                y="nombre_dossiers",
                markers=True,
            )
            fig.update_traces(
                line_color="#2f855a",
                marker_color="#2f855a",
                line=dict(width=3),
                marker=dict(size=7),
            )
            fig.update_layout(height=380)
            st_plot(fig, key="overview_monthly_line", height=380)

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
            st_plot(fig, key="overview_risk_pie", height=340)

    with risk_right:
        age_df = build_age_bucket_table(df)
        if not age_df.empty:
            render_panel_title("Distribution par tranche d'âge")
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
            st_plot(fig, key="overview_age_buckets", height=340)

    demo_left, demo_right = st.columns((1, 1.2))

    with demo_left:
        sex_df = build_sex_distribution(df)
        if not sex_df.empty:
            render_panel_title("Répartition par sexe")
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
            st_plot(fig, key="overview_sex_pie", height=360)

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
            max_value = max(
                [abs(value) for value in male_values + female_values] + [0]
            )
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
            st_plot(fig, key="overview_age_sex_pyramid", height=360, annotate_values=False)
