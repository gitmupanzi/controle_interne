from io import BytesIO

import pandas as pd

from credit_app.display_columns import (
    USER_COLUMN_NAME_PATTERN,
    prepare_dataframe_with_user_columns,
    resolve_user_column_mapping,
    validate_user_column_names,
)
from credit_app.services.mpesa_analysis import create_excel_export


def test_prepare_dataframe_with_user_columns_uses_reference_mapping():
    frame = pd.DataFrame(
        {
            "customer_id": ["37370"],
            "currency_code": ["USD"],
            "loan_amount": [5.0],
            "is_interest_calculated": ["1"],
            "last_interest_calculation_date": [pd.Timestamp("2026-07-20")],
            "next_interest_calculation_date": [pd.Timestamp("2026-08-20")],
            "Date Échéance": [pd.Timestamp("2026-07-31")],
        }
    )

    display, mapping = prepare_dataframe_with_user_columns(frame, enabled=True)

    assert list(display.columns) == [
        "id_client",
        "devise",
        "montant_credit",
        "interet_calcule",
        "date_dernier_calcul_interet",
        "date_prochain_calcul_interet",
        "date_echeance",
    ]
    assert mapping["customer_id"] == "id_client"
    assert display["id_client"].tolist() == ["37370"]
    assert display["montant_credit"].tolist() == [5.0]


def test_prepare_dataframe_with_user_columns_can_be_disabled():
    frame = pd.DataFrame({"customer_id": ["37370"], "currency_code": ["USD"]})

    display, mapping = prepare_dataframe_with_user_columns(frame, enabled=False)

    assert display is frame
    assert mapping == {}
    assert list(display.columns) == ["customer_id", "currency_code"]


def test_resolve_user_column_mapping_keeps_colliding_columns():
    mapping = resolve_user_column_mapping(["msisdn1", "msisdn", "telephone"])

    assert len(set(mapping.values())) == 3
    assert mapping["msisdn1"] == "numero_telephone"
    assert all(USER_COLUMN_NAME_PATTERN.fullmatch(column) for column in mapping.values())


def test_validate_user_column_names_detects_non_snake_case_columns():
    invalid = validate_user_column_names(["id_client", "Date Échéance", "solde-final"])

    assert invalid == ["Date Échéance", "solde-final"]


def test_create_excel_export_renames_visible_columns_when_enabled():
    export = create_excel_export(
        {
            "accounting_client_balances": pd.DataFrame(
                {
                    "customer_id": ["37370"],
                    "currency_code": ["USD"],
                    "solde_epargne_courante": [0.0],
                    "Date Échéance": [pd.Timestamp("2026-07-31")],
                }
            )
        },
        rename_user_columns=True,
    )

    workbook = pd.ExcelFile(BytesIO(export), engine="openpyxl")
    exported = pd.read_excel(workbook, sheet_name="Balance_Clients_Turbo")

    assert list(exported.columns) == [
        "id_client",
        "devise",
        "solde_epargne_courante",
        "date_echeance",
    ]
    assert validate_user_column_names(exported.columns) == []
