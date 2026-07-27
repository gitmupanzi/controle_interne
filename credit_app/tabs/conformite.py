from __future__ import annotations

import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

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
    for column in ["montant", "volume", "nombre", "nombre_anomalies", "ligne_reporting", "ligne_excel"]:
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")
    for column in [
        "date_evenement",
        "date_alerte",
        "date_declaration",
        "date_operation",
        "date_debut",
        "date_fin",
    ]:
        if column in working.columns:
            working[column] = pd.to_datetime(working[column], errors="coerce")
    return working


def _normalized_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(character for character in text if not unicodedata.combining(character)).casefold().strip()


def _subset(df: pd.DataFrame, *, analyse_prefix: str | None = None, type_ligne: str | None = None) -> pd.DataFrame:
    working = _copy_frame(df)
    if working.empty:
        return working
    if analyse_prefix:
        analyse_column = _first_existing_column(working, ["analyse", "analyse_source"])
        if analyse_column:
            working = working.loc[
                working[analyse_column]
                .astype("string")
                .str.startswith(analyse_prefix[:3], na=False)
            ]
    if type_ligne:
        if "type_element" in working.columns:
            expected_label = {
                "REPORTING": "Reporting agrege",
                "MOUVEMENT_OPERATION": "Mouvement",
                "REMBOURSEMENT_ANTICIPE": "Remboursement anticipe",
                "ALERTE": "Alerte",
                "DECLARATION": "Declaration",
                "PROFIL_RISQUE": "Profil de risque",
                "BLACKLIST": "Sanction",
                "REACTIVATION_COMPTE": "Reactivation de compte",
                "CONTROLE_QUALITE": "Controle qualite",
                "SYNTHESE_FLUX": "Synthese des flux",
                "FRACTIONNEMENT": "Fractionnement",
                "COUVERTURE": "Couverture",
                "GROS_MOUVEMENT_AGREGE": "Gros mouvement agrege",
            }.get(type_ligne.upper(), type_ligne)
            working = working.loc[
                working["type_element"].map(_normalized_text).eq(_normalized_text(expected_label))
            ]
        elif "type_ligne" in working.columns:
            working = working.loc[working["type_ligne"].astype("string").str.upper().eq(type_ligne.upper())]
    return working.reset_index(drop=True)


def _sum_numeric(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def _canonical_text_column(df: pd.DataFrame, canonical: str, *legacy: str) -> str | None:
    """Retourne le champ canonique, puis un ancien alias pour les exports historiques."""
    return _first_existing_column(df, [canonical, *legacy])


def _sum_reporting_number(reporting_df: pd.DataFrame, line: int) -> float:
    line_column = _first_existing_column(reporting_df, ["ligne_reporting", "ligne_excel"])
    if reporting_df.empty or line_column is None or "nombre" not in reporting_df.columns:
        return 0.0
    found = pd.to_numeric(
        reporting_df.loc[reporting_df[line_column].eq(line), "nombre"],
        errors="coerce",
    ).dropna()
    return float(found.sum()) if not found.empty else 0.0


def _first_reporting_number(reporting_df: pd.DataFrame, line: int) -> float:
    line_column = _first_existing_column(reporting_df, ["ligne_reporting", "ligne_excel"])
    if reporting_df.empty or line_column is None or "nombre" not in reporting_df.columns:
        return 0.0
    found = reporting_df.loc[reporting_df[line_column].eq(line), "nombre"].dropna()
    return float(found.iloc[0]) if not found.empty else 0.0


def render_conformite_alertes_tab(df: pd.DataFrame) -> None:
    working = _copy_frame(df)
    alertes_df = _subset(working, analyse_prefix="150_", type_ligne="ALERTE")
    reporting_df = _subset(working, analyse_prefix="149_", type_ligne="REPORTING")
    fractionnements_df = _subset(working, analyse_prefix="039_", type_ligne="FRACTIONNEMENT")
    gros_mouvements_df = _subset(working, analyse_prefix="057_", type_ligne="GROS_MOUVEMENT_AGREGE")
    review_column = _first_existing_column(alertes_df, ["statut_revue", "statut_revue_conformite"])
    alert_state_column = _first_existing_column(alertes_df, ["etat", "etat_alerte"])

    total_alertes = len(alertes_df) if not alertes_df.empty else int(_first_reporting_number(reporting_df, 144))
    traitees = (
        int(alertes_df[review_column].astype("string").str.contains("TRAIT", case=False, na=False).sum())
        if review_column
        else int(_first_reporting_number(reporting_df, 145))
    )
    fractionnees = len(fractionnements_df)
    if fractionnees == 0:
        fractionnees = (
            int(alertes_df["indicateurs"].astype("string").str.contains("Fractionnement", case=False, na=False).sum())
            if "indicateurs" in alertes_df.columns and not alertes_df.empty
            else int(alertes_df["operation_fractionnee"].fillna(False).astype(bool).sum())
            if "operation_fractionnee" in alertes_df.columns and not alertes_df.empty
            else int(_first_reporting_number(reporting_df, 150))
        )
    gros_mouvements = int(_sum_numeric(gros_mouvements_df, "nombre"))
    a_revoir = max(total_alertes - traitees, 0) + fractionnees + len(gros_mouvements_df)
    client_series = []
    for frame in [alertes_df, fractionnements_df]:
        client_column = _first_existing_column(frame, ["code_client", "client_id"])
        if client_column:
            client_series.append(frame[client_column])
    clients_concernes = (
        int(pd.concat(client_series, ignore_index=True).dropna().nunique())
        if client_series
        else 0
    )
    devise_series = [
        frame["devise"]
        for frame in [alertes_df, fractionnements_df, gros_mouvements_df]
        if "devise" in frame.columns
    ]
    devises_surveillees = (
        int(pd.concat(devise_series, ignore_index=True).dropna().nunique())
        if devise_series
        else 0
    )

    render_panel_title("Alertes conformité LBC-FT")
    render_kpi_cards(
        [
            ("Alertes", f"{total_alertes:,}".replace(",", " "), "Générées ou importées", "blue"),
            ("Traitées", f"{traitees:,}".replace(",", " "), "Selon statut conformité", "green"),
            ("À revoir", f"{a_revoir:,}".replace(",", " "), "Solde opérationnel", "orange"),
            ("Fractionnement", f"{fractionnees:,}".replace(",", " "), "Groupes client-jour-devise", "red"),
            ("Gros mouvements", f"{gros_mouvements:,}".replace(",", " "), "Mouvements au-dessus du seuil", "navy"),
            ("Clients", f"{clients_concernes:,}".replace(",", " "), "Alertes et fractionnements", "slate"),
            ("Devises", f"{devises_surveillees:,}".replace(",", " "), "Aucune consolidation CDF/USD", "green"),
        ]
    )
    render_summary_box(
        "Lecture conformité",
        [
            "Cet onglet suit la chaîne d'alerte : génération, traitement, reste à revoir et signaux de fractionnement.",
            "Le fichier 156 rassemble les alertes 150, les fractionnements 39 et les gros mouvements 57.",
            "Les montants gardent leur devise d'origine ; l'analyse ne mélange pas CDF et USD.",
        ],
    )

    left, right = st.columns(2)
    with left:
        if not alertes_df.empty and alert_state_column:
            status_df = (
                alertes_df[alert_state_column].fillna("Non renseigné").astype(str).value_counts().reset_index()
            )
            status_df.columns = ["etat", "nombre_alertes"]
            render_panel_title("Alertes par état")
            fig = px.bar(status_df, x="etat", y="nombre_alertes", color_discrete_sequence=["#2b74ca"])
            style_standard_vertical_bar(fig, height=340, tickangle=-25)
            st_plot(fig, key="conformite_alertes_etat", height=340)
        else:
            st.info("Aucun détail d'alerte n'est présent dans le fichier 156.")
    with right:
        alert_label_column = _canonical_text_column(alertes_df, "rubrique", "type_alerte")
        if not alertes_df.empty and alert_label_column:
            type_df = (
                alertes_df[alert_label_column]
                .fillna("Non renseigné")
                .astype(str)
                .value_counts()
                .head(12)
                .reset_index()
            )
            type_df.columns = ["rubrique_alerte", "nombre_alertes"]
            render_panel_title("Types d'alertes")
            fig = px.bar(
                type_df.sort_values("nombre_alertes"),
                x="nombre_alertes",
                y="rubrique_alerte",
                orientation="h",
            )
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
            preferred_columns=["etat", "etat_alerte", "rubrique", "statut_revue", "statut_revue_conformite", "devise"],
            max_rows=80,
            height=430,
        )

    render_panel_title("Fractionnements potentiels — requête 39")
    if fractionnements_df.empty:
        st.info("Aucun groupe de fractionnement potentiel n'est présent sur la période.")
    else:
        render_filtered_dataframe(
            fractionnements_df,
            key_prefix="conformite_fractionnements_detail",
            preferred_columns=["date_evenement", "date_operation", "devise", "type_operation", "statut_revue", "statut_revue_conformite"],
            max_rows=100,
            height=420,
        )

    render_panel_title("Gros mouvements — requête 57")
    if gros_mouvements_df.empty:
        st.info("Aucun agrégat de gros mouvements n'est présent sur la période.")
    else:
        render_filtered_dataframe(
            gros_mouvements_df,
            key_prefix="conformite_gros_mouvements_detail",
            preferred_columns=["date_evenement", "date_operation", "point_service", "devise", "severite"],
            max_rows=80,
            height=360,
        )


def render_conformite_cycle_tab(df: pd.DataFrame) -> None:
    working = _copy_frame(df)
    synthese_flux_df = _subset(working, analyse_prefix="038_", type_ligne="SYNTHESE_FLUX")
    fractionnements_df = _subset(working, analyse_prefix="039_", type_ligne="FRACTIONNEMENT")
    couverture_df = _subset(working, analyse_prefix="048_", type_ligne="COUVERTURE")
    gros_mouvements_df = _subset(working, analyse_prefix="057_", type_ligne="GROS_MOUVEMENT_AGREGE")
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
            ("38 Flux LBC-FT", f"{len(synthese_flux_df):,}".replace(",", " "), "Synthèses par devise", "blue"),
            ("39 Fractionnement", f"{len(fractionnements_df):,}".replace(",", " "), "Groupes à examiner", "red"),
            (
                "48 Non couverts",
                f"{int(couverture_df.get('statut_couverture', pd.Series(dtype='string')).map(_normalized_text).eq('non couvert').sum()):,}".replace(",", " "),
                "Trous de couverture",
                "orange",
            ),
            ("57 Gros mouvements", f"{int(_sum_numeric(gros_mouvements_df, 'nombre')):,}".replace(",", " "), "Mouvements au-dessus du seuil", "navy"),
            ("149 Reporting", f"{len(reporting_df):,}".replace(",", " "), "Lignes réglementaires", "slate"),
            ("150 Alertes", f"{len(alertes_df):,}".replace(",", " "), "Alertes détaillées", "green"),
        ]
    )
    render_summary_box(
        "Lecture du fichier 156",
        [
            "Cet onglet centralise le contenu du fichier 156 téléversé pour le cycle conformité.",
            "Le socle couvre les requêtes 38, 39, 48, 57 et 149 à 155 dans une seule table.",
            "Les onglets Surveillance, Portefeuille, Risques et Qualité détaillent ensuite les mêmes données par angle de contrôle.",
            "Si une analyse affiche 0 ligne, cela veut dire que le fichier 156 exporté ne contient pas encore ce bloc d'analyse.",
        ],
    )

    coverage_df = pd.DataFrame(
        [
            {"analyse": "38 Synthèse flux", "lignes": len(synthese_flux_df), "statut": "Présent" if len(synthese_flux_df) else "Absent"},
            {"analyse": "39 Fractionnement", "lignes": len(fractionnements_df), "statut": "Présent" if len(fractionnements_df) else "Absent"},
            {"analyse": "48 Trous couverture", "lignes": len(couverture_df), "statut": "Présent" if len(couverture_df) else "Absent"},
            {"analyse": "57 Gros mouvements", "lignes": len(gros_mouvements_df), "statut": "Présent" if len(gros_mouvements_df) else "Absent"},
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
            + ". Réexporte la requête 156 mise à jour pour couvrir ces analyses dans le même fichier."
        )

    left, right = st.columns((1, 1))
    with left:
        render_panel_title("Couverture des analyses du cycle conformité")
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

    render_panel_title("Trous et prérequis de couverture — requête 48")
    if couverture_df.empty:
        st.info("Le bloc 48_TROUS_COUVERTURE_LBC_FT n'est pas présent dans le fichier.")
    else:
        render_filtered_dataframe(
            couverture_df,
            key_prefix="conformite_cycle_couverture_48",
            preferred_columns=["statut_couverture", "severite", "rubrique"],
            max_rows=40,
            height=360,
        )

    render_panel_title("Matrice de couverture du socle 156")
    render_filtered_dataframe(
        coverage_df,
        key_prefix="conformite_cycle_matrix",
        preferred_columns=["statut"],
        height=280,
    )


def render_conformite_portefeuille_tab(df: pd.DataFrame) -> None:
    working = _copy_frame(df)
    synthese_flux_df = _subset(working, analyse_prefix="038_", type_ligne="SYNTHESE_FLUX")
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
            ("Dépôts observés", f"{int(_sum_reporting_number(synthese_flux_df, 38)):,}".replace(",", " "), "Analyse 38, toutes devises en nombre", "green"),
        ]
    )
    render_summary_box(
        "Lecture portefeuille",
        [
            "Le portefeuille conformité rapproche les flux 38, les lignes réglementaires 65, 66 et 68 et les profils de risque détaillés.",
            "Si les profils 152 ne sont pas dans le fichier exporté, l'onglet conserve les chiffres agrégés du reporting 149.",
        ],
    )

    left, right = st.columns(2)
    with left:
        render_panel_title("Rubriques reporting portefeuille")
        line_column = _first_existing_column(reporting_df, ["ligne_reporting", "ligne_excel"])
        portfolio_lines = (
            reporting_df.loc[reporting_df[line_column].isin([65, 66, 68])]
            if line_column
            else pd.DataFrame()
        )
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
                ["niveau_risque", "profil_risque", "statut_revue", "statut_revue_conformite", "statut_couverture", "rubrique"],
            )
            if risk_column is None:
                st.info("Les lignes 152 sont présentes, mais aucune colonne de classification du risque n'est disponible.")
            else:
                risk_df = profils_df[risk_column].fillna("Non renseigné").astype(str).value_counts().reset_index()
                risk_df.columns = [risk_column, "nombre_clients"]
                fig = px.bar(risk_df, x=risk_column, y="nombre_clients", color_discrete_sequence=["#d97b16"])
                style_standard_vertical_bar(fig, height=320, tickangle=-20)
                st_plot(fig, key="conformite_portefeuille_profils", height=320)

    render_panel_title("Flux dépôts, retraits et mobile banking — requête 38")
    if synthese_flux_df.empty:
        st.info("La synthèse 38 n'est pas présente dans le fichier 156.")
    else:
        render_filtered_dataframe(
            synthese_flux_df,
            key_prefix="conformite_portefeuille_flux_38",
            preferred_columns=["devise", "section", "rubrique"],
            max_rows=40,
            height=360,
        )

    render_panel_title("Détails clients/profils")
    if profils_df.empty:
        st.info("Aucun détail client de l'analyse 152 n'est disponible.")
    else:
        render_filtered_dataframe(
            profils_df,
            key_prefix="conformite_portefeuille_profils_detail",
            preferred_columns=["niveau_risque", "profil_risque", "statut_revue", "statut_revue_conformite"],
            max_rows=80,
            height=420,
        )


def render_conformite_risques_tab(df: pd.DataFrame) -> None:
    working = _copy_frame(df)
    fractionnements_df = _subset(working, analyse_prefix="039_", type_ligne="FRACTIONNEMENT")
    couverture_df = _subset(working, analyse_prefix="048_", type_ligne="COUVERTURE")
    gros_mouvements_df = _subset(working, analyse_prefix="057_", type_ligne="GROS_MOUVEMENT_AGREGE")
    alertes_df = _subset(working, analyse_prefix="150_", type_ligne="ALERTE")
    declarations_df = _subset(working, analyse_prefix="151_", type_ligne="DECLARATION")
    profils_df = _subset(working, analyse_prefix="152_", type_ligne="PROFIL_RISQUE")
    sanctions_df = _subset(working, analyse_prefix="153_", type_ligne="BLACKLIST")
    reactivations_df = _subset(working, analyse_prefix="154_", type_ligne="REACTIVATION_COMPTE")

    alert_label_column = _canonical_text_column(alertes_df, "rubrique", "type_alerte")
    operation_suspecte_count = 0
    if not alertes_df.empty:
        if alert_label_column:
            operation_suspecte_count += int(
                alertes_df[alert_label_column]
                .astype("string")
                .str.contains("SUSPECT|ATYPI", case=False, regex=True, na=False)
                .sum()
            )
        description_column = _first_existing_column(alertes_df, ["description", "description_alerte"])
        if description_column:
            operation_suspecte_count += int(
                alertes_df[description_column]
                .astype("string")
                .str.contains("SUSPECT|ATYPI", case=False, regex=True, na=False)
                .sum()
            )
    non_couverts = (
        int(couverture_df["statut_couverture"].map(_normalized_text).eq("non couvert").sum())
        if "statut_couverture" in couverture_df.columns
        else 0
    )

    render_panel_title("Risques conformité")
    render_kpi_cards(
        [
            ("Alertes détaillées", f"{len(alertes_df):,}".replace(",", " "), "Analyse 150", "orange"),
            ("Fractionnements", f"{len(fractionnements_df):,}".replace(",", " "), "Analyse 39", "red"),
            ("Gros mouvements", f"{int(_sum_numeric(gros_mouvements_df, 'nombre')):,}".replace(",", " "), "Analyse 57", "navy"),
            ("DOS / CENTIF", f"{len(declarations_df):,}".replace(",", " "), "Analyse 151", "navy"),
            ("Profils risque", f"{len(profils_df):,}".replace(",", " "), "Analyse 152", "slate"),
            ("Non couverts", f"{non_couverts:,}".replace(",", " "), "Analyse 48", "blue"),
        ]
    )
    render_summary_box(
        "Lecture risque",
        [
            "Cet onglet regroupe les signaux LBC-FT : fractionnements, gros mouvements, alertes, soupçons, profils à risque, sanctions et réactivations.",
            f"{operation_suspecte_count:,}".replace(",", " ") + " alerte(s) contiennent les mots-clés suspect ou atypique.",
            "Les sanctions issues du référentiel ne prouvent pas à elles seules un gel ou un refus : il faut une trace d'action opérationnelle.",
        ],
    )

    left, right = st.columns(2)
    with left:
        render_panel_title("Risques par source d'analyse")
        analysis_column = _first_existing_column(working, ["analyse", "analyse_source"])
        if analysis_column:
            source_df = working[analysis_column].fillna("Non renseigné").astype(str).value_counts().reset_index()
            source_df.columns = ["analyse", "nombre_lignes"]
            fig = px.bar(source_df, x="nombre_lignes", y="analyse", orientation="h", color_discrete_sequence=["#1553a1"])
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
        [
            frame
            for frame in [
                fractionnements_df,
                couverture_df,
                gros_mouvements_df,
                alertes_df,
                declarations_df,
                profils_df,
                sanctions_df,
                reactivations_df,
            ]
            if not frame.empty
        ],
        ignore_index=True,
    )
    if risk_detail.empty:
        st.info("Aucun détail de risque n'est présent dans ce fichier.")
    else:
        render_filtered_dataframe(
            risk_detail,
            key_prefix="conformite_risques_detail",
            preferred_columns=["analyse", "analyse_source", "type_element", "type_ligne", "niveau_risque", "severite", "devise"],
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
    controle_column = _canonical_text_column(controles_df, "rubrique", "controle")
    nombre_column = _first_existing_column(controles_df, ["nombre", "nombre_anomalies"])
    critiques = (
        int(controles_df["severite"].astype("string").str.upper().eq("CRITIQUE").sum())
        if "severite" in controles_df.columns
        else 0
    )
    total_anomalies_156 = _sum_numeric(controles_df, nombre_column) if nombre_column else 0.0

    render_panel_title("Qualité conformité issue du fichier 156")
    render_kpi_cards(
        [
            ("Contrôles 156", f"{len(controles_df):,}".replace(",", " "), "Analyse 155", "blue"),
            ("Anomalies 156", f"{total_anomalies_156:,.0f}".replace(",", " "), "Somme du champ nombre", "red"),
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
        if nombre_column and controle_column:
            action_df = controles_df.sort_values(nombre_column, ascending=False).head(10)
            fig = px.bar(
                action_df.sort_values(nombre_column),
                x=nombre_column,
                y=controle_column,
                orientation="h",
                color_discrete_sequence=["#9b2c2c"],
            )
            style_standard_horizontal_bar(fig, height=320)
            st_plot(fig, key="conformite_quality_controles", height=320)
        else:
            st.info("Les libellés ou nombres des contrôles qualité ne sont pas disponibles.")

    render_panel_title("Contrôles qualité LBC-FT")
    render_filtered_dataframe(
        controles_df,
        key_prefix="conformite_quality_155",
        preferred_columns=["severite", "rubrique"],
        max_rows=80,
        height=420,
    )
