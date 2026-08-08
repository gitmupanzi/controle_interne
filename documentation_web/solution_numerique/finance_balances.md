# Finance, balances et journaux

## Objectif

Le bloc Finance restitue les mouvements observés dans les transactions numériques :

- balance par client ;
- journaux ;
- évolution des dépôts et retraits ;
- remboursements observés ;
- nouveaux crédits ;
- export Word/PDF portrait de la balance ;
- export Excel du suivi des dépôts et retraits.

## Balance observée

La balance observée est construite depuis les transactions importées. Elle permet de voir, par client et devise, les entrées, sorties et soldes observés sur la période filtrée.

## Suivi des dépôts et retraits

Le suivi demandé par période est orienté Excel pour permettre le retraitement :

| Colonne | Lecture |
|---|---|
| Client | Numéro et nom si G2 est disponible |
| Opération | Dépôt ou retrait |
| Devise | CDF ou USD |
| Période | Jours compris dans le filtre |
| Solde | Solde du client |
| Score | Nombre d'occurrences rapporté à l'ensemble de la période |

## Précaution

La balance observée est une restitution analytique issue des exports importés. Elle ne remplace pas une balance générale certifiée.
