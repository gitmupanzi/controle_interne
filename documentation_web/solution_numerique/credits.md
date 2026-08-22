# Solution Numérique — Crédits

Le cockpit `Crédits` pilote le portefeuille crédit, les remboursements observés, les échéances, le risque et les opportunités de suivi. Il est conçu comme un outil opérationnel : peu de feuilles, colonnes utiles, lecture par devise et actions directement exploitables.

## Sources utilisées

| Source | Rôle |
|---|---|
| `Loans Account` | Source principale de l'encours crédit actuel : prêts, encours, statuts, échéances, défauts, renouvellements, périodes de grâce, intérêts, frais et pénalités. |
| `Transactions` | Source des flux observés sur la période : décaissements, remboursements, intérêts et pénalités détectables. |
| `Savings Account` | Mise en regard analytique entre crédit, compte ouvert et DAT. |
| `G2` | Source facultative d'identité ou de contrôle ; elle ne modifie pas les montants crédit. |

## Principe de lecture

Deux lectures doivent rester séparées :

- `Loans Account` donne le stock à la date de situation : encours, statut, échéance, intérêts, frais et pénalités.
- `Transactions` donne les flux de la période : nouveaux crédits et remboursements observés.

Un remboursement observé dans `Transactions` ne doit pas être mélangé avec l'encours instantané de `Loans Account` sans rappeler qu'il s'agit de deux grains différents. Les montants restent toujours séparés par devise : un prêt USD et un prêt CDF ne doivent pas être additionnés dans une même valeur monétaire globale.

## Analyses principales

Le cockpit Crédits mesure :

- les crédits actifs et l'encours par devise ;
- les nouveaux crédits et remboursements observés sur la période ;
- les échéances et crédits échus ;
- le PAR simplifié `1/7/30/90/180` à partir de `due_date` ;
- les crédits en retard à la date d'analyse ;
- l'encours crédit en retard, c'est-à-dire l'encours des crédits ayant au moins un jour de retard ;
- le taux de portefeuille à risque PAR 30, calculé comme l'encours en retard de 30 jours ou plus divisé par l'encours crédit total de la devise ;
- le niveau de risque exclusif par prêt : `Sain`, `PAR1`, `PAR7`, `PAR30`, `PAR90`, `PAR180`, `Echeance_non_renseignee` ;
- les crédits avec pénalités, défaut observé ou renouvellement ;
- la concentration par client et par tranche d'encours ;
- le rapprochement crédit / épargne lorsque `savings_account_id` ou le couple `customer_id + currency_code` le permet.

## Volets de l'interface

| Volet | Contenu principal |
|---|---|
| `Vue d'ensemble` | KPI du portefeuille crédit par devise. |
| `Production et remboursements` | Décaissements et remboursements observés sur la période. |
| `Portefeuille et échéances` | Position crédit, échéances, maturité et cohortes à date. |
| `Risques et concentration` | PAR simplifié, prêts à surveiller, top expositions et concentration. |
| `Crédit et épargne` | Rapprochement analytique crédit, compte ouvert et DAT. |
| `Opportunités et qualité` | Opportunités crédit, contrôles qualité, KPI non calculables et limites. |

## Feuilles clés du cockpit Excel Crédits

Pour rendre le cockpit partageable avec la Direction et les équipes opérationnelles, l'export Excel privilégie les feuilles ci-dessous. Elles écartent les colonnes purement techniques : fichiers sources, clés internes inutiles à l'action, colonnes brutes, ordres d'import et traces de calcul.

| Priorité | Feuille | Lecture recommandée |
|---:|---|---|
| 1 | `Credit_Synthese` | Vue de décision par devise : crédits, emprunteurs, encours, production de la période, remboursements et PAR. |
| 2 | `Credit_Portefeuille` | Liste propre des crédits à la date de situation avec client, numéro, produit, devise, encours, échéance et niveau de risque. |
| 3 | `Credit_Risque_PAR` | PAR 1/7/30/90/180 par devise, avec montants, nombres de crédits, clients concernés et taux. |
| 4 | `Credit_Actions` | Liste consolidée des actions à suivre : échus, PAR30+, pénalités, défauts, fortes expositions et échéances proches. |
| 5 | `Credit_Clients_360` | Vue client x devise rapprochant crédit, compte ouvert et DAT, sans compensation comptable. |
| 6 | `Credit_Concentration` | Clients les plus exposés, rang, part d'encours, part cumulée et tranche d'encours. |
| 7 | `Credit_Echeances` | Crédits échus ou arrivant bientôt à échéance. |
| 8 | `Credit_Tranches_Clients` | Répartition des clients par tranche d'encours et niveau de risque. |
| 9 | `Credit_Flux_Periode` | Flux journaliers ou périodiques de nouveaux crédits et remboursements depuis `Transactions`. |
| 10 | `Credit_Cohortes` | Lecture par cohorte de création des prêts. |
| 11 | `Credit_Qualite` | Contrôles qualité et limites des sources. |

Lecture Direction : commencer par `Credit_Synthese`, `Credit_Risque_PAR`, `Credit_Portefeuille`, `Credit_Actions` et `Credit_Clients_360`. Les feuilles de concentration, échéances et cohortes approfondissent l'analyse. Les anciens détails techniques restent réservés au diagnostic et ne doivent pas être le cœur du cockpit partagé.

## Colonnes importantes

Toutes les feuilles du cockpit doivent commencer par `date_situation`. Toute feuille contenant `nom_client` doit aussi contenir `numero_client` à côté du nom pour permettre aux opérations de retrouver ou contacter le client.

Dans le portefeuille crédit, les colonnes prioritaires sont :

`date_situation`, `id_client`, `numero_client`, `nom_client`, `numero_pret`, `produit_credit`, `devise`, `montant_credit`, `montant_deja_rembourse`, `encours_credit`, `capital_restant_du`, `frais_dossier_restants`, `interets_restants`, `penalites_restantes`, `statut_credit`, `pret_actif`, `date_echeance`, `jours_retard`, `niveau_risque`, `date_dernier_remboursement`, `pret_en_defaut`, `pret_renouvele`, `periode_grace`, `created_at`, `updated_at`, `tranche_encours`.

La colonne `encours_credit_2` ne doit pas être exposée dans l'export opérationnel. S'il existe plusieurs sources d'encours, la solution doit choisir l'encours métier retenu et documenter la limite dans `Credit_Qualite`.

## À retenir

- `Loans Account` est l'instantané du portefeuille crédit.
- Les remboursements de période viennent des événements consolidés de `Transactions`.
- Le PAR 1/7/30/90/180 est un PAR simplifié construit depuis `due_date`.
- `defaulted` et `is_rollover` restent distincts : le premier devient `pret_en_defaut`, le second `pret_renouvele`.
- L'épargne est mise en regard du crédit pour l'analyse, mais elle n'est pas compensée avec l'encours crédit sans preuve contractuelle.
