from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from credit_app.ui import render_panel_title, render_summary_box


def _build_standardization_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Bloc": "Mapping des colonnes", "Principe": "Plusieurs variantes de noms sont reconnues automatiquement.", "Impact": "Permet de charger des bases heterogenes sans exiger un schema unique strict."},
            {"Bloc": "Reference externe", "Principe": "`data/Rename_columns.xlsx` est utilise quand une correspondance utile existe.", "Impact": "Etend le mapping interne avec les conventions locales du projet."},
            {"Bloc": "Dates", "Principe": "Les dates sont converties si possible.", "Impact": "Active les filtres de periode et les analyses temporelles."},
            {"Bloc": "Numeriques", "Principe": "Les colonnes montants, score, retards, duree et age sont nettoyees puis converties.", "Impact": "Fiabilise les calculs et limite les erreurs de type."},
            {"Bloc": "Valeurs metier", "Principe": "Les statuts et certaines valeurs comme le sexe sont harmonises.", "Impact": "Permet des regroupements plus propres dans les graphiques et tableaux."},
        ]
    )


def _build_risk_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Priorite": 1, "Source": "Niveau de risque deja present", "Lecture": "Si la base contient deja un niveau de risque exploitable, il est privilegie."},
            {"Priorite": 2, "Source": "Score credit", "Lecture": "Le score alimente une classification simple en faible, moyen ou eleve."},
            {"Priorite": 3, "Source": "Taux d'endettement", "Lecture": "Le ratio charges / revenu sert de lecture de pression financiere."},
            {"Priorite": 4, "Source": "Retard en jours", "Lecture": "Les retards restent un signal fort de vigilance, surtout au-dela de 30 jours."},
        ]
    )


def _build_quality_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Controle": "Identifiants clients manquants", "Pourquoi c'est important": "Evite les dossiers non tracables."},
            {"Controle": "Identifiants dossiers manquants ou dupliques", "Pourquoi c'est important": "Protege les analyses contre les surcomptes et les confusions."},
            {"Controle": "Montants negatifs", "Pourquoi c'est important": "Signale des erreurs de saisie ou de signe."},
            {"Controle": "Montant accorde > montant demande", "Pourquoi c'est important": "Repere des incoherences metier."},
            {"Controle": "Informations financieres manquantes", "Pourquoi c'est important": "Fragilise la lecture de capacite et d'endettement."},
            {"Controle": "Capacite de remboursement negative", "Pourquoi c'est important": "Oriente rapidement vers les dossiers potentiellement fragiles."},
            {"Controle": "Retards negatifs", "Pourquoi c'est important": "Signale des erreurs temporelles dans les donnees."},
        ]
    )


def _inject_methodology_styles() -> None:
    st.markdown(
        """
<style>
    .method-hero {
        position: relative;
        overflow: hidden;
        padding: 1.2rem 1.35rem;
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
        width: 145px;
        height: 145px;
        left: -18px;
        bottom: -78px;
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


def _render_hero() -> None:
    st.markdown(
        """
<div class="method-hero">
  <div class="method-hero-badge">Methodologie</div>
  <h2>CONVENTIONS, REGLES DE CALCUL ET LIMITES D'INTERPRETATION</h2>
  <p>
    Cette page explique comment l'application standardise les donnees, calcule les variables
    derivees, classe le risque et applique ses controles qualite. Elle aide a relire les
    resultats avec les bons repères techniques et metiers.
  </p>
  <div class="method-chip-row">
    <span class="method-chip">Standardisation</span>
    <span class="method-chip">Formules</span>
    <span class="method-chip">Risque</span>
    <span class="method-chip">Qualite</span>
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


def _render_formula_cards() -> None:
    formulas = [
        {
            "label": "Capacite",
            "formula": "Revenu mensuel - Charges mensuelles",
            "why": "Mesure simple de la marge theorique de remboursement.",
        },
        {
            "label": "Endettement",
            "formula": "Charges mensuelles / Revenu mensuel",
            "why": "Aide a lire la pression financiere sur le client.",
        },
        {
            "label": "Mensualite estimee",
            "formula": "Montant accorde / Duree du credit en mois",
            "why": "Donne une approximation simple de l'effort mensuel attendu.",
        },
        {
            "label": "Risque simple",
            "formula": "Risque declare -> Score -> Endettement -> Retard",
            "why": "Ordre de priorite applique pour la classification automatique.",
        },
    ]
    blocks: list[str] = []
    for item in formulas:
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
  <div class="method-path-title">Pipeline logique</div>
  <div class="method-stepper">
    <div class="method-step">1. Charger la base</div>
    <div class="method-step">2. Renommer les colonnes</div>
    <div class="method-step">3. Nettoyer les types</div>
    <div class="method-step">4. Deriver les variables</div>
    <div class="method-step">5. Classer le risque</div>
    <div class="method-step">6. Controler la qualite</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_methodology_tab() -> None:
    _inject_methodology_styles()
    _render_hero()

    _render_card_grid(
        [
            {
                "label": "Point de depart",
                "value": "Base heterogene",
                "subtitle": "L'application part de fichiers Excel ou CSV qui ne suivent pas toujours le meme schema.",
            },
            {
                "label": "Objectif",
                "value": "Lire ensemble",
                "subtitle": "Rendre comparables les analyses portefeuille, risque, remboursement et qualite.",
            },
            {
                "label": "Reflexe",
                "value": "Verifier le mapping",
                "subtitle": "Le sens des indicateurs depend de la bonne reconnaissance des colonnes sources.",
            },
            {
                "label": "Limite",
                "value": "Heuristique",
                "subtitle": "Certaines regles restent simples et doivent etre adaptees a votre institution.",
            },
        ]
    )

    _render_path()

    render_summary_box(
        "Cadre de lecture",
        [
            "Cette page documente les conventions appliquees par l'application.",
            "Elle rassemble les definitions, conventions et limites utiles a la lecture des analyses.",
            "Elle aide a distinguer ce qui releve d'une regle de calcul automatique et ce qui reste du ressort de l'analyse humaine.",
        ],
    )

    render_panel_title("Principes de standardisation")
    st.dataframe(_build_standardization_table(), width="stretch", hide_index=True, height=280)

    render_panel_title("Formules de base")
    _render_formula_cards()

    left, right = st.columns((1, 1))
    with left:
        render_panel_title("Classification simple du risque")
        st.dataframe(_build_risk_table(), width="stretch", hide_index=True, height=250)
    with right:
        render_panel_title("Controles qualite appliques")
        st.dataframe(_build_quality_table(), width="stretch", hide_index=True, height=250)

    render_panel_title("Limites actuelles")
    render_summary_box(
        "Points d'attention",
        [
            "La qualite de l'analyse depend directement de la qualite du fichier source.",
            "Les aliases de colonnes peuvent etre enrichis selon vos bases reelles.",
            "Les regles de scoring et d'octroi doivent etre adaptees a votre institution.",
            "L'outil ne remplace pas les validations humaines du comite credit.",
        ],
    )
