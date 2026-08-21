# Solution Numérique — Analyse des risques

L'onglet `Analyse des risques` donne une lecture transversale du portefeuille numérique : crédits, comptes ouverts, comptes bloqués/DAT, couverture par client, liquidité, rentabilité estimée, concentration et qualité des données.

Cette analyse ne remplace pas les cockpits `Épargnes` et `Crédits`. Elle les relie pour aider la Direction et les opérations à répondre à une question simple : **quels clients, produits ou devises demandent une attention particulière ?**

Point important : cet onglet reste un outil de **constat**. Il ne valide pas un crédit, n'invalide pas un client et ne remplace pas la revue humaine. Il aide seulement à lire les signaux disponibles dans les fichiers chargés.

## Sources utilisées

| Source | Rôle dans l'analyse |
|---|---|
| `Loans Account` | Source de l'encours crédit, du montant accordé, du montant payé, des frais, intérêts, pénalités, échéances et statuts. |
| `Savings Account` | Source des comptes ouverts, DAT, soldes, dates d'activation, dates d'échéance et intérêts constatés lorsque disponibles. |
| `Transactions` | Non obligatoire pour l'analyse de stock. Les flux restent traités dans les onglets `Finance et comptabilité`, `Épargnes`, `Crédits` et `Solution Numérique / M-Pesa`. |
| `G2` | Facultatif. Il enrichit l'identité ou le contrôle dans les autres onglets, mais ne calcule aucun montant de risque. |

Règle de base : **aucun montant USD et CDF n'est additionné**. Les indicateurs monétaires restent toujours séparés par devise.

## Date de lecture des encours

Les ratios d'encours se calculent à la **date de situation**, c'est-à-dire la date de fin ou date d'arrêté choisie dans l'onglet.

La lecture est une photographie de stock :

- `Loans Account` donne l'encours crédit observé à la date de situation ;
- `Savings Account` donne les soldes des comptes ouverts et des DAT à la date de situation ;
- `Transactions` sert aux flux de période dans les autres analyses, mais ne pilote pas ces ratios de stock.

Si la période analysée va du 01/08/2026 au 19/08/2026, ces ratios lisent donc la position arrêtée au 19/08/2026. Pour une précision comptable parfaite, les fichiers `Loans Account` et `Savings Account` doivent être extraits à cette date ou contenir les dates nécessaires pour filtrer correctement jusqu'à cette date.

## Paramètres financiers

Les paramètres visibles dans l'onglet permettent de rendre les hypothèses explicites :

| Paramètre | Valeur par défaut | Lecture |
|---|---:|---|
| DAT - part client annuelle | 11 % | Part annuelle estimée revenant au client. |
| DAT - part Vodacom annuelle | 3 % | Part annuelle estimée revenant à Vodacom. |
| Crédit - part IMF mensuelle | 5 % | Part économique estimée pour IMF Bisou Bisou lorsque le client rembourse. |
| Crédit - part Vodacom mensuelle | 2 % | Part économique estimée pour Vodacom lorsque le client rembourse. |
| Crédit - taux total mensuel | 7 % | Taux total mensuel connu du crédit numérique. |

Le DAT est annualisé sur 365 jours. Pour le crédit, le taux de 7 % est traité comme un taux mensuel. Lorsque `interest_earned` est disponible dans `Loans Account`, l'analyse conserve cette valeur observée. Lorsqu'il manque, l'estimation utilise la durée du crédit en mois (`repayment_period`, `repayment_installments`, `repayment_period_unit`, ou à défaut l'écart entre `created_at` et `due_date`). Les indicateurs de marge restent des **estimations prudentes**, car une marge comptable définitive exige aussi la méthode exacte de calcul des intérêts et l'encours moyen.

## Deux ratios à ne pas confondre

L'analyse affiche deux lectures complémentaires :

| Ratio | Formule | Question à laquelle il répond |
|---|---|---|
| Couverture crédit par l'épargne | `épargne totale / encours crédit * 100` | Dans quelle mesure l'épargne observée peut-elle couvrir le crédit ? |
| Taux crédit / épargne | `encours crédit / épargne totale * 100` | Quelle part de l'épargne observée est transformée ou utilisée en encours crédit ? |
| Couverture DAT / crédit | `DAT bloqué / encours crédit * 100` | Le compte bloqué couvre-t-il le crédit observé ? |
| Taux crédit / DAT | `encours crédit / DAT bloqué * 100` | Le crédit dépasse-t-il le DAT disponible ? |

Exemple : si une devise présente 100 millions d'encours crédit et 200 millions d'épargne totale, le taux crédit / épargne est de 50 %. Si le taux dépasse 100 %, l'encours crédit dépasse l'épargne observée dans la même devise.

Pour la logique opérationnelle d'octroi numérique, la lecture `DAT / crédit` est plus stricte que la lecture par épargne totale. Un compte ouvert peut améliorer la position financière globale, mais le DAT doit être isolé lorsque la règle métier demande qu'un crédit soit couvert à hauteur du compte bloqué.

## Lecture par client

Le grain principal est :

```text
client numerique + devise
```

Dans la pratique, le client numérique est rapproché par `customer_id` (identifiant client) et par le numéro de téléphone disponible (`msisdn1`, `msisdn` ou numéro client). Le tableau `Risque_clients` rapproche :

- compte ouvert ;
- compte bloqué/DAT ;
- épargne totale ;
- encours crédit ;
- couverture crédit par l'épargne ;
- couverture crédit par le DAT seul ;
- exposition nette ;
- exposition nette DAT ;
- score de risque ;
- motifs de risque.

Pour faciliter la lecture opérationnelle, le tableau ajoute aussi des colonnes de synthèse :

| Colonne | Lecture |
|---|---|
| `numero_client` | Numéro client lisible sur le terrain, alimenté par le téléphone lorsque disponible, avec repli sur l'identifiant client. |
| `segment_observe` | Profil principal observé : crédit avec DAT, crédit sans épargne, DAT sans crédit actif, retard, etc. |
| `niveau_observation` | Priorité de revue : observation standard, opportunité commerciale prudente, revue recommandée ou suivi prioritaire. |
| `lecture_observee` | Commentaire court expliquant pourquoi la ligne mérite ou non une attention particulière. |
| `signaux_positifs` | Codes des éléments favorables observés : compte ouvert positif, DAT positif, crédit actif, remboursement observé, couverture confortable. |
| `signaux_attention` | Codes des points à surveiller : retard, crédit sans épargne, crédit supérieur à l'épargne, DAT proche de l'échéance, marge estimée négative. |

## Colonnes affichées et exportées

Les tableaux de l'onglet et le cockpit Excel `Analyse des risques` sont préparés pour une lecture opérationnelle. Les colonnes techniques ou redondantes ne doivent pas alourdir la lecture : par exemple `id_client` est masqué lorsque `numero_client` suffit, `telephone` est masqué lorsque le numéro client est déjà affiché, et les colonnes de contrôle technique comme `type_controle`, fichiers sources ou traces de debug restent internes.

Les noms de colonnes sont explicites, en français `snake_case`, sans accents. Les notions ambiguës sont clarifiées :

| Colonne technique interne | Nom opérationnel |
|---|---|
| `epargne_disponible` ou `epargne_courante` | `compte_ouvert` |
| `dat_bloque` | `encours_dat` |
| `couverture_credit_pct` ou `couverture_globale_pct` | `couverture_epargne_totale_credit_pct` |
| `taux_utilisation_epargne_credit_pct` | `taux_credit_epargne_totale_pct` |
| `exposition_nette` | `credit_non_couvert_compte_ouvert` |
| `exposition_nette_dat` | `credit_non_couvert_dat` |

## Indicateurs calculés

| Bloc | Indicateurs principaux | Utilité |
|---|---|---|
| Vue globale | Encours crédit, épargne totale, DAT, couverture globale, taux crédit / épargne, exposition nette, PAR 30, marge estimée | Donner une lecture rapide par devise. |
| Lecture clients | Couverture client, couverture DAT, taux crédit / épargne, taux crédit / DAT, exposition nette, segment observé, niveau d'observation, signaux positifs et signaux d'attention | Prioriser la revue humaine sans automatiser la décision. |
| Crédit | PAR 1/7/30/60/90, encours en retard, produit crédit estimé | Suivre la qualité du portefeuille crédit. |
| DAT | Encours DAT, coût client, part Vodacom, échéances à 7/30/90 jours | Préparer les sorties de trésorerie liées aux DAT. |
| Liquidité | Entrées attendues crédit, sorties DAT, gap de liquidité par horizon | Anticiper les tensions de trésorerie. |
| Rentabilité | Produit crédit IMF mensuel estimé, coût DAT estimé, marge financière estimée | Comprendre si le portefeuille produit assez pour couvrir le coût estimé des DAT. |
| Concentration | Top 5/10/20 et HHI par devise | Repérer la dépendance à quelques gros clients. |
| Alertes | Situations à revoir | Orienter l'action opérationnelle. |
| Qualité | Doublons, clients manquants, dates invalides, limites métier | Ne pas partager une analyse fragile sans prudence. |

## Principales alertes

| Alerte | Sens |
|---|---|
| `credit_sans_epargne` | Le client a un encours crédit mais aucune épargne observée dans la même devise. |
| `credit_superieur_epargne` | L'encours crédit dépasse l'épargne totale observée. |
| `couverture_insuffisante` | La couverture par l'épargne est faible ou absente. |
| `client_fortement_expose` | Le client fait partie des plus fortes expositions de la devise. |
| `retard_credit` | Le crédit est en retard selon le PAR simplifié. |
| `dat_echeance_proche` | Un DAT arrive bientôt à échéance. |
| `dat_sans_credit` | Le client a un DAT positif sans crédit actif observé. |
| `marge_negative` | La marge estimée est négative selon les paramètres saisis. |
| `gap_liquidite_negatif` | Les sorties DAT estimées dépassent les entrées attendues du crédit sur un horizon donné. |

## Export Excel

L'export Excel est généré uniquement après clic sur `Préparer l'export Excel Risques`. Les feuilles prévues sont :

| Feuille | Contenu |
|---|---|
| `Synthese_risque` | Indicateurs globaux par devise. |
| `Risque_clients` | Lecture client par client et par devise. |
| `Risque_credit` | Synthèse du risque crédit et PAR. |
| `Risque_DAT` | Synthèse des DAT et coûts estimés. |
| `Liquidite` | Horizons et gaps de liquidité. |
| `Rentabilite` | Marge estimée par devise. |
| `Concentration` | Top expositions et HHI. |
| `Alertes` | Lignes à examiner. |
| `Qualite_donnees` | Contrôles qualité. |
| `Parametres`, `Data_gaps`, `Audit` | Hypothèses, limites et audit des briques existantes. |

Chaque feuille garde `date_situation` en première colonne lorsque cela s'applique, afin de rappeler la date d'arrêté.

## Limites à garder en tête

- Le DAT peut couvrir économiquement un crédit, mais il n'est pas automatiquement mobilisable comme garantie sans règle métier validée.
- Comparer le coût DAT annuel et le produit crédit mensuel exige une même période économique. Le taux mensuel du crédit est documenté, mais la marge reste une estimation tant que l'encours moyen et la méthode exacte de calcul des intérêts ne sont pas entièrement confirmés.
- G2 ne remplace jamais `Loans Account` ou `Savings Account` pour les montants.
- Une alerte n'est pas une erreur certaine : c'est un signal de revue humaine.
