# Statistiques et projections

## Statistiques

L'onglet Statistiques est organisé en blocs repliables :

1. Clients ;
2. Comptes ouverts et comptes bloqués ;
3. Crédits ;
4. Transactions.

Le rapport Word conserve une lecture décisionnelle en quatre blocs :

1. Comparaison avec la période précédente ;
2. Clients ;
3. Épargnes et DAT ;
4. Crédits.

Dans le Word, le premier bloc couvre la comparaison entre deux périodes. Le bloc
**Flux observés sur la période** restitue ensuite deux lectures séparées :

- les **flux entrants** : entrées DAT, entrées sur comptes ouverts et remboursements observés, sans colonnes de comptage `Opérations` ni `Comptes clients` dans le Word ;
- les **flux sortants** : sorties totales, retraits d'épargne, décaissements crédits et flux net.

Ces flux restent des mouvements de période. Les trois blocs `Clients`, `Épargnes
et DAT` et `Crédits` restent, eux, des positions à date : ils lisent uniquement
les encours et situations arrêtées à la date de fin.

Dans les tableaux Word, tous les montants de flux sont présentés avec un
séparateur de milliers et deux décimales afin de faciliter la lecture par la
Direction.

## Vocabulaire métier du rapport

Dans le rapport statistique, le mot `compte client` désigne le numéro de téléphone normalisé. C'est la clé terrain la plus simple pour rapprocher les fichiers de la Solution Numérique et, à terme, Perfect Vision.

Un même compte client peut porter plusieurs produits financiers :

- un ou plusieurs produits d'épargne ouverte ;
- un ou plusieurs produits DAT / comptes bloqués ;
- un ou plusieurs produits crédit.

Le rapport Word et l'export Excel utilisent donc cette lecture :

| Ancienne lecture à éviter | Lecture recommandée |
|---|---|
| Clients actifs | Comptes clients actifs |
| Nouveaux comptes clients | Nouveaux numéros clients |
| Clients avec DAT positif | Comptes clients avec produit DAT positif |
| Nouveaux comptes ouverts | Nouveaux produits d'épargne ouverte |
| Comptes bloqués / DAT | Produits DAT / comptes bloqués |
| Comptes crédit | Produits crédit |

Cette convention évite de confondre la personne, son numéro de téléphone et les produits qu'elle détient. Elle rapproche aussi la Solution Numérique du raisonnement classique de Perfect Vision : un compte client peut avoir plusieurs produits.

Les filtres principaux sont :

- date de début ;
- date de fin ;
- fréquence ;
- période de comparaison ;
- périmètre annuel ;
- horizon échéances DAT ;
- devise.

`Horizon échéances DAT` indique le nombre de jours à regarder après la date de fin pour repérer les DAT positifs qui arrivent bientôt à échéance. Par exemple, avec une date de fin au 21/08/2026 et un horizon de 30 jours, le rapport compte les DAT dont l'échéance tombe entre le 21/08/2026 et le 20/09/2026.

## Rapport opérationnel

Le rapport Word `Statistiques` est conçu pour la Direction. Il est présenté en paysage afin de réduire les coupures de tableaux et il privilégie trois blocs :

1. Clients ;
2. Épargnes et DAT ;
3. Crédits.

Les libellés du rapport doivent rester métier. On parle donc de `position d'épargne`, `position DAT`, `position crédit`, `produits crédit`, `encours crédit`, `crédits en retard` et `portefeuille à risque`, plutôt que d'afficher les noms techniques des fichiers d'import dans les tableaux de décision.

Les indicateurs de stock sont lus à la date de fin, qui est la date d'arrêté. Dans
les blocs `Clients`, `Épargnes et DAT` et `Crédits`, le rapport ne répète pas les
créations ou mouvements de la période, car cette lecture est déjà portée par le bloc
`Comparaison avec la période précédente`.

- les produits DAT et les produits d'épargne ouverte sont mesurés à la date de fin ;
- les comptes clients avec histoire d'épargne active sont les numéros clients ayant au moins un produit d'épargne ou DAT actif, avec solde non nul et date de mise à jour différente de la date de création ;
- les crédits en retard comptent les produits crédit ayant au moins un jour de retard à la date de fin ;
- l'encours crédit en retard correspond à l'encours de ces crédits en retard ;
- le taux de portefeuille à risque PAR 30 correspond à l'encours en retard de 30 jours ou plus rapporté à l'encours total de la devise.

Pour les indicateurs décisionnels d'épargne et de DAT, un produit est considéré comme réellement actif lorsqu'il a un solde non nul, un statut actif et une date de mise à jour différente de la date de création. Cette règle évite de compter comme vrais produits les lignes techniques créées automatiquement au démarrage du parcours client, notamment les comptes ouverts à solde nul qui n'ont jamais évolué.

Ces indicateurs restent toujours séparés par devise pour les montants. Les nombres de comptes clients ou de produits peuvent être consolidés, mais les USD et les CDF ne doivent pas être additionnés dans un même montant.

## Comparaisons

Les indicateurs peuvent être comparés :

- à une période précédente variable : 7 jours, 15 jours, un mois ou autre période définie.

Les comparaisons annuelles N-1 ne sont plus affichées dans l'onglet `Statistiques`. L'objectif est de garder un écran plus opérationnel, centré sur la période analysée, la période précédente et les indicateurs de portefeuille à date.

Dans le rapport Word, le bloc `Comparaison avec la periode precedente` reste volontairement court. Il conserve seulement les indicateurs qui declenchent une lecture de pilotage : nouveaux numeros clients, nouveaux produits DAT / comptes bloques, montant des nouveaux produits DAT / comptes bloques, DAT arrivant a echeance, nouveaux produits credit et montant des nouveaux produits credit. Le taux de conversion DAT en credit n'est pas repris comme comparaison de periode, car il se lit mieux comme une position de portefeuille a la date d'arrete. Les volumes transactionnels, le chiffre d'affaires observe, les operations brutes, les remboursements observes et les depots DAT issus de `Transactions` restent hors de ce bloc.

Pour garder le Word lisible par la Direction, les blocs de stock sont aussi resserres :

- `Clients` : comptes clients connus, comptes clients avec histoire d'epargne active, comptes clients ayant a la fois un DAT positif et un credit actif ;
- `Epargnes et DAT` : encours DAT, encours d'epargne ouverte, nombre de DAT arrivant a echeance et encours DAT arrivant a echeance ;
- `Credits` : encours credit, nombre de credits en retard, encours credit en retard et PAR 30.

Les autres details restent disponibles dans les cockpits Excel et les onglets specialises.

## Projections

Les projections restent pragmatiques : elles doivent expliquer les limites du modèle et les notions de base au lecteur. Par exemple, WAPE signifie `Weighted Absolute Percentage Error`, soit erreur absolue pondérée en pourcentage.

## Règles visuelles

Les titres des graphiques doivent rester hors de la zone de légende. Les fonds des graphiques exportés doivent être blancs.
