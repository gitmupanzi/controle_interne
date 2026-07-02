from __future__ import annotations

import pandas as pd


RISK_CARTOGRAPHY = [
    {
        "Famille de risque": "Risque de crédit",
        "Description": "Impayés chroniques, nouveaux produits sans étude de faisabilité, culture de non-remboursement, revenus instables, garanties faibles.",
        "Probabilité": "Élevée",
        "Impact": "Majeur",
        "Niveau brut": "Critique",
    },
    {
        "Famille de risque": "Risque de change",
        "Description": "Économie fortement dollarisée et asymétrie entre dépôts en devises et crédits locaux.",
        "Probabilité": "Élevée",
        "Impact": "Majeur",
        "Niveau brut": "Critique",
    },
    {
        "Famille de risque": "Risque opérationnel",
        "Description": "Fraude interne, manipulation d'espèces et défaillances des systèmes d'information.",
        "Probabilité": "Élevée",
        "Impact": "Modéré",
        "Niveau brut": "Élevé",
    },
    {
        "Famille de risque": "Risque d'infrastructure",
        "Description": "Coupures d'électricité et connectivité instable bloquant les synchronisations d'agence et des agents terrain.",
        "Probabilité": "Élevée",
        "Impact": "Modéré",
        "Niveau brut": "Élevé",
    },
    {
        "Famille de risque": "Risque sécuritaire",
        "Description": "Pillages, incidents publics et risques physiques lors des transports de fonds.",
        "Probabilité": "Moyenne",
        "Impact": "Modéré",
        "Niveau brut": "Élevé",
    },
    {
        "Famille de risque": "Risque de conformité et LCB-FT",
        "Description": "Sanctions liées au non-respect des ratios prudentiels et des obligations réglementaires.",
        "Probabilité": "Moyenne",
        "Impact": "Majeur",
        "Niveau brut": "Élevé",
    },
]


CONTROL_LEVELS = [
    {
        "Niveau": "Premier niveau",
        "Périmètre": "Chaque agent et son supérieur hiérarchique",
        "Lecture": "Surveillance permanente dans le traitement quotidien des opérations et respect des procédures.",
    },
    {
        "Niveau": "Deuxième niveau",
        "Périmètre": "Contrôle interne / contrôle permanent / conformité",
        "Lecture": "Contrôle périodique ou inopiné à posteriori pour vérifier l'efficacité des contrôles de premier niveau.",
    },
    {
        "Niveau": "Troisième niveau",
        "Périmètre": "Audit interne, audit externe et inspections BCC",
        "Lecture": "Évaluation indépendante de la cohérence du dispositif global de contrôle interne.",
    },
]


CONTROL_PRINCIPLES = [
    {"Principe": "Intégrité", "Lecture": "Refus des cadeaux, des conflits d'intérêts et des pratiques irrégulières."},
    {"Principe": "Objectivité", "Lecture": "Jugement fondé sur des faits vérifiables et non sur les pressions ou préférences personnelles."},
    {"Principe": "Confidentialité", "Lecture": "Secret professionnel absolu sauf obligation légale de signalement."},
    {"Principe": "Compétence", "Lecture": "Mise à niveau technique continue pour garder des analyses pertinentes."},
    {"Principe": "Séparation des tâches", "Lecture": "Éviter qu'un même agent décide, exécute, enregistre et contrôle la même opération."},
]


REPORTING_CHAIN = [
    {
        "Document / fréquence": "Fiches de contrôle quotidien / mensuel",
        "Destinataire / usage": "Suivi opérationnel courant et preuve standardisée des vérifications.",
    },
    {
        "Document / fréquence": "Registre des incidents opérationnels et fraudes",
        "Destinataire / usage": "Documentation des incidents, suivi des anomalies et escalade des cas graves.",
    },
    {
        "Document / fréquence": "Rapport mensuel",
        "Destinataire / usage": "Direction générale : risques identifiés, faiblesses constatées et taux d'application des recommandations.",
    },
    {
        "Document / fréquence": "Rapport trimestriel",
        "Destinataire / usage": "Comité d'audit et Conseil d'administration.",
    },
    {
        "Document / fréquence": "Rapport annuel",
        "Destinataire / usage": "Banque Centrale du Congo.",
    },
]


def build_risk_cartography_table() -> pd.DataFrame:
    return pd.DataFrame(RISK_CARTOGRAPHY)


def build_control_levels_table() -> pd.DataFrame:
    return pd.DataFrame(CONTROL_LEVELS)


def build_control_principles_table() -> pd.DataFrame:
    return pd.DataFrame(CONTROL_PRINCIPLES)


def build_reporting_chain_table() -> pd.DataFrame:
    return pd.DataFrame(REPORTING_CHAIN)
