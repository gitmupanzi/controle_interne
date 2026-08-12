# Requêtes, cycles et KPI Perfect Vision

## Catalogue SQL

Le fichier `data/modelisation/requetes.sql` documente les requêtes avec :

- numéro ;
- export attendu ;
- objectif ;
- lecture métier ;
- niveau d'importance.

L'audit du catalogue montre des requêtes de niveau 9 et 10, donc prioritaires pour le contrôle interne et le reporting.

Pour consulter la liste complète et commentée des requêtes prioritaires, utiliser la page [Requêtes prioritaires 9 et 10](requetes_prioritaires.md). Elle présente les requêtes par cycle, avec une lecture simple pour les décideurs et les équipes métier.

## Cycles fortement représentés

| Cycle | Exemples de contrôles |
|---|---|
| Opérations dépôt/retrait | validation, dates, doublons, annulations, auto-validation |
| Comptable et financier | équilibre débit/crédit, rapprochement HDPM/HDPM_API, mouvements sans compte |
| Crédit | portefeuille, PAR, échéances, remboursements, top encours, garanties, décaissements |
| Épargne | mouvements, gros dépôts, comptes clôturés/inactifs, produits |
| CRM clients | doublons, données essentielles, comptes clients |
| Conformité | alertes, qualité KYC, clients et comptes |

## Où lire les requêtes par cockpit

Les requêtes utiles aux cockpits sont maintenant rangées dans chaque cycle :

| Besoin | Page à consulter |
|---|---|
| Cockpit Clients | [Cycle client](cycle_client.md) |
| Cockpit Épargnes | [Cycle épargne](cycle_epargne.md) |
| Cockpit Crédits | [Cycle crédit](cycle_credit.md) |
| Reporting réglementaire et LBC-FT | [Conformité](cycle_conformite.md) |

Cette organisation évite de mélanger les sujets. Le lecteur qui travaille sur les clients lit le cycle client ; celui qui prépare l'épargne lit le cycle épargne ; celui qui suit le portefeuille crédit lit le cycle crédit.

## Exemples de requêtes critiques

| Export | Objectif |
|---|---|
| `05_cycle_operations_depot_retrait_operations_validees_avant_la_saisie_ou_avant_la_date_d_operation` | Identifier les incohérences chronologiques |
| `14_cycle_comptable_et_financier_equilibre_debit_credit_par_operation_dans_hdpm` | Contrôler l'équilibre débit/crédit |
| `21_cycle_comptable_et_financier_rapprochement_des_totaux_hdpm_vs_hdpm_api_par_reference_operation` | Rapprocher les totaux HDPM et HDPM_API |
| `57_cycle_epargne_analyse_des_gros_mouvements_par_periode` | Suivre les gros mouvements par période |
| `96_cycle_credit_dashboard_par_details_credit_a_la_date_de_fin` | Alimenter les pages crédit du dashboard |
| `146_cycle_credit_liste_detaillee_des_clients_avec_echeances_sur_la_periode` | Restituer les échéances crédit sur une période |

## KPI

Les KPI Perfect Vision doivent rester attachés à leur requête SQL ou à leur vue source. Lorsqu'un KPI est repris dans Power BI, la documentation Power BI doit indiquer la table de reporting et la mesure DAX correspondante.
