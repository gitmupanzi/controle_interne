# Clients, épargnes et crédits

## Clients

Le cockpit Clients mesure :

- clients chargés depuis `Customers` ;
- clients actifs sur la période ;
- créations de clients ;
- nouveaux clients et comptes créés sur la période, avec activité transactionnelle, nombre de transactions, solde du compte ouvert et montant DAT par devise ;
- tranches d'encours par famille (`compte_ouvert`, `dat`, `credit`) et par devise ;
- croisements avec G2 et Clients Perfect lorsqu'ils sont disponibles.

La table `Nouveaux clients et comptes actifs par devise` répond à une question de pilotage : un client ou un compte récemment créé est-il réellement utilisé ? Elle croise `Customers` pour la date de création client, `Transactions` pour l'activité consolidée et `Savings Account` pour les positions compte ouvert et DAT. Les montants restent toujours séparés entre CDF et USD.

L'interface regroupe les analyses Clients en cinq volets :

| Volet | Contenu principal |
|---|---|
| `Vue d'ensemble` | KPI clients et qualité des données |
| `Activité et activation` | activité observée, inactivité, acquisition et activation |
| `Nouveaux clients et comptes` | nouveaux clients, comptes ouverts et DAT créés sur la période |
| `Client 360 et segmentation` | produits détenus, présence épargne/DAT/crédit, tranches d'encours et segmentation |
| `Opportunités` | DAT sans crédit actif et listes commerciales prudentes |

## Épargnes

Le cockpit Épargnes repose sur `Savings Account`.

Analyses principales :

- comptes ouverts ;
- comptes bloqués / DAT ;
- encours par devise ;
- statuts ;
- DAT échus ou bientôt à terme ;
- intérêts calculés ou à estimer.
- concentration par rang client et par tranche d'encours.

L'interface regroupe ces analyses en six volets pour éviter une navigation trop longue :

| Volet | Contenu principal |
|---|---|
| `Vue d'ensemble` | KPI de synthèse par devise |
| `Flux et activité` | dépôts, retraits, remboursements depuis compte ouvert et activité observée |
| `Portefeuille et produits` | portefeuille actuel, détail des comptes, nouveaux comptes, clients et produits |
| `DAT et échéances` | position DAT, échéances, intérêts estimés et préparation des remboursements |
| `Concentration et opportunités` | concentration des encours, tranches d'encours, gros épargnants, DAT sans crédit actif et forte épargne sans crédit |
| `Contrôles et anomalies` | qualité des données, catalogue KPI et limites |

Les colonnes visibles doivent être en français, sans accents ni espaces lorsque cela sert aux traitements techniques.

## Crédits

Le cockpit Crédits repose sur `Loans Account` et, pour les remboursements observés, sur `Transactions`.

Analyses principales :

- nouveaux crédits ;
- encours ;
- remboursements ;
- échéances ;
- crédits actifs, terminés, en retard ou à surveiller ;
- concentration par client, produit et tranche d'encours ;
- rapprochement crédit / épargne lorsque le `savings_account_id` est disponible.

L'interface regroupe les analyses Crédits en six volets :

| Volet | Contenu principal |
|---|---|
| `Vue d'ensemble` | KPI du portefeuille crédit par devise |
| `Production et remboursements` | décaissements et remboursements observés sur la période |
| `Portefeuille et échéances` | position Loans Account, échéances, maturité et cohortes à date |
| `Risques et concentration` | PAR simplifié, prêts à surveiller, top expositions et concentration |
| `Crédit et épargne` | rapprochement analytique crédit, compte ouvert et DAT |
| `Opportunités et qualité` | opportunités crédit, contrôles qualité, KPI non calculables et limites |

## Séparation des lectures

Épargne et crédit ne doivent pas être mélangés dans l'extrait client. Le détail transactionnel montre le compte ouvert ; les DAT et remboursements ont leurs blocs dédiés.
