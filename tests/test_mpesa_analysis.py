from __future__ import annotations

import unittest

import pandas as pd

from credit_app.services.mpesa_analysis import (
    MpesaPreparedData,
    build_g2_dat_crosscheck,
    build_load_report,
    build_mpesa_statement,
    create_excel_export,
    prepare_current_savings,
    prepare_fixed_savings,
    prepare_g2_transactions,
    prepare_loans,
    prepare_transactions,
    search_customers,
    validate_required_columns,
    TRANSACTION_REQUIRED_COLUMNS,
)


def _sample_prepared_data() -> MpesaPreparedData:
    transactions = pd.DataFrame(
        [
            {
                "id": 1,
                "customer_id": 1001.0,
                "msisdn1": "0812345678",
                "account_type": "MPESA ACCOUNT",
                "reference_id": "FA001",
                "currency_code": "cdf",
                "dr": 1000,
                "cr": 0,
                "bal_before": 9000,
                "bal_after": 8000,
                "ref_no": "TX001",
                "description": "M-Pesa Compte",
                "created_at": "2026-07-01 10:00:00",
            },
            {
                "id": 2,
                "customer_id": 1001.0,
                "msisdn1": "0812345678",
                "account_type": "FIXED SAVINGS",
                "reference_id": "FA001",
                "currency_code": "cdf",
                "dr": 0,
                "cr": 1000,
                "bal_before": 4000,
                "bal_after": 5000,
                "ref_no": "TX001",
                "description": "Depot Bloque",
                "created_at": "2026-07-01 10:00:00",
            },
            {
                "id": 3,
                "customer_id": 1001.0,
                "msisdn1": "0812345678",
                "account_type": "MPESA ACCOUNT",
                "reference_id": "LN001",
                "currency_code": "cdf",
                "dr": 0,
                "cr": 2000,
                "bal_before": 8000,
                "bal_after": 10000,
                "ref_no": "TX002",
                "description": "Montant pret",
                "created_at": "2026-07-02 10:00:00",
            },
        ]
    )
    current = pd.DataFrame(
        [
            {
                "customer_id": 1001.0,
                "msisdn": "0812345678",
                "product_name": "Courant",
                "account_type": "NORMAL SAVINGS",
                "balance": 12500,
                "currency_code": "cdf",
                "created_at": "2026-01-01",
                "updated_at": "2026-07-02",
            }
        ]
    )
    fixed = pd.DataFrame(
        [
            {
                "customer_id": 1001.0,
                "msisdn": "0812345678",
                "product_name": "DAT",
                "account_type": "FIXED SAVINGS",
                "balance": 5000,
                "currency_code": "cdf",
                "date_approved": "2026-06-01",
                "maturity_date": "2026-09-01",
            }
        ]
    )
    loans = pd.DataFrame(
        [
            {
                "loan_id": "LN001",
                "customer_id": 1001.0,
                "customer": "Client Test",
                "msisdn1": "0812345678",
                "currency_code": "cdf",
                "loan_amount": 2000,
                "loan_balance": 1500,
                "amount_paid": 500,
                "outstanding_principle": 1500,
                "outstanding_interest": 0,
                "outstanding_penalty_fees": 0,
                "status_name": "Active",
                "due_date": "2026-08-01",
                "last_repayment_date": None,
                "created_at": "2026-07-02",
                "updated_at": "2026-07-02",
            }
        ]
    )
    return MpesaPreparedData(
        transactions=prepare_transactions(transactions),
        current_savings=prepare_current_savings(current),
        fixed_savings=prepare_fixed_savings(fixed),
        loans=prepare_loans(loans),
        load_report=build_load_report({}, {}),
    )


class MpesaAnalysisTests(unittest.TestCase):
    def test_validate_required_columns_detects_missing_values(self) -> None:
        missing = validate_required_columns(pd.DataFrame({"id": [1]}), TRANSACTION_REQUIRED_COLUMNS, "Transactions")

        self.assertIn("customer_id", missing)
        self.assertIn("created_at", missing)

    def test_search_customer_by_normalized_phone(self) -> None:
        prepared = _sample_prepared_data()

        result = search_customers("243812345678", prepared)

        self.assertFalse(result.empty)
        self.assertEqual(result.iloc[0]["customer_id"], "1001")

    def test_build_statement_reconstructs_balances_and_loans(self) -> None:
        prepared = _sample_prepared_data()

        report = build_mpesa_statement(prepared, "1001", {"CDF": 10000})
        statement = report["extrait"]

        self.assertEqual(len(statement), 2)
        self.assertIn("solde_mpesa_apres", statement.columns)
        self.assertEqual(float(statement.iloc[-1]["solde_mpesa_apres"]), 11000.0)
        self.assertIn("loan_balance", statement.columns)
        self.assertEqual(float(statement["dat_final_client"].iloc[0]), 5000.0)

    def test_excel_export_contains_content(self) -> None:
        prepared = _sample_prepared_data()
        report = build_mpesa_statement(prepared, "1001", {"CDF": None})

        export = create_excel_export(report)

        self.assertGreater(len(export), 5000)

    def test_g2_transactions_extract_phone_and_match_dat(self) -> None:
        prepared = _sample_prepared_data()
        g2 = pd.DataFrame(
            [
                {
                    "Receipt No.\xa0": "TX001",
                    "Completion Time\xa0": "2026-07-11 10:23:05",
                    "Opposite Party\xa0": "0999999999 - AUTRE TELEPHONE",
                    "Currency\xa0": "CDF",
                    "Transaction Amount\xa0": "CDF 1,000.00",
                    "Balance\xa0": "CDF 2,000.00",
                    "Transaction Status\xa0": "Completed",
                }
            ]
        )
        prepared = MpesaPreparedData(
            prepared.transactions,
            prepared.current_savings,
            prepared.fixed_savings,
            prepared.loans,
            prepared.load_report,
            prepare_g2_transactions(g2),
        )

        result = build_g2_dat_crosscheck(prepared)

        self.assertEqual(result.iloc[0]["phone_prefixe"], "243999999999")
        self.assertEqual(result.iloc[0]["customer_id_ref_no"], "1001")
        self.assertEqual(result.iloc[0]["customer_id_dat"], "1001")
        self.assertEqual(result.iloc[0]["reference_dat_operation"], "FA001")
        self.assertEqual(float(result.iloc[0]["solde_dat_operation_avant"]), 4000.0)
        self.assertEqual(float(result.iloc[0]["solde_dat_operation_apres"]), 5000.0)
        self.assertEqual(float(result.iloc[0]["variation_dat_operation"]), 1000.0)
        self.assertEqual(result.iloc[0]["mode_rapprochement"], "Receipt No = ref_no + DAT operation")
        self.assertEqual(float(result.iloc[0]["dat_final_client_devise"]), 5000.0)


if __name__ == "__main__":
    unittest.main()
