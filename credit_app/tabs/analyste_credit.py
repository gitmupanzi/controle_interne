from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from credit_app.ui import render_panel_title, render_summary_box


def _build_concepts_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Notion": "Capacité de remboursement",
                "Definition": "Marge théorique du client après déduction des charges mensuelles.",
                "Lecture utile": "Une capacité négative ou trop faible invite à revoir la décision ou les conditions du crédit.",
            },
            {
                "Notion": "Taux d'endettement",
                "Definition": "Part des charges mensuelles dans le revenu mensuel.",
                "Lecture utile": "Un taux élevé signale une pression financière plus forte et un risque de défaut plus important.",
            },
            {
                "Notion": "Niveau de risque",
                "Definition": "Classement du dossier selon le risque déjà présent, le score crédit, l'endettement et les retards.",
                "Lecture utile": "Permet de prioriser les revues avant l'octroi et pendant le suivi.",
            },
            {
                "Notion": "Statut du dossier",
                "Definition": "Étape de vie du dossier : reçu, en analyse, approuvé, rejeté, décaissé, en remboursement, en retard, clôturé.",
                "Lecture utile": "Aide à suivre le pipeline et les points de blocage dans le processus de crédit.",
            },
            {
                "Notion": "Statut de remboursement",
                "Definition": "Situation du remboursement après décaissement.",
                "Lecture utile": "Permet d'identifier les clients à jour, en retard ou soldés.",
            },
            {
                "Notion": "Watchlist",
                "Definition": "Liste des dossiers signalés par les règles de surveillance.",
                "Lecture utile": "Concentre les cas à vérifier rapidement : risque élevé, retard long, capacité négative ou données incomplètes.",
            },
        ]
    )


def _build_role_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Bloc": "Évaluation des demandes", "Points cles": "Vérifier les revenus, charges, garanties, cohérence du dossier et capacité de remboursement."},
            {"Bloc": "Analyse des risques", "Points cles": "Mesurer l'endettement, les retards, le score, les fragilités et les mesures d'atténuation."},
            {"Bloc": "Recommandation", "Points cles": "Formuler une décision argumentée : recommandé, recommandé avec conditions, à revoir, non recommandé."},
            {"Bloc": "Suivi du portefeuille", "Points cles": "Surveiller les échéances, les retards, les dossiers sensibles et les comptes à risque."},
            {"Bloc": "Reporting", "Points cles": "Produire des tableaux de bord par agence, produit, période, risque et remboursement."},
            {"Bloc": "Qualité des données", "Points cles": "Détecter les doublons, incohérences, valeurs manquantes et documenter les corrections."},
        ]
    )


def _build_process_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Etape": 1, "Processus": "Réception de la demande de crédit"},
            {"Etape": 2, "Processus": "Collecte des informations du client"},
            {"Etape": 3, "Processus": "Verification des documents fournis"},
            {"Etape": 4, "Processus": "Analyse financiere et comportementale"},
            {"Etape": 5, "Processus": "Évaluation du risque"},
            {"Etape": 6, "Processus": "Calcul de la capacité de remboursement"},
            {"Etape": 7, "Processus": "Formulation d'une recommandation"},
            {"Etape": 8, "Processus": "Validation par les responsables concernes"},
            {"Etape": 9, "Processus": "Suivi du crédit après approbation"},
            {"Etape": 10, "Processus": "Reporting et mise a jour du dossier client"},
        ]
    )


def _build_kpi_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Famille": "Demande", "Indicateurs": "Nombre de demandes, taux d'approbation, montant demandé, montant accordé, délai de traitement"},
            {"Famille": "Risque", "Indicateurs": "Dossiers à risque élevé, taux d'endettement moyen, score moyen, dossiers incomplets"},
            {"Famille": "Remboursement", "Indicateurs": "Clients a jour, clients en retard, retard moyen, retard > 30 jours, portefeuille a risque"},
            {"Famille": "Pilotage", "Indicateurs": "Performance par agence, agent, produit, sexe, tranche d'âge et période"},
            {"Famille": "Qualite", "Indicateurs": "Doublons, valeurs manquantes, montants incoherents, statuts manquants"},
        ]
    )


def _inject_analyst_tab_styles() -> None:
    st.markdown(
        """
<style>
    .analyst-hero {
        position: relative;
        overflow: hidden;
        padding: 1.2rem 1.35rem;
        border-radius: 24px;
        color: #ffffff;
        background:
            linear-gradient(120deg, rgba(255,255,255,0.10), rgba(255,255,255,0.02)),
            linear-gradient(90deg, #0a2e69 0%, #1457ab 56%, #2e7dd7 100%);
        box-shadow: 0 18px 38px rgba(11, 44, 99, 0.18);
        border: 1px solid rgba(255,255,255,0.18);
        margin-bottom: 1rem;
    }

    .analyst-hero::before,
    .analyst-hero::after {
        content: "";
        position: absolute;
        border-radius: 50%;
        background: rgba(255,255,255,0.10);
        filter: blur(8px);
    }

    .analyst-hero::before {
        width: 220px;
        height: 220px;
        top: -120px;
        right: -30px;
    }

    .analyst-hero::after {
        width: 140px;
        height: 140px;
        left: -16px;
        bottom: -80px;
    }

    .analyst-hero-badge {
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

    .analyst-hero h2 {
        margin: 0;
        font-size: clamp(1.35rem, 2.2vw, 1.95rem);
        line-height: 1.15;
        letter-spacing: 0.03em;
        font-weight: 800;
    }

    .analyst-hero p {
        margin: 0.5rem 0 0;
        max-width: 62rem;
        font-size: 0.96rem;
        line-height: 1.45;
        color: rgba(255,255,255,0.94);
    }

    .analyst-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.8rem;
    }

    .analyst-chip {
        background: rgba(255,255,255,0.16);
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 999px;
        padding: 0.36rem 0.74rem;
        font-size: 0.77rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }

    .analyst-path {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(18, 53, 106, 0.10);
        border-radius: 20px;
        padding: 0.9rem 1rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
        margin: 0.35rem 0 1rem;
    }

    .analyst-path-title {
        color: #0b2c63;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
        margin-bottom: 0.6rem;
    }

    .analyst-stepper {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
    }

    .analyst-step {
        background: #f5f8fd;
        border: 1px solid rgba(18, 53, 106, 0.08);
        border-radius: 999px;
        padding: 0.45rem 0.72rem;
        color: #1d3a62;
        font-size: 0.8rem;
        font-weight: 700;
    }

    .analyst-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.75rem;
        margin: 0.35rem 0 1rem;
    }

    .analyst-card {
        background: rgba(255,255,255,0.95);
        border: 1px solid rgba(18, 53, 106, 0.10);
        border-radius: 18px;
        padding: 0.9rem 0.95rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
    }

    .analyst-card-label {
        color: #5a708c;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    .analyst-card-value {
        margin-top: 0.32rem;
        color: #1553a1;
        font-size: 1.32rem;
        line-height: 1.12;
        font-weight: 800;
    }

    .analyst-card-sub {
        margin-top: 0.24rem;
        color: #35506f;
        font-size: 0.83rem;
        line-height: 1.35;
    }

    .analyst-formula-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.75rem;
        margin-bottom: 1rem;
    }

    .analyst-formula-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(246,250,255,0.96) 100%);
        border-radius: 18px;
        border: 1px solid rgba(18, 53, 106, 0.10);
        padding: 0.95rem 1rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
    }

    .analyst-formula-label {
        color: #0b2c63;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    .analyst-formula-code {
        margin-top: 0.5rem;
        color: #1553a1;
        font-family: Consolas, "Courier New", monospace;
        font-size: 0.89rem;
        line-height: 1.45;
        white-space: pre-wrap;
    }

    .analyst-formula-why {
        margin-top: 0.5rem;
        color: #3d5878;
        font-size: 0.83rem;
        line-height: 1.38;
    }
    
</style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero() -> None:
    st.markdown(
        """
<div class="analyst-hero">
  <div class="analyst-hero-badge">Guide métier</div>
  <h2>NOTIONS IMPORTANTES POUR L'ANALYSE ET LE SUIVI DU CRÉDIT</h2>
  <p>
    Cet onglet aide à relire correctement les indicateurs du dashboard, à comprendre
    le rôle de l'analyste crédit, et à structurer les décisions autour du risque,
    de la capacité de remboursement, du suivi du portefeuille et de la qualité des données.
  </p>
  <div class="analyst-chip-row">
    <span class="analyst-chip">Analyse crédit</span>
    <span class="analyst-chip">Gestion du risque</span>
    <span class="analyst-chip">Suivi portefeuille</span>
    <span class="analyst-chip">Documentation et reporting</span>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_learning_path() -> None:
    st.markdown(
        """
<div class="analyst-path">
  <div class="analyst-path-title">Parcours conseillé</div>
  <div class="analyst-stepper">
    <div class="analyst-step">1. Comprendre le dossier</div>
    <div class="analyst-step">2. Mesurer la capacité</div>
    <div class="analyst-step">3. Lire le risque</div>
    <div class="analyst-step">4. Formuler la recommandation</div>
    <div class="analyst-step">5. Suivre le portefeuille</div>
    <div class="analyst-step">6. Vérifier la qualité</div>
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
<div class="analyst-card">
  <div class="analyst-card-label">{label}</div>
  <div class="analyst-card-value">{value}</div>
  <div class="analyst-card-sub">{subtitle}</div>
</div>
"""
        )
    st.markdown(f"<div class='analyst-card-grid'>{''.join(blocks)}</div>", unsafe_allow_html=True)


def _render_formula_cards() -> None:
    formulas = [
        {
            "label": "Capacite de remboursement",
            "formula": "Revenu mensuel - Charges mensuelles",
            "why": "Donne une première lecture de la marge théorique disponible pour rembourser le crédit.",
        },
        {
            "label": "Taux d'endettement",
            "formula": "Charges mensuelles / Revenu mensuel",
            "why": "Aide a estimer la pression financiere supportee par le client.",
        },
        {
            "label": "Mensualite estimee",
            "formula": "Montant accordé / Durée du crédit en mois",
            "why": "Approximation simple de l'effort mensuel attendu sur le dossier.",
        },
        {
            "label": "Taux d'approbation",
            "formula": "Dossiers favorables / total dossiers",
            "why": "Permet de suivre la dynamique de décision sur le périmètre analysé.",
        },
        {
            "label": "Taux de retard",
            "formula": "Dossiers en retard / total dossiers",
            "why": "Mesure la fragilité du portefeuille sur le périmètre courant.",
        },
        {
            "label": "Watchlist",
            "formula": "Risque élevé + retards longs + capacité négative + données incomplètes",
            "why": "Sert a prioriser les cas qui demandent une revue rapide ou une action immediate.",
        },
    ]
    blocks: list[str] = []
    for item in formulas:
        label = html.escape(item["label"], quote=False)
        formula = html.escape(item["formula"], quote=False)
        why = html.escape(item["why"], quote=False)
        blocks.append(
            f"""
<div class="analyst-formula-card">
  <div class="analyst-formula-label">{label}</div>
  <div class="analyst-formula-code">{formula}</div>
  <div class="analyst-formula-why">{why}</div>
</div>
"""
        )
    st.markdown(f"<div class='analyst-formula-grid'>{''.join(blocks)}</div>", unsafe_allow_html=True)


def render_analyste_credit_tab() -> None:
    _inject_analyst_tab_styles()
    _render_hero()

    _render_card_grid(
        [
            {
            "label": "Finalité",
            "value": "Décider juste",
            "subtitle": "Aider l'organisation à accorder les crédits de manière responsable et documentée.",
            },
            {
                "label": "Axes couverts",
                "value": "4 blocs",
                "subtitle": "Demande, risque, remboursement et qualité des données.",
            },
            {
                "label": "Lecture clé",
                "value": "Risque + capacité",
                "subtitle": "Un dossier ne se lit jamais sur un seul indicateur.",
            },
            {
                "label": "Réflexe",
                "value": "Vérifier",
                "subtitle": "Toujours relire le contexte, les pièces et la cohérence des données.",
            },
        ]
    )

    _render_learning_path()

    render_summary_box(
        "Finalité du projet",
        [
            "Cette application aide les équipes crédit, commerciales, recouvrement et direction à prendre des décisions plus fiables.",
            "Elle centralise l'analyse des demandes, le suivi du portefeuille, la lecture du risque et la qualité des données dans une même interface.",
            "L'objectif est de réduire les risques financiers tout en améliorant la performance du portefeuille crédit.",
        ],
    )

    top_left, top_right = st.columns(2)
    with top_left:
        render_panel_title("Contexte métier")
        render_summary_box(
            "Pourquoi l'analyse crédit est centrale",
            [
                "Chaque demande doit être évaluée à partir des informations personnelles, financières et comportementales du client.",
                "L'analyste crédit intervient avant l'octroi, mais aussi pendant le suivi des crédits approuvés.",
                "La qualité des données et la traçabilité des décisions sont essentielles pour limiter les pertes et documenter les choix.",
            ],
        )
    with top_right:
        render_panel_title("Resultats attendus")
        render_summary_box(
            "Ce que l'organisation recherche",
            [
                "Mieux analyser les demandes de crédit.",
                "Détecter plus vite les retards et les dossiers à risque.",
                "Produire des tableaux de bord clairs pour le pilotage.",
                "Faciliter la collaboration entre crédit, recouvrement, relation client et direction.",
            ],
        )

    render_panel_title("Formules de lecture rapide")
    _render_formula_cards()

    render_panel_title("Rôle de l'analyste crédit")
    st.dataframe(_build_role_table(), width="stretch", hide_index=True, height=320)

    render_panel_title("Processus général d'analyse crédit")
    st.dataframe(_build_process_table(), width="stretch", hide_index=True, height=410)

    concepts_left, concepts_right = st.columns((1.25, 1))
    with concepts_left:
        render_panel_title("Notions importantes à bien lire")
        st.dataframe(_build_concepts_table(), width="stretch", hide_index=True, height=360)
    with concepts_right:
        render_panel_title("Bonnes pratiques de lecture")
        render_summary_box(
            "Réflexes utiles",
            [
                "Relire un indicateur avec son périmètre filtré.",
                "Vérifier la qualité des données avant de conclure.",
                "Ne pas lire un risque élevé sans regarder aussi la capacité, l'endettement et les retards.",
                "Documenter la recommandation avec des éléments objectifs.",
                "Prioriser les dossiers watchlist et les retards longs.",
            ],
        )
        render_panel_title("Confidentialite")
        render_summary_box(
            "Regles essentielles",
            [
                "Limiter l'accès aux données aux personnes autorisées.",
                "Éviter le partage non sécurisé des fichiers clients.",
                "Protéger les informations personnelles et financières.",
                "Conserver une traçabilité des modifications et des décisions.",
            ],
        )

    render_panel_title("Indicateurs de performance à suivre")
    st.dataframe(_build_kpi_table(), width="stretch", hide_index=True, height=260)

    render_panel_title("Automatisations possibles")
    render_summary_box(
        "Pistes d'évolution",
        [
            "Génération automatique des rapports de crédit.",
            "Scoring automatique des demandes.",
            "Alertes sur les retards de paiement et les dossiers à risque.",
            "Contrôle automatique des données manquantes.",
            "Mise à jour automatisée des tableaux de bord et des exports.",
        ],
    )
