# Dictionnaire KPI — Solution M-PESA

Ce dictionnaire décrit les indicateurs utilisés dans la Solution M-PESA après le refactoring métier. Dans l'interface, `Solution Numérique` désigne l'ancienne source opérationnelle `Turbo`. Le terme `Turbo` reste conservé dans certains noms techniques, colonnes, clés Streamlit et feuilles Excel historiques. `G2` désigne le rapport de contrôle du canal M-Pesa; il enrichit ou rapproche les écritures, mais ne pilote pas les montants.

Règle permanente : les montants CDF et USD sont toujours calculés et restitués séparément. Les nombres de clients ou d'opérations peuvent être consolidés, mais aucun montant monétaire n'est additionné entre devises.

## Sources

| Priorité | Fichier | Statut | Rôle analytique |
|---:|---|---|---|
| 1 | Transactions [Solution Numérique] | Indispensable | Mouvements, dépôts, retraits, remboursements, crédits décaissés, chiffre d'affaires observé, activité dans le temps |
| 2 | Savings Account [Solution Numérique] | Indispensable | Comptes ouverts, comptes bloqués DAT, soldes d'épargne, échéances DAT, intérêts DAT estimés ou constatés |
| 3 | Loans Account [Solution Numérique] | Très important | Crédits accordés, encours, échéances à venir, impayés, portefeuille crédit |
| 4 | Customers [Solution Numérique] | Important | Clients connus, créations de clients, ancienneté de la base client |
| 5 | Rapports G2 [M-Pesa] | Facultatif utile | Nom client, reçu M-Pesa, statut, rapprochement et preuve de contrôle; pas de calcul des montants |
| 6 | Clients_Perfect | Facultatif analytique | Adoption Perfect, croisement téléphonique et qualité de présence intersystèmes |

## Clients

| KPI | Définition | Formule / logique | Source | Devise |
|---|---|---|---|---|
| Clients du fichier Customers chargé | Nombre total de lignes clients exploitables dans le fichier Customers chargé, avant restriction à la date de fin | `count(Customers.msisdn1)` après normalisation et déduplication contractuelle | Customers | Non monétaire |
| Clients connus à la date de fin | Clients dont la date de création est inférieure ou égale à la date de fin filtrée | `count_distinct(client)` avec `created_at <= date_fin` | Customers, repli Savings/Transactions si nécessaire | Non monétaire |
| Clients actifs | Clients ayant au moins une opération Solution Numérique sur la période filtrée | `count_distinct(customer_id ou msisdn)` dans Transactions filtrées | Transactions | Non monétaire |
| Nouveaux clients | Clients créés entre Date de début et Date de fin | `count_distinct(client)` avec `created_at` dans la période | Customers | Non monétaire |

## Comptes ouverts et comptes bloqués

| KPI | Définition | Formule / logique | Source | Devise |
|---|---|---|---|---|
| Comptes ouverts | Comptes `NORMAL SAVINGS` observés dans Savings Account | `count_distinct(savings_id)` par devise et statut si disponible | Savings Account | CDF/USD séparés pour les soldes |
| Solde compte ouvert | Solde courant du compte ouvert | `sum(balance)` des comptes `NORMAL SAVINGS`, séparé par `currency_code` | Savings Account | CDF/USD séparés |
| Comptes bloqués DAT | Comptes `FIXED SAVINGS` observés dans Savings Account | `count_distinct(savings_id)` | Savings Account | CDF/USD séparés pour les soldes |
| Solde compte bloqué | Capital bloqué disponible sur DAT | `sum(balance)` des comptes `FIXED SAVINGS` à solde positif | Savings Account | CDF/USD séparés |
| DAT échus ou proches | DAT arrivés à échéance ou arrivant bientôt à terme | `maturity_date - date_situation` comparé à l'horizon choisi | Savings Account | CDF/USD séparés |
| Capital + intérêt estimé DAT | Estimation de préparation au remboursement | `capital × (1 + taux_annuel / 100 × durée_jours / 365)`; taux par défaut 11 % | Savings Account | CDF/USD séparés |

## Crédits

| KPI | Définition | Formule / logique | Source | Devise |
|---|---|---|---|---|
| Nouveaux crédits | Crédits créés ou décaissés sur la période | Transactions consolidées de décaissement, rapprochées si possible à Loans Account | Transactions, Loans Account | CDF/USD séparés |
| Montant brut accordé | Montant nominal du crédit accordé | `sum(loan_amount)` ou événement de décaissement brut selon le volet | Loans Account, Transactions | CDF/USD séparés |
| Net versé au client | Montant effectivement sorti vers le client après intérêt prélevé | `prêt_brut - intérêt_prélevé`; référence métier actuelle : 7 % | Transactions | CDF/USD séparés |
| Intérêt prélevé à l'octroi | Produit financier retenu lors du décaissement | `prêt_brut × 7 %`, contrôlé par les lignes `MPESA ACCOUNT` lorsque disponibles | Transactions | CDF/USD séparés |
| Remboursements observés | Paiements de crédit réellement observés sur la période | Somme des événements `Remboursement de credit` et `Remboursement avec penalite` | Transactions | CDF/USD séparés |
| Encours crédit | Dette restante à la date de situation | `loan_balance` ou `outstanding_*` selon disponibilité | Loans Account | CDF/USD séparés |
| PAR simplifié | Portefeuille à risque selon retard observable | Encours des crédits avec `due_date` dépassée, par tranche 1/7/30 jours | Loans Account | CDF/USD séparés |

## Transactions

| KPI | Définition | Formule / logique | Source | Devise |
|---|---|---|---|---|
| Opérations Solution Numérique | Nombre d'événements métier consolidés | Regroupement par `ref_no`, puis par `customer_id + devise + created_at` lorsque `ref_no` manque | Transactions | Non monétaire |
| Dépôts compte ouvert | Entrées sur épargne ouverte | Événements `Epargne depot` / `Depot normal` sur `NORMAL SAVINGS` | Transactions | CDF/USD séparés |
| Retraits compte ouvert | Sorties depuis épargne ouverte vers M-Pesa | Événements `Retrait Vers M-Pesa` regroupés sans double compter les lignes miroir | Transactions | CDF/USD séparés |
| Dépôts DAT | Mouvements vers compte bloqué | Événements `Sortie M-PESA_Turbo vers DAT`, confirmés par Savings Account si nécessaire | Transactions, Savings Account | CDF/USD séparés |
| Volume transactionnel observé | Volume brut des opérations suivies | Somme des montants d'événements selon la famille, sans mélanger devises | Transactions | CDF/USD séparés |
| Chiffre d'affaires observé | Produits financiers détectables | Intérêts et frais observables dans les écritures techniques, notamment intérêts crédit et pénalités | Transactions | CDF/USD séparés |
| Score dépôts/retraits | Intensité d'activité client sur la période | `nombre d'opérations dépôt/retrait ÷ nombre de jours de la période` | Transactions | Non monétaire |

## Rapprochement M-Pesa / Rapport G2

| KPI | Définition | Formule / logique | Source | Devise |
|---|---|---|---|---|
| Reçus G2 chargés | Nombre de reçus distincts du rapport M-Pesa | `count_distinct(Receipt No)` après déduplication | Rapport G2 | Non monétaire |
| Taux de rapprochement | Part des reçus G2 retrouvés dans la Solution Numérique | `reçus rapprochés ÷ reçus contrôlables` | Rapport G2 + Transactions | Non monétaire |
| Écarts de rapprochement | Lignes à vérifier | Téléphone, devise, montant, date, statut ou référence non conforme | Rapport G2 + Transactions | Non monétaire |

## Projections

| KPI | Définition | Formule / logique | Source | Devise |
|---|---|---|---|---|
| Prévision / projection | Estimation prudente sur horizon futur | Historique récent, saisonnalité hebdomadaire et bornes de tendance | Sources Solution Numérique | CDF/USD séparés pour les montants |
| MAE — Mean Absolute Error / erreur absolue moyenne | Erreur moyenne en unité réelle | Moyenne de `abs(observé - prédit)` sur un test rétrospectif | Série historique | Même unité que le KPI |
| WAPE — Weighted Absolute Percentage Error / erreur absolue pondérée en pourcentage | Erreur relative pondérée par le volume | `sum(abs(observé - prédit)) ÷ sum(abs(observé)) × 100` | Série historique | Pourcentage |
| Intervalle | Fourchette prudente de lecture | Borne basse et borne haute autour de la projection selon l'incertitude choisie | Série historique | Même unité que le KPI |

