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


SAVINGS_PRODUCT_REFERENCE = [
    {
        "Produit": "Compte Épargne Standard",
        "Segment": "Particuliers / clientèle générale",
        "Seuil d'ouverture": "10 USD",
        "Solde minimum": "10 USD",
        "Rémunération": "2 % l'an",
        "Règle clé": "1 retrait gratuit par mois, puis 0,5 % à partir du 2e retrait.",
        "Lecture de contrôle": "Vérifier le seuil minimum, la fréquence des retraits et l'usage conforme du produit.",
    },
    {
        "Produit": "Dépôt à Terme (DAT)",
        "Segment": "Personne physique / morale",
        "Seuil d'ouverture": "500 USD / 5 000 USD",
        "Solde minimum": "500 USD",
        "Rémunération": "0 % à 8 % l'an",
        "Règle clé": "Retrait à l'échéance ; retrait anticipé = intérêts annulés.",
        "Lecture de contrôle": "Contrôler le minimum par segment, le taux servi et le respect du blocage contractuel.",
    },
    {
        "Produit": "Compte Courant Commercial",
        "Segment": "Personne physique / morale",
        "Seuil d'ouverture": "10 USD/EUR ou 100 USD/EUR",
        "Solde minimum": "Selon convention",
        "Rémunération": "Non rémunéré",
        "Règle clé": "Tenue de compte 2 USD/EUR ; retrait avec commission de 1 % ; préavis pour gros montants.",
        "Lecture de contrôle": "Vérifier les frais, les commissions et le respect du préavis au-delà du seuil.",
    },
    {
        "Produit": "Elubu ya ba Maman",
        "Segment": "Femmes entrepreneures",
        "Seuil d'ouverture": "Selon offre",
        "Solde minimum": "Selon offre",
        "Rémunération": "Selon convention",
        "Règle clé": "Produit orienté inclusion et sécurisation des recettes des femmes.",
        "Lecture de contrôle": "Confirmer la cohérence entre le profil client et le produit attribué.",
    },
    {
        "Produit": "Elenge ya Motuya",
        "Segment": "Jeunesse",
        "Seuil d'ouverture": "Selon offre",
        "Solde minimum": "Selon offre",
        "Rémunération": "Selon convention",
        "Règle clé": "Produit orienté épargne d'éducation et projets d'avenir.",
        "Lecture de contrôle": "Contrôler le ciblage du segment et la cohérence des informations client.",
    },
    {
        "Produit": "Likelemba structurée",
        "Segment": "Groupes / tontines",
        "Seuil d'ouverture": "Selon convention",
        "Solde minimum": "Selon cycle",
        "Rémunération": "Selon convention",
        "Règle clé": "Traçabilité des cotisations et accès au crédit selon l'assiduité du cycle.",
        "Lecture de contrôle": "Surveiller la traçabilité des membres, des cotisations et la discipline du groupe.",
    },
]


CREDIT_PRODUCT_MATRIX = [
    {
        "Produit": "Lisungi (AGR)",
        "Montant": "100 à 80 000 USD",
        "Durée": "2 à 12 mois",
        "Frais dossier": "2 %",
        "Frais décaissement": "0,5 %",
        "Taux": "2,5 % à 4 % / mois",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Garantie financière, parrainage, hypothèque ou gage",
    },
    {
        "Produit": "Crédit salaires",
        "Montant": "100 à 10 000 USD",
        "Durée": "2 à 24 mois",
        "Frais dossier": "2 %",
        "Frais décaissement": "0,5 %",
        "Taux": "2,5 % / mois",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Salaire, décompte final, parrainage et garantie financière",
    },
    {
        "Produit": "Crédit aux personnels",
        "Montant": "100 à 15 000 USD",
        "Durée": "2 à 24 mois",
        "Frais dossier": "0,5 %",
        "Frais décaissement": "0,5 %",
        "Taux": "2,5 % / mois",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Salaire, décompte final, parrainage et garantie financière",
    },
    {
        "Produit": "Avance sur salaire",
        "Montant": "1/3 du salaire net",
        "Durée": "1 mois",
        "Frais dossier": "0 %",
        "Frais décaissement": "0 %",
        "Taux": "5 % / mois",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Cession de salaire et décompte final",
    },
    {
        "Produit": "Crédit Dare Dare",
        "Montant": "100 à 10 000 USD",
        "Durée": "1 à 4 semaines",
        "Frais dossier": "0,25 %",
        "Frais décaissement": "0,5 %",
        "Taux": "2 % / semaine",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Garantie financière, parrainage, hypothèque ou gage",
    },
    {
        "Produit": "Crédit PEPSI",
        "Montant": "100 à 10 000 USD",
        "Durée": "1 à 4 semaines",
        "Frais dossier": "0,25 %",
        "Frais décaissement": "0,5 %",
        "Taux": "2 % / semaine",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Garantie financière, parrainage, hypothèque ou gage",
    },
    {
        "Produit": "Crédit auto",
        "Montant": "5 000 à 20 000 USD",
        "Durée": "12 à 24 mois",
        "Frais dossier": "0,5 %",
        "Frais décaissement": "0,5 %",
        "Taux": "2,5 % / mois",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Salaire, décompte final, parrainage et garantie financière",
    },
    {
        "Produit": "Crédit compte collectif",
        "Montant": "100 à 10 000 USD",
        "Durée": "2 à 12 mois",
        "Frais dossier": "2 %",
        "Frais décaissement": "0,5 %",
        "Taux": "2,5 % à 4 % / mois",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Compte collectif, caution solidaire, gage",
    },
    {
        "Produit": "Crédit LIKELEMBA",
        "Montant": "100 à 10 000 USD",
        "Durée": "Selon position",
        "Frais dossier": "1 %",
        "Frais décaissement": "0,5 %",
        "Taux": "2,5 % / mois",
        "Pénalité": "1 % / jour",
        "Garantie attendue": "Fonds collectif de blocage",
    },
]


SERVICE_PRICING_REFERENCE = [
    {
        "Service": "Carnet de chèque",
        "Tarif": "30 USD",
        "Condition": "Réservé aux comptes courants commerciaux.",
        "Lecture de contrôle": "Comparer les frais réellement prélevés au barème annoncé.",
    },
    {
        "Service": "Relevé certifié",
        "Tarif": "50 USD",
        "Condition": "Document officiel avec historique complet.",
        "Lecture de contrôle": "Vérifier l'application du bon tarif et la traçabilité de la demande.",
    },
    {
        "Service": "Relevé simple",
        "Tarif": "5 USD",
        "Condition": "Impression courante à la demande du client.",
        "Lecture de contrôle": "S'assurer de la cohérence entre service demandé et facturation.",
    },
    {
        "Service": "Carte VISA prépayée",
        "Tarif": "20 USD",
        "Condition": "Carte internationale prépayée.",
        "Lecture de contrôle": "Contrôler la bonne application du tarif d'émission.",
    },
    {
        "Service": "Ramassage de fonds",
        "Tarif": "À négocier",
        "Condition": "Convention selon volume, distance et fréquence.",
        "Lecture de contrôle": "Contrôler la présence d'une convention ou d'un accord tarifaire formel.",
    },
    {
        "Service": "Virement interne",
        "Tarif": "Inclus / selon barème",
        "Condition": "Transfert dans le réseau interne.",
        "Lecture de contrôle": "Confirmer le barème appliqué selon le type d'opération.",
    },
]


GENERAL_KYC_REQUIREMENTS = [
    {
        "Exigence": "Formulaire d'adhésion complet",
        "Applicabilité": "Tous les clients",
        "Lecture": "Vérifier la présence des informations de base et de la signature.",
    },
    {
        "Exigence": "Déclaration d'origine des fonds",
        "Applicabilité": "Tous les clients",
        "Lecture": "S'assurer que l'origine des fonds est documentée et exploitable.",
    },
    {
        "Exigence": "Pièce d'identité valide",
        "Applicabilité": "Tous les clients",
        "Lecture": "Contrôler la validité, la lisibilité et la concordance avec la fiche client.",
    },
    {
        "Exigence": "Deux photos d'identité",
        "Applicabilité": "Tous les clients",
        "Lecture": "Vérifier la présence des photos ou d'une capture faite en agence.",
    },
    {
        "Exigence": "Spécimen de signature",
        "Applicabilité": "Tous les clients",
        "Lecture": "S'assurer que la signature du client et des mandataires est enregistrée.",
    },
    {
        "Exigence": "Documents légaux",
        "Applicabilité": "Personnes morales",
        "Lecture": "Contrôler RCCM, ID Nat, statuts et autres pièces de création.",
    },
]


CREDIT_FILE_CHECKLIST = [
    {
        "Type de dossier": "Tous",
        "Pièce / preuve": "Contrat de crédit signé",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Aucun déblocage ne devrait intervenir sans contrat validé.",
    },
    {
        "Type de dossier": "Tous",
        "Pièce / preuve": "Pièce d'identité du client et du conjoint",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Base minimale de conformité et d'identification.",
    },
    {
        "Type de dossier": "Tous",
        "Pièce / preuve": "Analyse de la personnalité, des risques et de l'historique",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Doit justifier la décision et la maîtrise du risque.",
    },
    {
        "Type de dossier": "Groupe",
        "Pièce / preuve": "Contrat de caution solidaire",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Pièce clé pour les crédits solidaires et collectifs.",
    },
    {
        "Type de dossier": "Salarié / personnel",
        "Pièce / preuve": "Attestation de travail, fiches de paie, décompte final",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Permet de confirmer la source de remboursement et les garanties liées au salaire.",
    },
    {
        "Type de dossier": "Individuel / PME",
        "Pièce / preuve": "Factures, reçus de vente, justificatifs des actifs",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Sert à confirmer la réalité de l'activité et la cohérence du besoin.",
    },
    {
        "Type de dossier": "PME",
        "Pièce / preuve": "Hypothèque ou nantissement si exigé",
        "Niveau attendu": "Selon garantie",
        "Lecture": "La garantie réelle doit être traçable avant mise à disposition des fonds.",
    },
    {
        "Type de dossier": "Tous",
        "Pièce / preuve": "Photos du client, du garant et de l'activité",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Facilite la visite, la traçabilité et les revues ultérieures.",
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


def build_savings_product_reference_table() -> pd.DataFrame:
    return pd.DataFrame(SAVINGS_PRODUCT_REFERENCE)


def build_credit_product_matrix_table() -> pd.DataFrame:
    return pd.DataFrame(CREDIT_PRODUCT_MATRIX)


def build_service_pricing_reference_table() -> pd.DataFrame:
    return pd.DataFrame(SERVICE_PRICING_REFERENCE)


def build_general_kyc_requirements_table() -> pd.DataFrame:
    return pd.DataFrame(GENERAL_KYC_REQUIREMENTS)


def build_credit_file_checklist_table() -> pd.DataFrame:
    return pd.DataFrame(CREDIT_FILE_CHECKLIST)


SQL_OPERATIONS_CONTROL_CATALOG = [
    {
        "Contrôle ID": 49,
        "Thème": "Produits d'épargne",
        "Contrôle": "Produits d'épargne inactifs encore utilisés",
        "Lecture": "Repère les comptes encore rattachés à un produit inactif pour lancer une régularisation ou une migration.",
    },
    {
        "Contrôle ID": 50,
        "Thème": "Produits d'épargne",
        "Contrôle": "Produits d'épargne non valides encore utilisés",
        "Lecture": "Signale les comptes liés à un produit non valide afin de sécuriser le paramétrage du portefeuille.",
    },
    {
        "Contrôle ID": 51,
        "Thème": "Produits d'épargne",
        "Contrôle": "Produits sans dépôt ou retrait autorisé mais avec mouvements",
        "Lecture": "Compare les règles du produit aux mouvements réellement observés sur les comptes.",
    },
    {
        "Contrôle ID": 52,
        "Thème": "Produits d'épargne",
        "Contrôle": "Incohérences de devise produit, compte et mouvement",
        "Lecture": "Aide à repérer les écarts de devise qui peuvent fausser la lecture des opérations ou du produit.",
    },
    {
        "Contrôle ID": 53,
        "Thème": "Produits d'épargne",
        "Contrôle": "Comptes sans produit d'épargne exploitable",
        "Lecture": "Isole les comptes sans produit de référence ou avec produit introuvable ou invalide.",
    },
    {
        "Contrôle ID": 54,
        "Thème": "Mouvements HDPM",
        "Contrôle": "Mouvements sans compte ou sans opération rattachée",
        "Lecture": "Contrôle la présence des références minimales avant toute analyse détaillée.",
    },
    {
        "Contrôle ID": 55,
        "Thème": "Mouvements HDPM",
        "Contrôle": "Mouvements à montant nul, négatif ou très élevé",
        "Lecture": "Fait ressortir les écritures qui demandent une revue immédiate de cohérence ou de conformité.",
    },
    {
        "Contrôle ID": 56,
        "Thème": "Mouvements HDPM",
        "Contrôle": "Dépôts et retraits par client, compte, agence, devise et produit",
        "Lecture": "Donne une lecture consolidée des flux d'épargne sur la période.",
    },
    {
        "Contrôle ID": 57,
        "Thème": "Mouvements HDPM",
        "Contrôle": "Analyse des gros mouvements par période",
        "Lecture": "Suivi utile pour la vigilance LBC-FT, les pics d'activité et les volumes sensibles.",
    },
    {
        "Contrôle ID": 58,
        "Thème": "Mouvements HDPM",
        "Contrôle": "Analyse des mouvements par point de service",
        "Lecture": "Compare les points de service selon les volumes, les comptes touchés et les totaux débit/crédit.",
    },
    {
        "Contrôle ID": 59,
        "Thème": "Crédit",
        "Contrôle": "Demandes de crédit sans prêt accordé",
        "Lecture": "Suit les demandes reçues qui n'ont pas encore abouti à un prêt ou à une mise en place effective.",
    },
    {
        "Contrôle ID": 60,
        "Thème": "Crédit",
        "Contrôle": "Prêts incomplets",
        "Lecture": "Repère les prêts sans dossier, sans compte crédit, sans compte épargne ou sans cycle rattaché.",
    },
    {
        "Contrôle ID": 61,
        "Thème": "Crédit",
        "Contrôle": "Cycles de prêt échus non clôturés",
        "Lecture": "Met en évidence les cycles dépassés qui demandent un suivi de recouvrement ou une régularisation.",
    },
    {
        "Contrôle ID": 62,
        "Thème": "Crédit",
        "Contrôle": "Comparaison montant demandé et montant accordé",
        "Lecture": "Mesure les écarts entre la demande initiale, le dossier de crédit et le prêt finalement mis en place.",
    },
    {
        "Contrôle ID": 63,
        "Thème": "Crédit",
        "Contrôle": "Analyse des crédits par agence, produit, devise et état",
        "Lecture": "Offre une vue de pilotage du pipeline de crédit selon les axes les plus utiles pour la décision.",
    },
    {
        "Contrôle ID": 64,
        "Thème": "Risque et décision",
        "Contrôle": "Clients avec forte activité d'épargne et crédit actif",
        "Lecture": "Aide à cibler les profils très actifs qui méritent une lecture croisée épargne-crédit.",
    },
    {
        "Contrôle ID": 65,
        "Thème": "Risque et décision",
        "Contrôle": "Clients avec plusieurs demandes de crédit sur une même période",
        "Lecture": "Repère les clients qui multiplient les demandes et demandent une vigilance renforcée.",
    },
    {
        "Contrôle ID": 66,
        "Thème": "Risque et décision",
        "Contrôle": "Agences avec volume élevé de mouvements ou de crédits",
        "Lecture": "Compare la pression opérationnelle entre activité mouvement et activité crédit.",
    },
    {
        "Contrôle ID": 67,
        "Thème": "Risque et décision",
        "Contrôle": "Produits d'épargne les plus utilisés et produits crédit les plus sollicités",
        "Lecture": "Met en évidence les produits dominants pour le pilotage commercial et la supervision.",
    },
    {
        "Contrôle ID": 68,
        "Thème": "Risque et décision",
        "Contrôle": "Anomalies à prioriser pour audit",
        "Lecture": "Fournit une synthèse courte des signaux d'alerte à traiter en premier.",
    },
]


def build_sql_operations_control_catalog_table() -> pd.DataFrame:
    return pd.DataFrame(SQL_OPERATIONS_CONTROL_CATALOG)
