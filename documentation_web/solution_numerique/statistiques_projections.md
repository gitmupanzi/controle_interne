# Statistiques et projections

## Statistiques

L'onglet Statistiques est organisé en blocs repliables :

1. Clients ;
2. Comptes ouverts et comptes bloqués ;
3. Crédits ;
4. Transactions.

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
- devise.

## Comparaisons

Les indicateurs peuvent être comparés :

- à une période précédente variable : 7 jours, 15 jours, un mois ou autre période définie ;
- à la même période de l'année précédente lorsque les données existent.

Cette lecture aide à distinguer une tendance normale d'un effet lié à un événement social, économique, scolaire, politique ou environnemental.

## Projections

Les projections restent pragmatiques : elles doivent expliquer les limites du modèle et les notions de base au lecteur. Par exemple, WAPE signifie `Weighted Absolute Percentage Error`, soit erreur absolue pondérée en pourcentage.

## Règles visuelles

Les titres des graphiques doivent rester hors de la zone de légende. Les fonds des graphiques exportés doivent être blancs.
