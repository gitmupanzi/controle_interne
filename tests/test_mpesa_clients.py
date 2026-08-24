import pandas as pd
from dataclasses import replace

from credit_app.display_columns import prepare_dataframe_for_display
from credit_app.services.mpesa_analysis import (
    MpesaPreparedData,
    build_mpesa_clients_report,
    prepare_current_savings,
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
    assert _kpi_value(report, "clients_inactifs_observes") == 0
    assert _kpi_value(report, "clients_sans_produit_observe") == 0


def test_clients_report_identifies_customers_without_savings_or_loans():
    prepared = replace(
        _sample_prepared(),
        customers=pd.concat(
            [
                _sample_prepared().customers,
                pd.DataFrame(
                    {
                        "msisdn1": ["243844444444"],
                        "created_at": [pd.Timestamp("2026-06-15")],
                    }
                ),
            ],
            ignore_index=True,
        ),
        g2_transactions=pd.DataFrame(
            {
                "phone_prefixe": ["243844444444"],
                "Nom_client": ["CLIENT SANS PRODUIT"],
                "completion_time": [pd.Timestamp("2026-07-20")],
            }
        ),
    )

    report = build_mpesa_clients_report(
        prepared,
        date_start="2026-07-01",
        date_end="2026-07-31",
    )

    assert _kpi_value(report, "clients_sans_produit_observe") == 1
    no_product = report["listes_action"]["clients_sans_produit_observe"]
    assert len(no_product) == 1
    assert no_product.iloc[0]["numero_client"] == "243844444444"
    assert no_product.iloc[0]["nom_client"] == "CLIENT SANS PRODUIT"
    assert no_product.iloc[0]["statut_usage"] == "sans_produit_sans_mouvement"
    assert no_product.columns.get_loc("nom_client") == no_product.columns.get_loc("numero_client") + 1


def test_clients_report_links_savings_account_by_msisdn1_when_msisdn_column_is_empty():
    current_savings = prepare_current_savings(
        pd.DataFrame(
            {
                "customer_id": ["900"],
                "msisdn": [pd.NA],
                "msisdn1": ["2438555555550"],
                "product_name": ["Open Savings"],
                "account_type": ["NORMAL SAVINGS"],
                "balance": [15.0],
                "currency_code": ["USD"],
                "created_at": [pd.Timestamp("2026-06-01")],
            }
        )
    )
    prepared = MpesaPreparedData(
        transactions=pd.DataFrame(),
        current_savings=current_savings,
        fixed_savings=pd.DataFrame(),
        loans=pd.DataFrame(),
        load_report=pd.DataFrame(),
        customers=pd.DataFrame(
            {
                "msisdn1": ["243855555555"],
                "created_at": [pd.Timestamp("2026-06-01")],
            }
        ),
    )

    report = build_mpesa_clients_report(
        prepared,
        date_start="2026-07-01",
        date_end="2026-07-31",
    )

    assert _kpi_value(report, "clients_referentiel") == 1
    assert _kpi_value(report, "clients_sans_produit_observe") == 0
    assert report["listes_action"]["clients_sans_produit_observe"].empty


def test_clients_report_separates_inactive_from_simple_no_movement():
    prepared = _sample_prepared()
    prepared = replace(
        prepared,
        transactions=pd.concat(
            [
                prepared.transactions,
                pd.DataFrame(
                    {
                        "id": [99],
                        "customer_id": ["999"],
                        "msisdn1": ["243899999999"],
                        "account_type": ["NORMAL SAVINGS"],
                        "reference_id": ["R-OLD"],
                        "currency_code": ["USD"],
                        "dr": [0],
                        "cr": [1],
                        "bal_before": [0],
                        "bal_after": [1],
                        "ref_no": ["REF-OLD"],
                        "description": ["Epargne depot"],
                        "created_at": [pd.Timestamp("2026-03-01")],
                    }
                ),
            ],
            ignore_index=True,
        ),
        customers=pd.concat(
            [
                prepared.customers,
                pd.DataFrame(
                {
                    "msisdn1": ["243833333333"],
                    "created_at": [pd.Timestamp("2026-05-01")],
                }
                ),
            ],
            ignore_index=True,
        ),
    )

    report = build_mpesa_clients_report(
        prepared,
        date_start="2026-07-01",
        date_end="2026-07-31",
        inactivity_threshold_days=30,
    )

    assert _kpi_value(report, "clients_sans_mouvement") == 2
    assert _kpi_value(report, "clients_inactifs_observes") == 1

    inactive = report["listes_action"]["clients_inactifs_observes"]
    assert len(inactive) == 1
    assert inactive.iloc[0]["numero_client"] == "243833333333"
    assert inactive.iloc[0]["statut_inactivite"] == "inactif_observe"
    assert "aucune operation observee" in inactive.iloc[0]["lecture_inactivite"]


def test_clients_inactifs_uses_g2_name_after_client_number():
    prepared = replace(
        _sample_prepared(),
        transactions=pd.DataFrame(
            {
                "id": [99],
                "customer_id": ["999"],
                "msisdn1": ["243899999999"],
                "account_type": ["NORMAL SAVINGS"],
                "reference_id": ["R-OLD"],
                "currency_code": ["USD"],
                "dr": [0],
                "cr": [1],
                "bal_before": [0],
                "bal_after": [1],
                "ref_no": ["REF-OLD"],
                "description": ["Epargne depot"],
                "created_at": [pd.Timestamp("2026-03-01")],
            }
        ),
        current_savings=pd.DataFrame(),
        fixed_savings=pd.DataFrame(),
        loans=pd.DataFrame(),
        customers=pd.DataFrame(
            {
                "msisdn1": ["243833333333"],
                "created_at": [pd.Timestamp("2026-05-01")],
            }
        ),
        g2_transactions=pd.DataFrame(
            {
                "phone_prefixe": ["243833333333", "243833333333"],
                "Nom_client": ["CLIENT NOM G2", "ANCIEN NOM G2"],
                "completion_time": [pd.Timestamp("2026-07-15"), pd.Timestamp("2026-07-10")],
            }
        ),
    )

    report = build_mpesa_clients_report(
        prepared,
        date_start="2026-07-01",
        date_end="2026-07-31",
        inactivity_threshold_days=30,
    )

    inactive = report["listes_action"]["clients_inactifs_observes"]
    assert inactive.iloc[0]["numero_client"] == "243833333333"
    assert inactive.iloc[0]["nom_client"] == "CLIENT NOM G2"
    assert inactive.columns.get_loc("nom_client") == inactive.columns.get_loc("numero_client") + 1
    assert inactive.columns.get_loc("date_creation_compte") == inactive.columns.get_loc("nom_client") + 1
    assert inactive.columns.get_loc("date_premiere_operation_periode") > inactive.columns.get_loc("date_creation_compte")
    assert "date_creation_compte" in inactive.columns
    assert "date_premiere_operation_periode" in inactive.columns
    assert "date_derniere_operation" in inactive.columns
    assert inactive.iloc[0]["date_creation_compte"] == pd.Timestamp("2026-05-01")


def test_clients_report_uses_customers_date_for_new_clients():
    report = build_mpesa_clients_report(
        _sample_prepared(),
        date_start="2026-07-01",
        date_end="2026-07-31",
    )
    client_360 = report["client_360"].set_index("client_key")

    assert bool(client_360.loc["101", "nouveau_client"])
    assert client_360.loc["101", "segment_client"] == "nouveau_non_active"


def test_clients_report_tracks_new_clients_accounts_activity_by_currency():
    report = build_mpesa_clients_report(
        _sample_prepared(),
        date_start="2026-07-01",
        date_end="2026-07-31",
    )

    activation = report["nouveaux_clients_comptes_activation"].set_index(["client_key", "currency_code"])

    assert ("100", "USD") in activation.index
    assert bool(activation.loc[("100", "USD"), "nouveau_client"])
    assert bool(activation.loc[("100", "USD"), "actif_periode"])
    assert int(activation.loc[("100", "USD"), "nombre_transactions"]) == 2
    assert activation.loc[("100", "USD"), "solde_compte_ouvert"] == 5.0
    assert activation.loc[("100", "USD"), "solde_dat"] == 0.0

    assert ("101", "USD") in activation.index
    assert bool(activation.loc[("101", "USD"), "nouveau_client"])
    assert not bool(activation.loc[("101", "USD"), "actif_periode"])
    assert int(activation.loc[("101", "USD"), "nombre_transactions"]) == 0
    assert activation.loc[("101", "USD"), "solde_compte_ouvert"] == 0.0
    assert activation.loc[("101", "USD"), "solde_dat"] == 20.0


def test_clients_report_groups_encours_by_amount_band_and_currency():
    report = build_mpesa_clients_report(
        _sample_prepared(),
        date_start="2026-07-01",
        date_end="2026-07-31",
    )

    tranches = report["encours_clients_tranches"].set_index(
        ["currency_code", "famille_encours", "tranche_encours"]
    )

    assert ("USD", "compte_ouvert", "Moins de 100") in tranches.index
    assert ("USD", "dat", "Moins de 100") in tranches.index
    assert ("USD", "credit", "Moins de 100") in tranches.index
    assert float(tranches.loc[("USD", "compte_ouvert", "Moins de 100"), "encours_total"]) == 5.0
    assert float(tranches.loc[("USD", "dat", "Moins de 100"), "encours_total"]) == 20.0
    assert float(tranches.loc[("USD", "credit", "Moins de 100"), "encours_total"]) == 3.0


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
