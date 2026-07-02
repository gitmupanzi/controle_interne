from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from credit_app.app_loader import load_dataframe_from_path
from credit_app.cycles import build_cycle_coverage_summary, get_cycle_spec
from credit_app.domain import (
    build_age_bucket_table,
    build_age_sex_pyramid_table,
    build_activity_table,
    build_cycle_period_series,
    build_cycle_priority_actions,
    build_cycle_watchlist,
    build_delay_bucket_table,
    build_operational_snapshot,
    build_overview_narrative,
    build_priority_actions,
    build_quality_checks,
    build_sex_distribution,
    build_status_flow_table,
    build_standardized_dataframe,
    build_summary_metrics,
    build_watchlist,
    filter_dataframe,
    get_cycle_primary_date_column,
)


class CreditDomainTests(unittest.TestCase):
    def test_standardization_maps_columns_and_derives_metrics(self) -> None:
        raw = pd.DataFrame(
            {
                "ID Client": ["C1"],
                "Numero Dossier": ["D1"],
                "Montant demande": [1000],
                "Montant accorde": [900],
                "Revenu mensuel": [500],
                "Charges mensuelles": [100],
                "Score Credit": [82],
                "Statut dossier": ["approuve"],
            }
        )

        standardized, mapping = build_standardized_dataframe(raw)

        self.assertEqual(mapping["ID Client"], "client_id")
        self.assertIn("capacite_remboursement", standardized.columns)
        self.assertIn("taux_endettement", standardized.columns)
        self.assertEqual(standardized.loc[0, "capacite_remboursement"], 400)
        self.assertAlmostEqual(standardized.loc[0, "taux_endettement"], 0.2)
        self.assertEqual(standardized.loc[0, "niveau_risque_calcule"], "Faible")
        self.assertEqual(standardized.loc[0, "statut_dossier"], "Approuvé")

    def test_quality_checks_detect_inconsistencies(self) -> None:
        raw = pd.DataFrame(
            {
                "client_id": ["C1", None],
                "dossier_id": ["D1", "D1"],
                "montant_demande": [1000, 500],
                "montant_accorde": [1200, -10],
                "revenu_mensuel": [200, None],
                "charge_mensuelle": [250, 50],
            }
        )
        standardized, _ = build_standardized_dataframe(raw)
        quality_df = build_quality_checks(standardized)
        checks = dict(zip(quality_df["controle"], quality_df["nombre_lignes"]))

        self.assertEqual(checks["Clients sans identifiant"], 1)
        self.assertEqual(checks["Dossiers dupliqués"], 2)
        self.assertEqual(checks["Montants accordés négatifs"], 1)
        self.assertEqual(checks["Montants accordés supérieurs au demandé"], 1)
        self.assertEqual(checks["Capacité de remboursement négative"], 1)

    def test_summary_metrics_returns_core_indicators(self) -> None:
        raw = pd.DataFrame(
            {
                "client_id": ["C1", "C2"],
                "montant_demande": [1000, 500],
                "montant_accorde": [1000, 0],
                "statut_dossier": ["Approuve", "Rejete"],
                "retard_jours": [0, 10],
                "revenu_mensuel": [500, 400],
                "charge_mensuelle": [100, 160],
            }
        )
        standardized, _ = build_standardized_dataframe(raw)
        metrics = build_summary_metrics(standardized)

        self.assertEqual(metrics["nombre_dossiers"], 2)
        self.assertEqual(metrics["nombre_clients"], 2)
        self.assertEqual(metrics["montant_demande_total"], 1500.0)
        self.assertEqual(metrics["montant_accorde_total"], 1000.0)
        self.assertAlmostEqual(metrics["taux_approbation"], 0.5)
        self.assertAlmostEqual(metrics["taux_retard"], 0.5)

    def test_operational_snapshot_and_narrative_capture_priority_signals(self) -> None:
        raw = pd.DataFrame(
            {
                "client_id": ["C1", "C2", "C3"],
                "dossier_id": ["D1", "D2", "D3"],
                "agence": ["Kin 1", "Kin 1", "Matadi"],
                "type_produit": ["PME", "PME", "Salaire"],
                "agent_credit": ["Agent A", "Agent A", "Agent B"],
                "montant_demande": [1000, 2000, 500],
                "montant_accorde": [900, 1800, 0],
                "revenu_mensuel": [500, 300, None],
                "charge_mensuelle": [100, 250, 50],
                "score_credit": [82, 40, 55],
                "retard_jours": [0, 45, 10],
                "statut_dossier": ["Approuvé", "En remboursement", "Rejeté"],
                "statut_remboursement": ["À jour", "En retard", "En retard"],
            }
        )
        standardized, _ = build_standardized_dataframe(raw)

        snapshot = build_operational_snapshot(standardized)
        narrative = build_overview_narrative(standardized)
        actions = build_priority_actions(standardized)

        self.assertEqual(snapshot["high_risk_count"], 1)
        self.assertEqual(snapshot["overdue_30_count"], 1)
        self.assertEqual(snapshot["top_agence"], "Kin 1")
        self.assertIn("Kin 1", narrative)
        self.assertTrue(any("30 jours de retard" in action for action in actions))

    def test_status_flow_delay_buckets_and_watchlist_reasons(self) -> None:
        raw = pd.DataFrame(
            {
                "client_id": ["C1", "C2", "C3", "C4"],
                "dossier_id": ["D1", "D2", "D3", "D4"],
                "statut_dossier": ["Reçu", "Approuvé", "En remboursement", "Rejeté"],
                "retard_jours": [0, 5, 45, None],
                "revenu_mensuel": [500, 400, 300, None],
                "charge_mensuelle": [100, 150, 350, None],
                "score_credit": [82, 61, 35, 58],
            }
        )
        standardized, _ = build_standardized_dataframe(raw)

        flow = build_status_flow_table(standardized)
        delay_buckets = build_delay_bucket_table(standardized)
        watchlist = build_watchlist(standardized)

        self.assertEqual(flow.iloc[0]["statut_dossier"], "Reçu")
        self.assertIn("31-90 jours", delay_buckets["classe_retard"].tolist())
        self.assertIn("motif_alerte", watchlist.columns)
        self.assertTrue(any("Risque élevé" in str(value) or "Capacité négative" in str(value) for value in watchlist["motif_alerte"]))

    def test_sex_and_age_distributions_are_standardized_and_ordered(self) -> None:
        raw = pd.DataFrame(
            {
                "Sexe": ["M", "Feminin", "F", None],
                "Age": [22, 37, 58, None],
            }
        )

        standardized, mapping = build_standardized_dataframe(raw)
        sex_distribution = build_sex_distribution(standardized)
        age_distribution = build_age_bucket_table(standardized)

        self.assertEqual(mapping["Sexe"], "sexe")
        self.assertEqual(mapping["Age"], "age")
        self.assertIn("Masculin", sex_distribution["sexe"].tolist())
        self.assertIn("Féminin", sex_distribution["sexe"].tolist())
        self.assertEqual(age_distribution["tranche_age"].tolist()[:3], ["18-24", "35-44", "55-64"])

    def test_age_sex_pyramid_table_builds_expected_counts(self) -> None:
        raw = pd.DataFrame(
            {
                "Sexe": ["M", "F", "M", "Feminin"],
                "Age": [22, 22, 40, 40],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        pyramid = build_age_sex_pyramid_table(standardized)

        self.assertIn("18-24", pyramid["tranche_age"].tolist())
        row_18_24 = pyramid.loc[pyramid["tranche_age"] == "18-24"].iloc[0]
        row_35_44 = pyramid.loc[pyramid["tranche_age"] == "35-44"].iloc[0]
        self.assertEqual(int(row_18_24["Masculin"]), 1)
        self.assertEqual(int(row_18_24["Féminin"]), 1)
        self.assertEqual(int(row_35_44["Masculin"]), 1)
        self.assertEqual(int(row_35_44["Féminin"]), 1)

    def test_included_credit_workbook_loads_and_standardizes(self) -> None:
        sample_path = Path("line_list/base_donnees_brute_credit.xlsx")
        self.assertTrue(sample_path.exists())

        raw = load_dataframe_from_path(sample_path, sheet_name="Base_brute_credit")
        standardized, _ = build_standardized_dataframe(raw)

        self.assertEqual(len(raw), 157)
        self.assertIn("client_id", standardized.columns)
        self.assertIn("agence", standardized.columns)
        self.assertIn("statut_dossier", standardized.columns)
        self.assertIn("statut_remboursement", standardized.columns)
        self.assertIn("sexe", standardized.columns)
        self.assertIn("age", standardized.columns)
        self.assertIn("activite_economique", standardized.columns)
        self.assertIn("capacite_remboursement", standardized.columns)
        self.assertIn("Non décaissé", standardized["statut_remboursement"].astype(str).unique().tolist())

    def test_cycle_reference_matches_credit_dataset(self) -> None:
        raw = pd.DataFrame(
            {
                "ID Client": ["C1"],
                "Numero Dossier": ["D1"],
                "Agence": ["Kin 1"],
                "Agent Credit": ["Agent A"],
                "Type Produit": ["PME"],
                "Date Demande": ["2026-01-05"],
                "Date Decision": ["2026-01-06"],
                "Montant demande": [1000],
                "Montant accorde": [900],
                "Revenu mensuel": [500],
                "Charges mensuelles": [100],
                "Score Credit": [82],
                "Statut dossier": ["approuve"],
                "Statut remboursement": ["a jour"],
                "Retard jours": [0],
                "Activite economique": ["Commerce"],
                "Garantie": ["Caution"],
                "Commentaire brut": ["RAS"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        coverage = build_cycle_coverage_summary(standardized, "credit")
        cycle_spec = get_cycle_spec("credit")

        self.assertEqual(cycle_spec["label"], "Cycle crédit")
        self.assertGreaterEqual(coverage["detected_count"], 10)
        self.assertIn("commentaire", standardized.columns)

    def test_specialized_cycle_specs_are_available(self) -> None:
        likelemba_spec = get_cycle_spec("likelemba")
        money_provider_spec = get_cycle_spec("money_provider")

        self.assertEqual(likelemba_spec["label"], "Likelemba solidaire")
        self.assertIn("nom_groupe", likelemba_spec["expected_columns"])
        self.assertEqual(money_provider_spec["label"], "Money Provider")
        self.assertIn("numero_reference", money_provider_spec["expected_columns"])

    def test_cycle_period_helpers_support_operation_cycles(self) -> None:
        raw = pd.DataFrame(
            {
                "date_operation": ["2026-01-05", "2026-01-20", "2026-02-01"],
                "montant_operation": [100, 200, 300],
                "agence": ["Kin", "Kin", "Matadi"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        date_column = get_cycle_primary_date_column(standardized, "money_provider")
        filtered = filter_dataframe(
            standardized,
            start_date=pd.Timestamp("2026-01-01").date(),
            end_date=pd.Timestamp("2026-01-31").date(),
            date_column=date_column,
        )
        period_df = build_cycle_period_series(standardized, "money_provider")

        self.assertEqual(date_column, "date_operation")
        self.assertEqual(len(filtered), 2)
        self.assertEqual(period_df["periode"].tolist(), ["2026-01", "2026-02"])
        self.assertEqual(period_df["nombre_lignes"].tolist(), [2, 1])
        self.assertEqual(period_df["montant_total"].tolist(), [300, 300])

    def test_filter_dataframe_accepts_generic_column_filters(self) -> None:
        raw = pd.DataFrame(
            {
                "date_operation": ["2026-01-05", "2026-01-06", "2026-01-07"],
                "agence": ["Kin", "Matadi", "Kin"],
                "type_operation": ["Cash-out", "Cash-in", "Cash-out"],
                "operateur": ["A1", "A2", "A1"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        filtered = filter_dataframe(
            standardized,
            column_filters={
                "agence": ["Kin"],
                "type_operation": ["Cash-out"],
                "operateur": ["A1"],
            },
            date_column="date_operation",
        )

        self.assertEqual(len(filtered), 2)
        self.assertEqual(sorted(filtered["agence"].unique().tolist()), ["Kin"])
        self.assertEqual(sorted(filtered["type_operation"].unique().tolist()), ["Cash-out"])

    def test_money_provider_watchlist_and_actions_are_cycle_aware(self) -> None:
        raw = pd.DataFrame(
            {
                "date_operation": ["2026-01-05", "2026-01-06"],
                "agence": ["Kin", "Kin"],
                "type_operation": ["Cash-out", "Cash-in"],
                "numero_reference": [None, "REF-2"],
                "operateur": ["Agent 1", None],
                "tresorier": [None, "Trésorier 1"],
                "telephone": ["", "099000"],
                "journal_transaction": ["", "Journal A"],
                "montant_operation": [120, 80],
                "solde_final": [-10, 150],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        watchlist = build_cycle_watchlist(standardized, "money_provider")
        actions = build_cycle_priority_actions(standardized, "money_provider")

        self.assertFalse(watchlist.empty)
        self.assertIn("motif_alerte", watchlist.columns)
        self.assertTrue(any("Référence manquante" in str(value) for value in watchlist["motif_alerte"]))
        self.assertTrue(any("référence manquante" in action.lower() for action in actions))

    def test_activity_table_counts_alerts_for_generic_cycle(self) -> None:
        raw = pd.DataFrame(
            {
                "agence": ["Kin", "Kin", "Matadi"],
                "montant_operation": [100, 200, 50],
                "numero_reference": [None, "OK-1", "OK-2"],
                "operateur": ["A", "B", "C"],
                "tresorier": ["T1", "T2", "T3"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        watchlist = build_cycle_watchlist(standardized, "money_provider")
        activity = build_activity_table(
            standardized,
            "agence",
            amount_columns=["montant_operation"],
            alert_index=watchlist.index,
            top_n=5,
        )

        self.assertEqual(activity.iloc[0]["agence"], "Kin")
        self.assertEqual(int(activity.iloc[0]["alertes"]), 1)


if __name__ == "__main__":
    unittest.main()
