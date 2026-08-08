# KPI Clients - Solution Numérique

Ce référentiel décrit l'onglet `Clients`, placé après `Finance et comptabilité`.

## Sources

- `Customers [Solution Numérique]` : référentiel client par téléphone normalisé et date de création client.
- `Transactions [Solution Numérique]` : activité observée, au grain d'événement métier consolidé, jamais au grain de ligne brute.
- `Savings Account [Solution Numérique]` : comptes ouverts et DAT.
- `Loans Account [Solution Numérique]` : crédits actifs et encours observés.
- `Rapports G2 M-Pesa` : enrichissement du nom et contrôle uniquement; aucun montant ni solde n'est calculé depuis G2.

## Identité client canonique

Ordre de résolution :

1. `customer_id` lorsqu'il existe;
2. téléphone normalisé `243...`;
3. liaison prudente téléphone -> `customer_id` lorsqu'une seule correspondance est observée.

Conserver `methode_rapprochement` et `statut_confiance`. Ne jamais rapprocher uniquement sur le nom.

## KPI principaux

| KPI | Définition |
|---|---|
| `clients_referentiel` | Clients distincts de `Customers`, dédupliqués par téléphone normalisé. |
| `clients_connus_solution_numerique` | Clients observés dans au moins une source Solution Numérique. |
| `clients_actifs` | Clients ayant au moins un événement métier valide dans Transactions sur la période. |
| `taux_clients_actifs` | `clients_actifs / clients_referentiel` si Customers est disponible, sinon `/ clients_connus_solution_numerique`. |
| `nouveaux_clients` | Clients de `Customers` dont `created_at` est dans la période. |
| `nouveaux_clients_actifs` | Nouveaux clients ayant aussi au moins un événement valide dans la période. |
| `taux_activation_nouveaux_clients` | `nouveaux_clients_actifs / nouveaux_clients`. |
| `clients_sans_mouvement` | Clients de la population de référence sans événement valide sur la période. |

## Segmentations

Segments comportementaux objectifs :

- `nouveau_actif`
- `nouveau_non_active`
- `actif`
- `occasionnel`
- `inactif_observe`
- `multi_produits`
- `sans_mouvement`

Segments produits :

- `epargne`
- `dat`
- `credit`
- combinaisons `epargne_dat`, `epargne_credit`, `dat_credit`, `epargne_dat_credit`
- `sans_produit_observe`

Les seuils `Seuil inactivité` et `Seuil occasionnel` sont visibles et modifiables dans l'onglet. `inactif_observe` est une segmentation analytique, pas un statut réglementaire.

## DAT sans crédit actif

Réutiliser la logique `dat_sans_credit_actif` du cockpit financier. La liste signale un `potentiel_commercial_credit`; elle ne doit jamais être présentée comme une éligibilité automatique.

## Exports

Les listes d'action sont exportées en Excel. Lorsque l'option globale `Renommer automatiquement les colonnes` est active, les colonnes visibles et celles du fichier Excel suivent le même format utilisateur en `snake_case`.

## Filtres et libellés utilisateur

- Les colonnes visibles dans l'écran et dans l'export doivent rester en français fonctionnel.
- Le numéro de téléphone est une clé principale : il doit être disponible comme filtre `multiselect` dans les vues nominatives (`Activité`, `Client 360`, `DAT sans crédit actif`, `Listes d'action`).
- Les listes catégorielles et les listes d'action doivent privilégier `multiselect` lorsqu'un utilisateur peut vouloir comparer plusieurs segments, statuts ou listes en même temps.
