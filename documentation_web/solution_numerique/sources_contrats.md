# Sources et contrats de données Solution Numérique

## Contrats de données

Les contrats de données sont décrits dans cette documentation et implémentés principalement dans :

- `credit_app/data_schema.py`
- `credit_app/services/mpesa_analysis.py`
- `credit_app/tabs/solution_mpesa.py`
- `tests/test_solution_mpesa_uploads.py`

La page [Modèle relationnel des fichiers](modele_relationnel.md) présente ces fichiers comme des tables logiques reliées par `customer_id`, `msisdn1`, `reference_id`, `loan_id`, `savings_id` et `ref_no`.

## Modèle logique simplifié

```mermaid
erDiagram
    CUSTOMERS {
        string customer_id PK "identifiant_client_si_disponible"
        string msisdn1 UK "telephone_client"
        datetime created_at "date_creation"
    }
    TRANSACTIONS {
        string id PK "identifiant_ligne"
        string customer_id FK "identifiant_client"
        string msisdn1 FK "telephone_client"
        string reference_id FK "reference_metier"
        string ref_no FK "reference_operation"
        string currency_code "devise"
    }
    SAVINGS_ACCOUNT {
        string savings_id PK "identifiant_compte_epargne"
        string customer_id FK "identifiant_client"
        string msisdn1 FK "telephone_client"
        string product_id "identifiant_produit"
        string currency_code "devise"
    }
    LOANS_ACCOUNT {
        string loan_id PK "identifiant_credit"
        string customer_id FK "identifiant_client"
        string msisdn1 FK "telephone_client"
        string savings_account_id FK "compte_epargne_lie"
        string currency_code "devise"
    }
    G2_TRANSACTIONS {
        string Receipt_No PK "numero_recu_g2"
        string Linked_Transaction_ID FK "transaction_liee"
        datetime Completion_Time "date_finalisation"
        string Currency "devise"
    }
    CLIENTS_PERFECT {
        string code_client PK "code_client_perfect"
        string telephone UK "telephone_normalise"
        string num_manuel "numero_manuel"
    }
    CUSTOMERS ||--o{ TRANSACTIONS : "customer_id / msisdn1"
    CUSTOMERS ||--o{ SAVINGS_ACCOUNT : "customer_id / msisdn1"
    CUSTOMERS ||--o{ LOANS_ACCOUNT : "customer_id / msisdn1"
    SAVINGS_ACCOUNT ||--o{ TRANSACTIONS : "savings_id / reference_id"
    LOANS_ACCOUNT ||--o{ TRANSACTIONS : "loan_id / reference_id"
    TRANSACTIONS }o--o| G2_TRANSACTIONS : "ref_no / Receipt No."
    CUSTOMERS }o--o| CLIENTS_PERFECT : "msisdn1 / téléphone normalisé"
```

## Colonnes principales

### Transactions

Grain : une écriture transactionnelle.

Colonnes clés :

| Colonne anglaise | Nom français recommandé |
|---|---|
| `id` | identifiant_ligne |
| `customer_id` | identifiant_client |
| `msisdn1` | telephone_client |
| `account_type` | type_de_compte |
| `reference_id` | reference_metier |
| `currency_code` | devise |
| `dr` | debit_sortie |
| `cr` | credit_entree |
| `bal_before` | solde_avant |
| `bal_after` | solde_apres |
| `ref_no` | reference_operation |
| `description` | description_operation |
| `created_at` | date_creation |

### Savings Account

Grain : une position de compte d'épargne ouvert ou bloqué.

Colonnes clés :

| Colonne anglaise | Nom français recommandé |
|---|---|
| `savings_id` | identifiant_compte_epargne |
| `customer_id` | identifiant_client |
| `msisdn1` | telephone_client |
| `product_name` | nom_produit |
| `currency_code` | devise |
| `balance` | solde |
| `status` | statut |
| `date_activated` | date_activation |
| `maturity_date` | date_echeance |
| `interest_earned` | interet_client |
| `locked_balance` | solde_bloque |

### Loans Account

Grain : un prêt ou une position de prêt.

Colonnes clés :

| Colonne anglaise | Nom français recommandé |
|---|---|
| `loan_id` | identifiant_credit |
| `customer_id` | identifiant_client |
| `loan_amount` | montant_credit |
| `loan_balance` | solde_credit |
| `amount_paid` | montant_paye |
| `outstanding_principle` | capital_restant_du |
| `outstanding_interest` | interet_restant_du |
| `status_name` | statut_credit |
| `due_date` | date_echeance |
| `msisdn1` | telephone_client |

### Customers

Grain : un client connu par la Solution Numérique.

Colonnes clés :

| Colonne anglaise | Nom français recommandé |
|---|---|
| `msisdn1` | telephone_client |
| `created_at` | date_creation |

## Chargement multiple

`Savings Account` est la source complète. Les fichiers `Customers with Current Savings Account` et `Customers with Fixed Savings Account` sont des synthèses utiles mais ne doivent pas remplacer la source complète lorsqu'elle est disponible.
