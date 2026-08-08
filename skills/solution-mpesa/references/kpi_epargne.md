# KPI Epargne - Solution Numerique

Ce referentiel decrit l'onglet `Epargnes`. Il transforme l'ancien affichage centre DAT en cockpit complet de pilotage de l'epargne, sans creer d'onglet parallele.

## Sources

- `Savings Account [Solution Numerique]` : source maitre de position actuelle pour les comptes ouverts `NORMAL SAVINGS`, les DAT `FIXED SAVINGS`, les soldes, statuts, produits et dates contractuelles.
- Les colonnes techniques d'interet `is_interest_calculated`, `last_interest_calculation_date` et `next_interest_calculation_date` sont conservees lorsqu'elles existent et affichees en francais comme `interet_calcule`, `date_dernier_calcul_interet` et `date_prochain_calcul_interet`.
- `Transactions [Solution Numerique]` : source des flux observes sur la periode : depots, retraits, transferts DAT, retours DAT et remboursements depuis compte ouvert.
- `Loans Account [Solution Numerique]` : source de controle pour identifier les DAT ou fortes epargnes sans credit actif.
- `Rapports G2 M-Pesa` : enrichissement d'identite et preuve de rapprochement uniquement; G2 ne modifie aucun montant d'epargne.

## Regles fondamentales

- Ne jamais melanger les devises. Tout montant, solde, flux, ratio de concentration et estimation est calcule par `currency_code`.
- `Savings Account` est un instantane. Il autorise l'encours actuel, la situation produit et les echeances DAT, mais pas une evolution historique du solde sans plusieurs snapshots dates.
- `Transactions` porte les flux historiques. Ne jamais compter les lignes comptables brutes comme operations clients; utiliser les evenements canoniques.
- Un compte actif sur la periode a au moins un mouvement observe. `status = active` n'est pas une preuve d'activite transactionnelle.
- L'inactivite produite par l'onglet est analytique (`actif`, `a_surveille`, `inactif_observe`, `historique_insuffisant`), pas une dormance reglementaire certifiee.
- Les opportunites commerciales (`DAT sans credit actif`, `forte epargne sans credit`) ne sont jamais des decisions d'eligibilite credit.

## Catalogue KPI

| kpi | definition | formule | source | grain | devise | type_mesure | statut | limite |
|---|---|---|---|---|---|---|---|---|
| encours_epargne_courante | Solde actuel des comptes ouverts. | Somme `balance` des `NORMAL SAVINGS`. | Savings Account | compte x devise | oui | stock_actuel | implemente | Position instantanee, pas historique. |
| encours_dat | Solde actuel des comptes bloques. | Somme `balance` des `FIXED SAVINGS`. | Savings Account | DAT x devise | oui | stock_actuel | implemente | Position instantanee. |
| comptes_courants | Nombre de comptes ouverts. | Nombre distinct de `savings_id` en `NORMAL SAVINGS`. | Savings Account | compte | oui | stock_actuel | implemente | Les comptes a solde nul sont conserves si la source complete est chargee. |
| dat_positifs | Nombre de DAT avec solde strictement positif. | `balance > 0` sur `FIXED SAVINGS`. | Savings Account | DAT | oui | stock_actuel | implemente | Les DAT nuls restent disponibles dans le detail historique. |
| clients_epargnants | Clients ayant au moins un compte ouvert ou DAT. | Nombre distinct de `customer_id`. | Savings Account | client x devise | oui | stock_actuel | implemente | Depend de la qualite de `customer_id`. |
| depots_periode | Depots observes sur la periode. | Evenements `Sortie M-PESA_Turbo vers epargne` + `Sortie M-PESA_Turbo vers DAT`. | Transactions | evenement x devise | oui | flux_periode | implemente | Flux observe, pas collecte externe certifiee. |
| retraits_periode | Retraits observes depuis le compte ouvert. | Evenements `Entree M-PESA_Turbo depuis epargne`. | Transactions | evenement x devise | oui | flux_periode | implemente | Les Loan Request G2 ne sont pas des retraits d'epargne. |
| remboursements_depuis_compte_ouvert | Remboursements de credit finances par le compte ouvert. | Somme `remboursement_compte_ouvert` des evenements de remboursement. | Transactions | evenement x devise | oui | flux_periode | implemente | Mouvement sortant du compte client, transfert interne pour l'institution. |
| flux_net_epargne_observe | Flux net observe sur les comptes d'epargne. | depots compte ouvert + depots DAT + retours DAT - retraits - remboursements depuis compte ouvert. | Transactions | periode x devise | oui | flux_periode | implemente | Ne pas confondre avec la collecte externe nette. |
| comptes_actifs_observes | Comptes lies a un client/devise ayant un mouvement observe. | Derniere operation observee <= seuil. | Transactions + Savings Account | compte | oui | flux_periode | implemente | Approximation au niveau client/devise si l'evenement ne porte pas `savings_id`. |
| nouveaux_comptes | Comptes crees dans la periode. | `date_creation_compte` dans la periode. | Savings Account | compte | oui | stock_actuel | implemente | Creation de compte, pas creation client. |
| produits_epargne | Encours et comptes par produit. | Aggregation produit/devise/famille. | Savings Account | produit x devise | oui | stock_actuel | implemente | Pas de croissance historique produit sans snapshots. |
| concentration_epargne | Part des top clients. | Top 5/10/20 clients / encours de la devise. | Savings Account | devise x famille | oui | stock_actuel | implemente | Ne pas appeler Top 10 clients un pourcentage de clients. |
| echeances_dat | Tranches d'echeance DAT. | Echu, aujourd'hui, 0-7, 8-30, 31-60, 61-90, >90 jours. | Savings Account | DAT x devise | oui | suivi | implemente | Basee sur `maturity_date`. |
| interet_estime_dat | Estimation de preparation du remboursement DAT. | capital * taux annuel / 100 * duree contractuelle jours / 365. | Savings Account | DAT | oui | estimation | implemente | Estimation non comptable; taux 11 % par defaut, 0 autorise. |
| historique_encours_epargne | Evolution historique des encours. | Non calculable avec un seul snapshot. | Snapshots Savings Account successifs | periode x devise | oui | stock_historique | data_gap | Ne pas tracer une evolution de solde depuis le seul solde actuel. |
| dormance_reglementaire | Compte dormant certifie. | Derniere operation > seuil reglementaire valide. | Source/regle non disponible | compte | non | risque | data_gap | L'onglet affiche seulement une inactivite observee. |
| renouvellement_dat | DAT renouvele a echeance. | DAT renouveles / DAT arrives a terme. | Cle de renouvellement non disponible | DAT | oui | fidelisation | data_gap | Un nouveau DAT du meme client ne prouve pas le renouvellement. |
| churn_epargne_certifie | Attrition ou cloture certifiee. | Comptes clotures / comptes ouverts. | `date_closed` et regle metier | compte | oui | attrition | data_gap | Ne pas deduire la cloture du statut seul. |
| part_digitale | Part digitale des flux tous canaux. | Flux digitaux / flux tous canaux. | Source multi-canal non disponible | periode x devise | oui | canal | data_gap | G2 n'est pas un canal distinct a additionner. |

## Organisation de l'onglet

Sous-sous-onglets attendus :

1. `Vue d'ensemble`
2. `Collecte et flux`
3. `Portefeuille actuel`
4. `Clients et comptes`
5. `Activite observee`
6. `Produits`
7. `Concentration`
8. `DAT`
9. `Echeances DAT`
10. `Opportunites`
11. `Controles et anomalies`

## Filtres et aides utilisateur

- Utiliser deux champs explicites `Date de debut` et `Date de fin`, au format francais.
- Prioriser les `multiselect` pour les filtres de devise, famille d'epargne, produit, statut, tranche, client et telephone.
- Ajouter des infobulles pour les notions qui peuvent preter a confusion : horizon DAT, taux annuel, inactivite observee, forte epargne, flux net, concentration, data gap.
- Lorsque l'option globale `Renommer automatiquement les colonnes` est active, les tableaux visibles et exports Excel doivent utiliser des colonnes francaises en `snake_case`.

## Exports

L'export Excel du cockpit Epargne doit inclure les feuilles principales : vue d'ensemble, portefeuille, flux, activite, produits, concentration, DAT, echeances, opportunites, qualite et catalogue KPI. Les listes d'action sont exportees seulement lorsqu'elles sont fournies par l'appelant.
