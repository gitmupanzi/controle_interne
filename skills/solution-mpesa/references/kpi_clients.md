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

## Tranches d'encours client

Ajouter une synthèse par `tranche_encours` au grain `client x devise x famille` pour lire la structure des avoirs ou expositions :

- `compte_ouvert` : solde du compte ouvert issu de `Savings Account` ;
- `dat` : solde des comptes bloqués / DAT issu de `Savings Account` ;
- `credit` : encours crédit issu de `Loans Account`.

Cette lecture complète le classement des meilleurs clients. Elle ne doit jamais additionner CDF et USD, ni fusionner épargne, DAT et crédit dans un seul montant global.

## Nouveaux numeros clients et produits actifs par devise

Ajouter une table de lecture au grain `compte client x devise` pour répondre à une question opérationnelle simple : les nouveaux numeros clients ou produits nouvellement créés commencent-ils réellement à utiliser la Solution Numérique ?

La population comprend :

- les numeros clients dont `Customers.created_at` tombe dans la période ;
- les produits d'epargne ouverte et DAT dont la date de création/approbation/activation disponible dans `Savings Account` tombe dans la période.

Colonnes attendues :

| Colonne | Lecture |
|---|---|
| `client_key`, `customer_id`, `numero_telephone`, `nom_client` | Identification canonique du client. |
| `date_creation_client` | Date de création issue de `Customers` lorsque disponible. |
| `currency_code` | Devise de lecture. Les montants ne sont jamais totalisés entre devises. |
| `nouveau_client`, `nouveau_compte_ouvert_periode`, `nouveau_dat_periode` | Nature de la nouveauté observée : nouveau numero client, nouveau produit d'epargne ouverte ou nouveau produit DAT. |
| `actif_periode`, `statut_activation` | Indique si le compte client ou le produit a eu au moins une transaction consolidée. |
| `nombre_transactions` | Activité issue de `Transactions`, au grain d'événement métier consolidé. Ne pas utiliser `Transactions` pour produire un volume monétaire global lorsque l'export peut être plafonné. |
| `solde_compte_ouvert`, `solde_dat` | Positions issues de `Savings Account`, séparées par devise. |

G2 peut enrichir le nom du client, mais ne calcule ni activité, ni solde, ni montant.

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

## Organisation de l'onglet

Sous-sous-onglets attendus :

1. `Vue d'ensemble` : KPI et qualité des données.
2. `Activité et activation` : activité, inactivité, acquisition et activation.
3. `Nouveaux numeros clients et produits` : nouveaux numeros clients, produits d'epargne ouverte et produits DAT créés sur la période.
4. `Client 360 et segmentation` : produits détenus, Client 360, segments comportementaux et segments produits.
5. `Opportunités` : DAT sans crédit actif et listes commerciales prudentes.

Cette organisation remplace l'ancien découpage en 8 onglets. Les analyses restent disponibles, mais les blocs proches sont regroupés pour réduire la longueur de navigation.

## Exports

Les opportunités sont exportées en Excel. Lorsque l'option globale `Renommer automatiquement les colonnes` est active, les colonnes visibles et celles du fichier Excel suivent le même format utilisateur en `snake_case`.

Les feuilles décisionnelles du cockpit Clients doivent utiliser des contrats de colonnes explicites, pas un simple `drop` de colonnes techniques. Chaque feuille commence par `date_situation`, qui correspond à la `Date de fin` du cockpit. Les listes nominatives qui portent des montants restent au grain `client x devise`.

Contrat commun de `Clients_Actifs`, `Nouveaux_Clients_Actifs` et `Clients_Multi_Produits` :

```text
date_situation
id_client
numero_client
nom_client
date_creation_client
devise
solde_compte_ouvert
solde_dat
encours_credit
segment_produit
segment_client
statut_confiance
date_premiere_operation_periode
date_derniere_operation
jours_depuis_derniere_operation
nombre_operations
nombre_periodes_actives
nombre_total_operations
nombre_comptes_ouverts_positifs
nombre_credits_actifs
nombre_dat_positifs
nombre_comptes_ouverts
nombre_credits
nombre_dat
```

`Clients_Sans_Mouvement` retire les colonnes d'activité de période inutiles à la relance. `Clients_Tranches` garde `date_situation`, `famille_encours`, `nombre_clients`, `nombre_comptes`, `devise`, `encours_total`, `part_encours_pct` et `tranche_encours`. `DAT_Sans_Credit` garde uniquement les colonnes d'identification client, compte DAT, dates, devise, solde, statut, intérêts et frais utiles à une revue commerciale prudente.

Les colonnes `presence_epargne`, `presence_dat`, `presence_credit`, `presence_transaction`, `nouveau_client`, `nouveau_client_actif`, `actif_periode`, `sans_mouvement_periode`, `multi_produits`, `methode_rapprochement`, `sources_client` et les fichiers sources restent internes sauf besoin explicite de diagnostic.

## Filtres et libellés utilisateur

- Les colonnes visibles dans l'écran et dans l'export doivent rester en français fonctionnel.
- Le numéro de téléphone est une clé principale : il doit être disponible comme filtre `multiselect` dans les vues nominatives (`Activité et activation`, `Client 360 et segmentation`, `Opportunités`).
- Les listes catégorielles et les opportunités doivent privilégier `multiselect` lorsqu'un utilisateur peut vouloir comparer plusieurs segments, statuts ou listes en même temps.
