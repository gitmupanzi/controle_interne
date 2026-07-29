# Modèle sémantique et pages

## Principes

- Une table de faits porte un grain stable.
- Une dimension filtre plusieurs faits.
- Les flux et les instantanés restent dans des faits distincts.
- Une mesure monétaire conserve sa devise.
- Un même attribut métier doit être visible une seule fois dans le modèle.
- Les tables détaillées servent au drill-through, pas aux cartes de synthèse.

## Dimensions conformes

| Dimension | Attributs utiles |
|---|---|
| `DimDate` | date, mois, trimestre, année, fin de mois |
| `DimDevise` | code, libellé, symbole |
| `DimAgence` | code, nom, zone |
| `DimClient` | code client, type, catégorie, agence, profil de risque |
| `DimProduitCredit` | produit, objet, secteur, périodicité |
| `DimProduitEpargne` | produit, type de compte |
| `DimTypeOperation` | code, libellé, canal |

Les clés techniques peuvent rester dans le modèle pour les relations, mais doivent être masquées aux lecteurs.

## Faits recommandés

| Fait | Grain | Requêtes de référence |
|---|---|---|
| `FactPortefeuilleCredit` | prêt × date de situation | 96, 98, 106 à 108 |
| `FactPortefeuilleCreditAgrege` | agence × produit × devise × date | 97, 104, 105, 109 |
| `FactDecaissementCredit` | décaissement ou groupe mensuel | 99 |
| `FactEcheanceCredit` | échéance ou groupe mensuel | 100, 145, 146 |
| `FactRenouvellementCredit` | client ou cohorte de clôture | 85 à 89, 101 |
| `FactVintageCredit` | cohorte × âge × agence × produit × devise | 102 |
| `FactEpargneSnapshot` | compte × date de situation | 103, 110 |
| `FactOperation` | opération ou écriture | 36, 37, 126 |
| `FactConformite` | grain porté par `type_element` | 156 |
| `FactExceptionControle` | exception × requête × date | contrôles prioritaires normalisés |

Ne pas fusionner ces grains dans une seule table large.

## Pages V1

### Direction

Sources principales : 97, 99, 103, 109 et 156.

Afficher :

- encours ;
- nombre de prêts actifs ;
- PAR30 et PAR90 ;
- provision ;
- décaissements ;
- solde épargne ;
- nombre d'alertes conformité ;
- tendance mensuelle par agence, produit et devise.

### Crédit

Sources principales : 96 à 102 et 104 à 109.

Prévoir :

- portefeuille et qualité ;
- concentration ;
- décaissements ;
- échéances futures ;
- vintage ;
- renouvellement ;
- couverture par épargne et garanties ;
- drill-through client et prêt.

### Épargne

Sources principales : 103, 110 à 113, 124, 144 et 147.

Prévoir :

- soldes et comptes ;
- dépôts et retraits ;
- comptes dormants ;
- produits et agences ;
- DAT ;
- épargne disponible face au crédit.

### Conformité

Source Power BI : Q156.

Prévoir :

- synthèse LBC-FT ;
- alertes et statut de revue ;
- fractionnement ;
- profils à risque ;
- sanctions ;
- comptes réactivés ;
- qualité des données ;
- trous de couverture.

Utiliser Q149 à Q155 pour réconcilier les résultats de Q156 pendant les tests.

### Surveillance et qualité

Regrouper les anomalies prioritaires des contrôles, avec :

- numéro de requête ;
- cycle ;
- date ;
- entité ;
- référence source ;
- montant ;
- devise ;
- motif ;
- sévérité ;
- statut de traitement.

## Mesures

Pour chaque mesure, documenter :

- nom métier ;
- formule DAX ;
- table et colonne sources ;
- grain ;
- fenêtre de dates ;
- devise ;
- exclusions ;
- règle de comparaison ;
- requête SQL de rapprochement.

Mesures prioritaires :

- encours total ;
- PAR1, PAR30, PAR90 ;
- taux de PAR ;
- provision ;
- montant décaissé ;
- échéances futures ;
- solde épargne ;
- nombre de clients et comptes actifs ;
- concentration top 10 % ;
- exposition nette non couverte ;
- alertes à revoir ;
- taux de couverture des contrôles.

## Devises

Une mesure nominale doit :

- être filtrée sur une devise unique ; ou
- renvoyer vide lorsque plusieurs devises sont sélectionnées.

Une conversion exige une table de taux datée et une mesure portant explicitement un nom tel que `Équivalent CDF`. Ne jamais remplacer silencieusement les montants nominaux.

## Dates

- Utiliser `DateSituation` pour les instantanés.
- Utiliser `DateOperation`, `DateEcheance`, `DateDecaissement` ou `DateEvenement` pour les flux.
- Relier les dates secondaires par relations inactives et les activer dans les mesures appropriées.
- Utiliser une seule dimension Date officielle couvrant l'historique nécessaire.
