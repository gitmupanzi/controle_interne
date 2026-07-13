from __future__ import annotations

from io import BytesIO
import unittest

import pandas as pd

from credit_app.services.mpesa_analysis import (
    MpesaPreparedData,
    build_g2_daily_savings_report,
    build_g2_dat_crosscheck,
    build_g2_entry_report,
    build_entry_count_summary,
    build_large_dat_summary,
    build_diagnostics,
    build_load_report,
    build_savings_final,
    build_mpesa_statement,
    build_perfect_client_crosscheck,
    create_excel_export,
    enrich_transactions_with_g2_customer_names,
    enrich_turbo_with_g2_customer_names,
    filter_g2_transactions_by_completion_time,
    filter_g2_transactions_by_direction,
    numeric_column,
    prepare_current_savings,
    prepare_customers,
    prepare_fixed_savings,
    prepare_g2_transactions,
    prepare_loans,
    prepare_perfect_clients,
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
    def test_g2_count_summary_keeps_currencies_separate_and_fills_missing_categories(self) -> None:
        detail = pd.DataFrame(
            [
                {"currency_code": "CDF", "details_rapport": "DAT"},
                {"currency_code": "CDF", "details_rapport": "DAT"},
                {"currency_code": "CDF", "details_rapport": "Depot normal"},
                {"currency_code": "USD", "details_rapport": "Depot normal"},
                {"currency_code": "USD", "details_rapport": "Remboursement prets"},
            ]
        )

        result = build_entry_count_summary(detail).set_index("currency_code")

        self.assertEqual(int(result.loc["CDF", "Nombre de DAT"]), 2)
        self.assertEqual(int(result.loc["CDF", "Nombre de remboursement de pret"]), 0)
        self.assertEqual(int(result.loc["CDF", "Nombre total"]), 3)
        self.assertEqual(int(result.loc["USD", "Nombre de DAT"]), 0)
        self.assertEqual(int(result.loc["USD", "Nombre de depot normal"]), 1)
        self.assertEqual(int(result.loc["USD", "Nombre de remboursement de pret"]), 1)
        self.assertEqual(int(result.loc["USD", "Nombre total"]), 2)

    def test_filter_g2_completion_time_uses_inclusive_dates(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {"Receipt No.": "D1", "Completion Time": "10-07-2026 23:59:59", "Currency": "CDF", "Opposite Party": "0811111111 - A"},
                    {"Receipt No.": "D2", "Completion Time": "11-07-2026 00:00:00", "Currency": "CDF", "Opposite Party": "0822222222 - B"},
                    {"Receipt No.": "D3", "Completion Time": "11-07-2026 23:59:59", "Currency": "USD", "Opposite Party": "0833333333 - C"},
                    {"Receipt No.": "D4", "Completion Time": "12-07-2026 00:00:00", "Currency": "USD", "Opposite Party": "0844444444 - D"},
                ]
            )
        )

        result = filter_g2_transactions_by_completion_time(g2, "2026-07-11", "2026-07-11")

        self.assertEqual(result["receipt_no"].tolist(), ["D2", "D3"])

    def test_filter_g2_direction_supports_entries_outputs_and_both(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {"Receipt No.": "IN", "Currency": "CDF", "Paid In": 100, "Opposite Party": "0811111111 - A"},
                    {"Receipt No.": "OUT", "Currency": "CDF", "Withdrawn": -50, "Opposite Party": "0822222222 - B"},
                    {"Receipt No.": "CHECK", "Currency": "CDF", "Opposite Party": "0833333333 - C"},
                ]
            )
        )

        entries = filter_g2_transactions_by_direction(g2, "Entrees")
        outputs = filter_g2_transactions_by_direction(g2, "Sorties")
        both = filter_g2_transactions_by_direction(g2, None)

        self.assertEqual(entries["receipt_no"].tolist(), ["IN"])
        self.assertEqual(outputs["receipt_no"].tolist(), ["OUT"])
        self.assertEqual(set(both["receipt_no"]), {"IN", "OUT", "CHECK"})

    def test_prepare_g2_transactions_accepts_paid_in_and_withdrawn_format(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "Receipt No.": "ORG-IN",
                    "Completion Time": "11-07-2026 12:47:24",
                    "Initiation Time": "11-07-2026 12:46:00",
                    "Details": "BisouBisouC2B",
                    "Transaction Status": "Completed",
                    "Currency": "CDF",
                    "Paid In": 1000.0,
                    "Withdrawn": None,
                    "Balance": 5000.0,
                    "Opposite Party": "0812345678 - CLIENT DEPOT",
                },
                {
                    "Receipt No.": "ORG-REPAY",
                    "Completion Time": "11-07-2026 13:00:00",
                    "Initiation Time": "11-07-2026 12:59:00",
                    "Details": "BisouBisouRepayment",
                    "Transaction Status": "Completed",
                    "Currency": "CDF",
                    "Paid In": 250.0,
                    "Withdrawn": None,
                    "Balance": 5250.0,
                    "Opposite Party": "0812345678 - CLIENT DEPOT",
                },
                {
                    "Receipt No.": "ORG-OUT",
                    "Completion Time": "11-07-2026 14:00:00",
                    "Initiation Time": "11-07-2026 13:59:00",
                    "Details": "Super Transaction",
                    "Transaction Status": "Completed",
                    "Currency": "CDF",
                    "Paid In": None,
                    "Withdrawn": -500.0,
                    "Balance": 4750.0,
                    "Opposite Party": "0812345678 - CLIENT DEPOT",
                },
            ]
        )

        result = prepare_g2_transactions(raw).set_index("receipt_no")

        self.assertEqual(float(result.loc["ORG-IN", "transaction_amount_numeric"]), 1000.0)
        self.assertEqual(result.loc["ORG-IN", "transaction_amount_source"], "Paid In")
        self.assertEqual(float(result.loc["ORG-REPAY", "transaction_amount_numeric"]), 250.0)
        self.assertEqual(result.loc["ORG-REPAY", "transaction_amount_source"], "Paid In")
        self.assertEqual(float(result.loc["ORG-OUT", "transaction_amount_numeric"]), -500.0)
        self.assertEqual(result.loc["ORG-OUT", "transaction_amount_source"], "Withdrawn")
        self.assertEqual(result.loc["ORG-IN", "sens_flux"], "Entree")
        self.assertEqual(result.loc["ORG-OUT", "sens_flux"], "Sortie")
        self.assertEqual(float(result.loc["ORG-IN", "montant_entree"]), 1000.0)
        self.assertEqual(float(result.loc["ORG-OUT", "montant_sortie"]), 500.0)
        self.assertEqual(result.loc["ORG-OUT", "type_operation_g2"], "Operation interne Bisou")
        self.assertEqual(float(result.loc["ORG-OUT", "balance_numeric"]), 4750.0)
        self.assertEqual(result.loc["ORG-IN", "completion_time"], pd.Timestamp("2026-07-11 12:47:24"))
        self.assertEqual(result.loc["ORG-IN", "Nom_client"], "CLIENT DEPOT")

    def test_g2_report_classifies_b2c_and_loan_request_as_outflows(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "ENTRY",
                        "Completion Time": "13-07-2026 08:00:00",
                        "Details": "BisouBisouC2B",
                        "Reason Type": "BisouBisouC2B",
                        "Currency": "CDF",
                        "Paid In": 1000,
                        "Opposite Party": "0811111111 - CLIENT ENTREE",
                    },
                    {
                        "Receipt No.": "REPAY",
                        "Completion Time": "13-07-2026 08:10:00",
                        "Details": "BisouBisouC2BRepayment",
                        "Reason Type": "BisouBisouC2BRepayment",
                        "Currency": "CDF",
                        "Paid In": 250,
                        "Opposite Party": "0811111111 - CLIENT ENTREE",
                    },
                    {
                        "Receipt No.": "B2C",
                        "Completion Time": "13-07-2026 08:20:00",
                        "Details": "Bisou Bisou B2C payment to client",
                        "Reason Type": "BisouBisouB2C",
                        "Currency": "CDF",
                        "Withdrawn": -400,
                        "Opposite Party": "0822222222 - CLIENT SORTIE",
                    },
                    {
                        "Receipt No.": "LOAN",
                        "Completion Time": "13-07-2026 08:30:00",
                        "Details": "Bisou Bisou Loan Request payment",
                        "Reason Type": "BisouBisouLoanRequest",
                        "Currency": "CDF",
                        "Withdrawn": -1500,
                        "Opposite Party": "0833333333 - CLIENT CREDIT",
                    },
                    {
                        "Receipt No.": "SUPER",
                        "Completion Time": "13-07-2026 08:40:00",
                        "Details": "Super Transaction",
                        "Reason Type": "Super Transaction",
                        "Currency": "CDF",
                        "Withdrawn": -100,
                        "Opposite Party": "15558 - IMF BISOU",
                    },
                ]
            )
        )
        fixed = prepare_fixed_savings(
            pd.DataFrame(
                [
                    {
                        "customer_id": "3003",
                        "msisdn": "0833333333",
                        "product_name": "1 Month",
                        "account_type": "FIXED SAVINGS",
                        "balance": 1500,
                        "currency_code": "CDF",
                        "date_approved": "2026-07-13 08:30:00",
                        "maturity_date": "2026-08-13",
                    }
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=fixed,
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
        )

        report = build_g2_daily_savings_report(prepared)
        detail = report["detail"].set_index("receipt_no")
        pivot = report["pivot"].set_index("currency_code")

        self.assertEqual(detail.loc["ENTRY", "sens_flux"], "Entree")
        self.assertEqual(detail.loc["ENTRY", "details_rapport"], "Depot normal")
        self.assertEqual(detail.loc["REPAY", "details_rapport"], "Remboursement prets")
        self.assertEqual(detail.loc["B2C", "sens_flux"], "Sortie")
        self.assertEqual(detail.loc["B2C", "details_rapport"], "Paiement client B2C")
        self.assertEqual(detail.loc["LOAN", "details_rapport"], "Demande de credit")
        self.assertTrue(pd.isna(detail.loc["LOAN", "dat_customer_id"]))
        self.assertEqual(detail.loc["SUPER", "details_rapport"], "Operation interne Bisou")
        self.assertEqual(int(pivot.loc["CDF", "nombre_entrees"]), 2)
        self.assertEqual(int(pivot.loc["CDF", "nombre_sorties"]), 3)
        self.assertEqual(float(pivot.loc["CDF", "montant_Demande de credit"]), 1500.0)
        self.assertEqual(float(pivot.loc["CDF", "montant_total_sorties"]), 2000.0)
        self.assertEqual(float(pivot.loc["CDF", "solde_net_flux"]), -750.0)

    def test_large_dat_summary_ranks_clients_by_currency_without_mixing_totals(self) -> None:
        fixed = prepare_fixed_savings(
            pd.DataFrame(
                [
                    {
                        "customer_id": "1001",
                        "msisdn": "0811111111",
                        "Nom_client": "CLIENT A",
                        "product_name": "3 Months",
                        "account_type": "FIXED SAVINGS",
                        "balance": 7000,
                        "currency_code": "CDF",
                        "date_approved": "2026-06-01",
                        "maturity_date": "2026-07-20",
                    },
                    {
                        "customer_id": "1001",
                        "msisdn": "0811111111",
                        "Nom_client": "CLIENT A",
                        "product_name": "6 Months",
                        "account_type": "FIXED SAVINGS",
                        "balance": 3000,
                        "currency_code": "CDF",
                        "date_approved": "2026-05-01",
                        "maturity_date": "2026-11-01",
                    },
                    {
                        "customer_id": "1002",
                        "msisdn": "0822222222",
                        "Nom_client": "CLIENT B",
                        "product_name": "3 Months",
                        "account_type": "FIXED SAVINGS",
                        "balance": 2000,
                        "currency_code": "CDF",
                        "date_approved": "2026-06-10",
                        "maturity_date": "2026-09-10",
                    },
                    {
                        "customer_id": "2001",
                        "msisdn": "0833333333",
                        "Nom_client": "CLIENT USD",
                        "product_name": "3 Months",
                        "account_type": "FIXED SAVINGS",
                        "balance": 500,
                        "currency_code": "USD",
                        "date_approved": "2026-04-01",
                        "maturity_date": "2026-07-01",
                    },
                ]
            )
        )

        result = build_large_dat_summary(fixed, percentile=0.90, as_of_date="2026-07-13")
        clients = result["clients"]
        portfolio = result["portefeuille"].set_index("currency_code")
        cdf = clients.loc[clients["currency_code"].eq("CDF")].set_index("customer_id")

        self.assertEqual(float(cdf.loc["1001", "solde_dat_total"]), 10000.0)
        self.assertEqual(int(cdf.loc["1001", "nb_comptes_dat"]), 2)
        self.assertEqual(int(cdf.loc["1001", "rang_devise"]), 1)
        self.assertTrue(bool(cdf.loc["1001", "est_fort_dat"]))
        self.assertFalse(bool(cdf.loc["1002", "est_fort_dat"]))
        self.assertEqual(float(portfolio.loc["CDF", "total_dat"]), 12000.0)
        self.assertEqual(float(portfolio.loc["USD", "total_dat"]), 500.0)
        self.assertEqual(float(portfolio.loc["CDF", "solde_echeance_30j"]), 7000.0)
        self.assertEqual(float(portfolio.loc["USD", "solde_dat_echu"]), 500.0)

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

    def test_prepare_perfect_clients_normalizes_only_valid_phone_keys(self) -> None:
        result = prepare_perfect_clients(
            pd.DataFrame(
                [
                    {"id_client": 1.0, "Phone_Prefixe": "0812345678", "nom_complet": "CLIENT VALIDE"},
                    {"id_client": 2.0, "Phone_Prefixe": "A VERIFIER", "nom_complet": "CLIENT INVALIDE"},
                    {"id_client": 3.0, "Phone_Prefixe": "243701234567", "nom_complet": "PREFIXE INVALIDE"},
                ]
            )
        )

        self.assertEqual(result.loc[0, "phone_prefixe"], "243812345678")
        self.assertTrue(pd.isna(result.loc[1, "phone_prefixe"]))
        self.assertTrue(pd.isna(result.loc[2, "phone_prefixe"]))
        self.assertEqual(result.loc[1, "phone_prefixe_source"], "A VERIFIER")
        self.assertEqual(result.loc[0, "id_client"], "1")

    def test_perfect_crosscheck_aggregates_shared_phone_without_multiplying_operations(self) -> None:
        prepared = _sample_prepared_data()
        perfect = prepare_perfect_clients(
            pd.DataFrame(
                [
                    {
                        "id_client": 10,
                        "code_client": "P001",
                        "nom_complet": "NOM PERFECT A",
                        "Phone_Prefixe": "243812345678",
                        "Statut_phone": "OK",
                    },
                    {
                        "id_client": 11,
                        "code_client": "P002",
                        "nom_complet": "NOM PERFECT B",
                        "Phone_Prefixe": "0812345678",
                        "Statut_phone": "OK",
                    },
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=prepared.transactions,
            current_savings=prepared.current_savings,
            fixed_savings=prepared.fixed_savings,
            loans=prepared.loans,
            load_report=prepared.load_report,
            perfect_clients=perfect,
        )

        report = build_perfect_client_crosscheck(prepared)
        summary = report["synthese"]
        operations = report["operations"]

        self.assertEqual(len(summary), 1)
        self.assertEqual(int(summary.loc[0, "nb_clients_perfect"]), 2)
        self.assertEqual(
            summary.loc[0, "statut_rapprochement_perfect"],
            "Trouve dans Perfect - plusieurs clients",
        )
        self.assertEqual(summary.loc[0, "noms_clients_perfect"], "NOM PERFECT A | NOM PERFECT B")
        self.assertEqual(len(operations), int(summary.loc[0, "nombre_operations_turbo"]))
        self.assertTrue(operations["nb_clients_perfect"].eq(2).all())
        self.assertTrue(operations["noms_clients_perfect"].eq("NOM PERFECT A | NOM PERFECT B").all())

    def test_perfect_crosscheck_keeps_unmatched_mpesa_client(self) -> None:
        prepared = _sample_prepared_data()
        perfect = prepare_perfect_clients(
            pd.DataFrame([{"id_client": 10, "Phone_Prefixe": "243999999999", "nom_complet": "AUTRE CLIENT"}])
        )
        prepared = MpesaPreparedData(
            transactions=prepared.transactions,
            current_savings=prepared.current_savings,
            fixed_savings=prepared.fixed_savings,
            loans=prepared.loans,
            load_report=prepared.load_report,
            perfect_clients=perfect,
        )

        summary = build_perfect_client_crosscheck(prepared)["synthese"]

        self.assertEqual(len(summary), 1)
        self.assertEqual(int(summary.loc[0, "nb_clients_perfect"]), 0)
        self.assertEqual(summary.loc[0, "statut_rapprochement_perfect"], "Non trouve dans Perfect")

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

    def test_customer_excel_export_preserves_filtered_extract_and_required_sheets(self) -> None:
        prepared = _sample_prepared_data()
        report = build_mpesa_statement(prepared, "1001", {"CDF": None})
        filtered_report = dict(report)
        filtered_report["extrait"] = report["extrait"].iloc[[0]].copy()

        export = create_excel_export(filtered_report)
        workbook = pd.ExcelFile(BytesIO(export), engine="openpyxl")
        required_sheets = {
            "Synthese",
            "Extrait_MPESA",
            "DAT_Final",
            "Mouvements_DAT",
            "Mouvements_Epargne",
            "Credits",
            "G2_DAT",
            "Diagnostics",
        }

        self.assertTrue(required_sheets.issubset(workbook.sheet_names))
        exported_statement = pd.read_excel(workbook, sheet_name="Extrait_MPESA")
        exported_summary = pd.read_excel(workbook, sheet_name="Synthese")
        self.assertEqual(len(exported_statement), 1)
        self.assertEqual(len(exported_summary), len(report["synthese"]))
        self.assertIn("operation_reference", exported_statement.columns)
        self.assertIn("Nom_client", exported_statement.columns)
        self.assertIn("mouvement_net_mpesa", exported_statement.columns)

        filtered_report["extrait"] = report["extrait"].iloc[0:0].copy()
        empty_export = create_excel_export(filtered_report)
        empty_statement = pd.read_excel(BytesIO(empty_export), sheet_name="Extrait_MPESA")
        self.assertEqual(len(empty_statement), 0)
        self.assertIn("operation_reference", empty_statement.columns)

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
