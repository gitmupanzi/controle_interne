# Sources et contrats de données Solution Numérique

## Contrats de données

Les contrats sont documentés dans `skills/solution-mpesa/references/data-contracts.md` et implémentés principalement dans :

- `credit_app/data_schema.py`
- `credit_app/services/mpesa_analysis.py`
- `credit_app/tabs/solution_mpesa.py`
- `tests/test_solution_mpesa_uploads.py`

## Colonnes principales

### Transactions

Grain : une écriture transactionnelle.

Colonnes clés : `id`, `customer_id`, `msisdn1`, `account_type`, `reference_id`, `currency_code`, `dr`, `cr`, `bal_before`, `bal_after`, `ref_no`, `description`, `created_at`.

### Savings Account

Grain : une position de compte d'épargne ouvert ou bloqué.

Colonnes clés : `savings_id`, `customer_id`, `msisdn1`, `product_name`, `currency_code`, `balance`, `status`, `date_activated`, `maturity_date`, `interest_earned`, `locked_balance`.

### Loans Account

Grain : un prêt ou une position de prêt.

Colonnes clés : `loan_id`, `customer_id`, `loan_amount`, `loan_balance`, `amount_paid`, `outstanding_principle`, `outstanding_interest`, `status_name`, `due_date`, `msisdn1`.

### Customers

Grain : un client connu par la Solution Numérique.

Colonnes clés : `msisdn1`, `created_at`.

## Chargement multiple

`Savings Account` est la source complète. Les fichiers `Customers with Current Savings Account` et `Customers with Fixed Savings Account` sont des synthèses utiles mais ne doivent pas remplacer la source complète lorsqu'elle est disponible.
