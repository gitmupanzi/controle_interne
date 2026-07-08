from __future__ import annotations

import pandas as pd


RISK_CARTOGRAPHY = [
    {
        "Famille de risque": "Risque de crÃ©dit",
        "Description": "ImpayÃ©s chroniques, nouveaux produits sans Ã©tude de faisabilitÃ©, culture de non-remboursement, revenus instables, garanties faibles.",
        "ProbabilitÃ©": "Ã‰levÃ©e",
        "Impact": "Majeur",
        "Niveau brut": "Critique",
    },
    {
        "Famille de risque": "Risque de change",
        "Description": "Ã‰conomie fortement dollarisÃ©e et asymÃ©trie entre dÃ©pÃ´ts en devises et crÃ©dits locaux.",
        "ProbabilitÃ©": "Ã‰levÃ©e",
        "Impact": "Majeur",
        "Niveau brut": "Critique",
    },
    {
        "Famille de risque": "Risque opÃ©rationnel",
        "Description": "Fraude interne, manipulation d'espÃ¨ces et dÃ©faillances des systÃ¨mes d'information.",
        "ProbabilitÃ©": "Ã‰levÃ©e",
        "Impact": "ModÃ©rÃ©",
        "Niveau brut": "Ã‰levÃ©",
    },
    {
        "Famille de risque": "Risque d'infrastructure",
        "Description": "Coupures d'Ã©lectricitÃ© et connectivitÃ© instable bloquant les synchronisations d'agence et des agents terrain.",
        "ProbabilitÃ©": "Ã‰levÃ©e",
        "Impact": "ModÃ©rÃ©",
        "Niveau brut": "Ã‰levÃ©",
    },
    {
        "Famille de risque": "Risque sÃ©curitaire",
        "Description": "Pillages, incidents publics et risques physiques lors des transports de fonds.",
        "ProbabilitÃ©": "Moyenne",
        "Impact": "ModÃ©rÃ©",
        "Niveau brut": "Ã‰levÃ©",
    },
    {
        "Famille de risque": "Risque de conformitÃ© et LCB-FT",
        "Description": "Sanctions liÃ©es au non-respect des ratios prudentiels et des obligations rÃ©glementaires.",
        "ProbabilitÃ©": "Moyenne",
        "Impact": "Majeur",
        "Niveau brut": "Ã‰levÃ©",
    }
]


CONTROL_LEVELS = [
    {
        "Niveau": "Premier niveau",
        "PÃ©rimÃ¨tre": "Chaque agent et son supÃ©rieur hiÃ©rarchique",
        "Lecture": "Surveillance permanente dans le traitement quotidien des opÃ©rations et respect des procÃ©dures.",
    },
    {
        "Niveau": "DeuxiÃ¨me niveau",
        "PÃ©rimÃ¨tre": "ContrÃ´le interne / contrÃ´le permanent / conformitÃ©",
        "Lecture": "ContrÃ´le pÃ©riodique ou inopinÃ© Ã  posteriori pour vÃ©rifier l'efficacitÃ© des contrÃ´les de premier niveau.",
    },
    {
        "Niveau": "TroisiÃ¨me niveau",
        "PÃ©rimÃ¨tre": "Audit interne, audit externe et inspections BCC",
        "Lecture": "Ã‰valuation indÃ©pendante de la cohÃ©rence du dispositif global de contrÃ´le interne.",
    },
]


CONTROL_PRINCIPLES = [
    {"Principe": "IntÃ©gritÃ©", "Lecture": "Refus des cadeaux, des conflits d'intÃ©rÃªts et des pratiques irrÃ©guliÃ¨res."},
    {"Principe": "ObjectivitÃ©", "Lecture": "Jugement fondÃ© sur des faits vÃ©rifiables et non sur les pressions ou prÃ©fÃ©rences personnelles."},
    {"Principe": "ConfidentialitÃ©", "Lecture": "Secret professionnel absolu sauf obligation lÃ©gale de signalement."},
    {"Principe": "CompÃ©tence", "Lecture": "Mise Ã  niveau technique continue pour garder des analyses pertinentes."},
    {"Principe": "SÃ©paration des tÃ¢ches", "Lecture": "Ã‰viter qu'un mÃªme agent dÃ©cide, exÃ©cute, enregistre et contrÃ´le la mÃªme opÃ©ration."},
]


REPORTING_CHAIN = [
    {
        "Document / frÃ©quence": "Fiches de contrÃ´le quotidien / mensuel",
        "Destinataire / usage": "Suivi opÃ©rationnel courant et preuve standardisÃ©e des vÃ©rifications.",
    },
    {
        "Document / frÃ©quence": "Registre des incidents opÃ©rationnels et fraudes",
        "Destinataire / usage": "Documentation des incidents, suivi des anomalies et escalade des cas graves.",
    },
    {
        "Document / frÃ©quence": "Rapport mensuel",
        "Destinataire / usage": "Direction gÃ©nÃ©rale : risques identifiÃ©s, faiblesses constatÃ©es et taux d'application des recommandations.",
    },
    {
        "Document / frÃ©quence": "Rapport trimestriel",
        "Destinataire / usage": "ComitÃ© d'audit et Conseil d'administration.",
    },
    {
        "Document / frÃ©quence": "Rapport annuel",
        "Destinataire / usage": "Banque Centrale du Congo.",
    },
]


SAVINGS_PRODUCT_REFERENCE = [
    {
        "Produit": "Compte Ã‰pargne Standard",
        "Segment": "Particuliers / clientÃ¨le gÃ©nÃ©rale",
        "Seuil d'ouverture": "10 USD",
        "Solde minimum": "10 USD",
        "RÃ©munÃ©ration": "2 % l'an",
        "RÃ¨gle clÃ©": "1 retrait gratuit par mois, puis 0,5 % Ã  partir du 2e retrait.",
        "Lecture de contrÃ´le": "VÃ©rifier le seuil minimum, la frÃ©quence des retraits et l'usage conforme du produit.",
    },
    {
        "Produit": "DÃ©pÃ´t Ã  Terme (DAT)",
        "Segment": "Personne physique / morale",
        "Seuil d'ouverture": "500 USD / 5 000 USD",
        "Solde minimum": "500 USD",
        "RÃ©munÃ©ration": "0 % Ã  8 % l'an",
        "RÃ¨gle clÃ©": "Retrait Ã  l'Ã©chÃ©ance ; retrait anticipÃ© = intÃ©rÃªts annulÃ©s.",
        "Lecture de contrÃ´le": "ContrÃ´ler le minimum par segment, le taux servi et le respect du blocage contractuel.",
    },
    {
        "Produit": "Compte Courant Commercial",
        "Segment": "Personne physique / morale",
        "Seuil d'ouverture": "10 USD/EUR ou 100 USD/EUR",
        "Solde minimum": "Selon convention",
        "RÃ©munÃ©ration": "Non rÃ©munÃ©rÃ©",
        "RÃ¨gle clÃ©": "Tenue de compte 2 USD/EUR ; retrait avec commission de 1 % ; prÃ©avis pour gros montants.",
        "Lecture de contrÃ´le": "VÃ©rifier les frais, les commissions et le respect du prÃ©avis au-delÃ  du seuil.",
    },
    {
        "Produit": "Elubu ya ba Maman",
        "Segment": "Femmes entrepreneures",
        "Seuil d'ouverture": "Selon offre",
        "Solde minimum": "Selon offre",
        "RÃ©munÃ©ration": "Selon convention",
        "RÃ¨gle clÃ©": "Produit orientÃ© inclusion et sÃ©curisation des recettes des femmes.",
        "Lecture de contrÃ´le": "Confirmer la cohÃ©rence entre le profil client et le produit attribuÃ©.",
    },
    {
        "Produit": "Elenge ya Motuya",
        "Segment": "Jeunesse",
        "Seuil d'ouverture": "Selon offre",
        "Solde minimum": "Selon offre",
        "RÃ©munÃ©ration": "Selon convention",
        "RÃ¨gle clÃ©": "Produit orientÃ© Ã©pargne d'Ã©ducation et projets d'avenir.",
        "Lecture de contrÃ´le": "ContrÃ´ler le ciblage du segment et la cohÃ©rence des informations client.",
    },
    {
        "Produit": "Likelemba structurÃ©e",
        "Segment": "Groupes / tontines",
        "Seuil d'ouverture": "Selon convention",
        "Solde minimum": "Selon cycle",
        "RÃ©munÃ©ration": "Selon convention",
        "RÃ¨gle clÃ©": "TraÃ§abilitÃ© des cotisations et accÃ¨s au crÃ©dit selon l'assiduitÃ© du cycle.",
        "Lecture de contrÃ´le": "Surveiller la traÃ§abilitÃ© des membres, des cotisations et la discipline du groupe.",
    },
]


CREDIT_PRODUCT_MATRIX = [
    {
        "Produit": "Lisungi (AGR)",
        "Montant": "100 Ã  80 000 USD",
        "DurÃ©e": "2 Ã  12 mois",
        "Frais dossier": "2 %",
        "Frais dÃ©caissement": "0,5 %",
        "Taux": "2,5 % Ã  4 % / mois",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Garantie financiÃ¨re, parrainage, hypothÃ¨que ou gage",
    },
    {
        "Produit": "CrÃ©dit salaires",
        "Montant": "100 Ã  10 000 USD",
        "DurÃ©e": "2 Ã  24 mois",
        "Frais dossier": "2 %",
        "Frais dÃ©caissement": "0,5 %",
        "Taux": "2,5 % / mois",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Salaire, dÃ©compte final, parrainage et garantie financiÃ¨re",
    },
    {
        "Produit": "CrÃ©dit aux personnels",
        "Montant": "100 Ã  15 000 USD",
        "DurÃ©e": "2 Ã  24 mois",
        "Frais dossier": "0,5 %",
        "Frais dÃ©caissement": "0,5 %",
        "Taux": "2,5 % / mois",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Salaire, dÃ©compte final, parrainage et garantie financiÃ¨re",
    },
    {
        "Produit": "Avance sur salaire",
        "Montant": "1/3 du salaire net",
        "DurÃ©e": "1 mois",
        "Frais dossier": "0 %",
        "Frais dÃ©caissement": "0 %",
        "Taux": "5 % / mois",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Cession de salaire et dÃ©compte final",
    },
    {
        "Produit": "CrÃ©dit Dare Dare",
        "Montant": "100 Ã  10 000 USD",
        "DurÃ©e": "1 Ã  4 semaines",
        "Frais dossier": "0,25 %",
        "Frais dÃ©caissement": "0,5 %",
        "Taux": "2 % / semaine",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Garantie financiÃ¨re, parrainage, hypothÃ¨que ou gage",
    },
    {
        "Produit": "CrÃ©dit PEPSI",
        "Montant": "100 Ã  10 000 USD",
        "DurÃ©e": "1 Ã  4 semaines",
        "Frais dossier": "0,25 %",
        "Frais dÃ©caissement": "0,5 %",
        "Taux": "2 % / semaine",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Garantie financiÃ¨re, parrainage, hypothÃ¨que ou gage",
    },
    {
        "Produit": "CrÃ©dit auto",
        "Montant": "5 000 Ã  20 000 USD",
        "DurÃ©e": "12 Ã  24 mois",
        "Frais dossier": "0,5 %",
        "Frais dÃ©caissement": "0,5 %",
        "Taux": "2,5 % / mois",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Salaire, dÃ©compte final, parrainage et garantie financiÃ¨re",
    },
    {
        "Produit": "CrÃ©dit compte collectif",
        "Montant": "100 Ã  10 000 USD",
        "DurÃ©e": "2 Ã  12 mois",
        "Frais dossier": "2 %",
        "Frais dÃ©caissement": "0,5 %",
        "Taux": "2,5 % Ã  4 % / mois",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Compte collectif, caution solidaire, gage",
    },
    {
        "Produit": "CrÃ©dit LIKELEMBA",
        "Montant": "100 Ã  10 000 USD",
        "DurÃ©e": "Selon position",
        "Frais dossier": "1 %",
        "Frais dÃ©caissement": "0,5 %",
        "Taux": "2,5 % / mois",
        "PÃ©nalitÃ©": "1 % / jour",
        "Garantie attendue": "Fonds collectif de blocage",
    },
]


SERVICE_PRICING_REFERENCE = [
    {
        "Service": "Carnet de chÃ¨que",
        "Tarif": "30 USD",
        "Condition": "RÃ©servÃ© aux comptes courants commerciaux.",
        "Lecture de contrÃ´le": "Comparer les frais rÃ©ellement prÃ©levÃ©s au barÃ¨me annoncÃ©.",
    },
    {
        "Service": "RelevÃ© certifiÃ©",
        "Tarif": "50 USD",
        "Condition": "Document officiel avec historique complet.",
        "Lecture de contrÃ´le": "VÃ©rifier l'application du bon tarif et la traÃ§abilitÃ© de la demande.",
    },
    {
        "Service": "RelevÃ© simple",
        "Tarif": "5 USD",
        "Condition": "Impression courante Ã  la demande du client.",
        "Lecture de contrÃ´le": "S'assurer de la cohÃ©rence entre service demandÃ© et facturation.",
    },
    {
        "Service": "Carte VISA prÃ©payÃ©e",
        "Tarif": "20 USD",
        "Condition": "Carte internationale prÃ©payÃ©e.",
        "Lecture de contrÃ´le": "ContrÃ´ler la bonne application du tarif d'Ã©mission.",
    },
    {
        "Service": "Ramassage de fonds",
        "Tarif": "Ã€ nÃ©gocier",
        "Condition": "Convention selon volume, distance et frÃ©quence.",
        "Lecture de contrÃ´le": "ContrÃ´ler la prÃ©sence d'une convention ou d'un accord tarifaire formel.",
    },
    {
        "Service": "Virement interne",
        "Tarif": "Inclus / selon barÃ¨me",
        "Condition": "Transfert dans le rÃ©seau interne.",
        "Lecture de contrÃ´le": "Confirmer le barÃ¨me appliquÃ© selon le type d'opÃ©ration.",
    },
]


GENERAL_KYC_REQUIREMENTS = [
    {
        "Exigence": "Formulaire d'adhÃ©sion complet",
        "ApplicabilitÃ©": "Tous les clients",
        "Lecture": "VÃ©rifier la prÃ©sence des informations de base et de la signature.",
    },
    {
        "Exigence": "DÃ©claration d'origine des fonds",
        "ApplicabilitÃ©": "Tous les clients",
        "Lecture": "S'assurer que l'origine des fonds est documentÃ©e et exploitable.",
    },
    {
        "Exigence": "PiÃ¨ce d'identitÃ© valide",
        "ApplicabilitÃ©": "Tous les clients",
        "Lecture": "ContrÃ´ler la validitÃ©, la lisibilitÃ© et la concordance avec la fiche client.",
    },
    {
        "Exigence": "Deux photos d'identitÃ©",
        "ApplicabilitÃ©": "Tous les clients",
        "Lecture": "VÃ©rifier la prÃ©sence des photos ou d'une capture faite en agence.",
    },
    {
        "Exigence": "SpÃ©cimen de signature",
        "ApplicabilitÃ©": "Tous les clients",
        "Lecture": "S'assurer que la signature du client et des mandataires est enregistrÃ©e.",
    },
    {
        "Exigence": "Documents lÃ©gaux",
        "ApplicabilitÃ©": "Personnes morales",
        "Lecture": "ContrÃ´ler RCCM, ID Nat, statuts et autres piÃ¨ces de crÃ©ation.",
    },
]


CREDIT_FILE_CHECKLIST = [
    {
        "Type de dossier": "Tous",
        "PiÃ¨ce / preuve": "Contrat de crÃ©dit signÃ©",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Aucun dÃ©blocage ne devrait intervenir sans contrat validÃ©.",
    },
    {
        "Type de dossier": "Tous",
        "PiÃ¨ce / preuve": "PiÃ¨ce d'identitÃ© du client et du conjoint",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Base minimale de conformitÃ© et d'identification.",
    },
    {
        "Type de dossier": "Tous",
        "PiÃ¨ce / preuve": "Analyse de la personnalitÃ©, des risques et de l'historique",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Doit justifier la dÃ©cision et la maÃ®trise du risque.",
    },
    {
        "Type de dossier": "Groupe",
        "PiÃ¨ce / preuve": "Contrat de caution solidaire",
        "Niveau attendu": "Obligatoire",
        "Lecture": "PiÃ¨ce clÃ© pour les crÃ©dits solidaires et collectifs.",
    },
    {
        "Type de dossier": "SalariÃ© / personnel",
        "PiÃ¨ce / preuve": "Attestation de travail, fiches de paie, dÃ©compte final",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Permet de confirmer la source de remboursement et les garanties liÃ©es au salaire.",
    },
    {
        "Type de dossier": "Individuel / PME",
        "PiÃ¨ce / preuve": "Factures, reÃ§us de vente, justificatifs des actifs",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Sert Ã  confirmer la rÃ©alitÃ© de l'activitÃ© et la cohÃ©rence du besoin.",
    },
    {
        "Type de dossier": "PME",
        "PiÃ¨ce / preuve": "HypothÃ¨que ou nantissement si exigÃ©",
        "Niveau attendu": "Selon garantie",
        "Lecture": "La garantie rÃ©elle doit Ãªtre traÃ§able avant mise Ã  disposition des fonds.",
    },
    {
        "Type de dossier": "Tous",
        "PiÃ¨ce / preuve": "Photos du client, du garant et de l'activitÃ©",
        "Niveau attendu": "Obligatoire",
        "Lecture": "Facilite la visite, la traÃ§abilitÃ© et les revues ultÃ©rieures.",
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
        "ContrÃ´le ID": 49,
        "ThÃ¨me": "Produits d'Ã©pargne",
        "ContrÃ´le": "Produits d'Ã©pargne inactifs encore utilisÃ©s",
        "Lecture": "RepÃ¨re les comptes encore rattachÃ©s Ã  un produit inactif pour lancer une rÃ©gularisation ou une migration.",
    },
    {
        "ContrÃ´le ID": 50,
        "ThÃ¨me": "Produits d'Ã©pargne",
        "ContrÃ´le": "Produits d'Ã©pargne non valides encore utilisÃ©s",
        "Lecture": "Signale les comptes liÃ©s Ã  un produit non valide afin de sÃ©curiser le paramÃ©trage du portefeuille.",
    },
    {
        "ContrÃ´le ID": 51,
        "ThÃ¨me": "Produits d'Ã©pargne",
        "ContrÃ´le": "Produits sans dÃ©pÃ´t ou retrait autorisÃ© mais avec mouvements",
        "Lecture": "Compare les rÃ¨gles du produit aux mouvements rÃ©ellement observÃ©s sur les comptes.",
    },
    {
        "ContrÃ´le ID": 52,
        "ThÃ¨me": "Produits d'Ã©pargne",
        "ContrÃ´le": "IncohÃ©rences de devise produit, compte et mouvement",
        "Lecture": "Aide Ã  repÃ©rer les Ã©carts de devise qui peuvent fausser la lecture des opÃ©rations ou du produit.",
    },
    {
        "ContrÃ´le ID": 53,
        "ThÃ¨me": "Produits d'Ã©pargne",
        "ContrÃ´le": "Comptes sans produit d'Ã©pargne exploitable",
        "Lecture": "Isole les comptes sans produit de rÃ©fÃ©rence ou avec produit introuvable ou invalide.",
    },
    {
        "ContrÃ´le ID": 54,
        "ThÃ¨me": "Mouvements HDPM",
        "ContrÃ´le": "Mouvements sans compte ou sans opÃ©ration rattachÃ©e",
        "Lecture": "ContrÃ´le la prÃ©sence des rÃ©fÃ©rences minimales avant toute analyse dÃ©taillÃ©e.",
    },
    {
        "ContrÃ´le ID": 55,
        "ThÃ¨me": "Mouvements HDPM",
        "ContrÃ´le": "Mouvements Ã  montant nul, nÃ©gatif ou trÃ¨s Ã©levÃ©",
        "Lecture": "Fait ressortir les Ã©critures qui demandent une revue immÃ©diate de cohÃ©rence ou de conformitÃ©.",
    },
    {
        "ContrÃ´le ID": 56,
        "ThÃ¨me": "Mouvements HDPM",
        "ContrÃ´le": "DÃ©pÃ´ts et retraits par client, compte, agence, devise et produit",
        "Lecture": "Donne une lecture consolidÃ©e des flux d'Ã©pargne sur la pÃ©riode.",
    },
    {
        "ContrÃ´le ID": 57,
        "ThÃ¨me": "Mouvements HDPM",
        "ContrÃ´le": "Analyse des gros mouvements par pÃ©riode",
        "Lecture": "Suivi utile pour la vigilance LBC-FT, les pics d'activitÃ© et les volumes sensibles.",
    },
    {
        "ContrÃ´le ID": 58,
        "ThÃ¨me": "Mouvements HDPM",
        "ContrÃ´le": "Analyse des mouvements par point de service",
        "Lecture": "Compare les points de service selon les volumes, les comptes touchÃ©s et les totaux dÃ©bit/crÃ©dit.",
    },
    {
        "ContrÃ´le ID": 59,
        "ThÃ¨me": "CrÃ©dit",
        "ContrÃ´le": "Demandes de crÃ©dit sans prÃªt accordÃ©",
        "Lecture": "Suit les demandes reÃ§ues qui n'ont pas encore abouti Ã  un prÃªt ou Ã  une mise en place effective.",
    },
    {
        "ContrÃ´le ID": 60,
        "ThÃ¨me": "CrÃ©dit",
        "ContrÃ´le": "PrÃªts incomplets",
        "Lecture": "RepÃ¨re les prÃªts sans dossier, sans compte crÃ©dit, sans compte Ã©pargne ou sans cycle rattachÃ©.",
    },
    {
        "ContrÃ´le ID": 61,
        "ThÃ¨me": "CrÃ©dit",
        "ContrÃ´le": "Cycles de prÃªt Ã©chus non clÃ´turÃ©s",
        "Lecture": "Met en Ã©vidence les cycles dÃ©passÃ©s qui demandent un suivi de recouvrement ou une rÃ©gularisation.",
    },
    {
        "ContrÃ´le ID": 62,
        "ThÃ¨me": "CrÃ©dit",
        "ContrÃ´le": "Comparaison montant demandÃ© et montant accordÃ©",
        "Lecture": "Mesure les Ã©carts entre la demande initiale, le dossier de crÃ©dit et le prÃªt finalement mis en place.",
    },
    {
        "ContrÃ´le ID": 63,
        "ThÃ¨me": "CrÃ©dit",
        "ContrÃ´le": "Analyse des crÃ©dits par agence, produit, devise et Ã©tat",
        "Lecture": "Offre une vue de pilotage du pipeline de crÃ©dit selon les axes les plus utiles pour la dÃ©cision.",
    },
    {
        "ContrÃ´le ID": 64,
        "ThÃ¨me": "Risque et dÃ©cision",
        "ContrÃ´le": "Clients avec forte activitÃ© d'Ã©pargne et crÃ©dit actif",
        "Lecture": "Aide Ã  cibler les profils trÃ¨s actifs qui mÃ©ritent une lecture croisÃ©e Ã©pargne-crÃ©dit.",
    },
    {
        "ContrÃ´le ID": 65,
        "ThÃ¨me": "Risque et dÃ©cision",
        "ContrÃ´le": "Clients avec plusieurs demandes de crÃ©dit sur une mÃªme pÃ©riode",
        "Lecture": "RepÃ¨re les clients qui multiplient les demandes et demandent une vigilance renforcÃ©e.",
    },
    {
        "ContrÃ´le ID": 66,
        "ThÃ¨me": "Risque et dÃ©cision",
        "ContrÃ´le": "Agences avec volume Ã©levÃ© de mouvements ou de crÃ©dits",
        "Lecture": "Compare la pression opÃ©rationnelle entre activitÃ© mouvement et activitÃ© crÃ©dit.",
    },
    {
        "ContrÃ´le ID": 67,
        "ThÃ¨me": "Risque et dÃ©cision",
        "ContrÃ´le": "Produits d'Ã©pargne les plus utilisÃ©s et produits crÃ©dit les plus sollicitÃ©s",
        "Lecture": "Met en Ã©vidence les produits dominants pour le pilotage commercial et la supervision.",
    },
    {
        "ContrÃ´le ID": 68,
        "ThÃ¨me": "Risque et dÃ©cision",
        "ContrÃ´le": "Anomalies Ã  prioriser pour audit",
        "Lecture": "Fournit une synthÃ¨se courte des signaux d'alerte Ã  traiter en premier.",
    },
    {
        "ContrÃ´le ID": 69,
        "ThÃ¨me": "Octroi et validation",
        "ContrÃ´le": "PrÃªts dÃ©caissÃ©s sans validation prÃ©alable exploitable",
        "Lecture": "Isole les prÃªts sans validation, sans validation favorable ou validÃ©s trop tard par rapport au dÃ©boursement.",
    },
    {
        "ContrÃ´le ID": 70,
        "ThÃ¨me": "Garanties",
        "ContrÃ´le": "Couverture de garantie insuffisante",
        "Lecture": "Compare la valeur des garanties au niveau attendu par la tranche ou, Ã  dÃ©faut, au ratio prudent de couverture.",
    },
    {
        "ContrÃ´le ID": 71,
        "ThÃ¨me": "Garanties",
        "ContrÃ´le": "Caution financiÃ¨re insuffisante",
        "Lecture": "Rapproche la caution constatÃ©e, le taux attendu et le minimum du dossier pour repÃ©rer les insuffisances.",
    },
    {
        "ContrÃ´le ID": 72,
        "ThÃ¨me": "Garanties",
        "ContrÃ´le": "Garanties sans garant correctement documentÃ©",
        "Lecture": "RepÃ¨re les garanties sans garant exploitable, sans nom clair ou sans piÃ¨ce de rÃ©fÃ©rence.",
    },
    {
        "ContrÃ´le ID": 73,
        "ThÃ¨me": "Analyse de crÃ©dit",
        "ContrÃ´le": "Analyses obligatoires absentes ou inachevÃ©es",
        "Lecture": "VÃ©rifie la prÃ©sence des analyses de revenu et de projet quand la tranche les rend obligatoires.",
    },
    {
        "ContrÃ´le ID": 74,
        "ThÃ¨me": "DÃ©blocage",
        "ContrÃ´le": "DÃ©caissements sans support exploitable ou incohÃ©rents",
        "Lecture": "Rapproche le prÃªt, le dÃ©blocage et l'opÃ©ration de support pour identifier les cas Ã  revoir en prioritÃ©.",
    },
    {
        "ContrÃ´le ID": 75,
        "ThÃ¨me": "CrÃ©dit de groupe",
        "ContrÃ´le": "CrÃ©dits de groupe avec nombre de bÃ©nÃ©ficiaires hors norme",
        "Lecture": "Aide Ã  relire les dossiers collectifs dont la taille de groupe s'Ã©carte de la fourchette recommandÃ©e.",
    },
    {
        "ContrÃ´le ID": 76,
        "ThÃ¨me": "Risque et dÃ©cision",
        "ContrÃ´le": "Nombre de prÃªts actifs au-delÃ  de la limite du produit",
        "Lecture": "Compare le cumul de prÃªts actifs d'un client au maximum paramÃ©trÃ© sur le produit.",
    },
    {
        "ContrÃ´le ID": 77,
        "ThÃ¨me": "Garanties",
        "ContrÃ´le": "Retrait de garantie avant solde du prÃªt",
        "Lecture": "Signale les garanties retirÃ©es alors que le prÃªt reste non soldÃ© ou soldÃ© plus tard.",
    },
    {
        "ContrÃ´le ID": 78,
        "ThÃ¨me": "RÃ©Ã©chelonnement",
        "ContrÃ´le": "Demandes de rÃ©Ã©chelonnement sans validation exploitable",
        "Lecture": "Isole les rÃ©Ã©chelonnements non validÃ©s ou saisis sur des prÃªts dÃ©jÃ  sortis du portefeuille normal.",
    },
    {
        "ContrÃ´le ID": 79,
        "ThÃ¨me": "RÃ©Ã©chelonnement",
        "ContrÃ´le": "PrÃªts marquÃ©s rÃ©Ã©chelonnÃ©s sans demande formelle",
        "Lecture": "RepÃ¨re les prÃªts dont la date de rÃ©Ã©chelonnement existe sans dossier formalisÃ© correspondant.",
    },
    {
        "ContrÃ´le ID": 80,
        "ThÃ¨me": "Contentieux",
        "ContrÃ´le": "PrÃªts en contentieux avec incohÃ©rences de transfert ou de montant",
        "Lecture": "ContrÃ´le la cohÃ©rence des dates et des montants pour les dossiers basculÃ©s en contentieux.",
    },
    {
        "ContrÃ´le ID": 81,
        "ThÃ¨me": "Octroi et validation",
        "ContrÃ´le": "Validations de dossier incohÃ©rentes avec le dossier ou le prÃªt",
        "Lecture": "Compare le montant, les Ã©chÃ©ances, le diffÃ©rÃ© et la grÃ¢ce validÃ©s aux valeurs du dossier et du prÃªt.",
    },
    {
        "ContrÃ´le ID": 82,
        "ThÃ¨me": "Garanties",
        "ContrÃ´le": "Types de garantie utilisÃ©s mais non paramÃ©trÃ©s pour l'agence",
        "Lecture": "Signale les garanties hors paramÃ©trage du point de service ou de la devise concernÃ©e.",
    },
    {
        "ContrÃ´le ID": 83,
        "ThÃ¨me": "Suivi du prÃªt",
        "ContrÃ´le": "Cycles de prÃªt sans Ã©chÃ©ancier TABAMOR exploitable",
        "Lecture": "RepÃ¨re les cycles sans plan d'amortissement lisible pour le suivi des Ã©chÃ©ances et de la piste d'audit.",
    },
]

def build_sql_operations_control_catalog_table() -> pd.DataFrame:
    return pd.DataFrame(SQL_OPERATIONS_CONTROL_CATALOG)

