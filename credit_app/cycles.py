from __future__ import annotations

from typing import Any

import pandas as pd

DEFAULT_CYCLE_KEY = "credit"

CYCLE_SPECS: dict[str, dict[str, Any]] = {
    "credit": {
        "label": "Cycle crédit",
        "summary": "Contrôle des procédures d'octroi, de déblocage, de suivi, de recouvrement et de gestion des impayés.",
        "control_objective": "Sécuriser la décision de crédit, limiter le risque de non-remboursement et protéger la qualité du portefeuille.",
        "controls": [
            {"Axe": "Octroi", "Point de contrôle": "Capacité de remboursement, cohérence du dossier, visites, garanties et séparation des tâches."},
            {"Axe": "Déblocage", "Point de contrôle": "Validation des conditions préalables avant décaissement et traçabilité des autorisations."},
            {"Axe": "Suivi", "Point de contrôle": "Monitoring des échéances, alertes de retard et documentation des actions de recouvrement."},
            {"Axe": "Impayés", "Point de contrôle": "Traitement des défauts, provisionnement et passation en pertes selon les règles applicables."},
        ],
        "expected_columns": [
            "client_id",
            "dossier_id",
            "agence",
            "agent_credit",
            "type_produit",
            "date_demande",
            "date_decision",
            "montant_demande",
            "montant_accorde",
            "revenu_mensuel",
            "charge_mensuelle",
            "score_credit",
            "statut_dossier",
            "statut_remboursement",
            "retard_jours",
            "activite_economique",
            "garantie",
            "commentaire",
        ],
    },
    "epargne": {
        "label": "Cycle épargne",
        "summary": "Contrôle de l'ouverture de compte, de la conformité KYC, des dépôts, retraits, comptes sensibles et réconciliations.",
        "control_objective": "Sécuriser les dépôts, fiabiliser les mouvements clients et limiter les opérations irrégulières.",
        "controls": [
            {"Axe": "Ouverture de compte", "Point de contrôle": "Conformité documentaire, identification client et validation des habilitations."},
            {"Axe": "Opérations", "Point de contrôle": "Contrôle des dépôts, retraits, plafonds et justificatifs."},
            {"Axe": "Comptes sensibles", "Point de contrôle": "Revue des comptes dormants, bloqués ou à risque."},
            {"Axe": "Réconciliation", "Point de contrôle": "Rapprochement comptable et justification des écarts."},
        ],
        "expected_columns": [
            "compte_id",
            "client_id",
            "type_produit",
            "type_client",
            "date_operation",
            "solde_compte",
            "agent_credit",
            "telephone",
            "sexe",
            "zone_geographique",
            "statut_compte",
            "agence",
            "type_operation",
            "montant_operation",
        ],
    },
    "caisse": {
        "label": "Cycle caisse et guichet",
        "summary": "Contrôle des ouvertures et fermetures de caisse, limites d'encaisse, arrêtés quotidiens et écarts.",
        "control_objective": "Sécuriser les espèces et détecter rapidement les écarts ou anomalies de caisse.",
        "controls": [
            {"Axe": "Ouverture / fermeture", "Point de contrôle": "Journal de caisse, habilitations et signature des responsables."},
            {"Axe": "Encaisse", "Point de contrôle": "Respect des limites par caissier et par agence."},
            {"Axe": "Arrêté quotidien", "Point de contrôle": "Contrôle des écarts manquants / excédents et justificatifs."},
            {"Axe": "Transport de fonds", "Point de contrôle": "Approvisionnement, délestage et sécurité du circuit de fonds."},
        ],
        "expected_columns": ["agence", "caissier", "date_operation", "type_operation", "montant_operation", "encaisse_fin_jour", "ecart_caisse"],
    },
    "tresorerie": {
        "label": "Cycle trésorerie et banque",
        "summary": "Contrôle des rapprochements bancaires, signatures autorisées et suivi du risque de change.",
        "control_objective": "Sécuriser la liquidité, les relations bancaires et la position de change de l'institution.",
        "controls": [
            {"Axe": "Rapprochement", "Point de contrôle": "Rapprochements périodiques, validation hiérarchique et suivi des suspens."},
            {"Axe": "Signatures", "Point de contrôle": "Mise à jour des signataires et contrôle des autorisations."},
            {"Axe": "Change", "Point de contrôle": "Suivi des positions CDF/USD et des écarts de conversion."},
        ],
        "expected_columns": ["compte_bancaire", "banque", "date_operation", "montant_operation", "devise", "solde_banque", "ecart_rapprochement"],
    },
    "comptable": {
        "label": "Cycle comptable et financier",
        "summary": "Contrôle de la séparation des tâches, des clôtures et de la production des états financiers.",
        "control_objective": "Fiabiliser l'information comptable et financière et réduire les erreurs de traitement.",
        "controls": [
            {"Axe": "Séparation des tâches", "Point de contrôle": "Différenciation ordonnateur / comptable et contrôle des validations."},
            {"Axe": "Clôture", "Point de contrôle": "Procédures mensuelles et annuelles, pièces justificatives et revues."},
            {"Axe": "États financiers", "Point de contrôle": "Production, cohérence et transmission des états réglementaires."},
        ],
        "expected_columns": ["piece_id", "journal", "compte_comptable", "date_operation", "montant_debit", "montant_credit", "centre_cout"],
    },
    "rh_admin": {
        "label": "Cycle ressources humaines et administration",
        "summary": "Contrôle du recrutement, de l'intégration, de la paie, des accès physiques et des immobilisations.",
        "control_objective": "Sécuriser les accès, la gestion du personnel et le patrimoine administratif.",
        "controls": [
            {"Axe": "Recrutement / paie", "Point de contrôle": "Validation des dossiers RH, paie et mouvements du personnel."},
            {"Axe": "Accès physiques", "Point de contrôle": "Gestion des clés, coffres, badges et autorisations."},
            {"Axe": "Immobilisations", "Point de contrôle": "Inventaire physique et suivi des actifs."},
        ],
        "expected_columns": ["agent_id", "agence", "fonction", "date_entree", "statut_agent", "salaire", "immobilisation_id"],
    },
    "si": {
        "label": "Sécurité du système d'information",
        "summary": "Contrôle des accès, profils, mots de passe et révocation des droits.",
        "control_objective": "Réduire les accès non autorisés et protéger la confidentialité des données.",
        "controls": [
            {"Axe": "Profils", "Point de contrôle": "Affectation des droits selon le besoin d'en savoir."},
            {"Axe": "Mots de passe", "Point de contrôle": "Respect de la politique de mots de passe et traçabilité."},
            {"Axe": "Sorties d'agents", "Point de contrôle": "Révocation immédiate des accès après départ."},
        ],
        "expected_columns": ["agent_id", "profil_acces", "date_activation", "date_revocation", "application_source", "niveau_habilitation"],
    },
    "continuite": {
        "label": "Sauvegarde et continuité d'activité",
        "summary": "Contrôle des sauvegardes quotidiennes et du plan de reprise après sinistre.",
        "control_objective": "Assurer la continuité d'activité et la récupération des données en cas d'incident majeur.",
        "controls": [
            {"Axe": "Sauvegarde", "Point de contrôle": "Exécution, fréquence, support et preuve des sauvegardes."},
            {"Axe": "Reprise", "Point de contrôle": "Plan de reprise, tests et responsabilités documentées."},
            {"Axe": "Incident majeur", "Point de contrôle": "Journalisation des coupures, sinistres et actions correctives."},
        ],
        "expected_columns": ["date_sauvegarde", "type_sauvegarde", "support_sauvegarde", "statut_test_reprise", "incident_majeur"],
    },
    "likelemba": {
        "label": "Likelemba solidaire",
        "summary": "Produit de crédit rotatif et solidaire fondé sur la caution mutuelle, la discipline de groupe et une épargne de garantie.",
        "control_objective": "Sécuriser les cycles collectifs, éviter la fragilité d'un membre et maîtriser les impayés par la pression sociale et le contrôle terrain.",
        "controls": [
            {"Axe": "Éligibilité du groupe", "Point de contrôle": "Groupe de 5 à 10 membres, même zone géographique, activité génératrice de revenus stable, pas d'impayés ailleurs."},
            {"Axe": "Garantie", "Point de contrôle": "Épargne de garantie bloquée à hauteur de 20 % du montant sollicité avant tout déblocage."},
            {"Axe": "Analyse individuelle", "Point de contrôle": "Validation de la capacité de remboursement de chaque membre et vérification de l'activité sur le terrain."},
            {"Axe": "Gestion des impayés", "Point de contrôle": "Escalade J+1, J+3 et J+7, suspension du groupe et saisie de la garantie en dernier recours."},
            {"Axe": "Cycle progressif", "Point de contrôle": "Montée en plafond uniquement si le cycle précédent est clôturé sans impayé."},
        ],
        "expected_columns": [
            "client_id",
            "dossier_id",
            "nom_groupe",
            "montant_demande",
            "montant_accorde",
            "revenu_mensuel",
            "charge_mensuelle",
            "retard_jours",
            "garantie",
            "activite_economique",
            "date_demande",
            "statut_dossier",
            "statut_remboursement",
            "commentaire",
        ],
    },
    "money_provider": {
        "label": "Money Provider",
        "summary": "Contrôle des opérations de monnaie électronique : dépôt, retrait, transfert, cash-in, cash-out et réconciliation journalière.",
        "control_objective": "Sécuriser l'e-money, tracer les opérations, prévenir la fraude et garantir la concordance entre plateforme, journal et pièces de caisse.",
        "controls": [
            {"Axe": "Transactions", "Point de contrôle": "Dépôt, retrait, transfert, cash-in et cash-out enregistrés avec référence, agent et identité du client."},
            {"Axe": "Double vérification", "Point de contrôle": "Concordance entre demande, journal, reçu, bordereau client et validation opérateur / trésorier."},
            {"Axe": "Réconciliation", "Point de contrôle": "Solde initial = clôture J-1, puis rapprochement du solde final plateforme avec le journal."},
            {"Axe": "Conformité", "Point de contrôle": "Respect des limites de retrait, confidentialité, contrôle d'identité et normes réglementaires."},
            {"Axe": "Archivage", "Point de contrôle": "Transmission des pièces à la comptabilité puis au contrôle interne pour revue finale."},
        ],
        "expected_columns": [
            "date_operation",
            "type_operation",
            "montant_operation",
            "numero_reference",
            "telephone",
            "client_id",
            "agence",
            "operateur",
            "tresorier",
            "journal_transaction",
            "solde_initial",
            "solde_final",
            "commentaire",
        ],
    },
}

DEFAULT_ANALYSIS_PRESET: dict[str, Any] = {
    "record_label": "Lignes",
    "id_columns": ["dossier_id", "client_id"],
    "group_columns": ["agence", "type_produit", "agent_credit"],
    "status_columns": ["statut_dossier", "statut_remboursement"],
    "amount_columns": ["montant_demande", "montant_accorde"],
    "actor_columns": ["agent_credit"],
    "filter_columns": ["statut_dossier", "agence", "type_produit", "agent_credit"],
}

CYCLE_ANALYSIS_PRESETS: dict[str, dict[str, Any]] = {
    "credit": {
        "record_label": "Dossiers",
        "id_columns": ["dossier_id", "client_id"],
        "group_columns": ["agence", "type_produit", "agent_credit"],
        "status_columns": ["statut_dossier", "statut_remboursement"],
        "amount_columns": ["montant_demande", "montant_accorde"],
        "actor_columns": ["agent_credit"],
        "filter_columns": ["statut_dossier", "statut_remboursement", "agence", "type_produit", "agent_credit"],
    },
    "likelemba": {
        "record_label": "Dossiers solidaires",
        "id_columns": ["dossier_id", "client_id", "nom_groupe"],
        "group_columns": ["nom_groupe", "agence", "activite_economique"],
        "status_columns": ["statut_dossier", "statut_remboursement"],
        "amount_columns": ["montant_demande", "montant_accorde"],
        "actor_columns": ["agent_credit"],
        "filter_columns": ["statut_dossier", "statut_remboursement", "nom_groupe", "agence", "activite_economique"],
    },
    "epargne": {
        "record_label": "Comptes d'épargne",
        "id_columns": ["compte_id", "client_id"],
        "group_columns": ["type_produit", "type_client", "agent_credit", "zone_geographique"],
        "status_columns": ["statut_compte", "type_client", "type_produit"],
        "amount_columns": ["solde_compte", "montant_operation"],
        "actor_columns": ["agent_credit"],
        "filter_columns": ["type_produit", "type_client", "agent_credit", "zone_geographique", "sexe", "compte_id"],
    },
    "caisse": {
        "record_label": "Mouvements de caisse",
        "id_columns": ["agence", "caissier"],
        "group_columns": ["agence", "caissier", "type_operation"],
        "status_columns": ["type_operation"],
        "amount_columns": ["montant_operation", "encaisse_fin_jour"],
        "actor_columns": ["caissier"],
        "filter_columns": ["agence", "caissier", "type_operation"],
    },
    "tresorerie": {
        "record_label": "Mouvements de trésorerie",
        "id_columns": ["compte_bancaire", "banque"],
        "group_columns": ["banque", "compte_bancaire", "devise"],
        "status_columns": ["devise"],
        "amount_columns": ["montant_operation", "solde_banque"],
        "actor_columns": [],
        "filter_columns": ["banque", "compte_bancaire", "devise"],
    },
    "comptable": {
        "record_label": "Écritures comptables",
        "id_columns": ["piece_id"],
        "group_columns": ["journal", "compte_comptable", "centre_cout"],
        "status_columns": ["journal"],
        "amount_columns": ["montant_debit", "montant_credit"],
        "actor_columns": [],
        "filter_columns": ["journal", "compte_comptable", "centre_cout"],
    },
    "rh_admin": {
        "record_label": "Enregistrements RH",
        "id_columns": ["agent_id", "immobilisation_id"],
        "group_columns": ["agence", "fonction", "statut_agent"],
        "status_columns": ["statut_agent"],
        "amount_columns": ["salaire"],
        "actor_columns": [],
        "filter_columns": ["agence", "fonction", "statut_agent"],
    },
    "si": {
        "record_label": "Habilitations SI",
        "id_columns": ["agent_id"],
        "group_columns": ["application_source", "profil_acces", "niveau_habilitation"],
        "status_columns": ["profil_acces", "niveau_habilitation"],
        "amount_columns": [],
        "actor_columns": [],
        "filter_columns": ["application_source", "profil_acces", "niveau_habilitation"],
    },
    "continuite": {
        "record_label": "Sauvegardes et tests",
        "id_columns": ["date_sauvegarde"],
        "group_columns": ["type_sauvegarde", "support_sauvegarde", "statut_test_reprise"],
        "status_columns": ["statut_test_reprise", "incident_majeur"],
        "amount_columns": [],
        "actor_columns": [],
        "filter_columns": ["type_sauvegarde", "support_sauvegarde", "statut_test_reprise"],
    },
    "money_provider": {
        "record_label": "Transactions",
        "id_columns": ["numero_reference", "client_id"],
        "group_columns": ["agence", "type_operation", "operateur", "tresorier"],
        "status_columns": ["type_operation"],
        "amount_columns": ["montant_operation", "solde_final"],
        "actor_columns": ["operateur", "tresorier"],
        "filter_columns": ["agence", "type_operation", "operateur", "tresorier"],
    },
}


def list_cycle_keys() -> list[str]:
    return list(CYCLE_SPECS.keys())


def get_cycle_spec(cycle_key: str | None) -> dict[str, Any]:
    if cycle_key and cycle_key in CYCLE_SPECS:
        return CYCLE_SPECS[cycle_key]
    return CYCLE_SPECS[DEFAULT_CYCLE_KEY]


def get_cycle_analysis_preset(cycle_key: str | None) -> dict[str, Any]:
    preset = dict(DEFAULT_ANALYSIS_PRESET)
    preset.update(CYCLE_ANALYSIS_PRESETS.get(cycle_key or DEFAULT_CYCLE_KEY, {}))
    return preset


def build_cycle_control_table(cycle_key: str) -> pd.DataFrame:
    spec = get_cycle_spec(cycle_key)
    return pd.DataFrame(spec.get("controls", []))


def build_cycle_expected_fields_table(
    cycle_key: str,
    available_columns: list[str] | set[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    spec = get_cycle_spec(cycle_key)
    available = {str(column) for column in (available_columns or [])}
    rows = []
    for field_name in spec.get("expected_columns", []):
        rows.append(
            {
                "Champ attendu": field_name,
                "Détecté": "Oui" if field_name in available else "Non",
            }
        )
    return pd.DataFrame(rows)


def build_cycle_coverage_summary(df: pd.DataFrame | None, cycle_key: str) -> dict[str, Any]:
    spec = get_cycle_spec(cycle_key)
    expected_fields = list(spec.get("expected_columns", []))
    available_columns = set(df.columns) if df is not None else set()
    detected_fields = [field for field in expected_fields if field in available_columns]
    missing_fields = [field for field in expected_fields if field not in available_columns]
    total = len(expected_fields)
    detected_count = len(detected_fields)
    coverage_rate = (detected_count / total) if total else 0.0
    summary = (
        f"{detected_count}/{total} champ(s) clés détecté(s) pour {spec['label']}."
        if total
        else f"Aucun champ clé n'est configuré pour {spec['label']}."
    )
    return {
        "detected_count": detected_count,
        "total": total,
        "coverage_rate": coverage_rate,
        "detected_fields": detected_fields,
        "missing_fields": missing_fields,
        "summary": summary,
    }
