from __future__ import annotations

from datetime import time
from io import BytesIO
import unittest

import pandas as pd

from credit_app.services.mpesa_analysis import (
    MpesaPreparedData,
    CUSTOMER_STATEMENT_COLUMNS,
    CUSTOMER_STATEMENT_FOCUS_OPERATION_TYPES,
    G2_CLASSIFIED_TRANSACTION_COLUMNS,
    build_customer_statement_view,
    build_customer_statement_filename,
    build_customer_transaction_analysis,
    build_g2_daily_savings_report,
    build_g2_dat_crosscheck,
    build_g2_retention_report,
    build_g2_transaction_time_analysis,
    build_turbo_only_g2_transactions,
    build_mpesa_dat_maturity_analysis,
    build_mpesa_accounting_analysis,
    build_mpesa_management_dashboard,
    build_loan_savings_reconciliation,
    build_g2_dat_pdf_html,
    create_g2_dat_word,
    create_customer_statement_pdf,
    create_customer_statement_word,
    build_g2_entry_report,
    build_entry_count_summary,
    build_entry_pivot,
    build_large_dat_summary,
    build_diagnostics,
    build_load_report,
    build_savings_accounts_reconciliation,
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
    prepare_fixed_savings_from_accounts,
    prepare_savings_accounts,
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


def _sample_customer_transaction_analysis_data() -> MpesaPreparedData:
    common = {
        "customer_id": "CLIENT-ANALYSE",
        "msisdn1": "0812345678",
        "currency_code": "CDF",
    }
    rows: list[dict[str, object]] = []

    def add(
        row_id: int,
        *,
        account_type: str,
        reference_id: str,
        description: str,
        created_at: str,
        dr: float = 0,
        cr: float = 0,
        bal_before: float = 0,
        bal_after: float = 0,
        ref_no: str = "",
    ) -> None:
        rows.append(
            {
                **common,
                "id": row_id,
                "account_type": account_type,
                "reference_id": reference_id,
                "dr": dr,
                "cr": cr,
                "bal_before": bal_before,
                "bal_after": bal_after,
                "ref_no": ref_no,
                "description": description,
                "created_at": created_at,
            }
        )

    add(1, account_type="MPESA ACCOUNT", reference_id="SAV-1", description="M-Pesa Depot", created_at="2026-07-01 08:00:00", dr=100, bal_after=100, ref_no="DEP-1")
    add(2, account_type="NORMAL SAVINGS", reference_id="SAV-1", description="Epargne depot", created_at="2026-07-01 08:00:00", cr=100, bal_after=100, ref_no="DEP-1")
    add(3, account_type="MPESA ACCOUNT", reference_id="DAT-1", description="M-Pesa Compte", created_at="2026-07-02 08:00:00", dr=50, bal_after=50, ref_no="DAT-DEP-1")
    add(4, account_type="FIXED SAVINGS", reference_id="DAT-1", description="Depot Bloque", created_at="2026-07-02 08:00:00", cr=50, bal_after=50, ref_no="DAT-DEP-1")

    loan_time = "2026-07-03 08:00:00"
    add(5, account_type="PRINCIPLE", reference_id="LOAN-1", description="Montant principal", created_at=loan_time, dr=100, bal_after=100)
    add(6, account_type="LOAN ACCOUNT", reference_id="LOAN-1", description="Compte de pret", created_at=loan_time, cr=110, bal_after=110)
    add(7, account_type="PRINCIPLE", reference_id="LOAN-1", description="Montant principal", created_at=loan_time, cr=10, bal_after=10)
    add(8, account_type="LOAN ACCOUNT", reference_id="LOAN-1", description="Revenu du interets", created_at=loan_time, dr=10, bal_after=10)
    add(9, account_type="INTEREST EARNED", reference_id="LOAN-1", description="Revenu du interets", created_at=loan_time, cr=10, bal_after=10)
    add(10, account_type="LOAN AMOUNT A/C", reference_id="LOAN-1", description="Montant pret", created_at=loan_time, cr=100, bal_after=100)
    add(11, account_type="MPESA ACCOUNT", reference_id="LOAN-1", description="Montant pret", created_at=loan_time, cr=100, bal_after=100)
    add(12, account_type="MPESA ACCOUNT", reference_id="LOAN-1", description="Compte du M-Pesa", created_at=loan_time, dr=10, bal_after=10)

    repayment_time = "2026-07-04 08:00:00"
    add(13, account_type="PRINCIPLE", reference_id="LOAN-1", description="Remboursement du principal", created_at=repayment_time, cr=40, bal_before=100, bal_after=60)
    add(14, account_type="LOAN ACCOUNT", reference_id="LOAN-1", description="Remboursement du Pret", created_at=repayment_time, dr=40, bal_before=100, bal_after=60)
    add(15, account_type="LOAN PORTFOLIO", reference_id="LOAN-1", description="Portefeuille Pret Remboursement", created_at=repayment_time, dr=40, bal_before=100, bal_after=60)
    add(16, account_type="MPESA ACCOUNT", reference_id="LOAN-1", description="Remboursement du M-Pesa", created_at=repayment_time, dr=40, bal_after=40)
    add(17, account_type="LOAN PENALTY FEES", reference_id="LOAN-1", description="Compte de penalite de pret", created_at=repayment_time, cr=5, bal_after=5)
    add(18, account_type="CUSTOMER USD WALLET PENALTY", reference_id="LOAN-1", description="Compte de penalite de pret", created_at=repayment_time, cr=5, bal_after=5)

    transfer_time = "2026-07-05 08:00:00"
    add(19, account_type="FIXED SAVINGS", reference_id="DAT-1", description="Retrait Compte Bloque", created_at=transfer_time, dr=20, bal_before=50, bal_after=30)
    add(20, account_type="NORMAL SAVINGS", reference_id="SAV-1", description="Retrait Compte Bloque", created_at=transfer_time, dr=20, bal_before=100, bal_after=120)

    current = pd.DataFrame(
        [
            {
                "customer_id": "CLIENT-ANALYSE",
                "msisdn": "0812345678",
                "product_name": "Courant",
                "account_type": "NORMAL SAVINGS",
                "balance": 120,
                "currency_code": "CDF",
                "created_at": "2026-01-01",
                "updated_at": "2026-07-05",
            }
        ]
    )
    fixed = pd.DataFrame(
        [
            {
                "customer_id": "CLIENT-ANALYSE",
                "msisdn": "0812345678",
                "product_name": "DAT",
                "account_type": "FIXED SAVINGS",
                "balance": 30,
                "currency_code": "CDF",
                "date_approved": "2026-07-02",
                "maturity_date": "2026-10-02",
            }
        ]
    )
    loans = pd.DataFrame(
        [
            {
                "loan_id": "LOAN-1",
                "customer_id": "CLIENT-ANALYSE",
                "currency_code": "CDF",
                "loan_amount": 100,
                "loan_balance": 60,
                "amount_paid": 40,
                "outstanding_principle": 60,
                "outstanding_interest": 0,
                "outstanding_penalty_fees": 5,
                "status_name": "Active",
                "created_at": "2026-07-03",
                "updated_at": "2026-07-05",
            }
        ]
    )
    return MpesaPreparedData(
        transactions=prepare_transactions(pd.DataFrame(rows)),
        current_savings=prepare_current_savings(current),
        fixed_savings=prepare_fixed_savings(fixed),
        loans=prepare_loans(loans),
        load_report=pd.DataFrame(),
    )


class MpesaAnalysisTests(unittest.TestCase):
    def test_multi_file_turbo_and_perfect_snapshots_are_deduplicated_by_business_key(self) -> None:
        transaction_rows = pd.DataFrame(
            [
                {
                    "id": 1,
                    "customer_id": 10,
                    "msisdn1": "0811111111",
                    "account_type": "MPESA ACCOUNT",
                    "reference_id": "REF-1",
                    "currency_code": "CDF",
                    "dr": 100,
                    "cr": 0,
                    "bal_before": 500,
                    "bal_after": 400,
                    "ref_no": "TX-1",
                    "description": "M-Pesa Depot",
                    "created_at": "2026-07-15 08:00:00",
                    "fichier_source_transactions_turbo": "transactions_a.xlsx",
                    "ordre_fichier_import": 0,
                },
                {
                    "id": 1,
                    "customer_id": 10,
                    "msisdn1": "0811111111",
                    "account_type": "MPESA ACCOUNT",
                    "reference_id": "REF-1",
                    "currency_code": "CDF",
                    "dr": 100,
                    "cr": 0,
                    "bal_before": 500,
                    "bal_after": 400,
                    "ref_no": "TX-1",
                    "description": "M-Pesa Depot",
                    "created_at": "2026-07-15 08:00:00",
                    "fichier_source_transactions_turbo": "transactions_b.xlsx",
                    "ordre_fichier_import": 1,
                },
                {
                    "id": 2,
                    "customer_id": 10,
                    "msisdn1": "0811111111",
                    "account_type": "MPESA ACCOUNT",
                    "reference_id": "REF-2",
                    "currency_code": "CDF",
                    "dr": 0,
                    "cr": 50,
                    "bal_before": 400,
                    "bal_after": 450,
                    "ref_no": "TX-2",
                    "description": "Retrait vers M-Pesa",
                    "created_at": "2026-07-15 09:00:00",
                    "fichier_source_transactions_turbo": "transactions_b.xlsx",
                    "ordre_fichier_import": 1,
                },
            ]
        )
        transactions = prepare_transactions(transaction_rows).set_index("id")

        self.assertEqual(len(transactions), 2)
        self.assertEqual(float(transactions.loc["1", "dr"]), 100.0)
        self.assertEqual(float(transactions.loc["2", "cr"]), 50.0)
        self.assertEqual(
            transactions.loc["1", "fichiers_sources_transactions_turbo"],
            "transactions_a.xlsx | transactions_b.xlsx",
        )
        self.assertNotIn("ordre_fichier_import", transactions.columns)

        current_rows = pd.DataFrame(
            [
                {
                    "customer_id": 10,
                    "msisdn": "0811111111",
                    "product_name": "Open Savings",
                    "account_type": "Current account",
                    "balance": balance,
                    "currency_code": "CDF",
                    "created_at": "2026-07-01 08:00:00",
                    "updated_at": updated_at,
                    "fichier_source_epargne_turbo": source,
                    "ordre_fichier_import": order,
                }
                for balance, updated_at, source, order in [
                    (100, "2026-07-14 08:00:00", "epargne_a.xlsx", 0),
                    (150, "2026-07-15 08:00:00", "epargne_b.xlsx", 1),
                ]
            ]
        )
        current = prepare_current_savings(current_rows)
        self.assertEqual(len(current), 1)
        self.assertEqual(float(current.iloc[0]["balance"]), 150.0)
        self.assertEqual(current.iloc[0]["fichiers_sources_epargne_turbo"], "epargne_a.xlsx | epargne_b.xlsx")

        fixed_rows = pd.DataFrame(
            [
                {
                    "customer_id": 10,
                    "msisdn": "0811111111",
                    "product_name": "1 Month",
                    "account_type": "1 Month Fixed Account",
                    "balance": balance,
                    "currency_code": "CDF",
                    "date_approved": "2026-07-01 08:00:00",
                    "maturity_date": "2026-08-01 08:00:00",
                    "fichier_source_dat_turbo": source,
                    "ordre_fichier_import": order,
                }
                for balance, source, order in [
                    (1000, "dat_a.xlsx", 0),
                    (1100, "dat_b.xlsx", 1),
                ]
            ]
        )
        fixed = prepare_fixed_savings(fixed_rows)
        self.assertEqual(len(fixed), 1)
        self.assertEqual(float(fixed.iloc[0]["balance"]), 1100.0)

        loan_rows = pd.DataFrame(
            [
                {
                    "id": 1,
                    "loan_id": "LN-1",
                    "customer_id": 10,
                    "loan_balance": balance,
                    "updated_at": updated_at,
                    "fichier_source_credits_turbo": source,
                    "ordre_fichier_import": order,
                }
                for balance, updated_at, source, order in [
                    (500, "2026-07-14", "credits_a.xlsx", 0),
                    (400, "2026-07-15", "credits_b.xlsx", 1),
                ]
            ]
        )
        loans = prepare_loans(loan_rows)
        self.assertEqual(len(loans), 1)
        self.assertEqual(float(loans.iloc[0]["loan_balance"]), 400.0)

        customer_rows = pd.DataFrame(
            [
                {
                    "msisdn1": "0811111111",
                    "created_at": "2026-07-01",
                    "fichier_source_clients_turbo": source,
                    "ordre_fichier_import": order,
                }
                for source, order in [("clients_a.xlsx", 0), ("clients_b.xlsx", 1)]
            ]
        )
        customers = prepare_customers(customer_rows)
        self.assertEqual(len(customers), 1)
        self.assertEqual(customers.iloc[0]["fichier_source_clients_turbo"], "clients_b.xlsx")

        perfect_rows = pd.DataFrame(
            [
                {
                    "id_client": "P-1",
                    "code_client": "C-1",
                    "nom_complet": name,
                    "Phone_Prefixe": "243811111111",
                    "fichier_source_clients_perfect": source,
                    "ordre_fichier_import": order,
                }
                for name, source, order in [
                    ("ANCIEN NOM", "perfect_a.xlsx", 0),
                    ("NOUVEAU NOM", "perfect_b.xlsx", 1),
                ]
            ]
        )
        perfect = prepare_perfect_clients(perfect_rows)
        self.assertEqual(len(perfect), 1)
        self.assertEqual(perfect.iloc[0]["nom_complet"], "NOUVEAU NOM")
        self.assertEqual(perfect.iloc[0]["fichiers_sources_clients_perfect"], "perfect_a.xlsx | perfect_b.xlsx")

    def test_prepare_current_savings_accepts_mixed_savings_account_export(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "customer_id": 10,
                    "msisdn1": "0811111111",
                    "product_name": "Open Savings",
                    "product_description": "Current account",
                    "balance": 150,
                    "currency_code": "CDF",
                    "created_at": "2026-07-01 08:00:00",
                    "updated_at": "2026-07-17 08:00:00",
                },
                {
                    "customer_id": 11,
                    "msisdn1": "0822222222",
                    "product_name": "Open Savings",
                    "product_description": "Current account",
                    "balance": 25,
                    "currency_code": "USD",
                    "created_at": "2026-07-02 08:00:00",
                    "updated_at": "2026-07-17 08:00:00",
                },
                {
                    "customer_id": 10,
                    "msisdn1": "0811111111",
                    "product_name": "1 Month",
                    "product_description": "1 Month Fixed Account",
                    "balance": 500,
                    "currency_code": "CDF",
                    "created_at": "2026-07-03 08:00:00",
                    "updated_at": "2026-07-17 08:00:00",
                },
            ]
        )

        result = prepare_current_savings(raw)

        self.assertEqual(len(result), 2)
        self.assertEqual(set(result["account_type"]), {"NORMAL SAVINGS"})
        self.assertEqual(set(result["msisdn"]), {"243811111111", "243822222222"})
        self.assertEqual(float(result["balance"].sum()), 175.0)

    def test_complete_savings_account_source_retains_and_reconciles_fixed_accounts(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "savings_id": "SA-1",
                    "customer_id": 10,
                    "msisdn1": "0811111111",
                    "product_name": "Open Savings",
                    "product_description": "Current account",
                    "balance": 150,
                    "currency_code": "CDF",
                    "created_at": "2026-07-01",
                    "fichier_source_epargne_turbo": "Savings Account.xlsx",
                },
                {
                    "savings_id": "FA-1",
                    "customer_id": 10,
                    "msisdn1": "0811111111",
                    "product_name": "1 Month",
                    "product_description": "1 Month Fixed Account",
                    "balance": 500,
                    "currency_code": "CDF",
                    "date_approved": "2026-07-02",
                    "maturity_date": "2026-08-02",
                    "created_at": "2026-07-02",
                    "fichier_source_epargne_turbo": "Savings Account.xlsx",
                },
                {
                    "savings_id": "FA-2",
                    "customer_id": 11,
                    "msisdn1": "0822222222",
                    "product_name": "3 Months",
                    "product_description": "3 MONTH Fixed Account",
                    "balance": 0,
                    "currency_code": "USD",
                    "date_approved": "2026-04-02",
                    "maturity_date": "2026-07-02",
                    "created_at": "2026-04-02",
                    "fichier_source_epargne_turbo": "Savings Account.xlsx",
                },
            ]
        )
        control = prepare_fixed_savings(
            pd.DataFrame(
                [
                    {
                        "customer_id": 10,
                        "msisdn": "0811111111",
                        "product_name": "1 Month",
                        "account_type": "1 Month Fixed Account",
                        "balance": 500,
                        "currency_code": "CDF",
                        "date_approved": "2026-07-02",
                        "maturity_date": "2026-08-02",
                    }
                ]
            )
        )
        all_accounts = prepare_savings_accounts(raw)
        fixed = prepare_fixed_savings_from_accounts(raw)
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=all_accounts.loc[
                all_accounts["account_type"].eq("NORMAL SAVINGS")
            ],
            fixed_savings=fixed,
            fixed_savings_control=control,
            loans=pd.DataFrame(),
            load_report=pd.DataFrame(),
        )

        report = build_savings_accounts_reconciliation(prepared)
        summary = report["synthese"].iloc[0]

        self.assertEqual(len(all_accounts), 3)
        self.assertEqual(len(fixed), 2)
        self.assertEqual(int(summary["dat_solde_positif"]), 1)
        self.assertEqual(int(summary["dat_solde_nul"]), 1)
        self.assertEqual(int(summary["dat_export_retrouves"]), 1)
        self.assertEqual(summary["statut_rapprochement"], "Concordance exacte")
        self.assertTrue(report["ecarts"].empty)

    def test_savings_account_is_autonomous_without_summary_exports(self) -> None:
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(
                [
                    {"customer_id": 10, "balance": 150},
                    {"customer_id": 11, "balance": 0},
                ]
            ),
            fixed_savings=pd.DataFrame(
                [
                    {
                        "customer_id": 10,
                        "currency_code": "CDF",
                        "balance": 500,
                        "fichier_source_epargne_turbo": "Savings Account.xlsx",
                    },
                    {
                        "customer_id": 11,
                        "currency_code": "USD",
                        "balance": 0,
                        "fichier_source_epargne_turbo": "Savings Account.xlsx",
                    },
                ]
            ),
            loans=pd.DataFrame(),
            load_report=pd.DataFrame(),
        )

        report = build_savings_accounts_reconciliation(prepared)
        summary = report["synthese"].iloc[0]

        self.assertEqual(summary["statut_rapprochement"], "Source autonome")
        self.assertEqual(int(summary["comptes_courants"]), 2)
        self.assertEqual(int(summary["dat_total_source_complete"]), 2)
        self.assertEqual(int(summary["dat_solde_positif"]), 1)
        self.assertEqual(int(summary["dat_solde_nul"]), 1)
        self.assertEqual(int(summary["dat_positifs_absents_export_resume"]), 0)
        self.assertTrue(report["ecarts"].empty)

    def test_prepare_g2_transactions_promotes_two_organization_statement_headers(self) -> None:
        def statement_frame(
            account_name: str,
            source_name: str,
            receipt_no: str,
            *,
            paid_in: object = None,
            withdrawn: object = None,
        ) -> pd.DataFrame:
            columns = ["Account Holder:", account_name] + [
                f"Unnamed: {index}" for index in range(2, 12)
            ]
            rows = [
                ["Short Code:", "1441", *([None] * 10)],
                ["Account:", "All Account", *([None] * 10)],
                ["Time Period:", "From", "01-07-2026", "To", "17-07-2026", *([None] * 7)],
                ["Operator:", "GOMA", "Organization:", account_name, *([None] * 8)],
                [
                    "Receipt No.",
                    "Completion Time",
                    "Initiation Time",
                    "Details",
                    "Transaction Status",
                    "Currency",
                    "Paid In",
                    "Withdrawn",
                    "Balance",
                    "Reason Type",
                    "Opposite Party",
                    "Linked Transaction ID",
                ],
                [
                    receipt_no,
                    "\t16-07-2026 10:00:00",
                    "\t16-07-2026 09:59:00",
                    "BisouBisouC2B" if paid_in is not None else "Bisou Bisou B2C payment",
                    "Completed",
                    "CDF",
                    paid_in,
                    withdrawn,
                    "1000",
                    "BisouBisouC2B" if paid_in is not None else "BisouBisouB2C",
                    "\t243811111111 - CLIENT TEST",
                    None,
                ],
            ]
            frame = pd.DataFrame(rows, columns=columns)
            frame["fichier_source_g2"] = source_name
            frame["ordre_fichier_import"] = 0
            return frame

        raw = pd.concat(
            [
                statement_frame(
                    "IMF Bisou Bisou SA",
                    "ORG_1441.xlsx",
                    "ENTRY-001",
                    paid_in="100",
                ),
                statement_frame(
                    "IMF Bisou Bisou  SA",
                    "ORG_15558.xlsx",
                    "OUTPUT-001",
                    withdrawn="-75",
                ),
            ],
            ignore_index=True,
            sort=False,
        )

        result = prepare_g2_transactions(raw).set_index("receipt_no")

        self.assertEqual(set(result.index), {"ENTRY-001", "OUTPUT-001"})
        self.assertEqual(result.loc["ENTRY-001", "sens_flux"], "Entree")
        self.assertEqual(result.loc["OUTPUT-001", "sens_flux"], "Sortie")
        self.assertEqual(float(result.loc["OUTPUT-001", "montant_sortie"]), 75.0)
        self.assertEqual(result.loc["ENTRY-001", "fichier_source_g2"], "ORG_1441.xlsx")
        self.assertEqual(result.loc["OUTPUT-001", "fichier_source_g2"], "ORG_15558.xlsx")

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

    def test_filter_g2_completion_time_uses_inclusive_hours(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {"Receipt No.": "T1", "Completion Time": "11-07-2026 09:59:59", "Currency": "CDF", "Opposite Party": "0811111111 - A"},
                    {"Receipt No.": "T2", "Completion Time": "11-07-2026 10:00:00", "Currency": "CDF", "Opposite Party": "0822222222 - B"},
                    {"Receipt No.": "T3", "Completion Time": "11-07-2026 15:30:00", "Currency": "USD", "Opposite Party": "0833333333 - C"},
                    {"Receipt No.": "T4", "Completion Time": "11-07-2026 15:30:01", "Currency": "USD", "Opposite Party": "0844444444 - D"},
                ]
            )
        )

        result = filter_g2_transactions_by_completion_time(
            g2,
            "2026-07-11",
            "2026-07-11",
            time(10, 0),
            time(15, 30),
        )

        self.assertEqual(result["receipt_no"].tolist(), ["T2", "T3"])

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
        self.assertEqual(
            detail.loc["SUPER", "statut_rapprochement"],
            "Non applicable - operation interne",
        )
        self.assertEqual(detail.loc["SUPER", "motif_anomalie"], "")
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
        self.assertTrue(report["clients_trois_systemes"].empty)

    def test_perfect_crosscheck_identifies_clients_present_in_g2_turbo_and_perfect(self) -> None:
        prepared = _sample_prepared_data()
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "TX001",
                        "Completion Time": "2026-07-01 10:00:00",
                        "Opposite Party": "0812345678 - CLIENT G2",
                        "Currency": "CDF",
                        "Transaction Amount": 1000,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    }
                ]
            )
        )
        perfect = prepare_perfect_clients(
            pd.DataFrame(
                [
                    {
                        "id_client": 10,
                        "code_client": "P001",
                        "nom_complet": "CLIENT PERFECT",
                        "Phone_Prefixe": "243812345678",
                    }
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=prepared.transactions,
            current_savings=prepared.current_savings,
            fixed_savings=prepared.fixed_savings,
            loans=prepared.loans,
            load_report=prepared.load_report,
            g2_transactions=g2,
            perfect_clients=perfect,
        )

        report = build_perfect_client_crosscheck(prepared)
        summary = report["synthese"]
        clients_trois_systemes = report["clients_trois_systemes"]

        self.assertEqual(len(clients_trois_systemes), 1)
        self.assertTrue(bool(summary.loc[0, "present_dans_turbo"]))
        self.assertTrue(bool(summary.loc[0, "present_dans_g2"]))
        self.assertTrue(bool(summary.loc[0, "present_dans_perfect"]))
        self.assertTrue(bool(summary.loc[0, "present_dans_les_3_systemes"]))
        self.assertEqual(
            summary.loc[0, "statut_presence_systemes"],
            "Present dans G2, Turbo et Perfect",
        )
        self.assertEqual(clients_trois_systemes.loc[0, "noms_clients_perfect"], "CLIENT PERFECT")
        self.assertEqual(len(report["clients_perfect_dans_mpesa"]), 1)
        self.assertEqual(len(report["clients_perfect_dans_turbo"]), 1)
        self.assertEqual(len(report["clients_perfect_dans_turbo_et_mpesa"]), 1)
        export = create_excel_export({"clients_3_systemes": clients_trois_systemes})
        exported = pd.read_excel(BytesIO(export), sheet_name="Clients_Perfect_3_Systemes")
        self.assertEqual(len(exported), 1)
        self.assertEqual(exported.loc[0, "phone_prefixe"], 243812345678)

    def test_perfect_crosscheck_builds_the_three_requested_populations(self) -> None:
        prepared = _sample_prepared_data()
        turbo_extra = prepared.transactions.iloc[[0]].copy()
        turbo_extra["id"] = "TURBO-B"
        turbo_extra["customer_id"] = "2002"
        turbo_extra["msisdn1"] = "243822222222"
        turbo_extra["ref_no"] = "TURBO-B"
        turbo_extra["reference_id"] = "TURBO-B"
        transactions = pd.concat([prepared.transactions, turbo_extra], ignore_index=True)
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "G2-A",
                        "Completion Time": "2026-07-01 11:00:00",
                        "Opposite Party": "0833333333 - CLIENT A",
                        "Currency": "CDF",
                        "Transaction Amount": 500,
                        "Details": "BisouBisouC2B",
                    },
                    {
                        "Receipt No.": "TX001",
                        "Completion Time": "2026-07-01 10:00:00",
                        "Opposite Party": "0812345678 - CLIENT C",
                        "Currency": "CDF",
                        "Transaction Amount": 1000,
                        "Details": "BisouBisouC2B",
                    },
                ]
            )
        )
        perfect = prepare_perfect_clients(
            pd.DataFrame(
                [
                    {"id_client": 1, "nom_complet": "PERFECT A", "Phone_Prefixe": "243833333333"},
                    {"id_client": 2, "nom_complet": "PERFECT B", "Phone_Prefixe": "243822222222"},
                    {"id_client": 3, "nom_complet": "PERFECT C", "Phone_Prefixe": "243812345678"},
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=transactions,
            current_savings=prepared.current_savings,
            fixed_savings=prepared.fixed_savings,
            loans=prepared.loans,
            load_report=prepared.load_report,
            g2_transactions=g2,
            perfect_clients=perfect,
        )

        report = build_perfect_client_crosscheck(prepared)

        self.assertEqual(
            set(report["clients_perfect_dans_mpesa"]["phone_prefixe"]),
            {"243833333333", "243812345678"},
        )
        self.assertEqual(
            set(report["clients_perfect_dans_turbo"]["phone_prefixe"]),
            {"243822222222", "243812345678"},
        )
        self.assertEqual(
            report["clients_perfect_dans_turbo_et_mpesa"]["phone_prefixe"].tolist(),
            ["243812345678"],
        )
        export = create_excel_export(
            {
                "clients_perfect_dans_mpesa": report["clients_perfect_dans_mpesa"],
                "clients_perfect_dans_turbo": report["clients_perfect_dans_turbo"],
                "clients_perfect_dans_turbo_et_mpesa": report["clients_perfect_dans_turbo_et_mpesa"],
            }
        )
        workbook = pd.ExcelFile(BytesIO(export), engine="openpyxl")
        self.assertEqual(
            workbook.sheet_names,
            ["Clients_Perfect_G2", "Clients_Perfect_Turbo", "Clients_Perfect_Turbo_G2"],
        )

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

    def test_search_customer_identifies_clients_turbo_as_its_own_source(self) -> None:
        customers = prepare_customers(
            pd.DataFrame(
                [
                    {
                        "customer_id": "CLIENT-TURBO-1",
                        "msisdn1": "0811111111",
                        "created_at": "2026-07-01 08:00:00",
                    }
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            customers=customers,
        )

        result = search_customers("CLIENT-TURBO-1", prepared)

        self.assertEqual(result["customer_id"].tolist(), ["CLIENT-TURBO-1"])
        self.assertEqual(result["source"].tolist(), ["Clients_Turbo"])

    def test_build_statement_reconstructs_balances_and_loans(self) -> None:
        prepared = _sample_prepared_data()

        report = build_mpesa_statement(prepared, "1001", {"CDF": 10000})
        statement = report["extrait"]

        self.assertEqual(report["mode_source_extrait"], "Turbo seul")
        self.assertFalse(report["controle_g2_disponible"])
        self.assertFalse(report["nom_client_enrichi_g2"])
        self.assertTrue(report["g2_dat"].empty)
        self.assertEqual(len(statement), 2)
        self.assertIn("solde_mpesa_apres", statement.columns)
        self.assertEqual(float(statement.iloc[-1]["solde_mpesa_apres"]), 11000.0)
        self.assertIn("loan_balance", statement.columns)
        self.assertEqual(float(statement["dat_final_client"].iloc[0]), 5000.0)

    def test_customer_transaction_analysis_reconstructs_credit_internal_dat_and_positions(self) -> None:
        prepared = _sample_customer_transaction_analysis_data()

        analysis = build_customer_transaction_analysis(prepared, "CLIENT-ANALYSE")

        self.assertEqual(len(analysis["parcours_turbo"]), 5)
        credit = analysis["credit_turbo_synthese_client"].iloc[0]
        self.assertEqual(credit["currency_code"], "CDF")
        self.assertEqual(int(credit["nombre_decaissements"]), 1)
        self.assertEqual(float(credit["montant_decaisse_client"]), 100.0)
        self.assertEqual(float(credit["dette_creee_observee"]), 110.0)
        self.assertEqual(float(credit["interet_observe"]), 10.0)
        self.assertEqual(int(credit["nombre_remboursements"]), 1)
        self.assertEqual(float(credit["principal_rembourse"]), 40.0)
        self.assertEqual(int(credit["remboursements_avec_penalite"]), 1)
        self.assertEqual(float(credit["penalite_observee"]), 5.0)

        internal = analysis["mouvements_internes_turbo"]
        self.assertEqual(len(internal), 1)
        self.assertEqual(internal.iloc[0]["type_operation"], "Transfert DAT vers epargne courante")
        self.assertEqual(float(internal.iloc[0]["montant_operation"]), 20.0)

        positions = analysis["positions_turbo"].set_index("famille_position")
        self.assertEqual(float(positions.loc["Epargne courante", "solde_transactions_observe"]), 120.0)
        self.assertEqual(float(positions.loc["DAT", "solde_transactions_observe"]), 30.0)
        self.assertEqual(float(positions.loc["Credit", "solde_transactions_observe"]), 60.0)
        self.assertTrue(positions["statut_rapprochement_solde"].eq("Conforme").all())
        self.assertTrue(
            analysis["controles_client_turbo"]["statut_controle_turbo"].eq("Conforme").all()
        )

    def test_customer_transaction_analysis_applies_currency_type_date_and_reference_filters(self) -> None:
        prepared = _sample_customer_transaction_analysis_data()

        analysis = build_customer_transaction_analysis(
            prepared,
            "CLIENT-ANALYSE",
            currency="CDF",
            operation_types=["Sortie M-PESA_Turbo vers DAT"],
            date_start=pd.Timestamp("2026-07-02").date(),
            date_end=pd.Timestamp("2026-07-02").date(),
            reference_query="DAT-DEP-1",
        )

        self.assertEqual(len(analysis["parcours_turbo"]), 1)
        self.assertEqual(
            analysis["parcours_turbo"].iloc[0]["type_operation"],
            "Sortie M-PESA_Turbo vers DAT",
        )
        self.assertTrue(analysis["credit_turbo_detail_client"].empty)
        self.assertEqual(analysis["jalons_turbo"]["nombre_operations"].tolist(), [1])
        self.assertTrue(
            analysis["positions_turbo"]["statut_rapprochement_solde"]
            .astype(str)
            .str.contains("Non comparable")
            .any()
        )

    def test_customer_statement_uses_g2_only_for_name_and_selected_customer_control(self) -> None:
        transactions = prepare_transactions(
            pd.DataFrame(
                [
                    {
                        "id": 1,
                        "customer_id": 1001,
                        "msisdn1": "0811111111",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "SA-1001",
                        "currency_code": "CDF",
                        "dr": 100,
                        "cr": 0,
                        "bal_before": 500,
                        "bal_after": 400,
                        "ref_no": "G2-1001",
                        "description": "M-Pesa Compte",
                        "created_at": "2026-07-15 08:00:00",
                    },
                    {
                        "id": 2,
                        "customer_id": 2002,
                        "msisdn1": "0822222222",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "SA-2002",
                        "currency_code": "CDF",
                        "dr": 200,
                        "cr": 0,
                        "bal_before": 800,
                        "bal_after": 600,
                        "ref_no": "G2-2002",
                        "description": "M-Pesa Compte",
                        "created_at": "2026-07-15 09:00:00",
                    },
                ]
            )
        )
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "G2-1001",
                        "Initiation Time": "2026-07-15 08:00:00",
                        "Completion Time": "2026-07-15 08:00:10",
                        "Details": "BisouBisouC2B",
                        "Transaction Status": "Completed",
                        "Currency": "CDF",
                        "Paid In": 100,
                        "Opposite Party": "0811111111 - CLIENT UN",
                    },
                    {
                        "Receipt No.": "G2-2002",
                        "Initiation Time": "2026-07-15 09:00:00",
                        "Completion Time": "2026-07-15 09:00:10",
                        "Details": "BisouBisouC2B",
                        "Transaction Status": "Completed",
                        "Currency": "CDF",
                        "Paid In": 200,
                        "Opposite Party": "0822222222 - CLIENT DEUX",
                    },
                ]
            )
        )
        transactions = enrich_transactions_with_g2_customer_names(transactions, g2)
        prepared = MpesaPreparedData(
            transactions=transactions,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
        )

        report = build_mpesa_statement(prepared, "1001", {"CDF": None})

        self.assertEqual(report["mode_source_extrait"], "Turbo + verification G2")
        self.assertTrue(report["controle_g2_disponible"])
        self.assertTrue(report["nom_client_enrichi_g2"])
        self.assertEqual(report["extrait"]["Nom_client"].dropna().unique().tolist(), ["CLIENT UN"])
        self.assertEqual(report["g2_dat"]["receipt_no"].tolist(), ["G2-1001"])
        official_view = build_customer_statement_view(report["extrait"], account_number="1441")
        official_description = official_view["transactions"].iloc[0]["description"]
        self.assertIn("M-Pesa Compte", official_description)
        self.assertIn("CLIENT UN", official_description)
        self.assertNotIn("BisouBisouC2B", official_description)

    def test_customer_statement_view_matches_the_short_statement_contract(self) -> None:
        prepared = _sample_prepared_data()
        report = build_mpesa_statement(prepared, "1001", {"CDF": 10000})
        statement = report["extrait"].copy()
        statement["Nom_client"] = "CLIENT TEST"

        view = build_customer_statement_view(statement, account_number="1441")

        self.assertEqual(list(view["transactions"].columns), CUSTOMER_STATEMENT_COLUMNS)
        self.assertEqual(view["currency"], "CDF")
        self.assertTrue(view["balance_is_real"])
        self.assertEqual(view["balance_label"], "Solde")
        self.assertEqual(float(view["opening_amount"]), 10000.0)
        self.assertEqual(float(view["total_entries"]), 1000.0)
        self.assertEqual(float(view["total_outputs"]), 2000.0)
        self.assertEqual(float(view["closing_amount"]), 9000.0)
        self.assertTrue(view["transactions"]["compte"].eq("1441").all())
        self.assertTrue(view["transactions"]["devise"].eq("CDF").all())
        first_description = view["transactions"].iloc[0]["description"]
        self.assertIn("M-Pesa Compte", first_description)
        self.assertIn("Depot Bloque", first_description)
        self.assertIn("CLIENT TEST", first_description)

        relative_report = build_mpesa_statement(prepared, "1001", {"CDF": None})
        relative_view = build_customer_statement_view(relative_report["extrait"], account_number="1441")
        self.assertFalse(relative_view["balance_is_real"])
        self.assertEqual(relative_view["balance_label"], "Cumul net")
        self.assertEqual(float(relative_view["opening_amount"]), 0.0)
        self.assertEqual(float(relative_view["closing_amount"]), -1000.0)

    def test_customer_statement_filename_uses_turbo_identity_and_optional_g2_name(self) -> None:
        turbo_only = build_customer_statement_filename(
            customer_id="37335",
            customer_name="CE NOM DOIT ETRE IGNORE",
            telephone="243827972206",
            currency="USD",
            period_start=pd.Timestamp("2026-07-09"),
            period_end=pd.Timestamp("2026-07-15"),
            g2_available=False,
        )
        turbo_with_g2 = build_customer_statement_filename(
            customer_id="37335",
            customer_name="ELIANE LUAMBA MULEMBO",
            telephone="243827972206",
            currency="USD",
            period_start=pd.Timestamp("2026-07-09"),
            period_end=pd.Timestamp("2026-07-15"),
            g2_available=True,
        )

        self.assertEqual(
            turbo_only,
            "extrait_compte_37335_243827972206_USD_20260709_20260715.docx",
        )
        self.assertEqual(
            turbo_with_g2,
            "extrait_compte_37335_ELIANE LUAMBA MULEMBO_243827972206_USD_20260709_20260715.docx",
        )

    def test_turbo_withdrawals_are_unique_default_outputs_in_customer_statement(self) -> None:
        amounts = [20.0, 30.0, 35.0, 6.0, 50.0, 10.0, 40.0]
        dates = pd.to_datetime(
            [
                "2026-07-09 23:47:49",
                "2026-07-11 14:03:57",
                "2026-07-12 18:00:12",
                "2026-07-13 07:49:05",
                "2026-07-14 14:42:18",
                "2026-07-14 16:29:23",
                "2026-07-15 08:48:11",
            ]
        )
        rows: list[dict[str, object]] = []
        for index, (amount, created_at) in enumerate(zip(amounts, dates, strict=True), start=1):
            rows.extend(
                [
                    {
                        "id": index * 2 - 1,
                        "customer_id": "37301",
                        "msisdn1": "243814256725",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "SA8G57RHR4",
                        "currency_code": "USD",
                        "dr": 0.0,
                        "cr": amount,
                        "bal_before": 0.0,
                        "bal_after": amount,
                        "ref_no": "",
                        "description": "Retrait Vers M-Pesa",
                        "created_at": created_at,
                    },
                    {
                        "id": index * 2,
                        "customer_id": "37301",
                        "msisdn1": "243814256725",
                        "account_type": "NORMAL SAVINGS",
                        "reference_id": "SA8G57RHR4",
                        "currency_code": "USD",
                        "dr": amount,
                        "cr": 0.0,
                        "bal_before": amount,
                        "bal_after": 0.0,
                        "ref_no": "",
                        "description": "Retrait Vers M-Pesa",
                        "created_at": created_at,
                    },
                ]
            )
        transactions = prepare_transactions(pd.DataFrame(rows))
        prepared = MpesaPreparedData(
            transactions=transactions,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=pd.DataFrame(),
        )

        statement = build_mpesa_statement(prepared, "37301")["extrait"]
        focused = statement.loc[
            statement["type_operation"].isin(CUSTOMER_STATEMENT_FOCUS_OPERATION_TYPES)
        ].copy()
        view = build_customer_statement_view(
            focused,
            entry_account_number="1441",
            output_account_number="15558",
        )

        self.assertEqual(len(focused), 7)
        self.assertTrue(focused["type_operation"].eq("Entree M-PESA_Turbo depuis epargne").all())
        self.assertEqual(float(view["total_entries"]), 0.0)
        self.assertEqual(float(view["total_outputs"]), 191.0)
        self.assertTrue(view["transactions"]["compte"].eq("15558").all())
        self.assertEqual(len(view["transactions"]), 7)

    def test_customer_statement_word_is_editable_filtered_and_single_currency(self) -> None:
        from docx import Document
        from docx.enum.section import WD_ORIENT

        prepared = _sample_prepared_data()
        report = build_mpesa_statement(prepared, "1001", {"CDF": 10000})
        statement = report["extrait"].copy()
        statement["Nom_client"] = "CLIENT TEST"

        content = create_customer_statement_word(
            statement,
            customer_id="1001",
            customer_name="CLIENT TEST",
            telephone="243812345678",
            currency="CDF",
            entry_account_number="1441",
            output_account_number="15558",
            period_start=pd.Timestamp("2026-07-01"),
            period_end=pd.Timestamp("2026-07-02"),
            generated_at=pd.Timestamp("2026-07-15 10:30:00"),
        )

        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        statement_tables = [
            table
            for table in document.tables
            if table.rows and table.rows[0].cells[0].text == "Date"
        ]
        self.assertTrue(content.startswith(b"PK"))
        self.assertIn("Extrait de compte - 243812345678 - CLIENT TEST - CDF", text)
        self.assertNotIn("[Turbo]", text)
        self.assertEqual(len(statement_tables), 1)
        self.assertEqual(
            [cell.text for cell in statement_tables[0].rows[0].cells],
            ["Date", "Compte", "Receipt No", "Devise", "Description", "Entrée", "Sortie", "Solde"],
        )
        self.assertEqual(statement_tables[0].rows[1].cells[1].text, "1441")
        self.assertEqual(statement_tables[0].rows[1].cells[2].text, "TX001")
        self.assertEqual(statement_tables[0].rows[1].cells[3].text, "CDF")
        self.assertIn("M-Pesa Compte", statement_tables[0].rows[1].cells[4].text)
        self.assertEqual(statement_tables[0].rows[2].cells[1].text, "15558")
        criteria_table = document.tables[0].cell(1, 1).tables[0]
        criteria_labels = [row.cells[0].text for row in criteria_table.rows]
        self.assertIn("Devise :", criteria_labels)
        self.assertNotIn("Compte :", criteria_labels)
        self.assertEqual(document.sections[0].orientation, WD_ORIENT.LANDSCAPE)
        self.assertGreaterEqual(len(document.inline_shapes), 1)

        relative_statement = build_mpesa_statement(prepared, "1001", {"CDF": None})["extrait"]
        relative_content = create_customer_statement_word(
            relative_statement,
            customer_id="1001",
            customer_name="NON DISPONIBLE",
            telephone="243812345678",
            currency="CDF",
            entry_account_number="1441",
            output_account_number="15558",
        )
        relative_document = Document(BytesIO(relative_content))
        relative_tables = [
            table
            for table in relative_document.tables
            if table.rows and table.rows[0].cells[0].text == "Date"
        ]
        relative_text = "\n".join(paragraph.text for paragraph in relative_document.paragraphs)
        self.assertEqual(relative_tables[0].rows[0].cells[-1].text, "Cumul net")
        self.assertNotIn("le solde d'ouverture n'a pas ete fourni", relative_text)
        self.assertIn("Extrait de compte - 243812345678 - CDF", relative_text)
        self.assertNotIn("Extrait de compte - 243812345678 - NON DISPONIBLE - CDF", relative_text)

    def test_customer_statement_pdf_contains_logo_and_keeps_currency_totals_separate(self) -> None:
        prepared = _sample_prepared_data()
        cdf_statement = build_mpesa_statement(prepared, "1001", {"CDF": None})["extrait"]
        usd_statement = cdf_statement.copy()
        usd_statement["currency_code"] = "USD"
        usd_statement["operation_reference"] = "USD-" + usd_statement["operation_reference"].astype(str)
        combined = pd.concat([cdf_statement, usd_statement], ignore_index=True)

        content = create_customer_statement_pdf(
            combined,
            customer_id="1001",
            customer_name="CLIENT TEST",
            telephone="243812345678",
            currency="ALL",
            entry_account_number="1441",
            output_account_number="15558",
            generated_at=pd.Timestamp("2026-07-16 10:30:00"),
        )

        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertGreater(len(content), 5_000)
        self.assertIn(b"/Subtype /Image", content)

    def test_customer_statement_word_includes_filtered_turbo_analyses(self) -> None:
        from docx import Document

        prepared = _sample_customer_transaction_analysis_data()
        report = build_mpesa_statement(prepared, "CLIENT-ANALYSE", {"CDF": None})
        analysis = build_customer_transaction_analysis(prepared, "CLIENT-ANALYSE")

        content = create_customer_statement_word(
            report["extrait"],
            analysis_report=analysis,
            customer_id="CLIENT-ANALYSE",
            customer_name="CLIENT ANALYSE",
            telephone="243812345678",
            currency="CDF",
            entry_account_number="1441",
            output_account_number="15558",
        )

        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        footer_text = "\n".join(
            paragraph.text
            for section in document.sections
            for paragraph in section.footer.paragraphs
        )
        self.assertNotIn("Synthese du comportement observe", text)
        self.assertIn("Credit et remboursements observes", text)
        self.assertNotIn("Positions observees et rapprochement des soldes", text)
        self.assertNotIn("Jalons du parcours financier", text)
        self.assertIn("Mouvements internes epargne / DAT", text)
        self.assertIn("Detail des transactions", text)
        self.assertNotIn("[Turbo]", text)
        self.assertIn("Solution Bisou Bisou Digital", footer_text)
        self.assertNotIn("Solution Controle Interne", footer_text)

    def test_customer_statement_word_all_keeps_currency_totals_separate(self) -> None:
        from docx import Document

        prepared = _sample_prepared_data()
        cdf_statement = build_mpesa_statement(prepared, "1001", {"CDF": None})["extrait"]
        usd_statement = cdf_statement.copy()
        usd_statement["currency_code"] = "USD"
        usd_statement["operation_reference"] = "USD-" + usd_statement["operation_reference"].astype(str)
        combined = pd.concat([cdf_statement, usd_statement], ignore_index=True)

        view = build_customer_statement_view(
            combined,
            entry_account_number="1441",
            output_account_number="15558",
            allow_multiple_currencies=True,
        )
        self.assertEqual(view["currency"], "ALL")
        self.assertTrue(pd.isna(view["total_entries"]))
        self.assertEqual(set(view["summary_by_currency"]["currency_code"]), {"CDF", "USD"})

        content = create_customer_statement_word(
            combined,
            customer_id="1001",
            customer_name="CLIENT TEST",
            telephone="243812345678",
            currency="ALL",
            entry_account_number="1441",
            output_account_number="15558",
            generated_at=pd.Timestamp("2026-07-16 10:30:00"),
        )
        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        statement_table = next(
            table for table in document.tables if table.rows[0].cells[0].text == "Date"
        )
        summary_table = next(
            table
            for table in document.tables
            if table.rows[0].cells[0].text == "Devise" and len(table.rows[0].cells) == 5
        )
        self.assertIn("ALL (CDF, USD)", text)
        self.assertEqual(
            {row.cells[0].text.split()[0] for row in summary_table.rows[1:]},
            {"CDF", "USD"},
        )
        self.assertEqual(
            {row.cells[3].text for row in statement_table.rows[1:]},
            {"CDF", "USD"},
        )
        self.assertEqual(
            {row.cells[1].text for row in statement_table.rows[1:]},
            {"1441", "15558"},
        )

    def test_excel_export_contains_content(self) -> None:
        prepared = _sample_prepared_data()
        report = build_mpesa_statement(prepared, "1001", {"CDF": None})

        export = create_excel_export(report)

        self.assertGreater(len(export), 5000)

    def test_excel_export_writes_only_requested_sheets(self) -> None:
        export = create_excel_export(
            {
                "synthese": pd.DataFrame([{"indicateur": "Clients", "valeur": 1}]),
                "extrait": pd.DataFrame([{"operation_reference": "REF-001"}]),
            }
        )

        workbook = pd.ExcelFile(BytesIO(export), engine="openpyxl")

        self.assertEqual(workbook.sheet_names, ["Synthese", "Extrait_Turbo"])

    def test_customer_excel_export_preserves_filtered_extract_and_required_sheets(self) -> None:
        prepared = _sample_prepared_data()
        report = build_mpesa_statement(prepared, "1001", {"CDF": None})
        filtered_report = dict(report)
        filtered_report["extrait"] = report["extrait"].iloc[[0]].copy()

        export = create_excel_export(filtered_report)
        workbook = pd.ExcelFile(BytesIO(export), engine="openpyxl")
        required_sheets = {
            "Synthese",
            "Extrait_Turbo",
            "Parcours_Turbo",
            "Credit_Client_Turbo",
            "Positions_Turbo",
            "Comportement_Turbo",
            "Mouvements_Internes",
            "Controles_Client_Turbo",
            "DAT_Final",
            "Mouvements_DAT",
            "Mouvements_Epargne",
            "Credits",
            "G2_DAT",
            "Diagnostics",
        }

        self.assertTrue(required_sheets.issubset(workbook.sheet_names))
        exported_statement = pd.read_excel(workbook, sheet_name="Extrait_Turbo")
        exported_summary = pd.read_excel(workbook, sheet_name="Synthese")
        self.assertEqual(len(exported_statement), 1)
        self.assertEqual(len(exported_summary), len(report["synthese"]))
        self.assertIn("operation_reference", exported_statement.columns)
        self.assertIn("Nom_client", exported_statement.columns)
        self.assertIn("mouvement_net_mpesa", exported_statement.columns)

        filtered_report["extrait"] = report["extrait"].iloc[0:0].copy()
        empty_export = create_excel_export(filtered_report)
        empty_statement = pd.read_excel(BytesIO(empty_export), sheet_name="Extrait_Turbo")
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

    def test_daily_g2_report_uses_portal_reference_to_classify_each_receipt(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "REF-DAT",
                        "Completion Time": "2026-07-13 10:00:00",
                        "Opposite Party": "0811111111 - CLIENT A",
                        "Currency": "CDF",
                        "Transaction Amount": 5000,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    },
                    {
                        "Receipt No.": "REF-SAVE",
                        "Completion Time": "2026-07-13 10:05:00",
                        "Opposite Party": "0811111111 - CLIENT A",
                        "Currency": "CDF",
                        "Transaction Amount": 80000,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    },
                    {
                        "Receipt No.": "REF-LOAN",
                        "Completion Time": "2026-07-13 10:10:00",
                        "Opposite Party": "0811111111 - CLIENT A",
                        "Currency": "CDF",
                        "Transaction Amount": 1285,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    },
                ]
            )
        )
        portal_rows = []
        for ref_no, amount, target_type, description, minute in [
            ("REF-DAT", 5000, "FIXED SAVINGS", "Depot Bloque", "00"),
            ("REF-SAVE", 80000, "NORMAL SAVINGS", "Epargne depot", "05"),
            ("REF-LOAN", 1285, "LOAN ACCOUNT", "Remboursement", "10"),
        ]:
            portal_rows.extend(
                [
                    {
                        "customer_id": 1001,
                        "msisdn1": "0811111111",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": ref_no,
                        "currency_code": "CDF",
                        "dr": amount,
                        "cr": 0,
                        "bal_before": 100000,
                        "bal_after": 100000 - amount,
                        "ref_no": ref_no,
                        "description": "M-Pesa Compte",
                        "created_at": f"2026-07-13 10:{minute}:00",
                    },
                    {
                        "customer_id": 1001,
                        "msisdn1": "0811111111",
                        "account_type": target_type,
                        "reference_id": ref_no,
                        "currency_code": "CDF",
                        "dr": 0,
                        "cr": amount,
                        "bal_before": 0,
                        "bal_after": amount,
                        "ref_no": ref_no,
                        "description": description,
                        "created_at": f"2026-07-13 10:{minute}:00",
                    },
                ]
            )
        portal_frame = pd.DataFrame(portal_rows)
        portal_frame["id"] = range(1, len(portal_frame) + 1)
        prepared = MpesaPreparedData(
            transactions=prepare_transactions(portal_frame),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
        )

        report = build_g2_daily_savings_report(prepared)
        detail = report["detail"].set_index("receipt_no")

        self.assertEqual(detail.loc["REF-DAT", "details_rapport"], "DAT")
        self.assertEqual(detail.loc["REF-SAVE", "details_rapport"], "Depot normal")
        self.assertEqual(detail.loc["REF-LOAN", "details_rapport"], "Remboursement prets")
        self.assertTrue(detail["statut_rapprochement"].eq("Rapproche exact").all())
        self.assertTrue(report["anomalies"].empty)

    def test_g2_daily_report_falls_back_to_turbo_when_g2_is_absent(self) -> None:
        portal_rows = [
            {
                "id": 1,
                "customer_id": 1001,
                "msisdn1": "0811111111",
                "account_type": "MPESA ACCOUNT",
                "reference_id": "NORMAL-1",
                "currency_code": "CDF",
                "dr": 100,
                "cr": 0,
                "bal_before": 500,
                "bal_after": 400,
                "ref_no": "REF-NORMAL",
                "description": "M-Pesa Depot",
                "created_at": "2026-07-15 08:00:00",
            },
            {
                "id": 2,
                "customer_id": 1001,
                "msisdn1": "0811111111",
                "account_type": "NORMAL SAVINGS",
                "reference_id": "NORMAL-1",
                "currency_code": "CDF",
                "dr": 0,
                "cr": 100,
                "bal_before": 0,
                "bal_after": 100,
                "ref_no": "REF-NORMAL",
                "description": "Epargne depot",
                "created_at": "2026-07-15 08:00:00",
            },
            {
                "id": 3,
                "customer_id": 1001,
                "msisdn1": "0811111111",
                "account_type": "MPESA ACCOUNT",
                "reference_id": "FIXED-1",
                "currency_code": "CDF",
                "dr": 200,
                "cr": 0,
                "bal_before": 400,
                "bal_after": 200,
                "ref_no": "REF-DAT",
                "description": "M-Pesa Compte",
                "created_at": "2026-07-15 09:00:00",
            },
            {
                "id": 4,
                "customer_id": 1001,
                "msisdn1": "0811111111",
                "account_type": "FIXED SAVINGS",
                "reference_id": "FIXED-1",
                "currency_code": "CDF",
                "dr": 0,
                "cr": 200,
                "bal_before": 0,
                "bal_after": 200,
                "ref_no": "REF-DAT",
                "description": "Depot Bloque",
                "created_at": "2026-07-15 09:00:00",
            },
            {
                "id": 5,
                "customer_id": 1001,
                "msisdn1": "0811111111",
                "account_type": "NORMAL SAVINGS",
                "reference_id": "SA-OUT-1",
                "currency_code": "CDF",
                "dr": 50,
                "cr": 0,
                "bal_before": 100,
                "bal_after": 50,
                "ref_no": "",
                "description": "Retrait Vers M-Pesa",
                "created_at": "2026-07-15 10:00:00",
            },
            {
                "id": 6,
                "customer_id": 1001,
                "msisdn1": "0811111111",
                "account_type": "MPESA ACCOUNT",
                "reference_id": "SA-OUT-1",
                "currency_code": "CDF",
                "dr": 0,
                "cr": 50,
                "bal_before": 200,
                "bal_after": 250,
                "ref_no": "",
                "description": "Retrait Vers M-Pesa",
                "created_at": "2026-07-15 10:00:00",
            },
        ]
        transactions = prepare_transactions(pd.DataFrame(portal_rows))
        prepared = MpesaPreparedData(
            transactions=transactions,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
        )

        proxy = build_turbo_only_g2_transactions(transactions)
        report = build_g2_daily_savings_report(prepared)
        detail = report["detail"].set_index("details_rapport")

        self.assertEqual(len(proxy), 3)
        self.assertEqual(len(detail), 3)
        self.assertEqual(set(detail.index), {"Depot normal", "DAT", "Paiement client B2C"})
        self.assertEqual(int(detail["sens_flux"].eq("Entree").sum()), 2)
        self.assertEqual(int(detail["sens_flux"].eq("Sortie").sum()), 1)
        self.assertTrue(detail["source_analytique"].eq("Turbo seul").all())
        self.assertTrue(detail["statut_transaction_g2"].eq("Comptabilisee Turbo").all())
        self.assertTrue(detail["incluse_synthese"].all())
        self.assertTrue(detail["statut_rapprochement"].eq("Non applicable - Turbo seul").all())
        self.assertTrue(detail["controle_date"].eq("Non applicable - Turbo seul").all())
        self.assertTrue(report["anomalies"].empty)
        self.assertEqual(float(report["pivot"].iloc[0]["montant_total_entrees"]), 300.0)
        self.assertEqual(float(report["pivot"].iloc[0]["montant_total_sorties"]), 50.0)
        self.assertFalse(build_g2_retention_report(prepared, daily_detail=report["detail"])["mensuelle"].empty)

    def test_daily_g2_report_counts_duplicate_receipt_once_and_exports_anomaly(self) -> None:
        duplicate_rows = [
            {
                "Receipt No.": "DUP-001",
                "Completion Time": completion,
                "Opposite Party": "0811111111 - CLIENT A",
                "Currency": "CDF",
                "Transaction Amount": 5000,
                "Transaction Status": "Completed",
                "Details": "BisouBisouC2B",
            }
            for completion in ["2026-07-13 10:00:00", "2026-07-13 10:01:00"]
        ]
        portal_frame = pd.DataFrame(
                [
                    {
                        "customer_id": 1001,
                        "msisdn1": "0811111111",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "DUP-001",
                        "currency_code": "CDF",
                        "dr": 5000,
                        "cr": 0,
                        "bal_before": 10000,
                        "bal_after": 5000,
                        "ref_no": "DUP-001",
                        "description": "M-Pesa Compte",
                        "created_at": "2026-07-13 10:01:00",
                    },
                    {
                        "customer_id": 1001,
                        "msisdn1": "0811111111",
                        "account_type": "FIXED SAVINGS",
                        "reference_id": "FA-001",
                        "currency_code": "CDF",
                        "dr": 0,
                        "cr": 5000,
                        "bal_before": 0,
                        "bal_after": 5000,
                        "ref_no": "DUP-001",
                        "description": "Depot Bloque",
                        "created_at": "2026-07-13 10:01:00",
                    },
                ]
            )
        portal_frame["id"] = range(1, len(portal_frame) + 1)
        portal = prepare_transactions(portal_frame)
        prepared = MpesaPreparedData(
            transactions=portal,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=prepare_g2_transactions(pd.DataFrame(duplicate_rows)),
        )

        report = build_g2_daily_savings_report(prepared)

        self.assertEqual(len(report["detail"]), 1)
        self.assertEqual(int(report["detail"].iloc[0]["nombre_lignes_g2_reference"]), 2)
        self.assertEqual(float(report["pivot"].iloc[0]["montant_DAT"]), 5000.0)
        self.assertEqual(len(report["anomalies"]), 1)
        self.assertIn("Receipt No duplique", report["anomalies"].iloc[0]["motif_anomalie"])

    def test_g2_statuses_are_traced_but_only_completed_transactions_feed_analyses(self) -> None:
        statuses = ["Completed", "Declined", "Cancelled", "Expired", "Pending", ""]
        raw = pd.DataFrame(
            [
                {
                    "Receipt No.": f"STATUS-{index}",
                    "Completion Time": f"2026-07-15 {8 + index:02d}:00:00",
                    "Details": "BisouBisouC2B",
                    "Transaction Status": status,
                    "Currency": "CDF",
                    "Paid In": 1000,
                    "Withdrawn": 0,
                    "Opposite Party": f"08111111{index:02d} - CLIENT {index}",
                    "Fichier source G2": "statuts_entrees.xlsx",
                }
                for index, status in enumerate(statuses)
            ]
        )
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=prepare_g2_transactions(raw),
        )

        report = build_g2_daily_savings_report(prepared)
        detail = report["detail"].set_index("transaction_status")

        self.assertEqual(len(detail), 6)
        self.assertTrue(bool(detail.loc["Completed", "incluse_synthese"]))
        for status in ["Declined", "Cancelled", "Expired", "Pending", ""]:
            self.assertFalse(bool(detail.loc[status, "incluse_synthese"]))
        self.assertEqual(float(report["pivot"].iloc[0]["montant_total_entrees"]), 1000.0)
        self.assertEqual(int(report["pivot"].iloc[0]["nombre_entrees"]), 1)
        self.assertEqual(
            int(build_g2_transaction_time_analysis(report["detail"])["par_heure"]["nombre_transactions"].sum()),
            1,
        )
        status_summary = report["statuts"].set_index("statut_transaction_g2")
        self.assertEqual(int(status_summary.loc["Completed", "nombre_transactions"]), 1)
        self.assertEqual(status_summary.loc["Completed", "prise_en_compte_analyse"], "Oui")
        self.assertEqual(status_summary.loc["Declined", "prise_en_compte_analyse"], "Non - controle uniquement")
        self.assertIn("Non renseigne", status_summary.index)
        self.assertEqual(set(report["detail"]["fichier_source_g2"]), {"statuts_entrees.xlsx"})

    def test_g2_completed_b2c_withdrawals_are_integrated_as_outputs(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "Receipt No.": "B2C-OUT-001",
                    "Completion Time": "2026-07-15 14:17:59",
                    "Details": "Bisou Bisou B2C payment from 15558 to 243811495678 - CLIENT SORTIE",
                    "Transaction Status": "Completed",
                    "Currency": "USD",
                    "Paid In": pd.NA,
                    "Withdrawn": -200,
                    "Balance": 81859.97,
                    "Opposite Party": "243811495678 - CLIENT SORTIE",
                    "Fichier source G2": "sorties_g2.xlsx",
                }
            ]
        )
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=prepare_g2_transactions(raw),
        )

        report = build_g2_daily_savings_report(prepared)
        row = report["detail"].iloc[0]

        self.assertEqual(row["sens_flux"], "Sortie")
        self.assertEqual(row["details_rapport"], "Paiement client B2C")
        self.assertEqual(float(row["montant_sortie"]), 200.0)
        self.assertEqual(int(report["pivot"].iloc[0]["nombre_sorties"]), 1)
        self.assertEqual(float(report["pivot"].iloc[0]["montant_total_sorties"]), 200.0)
        self.assertEqual(row["fichier_source_g2"], "sorties_g2.xlsx")

    def test_g2_b2c_output_matches_turbo_withdrawal_without_ref_no(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "G2-OUTPUT-001",
                        "Initiation Time": "2026-07-15 14:17:59",
                        "Completion Time": "2026-07-15 14:17:59",
                        "Details": "Bisou Bisou B2C payment to 243811495678 - CLIENT SORTIE",
                        "Reason Type": "BisouBisouB2C",
                        "Transaction Status": "Completed",
                        "Currency": "USD",
                        "Paid In": pd.NA,
                        "Withdrawn": -200,
                        "Opposite Party": "243811495678 - CLIENT SORTIE",
                    }
                ]
            )
        )
        turbo = prepare_transactions(
            pd.DataFrame(
                [
                    {
                        "id": 1,
                        "customer_id": 321,
                        "msisdn1": "243811495678",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "SA-OUTPUT-001",
                        "currency_code": "USD",
                        "dr": 0,
                        "cr": 200,
                        "bal_before": 0,
                        "bal_after": 200,
                        "ref_no": pd.NA,
                        "description": "Retrait Vers M-Pesa",
                        "created_at": "2026-07-15 13:17:58",
                    },
                    {
                        "id": 2,
                        "customer_id": 321,
                        "msisdn1": "243811495678",
                        "account_type": "NORMAL SAVINGS",
                        "reference_id": "SA-OUTPUT-001",
                        "currency_code": "USD",
                        "dr": 200,
                        "cr": 0,
                        "bal_before": 400,
                        "bal_after": 200,
                        "ref_no": pd.NA,
                        "description": "Retrait Vers M-Pesa",
                        "created_at": "2026-07-15 13:17:58",
                    },
                    {
                        "id": 3,
                        "customer_id": 321,
                        "msisdn1": "243811495678",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "SA-OUTPUT-001",
                        "currency_code": "USD",
                        "dr": 0,
                        "cr": 200,
                        "bal_before": 0,
                        "bal_after": 200,
                        "ref_no": pd.NA,
                        "description": "Retrait Vers M-Pesa",
                        "created_at": "2026-07-14 10:00:00",
                    },
                    {
                        "id": 4,
                        "customer_id": 321,
                        "msisdn1": "243811495678",
                        "account_type": "NORMAL SAVINGS",
                        "reference_id": "SA-OUTPUT-001",
                        "currency_code": "USD",
                        "dr": 200,
                        "cr": 0,
                        "bal_before": 600,
                        "bal_after": 400,
                        "ref_no": pd.NA,
                        "description": "Retrait Vers M-Pesa",
                        "created_at": "2026-07-14 10:00:00",
                    },
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=turbo,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
        )

        report = build_g2_daily_savings_report(prepared)
        row = report["detail"].iloc[0]

        self.assertTrue(pd.isna(row["ref_no_portal"]))
        self.assertEqual(row["reference_sortie_turbo"], "SA-OUTPUT-001")
        self.assertEqual(
            row["methode_rapprochement_turbo"],
            "Telephone + devise + montant + heure (sortie)",
        )
        self.assertEqual(row["operation_turbo_confirmee"], "Retrait epargne vers M-PESA")
        self.assertEqual(row["customer_id_portal"], "321")
        self.assertEqual(int(row["nombre_candidats_sortie_turbo"]), 1)
        self.assertEqual(row["controle_telephone"], "Conforme")
        self.assertEqual(row["controle_devise"], "Conforme")
        self.assertEqual(row["controle_montant"], "Conforme")
        self.assertAlmostEqual(float(row["ecart_creation_minutes"]), 60.0166667, places=4)
        self.assertEqual(row["controle_date_creation"], "Ecart de date")
        self.assertEqual(row["statut_rapprochement"], "Rapproche avec ecart")
        self.assertEqual(row["source_analytique"], "G2 + Turbo")
        self.assertEqual(len(report["anomalies"]), 1)
        self.assertIn("Ecart de date de creation", row["motif_anomalie"])

    def test_g2_turbo_gap_of_exactly_60_minutes_is_accepted(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "G2-OUTPUT-060",
                        "Initiation Time": "2026-07-16 11:00:00",
                        "Completion Time": "2026-07-16 11:00:00",
                        "Details": "Bisou Bisou B2C payment to 243811495678 - CLIENT SORTIE",
                        "Reason Type": "BisouBisouB2C",
                        "Transaction Status": "Completed",
                        "Currency": "USD",
                        "Paid In": pd.NA,
                        "Withdrawn": -200,
                        "Opposite Party": "243811495678 - CLIENT SORTIE",
                    }
                ]
            )
        )
        turbo = prepare_transactions(
            pd.DataFrame(
                [
                    {
                        "id": 1,
                        "customer_id": 321,
                        "msisdn1": "243811495678",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "SA-OUTPUT-060",
                        "currency_code": "USD",
                        "dr": 0,
                        "cr": 200,
                        "bal_before": 0,
                        "bal_after": 200,
                        "ref_no": pd.NA,
                        "description": "Retrait Vers M-Pesa",
                        "created_at": "2026-07-16 10:00:00",
                    },
                    {
                        "id": 2,
                        "customer_id": 321,
                        "msisdn1": "243811495678",
                        "account_type": "NORMAL SAVINGS",
                        "reference_id": "SA-OUTPUT-060",
                        "currency_code": "USD",
                        "dr": 200,
                        "cr": 0,
                        "bal_before": 400,
                        "bal_after": 200,
                        "ref_no": pd.NA,
                        "description": "Retrait Vers M-Pesa",
                        "created_at": "2026-07-16 10:00:00",
                    },
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=turbo,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
        )

        row = build_g2_daily_savings_report(prepared)["detail"].iloc[0]

        self.assertEqual(float(row["ecart_creation_minutes"]), 60.0)
        self.assertEqual(row["controle_date_creation"], "Conforme")
        self.assertEqual(row["statut_rapprochement"], "Rapproche exact")
        self.assertNotIn("Ecart de date de creation", row["motif_anomalie"])

    def test_daily_g2_report_retains_phone_currency_amount_and_date_gaps(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "GAP-001",
                        "Completion Time": "2026-07-13 10:00:00",
                        "Opposite Party": "0811111111 - CLIENT A",
                        "Currency": "CDF",
                        "Transaction Amount": 5000,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    }
                ]
            )
        )
        portal_frame = pd.DataFrame(
                [
                    {
                        "customer_id": 9999,
                        "msisdn1": "0899999999",
                        "account_type": "FIXED SAVINGS",
                        "reference_id": "FA-GAP",
                        "currency_code": "USD",
                        "dr": 0,
                        "cr": 4000,
                        "bal_before": 0,
                        "bal_after": 4000,
                        "ref_no": "GAP-001",
                        "description": "Depot Bloque",
                        "created_at": "2026-07-14 10:00:00",
                    }
                ]
            )
        portal_frame["id"] = range(1, len(portal_frame) + 1)
        portal = prepare_transactions(portal_frame)
        prepared = MpesaPreparedData(
            transactions=portal,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
        )

        report = build_g2_daily_savings_report(prepared)
        row = report["detail"].iloc[0]

        self.assertEqual(row["statut_rapprochement"], "Rapproche avec ecart")
        self.assertEqual(row["controle_telephone"], "Ecart")
        self.assertEqual(row["controle_devise"], "Ecart")
        self.assertEqual(row["controle_montant"], "Ecart")
        self.assertEqual(row["controle_date"], "Ecart de date")
        self.assertEqual(row["controle_date_creation"], "Ecart de date")
        self.assertEqual(row["source_date_creation_g2"], "Completion Time (repli)")
        self.assertEqual(float(row["ecart_creation_minutes"]), -1440.0)
        self.assertIn("Creation G2 : 13/07/2026 10:00:00", row["Observation"])
        self.assertIn("Creation Turbo : 14/07/2026 10:00:00", row["Observation"])
        self.assertIn("Decalage creation : 1440 minute(s)", row["Observation"])
        self.assertEqual(len(report["anomalies"]), 1)
        self.assertIn("Observation", report["anomalies"].columns)
        self.assertIn("Ecart de montant", row["motif_anomalie"])

    def test_g2_creation_date_uses_initiation_time_and_treats_midnight_completion_as_delay(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "MIDNIGHT-001",
                        "Initiation Time": "2026-07-13 23:59:00",
                        "Completion Time": "2026-07-14 00:01:00",
                        "Opposite Party": "0811111111 - CLIENT A",
                        "Currency": "CDF",
                        "Transaction Amount": 5000,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    }
                ]
            )
        )
        portal = prepare_transactions(
            pd.DataFrame(
                [
                    {
                        "id": 1,
                        "customer_id": 9999,
                        "msisdn1": "0811111111",
                        "account_type": "NORMAL SAVINGS",
                        "reference_id": "SA-MIDNIGHT",
                        "currency_code": "CDF",
                        "dr": 0,
                        "cr": 5000,
                        "bal_before": 0,
                        "bal_after": 5000,
                        "ref_no": "MIDNIGHT-001",
                        "description": "Epargne depot",
                        "created_at": "2026-07-13 23:59:00",
                    }
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=portal,
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
        )

        report = build_g2_daily_savings_report(prepared)
        row = report["detail"].iloc[0]

        self.assertEqual(row["source_date_creation_g2"], "Initiation Time")
        self.assertEqual(row["date_creation_g2"], pd.Timestamp("2026-07-13 23:59:00"))
        self.assertEqual(row["date_creation_turbo"], pd.Timestamp("2026-07-13 23:59:00"))
        self.assertEqual(row["date_finalisation_g2"], pd.Timestamp("2026-07-14 00:01:00"))
        self.assertEqual(float(row["ecart_creation_minutes"]), 0.0)
        self.assertEqual(float(row["delai_traitement_g2_minutes"]), 2.0)
        self.assertEqual(float(row["ecart_finalisation_minutes"]), 2.0)
        self.assertEqual(row["controle_date_creation"], "Conforme")
        self.assertEqual(row["controle_date"], "Conforme")
        self.assertEqual(row["controle_date_finalisation"], "Conforme - passage de date")
        self.assertEqual(row["statut_rapprochement"], "Rapproche exact")
        self.assertIn("Creation conforme; finalisation sur une autre date", row["Observation"])
        self.assertIn("Delai traitement G2 : 2 minute(s)", row["Observation"])
        self.assertTrue(report["anomalies"].empty)

    def test_g2_transaction_time_analysis_counts_days_hours_and_fills_inactive_hours(self) -> None:
        detail = pd.DataFrame(
            [
                {
                    "date": "2026-07-14 09:05:00",
                    "receipt_no": "DAY-001",
                    "currency_code": "CDF",
                    "sens_flux": "Entree",
                    "incluse_synthese": True,
                },
                {
                    "date": "2026-07-14 09:45:00",
                    "receipt_no": "DAY-002",
                    "currency_code": "CDF",
                    "sens_flux": "Sortie",
                    "incluse_synthese": True,
                },
                {
                    "date": "2026-07-14 11:00:00",
                    "receipt_no": "DAY-003",
                    "currency_code": "USD",
                    "sens_flux": "Entree",
                    "incluse_synthese": True,
                },
                {
                    "date": "2026-07-16 09:00:00",
                    "receipt_no": "DAY-004",
                    "currency_code": "CDF",
                    "sens_flux": "Entree",
                    "incluse_synthese": True,
                },
                {
                    "date": "2026-07-16 10:00:00",
                    "receipt_no": "EXCLUDED",
                    "currency_code": "CDF",
                    "sens_flux": "Entree",
                    "incluse_synthese": False,
                },
            ]
        )

        report = build_g2_transaction_time_analysis(detail)
        par_jour = report["par_jour"]
        par_jour_semaine = report["par_jour_semaine"]
        par_heure = report["par_heure"]
        jour_heure = report["jour_heure"]

        self.assertEqual(int(par_jour["nombre_transactions"].sum()), 4)
        self.assertEqual(par_jour["date_transaction"].nunique(), 3)
        july_15 = par_jour["date_transaction"].eq(pd.Timestamp("2026-07-15"))
        self.assertEqual(int(par_jour.loc[july_15, "nombre_transactions"].sum()), 0)

        cdf_entries_at_9 = par_heure.loc[
            par_heure["heure_num"].eq(9)
            & par_heure["currency_code"].eq("CDF")
            & par_heure["sens_flux"].eq("Entree"),
            "nombre_transactions",
        ]
        self.assertEqual(int(cdf_entries_at_9.iloc[0]), 2)
        self.assertEqual(int(par_heure.loc[par_heure["heure_num"].eq(0), "nombre_transactions"].sum()), 0)
        self.assertEqual(set(par_heure["heure_num"]), set(range(24)))
        self.assertEqual(int(jour_heure["nombre_transactions"].sum()), 4)
        self.assertEqual(int(par_jour_semaine["nombre_transactions"].sum()), 4)
        self.assertEqual(set(par_jour_semaine["jour_semaine_num"]), set(range(7)))
        weekday_totals = par_jour_semaine.groupby("jour_semaine", as_index=True)["nombre_transactions"].sum()
        self.assertEqual(int(weekday_totals["Mardi"]), 3)
        self.assertEqual(int(weekday_totals["Mercredi"]), 0)

        export = create_excel_export(
            {
                "transactions_par_jour": par_jour,
                "transactions_par_jour_semaine": par_jour_semaine,
                "transactions_par_heure": par_heure,
                "transactions_jour_heure": jour_heure,
            }
        )
        workbook = pd.ExcelFile(BytesIO(export), engine="openpyxl")
        self.assertEqual(
            workbook.sheet_names,
            [
                "Transactions_Jour",
                "Transactions_Jour_Semaine",
                "Transactions_Heure",
                "Transactions_Jour_Heure",
            ],
        )

    def test_g2_transaction_time_analysis_returns_empty_frames_without_valid_dates(self) -> None:
        report = build_g2_transaction_time_analysis(pd.DataFrame({"date": ["invalide"]}))

        self.assertTrue(report["par_jour"].empty)
        self.assertTrue(report["par_jour_semaine"].empty)
        self.assertTrue(report["par_heure"].empty)
        self.assertTrue(report["jour_heure"].empty)

    def test_mpesa_accounting_analysis_builds_client_balance_from_turbo_only(self) -> None:
        transactions = prepare_transactions(
            pd.DataFrame(
                [
                    {
                        "id": "CDF-1",
                        "customer_id": "CLIENT-CDF",
                        "msisdn1": "0811111111",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "SA-CDF",
                        "currency_code": "CDF",
                        "dr": 100,
                        "cr": 0,
                        "bal_before": 0,
                        "bal_after": 100,
                        "ref_no": "REF-CDF",
                        "description": "M-Pesa Depot",
                        "created_at": "2026-07-16 10:00:00",
                    },
                    {
                        "id": "CDF-2",
                        "customer_id": "CLIENT-CDF",
                        "msisdn1": "0811111111",
                        "account_type": "NORMAL SAVINGS",
                        "reference_id": "SA-CDF",
                        "currency_code": "CDF",
                        "dr": 0,
                        "cr": 100,
                        "bal_before": 200,
                        "bal_after": 300,
                        "ref_no": "REF-CDF",
                        "description": "Epargne depot",
                        "created_at": "2026-07-16 10:00:00",
                    },
                    {
                        "id": "USD-1",
                        "customer_id": "CLIENT-USD",
                        "msisdn1": "0822222222",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "LN-USD",
                        "currency_code": "USD",
                        "dr": 0,
                        "cr": 20,
                        "bal_before": 0,
                        "bal_after": 20,
                        "ref_no": "REF-USD",
                        "description": "Montant pret",
                        "created_at": "2026-07-16 11:00:00",
                    },
                    {
                        "id": "USD-2",
                        "customer_id": "CLIENT-USD",
                        "msisdn1": "0822222222",
                        "account_type": "PRINCIPLE",
                        "reference_id": "LN-USD",
                        "currency_code": "USD",
                        "dr": 20,
                        "cr": 0,
                        "bal_before": 0,
                        "bal_after": 20,
                        "ref_no": "REF-USD",
                        "description": "Montant principal",
                        "created_at": "2026-07-16 11:00:00",
                    },
                    {
                        "id": "NEXT-DAY",
                        "customer_id": "CLIENT-CDF",
                        "msisdn1": "0811111111",
                        "account_type": "MPESA ACCOUNT",
                        "reference_id": "SA-CDF",
                        "currency_code": "CDF",
                        "dr": 999,
                        "cr": 0,
                        "bal_before": 100,
                        "bal_after": 1099,
                        "ref_no": "REF-NEXT",
                        "description": "M-Pesa Depot",
                        "created_at": "2026-07-17 08:00:00",
                    },
                ]
            )
        )
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "REF-CDF",
                        "Completion Time": "2026-07-16 10:01:00",
                        "Initiation Time": "2026-07-16 10:00:00",
                        "Opposite Party": "0811111111 - CLIENT CDF",
                        "Currency": "CDF",
                        "Paid In": 900,
                        "Withdrawn": 0,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    },
                    {
                        "Receipt No.": "REF-USD",
                        "Completion Time": "2026-07-16 11:01:00",
                        "Initiation Time": "2026-07-16 11:00:00",
                        "Opposite Party": "0822222222 - CLIENT USD",
                        "Currency": "USD",
                        "Paid In": 800,
                        "Withdrawn": 0,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    },
                ]
            )
        )
        transactions = enrich_transactions_with_g2_customer_names(transactions, g2)
        prepared = MpesaPreparedData(
            transactions=transactions,
            current_savings=prepare_current_savings(
                pd.DataFrame(
                    [
                        {
                            "customer_id": "CLIENT-CDF",
                            "msisdn": "0811111111",
                            "product_name": "Courant",
                            "account_type": "NORMAL SAVINGS",
                            "balance": 300,
                            "currency_code": "CDF",
                            "created_at": "2026-01-01",
                            "updated_at": "2026-07-17",
                        }
                    ]
                )
            ),
            fixed_savings=pd.DataFrame(),
            loans=prepare_loans(
                pd.DataFrame(
                    [
                        {
                            "loan_id": "LN-USD",
                            "customer_id": "CLIENT-USD",
                            "currency_code": "USD",
                            "loan_balance": 20,
                            "updated_at": "2026-07-17",
                        }
                    ]
                )
            ),
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
        )

        report = build_mpesa_accounting_analysis(
            prepared,
            date_start="2026-07-16",
            date_end="2026-07-16",
        )

        self.assertEqual(set(report["synthese"]["currency_code"]), {"CDF", "USD"})
        self.assertEqual(len(report["journal_ecritures"]), 4)
        self.assertEqual(len(report["journal_operations"]), 2)
        self.assertTrue(report["journal_operations"]["operation_symetrique"].all())
        cdf_summary = report["synthese"].loc[
            report["synthese"]["currency_code"].eq("CDF")
        ].iloc[0]
        self.assertEqual(float(cdf_summary["total_debit"]), 100.0)
        self.assertEqual(float(cdf_summary["total_credit"]), 100.0)
        self.assertEqual(float(cdf_summary["taux_rapprochement_g2_pct"]), 100.0)
        cdf_client = report["balance_clients"].loc[
            report["balance_clients"]["customer_id"].eq("CLIENT-CDF")
        ].iloc[0]
        usd_client = report["balance_clients"].loc[
            report["balance_clients"]["customer_id"].eq("CLIENT-USD")
        ].iloc[0]
        self.assertEqual(float(cdf_client["solde_epargne_courante_observe"]), 300.0)
        self.assertEqual(float(usd_client["encours_principal_observe"]), 20.0)
        self.assertEqual(cdf_client["Nom_client"], "CLIENT CDF")
        # Les montants G2 volontairement differents ne remplacent jamais Turbo.
        self.assertNotEqual(float(cdf_summary["total_debit"]), 900.0)

    def test_mpesa_accounting_analysis_degrades_without_g2_and_exports_targeted_sheets(self) -> None:
        prepared = _sample_prepared_data()

        report = build_mpesa_accounting_analysis(
            prepared,
            date_start="2026-07-01",
            date_end="2026-07-01",
        )

        self.assertFalse(report["synthese"].empty)
        self.assertFalse(report["balance_clients"].empty)
        self.assertEqual(int(report["controle_g2"]["transactions_g2_chargees"].sum()), 0)
        export = create_excel_export(
            {
                "accounting_summary": report["synthese"],
                "accounting_client_balances": report["balance_clients"],
                "accounting_account_balance": report["balance_comptes"],
                "accounting_operation_journal": report["journal_operations"],
            }
        )
        workbook = pd.ExcelFile(BytesIO(export), engine="openpyxl")
        self.assertEqual(
            workbook.sheet_names,
            [
                "Compta_Synthese_Turbo",
                "Balance_Clients_Turbo",
                "Balance_Comptes_Turbo",
                "Journal_Operations_Turbo",
            ],
        )

    def test_mpesa_management_dashboard_builds_actionable_microfinance_views(self) -> None:
        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "PILOT-001",
                        "Completion Time": "2026-01-01 09:00:00",
                        "Opposite Party": "0811111111 - CLIENT A",
                        "Currency": "CDF",
                        "Paid In": 100,
                        "Withdrawn": 0,
                        "Balance": 1000,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    },
                    {
                        "Receipt No.": "PILOT-002",
                        "Completion Time": "2026-07-10 10:00:00",
                        "Opposite Party": "0811111111 - CLIENT A",
                        "Currency": "CDF",
                        "Paid In": 200,
                        "Withdrawn": 0,
                        "Balance": 1200,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    },
                    {
                        "Receipt No.": "PILOT-003",
                        "Completion Time": "2026-07-14 11:00:00",
                        "Opposite Party": "0822222222 - CLIENT B",
                        "Currency": "CDF",
                        "Paid In": 0,
                        "Withdrawn": 50,
                        "Balance": 1150,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouB2C",
                    },
                    {
                        "Receipt No.": "PILOT-004",
                        "Completion Time": "2026-03-01 12:00:00",
                        "Opposite Party": "0833333333 - CLIENT C",
                        "Currency": "USD",
                        "Paid In": 10,
                        "Withdrawn": 0,
                        "Balance": 100,
                        "Transaction Status": "Completed",
                        "Details": "BisouBisouC2B",
                    },
                ]
            )
        )
        loans = prepare_loans(
            pd.DataFrame(
                [
                    {
                        "loan_id": "LN-001",
                        "customer_id": "A",
                        "msisdn1": "0811111111",
                        "currency_code": "CDF",
                        "loan_amount": 1000,
                        "loan_balance": 500,
                        "amount_paid": 500,
                        "due_date": "2026-06-01",
                        "updated_at": "2026-07-15",
                    },
                    {
                        "loan_id": "LN-002",
                        "customer_id": "B",
                        "msisdn1": "0822222222",
                        "currency_code": "CDF",
                        "loan_amount": 500,
                        "loan_balance": 0,
                        "amount_paid": 500,
                        "due_date": "2026-07-01",
                        "updated_at": "2026-07-15",
                    },
                    {
                        "loan_id": "LN-003",
                        "customer_id": "C",
                        "msisdn1": "0833333333",
                        "currency_code": "USD",
                        "loan_amount": 100,
                        "loan_balance": 100,
                        "amount_paid": 0,
                        "due_date": "2026-07-14",
                        "updated_at": "2026-07-15",
                    },
                ]
            )
        )
        fixed = prepare_fixed_savings(
            pd.DataFrame(
                [
                    {
                        "customer_id": "A",
                        "msisdn": "0811111111",
                        "product_name": "1 Month",
                        "account_type": "FIXED SAVINGS",
                        "balance": 200,
                        "currency_code": "CDF",
                        "date_approved": "2026-07-10",
                        "maturity_date": "2026-07-20",
                    },
                    {
                        "customer_id": "B",
                        "msisdn": "0822222222",
                        "product_name": "1 Month",
                        "account_type": "FIXED SAVINGS",
                        "balance": 500,
                        "currency_code": "CDF",
                        "date_approved": "2026-05-30",
                        "maturity_date": "2026-06-30",
                    },
                    {
                        "customer_id": "C",
                        "msisdn": "0833333333",
                        "product_name": "3 Months",
                        "account_type": "FIXED SAVINGS",
                        "balance": 50,
                        "currency_code": "USD",
                        "date_approved": "2026-06-01",
                        "maturity_date": "2026-09-01",
                    },
                ]
            )
        )
        perfect = prepare_perfect_clients(
            pd.DataFrame(
                [
                    {"id_client": "PA", "Phone_Prefixe": "243811111111", "nom_complet": "CLIENT A"},
                    {"id_client": "PB", "Phone_Prefixe": "243822222222", "nom_complet": "CLIENT B"},
                    {"id_client": "PD", "Phone_Prefixe": "243844444444", "nom_complet": "CLIENT D"},
                ]
            )
        )
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=fixed,
            loans=loans,
            load_report=build_load_report({}, {}),
            g2_transactions=g2,
            perfect_clients=perfect,
        )

        report = build_mpesa_management_dashboard(
            prepared,
            as_of_date="2026-07-15",
            dat_annual_interest_rate_pct=12.0,
        )

        credit_cdf = report["credit_synthese"].loc[
            report["credit_synthese"]["currency_code"].eq("CDF")
        ].iloc[0]
        self.assertEqual(float(credit_cdf["encours_total"]), 500.0)
        self.assertEqual(float(credit_cdf["par_30j_pct"]), 100.0)
        self.assertEqual(int(credit_cdf["credits_retard_30j"]), 1)

        client_a = report["activite_clients"].loc[
            report["activite_clients"]["phone_prefixe"].astype("string").eq("243811111111")
        ].iloc[0]
        self.assertTrue(bool(client_a["est_reactive_30j"]))
        self.assertEqual(client_a["statut_activite"], "Actif 30 jours")

        conversion_a = report["conversion_clients"].loc[
            report["conversion_clients"]["phone_prefixe"].astype("string").eq("243811111111")
        ].iloc[0]
        self.assertTrue(bool(conversion_a["conversion_observee"]))

        maturity_buckets = set(report["dat_echeances_synthese"]["tranche_echeance"])
        self.assertIn("Echu", maturity_buckets)
        self.assertIn("0 a 7 jours", maturity_buckets)
        self.assertTrue(report["dat_echeances_detail"]["taux_interet_annuel_pct"].eq(12.0).all())
        self.assertTrue(report["dat_echeances_detail"]["interet_estime_echeance"].notna().all())

        perfect_summary = report["perfect_adoption_synthese"].iloc[0]
        self.assertEqual(int(perfect_summary["telephones_perfect_valides"]), 3)
        self.assertEqual(int(perfect_summary["clients_perfect_dans_mpesa"]), 2)
        self.assertEqual(int(perfect_summary["clients_perfect_jamais_observes"]), 1)
        self.assertEqual(set(report["liquidite_synthese"]["currency_code"]), {"CDF", "USD"})
        self.assertFalse(report["concentration_clients"].empty)
        self.assertFalse(report["qualite_synthese"].empty)

        export_keys = [
            "credit_synthese",
            "credit_detail",
            "liquidite_synthese",
            "liquidite_journaliere",
            "activite_clients",
            "conversion_clients",
            "concentration_clients",
            "qualite_synthese",
            "alertes_transactions",
            "dat_echeances_detail",
            "perfect_adoption_detail",
        ]
        export = create_excel_export({key: report[key] for key in export_keys if not report[key].empty})
        workbook = pd.ExcelFile(BytesIO(export), engine="openpyxl")
        self.assertEqual(
            workbook.sheet_names,
            [
                "Pilotage_Credit_Turbo",
                "Credits_Risque_Turbo",
                "Liquidite_G2",
                "Liquidite_Jour_G2",
                "Activite_Turbo_G2",
                "Conversion_DAT_G2",
                "Concentration_G2",
                "Qualite_G2",
                "Alertes_G2",
                "Echeances_DAT_Turbo",
                "Adoption_Turbo_G2",
            ],
        )

    def test_mpesa_management_dashboard_degrades_cleanly_without_optional_sources(self) -> None:
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
        )

        report = build_mpesa_management_dashboard(prepared, as_of_date="2026-07-15")

        self.assertTrue(report["credit_synthese"].empty)
        self.assertTrue(report["liquidite_synthese"].empty)
        self.assertTrue(report["activite_clients"].empty)
        self.assertTrue(report["perfect_adoption_detail"].empty)
        self.assertEqual(len(report["sources"]), 7)
        self.assertIn("Clients_Turbo", report["sources"]["source"].tolist())
        self.assertIn("Clients_Perfect", report["sources"]["source"].tolist())

    def test_dat_maturity_interest_is_estimated_only_with_a_positive_rate(self) -> None:
        fixed = prepare_fixed_savings(
            pd.DataFrame(
                [
                    {
                        "customer_id": "DAT-1",
                        "msisdn": "0811111111",
                        "product_name": "3 Months",
                        "account_type": "FIXED SAVINGS",
                        "balance": 1000,
                        "currency_code": "CDF",
                        "date_approved": "2026-01-01",
                        "maturity_date": "2026-04-01",
                    }
                ]
            )
        )

        with_rate = build_mpesa_dat_maturity_analysis(
            fixed,
            as_of_date="2026-07-15",
            annual_interest_rate_pct=12.0,
        )
        without_rate = build_mpesa_dat_maturity_analysis(
            fixed,
            as_of_date="2026-07-15",
            annual_interest_rate_pct=0.0,
        )

        row = with_rate["detail"].iloc[0]
        self.assertEqual(int(row["duree_contractuelle_jours"]), 90)
        self.assertAlmostEqual(float(row["interet_estime_echeance"]), 1000 * 0.12 * 90 / 365, places=6)
        self.assertAlmostEqual(
            float(row["capital_plus_interet_estime"]),
            1000 + 1000 * 0.12 * 90 / 365,
            places=6,
        )
        self.assertTrue(without_rate["detail"]["interet_estime_echeance"].isna().all())
        self.assertTrue(without_rate["synthese"]["interet_estime_echeance"].isna().all())

    def test_dat_repayment_preparation_defaults_to_eleven_percent(self) -> None:
        fixed = prepare_fixed_savings(
            pd.DataFrame(
                [
                    {
                        "savings_id": "DAT-6M",
                        "customer_id": "CLIENT-6M",
                        "msisdn": "0811111111",
                        "product_name": "6 Months",
                        "account_type": "FIXED SAVINGS",
                        "balance": 1000,
                        "currency_code": "USD",
                        "date_approved": "2026-01-01",
                        "maturity_date": "2026-07-01",
                    },
                    {
                        "savings_id": "DAT-ECHU",
                        "customer_id": "CLIENT-ECHU",
                        "msisdn": "0822222222",
                        "product_name": "3 Months",
                        "account_type": "FIXED SAVINGS",
                        "balance": 500,
                        "currency_code": "CDF",
                        "date_approved": "2026-03-01",
                        "maturity_date": "2026-06-01",
                    },
                ]
            )
        )

        report = build_mpesa_dat_maturity_analysis(
            fixed,
            as_of_date="2026-06-15",
            preparation_horizon_days=30,
        )
        detail = report["detail"].set_index("savings_id")
        six_months = detail.loc["DAT-6M"]
        expired = detail.loc["DAT-ECHU"]

        self.assertEqual(float(six_months["taux_interet_annuel_pct"]), 11.0)
        self.assertEqual(int(six_months["duree_contractuelle_jours"]), 181)
        self.assertAlmostEqual(
            float(six_months["interet_estime_echeance"]),
            1000 * 0.11 * 181 / 365,
            places=6,
        )
        self.assertAlmostEqual(float(six_months["duree_contractuelle_mois_estimee"]), 6.0, places=1)
        self.assertEqual(int(six_months["jours_avant_echeance"]), 16)
        self.assertTrue(bool(six_months["a_preparer_remboursement"]))
        self.assertEqual(
            six_months["statut_preparation_remboursement"],
            "A preparer sous 30 jours",
        )
        self.assertTrue(bool(expired["a_preparer_remboursement"]))
        self.assertEqual(
            expired["statut_preparation_remboursement"],
            "Echu - remboursement a traiter",
        )

    def test_g2_retention_report_calculates_m1_and_90_days_without_mixing_currencies(self) -> None:
        rows = [
            ("JAN-A", "2026-01-10", "0811111111 - CLIENT A", "CDF", "Completed", "BisouBisouC2B"),
            ("JAN-B", "2026-01-15", "0822222222 - CLIENT B", "CDF", "Completed", "BisouBisouC2B"),
            ("FEB-A", "2026-02-05", "0811111111 - CLIENT A", "CDF", "Completed", "BisouBisouC2B"),
            ("MAR-B", "2026-03-10", "0822222222 - CLIENT B", "CDF", "Completed", "BisouBisouC2BRepayment"),
            ("JAN-U", "2026-01-20", "0833333333 - CLIENT USD", "USD", "Completed", "BisouBisouC2B"),
            ("MAY-C", "2026-05-15", "0844444444 - CLIENT C", "CDF", "Completed", "BisouBisouC2B"),
            ("INTERNAL", "2026-01-12", "0855555555 - INTERNE", "CDF", "Completed", "Super Transaction"),
            ("FAILED", "2026-01-13", "0866666666 - ECHEC", "CDF", "Failed", "BisouBisouC2B"),
        ]
        raw = pd.DataFrame(
            [
                {
                    "Receipt No.": receipt,
                    "Completion Time": date,
                    "Opposite Party": party,
                    "Currency": currency,
                    "Transaction Amount": 1000,
                    "Transaction Status": status,
                    "Details": details,
                }
                for receipt, date, party, currency, status, details in rows
            ]
        )
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=prepare_g2_transactions(raw),
        )

        report = build_g2_retention_report(prepared)
        january = report["mensuelle"].loc[report["mensuelle"]["mois"].eq("2026-01")].set_index("currency_code")

        self.assertEqual(int(january.loc["CDF", "clients_actifs_mois_base"]), 2)
        self.assertEqual(float(january.loc["CDF", "retention_m1_pct"]), 50.0)
        self.assertEqual(float(january.loc["CDF", "retention_90j_pct"]), 100.0)
        self.assertEqual(int(january.loc["USD", "clients_actifs_mois_base"]), 1)
        self.assertEqual(float(january.loc["USD", "retention_m1_pct"]), 0.0)
        self.assertEqual(float(january.loc["USD", "retention_90j_pct"]), 0.0)
        self.assertEqual(len(report["detail_clients"].loc[report["detail_clients"]["mois"].eq("2026-01")]), 3)
        self.assertFalse(report["definitions"].empty)

    def test_g2_retention_report_leaves_incomplete_windows_blank(self) -> None:
        raw = pd.DataFrame(
            [
                {
                    "Receipt No.": "JUL-A",
                    "Completion Time": "2026-07-10",
                    "Opposite Party": "0811111111 - CLIENT A",
                    "Currency": "CDF",
                    "Transaction Amount": 1000,
                    "Transaction Status": "Completed",
                    "Details": "BisouBisouC2B",
                }
            ]
        )
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=prepare_g2_transactions(raw),
        )

        row = build_g2_retention_report(prepared)["mensuelle"].iloc[0]

        self.assertFalse(bool(row["eligible_retention_m1"]))
        self.assertFalse(bool(row["eligible_retention_90j"]))
        self.assertTrue(pd.isna(row["retention_m1_pct"]))
        self.assertTrue(pd.isna(row["retention_90j_pct"]))

    def test_g2_retention_report_excludes_non_completed_rows_from_activity(self) -> None:
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=pd.DataFrame([{"receipt_no": "SOURCE"}]),
        )
        daily_detail = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp("2026-01-10 09:00:00"),
                    "receipt_no": "COMPLETED-1",
                    "phone_prefixe": "243811111111",
                    "currency_code": "CDF",
                    "details_rapport": "Depot normal",
                    "transaction_status": "Completed",
                    "incluse_synthese": True,
                    "montant_entree": 1000,
                    "montant_sortie": 0,
                },
                {
                    "date": pd.Timestamp("2026-01-10 10:00:00"),
                    "receipt_no": "PENDING-1",
                    "phone_prefixe": "243822222222",
                    "currency_code": "CDF",
                    "details_rapport": "Depot normal",
                    "transaction_status": "Pending",
                    "incluse_synthese": False,
                    "montant_entree": 5000,
                    "montant_sortie": 0,
                },
            ]
        )

        retention = build_g2_retention_report(prepared, daily_detail=daily_detail)

        self.assertEqual(int(retention["mensuelle"].iloc[0]["clients_actifs_mois_base"]), 1)
        self.assertEqual(retention["detail_clients"]["phone_prefixe"].tolist(), ["243811111111"])

    def test_g2_dat_pdf_html_contains_summary_without_client_phone_detail(self) -> None:
        monthly = pd.DataFrame(
            [
                {
                    "periode": pd.Timestamp("2026-01-01"),
                    "mois": "2026-01",
                    "currency_code": "CDF",
                    "clients_actifs_mois_base": 10,
                    "clients_retenus_m1": 6,
                    "retention_m1_pct": 60.0,
                    "clients_retenus_90j": 8,
                    "retention_90j_pct": 80.0,
                    "eligible_retention_m1": True,
                    "eligible_retention_90j": True,
                }
            ]
        )
        report = {
            "rapport_journalier_pivot": pd.DataFrame(
                [{"currency_code": "CDF", "nombre_entrees": 12, "montant_total_entrees": 10000}]
            ),
            "rapport_journalier_synthese": pd.DataFrame(
                [{"currency_code": "CDF", "sens_flux": "Entree", "details_rapport": "DAT", "nombre": 4, "montant": 5000}]
            ),
            "g2_dat": pd.DataFrame([{"customer_id_dat": "1001", "phone_prefixe": "243811111111"}]),
            "retention_mensuelle": monthly,
            "retention_operations": pd.DataFrame(),
        }

        html = build_g2_dat_pdf_html(
            report,
            period_text="du 01/01/2026 au 31/05/2026",
            direction_label="Tous <flux>",
            generated_at=pd.Timestamp("2026-07-14 10:00:00"),
        )

        self.assertIn("Synthese executive", html)
        self.assertIn("Retention M+1", html)
        self.assertIn("60.0%", html)
        self.assertIn("Tous &lt;flux&gt;", html)
        self.assertNotIn("243811111111", html)
        self.assertNotIn("Questions ouvertes", html)
        self.assertNotIn("Hypotheses et limites", html)

    def test_g2_dat_word_is_editable_and_uses_the_short_executive_structure(self) -> None:
        from docx import Document
        from docx.enum.section import WD_ORIENT

        report = {
            "rapport_journalier_pivot": pd.DataFrame(
                [
                    {
                        "currency_code": "CDF",
                        "nombre_entrees": 12,
                        "montant_total_entrees": 10000,
                        "nombre_sorties": 2,
                        "montant_total_sorties": 1000,
                        "solde_net_flux": 9000,
                    }
                ]
            ),
            "rapport_journalier_synthese": pd.DataFrame(
                [{"currency_code": "CDF", "sens_flux": "Entree", "details_rapport": "DAT", "nombre": 4, "montant": 5000}]
            ),
            "g2_dat": pd.DataFrame([{"customer_id_dat": "1001", "statut_rapprochement_dat": "Rapproche"}]),
            "retention_mensuelle": pd.DataFrame(),
            "rapport_journalier_detail": pd.DataFrame(
                [
                    {
                        "currency_code": "CDF",
                        "date": pd.Timestamp("2026-07-13 10:15:00"),
                        "receipt_no": "CDF-001",
                        "sens_flux": "Entree",
                        "details_rapport": "DAT",
                        "opposite_party": "243811111111 - CLIENT TEST",
                        "duree": "3 Months",
                        "compte_cree": pd.Timestamp("2026-07-10 08:30:00"),
                        "montant": 12500,
                        "montant_entree": 12500,
                        "montant_sortie": 0,
                        "balance_numeric": 25000,
                        "incluse_synthese": True,
                    },
                    {
                        "currency_code": "USD",
                        "date": pd.Timestamp("2026-07-13 11:00:00"),
                        "receipt_no": "USD-001",
                        "sens_flux": "Sortie",
                        "details_rapport": "Demande de credit",
                        "opposite_party": "243822222222 - CLIENT USD",
                        "duree": "-",
                        "compte_cree": pd.NaT,
                        "montant": 100,
                        "montant_entree": 0,
                        "montant_sortie": 100,
                        "balance_numeric": 900,
                        "incluse_synthese": True,
                    },
                    {
                        "currency_code": "CDF",
                        "date": pd.Timestamp("2026-07-13 12:00:00"),
                        "receipt_no": "DECLINED-001",
                        "sens_flux": "Entree",
                        "details_rapport": "Depot normal",
                        "opposite_party": "243899999999 - CLIENT REFUSE",
                        "montant": 5000,
                        "montant_entree": 5000,
                        "montant_sortie": 0,
                        "transaction_status": "Declined",
                        "statut_transaction_g2": "Declined",
                        "incluse_synthese": False,
                    },
                ]
            ),
        }

        content = create_g2_dat_word(
            report,
            period_text="du 01/01/2026 au 31/01/2026",
            direction_label="Tous",
            generated_at=pd.Timestamp("2026-07-14 10:00:00"),
        )
        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        table_text = "\n".join(
            cell.text
            for table in document.tables
            for row in table.rows
            for cell in row.cells
        )
        classified_tables = [
            table
            for table in document.tables
            if table.rows and table.rows[0].cells[0].text == "date"
        ]

        self.assertTrue(content.startswith(b"PK"))
        self.assertIn("Rapport M-PESA - G2/DAT", text)
        self.assertIn("Synthese executive", text)
        self.assertIn("Fréquence temporelle", text)
        self.assertIn("Heure la plus fréquente : 10h", text)
        self.assertNotIn("Jour de semaine le plus actif", text)
        self.assertIn("Synthese des flux G2 par devise", text)
        self.assertIn("Point de vigilance", text)
        self.assertIn("CDF : 1 transaction(s) Completed, 1 client(s) distinct(s)", text)
        self.assertIn("USD : 1 transaction(s) Completed, 1 client(s) distinct(s)", text)
        self.assertIn("2 transaction(s) Completed", text)
        self.assertIn("1 transaction(s) d'autres statuts", text)
        self.assertIn("Transactions", text)
        self.assertEqual(len(classified_tables), 1)
        self.assertEqual(
            [cell.text for cell in classified_tables[0].rows[0].cells],
            G2_CLASSIFIED_TRANSACTION_COLUMNS,
        )
        self.assertEqual(classified_tables[0].rows[1].cells[2].text, "CDF")
        self.assertEqual(classified_tables[0].rows[2].cells[2].text, "USD")
        self.assertIn("243811111111", table_text)
        self.assertIn("CLIENT TEST", table_text)
        self.assertIn("13/07/2026 10:15:00", table_text)
        self.assertIn("10/07/2026 08:30:00", table_text)
        self.assertNotIn("DECLINED-001", table_text)
        self.assertNotIn("CLIENT REFUSE", table_text)
        self.assertNotIn("Questions ouvertes", text)
        self.assertGreaterEqual(len(document.tables), 3)
        self.assertGreaterEqual(len(document.sections), 2)
        self.assertEqual(document.sections[-1].orientation, WD_ORIENT.LANDSCAPE)

        multi_day_report = dict(report)
        multi_day_detail = pd.concat(
            [
                report["rapport_journalier_detail"],
                pd.DataFrame(
                    [
                        {
                            "currency_code": "CDF",
                            "date": pd.Timestamp("2026-07-14 09:00:00"),
                            "receipt_no": "CDF-002",
                            "sens_flux": "Entree",
                            "details_rapport": "Depot normal",
                            "opposite_party": "243833333333 - CLIENT MULTI",
                            "montant": 1000,
                            "montant_entree": 1000,
                            "montant_sortie": 0,
                            "incluse_synthese": True,
                        },
                        {
                            "currency_code": "CDF",
                            "date": pd.Timestamp("2026-07-14 09:15:00"),
                            "receipt_no": "CDF-003",
                            "sens_flux": "Entree",
                            "details_rapport": "DAT",
                            "opposite_party": "243844444444 - CLIENT MULTI 2",
                            "montant": 2000,
                            "montant_entree": 2000,
                            "montant_sortie": 0,
                            "incluse_synthese": True,
                        },
                        {
                            "currency_code": "USD",
                            "date": pd.Timestamp("2026-07-14 09:45:00"),
                            "receipt_no": "USD-002",
                            "sens_flux": "Sortie",
                            "details_rapport": "Demande de credit",
                            "opposite_party": "243855555555 - CLIENT MULTI 3",
                            "montant": 50,
                            "montant_entree": 0,
                            "montant_sortie": 50,
                            "incluse_synthese": True,
                        },
                    ]
                ),
            ],
            ignore_index=True,
        )
        time_report = build_g2_transaction_time_analysis(multi_day_detail)
        multi_day_report["rapport_journalier_detail"] = multi_day_detail
        multi_day_report["transactions_par_jour"] = time_report["par_jour"]
        multi_day_report["transactions_par_jour_semaine"] = time_report["par_jour_semaine"]
        multi_day_report["transactions_par_heure"] = time_report["par_heure"]
        multi_day_report["analysis_date_start"] = pd.Timestamp("2026-07-13")
        multi_day_report["analysis_date_end"] = pd.Timestamp("2026-07-14")
        multi_day_content = create_g2_dat_word(
            multi_day_report,
            period_text="du 13/07/2026 au 14/07/2026",
            direction_label="Tous",
            generated_at=pd.Timestamp("2026-07-15 10:00:00"),
        )
        multi_day_document = Document(BytesIO(multi_day_content))
        multi_day_text = "\n".join(paragraph.text for paragraph in multi_day_document.paragraphs)
        self.assertIn("Heure la plus fréquente : 09h, avec 3 transaction(s), soit 60.0%", multi_day_text)
        self.assertIn("Jour de semaine le plus actif : Mardi, avec 3 transaction(s), soit 60.0%", multi_day_text)

        report_without_pivot = dict(report)
        report_without_pivot.pop("rapport_journalier_pivot")
        fallback_content = create_g2_dat_word(
            report_without_pivot,
            period_text="du 01/01/2026 au 31/01/2026",
            direction_label="Tous",
            generated_at=pd.Timestamp("2026-07-14 10:00:00"),
        )
        fallback_document = Document(BytesIO(fallback_content))
        fallback_text = "\n".join(paragraph.text for paragraph in fallback_document.paragraphs)
        flow_tables = [
            table
            for table in fallback_document.tables
            if table.rows and table.rows[0].cells[0].text == "Devise"
        ]
        self.assertIn("Synthese des flux G2 par devise", fallback_text)
        self.assertNotIn("Aucune donnee disponible.", fallback_text)
        self.assertEqual(len(flow_tables), 2)
        self.assertEqual(flow_tables[0].rows[1].cells[0].text, "CDF")
        self.assertEqual(flow_tables[0].rows[2].cells[0].text, "USD")

    def test_g2_dat_word_labels_turbo_only_source_without_simulating_g2_controls(self) -> None:
        from docx import Document

        detail = pd.DataFrame(
            [
                {
                    "currency_code": "CDF",
                    "date": pd.Timestamp("2026-07-15 08:30:00"),
                    "receipt_no": "REF-TURBO",
                    "sens_flux": "Entree",
                    "details_rapport": "Depot normal",
                    "opposite_party": "243811111111",
                    "montant": 1000,
                    "montant_entree": 1000,
                    "montant_sortie": 0,
                    "incluse_synthese": True,
                    "transaction_status": "Comptabilisee Turbo",
                }
            ]
        )
        report = {
            "analysis_source_label": "Turbo",
            "rapport_journalier_pivot": build_entry_pivot(detail),
            "rapport_journalier_synthese": pd.DataFrame(),
            "rapport_journalier_detail": detail,
            "g2_dat": detail.assign(
                statut_rapprochement="Non applicable - Turbo seul",
                est_anomalie=False,
            ),
            "retention_mensuelle": pd.DataFrame(),
        }

        content = create_g2_dat_word(
            report,
            period_text="le 15/07/2026",
            direction_label="Tous",
            generated_at=pd.Timestamp("2026-07-15 10:00:00"),
        )
        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)

        self.assertIn("Rapport M-PESA - Turbo/DAT", text)
        self.assertIn("Synthese des flux Turbo par devise", text)
        self.assertIn("operation(s) comptabilisee(s) dans Turbo", text)
        self.assertIn("controles croises G2/Turbo sont non applicables", text)
        self.assertNotIn("Rapprochement Receipt No/ref_no", text)

    def test_g2_dat_word_activity_uses_filtered_detail_not_retention_month(self) -> None:
        from docx import Document

        filtered_detail = pd.DataFrame(
            [
                {
                    "currency_code": "CDF",
                    "date": pd.Timestamp("2026-07-15 08:30:00"),
                    "receipt_no": "FILTERED-1",
                    "sens_flux": "Entree",
                    "details_rapport": "Depot normal",
                    "opposite_party": "243811111111 - CLIENT FILTRE",
                    "montant": 1000,
                    "montant_entree": 1000,
                    "montant_sortie": 0,
                    "incluse_synthese": True,
                }
            ]
        )
        report = {
            "rapport_journalier_pivot": build_entry_pivot(filtered_detail),
            "rapport_journalier_synthese": pd.DataFrame(),
            "rapport_journalier_detail": filtered_detail,
            "retention_mensuelle": pd.DataFrame(
                [
                    {
                        "periode": pd.Timestamp("2026-07-01"),
                        "currency_code": "CDF",
                        "clients_actifs_mois_base": 99,
                        "retention_m1_pct": pd.NA,
                        "retention_90j_pct": pd.NA,
                    }
                ]
            ),
        }

        content = create_g2_dat_word(
            report,
            period_text="du 15/07/2026 a 08:00:00 au 15/07/2026 a 09:00:00",
            direction_label="Entrees",
            generated_at=pd.Timestamp("2026-07-15 10:00:00"),
        )
        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)

        self.assertIn("CDF : 1 transaction(s) Completed, 1 client(s) distinct(s)", text)
        self.assertNotIn("99 client(s) actif(s)", text)
        self.assertIn("Sens : Entrees", text)

    def test_g2_dat_word_all_sections_use_date_time_direction_and_status_scope(self) -> None:
        from docx import Document

        g2 = prepare_g2_transactions(
            pd.DataFrame(
                [
                    {
                        "Receipt No.": "IN-SCOPE",
                        "Completion Time": "2026-07-15 08:30:00",
                        "Transaction Status": "Completed",
                        "Opposite Party": "0811111111 - CLIENT DANS FILTRE",
                        "Currency": "CDF",
                        "Paid In": 1000,
                        "Withdrawn": 0,
                        "Details": "BisouBisouC2B",
                    },
                    {
                        "Receipt No.": "OUT-DIRECTION",
                        "Completion Time": "2026-07-15 08:40:00",
                        "Transaction Status": "Completed",
                        "Opposite Party": "0822222222 - CLIENT SORTIE",
                        "Currency": "CDF",
                        "Paid In": 0,
                        "Withdrawn": 200,
                        "Details": "BisouBisouB2C",
                    },
                    {
                        "Receipt No.": "OUT-TIME",
                        "Completion Time": "2026-07-15 12:00:00",
                        "Transaction Status": "Completed",
                        "Opposite Party": "0833333333 - CLIENT HORS HEURE",
                        "Currency": "CDF",
                        "Paid In": 5000,
                        "Withdrawn": 0,
                        "Details": "BisouBisouC2B",
                    },
                    {
                        "Receipt No.": "PENDING-SCOPE",
                        "Completion Time": "2026-07-15 08:50:00",
                        "Transaction Status": "Pending",
                        "Opposite Party": "0844444444 - CLIENT PENDING",
                        "Currency": "CDF",
                        "Paid In": 7000,
                        "Withdrawn": 0,
                        "Details": "BisouBisouC2B",
                    },
                ]
            )
        )
        filtered_g2 = filter_g2_transactions_by_completion_time(
            g2,
            pd.Timestamp("2026-07-15").date(),
            pd.Timestamp("2026-07-15").date(),
            time(8, 0),
            time(9, 0),
        )
        filtered_g2 = filter_g2_transactions_by_direction(filtered_g2, ["Entree"])
        prepared = MpesaPreparedData(
            transactions=pd.DataFrame(),
            current_savings=pd.DataFrame(),
            fixed_savings=pd.DataFrame(),
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
            g2_transactions=filtered_g2,
        )
        daily = build_g2_daily_savings_report(prepared)
        time_report = build_g2_transaction_time_analysis(daily["detail"])
        retention = build_g2_retention_report(prepared, daily_detail=daily["detail"])
        word_report = {
            "rapport_journalier_pivot": daily["pivot"],
            "rapport_journalier_synthese": daily["synthese"],
            "rapport_journalier_detail": daily["detail"],
            "statuts_g2": daily["statuts"],
            "transactions_par_jour": time_report["par_jour"],
            "transactions_par_jour_semaine": time_report["par_jour_semaine"],
            "transactions_par_heure": time_report["par_heure"],
            "retention_mensuelle": retention["mensuelle"],
            "g2_dat": pd.DataFrame(),
            "analysis_date_start": pd.Timestamp("2026-07-15 08:00:00"),
            "analysis_date_end": pd.Timestamp("2026-07-15 09:00:00"),
        }

        content = create_g2_dat_word(
            word_report,
            period_text="du 15/07/2026 a 08:00:00 au 15/07/2026 a 09:00:00",
            direction_label="Entrees",
            generated_at=pd.Timestamp("2026-07-15 10:00:00"),
        )
        document = Document(BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        table_text = "\n".join(
            cell.text
            for table in document.tables
            for row in table.rows
            for cell in row.cells
        )

        self.assertIn("CDF : 1 transaction(s) Completed, 1 client(s) distinct(s)", text)
        self.assertIn("1 transaction(s) Completed incluse(s)", text)
        self.assertIn("1 transaction(s) d'autres statuts", text)
        self.assertIn("08h, avec 1 transaction(s), soit 100.0% du volume", text)
        self.assertIn("IN-SCOPE", table_text)
        self.assertIn("Depot normal", table_text)
        self.assertNotIn("OUT-DIRECTION", table_text)
        self.assertNotIn("OUT-TIME", table_text)
        self.assertNotIn("PENDING-SCOPE", table_text)

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

    def test_diagnostics_separates_linked_entries_and_monitors_dat_dates(self) -> None:
        transactions = pd.DataFrame(
            [
                {
                    "id": "TX-1",
                    "customer_id": "1",
                    "reference_id": "REF001",
                    "ref_no": "G2REF",
                    "created_at": "2026-07-15 10:00:00",
                    "currency_code": "CDF",
                    "account_type": "MPESA ACCOUNT",
                    "dr": 0,
                    "cr": 100,
                    "bal_before": 0,
                    "bal_after": 100,
                },
                {
                    "id": "TX-2",
                    "customer_id": "1",
                    "reference_id": "REF001",
                    "ref_no": "G2REF",
                    "created_at": "2026-07-15 10:00:00",
                    "currency_code": "CDF",
                    "account_type": "LOAN ACCOUNT",
                    "dr": 0,
                    "cr": 100,
                    "bal_before": 0,
                    "bal_after": 100,
                },
            ]
        )
        fixed = pd.DataFrame(
            [
                {
                    "customer_id": "1",
                    "balance": 100,
                    "date_approved": "2026-06-07",
                    "maturity_date": "2026-04-22",
                },
                {
                    "customer_id": "2",
                    "balance": 200,
                    "date_approved": "2026-07-01",
                    "maturity_date": "2026-08-01",
                },
            ]
        )
        prepared = MpesaPreparedData(
            transactions=transactions,
            current_savings=pd.DataFrame(),
            fixed_savings=fixed,
            loans=pd.DataFrame(),
            load_report=build_load_report({}, {}),
        )

        diagnostics = build_diagnostics(prepared).set_index("controle")

        self.assertEqual(diagnostics.loc["Lignes sans customer_id", "statut"], "OK")
        self.assertEqual(int(diagnostics.loc["Types de comptes a classifier", "valeur"]), 0)
        self.assertEqual(int(diagnostics.loc["Doublons exacts", "valeur"]), 0)
        self.assertEqual(int(diagnostics.loc["Ecritures comptables liees", "valeur"]), 1)
        self.assertEqual(diagnostics.loc["Ecritures comptables liees", "statut"], "Information")
        self.assertEqual(int(diagnostics.loc["Groupes d'ecritures repetees a verifier", "valeur"]), 0)
        self.assertEqual(int(diagnostics.loc["DAT - echeance anterieure a l'approbation", "valeur"]), 1)
        self.assertEqual(diagnostics.loc["DAT - echeance anterieure a l'approbation", "statut"], "A surveiller")
        self.assertEqual(int(diagnostics.loc["DAT echus avec solde positif", "valeur"]), 1)
        self.assertEqual(diagnostics.loc["DAT echus avec solde positif", "statut"], "Controle metier")


class TestLoanSavingsReconciliation(unittest.TestCase):
    def test_deduced_match_consolidates_savings_once_per_client_currency(self) -> None:
        loans = pd.DataFrame(
            [
                {
                    "loan_id": "LN-1",
                    "customer_id": "C1",
                    "msisdn1": "0811111111",
                    "currency_code": "CDF",
                    "loan_amount": 1000,
                    "loan_balance": 400,
                    "amount_paid": 600,
                },
                {
                    "loan_id": "LN-2",
                    "customer_id": "C1",
                    "msisdn1": "0811111111",
                    "currency_code": "CDF",
                    "loan_amount": 500,
                    "loan_balance": 100,
                    "amount_paid": 400,
                },
                {
                    "loan_id": "LN-3",
                    "customer_id": "C3",
                    "msisdn1": "0833333333",
                    "currency_code": "USD",
                    "loan_amount": 100,
                    "loan_balance": 100,
                    "amount_paid": 0,
                },
            ]
        )
        current = pd.DataFrame(
            [
                {
                    "id": 10,
                    "savings_id": "SAV-1",
                    "customer_id": "C1",
                    "msisdn": "0811111111",
                    "currency_code": "CDF",
                    "balance": 100,
                    "source_savings_account_complete": True,
                }
            ]
        )
        fixed = pd.DataFrame(
            [
                {
                    "savings_id": "DAT-1",
                    "customer_id": "C1",
                    "currency_code": "CDF",
                    "balance": 200,
                }
            ]
        )

        report = build_loan_savings_reconciliation(loans, current, fixed)
        cdf_summary = report["synthese"].set_index("currency_code").loc["CDF"]
        cdf_client = report["clients"].set_index(["customer_id", "currency_code"]).loc[("C1", "CDF")]

        self.assertEqual(int(cdf_summary["nombre_credits"]), 2)
        self.assertEqual(float(cdf_summary["encours_credit"]), 500.0)
        self.assertEqual(float(cdf_summary["solde_epargne_courante_clients_credit"]), 100.0)
        self.assertEqual(float(cdf_summary["solde_dat_clients_credit"]), 200.0)
        self.assertEqual(float(cdf_summary["taux_rapprochement_pct"]), 100.0)
        self.assertEqual(int(cdf_client["nombre_credits"]), 2)
        self.assertEqual(float(cdf_client["solde_epargne_courante"]), 100.0)
        self.assertEqual(float(cdf_client["solde_dat_positif"]), 200.0)
        self.assertEqual(cdf_client["savings_id_correspondant"], "SAV-1")
        self.assertEqual(set(report["controles"]["loan_id"]), {"LN-3"})
        export = create_excel_export(
            {
                "loan_savings_summary": report["synthese"],
                "loan_savings_clients": report["clients"],
                "loan_savings_detail": report["detail"],
                "loan_savings_controls": report["controles"],
            }
        )
        self.assertEqual(
            pd.ExcelFile(BytesIO(export)).sheet_names,
            [
                "Credit_Epargne_Synthese",
                "Credit_Epargne_Clients",
                "Credit_Epargne_Detail",
                "Controle_Credit_Epargne",
            ],
        )

    def test_direct_identifier_wins_over_ambiguous_customer_currency(self) -> None:
        loans = pd.DataFrame(
            [
                {
                    "loan_id": "LN-DIRECT",
                    "customer_id": "C1",
                    "msisdn1": "0811111111",
                    "currency_code": "CDF",
                    "loan_balance": 50,
                    "savings_account_id": 20,
                },
                {
                    "loan_id": "LN-AMBIGUOUS",
                    "customer_id": "C1",
                    "msisdn1": "0811111111",
                    "currency_code": "CDF",
                    "loan_balance": 25,
                },
            ]
        )
        current = pd.DataFrame(
            [
                {
                    "id": 20,
                    "savings_id": "SAV-20",
                    "customer_id": "C1",
                    "msisdn": "0811111111",
                    "currency_code": "CDF",
                    "balance": 10,
                },
                {
                    "id": 21,
                    "savings_id": "SAV-21",
                    "customer_id": "C1",
                    "msisdn": "0811111111",
                    "currency_code": "CDF",
                    "balance": 15,
                },
            ]
        )

        detail = build_loan_savings_reconciliation(loans, current)["detail"].set_index("loan_id")

        self.assertEqual(detail.loc["LN-DIRECT", "savings_id_correspondant"], "SAV-20")
        self.assertEqual(
            detail.loc["LN-DIRECT", "statut_controle"],
            "Conforme - correspondance directe",
        )
        self.assertTrue(bool(detail.loc["LN-DIRECT", "liaison_directe_source"]))
        self.assertEqual(detail.loc["LN-AMBIGUOUS", "statut_controle"], "A revoir")
        self.assertIn("Plusieurs comptes courants", detail.loc["LN-AMBIGUOUS", "motif_controle"])

    def test_missing_savings_source_is_not_reported_as_an_operational_anomaly(self) -> None:
        loans = pd.DataFrame(
            [
                {
                    "loan_id": "LN-1",
                    "customer_id": "C1",
                    "currency_code": "CDF",
                    "loan_balance": 50,
                }
            ]
        )

        report = build_loan_savings_reconciliation(loans, pd.DataFrame())

        self.assertEqual(
            report["detail"].iloc[0]["statut_controle"],
            "Non calculable - Savings Account absent",
        )
        self.assertTrue(report["controles"].empty)
        self.assertTrue(pd.isna(report["synthese"].iloc[0]["taux_rapprochement_pct"]))


if __name__ == "__main__":
    unittest.main()
