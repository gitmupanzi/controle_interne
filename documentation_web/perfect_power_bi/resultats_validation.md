# Résultats de validation Power BI

## Lot Crédit cœur — 30 juin 2026

Source autorisée : `BB_VISION_PRO_TEST`. Base cible : `BB_VISION_REPORTING`.

- procédure installée : `rpt.load_f_credit_core` ;
- batch mensuel complet de référence : 20 ;
- détail Q96 : 1 172 lignes, 1 172 numéros de prêt distincts ;
- synthèse Q97 : 12 lignes ;
- doublons au grain prêt × devise × date : 0 ;
- devise manquante, numéro de prêt manquant, encours nul ou non positif : 0 ;
- rechargement ciblé `@id_devise_reporting = 1` testé sous transaction : 1 137 détails USD et 9 synthèses USD, puis retour arrière réussi ;
- références exécutables vers la base de production : 0.

### Rapprochement Q97 — CDF

| KPI | Source | Reporting | Écart |
|---|---:|---:|---:|
| Prêts actifs | 35 | 35 | 0 |
| Encours | 134 639 483,12 | 134 639 483,12 | 0 |
| PAR1 | 96 249 575,12 | 96 249 575,12 | 0 |
| PAR30 | 92 598 987,12 | 92 598 987,12 | 0 |
| PAR90 | 92 367 564,12 | 92 367 564,12 | 0 |
| PAR180 | 2 493 863,60 | 2 493 863,60 | 0 |
| Provision | 206 932,00 | 206 932,00 | 0 |

### Rapprochement Q97 — USD

| KPI | Source | Reporting | Écart |
|---|---:|---:|---:|
| Prêts actifs | 1 137 | 1 137 | 0 |
| Encours | 6 144 278,26 | 6 144 278,26 | 0 |
| PAR1 | 2 892 311,39 | 2 892 311,39 | 0 |
| PAR30 | 2 216 230,15 | 2 216 230,15 | 0 |
| PAR90 | 1 435 663,28 | 1 435 663,28 | 0 |
| PAR180 | 434 251,05 | 434 251,05 | 0 |
| Provision | 95 941,2775 | 95 941,2775 | 0 |

Les 14 contrôles du lot Crédit cœur ont le statut `SOURCE_REPORTING_OK` dans `ctl.kpi_reconciliation`.

## Lot Crédit flux — juin 2026

Source autorisée : `BB_VISION_PRO_TEST`. Base cible : `BB_VISION_REPORTING`.

- procédure installée : `rpt.load_f_credit_flows` ;
- batch mensuel complet : 22 ;
- message batch : `Chargement Conformite + Clients + Credit coeur + Credit flux termine. Lignes inserees : 69461.` ;
- `rpt.f_credit_decaissements` : 12 lignes ;
- `rpt.f_credit_echeances_futures` : 92 lignes ;
- doublons au grain reporting des décaissements : 0 ;
- doublons au grain reporting des échéances futures : 0 ;
- vues Power BI `pbi.F_Credit_Decaissements` et `pbi.F_Credit_Echeances_Futures` : 12 et 92 lignes.

### Rapprochement Q99 — Décaissements

| Devise | Lignes source | Lignes reporting | Prêts source | Prêts reporting | Clients source | Clients reporting | Montant source | Montant reporting | Écart montant |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CDF | 2 | 2 | 11 | 11 | 11 | 11 | 11 000 000,0000 | 11 000 000,0000 | 0 |
| USD | 10 | 10 | 237 | 237 | 232 | 232 | 753 967,5000 | 753 967,5000 | 0 |

### Rapprochement Q100 — Échéances futures

| Devise | Lignes source | Lignes reporting | Prêts source | Prêts reporting | Échéances source | Échéances reporting | Montant source | Montant reporting | Écart montant |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CDF | 12 | 12 | 120 | 120 | 120 | 120 | 161 722 292,0000 | 161 722 292,0000 | 0 |
| USD | 80 | 80 | 5 717 | 5 717 | 5 828 | 5 828 | 5 214 286,6800 | 5 214 286,6800 | 0 |

Le script de rapprochement est `data/kpi_perfect/reporting_sql/15_validate_credit_flows_june_2026.sql`.

## Feuille Direction — structure PBIR

- les fichiers `visual.json` de la page sont valides en JSON ;
- toutes les mesures `_Mesures` référencées par les visuels existent ;
- les deux graphiques et les deux cartes empilées de la rangée inférieure occupent des zones distinctes, sans chevauchement ;
- les ratios crédits/dépôts sont séparés en CDF et USD ;
- le contrôle visuel final dans Power BI Desktop reste à exécuter après ouverture et actualisation du PBIP.

## Lot Épargne soldes — juin 2026

Source autorisée : `BB_VISION_PRO_TEST`. Base cible : `BB_VISION_REPORTING`.

- procédure installée : `rpt.load_f_epargne_soldes` ;
- batch mensuel complet : 23 ;
- `rpt.f_epargne_soldes` : 934 lignes ;
- doublons au grain mois × agence × produit épargne × type compte × devise : 0 ;
- vue Power BI `pbi.F_Epargne_Soldes` alimentée depuis `rpt.f_epargne_soldes`.

### Rapprochement Q103 — Soldes épargne

| Devise | Lignes source | Lignes reporting | Comptes source | Comptes reporting | Clients agrégés source | Clients agrégés reporting | Solde source | Solde reporting | Écart solde |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CDF | 639 | 639 | 7 505 | 7 505 | 7 479 | 7 479 | 892 347 239,0100 | 892 347 239,0100 | 0 |
| USD | 295 | 295 | 13 321 | 13 321 | 13 279 | 13 279 | 7 942 318,9800 | 7 942 318,9800 | 0 |

Le script de rapprochement est `data/kpi_perfect/reporting_sql/17_validate_epargne_soldes_june_2026.sql`.

## Feuille Risque crédit — structure PBIR

- les cartes prioritaires compactes `PAR 7`, `PAR 30` et `PAR 60` ont été ajoutées ;
- toutes les valeurs KPI de type carte utilisent une police 15 pour rester lisibles ;
- tous les fichiers JSON du rapport sont valides ;
- toutes les mesures référencées par les visuels existent dans `_Mesures`.

## Lot Crédit analytique — juin 2026

Source autorisée : `BB_VISION_PRO_TEST`. Base cible : `BB_VISION_REPORTING`.

- procédure installée : `rpt.load_f_credit_analytics` ;
- batch mensuel complet : 26 ;
- script de validation : `data/kpi_perfect/reporting_sql/19_validate_credit_analytics_june_2026.sql` ;
- doublons au grain métier : 0 sur les 9 tables ;
- vues Power BI `pbi.*` alignées avec les tables `rpt.*`.

| Requête | Table reporting | Lignes juin 2026 | Doublons |
|---:|---|---:|---:|
| 98 | `rpt.f_credit_top_encours` | 50 | 0 |
| 101 | `rpt.f_credit_retention` | 5 | 0 |
| 102 | `rpt.f_credit_vintage` | 9 | 0 |
| 104 | `rpt.f_credit_tranches` | 29 | 0 |
| 105 | `rpt.f_credit_concentration` | 12 | 0 |
| 106 | `rpt.f_credit_couverture` | 1 172 | 0 |
| 107 | `rpt.f_credit_provisions_detail` | 879 | 0 |
| 108 | `rpt.f_credit_duree` | 1 172 | 0 |
| 109 | `rpt.f_credit_tendance_par` | 12 | 0 |

Les batches 24 et 25 sont des essais techniques échoués conservés dans l'historique ETL. Le batch valide le plus récent est le batch 26.
