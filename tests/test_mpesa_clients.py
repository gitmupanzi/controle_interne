import pandas as pd

from credit_app.display_columns import prepare_dataframe_for_display
from credit_app.services.mpesa_analysis import (
    MpesaPreparedData,
    build_mpesa_clients_report,
)


def _sample_prepared() -> MpesaPreparedData:
    transactions = pd.DataFrame(
        {
            "id": [1, 2],
            "customer_id": ["100", "100"],
            "msisdn1": ["243811111111", "243811111111"],
            "account_type": ["NORMAL SAVINGS", "NORMAL SAVINGS"],
            "reference_id": ["R1", "R2"],
            "currency_code": ["USD", "USD"],
            "dr": [0, 5],
            "cr": [10, 0],
            "bal_before": [0, 10],
            "bal_after": [10, 5],
            "ref_no": ["REF1", "REF2"],
            "description": ["Epargne depot", "Retrait Vers M-Pesa"],
            "created_at": [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-05")],
        }
    )
    current = pd.DataFrame(
        {
            "customer_id": ["100"],
            "msisdn": ["243811111111"],
            "product_name": ["Open Savings"],
            "account_type": ["NORMAL SAVINGS"],
            "balance": [5.0],
            "currency_code": ["USD"],
            "created_at": [pd.Timestamp("2026-06-01")],
            "updated_at": [pd.Timestamp("2026-07-05")],
        }
    )
    fixed = pd.DataFrame(
        {
            "customer_id": ["101"],
            "msisdn": ["243822222222"],
            "product_name": ["Fixed Savings"],
            "account_type": ["FIXED SAVINGS"],
            "balance": [20.0],
            "currency_code": ["USD"],
            "date_approved": [pd.Timestamp("2026-06-01")],
            "maturity_date": [pd.Timestamp("2026-12-01")],
            "created_at": [pd.Timestamp("2026-06-01")],
        }
    )
    loans = pd.DataFrame(
        {
            "loan_id": ["L1"],
            "customer_id": ["100"],
            "msisdn1": ["243811111111"],
            "currency_code": ["USD"],
            "loan_balance": [3.0],
            "created_at": [pd.Timestamp("2026-07-02")],
        }
    )
    customers = pd.DataFrame(
        {
            "msisdn1": ["243811111111", "243822222222"],
            "created_at": [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-03")],
        }
    )
    return MpesaPreparedData(
        transactions=transactions,
        current_savings=current,
        fixed_savings=fixed,
        loans=loans,
        load_report=pd.DataFrame(),
        customers=customers,
    )


def _kpi_value(report: dict, indicator: str) -> float:
    kpi = report["kpi"]
    return float(kpi.loc[kpi["indicateur"].eq(indicator), "valeur"].iloc[0])


def test_clients_report_counts_reference_active_and_activation():
    report = build_mpesa_clients_report(
        _sample_prepared(),
        date_start="2026-07-01",
        date_end="2026-07-31",
    )

    assert _kpi_value(report, "clients_referentiel") == 2
    assert _kpi_value(report, "clients_connus_solution_numerique") == 2
    assert _kpi_value(report, "clients_actifs") == 1
    assert _kpi_value(report, "nouveaux_clients") == 2
    assert _kpi_value(report, "nouveaux_clients_actifs") == 1
    assert _kpi_value(report, "clients_sans_mouvement") == 1


def test_clients_report_uses_customers_date_for_new_clients():
    report = build_mpesa_clients_report(
        _sample_prepared(),
        date_start="2026-07-01",
        date_end="2026-07-31",
    )
    client_360 = report["client_360"].set_index("client_key")

    assert bool(client_360.loc["101", "nouveau_client"])
    assert client_360.loc["101", "segment_client"] == "nouveau_non_active"


def test_clients_report_reuses_dat_without_active_credit_logic():
    report = build_mpesa_clients_report(
        _sample_prepared(),
        date_start="2026-07-01",
        date_end="2026-07-31",
    )

    dat_without_credit = report["dat_sans_credit_actif"]
    assert len(dat_without_credit) == 1
    assert str(dat_without_credit.iloc[0]["customer_id"]) == "101"


def test_clients_display_columns_are_user_facing_french_names():
    report = build_mpesa_clients_report(
        _sample_prepared(),
        date_start="2026-07-01",
        date_end="2026-07-31",
    )

    display = prepare_dataframe_for_display(report["client_360"], enabled=True)

    assert "cle_client" in display.columns
    assert "id_client" in display.columns
    assert "numero_telephone" in display.columns
    assert "present_dans_referentiel_clients" in display.columns
    assert "nombre_comptes_ouverts" in display.columns
    assert "nombre_dat_positifs" in display.columns
    assert "nombre_credits_actifs" in display.columns
    assert "encours_credit" in display.columns
    assert "sans_mouvement_sur_periode" in display.columns
    assert all("customer" not in str(column).lower() for column in display.columns)
    assert all("key" not in str(column).lower() for column in display.columns)
