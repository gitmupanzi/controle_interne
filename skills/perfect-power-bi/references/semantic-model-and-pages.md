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

Avant de proposer une nouvelle page ou un nouveau visuel, inspecter le PBIP existant. Dans le projet IMF BB actuel, les pages `Paramétrage`, `Direction`, `Clients`, `Crédit`, `Risque crédit`, `Prévisions crédit`, `Épargne`, `Conformité` et `Surveillance` existent déjà. Les ajouts doivent donc enrichir une décision métier absente ou renforcer la traçabilité, pas répéter ces pages.

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

## Analyses avancées après V1

Ces analyses complètent la V1 du tableau de bord IMF BB. Ne les ajouter que si la source SQL, le grain, la devise, la période, la mesure DAX et le test de rapprochement sont clairement définis.

### Rapprochement KPI avec SQL

Objectif : rendre le tableau de bord audit-proof.

Prévoir une matrice de rapprochement pour chaque KPI majeur :

- nom de la mesure Power BI ;
- page et visuel ;
- requête SQL de référence dans `data/modelisation/requetes.sql` ;
- table de fait utilisée ;
- grain attendu ;
- filtre de période ;
- filtre de devise ;
- exclusions ou statuts pris en compte ;
- écart toléré ;
- résultat du dernier rapprochement.

Priorité : encours, prêts actifs, PAR1, PAR30, PAR90, provision, décaissements, épargne, comptes, clients actifs, alertes conformité, dossiers à revoir et lignes Q156.

### Recouvrement opérationnel

Objectif : aider les agents crédit à décider qui relancer et où récupérer une partie de l'impayé.

Sources de référence : 91, 100, 136, 143, 145, 146 et surtout 147.

Questions métier :

- quels clients ont des échéances impayées ;
- combien de jours de retard ;
- quel montant est en arriéré ;
- quel solde existe sur le compte ordinaire ou d'épargne ;
- quel montant est récupérable estimé ;
- quel reste impayé subsiste après récupération estimée ;
- quels remboursements ont été encaissés mais mal imputés.

Affichage recommandé : bloc dans `Risque crédit` ou page de détail `Recouvrement`, avec tableau exploitable par client, prêt, devise, impayé, solde disponible et action de suivi.

### Épargne mobilisable face au crédit

Objectif : rapprocher l'épargne disponible, les DAT et les crédits en cours sans compenser automatiquement les devises.

Sources de référence : 110, 113, 144, 147 et 157.

Questions métier :

- quels clients en crédit disposent aussi d'une épargne disponible ;
- quels clients ont un DAT sans crédit en cours ;
- quels DAT arrivent à échéance sur la période ;
- quels clients ont crédit à rembourser et solde positif dans la même devise ;
- quels cas nécessitent une analyse juridique ou opérationnelle avant récupération.

Règle : juxtaposer les positions sans assimilation automatique à une garantie et sans total nominal CDF + USD.

### Qualité transversale des données

Objectif : donner une vue consolidée des anomalies importantes des cycles crédit, épargne, clients et conformité.

Sources de référence : requêtes de niveau d'importance 9 ou 10, notamment 24 à 28, 49 à 55, 60, 68 à 83, 122, 136 à 142 et 155.

Questions métier :

- combien d'anomalies par cycle ;
- quelles anomalies sont critiques ;
- quels clients, comptes, prêts ou opérations sont concernés ;
- quel montant et quelle devise sont exposés ;
- quelle requête source justifie le cas ;
- quelles anomalies reviennent plusieurs mois de suite.

Affichage recommandé : page `Surveillance` enrichie ou page `Qualité des données`, avec sévérité, cycle, requête source, statut de traitement et référence audit.

### Suivi de traitement des anomalies

Objectif : passer de la détection à la gestion opérationnelle.

Prévoir, dans la couche de reporting ou dans un fichier de suivi gouverné, des champs de traitement :

- statut de traitement ;
- responsable ;
- date d'affectation ;
- date de justification ;
- action menée ;
- commentaire de clôture ;
- preuve ou référence interne.

Les statuts recommandés sont : `A_REVOIR`, `EN_COURS`, `JUSTIFIE`, `REGULARISE`, `NON_COUVERT`, `CLOS`.

Ne pas stocker ces statuts dans la base Perfect Vision du progiciel. Utiliser une table de reporting ou une source gouvernée distincte.

### Dictionnaire officiel des pages

Objectif : stabiliser la maintenance du rapport.

Pour chaque page Power BI, documenter :

- objectif métier ;
- audience ;
- questions couvertes ;
- tables de faits ;
- mesures principales ;
- dimensions et filtres obligatoires ;
- requêtes SQL de rapprochement ;
- niveau de détail attendu ;
- données personnelles exposées ;
- limites connues ;
- tests à refaire après modification.

Ce dictionnaire doit être mis à jour avant d'ajouter une nouvelle page ou de modifier une mesure partagée.

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
