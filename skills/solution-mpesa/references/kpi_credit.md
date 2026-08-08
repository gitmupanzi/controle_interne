# KPI Crédit - Solution Numérique

Ce référentiel décrit l'onglet `Crédits`. Il complète `Finance et comptabilité` sans créer un cockpit parallèle.

## Sources

- `Loans Account [Solution Numérique]` : instantané actuel du portefeuille crédit, des statuts, encours, dates d'échéance et champs de suivi disponibles.
- `Transactions [Solution Numérique]` : flux observés de décaissements, remboursements, intérêts et pénalités. Les calculs se font au grain d'événement métier consolidé, jamais au grain de ligne brute.
- `Savings Account [Solution Numérique]` : rapprochement analytique crédit/compte ouvert/DAT. L'épargne est juxtaposée au crédit; elle n'est jamais compensée ni appelée garantie sans preuve contractuelle.
- `Rapports G2 M-Pesa` : contrôle facultatif du versement et enrichissement d'identité. G2 ne calcule ni l'encours, ni les montants de prêt, ni les remboursements.

## KPI implémentés

| kpi | definition | formule | source | grain | devise | type_mesure | statut | limite |
|---|---|---|---|---|---|---|---|---|
| portefeuille_credit | Position actuelle du portefeuille. | Agrégats de `loan_amount`, `loan_balance`, `amount_paid`, `outstanding_*`. | Loans Account | prêt x devise | oui | position | implemente | Instantané actuel, pas historique. |
| par_simplifie_1j_7j_30j | Encours dont `due_date` est dépassée selon le seuil. | Encours en retard n jours / encours total. | Loans Account | prêt x devise | oui | risque | implemente | Simplifié; ne remplace pas un PAR réglementaire détaillé. |
| production_credit | Décaissements observés sur la période. | Événements consolidés de décaissement. | Transactions | événement x devise | oui | flux | implemente | Flux observé, pas encours historique. |
| remboursements_observes | Remboursements détectés dans Transactions. | Événements consolidés de remboursement. | Transactions | événement x devise | oui | flux | implemente | Ne fournit pas le montant exigible. |
| echeances_maturite | Maturité du prêt depuis `due_date`. | Échu, aujourd'hui, 0-7, 8-30, 31-60, 61-90, >90 jours. | Loans Account | prêt x devise | oui | suivi | implemente | Ce n'est pas un échéancier détaillé. |
| concentration_credit | Concentration par prêt, client, produit et tranche. | Part des top expositions / encours de la devise. | Loans Account | devise | oui | risque | implemente | Ne jamais mélanger CDF et USD. |
| cohortes_a_date | Lecture par mois de création du prêt. | Nombre, montant initial, encours, défauts observés. | Loans Account | cohorte x devise | oui | analyse | implemente | Cohorte à date, pas vraie vintage historique. |
| credit_epargne_observee | Juxtaposition crédit, compte ouvert et DAT. | Encours crédit vs épargne observée par client/devise. | Loans + Savings | client x devise | oui | rapprochement | implemente | Analyse, pas garantie ni compensation. |

## KPI en data gap

Ces indicateurs ne doivent pas être forcés tant qu'une source fiable n'est pas disponible :

- PAR réglementaire détaillé;
- PAR90/PAR180 exacts;
- aging détaillé par échéance;
- provision réglementaire;
- garantie/caution/sûreté;
- collection efficiency basé sur le montant exigible;
- radiation/write-off;
- restructuration;
- coût du risque;
- rendement sur encours moyen.

## Règles d'interface

- Organiser l'onglet en blocs : `Vue d'ensemble`, `Production`, `Portefeuille actuel`, `Remboursements`, `Risque simplifié`, `Échéances`, `Concentration`, `Crédit et épargne`, `Cohortes à date`, `Listes d'action`, `Qualité des données`.
- Prioriser les `multiselect` pour les filtres de devise, statut, produit, client, téléphone, échéance, tranche et liste d'action.
- Conserver les `selectbox` uniquement pour les choix exclusifs : fréquence, mode d'affichage, horizon ou indicateur graphique unique.
- Afficher une aide claire sur le PAR simplifié : il est construit depuis `due_date` et ne remplace pas un plan d'amortissement détaillé.

