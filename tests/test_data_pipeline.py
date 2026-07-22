from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from credit_app.compilation.fichiers_compilation import charger_fichiers_excel
from credit_app.colonne_valeur.colonne_nettoyage import load_excel_column_mapping
from credit_app.colonne_valeur.valeurs_nettoyage import _read_mapping_dataframe
from credit_app.services.data_pipeline import (
    assess_compilation_compatibility,
    build_preparation_summary,
    detect_cycle,
    normalize_filename,
    prepare_payload_from_dataframe,
)


class DataPipelineTests(unittest.TestCase):
    def test_normalize_filename_removes_accents_and_invisible_variants(self) -> None:
        self.assertEqual(normalize_filename("  Cycle Épargne—Juin.xlsx"), "cycle_epargne_juin")

    def test_cycle_detection_uses_business_tokens_not_substrings(self) -> None:
        credit = detect_cycle("102_cycle_credit_dashboard_cohorte_de_decaissement.xlsx")
        operations = detect_cycle("04_cycle_operations_depot_retrait_operations_apres_date.xlsx")
        conformite = detect_cycle("149_cycle_conformite_reporting_annuel_lbc_ft.xlsx")

        self.assertEqual(credit.cycle_key, "credit")
        self.assertEqual(operations.cycle_key, "operations_depot_retrait")
        self.assertEqual(conformite.cycle_key, "conformite")

    def test_cycle_detection_can_use_columns_when_name_is_neutral(self) -> None:
        result = detect_cycle(
            "extraction.xlsx",
            ["operation_id", "date_operation", "type_operation", "montant_operation"],
        )
        self.assertEqual(result.cycle_key, "operations_depot_retrait")
        self.assertGreater(result.confidence, 0.5)

    def test_compilation_rejects_different_cycles_and_incompatible_schemas(self) -> None:
        different_cycles = assess_compilation_compatibility(
            [
                ("cycle_credit_a.xlsx", ["client_id", "montant_accorde"], ["Data"]),
                ("cycle_epargne_b.xlsx", ["compte_id", "solde_compte"], ["Data"]),
            ]
        )
        different_schemas = assess_compilation_compatibility(
            [
                ("cycle_credit_a.xlsx", ["client_id", "montant_accorde"], ["Data"]),
                ("cycle_credit_b.xlsx", ["date_decaissement", "par30"], ["Data"]),
            ]
        )

        self.assertFalse(different_cycles.compatible)
        self.assertFalse(different_schemas.compatible)

    def test_compilation_preserves_source_traceability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Path(temp_dir) / "cycle_credit_a.xlsx"
            second = Path(temp_dir) / "cycle_credit_b.xlsx"
            pd.DataFrame({"date_operation": ["2026-01-01"], "montant": [10]}).to_excel(first, sheet_name="Data", index=False)
            pd.DataFrame({"date_operation": ["2026-01-02"], "montant": [20]}).to_excel(second, sheet_name="Data", index=False)

            compiled = charger_fichiers_excel(
                liste_fichiers=[str(first), str(second)],
                sheet_name="Data",
                renommer_variable=False,
                variables_brute=True,
            )

        self.assertEqual(len(compiled), 2)
        self.assertEqual(set(compiled["source_fichier"]), {first.name, second.name})
        self.assertEqual(set(compiled["source_feuille"]), {"Data"})
        self.assertEqual(compiled["numero_ligne_source"].tolist(), [2, 2])

    def test_compilation_rejects_a_missing_sheet_instead_of_skipping_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cycle_credit.xlsx"
            pd.DataFrame({"id": [1]}).to_excel(path, sheet_name="Data", index=False)
            with self.assertRaisesRegex(ValueError, "Feuille 'Absente'"):
                charger_fichiers_excel(
                    liste_fichiers=[str(path)],
                    sheet_name="Absente",
                    renommer_variable=False,
                    variables_brute=True,
                )

    def test_preparation_summary_reports_duplicates_mapping_and_missing_fields(self) -> None:
        raw = pd.DataFrame({"Code client": ["C1", "C1"], "Montant demandé": [10, 10]})
        payload = prepare_payload_from_dataframe(raw)
        summary = build_preparation_summary(
            payload,
            expected_columns=["client_id", "montant_demande", "date_demande"],
        )

        self.assertEqual(summary["duplicate_count"], 1)
        self.assertGreaterEqual(summary["renamed_columns"], 2)
        self.assertIn("date_demande", summary["missing_expected"])
        self.assertEqual(summary["status"], "warning")

    def test_column_mapping_rejects_contradictory_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rename.xlsx"
            pd.DataFrame(
                {"Original": ["Code client", "Code client"], "Renamed": ["client_id", "dossier_id"]}
            ).to_excel(path, index=False)
            with self.assertRaisesRegex(ValueError, "contradictoire"):
                load_excel_column_mapping(path)

    def test_value_mapping_rejects_empty_and_contradictory_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_path = Path(temp_dir) / "empty.xlsx"
            conflict_path = Path(temp_dir) / "conflict.xlsx"
            pd.DataFrame({"Original": ["A"], "Renamed": [None], "Variable": ["statut"]}).to_excel(empty_path, index=False)
            pd.DataFrame(
                {
                    "Original": ["A", "A"],
                    "Renamed": ["Actif", "Inactif"],
                    "Variable": ["statut", "statut"],
                }
            ).to_excel(conflict_path, index=False)

            with self.assertRaisesRegex(ValueError, "essentielle vide"):
                _read_mapping_dataframe(empty_path, require_variable=True)
            with self.assertRaisesRegex(ValueError, "contradictoires"):
                _read_mapping_dataframe(conflict_path, require_variable=True)


if __name__ == "__main__":
    unittest.main()
