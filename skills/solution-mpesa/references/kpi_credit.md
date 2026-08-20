# KPI Crédit - Solution Numérique

Ce référentiel décrit l'onglet `Crédits`. Il complète `Finance et comptabilité` sans créer un cockpit parallèle. L'objectif est de produire une lecture opérationnelle du portefeuille crédit, lisible par la Direction et les équipes terrain.

## Sources

- `Loans Account [Solution Numérique]` : source principale de l'encours crédit à la date de situation. Il fournit les prêts, montants accordés, soldes, montants payés, intérêts, frais, pénalités, statuts, échéances et champs `defaulted`, `is_rollover`, `is_grace_period`.
- `Transactions [Solution Numérique]` : source des flux observés sur la période : décaissements, remboursements, intérêts et pénalités. Les calculs se font au grain d'événement métier consolidé, jamais au grain de ligne brute.
- `Savings Account [Solution Numérique]` : source utilisée seulement pour mettre en regard crédit, compte ouvert et DAT par client/devise. L'épargne n'est jamais compensée avec le crédit et n'est jamais appelée garantie sans preuve contractuelle.
- `Rapports G2 M-Pesa` : source facultative de contrôle et d'enrichissement d'identité. G2 ne calcule ni l'encours, ni les montants de prêt, ni les remboursements.

## KPI implémentés

| KPI | Définition | Formule | Source | Grain | Devise | Type | Statut | Limite |
|---|---|---|---|---|---|---|---|---|
| portefeuille_credit | Position actuelle du portefeuille crédit. | Agrégats de `loan_amount`, `loan_balance`, `amount_paid`, `outstanding_*`. | Loans Account | prêt x devise | oui | position | implémenté | Instantané actuel, pas historique. |
| par_simplifie_1j_7j_30j_90j_180j | Encours dont `due_date` est dépassée selon le seuil. | Encours en retard n jours / encours actif total. | Loans Account | prêt x devise | oui | risque | implémenté | Simplifié; ne remplace pas un PAR réglementaire détaillé issu d'un échéancier. |
| niveau_risque_credit | Classe exclusive du prêt pour éviter le double comptage. | `Sain`, `PAR1`, `PAR7`, `PAR30`, `PAR90`, `PAR180`, `Echeance_non_renseignee`. | Loans Account | prêt | oui | risque | implémenté | Classe de lecture opérationnelle. |
| production_credit | Décaissements observés sur la période. | Événements consolidés de décaissement. | Transactions | événement x devise | oui | flux | implémenté | Flux observé, pas encours historique. |
| remboursements_observes | Remboursements détectés dans Transactions. | Événements consolidés de remboursement. | Transactions | événement x devise | oui | flux | implémenté | Ne fournit pas le montant exigible. |
| echeances_maturite | Maturité du prêt depuis `due_date`. | `Echu`, `Aujourd_hui`, `0_7_jours`, `8_30_jours`, `31_60_jours`, `61_90_jours`, `Plus_90_jours`, `Non_renseignee`. | Loans Account | prêt x devise | oui | suivi | implémenté | Ce n'est pas un échéancier détaillé. |
| concentration_credit | Concentration par client et par tranche d'encours. | Part client / encours de la devise, rang et part cumulée. | Loans Account | client x devise | oui | risque | implémenté | Ne jamais mélanger CDF et USD. |
| cohortes_a_date | Lecture par mois de création du prêt. | Nombre, montant initial, encours, défauts et PAR30 observés. | Loans Account | cohorte x devise | oui | analyse | implémenté | Cohorte à date, pas vraie vintage historique. |
| credit_epargne_observee | Juxtaposition crédit, compte ouvert et DAT. | Encours crédit vs épargne observée par client/devise. | Loans + Savings | client x devise | oui | rapprochement | implémenté | Analyse, pas garantie ni compensation. |

## KPI en data gap

Ces indicateurs ne doivent pas être forcés tant qu'une source fiable n'est pas disponible :

- PAR réglementaire détaillé par échéance;
- aging détaillé issu d'un plan d'amortissement complet;
- provision réglementaire;
- garantie/caution/sûreté documentée;
- collection efficiency basée sur le montant exigible;
- radiation/write-off;
- restructuration confirmée;
- coût du risque;
- rendement sur encours moyen.

## Règles d'interface

- Organiser l'onglet en six blocs : `Vue d'ensemble`, `Production et remboursements`, `Portefeuille et échéances`, `Risques et concentration`, `Crédit et épargne`, `Opportunités et qualité`.
- Cette organisation remplace l'ancien découpage en nombreux sous-onglets. Conserver les analyses de production, portefeuille, remboursements, risque, échéances, concentration, crédit/épargne, cohortes, opportunités et qualité, mais les regrouper pour réduire la navigation.
- Dans `Risques et concentration`, conserver le classement des prêts et des clients, puis ajouter une synthèse par `tranche_encours` client pour lire les niveaux d'exposition.
- Prioriser les `multiselect` pour les filtres de devise, statut, produit, client, téléphone, échéance, tranche et liste d'action.
- Conserver les `selectbox` uniquement pour les choix exclusifs : fréquence, mode d'affichage, horizon ou indicateur graphique unique.
- Afficher une aide claire sur le PAR simplifié : il est construit depuis `due_date` et ne remplace pas un plan d'amortissement détaillé.

## Export Excel du cockpit Crédits

L'export opérationnel doit privilégier les feuilles suivantes :

| Feuille | Rôle |
|---|---|
| `Credit_Synthese` | Vue de décision par devise : nombre de crédits, emprunteurs, encours, remboursements, production de la période et PAR. |
| `Credit_Flux_Periode` | Flux observés sur la période depuis `Transactions` : nouveaux crédits et remboursements par date/devise. |
| `Credit_Portefeuille` | Liste propre des crédits à la date de situation, sans doublon d'encours comme `encours_credit_2`. |
| `Credit_Risque_PAR` | PAR 1/7/30/90/180 par devise, avec montants, nombres de crédits, clients concernés et taux. |
| `Credit_Echeances` | Crédits échus ou à échéance proche par tranche d'horizon. |
| `Credit_Concentration` | Clients les plus exposés par devise, rang, part et tranche d'encours. |
| `Credit_Tranches_Clients` | Répartition des clients par tranche d'encours et niveau de risque. |
| `Credit_Cohortes` | Lecture par cohorte de création des prêts. |
| `Credit_Clients_360` | Vue client x devise rapprochant crédit, compte ouvert et DAT. |
| `Credit_Actions` | Liste consolidée des actions à suivre : échus, PAR30+, pénalités, défauts, fortes expositions, échéances proches. |
| `Credit_Qualite` | Contrôles qualité et limites des sources. |

Toutes ces feuilles doivent commencer par `date_situation`. Toute feuille contenant un nom client doit afficher `numero_client` à côté du nom. Les champs `defaulted` et `is_rollover` doivent rester distincts dans le traitement métier : `defaulted` devient `pret_en_defaut`, `is_rollover` devient `pret_renouvele`.
