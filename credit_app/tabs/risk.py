from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.core import format_currency, format_percent
from credit_app.cycles import get_cycle_analysis_preset, get_cycle_spec
from credit_app.domain import (
    build_activity_table,
    build_cycle_priority_actions,
    build_cycle_watchlist,
    build_delay_bucket_table,
    build_epargne_phone_quality_table,
    build_frequency_table,
    build_operational_snapshot,
    build_risk_distribution,
    get_first_existing_column,
)
from credit_app.ui import (
    render_kpi_cards,
    render_panel_title,
    render_summary_box,
    st_plot,
    style_standard_donut,
    style_standard_histogram,
    style_standard_vertical_bar,
)


def _resolve_amount_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def render_risk_tab(df: pd.DataFrame, cycle_key: str = "credit") -> None:
    if df.empty:
        st.warning("Aucune donnée disponible pour cet onglet.")
        return

    cycle_spec = get_cycle_spec(cycle_key)
    preset = get_cycle_analysis_preset(cycle_key)
    snapshot = build_operational_snapshot(df)
    watchlist = build_cycle_watchlist(df, cycle_key)
    status_column = get_first_existing_column(df, preset.get("status_columns", []))
    amount_column = _resolve_amount_column(df, preset.get("amount_columns", []))
    primary_group = get_first_existing_column(df, preset.get("group_columns", []))

    render_panel_title("Risque et anomalies")
    render_kpi_cards(
        [
            ("Éléments signalés", f"{len(watchlist):,}".replace(",", " "), "Watchlist active", "slate"),
            ("Risque élevé", f"{snapshot['high_risk_count']:,}".replace(",", " "), "Vigilance maximale", "slate"),
            ("Risque moyen", f"{snapshot['medium_risk_count']:,}".replace(",", " "), "À monitorer", "slate"),
            ("Retards", f"{snapshot['delayed_count']:,}".replace(",", " "), "Retards identifiés", "slate"),
            (
                "Endettement moyen",
                format_percent(snapshot["taux_endettement_moyen"]),
                "Charges / revenu",
                "slate",
            ),
            (
                "Montant exposé",
                format_currency(
                    next(
                        (
                            value
                            for value in [snapshot.get("montant_accorde_total"), snapshot.get("montant_demande_total")]
                            if value is not None
                        ),
                        None,
                    )
                ),
                "Volume documenté",
                "slate",
            ),
        ]
    )
    render_summary_box(
        "Lecture risque",
        [
            f"Cet espace consolide les signaux d'alerte du {cycle_spec['label']}.",
            *build_cycle_priority_actions(df, cycle_key)[:3],
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
            style_standard_vertical_bar(fig, height=360, tickangle=0)
            st_plot(fig, key=f"risk_distribution_{cycle_key}", height=360)
        elif status_column:
            status_df = build_frequency_table(df, status_column, top_n=10)
            if not status_df.empty:
                render_panel_title(f"Distribution de {status_column.replace('_', ' ')}")
                fig = px.bar(status_df, x=status_column, y="nombre_lignes", color_discrete_sequence=["#2b74ca"])
                style_standard_vertical_bar(fig, height=360, tickangle=-25)
                st_plot(fig, key=f"risk_status_distribution_{cycle_key}", height=360)

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
                style_standard_histogram(fig, height=360)
                st_plot(fig, key=f"risk_debt_hist_{cycle_key}", height=360)
        elif amount_column:
            amount_base = df.dropna(subset=[amount_column]).copy()
            if not amount_base.empty:
                render_panel_title(f"Distribution de {amount_column.replace('_', ' ')}")
                fig = px.histogram(
                    amount_base,
                    x=amount_column,
                    nbins=20,
                    color_discrete_sequence=["#102a43"],
                )
                style_standard_histogram(fig, height=360)
                st_plot(fig, key=f"risk_amount_hist_{cycle_key}", height=360)

    lower_left, lower_right = st.columns(2)

    with lower_left:
        if cycle_key in {"credit", "likelemba"} and "statut_remboursement" in df.columns:
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
            style_standard_donut(fig, height=360)
            st_plot(fig, key=f"risk_reimbursement_pie_{cycle_key}", height=360)
        elif status_column:
            status_df = build_frequency_table(df, status_column, top_n=8)
            if not status_df.empty:
                render_panel_title(f"Répartition de {status_column.replace('_', ' ')}")
                fig = px.pie(
                    status_df,
                    names=status_column,
                    values="nombre_lignes",
                    hole=0.45,
                    color_discrete_sequence=["#2b74ca", "#4b84d7", "#9fbce8", "#dbe8f9"],
                )
                style_standard_donut(fig, height=360)
                st_plot(fig, key=f"risk_status_pie_{cycle_key}", height=360)

    with lower_right:
        if cycle_key == "epargne":
            phone_df = build_epargne_phone_quality_table(df)
            if not phone_df.empty:
                render_panel_title("Qualité des téléphones")
                fig = px.pie(
                    phone_df,
                    names="qualite_telephone",
                    values="nombre_lignes",
                    hole=0.55,
                    color="qualite_telephone",
                    color_discrete_map={
                        "Format international": "#2b74ca",
                        "Format local": "#4b84d7",
                        "Autre format": "#d77a0f",
                        "Manquant": "#a7a9ac",
                    },
                )
                style_standard_donut(fig, height=360)
                st_plot(fig, key="risk_epargne_phone_quality", height=360)
            elif not watchlist.empty and "motif_alerte" in watchlist.columns:
                reason_df = watchlist["motif_alerte"].astype("string").str.split("; ").explode().dropna().to_frame("motif_alerte")
                reason_df = (
                    reason_df.groupby("motif_alerte", dropna=False)
                    .size()
                    .reset_index(name="nombre_lignes")
                    .sort_values("nombre_lignes", ascending=False)
                )
                if not reason_df.empty:
                    render_panel_title("Motifs d'alerte")
                    fig = px.bar(
                        reason_df,
                        x="motif_alerte",
                        y="nombre_lignes",
                        color_discrete_sequence=["#c05621"],
                    )
                    style_standard_vertical_bar(fig, height=360, tickangle=-25)
                    st_plot(fig, key=f"risk_alert_reasons_{cycle_key}", height=360)
        else:
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
                style_standard_vertical_bar(fig, height=360, tickangle=0)
                st_plot(fig, key=f"risk_delay_buckets_{cycle_key}", height=360)
            elif not watchlist.empty and "motif_alerte" in watchlist.columns:
                reason_df = watchlist["motif_alerte"].astype("string").str.split("; ").explode().dropna().to_frame("motif_alerte")
                reason_df = (
                    reason_df.groupby("motif_alerte", dropna=False)
                    .size()
                    .reset_index(name="nombre_lignes")
                    .sort_values("nombre_lignes", ascending=False)
                )
                if not reason_df.empty:
                    render_panel_title("Motifs d'alerte")
                    fig = px.bar(
                        reason_df,
                        x="motif_alerte",
                        y="nombre_lignes",
                        color_discrete_sequence=["#c05621"],
                    )
                    style_standard_vertical_bar(fig, height=360, tickangle=-25)
                    st_plot(fig, key=f"risk_alert_reasons_{cycle_key}", height=360)

    if primary_group:
        group_risk = build_activity_table(
            df,
            primary_group,
            amount_columns=preset.get("amount_columns", []),
            alert_index=watchlist.index if not watchlist.empty else None,
            top_n=8,
        )
        if not group_risk.empty:
            render_panel_title(f"Zones les plus exposées par {primary_group.replace('_', ' ')}")
            st.dataframe(group_risk, width="stretch", hide_index=True)

    render_panel_title("Watchlist risque")
    if watchlist.empty:
        st.success("Aucune ligne d'alerte n'a été détectée sur le périmètre courant.")
    else:
        st.dataframe(watchlist.head(200), width="stretch", hide_index=True)
