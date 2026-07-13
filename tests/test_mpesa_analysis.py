from __future__ import annotations

import unittest

import pandas as pd

from credit_app.services.mpesa_analysis import (
    MpesaPreparedData,
    build_g2_daily_savings_report,
    build_g2_dat_crosscheck,
    build_g2_entry_report,
    build_diagnostics,
    build_load_report,
    build_savings_final,
    build_mpesa_statement,
    create_excel_export,
    enrich_transactions_with_g2_customer_names,
    enrich_turbo_with_g2_customer_names,
    numeric_column,
    prepare_current_savings,
    prepare_customers,
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
    def test_g2_customer_name_enrichment_prioritizes_phone_then_reference(self) -> None:
        transactions = prepare_transactions(
            pd.DataFrame(
                [
                    {
                        "id": 1,
                        "customer_id": "1001",
                        "msisdn1": "0812345678",
                        "ref_no": "REF-PHONE",
                    },
                    {
                        "id": 2,
                        "customer_id": "1002",
                        "msisdn1": "0999999999",
                        "ref_no": "REF-FALLBACK",
                    },
                    {
                        "id": 3,
                        "customer_id": "1003",
                        "msisdn1": "0977777777",
                        "ref_no": "REF-ABSENT",
                    },
                ]
            )
        )
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {"Receipt No.": "REF-PHONE", "Opposite Party": "0812345678 - NOM PAR TELEPHONE", "Currency": "CDF"},
                    {"Receipt No.": "REF-FALLBACK", "Opposite Party": "0822222222 - NOM PAR REFERENCE", "Currency": "CDF"},
                ]
            )
        )

        result = enrich_transactions_with_g2_customer_names(transactions, g2)

        self.assertEqual(result.loc[0, "Nom_client"], "NOM PAR TELEPHONE")
        self.assertEqual(result.loc[0, "mode_rapprochement_nom_client"], "Telephone G2 = msisdn1 Turbo")
        self.assertEqual(result.loc[1, "Nom_client"], "NOM PAR REFERENCE")
        self.assertEqual(result.loc[1, "mode_rapprochement_nom_client"], "Receipt No G2 = ref_no Turbo")
        self.assertTrue(pd.isna(result.loc[2, "Nom_client"]))
        self.assertEqual(result.loc[2, "mode_rapprochement_nom_client"], "Nom G2 non rapproche")

    def test_g2_customer_name_enrichment_handles_missing_optional_file(self) -> None:
        transactions = prepare_transactions(pd.DataFrame([{"id": 1, "msisdn1": "0812345678", "ref_no": "REF-1"}]))

        result = enrich_transactions_with_g2_customer_names(transactions, pd.DataFrame())

        self.assertIn("Nom_client", result.columns)
        self.assertTrue(pd.isna(result.loc[0, "Nom_client"]))
        self.assertEqual(result.loc[0, "mode_rapprochement_nom_client"], "Fichier G2 absent")

    def test_g2_customer_name_is_propagated_to_turbo_reports(self) -> None:
        prepared = _sample_prepared_data()
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {"Receipt No.": "TX001", "Opposite Party": "0812345678 - CLIENT TEST", "Currency": "CDF"},
                ]
            )
        )
        transactions = enrich_transactions_with_g2_customer_names(prepared.transactions, g2)
        current = enrich_turbo_with_g2_customer_names(prepared.current_savings, g2, phone_column="msisdn")
        prepared = MpesaPreparedData(
            transactions,
            current,
            prepared.fixed_savings,
            prepared.loans,
            prepared.load_report,
            g2,
        )

        report = build_mpesa_statement(prepared, "1001", {"CDF": None})
        matches = search_customers("1001", prepared)
        matches_by_name = search_customers("client test", prepared)

        self.assertEqual(report["extrait"].iloc[0]["Nom_client"], "CLIENT TEST")
        self.assertEqual(report["synthese"].iloc[0]["Nom_client"], "CLIENT TEST")
        self.assertEqual(report["mouvements_dat"].iloc[0]["Nom_client"], "CLIENT TEST")
        self.assertIn("CLIENT TEST", matches["Nom_client"].dropna().tolist())
        self.assertEqual(matches_by_name["customer_id"].dropna().unique().tolist(), ["1001"])

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

    def test_build_statement_accepts_transactions_only(self) -> None:
        prepared = _sample_prepared_data()
        prepared = MpesaPreparedData(
            transactions=prepared.transactions,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=prepared.load_report,
        )

        report = build_mpesa_statement(prepared, "1001", {"CDF": None})

        self.assertEqual(len(report["extrait"]), 2)
        self.assertTrue(report["dat_final"].empty)
        self.assertTrue(report["credits"].empty)
        self.assertEqual(float(report["synthese"].iloc[0]["dat_final"]), 0.0)

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
        self.assertEqual(float(result.iloc[0]["solde_dat_operation"]), 5000.0)
        self.assertEqual(float(result.iloc[0]["dat_final"]), 5000.0)
        self.assertEqual(float(result.iloc[0]["variation_dat_operation"]), 1000.0)
        self.assertEqual(result.iloc[0]["mode_rapprochement"], "Receipt No = ref_no + DAT operation")
        self.assertEqual(float(result.iloc[0]["dat_final_client_devise"]), 5000.0)

    def test_g2_entry_report_builds_detail_and_summary(self) -> None:
        prepared = _sample_prepared_data()
        g2 = pd.DataFrame(
            [
                {
                    "Receipt No.\xa0": "TX001",
                    "Completion Time\xa0": "2026-07-11 10:23:05",
                    "Opposite Party\xa0": "0812345678 - CLIENT TEST",
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

        report = build_g2_entry_report(prepared)

        self.assertEqual(report["detail"].iloc[0]["details_rapport"], "DAT")
        self.assertEqual(float(report["detail"].iloc[0]["montant"]), 1000.0)
        self.assertIn("Total CDF", report["synthese"]["details_rapport"].tolist())
        self.assertIn("montant_DAT", report["pivot"].columns)
        self.assertEqual(float(report["pivot"].iloc[0]["montant_DAT"]), 1000.0)

    def test_g2_repayment_detail_has_priority_over_dat_match(self) -> None:
        prepared = _sample_prepared_data()
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "TX001",
                        "Completion Time": "2026-07-11 10:23:05",
                        "Details": "BisouBisouRepayment",
                        "Opposite Party": "0812345678 - CLIENT TEST",
                        "Currency": "CDF",
                        "Transaction Amount": "CDF 1,000.00",
                    }
                ]
            )
        )
        prepared = MpesaPreparedData(
            prepared.transactions,
            prepared.current_savings,
            prepared.fixed_savings,
            prepared.loans,
            prepared.load_report,
            g2,
        )

        detail = build_g2_entry_report(prepared)["detail"]

        self.assertEqual(detail.iloc[0]["details_rapport"], "Remboursement prets")
        self.assertEqual(detail.iloc[0]["Nom_client"], "CLIENT TEST")

    def test_daily_g2_savings_report_matches_dat_by_phone_currency_and_amount(self) -> None:
        g2 = pd.DataFrame(
            [
                {
                    "Receipt No.\xa0": "DAT001",
                    "Completion Time\xa0": "2026-07-11 12:47:24",
                    "Opposite Party\xa0": "243826325569 - CLIENT DAT",
                    "Currency\xa0": "CDF",
                    "Transaction Amount\xa0": "Fc 5,000",
                    "Transaction Status\xa0": "Completed",
                },
                {
                    "Receipt No.\xa0": "DAT002",
                    "Completion Time\xa0": "2026-07-11 12:44:13",
                    "Opposite Party\xa0": "243826325569 - CLIENT DAT",
                    "Currency\xa0": "CDF",
                    "Transaction Amount\xa0": "Fc 80,000",
                    "Transaction Status\xa0": "Completed",
                },
                {
                    "Receipt No.\xa0": "LOAN001",
                    "Completion Time\xa0": "2026-07-11 12:43:23",
                    "Opposite Party\xa0": "243835549888 - CLIENT CREDIT",
                    "Currency\xa0": "CDF",
                    "Transaction Amount\xa0": "Fc 1,285",
                    "Transaction Status\xa0": "Completed",
                },
                {
                    "Receipt No.\xa0": "SAVE001",
                    "Completion Time\xa0": "2026-07-11 10:18:58",
                    "Opposite Party\xa0": "243822452403 - CLIENT EPARGNE",
                    "Currency\xa0": "CDF",
                    "Transaction Amount\xa0": "Fc 2,000",
                    "Transaction Status\xa0": "Completed",
                },
            ]
        )
        fixed = pd.DataFrame(
            [
                {
                    "customer_id": 37478,
                    "msisdn": "243826325569",
                    "product_name": "3 Months",
                    "account_type": "3 MONTH Fixed Account",
                    "balance": 85000,
                    "currency_code": "CDF",
                    "date_approved": "2026-07-11 11:44:14",
                    "maturity_date": "2026-10-11 11:44:14",
                },
                {
                    "customer_id": 26303,
                    "msisdn": "243835549888",
                    "product_name": "1 Month",
                    "account_type": "1 Month Fixed Account",
                    "balance": 1500,
                    "currency_code": "CDF",
                    "date_approved": "2026-07-11 11:46:11",
                    "maturity_date": "2026-08-11 11:46:11",
                },
            ]
        )
        current = pd.DataFrame(
            [
                {
                    "customer_id": 37478,
                    "msisdn": "243826325569",
                    "product_name": "Open Savings",
                    "account_type": "Current account",
                    "balance": 0,
                    "currency_code": "CDF",
                    "created_at": "2026-07-10 22:37:54",
                    "updated_at": "2026-07-11 08:00:00",
                }
            ]
        )
        customers = pd.DataFrame(
            [
                {
                    "msisdn1": "243826325569",
                    "created_at": "2026-07-09 09:30:00",
                }
            ]
        )
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=prepare_current_savings(current),
            fixed_savings=prepare_fixed_savings(fixed),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=prepare_g2_transactions(g2),
            customers=prepare_customers(customers),
        )

        report = build_g2_daily_savings_report(prepared)
        detail = report["detail"].set_index("receipt_no")

        self.assertEqual(detail.loc["DAT001", "details_rapport"], "DAT")
        self.assertEqual(detail.loc["DAT002", "details_rapport"], "DAT")
        self.assertEqual(detail.loc["LOAN001", "details_rapport"], "Remboursement prets")
        self.assertEqual(detail.loc["SAVE001", "details_rapport"], "Depot normal")
        self.assertEqual(pd.Timestamp(detail.loc["DAT001", "compte_cree"]), pd.Timestamp("2026-07-09 09:30:00"))
        self.assertEqual(pd.Timestamp(detail.loc["DAT001", "compte_cree_client"]), pd.Timestamp("2026-07-09 09:30:00"))
        self.assertEqual(pd.Timestamp(detail.loc["DAT001", "compte_cree_epargne_courante"]), pd.Timestamp("2026-07-10 22:37:54"))
        self.assertEqual(pd.Timestamp(detail.loc["DAT001", "compte_cree_dat"]), pd.Timestamp("2026-07-11 11:44:14"))
        pivot = report["pivot"].set_index("currency_code")
        self.assertEqual(float(pivot.loc["CDF", "montant_DAT"]), 85000.0)
        self.assertEqual(float(pivot.loc["CDF", "montant_Remboursement prets"]), 1285.0)

    def test_numeric_column_handles_missing_columns_like_zero_series(self) -> None:
        frame = pd.DataFrame({"customer_id": ["1", "2"]})

        values = numeric_column(frame, "cr")

        self.assertEqual(values.tolist(), [0.0, 0.0])
        self.assertEqual(float(values.sum()), 0.0)

    def test_savings_final_accepts_file_without_balance_column(self) -> None:
        current = prepare_current_savings(
            pd.DataFrame(
                [
                    {
                        "customer_id": 1001,
                        "msisdn": "0812345678",
                        "currency_code": "CDF",
                        "created_at": "2026-07-11",
                    }
                ]
            )
        )

        result = build_savings_final(current, "1001")

        self.assertEqual(result, {})

    def test_diagnostics_accept_transactions_without_amount_columns(self) -> None:
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(
                [
                    {
                        "customer_id": "1",
                        "reference_id": "REF001",
                        "ref_no": "G2REF",
                        "created_at": "2026-07-11",
                        "currency_code": "CDF",
                        "account_type": "MPESA ACCOUNT",
                    }
                ]
            ),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
        )

        diagnostics = build_diagnostics(prepared)

        self.assertFalse(diagnostics.empty)
        self.assertIn("Mouvements dr = 0 et cr = 0", diagnostics["controle"].tolist())


if __name__ == "__main__":
    unittest.main()
