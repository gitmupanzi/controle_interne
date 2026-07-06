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

PANEL_LABELS = {
    "agence": "Agences",
    "type_produit": "Produits",
    "type_client": "Types de client",
    "agent_credit": "Gestionnaires",
    "nom_groupe": "Groupes",
    "type_operation": "Types d'opération",
    "statut_compte": "Statuts de compte",
    "caissier": "Caissiers",
    "banque": "Banques",
    "compte_bancaire": "Comptes bancaires",
    "journal": "Journaux",
    "compte_comptable": "Comptes comptables",
    "fonction": "Fonctions",
    "statut_agent": "Statuts d'agent",
    "application_source": "Applications",
    "profil_acces": "Profils d'accès",
    "type_sauvegarde": "Types de sauvegarde",
    "support_sauvegarde": "Supports",
    "operateur": "Opérateurs",
    "tresorier": "Trésoriers",
}

DISPLAY_COLUMN_LABELS = {
    "agence": "Agence",
    "type_produit": "Produit",
    "type_client": "Type client",
    "agent_credit": "Gestionnaire",
    "nom_groupe": "Groupe",
    "type_operation": "Opération",
    "statut_compte": "Statut",
    "caissier": "Caissier",
    "banque": "Banque",
    "compte_bancaire": "Compte bancaire",
    "journal": "Journal",
    "compte_comptable": "Compte comptable",
    "fonction": "Fonction",
    "statut_agent": "Statut agent",
    "application_source": "Application",
    "profil_acces": "Profil d'accès",
    "type_sauvegarde": "Type sauvegarde",
    "support_sauvegarde": "Support",
    "operateur": "Opérateur",
    "tresorier": "Trésorier",
    "lignes": "Lignes",
    "montant_total": "Montant",
    "alertes": "Alertes",
    "lecture": "Lecture",
    "classe_inactivite": "Inactivité",
    "nombre_lignes": "Lignes",
    "part_lignes": "Part",
    "classe_comptes": "Classe",
    "nombre_clients": "Clients",
    "client_id": "Client",
    "nom_client": "Nom client",
    "nombre_comptes": "Nb comptes",
    "solde_total": "Solde total",
    "Provenance": "Source",
    "motif_alerte": "Motif",
    "telephone": "Téléphone",
    "zone_geographique": "Zone",
    "compte_id": "Compte",
    "champs_kyc_manquants": "Éléments KYC manquants",
    "produit_reference": "Référence produit",
    "seuil_minimum_produit": "Seuil minimum",
    "duree_credit_mois": "Durée (mois)",
    "taux_interet": "Taux d'intérêt",
}


def _humanize_column_name(column: object) -> str:
    text = str(column)
    if text in DISPLAY_COLUMN_LABELS:
        return DISPLAY_COLUMN_LABELS[text]
    text = text.replace("_", " ").strip()
    if not text:
        return str(column)
    return text[:1].upper() + text[1:]


def _group_title(column: str) -> str:
    return PANEL_LABELS.get(column, _humanize_column_name(column))


def _rename_columns_for_display(df: pd.DataFrame, extra_map: dict[str, str] | None = None) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    rename_map = {column: _humanize_column_name(column) for column in df.columns}
    if extra_map:
        rename_map.update(extra_map)
    return df.rename(columns=rename_map)


def _build_alert_comment(alert_count: object) -> str:
    numeric = pd.to_numeric(pd.Series([alert_count]), errors="coerce").iloc[0]
    if pd.isna(numeric) or float(numeric) <= 0:
        return "Aucune ligne de ce groupe n'est remontée dans la liste de suivi."
    if float(numeric) == 1:
        return "Ce groupe contient 1 ligne signalée dans la liste de suivi."
    return f"Ce groupe contient {int(float(numeric))} lignes signalées dans la liste de suivi."


def _prepare_activity_display_table(table: pd.DataFrame, group_column: str) -> pd.DataFrame:
    if table.empty:
        return table.copy()

    display_df = table.copy()
    if "alertes" in display_df.columns:
        display_df["lecture"] = display_df["alertes"].apply(_build_alert_comment)

    return _rename_columns_for_display(
        display_df,
        extra_map={group_column: DISPLAY_COLUMN_LABELS.get(group_column, _humanize_column_name(group_column))},
    )


def _prepare_multi_account_clients_display_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    display_df = df.copy()
    display_df["lecture"] = display_df["nombre_comptes"].apply(
        lambda value: (
            "Client à revoir en priorité pour cumul élevé de comptes."
            if pd.notna(value) and float(value) >= 5
            else "Client avec plusieurs comptes à confirmer."
        )
    )
    return _rename_columns_for_display(display_df)


def _prepare_provenance_display_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    display_df = df.copy().reset_index(drop=True)
    if len(display_df) > 1:
        max_lines = pd.to_numeric(display_df["nombre_lignes"], errors="coerce").max()
        display_df["lecture"] = pd.to_numeric(display_df["nombre_lignes"], errors="coerce").apply(
            lambda value: (
                "Extraction principale de la session."
                if pd.notna(value) and value == max_lines
                else "Extraction secondaire utile pour la comparaison."
            )
        )
    else:
        display_df["lecture"] = "Une seule extraction est disponible."
    return _rename_columns_for_display(display_df)


def _prepare_watchlist_display_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return _rename_columns_for_display(df)


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

    return motifs.value_counts().head(top_n).rename_axis("motif_alerte").reset_index(name="nombre_lignes")


def _render_epargne_surveillance_block(df: pd.DataFrame, watchlist: pd.DataFrame) -> None:
    dormancy_df = build_epargne_dormancy_table(df)
    multi_account_df = build_epargne_multi_account_table(df)
    multi_clients_df = build_epargne_multi_account_clients(df, top_n=15)
    provenance_df = build_provenance_summary_table(df)
    watchlist_reasons_df = _build_watchlist_reason_table(watchlist)

    top_left, top_right = st.columns((1, 1))

    with top_left:
        if not dormancy_df.empty:
            render_panel_title("Dormance")
            fig = px.bar(
                dormancy_df,
                x="classe_inactivite",
                y="nombre_lignes",
                color_discrete_sequence=["#2b74ca"],
            )
            style_standard_vertical_bar(fig, height=320, tickangle=-20)
            st_plot(fig, key="surveillance_epargne_dormancy", height=320)
        else:
            st.info("L'information sur la dormance n'est pas disponible pour les données actuelles.")

    with top_right:
        if not multi_account_df.empty:
            render_panel_title("Multi-comptes")
            fig = px.bar(
                multi_account_df,
                x="classe_comptes",
                y="nombre_clients",
                color_discrete_sequence=["#4b84d7"],
            )
            style_standard_vertical_bar(fig, height=320, tickangle=-20)
            st_plot(fig, key="surveillance_epargne_multi_accounts", height=320)
        else:
            st.info("La répartition des multi-comptes n'est pas disponible pour les données actuelles.")

    mid_left, mid_right = st.columns((1, 1))

    with mid_left:
        render_panel_title("Clients multi-comptes")
        if multi_clients_df.empty:
            st.info("Aucun client avec plusieurs comptes n'a été détecté.")
        else:
            st.dataframe(_prepare_multi_account_clients_display_table(multi_clients_df), width="stretch", hide_index=True)

    with mid_right:
        if not provenance_df.empty and len(provenance_df) > 1:
            render_panel_title("Comparaison des extractions")
            st.dataframe(_prepare_provenance_display_table(provenance_df), width="stretch", hide_index=True)
        else:
            st.info("Une seule extraction est disponible pour les données actuelles.")

    if not watchlist_reasons_df.empty:
        render_panel_title("Motifs de vigilance")
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
        top_reason = ""
        if not watchlist_reasons_df.empty:
            top_reason = str(watchlist_reasons_df.iloc[0]["motif_alerte"])
        render_summary_box(
            "Lecture rapide de la surveillance épargne",
            [
                f"{len(watchlist):,}".replace(",", " ") + " ligne(s) sont actuellement dans la liste de suivi.",
                (
                    f"Le motif le plus fréquent est : {top_reason}."
                    if top_reason
                    else "Les alertes proviennent de plusieurs motifs à examiner."
                ),
                "Les tableaux ci-dessus aident à repérer les clients multi-comptes, la dormance et les écarts entre extractions.",
            ],
        )


def render_surveillance_tab(df: pd.DataFrame, cycle_key: str = "credit") -> None:
    if df.empty:
        st.warning("Aucune ligne ne correspond aux filtres choisis.")
        return

    cycle_spec = get_cycle_spec(cycle_key)
    preset = get_cycle_analysis_preset(cycle_key)
    snapshot = build_operational_snapshot(df)
    metrics = build_summary_metrics(df)
    watchlist = build_cycle_watchlist(df, cycle_key)
    group_columns = [column for column in preset.get("group_columns", []) if column in df.columns]
    primary_group = group_columns[0] if group_columns else None
    secondary_group = group_columns[1] if len(group_columns) > 1 else None

    render_panel_title("Surveillance")
    render_summary_box(
        "À retenir",
        [
            f"Cet onglet regroupe les actions prioritaires et les classements opérationnels du {cycle_spec['label']}.",
            f"{len(watchlist):,}".replace(",", " ")
            + f" élément(s) demandent actuellement une attention particulière dans les {preset['record_label'].lower()}.",
        ],
    )

    action_col, snapshot_col = st.columns((1.2, 1))

    with action_col:
        render_panel_title("Actions prioritaires")
        render_summary_box("Focus de gestion", build_cycle_priority_actions(df, cycle_key))

    with snapshot_col:
        top_dimension = primary_group or get_first_existing_column(df, ["agence", "type_operation", "banque", "journal"])
        top_message = "Aucun regroupement principal n'est disponible."
        if top_dimension:
            top_value_series = df[top_dimension].dropna().astype("string").str.strip()
            if not top_value_series.empty:
                top_value = top_value_series.value_counts().index[0]
                top_message = f"L'élément le plus actif pour `{top_dimension}` est **{top_value}**."

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
        render_panel_title("Repères rapides")
        render_summary_box(
            "Priorités du moment",
            [
                top_message,
                "Montant observé : " + format_currency(montant_reference) + ".",
                f"{snapshot['high_risk_count']:,}".replace(",", " ") + " ligne(s) présentent un risque élevé.",
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
                st.dataframe(_prepare_activity_display_table(ranking_df, primary_group), width="stretch", hide_index=True)
            else:
                st.info("Aucun classement principal n'est disponible pour les données actuelles.")
        else:
            st.info("Aucun regroupement principal n'est disponible pour ce cycle.")

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
                st.dataframe(
                    _prepare_activity_display_table(ranking_df, secondary_group),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("Aucun classement secondaire n'est disponible pour les données actuelles.")
        else:
            st.info("Aucun second regroupement n'est disponible pour ce cycle.")

    if cycle_key == "epargne":
        _render_epargne_surveillance_block(df, watchlist)

    render_panel_title("Cas prioritaires")
    if not watchlist.empty:
        st.dataframe(_prepare_watchlist_display_table(watchlist.head(50)), width="stretch", hide_index=True)
    else:
        st.success("Aucun élément prioritaire n'a été détecté avec les règles de surveillance actuelles.")

    render_panel_title("Aperçu")
    preview_columns = [column for column in df.columns if column not in {"mois_demande"}]
    st.dataframe(_rename_columns_for_display(df[preview_columns].head(200)), width="stretch", hide_index=True)
