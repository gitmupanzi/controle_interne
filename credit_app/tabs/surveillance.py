from __future__ import annotations

import pandas as pd
import streamlit as st

from credit_app.core import format_currency
from credit_app.cycles import get_cycle_analysis_preset, get_cycle_spec
from credit_app.domain import (
    build_activity_table,
    build_cycle_priority_actions,
    build_cycle_watchlist,
    build_operational_snapshot,
    build_summary_metrics,
    get_first_existing_column,
)
from credit_app.ui import render_panel_title, render_summary_box

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

    render_panel_title("Éléments à suivre en priorité")
    if not watchlist.empty:
        st.dataframe(watchlist.head(50), width="stretch", hide_index=True)
    else:
        st.success("Aucun élément prioritaire n'a été détecté avec les règles de surveillance actuelles.")

    render_panel_title("Aperçu des données filtrées")
    preview_columns = [column for column in df.columns if column not in {"mois_demande"}]
    st.dataframe(df[preview_columns].head(200), width="stretch", hide_index=True)
