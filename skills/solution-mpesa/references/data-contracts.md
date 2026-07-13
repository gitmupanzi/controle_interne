# Contrats de données M-PESA

La source de vérité exécutable reste `credit_app/data_schema.py`. Cette référence explique le rôle des fichiers et les règles de rapprochement.

## Sources

| Source | Colonnes obligatoires principales | Rôle |
|---|---|---|
| Transactions M-PESA | `id`, `customer_id`, `msisdn1`, `account_type`, `reference_id`, `currency_code`, `dr`, `cr`, `bal_before`, `bal_after`, `ref_no`, `description`, `created_at` | Mouvements et extrait client |
| Épargne courante | `customer_id`, `msisdn`, `product_name`, `account_type`, `balance`, `currency_code`, `created_at`, `updated_at` | Solde d'épargne courant |
| DAT | `customer_id`, `msisdn`, `product_name`, `account_type`, `balance`, `currency_code`, `date_approved`, `maturity_date` | Dépôts à terme et échéances |
| Crédits | `loan_id`, `customer_id` | Crédits rattachés au client |
| Transactions G2 | `Receipt No`, `Currency`, `Opposite Party`; montant dans `Transaction Amount` ou dans `Paid In`/`Withdrawn` | Encaissements et rapprochement G2 |
| Clients | `msisdn1`, `created_at` | Informations complémentaires client |

Les colonnes facultatives et alias sont définis dans `credit_app/data_schema.py`.

## Clés et contrôles

- Client : normaliser puis résoudre vers `customer_id`.
- Référence G2 : rapprocher prioritairement `Receipt No.` avec `ref_no` M-PESA.
- Devise : comparer uniquement des lignes de même `currency_code`/`Currency`.
- Temps : convertir les dates avec erreurs contrôlées, puis expliciter la journée ou période de reporting.
- Doublons : rechercher les doublons sur les identifiants et références avant agrégation.
- Montants : vérifier séparément débit, crédit, mouvement net et solde.

## Fonctions existantes à privilégier

- Préparation : `prepare_transactions`, `prepare_current_savings`, `prepare_fixed_savings`, `prepare_loans`, `prepare_g2_transactions`, `prepare_customers`.
- Extrait : `build_mpesa_statement`, `build_customer_summary`, `build_diagnostics`.
- G2/DAT : `build_g2_dat_crosscheck`, `build_g2_entry_report`, `build_g2_daily_savings_report`.
- Recherche : `search_customers`, `resolve_customer_id`.
- Export : `create_excel_export`.

## Conditions d'interprétation

- Sans solde d'ouverture, le mouvement cumulé M-PESA n'est pas un solde réel.
- Une absence de correspondance est un résultat de contrôle à conserver.
- Un fichier facultatif absent doit réduire le rapport proprement, sans bloquer les analyses possibles.
- Toute synthèse financière doit afficher la devise et éviter un total multidevise.
