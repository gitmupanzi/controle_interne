from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.core import format_currency
from credit_app.tabs.table_filters import render_filtered_dataframe
from credit_app.ui import (
    render_kpi_cards,
    render_panel_title,
    render_summary_box,
    st_plot,
    style_standard_horizontal_bar,
    style_standard_vertical_bar,
)


def _copy_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame):
        return pd.DataFrame()
    working = df.copy()
    for column in ["montant", "volume", "nombre", "nombre_anomalies", "ligne_excel"]:
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")
    for column in ["date_alerte", "date_declaration", "date_operation", "date_debut", "date_fin"]:
        if column in working.columns:
            working[column] = pd.to_datetime(working[column], errors="coerce")
    return working


def _subset(df: pd.DataFrame, *, analyse_prefix: str | None = None, type_ligne: str | None = None) -> pd.DataFrame:
    working = _copy_frame(df)
    if working.empty:
        return working
    if analyse_prefix and "analyse_source" in working.columns:
        working = working.loc[working["analyse_source"].astype("string").str.startswith(analyse_prefix, na=False)]
    if type_ligne and "type_ligne" in working.columns:
        working = working.loc[working["type_ligne"].astype("string").str.upper().eq(type_ligne.upper())]
    return working.reset_index(drop=True)


def _nonnull_count(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns:
        return 0
    return int(df[column].dropna().nunique())


def _sum_numeric(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def _first_reporting_number(reporting_df: pd.DataFrame, line: int) -> float:
    if reporting_df.empty or "ligne_excel" not in reporting_df.columns or "nombre" not in reporting_df.columns:
        return 0.0
    found = reporting_df.loc[reporting_df["ligne_excel"].eq(line), "nombre"].dropna()
    return float(found.iloc[0]) if not found.empty else 0.0


def render_conformite_alertes_tab(df: pd.DataFrame) -> None:
    working = _copy_frame(df)
    alertes_df = _subset(working, analyse_prefix="150_", type_ligne="ALERTE")
    reporting_df = _subset(working, analyse_prefix="149_", type_ligne="REPORTING")

    total_alertes = len(alertes_df) if not alertes_df.empty else int(_first_reporting_number(reporting_df, 144))
    traitees = (
        int(alertes_df["statut_revue_conformite"].astype("string").str.contains("TRAIT", case=False, na=False).sum())
        if "statut_revue_conformite" in alertes_df.columns
        else int(_first_reporting_number(reporting_df, 145))
    )
    fractionnees = (
        int(alertes_df["operation_fractionnee"].fillna(False).astype(bool).sum())
        if "operation_fractionnee" in alertes_df.columns and not alertes_df.empty
        else int(_first_reporting_number(reporting_df, 150))
    )
    a_revoir = max(total_alertes - traitees, 0)

    render_panel_title("Alertes conformité LBC-FT")
    render_kpi_cards(
        [
            ("Alertes", f"{total_alertes:,}".replace(",", " "), "Générées ou importées", "blue"),
            ("Traitées", f"{traitees:,}".replace(",", " "), "Selon statut conformité", "green"),
            ("À revoir", f"{a_revoir:,}".replace(",", " "), "Solde opérationnel", "orange"),
            ("Fractionnement", f"{fractionnees:,}".replace(",", " "), "Signal de contournement", "red"),
            ("Clients", f"{_nonnull_count(alertes_df, 'client_id'):,}".replace(",", " "), "Clients concernés", "slate"),
            ("Montant alerté", format_currency(_sum_numeric(alertes_df, "montant")), "Sans conversion devise", "navy"),
        ]
    )
    render_summary_box(
        "Lecture conformité",
        [
            "Cet onglet suit la chaîne d'alerte : génération, traitement, reste à revoir et signaux de fractionnement.",
            "Quand le fichier 156 contient les détails 150, les tableaux descendent au niveau alerte/opération.",
            "Les montants gardent leur devise d'origine ; l'analyse ne mélange pas CDF et USD.",
        ],
    )

    left, right = st.columns(2)
    with left:
        if not alertes_df.empty and "etat_alerte" in alertes_df.columns:
            status_df = (
                alertes_df["etat_alerte"].fillna("Non renseigné").astype(str).value_counts().reset_index()
            )
            status_df.columns = ["etat_alerte", "nombre_alertes"]
            render_panel_title("Alertes par état")
            fig = px.bar(status_df, x="etat_alerte", y="nombre_alertes", color_discrete_sequence=["#2b74ca"])
            style_standard_vertical_bar(fig, height=340, tickangle=-25)
            st_plot(fig, key="conformite_alertes_etat", height=340)
        else:
            st.info("Aucun détail d'alerte n'est présent dans le fichier 156.")
    with right:
        if not alertes_df.empty and "type_alerte" in alertes_df.columns:
            type_df = (
                alertes_df["type_alerte"].fillna("Non renseigné").astype(str).value_counts().head(12).reset_index()
            )
            type_df.columns = ["type_alerte", "nombre_alertes"]
            render_panel_title("Types d'alertes")
            fig = px.bar(type_df.sort_values("nombre_alertes"), x="nombre_alertes", y="type_alerte", orientation="h")
            style_standard_horizontal_bar(fig, height=340)
            st_plot(fig, key="conformite_alertes_type", height=340)
        else:
            st.info("Aucun type d'alerte exploitable n'est disponible.")

    render_panel_title("Détail des alertes à traiter")
    if alertes_df.empty:
        st.info("Le fichier contient seulement le reporting agrégé ; exporte la requête 156 mise à jour pour obtenir les détails.")
    else:
        render_filtered_dataframe(
            alertes_df,
            key_prefix="conformite_alertes_detail",
            preferred_columns=["etat_alerte", "type_alerte", "statut_revue_conformite", "devise"],
            max_rows=80,
            height=430,
        )


def render_conformite_cycle_tab(df: pd.DataFrame) -> None:
    working = _copy_frame(df)
    reporting_df = _subset(working, analyse_prefix="149_", type_ligne="REPORTING")
    alertes_df = _subset(working, analyse_prefix="150_", type_ligne="ALERTE")
    declarations_df = _subset(working, analyse_prefix="151_", type_ligne="DECLARATION")
    profils_df = _subset(working, analyse_prefix="152_", type_ligne="PROFIL_RISQUE")
    sanctions_df = _subset(working, analyse_prefix="153_", type_ligne="BLACKLIST")
    reactivations_df = _subset(working, analyse_prefix="154_", type_ligne="REACTIVATION_COMPTE")
    controles_df = _subset(working, analyse_prefix="155_", type_ligne="CONTROLE_QUALITE")

    render_panel_title("Tableau de bord conformité")
    render_kpi_cards(
        [
            ("149 Reporting", f"{len(reporting_df):,}".replace(",", " "), "Lignes réglementaires", "blue"),
            ("150 Alertes", f"{len(alertes_df):,}".replace(",", " "), "Alertes détaillées", "orange"),
            ("151 Déclarations", f"{len(declarations_df):,}".replace(",", " "), "DOS / CENTIF", "navy"),
            ("152 Profils", f"{len(profils_df):,}".replace(",", " "), "Clients à risque", "slate"),
            ("153 Sanctions", f"{len(sanctions_df):,}".replace(",", " "), "Référentiel sanctions", "red"),
            ("155 Qualité", f"{len(controles_df):,}".replace(",", " "), "Contrôles qualité", "green"),
        ]
    )
    render_summary_box(
        "Lecture du fichier 156",
        [
            "Cet onglet centralise le contenu du fichier 156 téléversé pour le cycle conformité.",
            "Les onglets Alertes, Portefeuille, Risques et Qualité détaillent ensuite les mêmes données par angle de contrôle.",
            "Si une analyse affiche 0 ligne, cela veut dire que le fichier 156 exporté ne contient pas encore ce bloc d'analyse.",
        ],
    )

    coverage_df = pd.DataFrame(
        [
            {"analyse": "149 Reporting", "lignes": len(reporting_df), "statut": "Présent" if len(reporting_df) else "Absent"},
            {"analyse": "150 Alertes", "lignes": len(alertes_df), "statut": "Présent" if len(alertes_df) else "Absent"},
            {"analyse": "151 Déclarations", "lignes": len(declarations_df), "statut": "Présent" if len(declarations_df) else "Absent"},
            {"analyse": "152 Profils risque", "lignes": len(profils_df), "statut": "Présent" if len(profils_df) else "Absent"},
            {"analyse": "153 Sanctions", "lignes": len(sanctions_df), "statut": "Présent" if len(sanctions_df) else "Absent"},
            {"analyse": "154 Comptes réactivés", "lignes": len(reactivations_df), "statut": "Présent" if len(reactivations_df) else "Absent"},
            {"analyse": "155 Qualité", "lignes": len(controles_df), "statut": "Présent" if len(controles_df) else "Absent"},
        ]
    )
    missing_blocks = coverage_df.loc[coverage_df["lignes"].eq(0), "analyse"].tolist()
    if missing_blocks:
        st.warning(
            "Blocs absents du fichier 156 téléversé : "
            + ", ".join(missing_blocks)
            + ". Réexporte la requête 156 mise à jour si tu veux couvrir ces analyses ligne par ligne."
        )

    left, right = st.columns((1, 1))
    with left:
        render_panel_title("Couverture des analyses 149 à 155")
        fig = px.bar(
            coverage_df.sort_values("lignes"),
            x="lignes",
            y="analyse",
            orientation="h",
            color_discrete_sequence=["#1553a1"],
        )
        style_standard_horizontal_bar(fig, height=360)
        st_plot(fig, key="conformite_cycle_couverture_analyses", height=360)

    with right:
        render_panel_title("Statut de couverture reporting")
        if reporting_df.empty or "statut_couverture" not in reporting_df.columns:
            st.info("Aucune ligne de reporting 149 n'est disponible.")
        else:
            status_df = reporting_df["statut_couverture"].fillna("Non renseigné").astype(str).value_counts().reset_index()
            status_df.columns = ["statut_couverture", "nombre_lignes"]
            fig = px.bar(status_df, x="statut_couverture", y="nombre_lignes", color_discrete_sequence=["#d97b16"])
            style_standard_vertical_bar(fig, height=360, tickangle=-20)
            st_plot(fig, key="conformite_cycle_statut_couverture", height=360)

    render_panel_title("Rubriques du reporting LBC-FT")
    if reporting_df.empty:
        st.info("Aucune rubrique 149_REPORTING_LBC_FT n'est présente dans le fichier.")
    else:
        render_filtered_dataframe(
            reporting_df,
            key_prefix="conformite_cycle_reporting",
            preferred_columns=["section", "statut_couverture", "devise"],
            max_rows=80,
            height=420,
        )

    render_panel_title("Matrice de couverture 149 à 155")
    render_filtered_dataframe(
        coverage_df,
        key_prefix="conformite_cycle_matrix",
        preferred_columns=["statut"],
        height=280,
    )


def render_conformite_portefeuille_tab(df: pd.DataFrame) -> None:
    working = _copy_frame(df)
    reporting_df = _subset(working, analyse_prefix="149_", type_ligne="REPORTING")
    profils_df = _subset(working, analyse_prefix="152_", type_ligne="PROFIL_RISQUE")
    declarations_df = _subset(working, analyse_prefix="151_", type_ligne="DECLARATION")

    render_panel_title("Portefeuille conformité")
    render_kpi_cards(
        [
            ("Clients nouveaux", f"{_first_reporting_number(reporting_df, 65):,.0f}".replace(",", " "), "Ligne Excel 65", "blue"),
            ("Haut risque", f"{_first_reporting_number(reporting_df, 66):,.0f}".replace(",", " "), "Ligne Excel 66", "red"),
            ("Surveillance renforcée", f"{_first_reporting_number(reporting_df, 68):,.0f}".replace(",", " "), "Ligne Excel 68", "orange"),
            ("Profils détaillés", f"{len(profils_df):,}".replace(",", " "), "Analyse 152", "slate"),
            ("Déclarations", f"{len(declarations_df):,}".replace(",", " "), "Analyse 151", "navy"),
            ("Rubriques reporting", f"{len(reporting_df):,}".replace(",", " "), "Analyse 149", "green"),
        ]
    )
    render_summary_box(
        "Lecture portefeuille",
        [
            "Le portefeuille conformité rapproche les lignes réglementaires 65, 66 et 68 avec les profils de risque détaillés quand ils sont présents.",
            "Si les profils 152 ne sont pas dans le fichier exporté, l'onglet conserve les chiffres agrégés du reporting 149.",
        ],
    )

    left, right = st.columns(2)
    with left:
        render_panel_title("Rubriques reporting portefeuille")
        portfolio_lines = reporting_df.loc[reporting_df["ligne_excel"].isin([65, 66, 68])] if "ligne_excel" in reporting_df.columns else pd.DataFrame()
        if portfolio_lines.empty:
            st.info("Aucune rubrique portefeuille 65/66/68 n'est disponible.")
        else:
            render_filtered_dataframe(
                portfolio_lines,
                key_prefix="conformite_portefeuille_reporting",
                preferred_columns=["statut_couverture", "section"],
            )
    with right:
        render_panel_title("Profils de risque clients")
        if profils_df.empty:
            st.info("Les détails de profils 152 ne sont pas présents dans ce fichier.")
        else:
            risk_column = _first_existing_column(
                profils_df,
                ["niveau_risque", "profil_risque", "statut_revue_conformite", "statut_couverture", "rubrique"],
            )
            if risk_column is None:
                st.info("Les lignes 152 sont présentes, mais aucune colonne de classification du risque n'est disponible.")
            else:
                risk_df = profils_df[risk_column].fillna("Non renseigné").astype(str).value_counts().reset_index()
                risk_df.columns = [risk_column, "nombre_clients"]
                fig = px.bar(risk_df, x=risk_column, y="nombre_clients", color_discrete_sequence=["#d97b16"])
                style_standard_vertical_bar(fig, height=320, tickangle=-20)
                st_plot(fig, key="conformite_portefeuille_profils", height=320)

    render_panel_title("Détails clients/profils")
    if profils_df.empty:
        st.info("Aucun détail client de l'analyse 152 n'est disponible.")
    else:
        render_filtered_dataframe(
            profils_df,
            key_prefix="conformite_portefeuille_profils_detail",
            preferred_columns=["niveau_risque", "profil_risque", "statut_revue_conformite"],
            max_rows=80,
            height=420,
        )


def render_conformite_risques_tab(df: pd.DataFrame) -> None:
    working = _copy_frame(df)
    alertes_df = _subset(working, analyse_prefix="150_", type_ligne="ALERTE")
    declarations_df = _subset(working, analyse_prefix="151_", type_ligne="DECLARATION")
    profils_df = _subset(working, analyse_prefix="152_", type_ligne="PROFIL_RISQUE")
    sanctions_df = _subset(working, analyse_prefix="153_", type_ligne="BLACKLIST")
    reactivations_df = _subset(working, analyse_prefix="154_", type_ligne="REACTIVATION_COMPTE")

    operation_suspecte_count = (
        int(
            alertes_df["type_alerte"].astype("string").str.contains("SUSPECT|ATYPI", case=False, regex=True, na=False).sum()
            + alertes_df["description_alerte"].astype("string").str.contains("SUSPECT|ATYPI", case=False, regex=True, na=False).sum()
        )
        if not alertes_df.empty and {"type_alerte", "description_alerte"}.issubset(alertes_df.columns)
        else 0
    )

    render_panel_title("Risques conformité")
    render_kpi_cards(
        [
            ("Alertes détaillées", f"{len(alertes_df):,}".replace(",", " "), "Analyse 150", "orange"),
            ("Suspect / atypique", f"{operation_suspecte_count:,}".replace(",", " "), "Mots-clés alerte", "red"),
            ("DOS / CENTIF", f"{len(declarations_df):,}".replace(",", " "), "Analyse 151", "navy"),
            ("Profils risque", f"{len(profils_df):,}".replace(",", " "), "Analyse 152", "slate"),
            ("Référentiel sanctions", f"{len(sanctions_df):,}".replace(",", " "), "Analyse 153", "red"),
            ("Comptes réactivés", f"{len(reactivations_df):,}".replace(",", " "), "Analyse 154", "blue"),
        ]
    )
    render_summary_box(
        "Lecture risque",
        [
            "Cet onglet regroupe les signaux LBC-FT : alertes, soupçons, profils à risque, sanctions et réactivation de comptes dormants.",
            "Les sanctions issues du référentiel ne prouvent pas à elles seules un gel ou un refus : il faut une trace d'action opérationnelle.",
        ],
    )

    left, right = st.columns(2)
    with left:
        render_panel_title("Risques par source d'analyse")
        if "analyse_source" in working.columns:
            source_df = working["analyse_source"].fillna("Non renseigné").astype(str).value_counts().reset_index()
            source_df.columns = ["analyse_source", "nombre_lignes"]
            fig = px.bar(source_df, x="nombre_lignes", y="analyse_source", orientation="h", color_discrete_sequence=["#1553a1"])
            style_standard_horizontal_bar(fig, height=360)
            st_plot(fig, key="conformite_risques_sources", height=360)
    with right:
        render_panel_title("Statuts de couverture")
        if "statut_couverture" in working.columns:
            coverage_df = working["statut_couverture"].fillna("Non renseigné").astype(str).value_counts().reset_index()
            coverage_df.columns = ["statut_couverture", "nombre_lignes"]
            fig = px.bar(coverage_df, x="statut_couverture", y="nombre_lignes", color_discrete_sequence=["#d97b16"])
            style_standard_vertical_bar(fig, height=360, tickangle=-25)
            st_plot(fig, key="conformite_risques_couverture", height=360)

    render_panel_title("Détail des éléments de risque")
    risk_detail = pd.concat(
        [frame for frame in [alertes_df, declarations_df, profils_df, sanctions_df, reactivations_df] if not frame.empty],
        ignore_index=True,
    )
    if risk_detail.empty:
        st.info("Aucun détail de risque n'est présent dans ce fichier.")
    else:
        render_filtered_dataframe(
            risk_detail,
            key_prefix="conformite_risques_detail",
            preferred_columns=["analyse_source", "type_ligne", "niveau_risque", "severite", "devise"],
            max_rows=100,
            height=460,
        )


def render_conformite_quality_extension(
    standardized_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    missing_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
) -> None:
    working = _copy_frame(standardized_df)
    controles_df = _subset(working, analyse_prefix="155_", type_ligne="CONTROLE_QUALITE")
    critiques = (
        int(controles_df["severite"].astype("string").str.upper().eq("CRITIQUE").sum())
        if "severite" in controles_df.columns
        else 0
    )
    total_anomalies_156 = _sum_numeric(controles_df, "nombre_anomalies")

    render_panel_title("Qualité conformité issue du fichier 156")
    render_kpi_cards(
        [
            ("Contrôles 156", f"{len(controles_df):,}".replace(",", " "), "Analyse 155", "blue"),
            ("Anomalies 156", f"{total_anomalies_156:,.0f}".replace(",", " "), "Somme nombre_anomalies", "red"),
            ("Critiques", f"{critiques:,}".replace(",", " "), "Sévérité critique", "orange"),
            ("Colonnes manquantes", f"{len(missing_df):,}".replace(",", " "), "Profil standardisation", "slate"),
            ("Mapping colonnes", f"{len(mapping_df):,}".replace(",", " "), "Colonnes analysées", "green"),
            ("Qualité générique", f"{_sum_numeric(quality_df, 'nombre_lignes'):,.0f}".replace(",", " "), "Contrôles app", "navy"),
        ]
    )
    render_summary_box(
        "Lecture qualité",
        [
            "Les contrôles 155 du fichier 156 sont affichés à côté des contrôles qualité génériques de l'application.",
            "Priorité : traiter d'abord les contrôles CRITIQUE, puis les anomalies ÉLEVÉE.",
        ],
    )

    if controles_df.empty:
        st.info("Le fichier 156 ne contient pas encore les lignes 155_QUALITE_DONNEES_LBC_FT.")
        return

    left, right = st.columns(2)
    with left:
        severity_df = controles_df["severite"].fillna("Non renseigné").astype(str).value_counts().reset_index()
        severity_df.columns = ["severite", "nombre_controles"]
        fig = px.bar(severity_df, x="severite", y="nombre_controles", color_discrete_sequence=["#d97b16"])
        style_standard_vertical_bar(fig, height=320, tickangle=-20)
        st_plot(fig, key="conformite_quality_severite", height=320)
    with right:
        action_df = controles_df.sort_values("nombre_anomalies", ascending=False).head(10)
        fig = px.bar(
            action_df.sort_values("nombre_anomalies"),
            x="nombre_anomalies",
            y="controle",
            orientation="h",
            color_discrete_sequence=["#9b2c2c"],
        )
        style_standard_horizontal_bar(fig, height=320)
        st_plot(fig, key="conformite_quality_controles", height=320)

    render_panel_title("Contrôles qualité LBC-FT")
    render_filtered_dataframe(
        controles_df,
        key_prefix="conformite_quality_155",
        preferred_columns=["severite", "controle"],
        max_rows=80,
        height=420,
    )
