from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from credit_app.control_references import (
    build_credit_file_checklist_table,
    build_credit_product_matrix_table,
    build_control_levels_table,
    build_control_principles_table,
    build_general_kyc_requirements_table,
    build_reporting_chain_table,
    build_risk_cartography_table,
    build_savings_product_reference_table,
    build_service_pricing_reference_table,
)
from credit_app.cycles import (
    build_cycle_control_table,
    build_cycle_coverage_summary,
    build_cycle_expected_fields_table,
    get_cycle_spec,
)
from credit_app.ui import render_panel_title, render_summary_box


def _build_mission_steps_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Phase": "Préparer", "Contenu": "Définir le périmètre, la période, les objectifs, les sources et les seuils de revue."},
            {"Phase": "Collecter", "Contenu": "Rassembler les extractions, procédures, pièces et justificatifs utiles."},
            {"Phase": "Tester", "Contenu": "Comparer la pratique aux règles, vérifier les écarts et isoler les cas sensibles."},
            {"Phase": "Conclure", "Contenu": "Formuler un constat clair, une cause probable, un impact et une recommandation."},
            {"Phase": "Suivre", "Contenu": "Documenter les actions correctives, les responsables et les échéances."},
        ]
    )


def _build_evidence_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Preuve": "Base détaillée", "Utilité": "Mesure les volumes, les anomalies, les concentrations et les variations."},
            {"Preuve": "Procédure interne", "Utilité": "Permet de comparer la pratique observée à la règle officielle."},
            {"Preuve": "Pièce justificative", "Utilité": "Confirme la conformité d'une opération ou d'une décision."},
            {"Preuve": "Validation hiérarchique", "Utilité": "Vérifie l'existence d'une autorisation ou d'une revue formelle."},
            {"Preuve": "Journal / traçabilité", "Utilité": "Permet de relier une action, une date, un acteur et un support."},
        ]
    )


def _build_finding_structure_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Élément": "Constat", "Attendu": "Ce qui a été observé, de façon factuelle et vérifiable."},
            {"Élément": "Critère", "Attendu": "La règle, la procédure ou l'exigence qui sert de référence."},
            {"Élément": "Cause", "Attendu": "L'explication probable de l'écart ou de la faiblesse de contrôle."},
            {"Élément": "Impact", "Attendu": "Le risque ou la conséquence pour l'IMF."},
            {"Élément": "Recommandation", "Attendu": "L'action à mettre en place pour réduire le risque."},
            {"Élément": "Responsable / délai", "Attendu": "La personne en charge et l'échéance de suivi."},
        ]
    )


def _build_follow_up_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Priorité": "Immédiate", "Quand l'utiliser": "Risque fort, irrégularité sensible ou faiblesse majeure de contrôle."},
            {"Priorité": "Courte", "Quand l'utiliser": "Écart significatif corrigeable rapidement."},
            {"Priorité": "Planifiée", "Quand l'utiliser": "Amélioration de processus demandant coordination ou paramétrage."},
            {"Priorité": "Récurrente", "Quand l'utiliser": "Point à suivre dans chaque mission ou chaque clôture."},
        ]
    )


def _build_review_questions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Question": "Le périmètre est-il complet ?", "Pourquoi": "Évite de conclure sur une vision partielle ou tronquée."},
            {"Question": "La base est-elle assez propre ?", "Pourquoi": "Un indicateur fragile peut créer une fausse alerte ou masquer un vrai risque."},
            {"Question": "Quelle règle a été enfreinte ?", "Pourquoi": "Un constat doit toujours être relié à un critère clair."},
            {"Question": "L'écart est-il isolé ou systémique ?", "Pourquoi": "Aide à distinguer l'incident ponctuel de la faiblesse structurelle."},
            {"Question": "Qui doit agir, et quand ?", "Pourquoi": "Le suivi devient utile seulement si une action est attribuée et datée."},
        ]
    )


def _build_dashboard_reading_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Bloc": "Surveillance", "Utilité": "Faire ressortir les alertes, les regroupements actifs et les cas à revoir rapidement."},
            {"Bloc": "Portefeuille", "Utilité": "Lire les volumes, les concentrations et les variations de structure."},
            {"Bloc": "Risque", "Utilité": "Qualifier les signaux d'exposition, de fragilité ou d'irrégularité."},
            {"Bloc": "Qualité", "Utilité": "Mesurer la fiabilité de la base avant de tirer une conclusion."},
            {"Bloc": "Export", "Utilité": "Conserver une trace de la base standardisée, des contrôles et des résultats."},
        ]
    )


def _inject_audit_styles() -> None:
    st.markdown(
        """
<style>
    .audit-hero {
        position: relative;
        overflow: hidden;
        padding: 1.25rem 1.4rem;
        border-radius: 24px;
        color: #ffffff;
        background:
            linear-gradient(125deg, rgba(255,255,255,0.10), rgba(255,255,255,0.02)),
            linear-gradient(90deg, #0d2b57 0%, #16519a 55%, #3a7bd5 100%);
        box-shadow: 0 18px 38px rgba(11, 44, 99, 0.16);
        border: 1px solid rgba(255,255,255,0.18);
        margin-bottom: 1rem;
    }

    .audit-hero::before,
    .audit-hero::after {
        content: "";
        position: absolute;
        border-radius: 50%;
        background: rgba(255,255,255,0.10);
        filter: blur(8px);
    }

    .audit-hero::before {
        width: 220px;
        height: 220px;
        top: -120px;
        right: -28px;
    }

    .audit-hero::after {
        width: 150px;
        height: 150px;
        left: -22px;
        bottom: -76px;
    }

    .audit-hero-badge {
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

    .audit-hero h2 {
        margin: 0;
        font-size: clamp(1.35rem, 2.2vw, 1.95rem);
        line-height: 1.15;
        letter-spacing: 0.03em;
        font-weight: 800;
    }

    .audit-hero p {
        margin: 0.5rem 0 0;
        max-width: 62rem;
        font-size: 0.96rem;
        line-height: 1.45;
        color: rgba(255,255,255,0.94);
    }

    .audit-chip-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.8rem;
    }

    .audit-chip {
        background: rgba(255,255,255,0.16);
        border: 1px solid rgba(255,255,255,0.22);
        border-radius: 999px;
        padding: 0.36rem 0.74rem;
        font-size: 0.77rem;
        font-weight: 700;
    }

    .audit-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.75rem;
        margin: 0.35rem 0 1rem;
    }

    .audit-card {
        background: rgba(255,255,255,0.96);
        border: 1px solid rgba(18, 53, 106, 0.10);
        border-radius: 18px;
        padding: 0.9rem 0.95rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
    }

    .audit-card-label {
        color: #5a708c;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    .audit-card-value {
        margin-top: 0.32rem;
        color: #1553a1;
        font-size: 1.32rem;
        line-height: 1.12;
        font-weight: 800;
    }

    .audit-card-sub {
        margin-top: 0.24rem;
        color: #35506f;
        font-size: 0.83rem;
        line-height: 1.35;
    }

    .audit-path {
        background: rgba(255,255,255,0.94);
        border: 1px solid rgba(18, 53, 106, 0.10);
        border-radius: 20px;
        padding: 0.9rem 1rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
        margin: 0.35rem 0 1rem;
    }

    .audit-path-title {
        color: #0b2c63;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
        margin-bottom: 0.6rem;
    }

    .audit-stepper {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
    }

    .audit-step {
        background: #f5f8fd;
        border: 1px solid rgba(18, 53, 106, 0.08);
        border-radius: 999px;
        padding: 0.45rem 0.72rem;
        color: #1d3a62;
        font-size: 0.8rem;
        font-weight: 700;
    }

    .audit-focus-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.75rem;
        margin: 0.25rem 0 1rem;
    }

    .audit-focus-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(246,250,255,0.96) 100%);
        border-radius: 18px;
        border: 1px solid rgba(18, 53, 106, 0.10);
        padding: 0.95rem 1rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.07);
    }

    .audit-focus-label {
        color: #0b2c63;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
    }

    .audit-focus-text {
        margin-top: 0.45rem;
        color: #35506f;
        font-size: 0.84rem;
        line-height: 1.42;
    }

    .audit-note-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 0.8rem;
        margin: 0.35rem 0 1rem;
    }

    .audit-note {
        border-radius: 20px;
        padding: 1rem 1.05rem;
        box-shadow: 0 12px 26px rgba(11, 44, 99, 0.06);
    }

    .audit-note-good {
        background: linear-gradient(180deg, rgba(239,247,255,0.95) 0%, rgba(248,252,255,0.97) 100%);
        border: 1px solid rgba(51, 112, 191, 0.14);
    }

    .audit-note-risk {
        background: linear-gradient(180deg, rgba(255,246,239,0.95) 0%, rgba(255,251,248,0.97) 100%);
        border: 1px solid rgba(222, 122, 45, 0.14);
    }

    .audit-note-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 800;
        margin-bottom: 0.45rem;
    }

    .audit-note-good .audit-note-title {
        color: #0b2c63;
    }

    .audit-note-risk .audit-note-title {
        color: #a65310;
    }

    .audit-note-text {
        color: #35506f;
        font-size: 0.84rem;
        line-height: 1.42;
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero(cycle_label: str) -> None:
    st.markdown(
        f"""
<div class="audit-hero">
  <div class="audit-hero-badge">Audit et contrôle</div>
  <h2>CADRE DE REVUE, DE CONFORMITÉ ET DE SUIVI DES RISQUES</h2>
  <p>
    Cet onglet rassemble les repères utiles pour conduire une mission de contrôle interne
    ou d'audit sur le <strong>{html.escape(cycle_label)}</strong> :
    périmètre, preuves attendues, structure des constats, chaîne de suivi et logique
    de recommandation.
  </p>
  <div class="audit-chip-row">
    <span class="audit-chip">Gouvernance</span>
    <span class="audit-chip">Conformité</span>
    <span class="audit-chip">Traçabilité</span>
    <span class="audit-chip">Suivi des recommandations</span>
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
<div class="audit-card">
  <div class="audit-card-label">{label}</div>
  <div class="audit-card-value">{value}</div>
  <div class="audit-card-sub">{subtitle}</div>
</div>
"""
        )
    st.markdown(f"<div class='audit-card-grid'>{''.join(blocks)}</div>", unsafe_allow_html=True)


def _render_focus_grid(items: list[dict[str, str]]) -> None:
    blocks: list[str] = []
    for item in items:
        label = html.escape(str(item.get("label", "")), quote=False)
        text = html.escape(str(item.get("text", "")), quote=False)
        blocks.append(
            f"""
<div class="audit-focus-card">
  <div class="audit-focus-label">{label}</div>
  <div class="audit-focus-text">{text}</div>
</div>
"""
        )
    st.markdown(f"<div class='audit-focus-grid'>{''.join(blocks)}</div>", unsafe_allow_html=True)


def _render_note_pair() -> None:
    st.markdown(
        """
<div class="audit-note-grid">
  <div class="audit-note audit-note-good">
    <div class="audit-note-title">Ce que le tableau de bord fait bien</div>
    <div class="audit-note-text">
      Il aide à repérer rapidement les signaux, les concentrations, les anomalies de qualité
      et les regroupements qui demandent une revue immédiate.
    </div>
  </div>
  <div class="audit-note audit-note-risk">
    <div class="audit-note-title">Ce qu'il faut encore confirmer</div>
    <div class="audit-note-text">
      Les pièces, les validations, la conformité procédurale réelle, la matérialité de l'écart
      et la cause profonde restent à documenter par l'équipe de contrôle.
    </div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _render_path() -> None:
    st.markdown(
        """
<div class="audit-path">
  <div class="audit-path-title">Parcours de mission</div>
  <div class="audit-stepper">
    <div class="audit-step">1. Cadrer le périmètre</div>
    <div class="audit-step">2. Vérifier la base</div>
    <div class="audit-step">3. Tester les points de contrôle</div>
    <div class="audit-step">4. Qualifier les écarts</div>
    <div class="audit-step">5. Recommander</div>
    <div class="audit-step">6. Suivre les actions</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_audit_control_tab(cycle_key: str = "credit", standardized_df: pd.DataFrame | None = None) -> None:
    _inject_audit_styles()
    cycle_spec = get_cycle_spec(cycle_key)
    cycle_coverage = build_cycle_coverage_summary(standardized_df, cycle_key)

    _render_hero(cycle_spec["label"])
    _render_card_grid(
        [
            {
                "label": "Finalité",
                "value": "Sécuriser",
                "subtitle": "Réduire les risques, fiabiliser les traitements et renforcer la conformité.",
            },
            {
                "label": "Réflexe",
                "value": "Prouver",
                "subtitle": "Chaque conclusion doit pouvoir être reliée à une source ou une pièce.",
            },
            {
                "label": "Couverture",
                "value": f"{cycle_coverage['detected_count']}/{cycle_coverage['total']}",
                "subtitle": "Champs clés disponibles pour le cycle sélectionné.",
            },
            {
                "label": "Résultat attendu",
                "value": "Constat utile",
                "subtitle": "Un bon constat est clair, traçable, priorisé et suivi dans le temps.",
            },
        ]
    )

    _render_path()
    _render_focus_grid(
        [
            {
                "label": "Point de départ",
                "text": "Toujours vérifier si la base chargée couvre vraiment le processus à contrôler avant de commenter les indicateurs.",
            },
            {
                "label": "Lecture métier",
                "text": "Un même signal peut être mineur ou critique selon la procédure, le montant, la fréquence et le niveau d'autorisation.",
            },
            {
                "label": "Décision utile",
                "text": "Le meilleur constat est celui qui aide l'IMF à agir, pas seulement celui qui décrit l'écart.",
            },
        ]
    )

    render_summary_box(
        "Rôle de cet onglet",
        [
            "Cette page sert de guide pratique pour l'audit, le contrôle interne et la conformité.",
            "Elle aide à relier les analyses du tableau de bord aux procédures, aux preuves et aux suites à donner.",
            cycle_coverage["summary"],
        ],
    )

    render_summary_box(
        f"Référentiel du cycle : {cycle_spec['label']}",
        [
            cycle_spec["summary"],
            cycle_spec["control_objective"],
            "Le contrôleur doit toujours rapprocher les indicateurs de la procédure applicable et des justificatifs disponibles.",
        ],
    )

    _render_note_pair()

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

    if cycle_key == "epargne":
        ref_left, ref_right = st.columns((1.3, 1))
        with ref_left:
            render_panel_title("Référentiel des produits d'épargne")
            st.dataframe(build_savings_product_reference_table(), width="stretch", hide_index=True, height=280)
        with ref_right:
            render_panel_title("Exigences KYC à l'ouverture")
            st.dataframe(build_general_kyc_requirements_table(), width="stretch", hide_index=True, height=280)

        render_panel_title("Services et tarification de référence")
        st.dataframe(build_service_pricing_reference_table(), width="stretch", hide_index=True, height=250)
        render_summary_box(
            "Ce que l'application peut mieux contrôler",
            [
                "les comptes avec informations KYC incomplètes ou peu fiables",
                "les comptes DAT sous le minimum attendu quand le type de client et le solde sont disponibles",
                "les produits d'épargne attribués à un profil qui demande une confirmation",
                "les écarts de lecture sur les frais et services quand la base contient les colonnes de tarification",
            ],
        )
    elif cycle_key in {"credit", "likelemba"}:
        ref_left, ref_right = st.columns((1.15, 1))
        with ref_left:
            render_panel_title("Matrice d'octroi et de tarification")
            st.dataframe(build_credit_product_matrix_table(), width="stretch", hide_index=True, height=300)
        with ref_right:
            render_panel_title("Checklist dossier de crédit")
            st.dataframe(build_credit_file_checklist_table(), width="stretch", hide_index=True, height=300)

        render_panel_title("Exigences KYC générales")
        st.dataframe(build_general_kyc_requirements_table(), width="stretch", hide_index=True, height=250)
        render_summary_box(
            "Ce que l'application peut mieux contrôler",
            [
                "les montants, durées et taux hors référentiel quand le produit est reconnu",
                "les avances sur salaire supérieures au tiers du salaire net quand le revenu est disponible",
                "les dossiers sans garantie renseignée pour les produits qui l'exigent",
                "les écarts documentaires à confirmer ensuite avec les pièces du dossier",
            ],
        )
    elif cycle_key == "crm_clients":
        render_panel_title("Exigences KYC et identité client")
        st.dataframe(build_general_kyc_requirements_table(), width="stretch", hide_index=True, height=240)
        render_summary_box(
            "Lecture pour le suivi CRM",
            [
                "Une fiche CRM utile doit d'abord permettre d'identifier, joindre et suivre correctement le client.",
                "Les informations d'identité, de contact et de dernière activité restent prioritaires pour accélérer les corrections.",
            ],
        )

    govern_left, govern_right = st.columns((1, 1))
    with govern_left:
        render_panel_title("Niveaux de contrôle")
        st.dataframe(build_control_levels_table(), width="stretch", hide_index=True, height=240)
    with govern_right:
        render_panel_title("Principes directeurs")
        st.dataframe(build_control_principles_table(), width="stretch", hide_index=True, height=240)

    render_panel_title("Chaîne de reporting et d'escalade")
    st.dataframe(build_reporting_chain_table(), width="stretch", hide_index=True, height=230)

    render_panel_title("Comment lire les autres onglets")
    st.dataframe(_build_dashboard_reading_table(), width="stretch", hide_index=True, height=225)

    render_panel_title("Cartographie des risques")
    st.dataframe(build_risk_cartography_table(), width="stretch", hide_index=True, height=280)

    mission_left, mission_right = st.columns((1, 1))
    with mission_left:
        render_panel_title("Étapes d'une mission")
        st.dataframe(_build_mission_steps_table(), width="stretch", hide_index=True, height=230)
    with mission_right:
        render_panel_title("Preuves à rechercher")
        st.dataframe(_build_evidence_table(), width="stretch", hide_index=True, height=230)

    finding_left, finding_right = st.columns((1, 1))
    with finding_left:
        render_panel_title("Structure d'un bon constat")
        st.dataframe(_build_finding_structure_table(), width="stretch", hide_index=True, height=260)
    with finding_right:
        render_panel_title("Priorisation du suivi")
        st.dataframe(_build_follow_up_table(), width="stretch", hide_index=True, height=260)

    question_left, question_right = st.columns((1, 1))
    with question_left:
        render_panel_title("Questions à se poser avant de conclure")
        st.dataframe(_build_review_questions(), width="stretch", hide_index=True, height=245)
    with question_right:
        render_panel_title("Réflexes de rédaction")
        render_summary_box(
            "Pour un rapport plus solide",
            [
                "Nommer clairement le processus, la date et le périmètre revu.",
                "Séparer les faits observés des interprétations.",
                "Montrer le lien entre l'écart, le risque et la recommandation.",
                "Éviter les formules vagues quand un responsable ou un délai peut être précisé.",
            ],
        )
        render_summary_box(
            "Pour un suivi plus utile",
            [
                "Distinguer les corrections immédiates des actions structurelles.",
                "Documenter les preuves reçues après correction.",
                "Revenir sur les points récurrents à chaque mission suivante.",
            ],
        )

    render_summary_box(
        "Bonnes pratiques de lecture",
        [
            "Une alerte issue du dashboard doit être rapprochée d'une règle, d'une pièce et d'un responsable.",
            "Un écart sans impact majeur ne se traite pas comme une faiblesse systémique.",
            "Une base incomplète peut orienter la revue, mais ne doit pas produire une conclusion trop affirmée.",
            "Le suivi des recommandations vaut autant que le constat initial.",
        ],
    )


def render_analyste_credit_tab(cycle_key: str = "credit", standardized_df: pd.DataFrame | None = None) -> None:
    render_audit_control_tab(cycle_key, standardized_df)
