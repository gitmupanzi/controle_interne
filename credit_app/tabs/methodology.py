from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from credit_app.control_references import (
    build_control_levels_table,
    build_control_principles_table,
    build_reporting_chain_table,
    build_risk_cartography_table,
)
from credit_app.cycles import (
    build_cycle_control_table,
    build_cycle_coverage_summary,
    build_cycle_expected_fields_table,
    get_cycle_spec,
)
from credit_app.ui import render_panel_title, render_summary_box


def _build_standardization_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Bloc": "Colonnes",
                "Principe": "Les colonnes proches du référentiel métier sont reconnues puis renommées.",
                "Utilité": "Permet de charger des bases Excel ou CSV non uniformes.",
            },
            {
                "Bloc": "Référentiel",
                "Principe": "Le fichier `data/Rename_columns.xlsx` complète les alias internes.",
                "Utilité": "Adapte la lecture aux habitudes locales de nommage.",
            },
            {
                "Bloc": "Dates",
                "Principe": "Les dates utiles sont converties quand le format est exploitable.",
                "Utilité": "Active les filtres de période et les séries temporelles.",
            },
            {
                "Bloc": "Montants",
                "Principe": "Les montants, durées, retards, âges et scores sont nettoyés puis convertis.",
                "Utilité": "Fiabilise les calculs et réduit les erreurs de type.",
            },
            {
                "Bloc": "Valeurs métier",
                "Principe": "Les statuts, sexes et autres valeurs récurrentes sont harmonisés.",
                "Utilité": "Évite les doublons de libellés dans les tableaux et graphiques.",
            },
        ]
    )


def _build_analysis_scope_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Question": "Que fait automatiquement l'application ?",
                "Réponse": "Elle standardise les données, applique des règles simples et restitue des analyses par cycle.",
            },
            {
                "Question": "Que faut-il encore valider manuellement ?",
                "Réponse": "Les pièces, le contexte opérationnel, la conformité réelle et la pertinence des décisions.",
            },
            {
                "Question": "À quoi sert la couverture du cycle ?",
                "Réponse": "Elle montre la part des champs clés effectivement présents dans la base chargée.",
            },
            {
                "Question": "Pourquoi certaines analyses changent selon le cycle ?",
                "Réponse": "Chaque cycle a ses champs attendus, ses regroupements et ses règles d'alerte propres.",
            },
        ]
    )


def _build_quality_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Contrôle": "Identifiant manquant", "Lecture": "Empêche de tracer correctement un client, un compte ou un dossier."},
            {"Contrôle": "Doublon potentiel", "Lecture": "Peut gonfler les volumes ou créer des interprétations erronées."},
            {"Contrôle": "Montant incohérent", "Lecture": "Peut signaler une erreur de saisie, de signe ou de conversion."},
            {"Contrôle": "Statut absent", "Lecture": "Limite la lecture du processus et des ruptures de contrôle."},
            {"Contrôle": "Date absente ou invalide", "Lecture": "Fausse les périodes, tendances et délais."},
            {"Contrôle": "Valeur métier non harmonisée", "Lecture": "Multiplie artificiellement les catégories dans les analyses."},
        ]
    )


def _build_limit_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Limite": "Base incomplète",
                "Conséquence": "Une synthèse élégante ne remplace pas une base suffisamment renseignée.",
            },
            {
                "Limite": "Règles heuristiques",
                "Conséquence": "Certaines alertes sont des signaux de contrôle, pas une preuve définitive d'anomalie.",
            },
            {
                "Limite": "Lecture hors procédure",
                "Conséquence": "Un indicateur doit rester interprété à la lumière des procédures et des seuils de l'IMF.",
            },
            {
                "Limite": "Absence de justificatifs",
                "Conséquence": "Le tableau de bord oriente la revue, mais ne remplace pas la preuve documentaire.",
            },
        ]
    )


def _build_cycle_reading_table(cycle_label: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Axe": "Volumétrie",
                "Lecture": f"Mesure les volumes actifs du {cycle_label.lower()} et aide à repérer les zones concentrées.",
            },
            {
                "Axe": "Alertes",
                "Lecture": "Signale les lignes ou regroupements qui demandent une revue plus rapide.",
            },
            {
                "Axe": "Qualité",
                "Lecture": "Montre si la base est suffisamment propre pour soutenir une conclusion de contrôle.",
            },
            {
                "Axe": "Traçabilité",
                "Lecture": "Vérifie si les identifiants, dates, statuts et références clés sont bien présents.",
            },
        ]
    )


def _build_formula_cards(cycle_key: str) -> list[dict[str, str]]:
    generic_cards = [
        {
            "label": "Couverture",
            "formula": "Champs détectés / champs attendus",
            "why": "Mesure le niveau de préparation de la base pour le cycle choisi.",
        },
        {
            "label": "Part",
            "formula": "Montant ou volume d'un groupe / total du périmètre",
            "why": "Aide à lire rapidement les concentrations.",
        },
        {
            "label": "Variation",
            "formula": "Valeur actuelle - valeur précédente",
            "why": "Permet de suivre les évolutions entre deux extractions ou deux périodes.",
        },
        {
            "label": "Alerte",
            "formula": "Règle métier déclenchée sur une ligne ou un groupe",
            "why": "Oriente les revues prioritaires sans remplacer le jugement du contrôleur.",
        },
    ]

    if cycle_key in {"credit", "likelemba"}:
        generic_cards.extend(
            [
                {
                    "label": "Capacité",
                    "formula": "Revenu mensuel - charges mensuelles",
                    "why": "Donne une marge théorique simple avant décision ou revue.",
                },
                {
                    "label": "Endettement",
                    "formula": "Charges mensuelles / revenu mensuel",
                    "why": "Aide à lire la pression financière supportée par le client.",
                },
            ]
        )
    elif cycle_key == "epargne":
        generic_cards.extend(
            [
                {
                    "label": "Dormance",
                    "formula": "Date de référence - dernière activité",
                    "why": "Aide à classer les comptes selon leur niveau d'inactivité.",
                },
                {
                    "label": "Poids produit",
                    "formula": "Solde produit / solde total",
                    "why": "Met en évidence les produits dominants du portefeuille d'épargne.",
                },
            ]
        )
    return generic_cards


def _inject_methodology_styles() -> None:
    st.markdown(
        """
<style>
    .method-hero {
        position: relative;
        overflow: hidden;
        padding: 1.25rem 1.4rem;
        border-radius: 24px;
        color: #ffffff;
        background:
            linear-gradient(120deg, rgba(255,255,255,0.10), rgba(255,255,255,0.02)),
            linear-gradient(90deg, #12315f 0%, #1553a1 54%, #3576c8 100%);
        box-shadow: 0 18px 38px rgba(11, 44, 99, 0.16);
        border: 1px solid rgba(255,255,255,0.18);
        margin-bottom: 1rem;
    }

    .method-hero::before,
    .method-hero::after {
        content: "";
        position: absolute;
        border-radius: 50%;
        background: rgba(255,255,255,0.10);
        filter: blur(8px);
    }

    .method-hero::before {
        width: 220px;
        height: 220px;
        top: -120px;
        right: -28px;
    }

    .method-hero::after {
        width: 150px;
        height: 150px;
        left: -22px;
        bottom: -76px;
    }

    .method-hero-badge {
        display: inline-block;
        padding: 0.28rem 0.7rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.14);
        border: 1px solid rgba(255,255,255,0.18);
        font-size: 0.78rem;
        letter-spacing: 0.14em;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
    }

    .method-hero h2 {
        margin: 0;
        font-size: clamp(1.35rem, 2.2vw, 1.95rem);
        line-height: 1.15;
        letter-spacing: 0.03em;
        font-weight: 800;
    }

    .method-hero p {
        margin: 0.5rem 0 0;
        max-width: 62rem;
        font-size: 0.96rem;
        line-height: 1.45;
        color: rgba(255,255,255,0.94);
    }

    .method-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.8rem;
    }

    .method-chip {
        background: rgba(255,255,255,0.16);
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 999px;
        padding: 0.36rem 0.74rem;
        font-size: 0.77rem;
        font-weight: 700;
    }

    .method-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.75rem;
        margin: 0.35rem 0 1rem;
    }

    .method-card {
        background: rgba(255,255,255,0.95);
        border: 1px solid rgba(18, 53, 106, 0.10);
        border-radius: 18px;
        padding: 0.9rem 0.95rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
    }

    .method-card-label {
        color: #5a708c;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    .method-card-value {
        margin-top: 0.32rem;
        color: #1553a1;
        font-size: 1.32rem;
        line-height: 1.12;
        font-weight: 800;
    }

    .method-card-sub {
        margin-top: 0.24rem;
        color: #35506f;
        font-size: 0.83rem;
        line-height: 1.35;
    }

    .method-formula-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.75rem;
        margin-bottom: 1rem;
    }

    .method-formula-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(246,250,255,0.96) 100%);
        border-radius: 18px;
        border: 1px solid rgba(18, 53, 106, 0.10);
        padding: 0.95rem 1rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
    }

    .method-formula-label {
        color: #0b2c63;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    .method-formula-code {
        margin-top: 0.5rem;
        color: #1553a1;
        font-family: Consolas, "Courier New", monospace;
        font-size: 0.89rem;
        line-height: 1.45;
        white-space: pre-wrap;
    }

    .method-formula-why {
        margin-top: 0.5rem;
        color: #3d5878;
        font-size: 0.83rem;
        line-height: 1.38;
    }

    .method-path {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(18, 53, 106, 0.10);
        border-radius: 20px;
        padding: 0.9rem 1rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
        margin: 0.35rem 0 1rem;
    }

    .method-path-title {
        color: #0b2c63;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
        margin-bottom: 0.6rem;
    }

    .method-stepper {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
    }

    .method-step {
        background: #f5f8fd;
        border: 1px solid rgba(18, 53, 106, 0.08);
        border-radius: 999px;
        padding: 0.45rem 0.72rem;
        color: #1d3a62;
        font-size: 0.8rem;
        font-weight: 700;
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero(cycle_label: str) -> None:
    st.markdown(
        f"""
<div class="method-hero">
  <div class="method-hero-badge">Méthodologie</div>
  <h2>CONVENTIONS, RÈGLES DE LECTURE ET LIMITES DU DISPOSITIF</h2>
  <p>
    Cette page explique comment la plateforme de contrôle interne IMF prépare la donnée,
    applique un référentiel commun au cycle <strong>{html.escape(cycle_label)}</strong>,
    produit ses alertes et restitue des analyses de surveillance, de portefeuille, de risque
    et de qualité dans une interface unique.
  </p>
  <div class="method-chip-row">
    <span class="method-chip">Standardisation</span>
    <span class="method-chip">Contrôle interne</span>
    <span class="method-chip">Couverture de cycle</span>
    <span class="method-chip">Limites d'interprétation</span>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_card_grid(cards: list[dict[str, str]]) -> None:
    blocks: list[str] = []
    for card in cards:
        label = html.escape(str(card.get("label", "")), quote=False)
        value = html.escape(str(card.get("value", "")), quote=False)
        subtitle = html.escape(str(card.get("subtitle", "")), quote=False).replace("\n", "<br>")
        blocks.append(
            f"""
<div class="method-card">
  <div class="method-card-label">{label}</div>
  <div class="method-card-value">{value}</div>
  <div class="method-card-sub">{subtitle}</div>
</div>
"""
        )
    st.markdown(f"<div class='method-card-grid'>{''.join(blocks)}</div>", unsafe_allow_html=True)


def _render_formula_cards(cycle_key: str) -> None:
    blocks: list[str] = []
    for item in _build_formula_cards(cycle_key):
        label = html.escape(item["label"], quote=False)
        formula = html.escape(item["formula"], quote=False)
        why = html.escape(item["why"], quote=False)
        blocks.append(
            f"""
<div class="method-formula-card">
  <div class="method-formula-label">{label}</div>
  <div class="method-formula-code">{formula}</div>
  <div class="method-formula-why">{why}</div>
</div>
"""
        )
    st.markdown(f"<div class='method-formula-grid'>{''.join(blocks)}</div>", unsafe_allow_html=True)


def _render_path() -> None:
    st.markdown(
        """
<div class="method-path">
  <div class="method-path-title">Chaîne de traitement</div>
  <div class="method-stepper">
    <div class="method-step">1. Charger la base</div>
    <div class="method-step">2. Renommer les colonnes</div>
    <div class="method-step">3. Nettoyer dates et montants</div>
    <div class="method-step">4. Harmoniser les valeurs métier</div>
    <div class="method-step">5. Détecter les alertes</div>
    <div class="method-step">6. Restituer les analyses</div>
    <div class="method-step">7. Valider humainement</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_methodology_tab(cycle_key: str = "credit", standardized_df: pd.DataFrame | None = None) -> None:
    _inject_methodology_styles()
    cycle_spec = get_cycle_spec(cycle_key)
    cycle_coverage = build_cycle_coverage_summary(standardized_df, cycle_key)

    _render_hero(cycle_spec["label"])
    _render_card_grid(
        [
            {
                "label": "Source",
                "value": "Excel / CSV",
                "subtitle": "La plateforme part de fichiers opérationnels qui ne suivent pas toujours la même structure.",
            },
            {
                "label": "Objectif",
                "value": "Lecture commune",
                "subtitle": "Rendre les analyses comparables malgré des bases hétérogènes.",
            },
            {
                "label": "Cycle actif",
                "value": cycle_spec["label"],
                "subtitle": cycle_spec["control_objective"],
            },
            {
                "label": "Couverture",
                "value": f"{cycle_coverage['detected_count']}/{cycle_coverage['total']}",
                "subtitle": "Champs clés détectés dans la base chargée pour ce cycle.",
            },
        ]
    )

    _render_path()

    render_summary_box(
        "Cadre de lecture",
        [
            "Cette page documente les conventions appliquées par la plateforme de contrôle interne.",
            "Elle aide à distinguer ce qui relève d'une automatisation utile de ce qui doit encore être confirmé par le contrôleur, l'auditeur ou le responsable métier.",
            cycle_coverage["summary"],
        ],
    )

    render_summary_box(
        f"Référentiel du cycle : {cycle_spec['label']}",
        [
            cycle_spec["summary"],
            cycle_spec["control_objective"],
            "Les tableaux ci-dessous servent de guide d'interprétation pour les autres onglets.",
        ],
    )

    cycle_left, cycle_right = st.columns((1.1, 1))
    with cycle_left:
        render_panel_title("Points de contrôle du cycle")
        st.dataframe(build_cycle_control_table(cycle_key), width="stretch", hide_index=True, height=250)
    with cycle_right:
        render_panel_title("Champs attendus")
        st.dataframe(
            build_cycle_expected_fields_table(
                cycle_key,
                available_columns=standardized_df.columns.tolist() if standardized_df is not None else [],
            ),
            width="stretch",
            hide_index=True,
            height=250,
        )

    governance_left, governance_right = st.columns((1, 1))
    with governance_left:
        render_panel_title("Niveaux de contrôle")
        st.dataframe(build_control_levels_table(), width="stretch", hide_index=True, height=250)
    with governance_right:
        render_panel_title("Principes directeurs")
        st.dataframe(build_control_principles_table(), width="stretch", hide_index=True, height=250)

    render_panel_title("Chaîne de reporting et de suivi")
    st.dataframe(build_reporting_chain_table(), width="stretch", hide_index=True, height=240)

    render_panel_title("Cartographie synthétique des risques")
    st.dataframe(build_risk_cartography_table(), width="stretch", hide_index=True, height=280)

    render_panel_title("Logique de standardisation")
    st.dataframe(_build_standardization_table(), width="stretch", hide_index=True, height=280)

    render_panel_title("Formules et lectures rapides")
    _render_formula_cards(cycle_key)

    reading_left, reading_right = st.columns((1, 1))
    with reading_left:
        render_panel_title("Portée de l'analyse")
        st.dataframe(_build_analysis_scope_table(), width="stretch", hide_index=True, height=230)
    with reading_right:
        render_panel_title("Lecture du cycle")
        st.dataframe(_build_cycle_reading_table(cycle_spec["label"]), width="stretch", hide_index=True, height=230)

    quality_left, quality_right = st.columns((1, 1))
    with quality_left:
        render_panel_title("Contrôles qualité intégrés")
        st.dataframe(_build_quality_table(), width="stretch", hide_index=True, height=250)
    with quality_right:
        render_panel_title("Limites à garder en tête")
        st.dataframe(_build_limit_table(), width="stretch", hide_index=True, height=250)

    render_summary_box(
        "Bon usage du tableau de bord",
        [
            "Un graphique, une watchlist ou un score doit toujours être relu avec le périmètre filtré, la qualité de la base et les procédures de l'institution.",
            "Une alerte est un point de départ pour la revue, pas une conclusion automatique.",
            "Le dispositif est plus robuste quand les équipes documentent les corrections, les commentaires et les suites données.",
        ],
    )
