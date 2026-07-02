from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.core import format_currency
from credit_app.cycles import get_cycle_analysis_preset, get_cycle_spec
from credit_app.domain import (
    build_activity_table,
    build_cycle_watchlist,
    build_frequency_table,
    build_grouped_amounts,
    build_status_flow_table,
    get_first_existing_column,
)
from credit_app.ui import render_kpi_cards, render_panel_title, render_summary_box, st_plot


def _resolve_amount_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def render_portfolio_tab(df: pd.DataFrame, cycle_key: str = "credit") -> None:
    if df.empty:
        st.warning("Aucune donnée disponible pour cet onglet.")
        return

    cycle_spec = get_cycle_spec(cycle_key)
    preset = get_cycle_analysis_preset(cycle_key)
    watchlist = build_cycle_watchlist(df, cycle_key)

    group_columns = [column for column in preset.get("group_columns", []) if column in df.columns]
    primary_group = group_columns[0] if group_columns else None
    secondary_group = group_columns[1] if len(group_columns) > 1 else None
    status_column = get_first_existing_column(df, preset.get("status_columns", []))
    actor_column = get_first_existing_column(df, preset.get("actor_columns", []))
    amount_column = _resolve_amount_column(df, preset.get("amount_columns", []))
    primary_count = int(df[primary_group].dropna().nunique()) if primary_group else 0
    secondary_count = int(df[secondary_group].dropna().nunique()) if secondary_group else 0
    actor_count = int(df[actor_column].dropna().nunique()) if actor_column else 0
    amount_total = float(df[amount_column].sum()) if amount_column else None

    render_panel_title("Portefeuille et production")
    render_kpi_cards(
        [
            (preset["record_label"], f"{len(df):,}".replace(",", " "), "Périmètre courant", "slate"),
            (
                primary_group.replace("_", " ").title() if primary_group else "Dimension 1",
                f"{primary_count:,}".replace(",", " "),
                "Catégories actives",
                "slate",
            ),
            (
                secondary_group.replace("_", " ").title() if secondary_group else "Dimension 2",
                f"{secondary_count:,}".replace(",", " "),
                "Sous-catégories actives",
                "slate",
            ),
            (
                actor_column.replace("_", " ").title() if actor_column else "Acteurs",
                f"{actor_count:,}".replace(",", " "),
                "Acteurs visibles",
                "slate",
            ),
            (
                "Montant observé",
                format_currency(amount_total),
                "Total documenté",
                "slate",
            ),
            (
                "Éléments signalés",
                f"{len(watchlist):,}".replace(",", " "),
                "Watchlist active",
                "slate",
            ),
        ]
    )
    render_summary_box(
        "Lecture portefeuille",
        [
            f"Cet espace met en avant les volumes, regroupements et croisements utiles du {cycle_spec['label']}.",
            f"La colonne de regroupement principale est `{primary_group}`." if primary_group else "Aucune dimension principale n'a été détectée.",
        ],
    )

    col1, col2 = st.columns(2)

    with col1:
        if primary_group and amount_column:
            primary_amounts = build_grouped_amounts(df, primary_group, amount_column=amount_column)
            if not primary_amounts.empty:
                render_panel_title(f"Volume par {primary_group.replace('_', ' ')}")
                fig = px.bar(
                    primary_amounts,
                    x=primary_group,
                    y=amount_column,
                    color=amount_column,
                    color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
                )
                fig.update_layout(height=360, coloraxis_showscale=False)
                st_plot(fig, key=f"portfolio_primary_amounts_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement principal monétaire n'est disponible.")
        elif primary_group:
            freq_df = build_frequency_table(df, primary_group, top_n=10)
            if not freq_df.empty:
                render_panel_title(f"Volume par {primary_group.replace('_', ' ')}")
                fig = px.bar(freq_df, x=primary_group, y="nombre_lignes", color_discrete_sequence=["#2b74ca"])
                fig.update_layout(height=360, showlegend=False, xaxis_tickangle=-25)
                st_plot(fig, key=f"portfolio_primary_freq_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement principal n'est disponible.")

    with col2:
        if secondary_group and amount_column:
            secondary_amounts = build_grouped_amounts(df, secondary_group, amount_column=amount_column)
            if not secondary_amounts.empty:
                render_panel_title(f"Top {secondary_group.replace('_', ' ')} par volume")
                fig = px.bar(
                    secondary_amounts,
                    x=secondary_group,
                    y=amount_column,
                    color=amount_column,
                    color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
                )
                fig.update_layout(height=360, coloraxis_showscale=False)
                st_plot(fig, key=f"portfolio_secondary_amounts_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement secondaire monétaire n'est disponible.")
        elif secondary_group:
            freq_df = build_frequency_table(df, secondary_group, top_n=10)
            if not freq_df.empty:
                render_panel_title(f"Top {secondary_group.replace('_', ' ')} actives")
                fig = px.bar(freq_df, x=secondary_group, y="nombre_lignes", color_discrete_sequence=["#4b84d7"])
                fig.update_layout(height=360, showlegend=False, xaxis_tickangle=-25)
                st_plot(fig, key=f"portfolio_secondary_freq_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement secondaire n'est disponible.")

    lower_left, lower_right = st.columns((1, 1.15))

    with lower_left:
        if cycle_key in {"credit", "likelemba"} and "statut_dossier" in df.columns:
            flow_df = build_status_flow_table(df)
            if not flow_df.empty:
                render_panel_title("Flux des statuts")
                fig = px.bar(
                    flow_df,
                    x="statut_dossier",
                    y="nombre_dossiers",
                    color="nombre_dossiers",
                    color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
                )
                fig.update_layout(height=340, coloraxis_showscale=False)
                st_plot(fig, key=f"portfolio_status_flow_{cycle_key}", height=340)
        elif status_column:
            status_df = build_frequency_table(df, status_column, top_n=10)
            if not status_df.empty:
                render_panel_title(f"Distribution de {status_column.replace('_', ' ')}")
                fig = px.bar(
                    status_df,
                    x=status_column,
                    y="nombre_lignes",
                    color_discrete_sequence=["#2b74ca"],
                )
                fig.update_layout(height=340, showlegend=False, xaxis_tickangle=-25)
                st_plot(fig, key=f"portfolio_status_distribution_{cycle_key}", height=340)

    with lower_right:
        if primary_group:
            summary_df = build_activity_table(
                df,
                primary_group,
                amount_columns=preset.get("amount_columns", []),
                alert_index=watchlist.index if not watchlist.empty else None,
                top_n=8,
            )
            if not summary_df.empty:
                render_panel_title(f"Top {primary_group.replace('_', ' ')} actives")
                st.dataframe(summary_df, width="stretch", hide_index=True)

    if primary_group and secondary_group and amount_column:
        pivot = pd.pivot_table(
            df,
            index=primary_group,
            columns=secondary_group,
            values=amount_column,
            aggfunc="sum",
            fill_value=0,
        )
        render_panel_title("Lecture croisée")
        st.dataframe(pivot, width="stretch")

    render_panel_title("Watchlist métier")
    if watchlist.empty:
        st.success("Aucun élément sensible n'a été détecté selon les règles actuelles.")
    else:
        st.dataframe(watchlist.head(200), width="stretch", hide_index=True)
