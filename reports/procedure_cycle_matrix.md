# Matrice procédures–cycles de microfinance

Cette synthèse décrit les thèmes de contrôle trouvés dans `SOP/`. Elle ne remplace pas les manuels et ne crée aucun seuil financier supplémentaire.

| Cycle | Processus documentés | Contrôles à refléter dans l'application | Sources principales |
|---|---|---|---|
| Crédit | admissibilité, collecte des données, analyse financière, comité, pré-déblocage, garanties, remboursement, arriérés, restructuration, radiation, provisionnement | KYC, capacité de remboursement, validation avant décaissement, cohérence demandé/accordé, garanties, retards, PAR, rééchelonnement, provisions | `MANUEL EPARGNE ET CREDIT.docx`, `MANUEL CONTROLE INTERNE DEFINITIF.docx`, `catalogue_global_complet_2026.docx` |
| Épargne | ouverture de compte, KYC, produits standards et segmentés, DAT, soldes, dormance | complétude KYC, multi-comptes, comptes dormants, soldes négatifs, conditions DAT, cohérence produit/devise | `MANUEL EPARGNE ET CREDIT.docx`, `catalogue_global_complet_2026.docx`, `controle_interne_IMF_par_cycle.xlsx` |
| Caisse et guichet | ouverture/fermeture, plafonds d'encaisse, comptage, dépôts/retraits, faux billets, pièces, écarts, incidents | rapprochement physique/SIG, écarts, respect des limites, traçabilité des pièces, annulations, séparation des responsabilités | `Procédure de caisse.pdf`, `controle_interne_IMF_par_cycle.xlsx` |
| Dépôts et retraits | saisie, validation, date de valeur, utilisateur, point de service, annulation, mobile banking | opération non validée, validation antérieure à la saisie, saisie tardive, auto-validation, absence d'utilisateur ou de point de service | `MANUEL CONTROLE INTERNE DEFINITIF.docx`, extractions de contrôle `line_list` |
| Trésorerie et banque | comptes bancaires, mouvements de fonds, rapprochement, signatures autorisées | rapprochement mensuel, double signature, écarts non justifiés, ancienneté des suspens | `MANUEL CONTROLE INTERNE DEFINITIF.docx`, `controle_interne_IMF_par_cycle.xlsx` |
| Comptable et financier | saisie, pièces, imputation, approbation, équilibre des écritures, dépenses | pièce et visa, débit/crédit, écritures déséquilibrées, doublons, dates incohérentes | `controle_interne_IMF_par_cycle.xlsx`, `saisie_controle_interne.xlsx` |
| Likelemba | constitution et gouvernance du groupe, analyse individuelle, cycle de crédit, impayés, LBC/FT, protection du client | nombre et identité des membres, graduation, solidarité, réunions, impayés, conflits, documents obligatoires | `MANUEL DES PROCÉDURES LIKELEMBA.docx` |
| Money Provider / M-PESA | monnaie électronique, E-money, dépôts/retraits, vérification, documentation, écarts, confidentialité | rapprochement G2/DAT, devise, téléphone normalisé, solde reconstitué, écarts, traçabilité et LBC/FT | `Procédure de MONEY PROVIDER-IMB BISOU BISOU.pdf`, fichiers M-PESA_Turbo décrits dans le README |
| CRM | qualité des fiches, traitement des demandes, escalade, incidents et actions | téléphone/e-mail, pièces manquantes, inactivité, doublons, priorité, responsable et statut de l'action | `CRM.pdf`, `CRM.xlsx`, `Proposition_solution_Zoho.xlsx` |
| Sécurité SI | gestion des accès, besoin d'en connaître, mots de passe, comptes utilisateurs | comptes sans propriétaire, profils excessifs, comptes inactifs, absence de revue ou de date de dernière connexion | `controle_interne_IMF_par_cycle.xlsx` |
| Contrôle transversal | plan de contrôle, cartographie des risques, incidents, recommandations, preuves et échéances | niveau de risque, résultat, gravité, responsable, preuve, action corrective, date d'échéance et clôture | `Cartographie des risques.docx`, `controle_interne_IMF_par_cycle.xlsx`, `saisie_controle_interne.xlsx` |

## Principes transversaux retenus

- Une anomalie automatique est un signal de contrôle, pas une preuve définitive.
- Les seuils financiers doivent provenir d'un catalogue ou d'une procédure explicite.
- Les étapes sensibles exigent une trace de l'auteur, du validateur, de la date et de la pièce justificative.
- La séparation des tâches doit être visible dans les contrôles de caisse, décaissement, validation et comptabilité.
- Les informations KYC et personnelles ne doivent apparaître que lorsqu'elles sont nécessaires au contrôle.
