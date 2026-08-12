# Solution Numérique — Épargnes

Le cockpit `Épargnes` est le cockpit unique des comptes ouverts, des comptes bloqués et des DAT dans la Solution Numérique.

## Sources utilisées

| Source | Rôle |
|---|---|
| `Savings Account` | Source principale : comptes ouverts, DAT, soldes, statuts, produits et échéances. |
| `Transactions` | Flux observés sur la période : dépôts, retraits, retours DAT et mouvements liés au compte ouvert. |
| `Loans Account` | Permet de repérer les clients avec ou sans crédit actif. |
| `G2` | Source facultative d'identité ou de contrôle ; elle ne calcule pas les soldes d'épargne. |

## Analyses principales

Le cockpit Épargnes mesure :

- les comptes ouverts ;
- les comptes bloqués / DAT ;
- les encours par devise ;
- les statuts des comptes ;
- les DAT échus ou bientôt à terme ;
- les intérêts calculés ou à estimer ;
- la concentration par rang client ;
- la concentration par tranche d'encours ;
- les clients avec DAT ou forte épargne sans crédit actif.

Les montants, soldes, flux et estimations restent séparés par devise. Il ne faut jamais additionner CDF et USD.

## Volets de l'interface

| Volet | Contenu principal |
|---|---|
| `Vue d'ensemble` | KPI de synthèse par devise. |
| `Flux et activité` | Dépôts, retraits, remboursements depuis compte ouvert et activité observée. |
| `Portefeuille et produits` | Portefeuille actuel, détail des comptes, nouveaux comptes, clients et produits. |
| `DAT et échéances` | Position DAT, échéances, intérêts estimés et préparation des remboursements. |
| `Concentration et opportunités` | Concentration des encours, tranches d'encours, gros épargnants, DAT sans crédit actif et forte épargne sans crédit. |
| `Contrôles et anomalies` | Qualité des données, catalogue KPI et limites. |

## Stock actuel et flux de période

Deux lectures doivent rester séparées :

- `Savings Account` donne une position actuelle : comptes, soldes, statuts et échéances.
- `Transactions` donne les mouvements observés sur une période.

Un seul fichier `Savings Account` ne suffit pas à reconstruire une évolution historique des soldes. Pour parler d'évolution d'encours, il faut plusieurs arrêtés datés.

## Feuilles clés du cockpit Excel Épargnes

Dans le fichier Excel généré, les onglets prioritaires sont colorés en rouge. Cette couleur signifie `à lire en priorité`; elle ne signifie pas automatiquement qu'il y a une anomalie.

Pour rendre le cockpit opérationnel, les feuilles clés écartent les colonnes purement techniques : fichiers sources, clés internes, colonnes brutes, ordres d'import, traces de calcul et identifiants intermédiaires. Elles conservent les informations utiles à l'action : client, téléphone, devise, produit d'épargne, statut, dates, solde, capital DAT, échéance, tranche, score, ratio et commentaire.

| Priorité | Feuille | Lecture recommandée |
|---:|---|---|
| 1 | `Epargne_Vue_Ensemble` | Synthèse générale des comptes ouverts, comptes bloqués et DAT. |
| 2 | `Epargne_Portefeuille` | Position du portefeuille par devise, famille d'épargne, produit et statut. |
| 3 | `Epargne_Flux` | Dépôts, retraits et mouvements observés sur la période. |
| 4 | `Epargne_DAT` | Liste des DAT en cours avec capital, échéance et situation. |
| 5 | `Epargne_Echeances_DAT` | DAT qui arrivent bientôt à terme ou qui sont échus : préparation du remboursement. |
| 6 | `Epargne_Top_Clients` | Clients qui épargnent le plus, par devise et par famille d'encours. |
| 7 | `Epargne_Tranches` | Répartition des clients par tranche d'encours, plus lisible qu'un simple rang individuel. |
| 8 | `Epargne_DAT_Sans_Credit` | Clients avec DAT sans crédit actif : opportunités commerciales prudentes. |
| 9 | `Epargne_Forte_Sans_Credit` | Clients avec forte épargne sans crédit actif : base d'analyse commerciale, sans décision automatique. |
| 10 | `Epargne_Qualite` | Qualité des données, anomalies et limites de lecture. |

Lecture Direction : commencer par `Epargne_Vue_Ensemble`, `Epargne_Portefeuille`, `Epargne_DAT`, `Epargne_Echeances_DAT` et `Epargne_Top_Clients`. Ces feuilles permettent de suivre les dépôts, les comptes bloqués, les échéances DAT et la concentration de l'épargne.

## À retenir

- `Savings Account` est la source maître pour les comptes ouverts et DAT.
- G2 peut enrichir l'identité, mais ne remplace pas les montants de la Solution Numérique.
- Les listes `DAT sans crédit actif` et `forte épargne sans crédit` sont des pistes commerciales prudentes, pas des décisions automatiques.
