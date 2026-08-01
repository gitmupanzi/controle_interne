# Prochaines étapes Power BI — IMF BB

État au 1er août 2026 : le modèle Power BI lit désormais les faits du data mart `BB_VISION_REPORTING`.
Le dernier chargement complet validé est le batch `26` pour la période `2026-06-01` à `2026-06-30`.

## 1. Validation visuelle dans Power BI Desktop

Objectif : confirmer que les pages restent lisibles et cohérentes après la bascule complète vers le reporting.

À faire :

1. Fermer puis rouvrir le projet PBIP.
2. Cliquer sur `Actualiser`.
3. Contrôler les pages dans cet ordre :
   - `Direction`
   - `Crédit`
   - `Risque crédit`
   - `Prévisions crédit`
   - `Épargne`
   - `Clients`
   - `Conformité`
   - `Surveillance`
4. Vérifier qu'aucun visuel ne montre `Corriger ceci`.
5. Vérifier que les segments `Période` et `Devise` filtrent correctement.
6. Vérifier que les cartes KPI restent lisibles, avec une taille de valeur proche de `15`.

## 2. Rapprochement final Power BI vs SQL

Objectif : verrouiller les chiffres visibles.

KPI à contrôler en priorité :

- encours CDF et USD ;
- prêts actifs ;
- PAR 7, PAR 30, PAR 60 ;
- taux PAR CDF et USD ;
- décaissements CDF et USD ;
- échéances futures ;
- épargne CDF et USD ;
- ratios crédits/dépôts CDF et USD ;
- exposition nette ;
- concentration top 10 % ;
- provisions.

Sources de validation :

- `data/kpi_perfect/reporting_sql/10_run_monthly_load.sql`
- `data/kpi_perfect/reporting_sql/12_validate_credit_core_june_2026.sql`
- `data/kpi_perfect/reporting_sql/15_validate_credit_flows_june_2026.sql`
- `data/kpi_perfect/reporting_sql/17_validate_epargne_soldes_june_2026.sql`
- `data/kpi_perfect/reporting_sql/19_validate_credit_analytics_june_2026.sql`

## 3. Optimisation SQL Server

Objectif : réduire le temps de chargement et d'actualisation.

À faire :

1. Mesurer la durée de `rpt.load_all_facts`.
2. Vérifier les index existants sur les tables `rpt.*`.
3. Ajouter ou ajuster les index sur :
   - dates de situation ;
   - mois ;
   - devise ;
   - agence ;
   - produit ;
   - numéro prêt lorsque le grain est prêt.
4. Relancer le batch mensuel et comparer les durées.

## 4. Paramétrage mensuel d'exploitation

Objectif : rendre le chargement répétable sans manipulations risquées.

À prévoir :

- garder `10_run_monthly_load.sql` comme script manuel de référence ;
- créer ensuite une procédure ou un job SQL Agent pour charger un mois donné ;
- documenter la convention :
  - `@id_devise_reporting = NULL` charge toutes les devises séparément ;
  - ne jamais consolider CDF et USD sans taux de change validé ;
  - charger d'abord en environnement local/test avant production.

## 5. Sécurité et publication

Objectif : préparer le passage à un usage institutionnel.

À faire :

1. Définir les rôles :
   - Direction ;
   - Crédit ;
   - Épargne ;
   - Conformité ;
   - Audit / contrôle interne.
2. Définir les règles RLS si l'accès doit être limité par agence, gestionnaire ou périmètre.
3. Préparer la passerelle Power BI vers SQL Server.
4. Tester le rafraîchissement planifié dans Power BI Service.
5. Documenter les droits d'export.

## 6. Gouvernance du data mart

Objectif : éviter que le tableau de bord devienne une boîte noire.

À maintenir :

- catalogue KPI ;
- statut de migration ;
- résultats de validation ;
- gaps fonctionnels ;
- scripts de chargement ;
- scripts de rapprochement ;
- règles de devise ;
- définitions métier des grains.

## 7. Prochains enrichissements métier

À traiter après stabilisation :

- mouvements détaillés d'épargne : dépôts, retraits, collecte nette ;
- DAT détaillés : échéances, intérêts, renouvellements ;
- comptabilité : produits, charges, résultat, liquidité prudentielle ;
- sécurité utilisateurs et RLS ;
- historique multi-mois plus long pour tendances.

## Règle de reprise rapide

Si le contexte de travail est perdu, reprendre ici :

1. Exécuter `10_run_monthly_load.sql`.
2. Exécuter les scripts de validation `12`, `15`, `17`, `19`.
3. Ouvrir le PBIP et actualiser.
4. Corriger uniquement les visuels en erreur ou les KPI non rapprochés.
