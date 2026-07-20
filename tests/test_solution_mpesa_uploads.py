from __future__ import annotations

from io import BytesIO

import pandas as pd

from credit_app.tabs.solution_mpesa import (
    MPESA_FINANCE_TURBO_TAB_LABELS,
    MPESA_SOLUTION_TAB_LABELS,
    _build_prepared_data,
    _render_alert_banner,
    _uploaded_dataframes,
)


class _UploadedExcel:
    def __init__(self, name: str, dataframe: pd.DataFrame) -> None:
        self.name = name
        buffer = BytesIO()
        dataframe.to_excel(buffer, index=False)
        self._content = buffer.getvalue()

    def getvalue(self) -> bytes:
        return self._content


def test_finance_turbo_replaces_the_two_previous_main_tabs() -> None:
    assert MPESA_SOLUTION_TAB_LABELS == (
        "Importation",
        "Finance Turbo",
        "Extrait client",
        "DAT",
        "G2 / DAT",
        "Perfect_client",
        "Detail des credits",
        "Controle des donnees",
    )
    assert MPESA_FINANCE_TURBO_TAB_LABELS == (
        "Vue direction",
        "Flux et activité",
        "Crédit, épargne et DAT",
        "Balances et journaux",
        "Risques et contrôles",
        "Export",
    )


def test_alert_banner_uses_the_red_streamlit_callout(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_error(message: str, *, icon: str) -> None:
        captured.update(message=message, icon=icon)

    monkeypatch.setattr("credit_app.tabs.solution_mpesa.st.error", fake_error)

    _render_alert_banner("6 operations necessitent une verification.")

    assert captured == {
        "message": "6 operations necessitent une verification.",
        "icon": ":material/error:",
    }


def test_uploaded_dataframes_unifies_files_and_preserves_provenance() -> None:
    files = [
        _UploadedExcel("transactions_a.xlsx", pd.DataFrame({"id": [1], "dr": [100], "cr": [0]})),
        _UploadedExcel("transactions_b.xlsx", pd.DataFrame({"id": [2], "dr": [0], "cr": [50]})),
    ]

    result = _uploaded_dataframes(
        files,
        source_column="fichier_source_transactions_turbo",
    )

    assert result["id"].tolist() == [1, 2]
    assert result["fichier_source_transactions_turbo"].tolist() == [
        "transactions_a.xlsx",
        "transactions_b.xlsx",
    ]
    assert result["ordre_fichier_import"].tolist() == [0, 1]


def test_prepared_data_uses_one_savings_account_upload_for_current_and_fixed() -> None:
    savings = pd.DataFrame(
        [
            {
                "savings_id": "CURRENT-1",
                "customer_id": 10,
                "msisdn1": "0811111111",
                "product_name": "Open Savings",
                "product_description": "Current account",
                "currency_code": "CDF",
                "balance": 150,
                "created_at": "2026-07-01",
                "updated_at": "2026-07-17",
                "fichier_source_epargne_turbo": "Savings Account.xlsx",
            },
            {
                "savings_id": "CURRENT-2",
                "customer_id": 11,
                "msisdn1": "0822222222",
                "product_name": "Open Savings",
                "product_description": "Current account",
                "currency_code": "USD",
                "balance": 0,
                "created_at": "2026-07-02",
                "updated_at": "2026-07-17",
                "fichier_source_epargne_turbo": "Savings Account.xlsx",
            },
            {
                "savings_id": "FIXED-1",
                "customer_id": 10,
                "msisdn1": "0811111111",
                "product_name": "1 Month",
                "product_description": "1 Month Fixed Account",
                "currency_code": "CDF",
                "balance": 500,
                "date_approved": "2026-07-02",
                "maturity_date": "2026-08-02",
                "created_at": "2026-07-02",
                "updated_at": "2026-07-17",
                "fichier_source_epargne_turbo": "Savings Account.xlsx",
            },
            {
                "savings_id": "FIXED-2",
                "customer_id": 11,
                "msisdn1": "0822222222",
                "product_name": "3 Months",
                "product_description": "3 Months Fixed Account",
                "currency_code": "USD",
                "balance": 0,
                "date_approved": "2026-04-02",
                "maturity_date": "2026-07-02",
                "created_at": "2026-04-02",
                "updated_at": "2026-07-17",
                "fichier_source_epargne_turbo": "Savings Account.xlsx",
            },
        ]
    )

    prepared, _ = _build_prepared_data(
        "unit-master-savings-only",
        pd.DataFrame(),
        savings,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )

    assert len(prepared.current_savings) == 2
    assert len(prepared.fixed_savings) == 2
    assert prepared.fixed_savings_control.empty
    assert set(prepared.current_savings["account_type"]) == {"NORMAL SAVINGS"}
    assert set(prepared.fixed_savings["account_type"]) == {"FIXED SAVINGS"}
    assert "DAT_Turbo (export resume de controle)" not in set(
        prepared.load_report["fichier"]
    )


def test_prepared_data_accepts_current_and_fixed_summaries_in_one_uploader() -> None:
    savings_summaries = pd.DataFrame(
        [
            {
                "customer_id": 21,
                "msisdn": "0810000021",
                "product_name": "Open Savings",
                "account_type": "NORMAL SAVINGS",
                "balance": 125,
                "currency_code": "CDF",
                "created_at": "2026-01-10",
                "updated_at": "2026-07-17",
                "fichier_source_epargne_turbo": "Customers with Current Savings Account.xlsx",
            },
            {
                "customer_id": 22,
                "msisdn": "0810000022",
                "product_name": "6 Months",
                "account_type": "6 Months Fixed Account",
                "balance": 250,
                "currency_code": "USD",
                "date_approved": "2026-02-01",
                "maturity_date": "2026-08-01",
                "fichier_source_epargne_turbo": "Customers with Fixed Savings Account.xlsx",
            },
        ]
    )

    prepared, _ = _build_prepared_data(
        "unit-savings-summaries-fallback",
        pd.DataFrame(),
        savings_summaries,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )

    assert len(prepared.current_savings) == 1
    assert len(prepared.fixed_savings) == 1
    assert prepared.fixed_savings.iloc[0]["created_at"] == pd.Timestamp("2026-02-01")
    assert not prepared.current_savings["source_savings_account_complete"].any()
    assert not prepared.fixed_savings["source_savings_account_complete"].any()


def test_complete_savings_account_has_priority_over_uploaded_summaries() -> None:
    savings = pd.DataFrame(
        [
            {
                "savings_id": "CURRENT-21",
                "customer_id": 21,
                "msisdn1": "0810000021",
                "product_name": "Open Savings",
                "product_description": "Current account",
                "balance": 125,
                "currency_code": "CDF",
                "created_at": "2026-01-10",
                "updated_at": "2026-07-17",
                "fichier_source_epargne_turbo": "Savings Account.xlsx",
            },
            {
                "savings_id": "FIXED-22",
                "customer_id": 22,
                "msisdn1": "0810000022",
                "product_name": "6 Months",
                "product_description": "6 Months Fixed Account",
                "balance": 250,
                "currency_code": "USD",
                "date_approved": "2026-02-01",
                "maturity_date": "2026-08-01",
                "created_at": "2026-02-01",
                "updated_at": "2026-07-17",
                "fichier_source_epargne_turbo": "Savings Account.xlsx",
            },
            {
                "customer_id": 21,
                "msisdn": "0810000021",
                "product_name": "Open Savings",
                "account_type": "NORMAL SAVINGS",
                "balance": 125,
                "currency_code": "CDF",
                "created_at": "2026-01-10",
                "updated_at": "2026-07-17",
                "fichier_source_epargne_turbo": "Customers with Current Savings Account.xlsx",
            },
            {
                "customer_id": 22,
                "msisdn": "0810000022",
                "product_name": "6 Months",
                "account_type": "6 Months Fixed Account",
                "balance": 250,
                "currency_code": "USD",
                "date_approved": "2026-02-01",
                "maturity_date": "2026-08-01",
                "fichier_source_epargne_turbo": "Customers with Fixed Savings Account.xlsx",
            },
        ]
    )

    prepared, _ = _build_prepared_data(
        "unit-complete-savings-priority",
        pd.DataFrame(),
        savings,
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
    )

    assert len(prepared.current_savings) == 1
    assert len(prepared.fixed_savings) == 1
    assert prepared.current_savings["source_savings_account_complete"].all()
    assert prepared.fixed_savings["source_savings_account_complete"].all()
    assert set(prepared.current_savings["fichier_source_epargne_turbo"]) == {
        "Savings Account.xlsx"
    }
    assert set(prepared.fixed_savings["fichier_source_epargne_turbo"]) == {
        "Savings Account.xlsx"
    }
