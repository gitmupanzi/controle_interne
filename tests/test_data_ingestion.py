from __future__ import annotations

from io import BytesIO
import unittest

import pandas as pd

from credit_app.app_loader import DataLoadError, load_dataframe_from_bytes
from credit_app.data_schema import (
    DataSchemaError,
    G2_TRANSACTIONS_SCHEMA,
    SQL_OPERATIONS_SCHEMA,
    canonical_column_key,
    normalize_dataframe_headers,
    validate_dataframe_schema,
)
from credit_app.services.mpesa_analysis import prepare_current_savings
from credit_app.sql_operations import (
    build_client_movement_summary_table,
    normalize_operations_analysis_frame,
)


class DataIngestionTests(unittest.TestCase):
    def test_column_keys_ignore_accents_spacing_and_punctuation(self) -> None:
        self.assertEqual(canonical_column_key("  Numéro opération. "), "numero_operation")
        self.assertEqual(canonical_column_key("NUMERO-OPERATION"), "numero_operation")

    def test_alias_columns_are_normalized_and_coalesced(self) -> None:
        raw = pd.DataFrame(
            {
                "Receipt No.": ["R1", None],
                "receipt_no": [None, "R2"],
                "Currency": ["CDF", "USD"],
                "Opposite Party": ["243810000001", "243810000002"],
            }
        )
        normalized = normalize_dataframe_headers(raw, G2_TRANSACTIONS_SCHEMA)

        self.assertEqual(normalized.columns.tolist().count("Receipt No"), 1)
        self.assertEqual(normalized["Receipt No"].tolist(), ["R1", "R2"])

    def test_missing_columns_error_names_source_missing_and_available_columns(self) -> None:
        raw = pd.DataFrame({"DATE_OPERATION": ["2026-01-01"]})

        with self.assertRaises(DataSchemaError) as context:
            validate_dataframe_schema(raw, SQL_OPERATIONS_SCHEMA, "dbo_operations.xlsx", raise_on_missing=True)

        message = str(context.exception)
        self.assertIn("dbo_operations.xlsx", message)
        self.assertIn("ID", message)
        self.assertIn("DATE_OPERATION", message)

    def test_flexible_csv_loader_supports_semicolon_and_utf8(self) -> None:
        loaded = load_dataframe_from_bytes("nom;montant\nÉpargne;12,5\n".encode("utf-8"), "test.csv")

        self.assertEqual(loaded.columns.tolist(), ["nom", "montant"])
        self.assertEqual(loaded.iloc[0]["nom"], "Épargne")

    def test_excel_loader_reads_selected_sheet(self) -> None:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            pd.DataFrame({"id": [1]}).to_excel(writer, sheet_name="A", index=False)
            pd.DataFrame({"id": [2]}).to_excel(writer, sheet_name="B", index=False)

        loaded = load_dataframe_from_bytes(buffer.getvalue(), "test.xlsx", "B")

        self.assertEqual(loaded["id"].tolist(), [2])

    def test_empty_file_is_rejected_when_data_is_required(self) -> None:
        buffer = BytesIO()
        pd.DataFrame(columns=["id"]).to_excel(buffer, index=False)

        with self.assertRaisesRegex(DataLoadError, "vide"):
            load_dataframe_from_bytes(buffer.getvalue(), "empty.xlsx", reject_empty=True)

    def test_invalid_dates_amounts_and_nulls_are_explicitly_coerced(self) -> None:
        prepared = prepare_current_savings(
            pd.DataFrame(
                {
                    "customer_id": ["C1", "C2"],
                    "balance": ["incorrect", None],
                    "created_at": ["not-a-date", None],
                }
            )
        )

        self.assertEqual(prepared["balance"].tolist(), [0.0, 0.0])
        self.assertTrue(prepared["created_at"].isna().all())

    def test_missing_operation_id_is_not_fabricated_and_counts_rows(self) -> None:
        raw = pd.DataFrame(
            {
                "client_id": ["C1", "C1"],
                "nom_client": ["Client", "Client"],
                "type_mouvement": ["Depot", "Retrait"],
                "montant_operation": [100.0, 25.0],
                "code_devise": ["CDF", "CDF"],
            }
        )
        normalized = normalize_operations_analysis_frame(raw)
        summary = build_client_movement_summary_table(normalized, conversion_rate=2800.0)

        self.assertTrue(normalized["operation_id"].isna().all())
        self.assertEqual(summary.iloc[0]["nb_operations"], 2)


if __name__ == "__main__":
    unittest.main()
