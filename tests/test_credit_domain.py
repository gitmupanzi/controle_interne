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
    build_epargne_agent_portfolio_table,
    build_epargne_dormancy_table,
    build_epargne_kyc_completeness_table,
    build_epargne_multi_account_clients,
    build_epargne_multi_account_table,
    build_epargne_phone_quality_table,
    build_epargne_product_concentration_table,
    build_operational_snapshot,
    build_overview_narrative,
    build_priority_actions,
    build_provenance_summary_table,
    build_quality_checks,
    build_sex_distribution,
    build_status_flow_table,
    build_standardized_dataframe,
    build_summary_metrics,
    build_watchlist,
    filter_dataframe,
    get_cycle_primary_date_column,
    get_reference_column_count,
)


class CreditDomainTests(unittest.TestCase):
    def test_reference_mapping_file_is_loaded(self) -> None:
        self.assertGreaterEqual(get_reference_column_count(), 100)

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

    def test_credit_watchlist_uses_catalog_rules_when_product_is_recognized(self) -> None:
        raw = pd.DataFrame(
            {
                "client_id": ["C1", "C2"],
                "dossier_id": ["D1", "D2"],
                "type_produit": ["Avance sur salaire", "CrÃ©dit Auto"],
                "montant_demande": [500, 25000],
                "revenu_mensuel": [900, 4000],
                "garantie": ["", None],
                "duree_credit_mois": [2, 30],
                "taux_interet": [6, 3],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        watchlist = build_watchlist(standardized)
        motifs = " | ".join(watchlist["motif_alerte"].astype(str).tolist())

        self.assertIn("Garantie non renseignée", motifs)
        self.assertIn("Montant hors référentiel produit", motifs)
        self.assertIn("Durée hors référentiel produit", motifs)
        self.assertIn("Avance sur salaire > 1/3 du salaire", motifs)

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

    def test_excel_value_cleaning_is_applied_to_standard_columns(self) -> None:
        raw = pd.DataFrame(
            {
                "Sexe": ["garçon", "fem"],
                "Activité économique": ["cultivatrice", "comerce"],
                "Localité": ["haut_katanga", "kinshasa"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)

        self.assertEqual(standardized["sexe"].tolist(), ["Masculin", "Féminin"])
        self.assertEqual(
            standardized["activite_economique"].tolist(),
            ["Agriculteur(trice)/Cultivateur(trice)", "Commerçant(e)"],
        )
        self.assertEqual(standardized["zone_geographique"].tolist(), ["Haut Katanga", "Kinshasa"])

    def test_excel_value_cleaning_supports_boolean_and_age_units(self) -> None:
        raw = pd.DataFrame(
            {
                "Age": [30, 6],
                "Unité d'âge": ["an", "moi"],
                "Statut test reprise": ["oui", "n0n"],
                "Incident majeur": ["true", "false"],
            }
        )

        standardized, mapping = build_standardized_dataframe(raw)

        self.assertEqual(mapping["Unité d'âge"], "unite_age")
        self.assertEqual(mapping["Statut test reprise"], "statut_test_reprise")
        self.assertEqual(mapping["Incident majeur"], "incident_majeur")
        self.assertEqual(standardized["unite_age"].tolist(), ["ans", "mois"])
        self.assertEqual(standardized["statut_test_reprise"].tolist(), ["Oui", "Non"])
        self.assertEqual(standardized["incident_majeur"].tolist(), ["Oui", "Non"])

    def test_reference_mapping_covers_internal_control_cycles(self) -> None:
        raw = pd.DataFrame(
            {
                "Nom caissier": ["A"],
                "Compte bancaire": ["001"],
                "Numéro pièce": ["PC-1"],
                "Matricule agent": ["AG-1"],
                "Profil d'accès": ["Lecture"],
                "Support sauvegarde": ["Disque externe"],
            }
        )

        standardized, mapping = build_standardized_dataframe(raw)

        self.assertEqual(mapping["Nom caissier"], "caissier")
        self.assertEqual(mapping["Compte bancaire"], "compte_bancaire")
        self.assertEqual(mapping["Numéro pièce"], "piece_id")
        self.assertEqual(mapping["Matricule agent"], "agent_id")
        self.assertEqual(mapping["Profil d'accès"], "profil_acces")
        self.assertEqual(mapping["Support sauvegarde"], "support_sauvegarde")
        for column_name in [
            "caissier",
            "compte_bancaire",
            "piece_id",
            "agent_id",
            "profil_acces",
            "support_sauvegarde",
        ]:
            self.assertIn(column_name, standardized.columns)

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
        if not sample_path.exists():
            self.skipTest("Le fichier de démonstration crédit n'est pas présent dans ce dépôt.")

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
        crm_clients_spec = get_cycle_spec("crm_clients")

        self.assertEqual(likelemba_spec["label"], "Likelemba solidaire")
        self.assertIn("nom_groupe", likelemba_spec["expected_columns"])
        self.assertEqual(money_provider_spec["label"], "Money Provider")
        self.assertIn("numero_reference", money_provider_spec["expected_columns"])
        self.assertEqual(crm_clients_spec["label"], "Suivi clients CRM")
        self.assertIn("client_id", crm_clients_spec["expected_columns"])

    def test_crm_client_cycle_maps_columns_and_builds_watchlist(self) -> None:
        raw = pd.DataFrame(
            {
                "Id de l’enregistrement": ["CL-1", "CL-2", "CL-3"],
                "Gestionnaire du Client": ["Agent A", None, "Agent B"],
                "Nom": ["Kanku", "Mbuyi", "Mbuyi"],
                "Client Name": ["Jean Kanku", "Anne Mbuyi", "Paul Mbuyi"],
                "Téléphone": ["099", None, "0812345678"],
                "Portable": [None, "0823456789", "0812345678"],
                "E-mail": ["jean@example.com", "", "badmail"],
                "Date de la dernière activité": ["2026-01-01", "2026-07-01", None],
                "Province de correspondance": ["Kinshasa", None, "Kinshasa"],
                "Catégorie socio-professionnelle": ["Commerçant", None, "Commerçant"],
                "Numéro de la pièce d’identité": ["ID-1", "0", "ID-1"],
                "Numéro de compte client": ["CP-1", "", "CP-3"],
                "Locked": [False, True, False],
                "Rejet des mails": [False, False, True],
                "Mode Désabonné": ["", "", "SMS"],
                "Origine du Prospect": ["Appel entrant", "Terrain", "Terrain"],
            }
        )

        standardized, mapping = build_standardized_dataframe(raw)
        watchlist = build_cycle_watchlist(standardized, "crm_clients")
        coverage = build_cycle_coverage_summary(standardized, "crm_clients")
        motifs = " | ".join(watchlist["motif_alerte"].astype(str).tolist())

        self.assertEqual(mapping["Id de l’enregistrement"], "client_id")
        self.assertEqual(mapping["Gestionnaire du Client"], "agent_credit")
        self.assertEqual(mapping["Date de la dernière activité"], "date_operation")
        self.assertEqual(mapping["Province de correspondance"], "zone_geographique")
        self.assertEqual(mapping["Catégorie socio-professionnelle"], "categorie")
        self.assertEqual(mapping["Numéro de compte client"], "compte_id")
        self.assertIn("nom_client", standardized.columns)
        self.assertIn("date_operation", standardized.columns)
        self.assertIn("jours_inactivite", watchlist.columns)
        self.assertIn("telephone", watchlist.columns)
        self.assertGreaterEqual(coverage["detected_count"], 8)
        self.assertIn("Gestionnaire non renseigné", motifs)
        self.assertIn("Téléphone non fiable", motifs)
        self.assertIn("E-mail non fiable", motifs)
        self.assertIn("Pièce d'identité manquante", motifs)
        self.assertIn("Pièce d'identité partagée", motifs)
        self.assertIn("Fiche verrouillée", motifs)
        self.assertIn("Client désabonné", motifs)

    def test_included_epargne_workbook_loads_and_standardizes(self) -> None:
        sample_candidates = sorted(
            path
            for path in Path("line_list").glob("Encours des épargnants *.xlsx")
            if not path.name.startswith("~$")
        )
        self.assertTrue(sample_candidates)

        raw = load_dataframe_from_path(sample_candidates[0], sheet_name="Sheet0")
        standardized, _ = build_standardized_dataframe(raw)
        coverage = build_cycle_coverage_summary(standardized, "epargne")

        self.assertIn("client_id", standardized.columns)
        self.assertIn("compte_id", standardized.columns)
        self.assertIn("solde_compte", standardized.columns)
        self.assertIn("date_operation", standardized.columns)
        self.assertIn("type_produit", standardized.columns)
        self.assertIn("type_client", standardized.columns)
        self.assertIn("agent_credit", standardized.columns)
        self.assertGreaterEqual(coverage["detected_count"], 7)

    def test_epargne_snapshot_maps_expected_columns_and_watchlist(self) -> None:
        raw = pd.DataFrame(
            {
                "Code client": ["C1", "C2"],
                "Compte": ["ACC-1", "ACC-2"],
                "Nom client": ["Client A", "Client B"],
                "Téléphone": ["099", "081"],
                "Type client": ["Personne physique", "Personne morale"],
                "Type produit": ["Compte courant CDF", None],
                "Encours epargnant": [-50, 1200],
                "Date dernière transaction": ["2025-01-01", "2026-06-29"],
                "Gestionnaire": ["Agent 1", "Agent 2"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        watchlist = build_cycle_watchlist(standardized, "epargne")

        self.assertIn("compte_id", standardized.columns)
        self.assertIn("solde_compte", standardized.columns)
        self.assertIn("date_operation", standardized.columns)
        self.assertIn("jours_inactivite", watchlist.columns)
        self.assertIn("champs_kyc_manquants", watchlist.columns)
        self.assertTrue(any("Solde négatif" in str(value) for value in watchlist["motif_alerte"]))
        self.assertTrue(any("Compte inactif >= 90 j" in str(value) for value in watchlist["motif_alerte"]))
        self.assertTrue(any("Téléphone non fiable" in str(value) for value in watchlist["motif_alerte"]))

    def test_epargne_advanced_analysis_tables_are_computed(self) -> None:
        raw = pd.DataFrame(
            {
                "Code client": ["C1", "C1", "C2", "C3", "C4"],
                "Compte": ["ACC-1", "ACC-2", "ACC-3", "ACC-4", "ACC-5"],
                "Téléphone": ["243990000001", "0810000000", "bad", None, "243990000005"],
                "Zone géographique": ["Zone A", None, "Zone B", None, "Zone C"],
                "Sexe": ["M", "F", None, "F", "M"],
                "Catégorie": ["M", "F", None, None, "M"],
                "Type client": ["Personne physique", "Personne physique", "Personne morale", "Groupe", "Personne physique"],
                "Type produit": ["Produit A", "Produit A", "Produit B", "Produit C", "Produit A"],
                "Encours épargnant": [1000, -50, 5000, 300, 700],
                "Date dernière transaction": ["2026-06-29", "2026-05-10", None, "2026-03-15", "2026-06-01"],
                "Gestionnaire": ["Agent 1", "Agent 1", "Agent 2", "Agent 2", "Agent 1"],
                "Provenance": ["Lot A", "Lot A", "Lot B", "Lot B", "Lot A"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        dormancy_df = build_epargne_dormancy_table(standardized)
        multi_account_df = build_epargne_multi_account_table(standardized)
        top_clients_df = build_epargne_multi_account_clients(standardized, top_n=5)
        concentration_df = build_epargne_product_concentration_table(standardized, top_n=5)
        agent_df = build_epargne_agent_portfolio_table(standardized, top_n=5)
        phone_df = build_epargne_phone_quality_table(standardized)
        kyc_df = build_epargne_kyc_completeness_table(standardized)
        provenance_df = build_provenance_summary_table(standardized)

        self.assertIn("31-90 j", dormancy_df["classe_inactivite"].tolist())
        self.assertIn("Non documenté", dormancy_df["classe_inactivite"].tolist())
        self.assertIn("2 comptes", multi_account_df["classe_comptes"].tolist())
        self.assertEqual(top_clients_df.iloc[0]["client_id"], "C1")
        self.assertIn("nom_client", top_clients_df.columns)
        self.assertIn("Produit A", concentration_df["type_produit"].tolist())
        self.assertIn("Agent 1", agent_df["agent_credit"].tolist())
        self.assertIn("Format international", phone_df["qualite_telephone"].tolist())
        self.assertIn("Autre format", phone_df["qualite_telephone"].tolist())
        self.assertIn("0 champ manquant", kyc_df["classe_completude"].tolist())
        self.assertIn("Lot A", provenance_df["Provenance"].tolist())

    def test_epargne_watchlist_surfaces_advanced_vigilance_signals(self) -> None:
        raw = pd.DataFrame(
            {
                "Code client": ["C1", "C1", "C1", "C2"],
                "Compte": ["ACC-1", "ACC-2", "ACC-3", "ACC-4"],
                "Nom client": ["Client A", "Client A", "Client A", "Client B"],
                "Téléphone": ["bad", "bad", "243990000003", None],
                "Zone géographique": [None, None, "Zone A", None],
                "Sexe": ["M", "M", "M", None],
                "Catégorie": ["M", "M", "M", None],
                "Type client": ["Personne physique"] * 4,
                "Type produit": ["Produit A", "Produit A", None, "Produit B"],
                "Encours épargnant": [-50, 300000, 100, 200],
                "Date dernière transaction": ["2026-03-01", "2026-03-01", "2026-06-29", None],
                "Gestionnaire": ["Agent 1", "Agent 1", "Agent 1", "Agent 2"],
                "Provenance": ["Lot A", "Lot B", "Lot A", "Lot B"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        watchlist = build_cycle_watchlist(standardized, "epargne")
        motifs = " | ".join(watchlist["motif_alerte"].astype(str).tolist())

        self.assertIn("jours_inactivite", watchlist.columns)
        self.assertIn("champs_kyc_manquants", watchlist.columns)
        self.assertIn("nombre_comptes_client", watchlist.columns)
        self.assertIn("telephone", watchlist.columns)
        self.assertIn("Solde négatif", motifs)
        self.assertIn("Compte inactif >= 90 j", motifs)
        self.assertIn("Téléphone non fiable", motifs)
        self.assertIn("KYC incomplet (2+ champs)", motifs)
        self.assertIn("Client multi-comptes (>= 3)", motifs)
        self.assertIn("Dormance sur solde significatif", motifs)

    def test_epargne_watchlist_uses_catalog_rules_for_dat_and_segmented_products(self) -> None:
        raw = pd.DataFrame(
            {
                "Code client": ["C1", "C2"],
                "Compte": ["DAT-1", "ELU-1"],
                "Nom client": ["Client DAT", "Client Maman"],
                "Type client": ["Personne morale", "Personne physique"],
                "Type produit": ["DAT SociÃ©tÃ©", "Elubu ya ba Maman"],
                "Encours Ã©pargnant": [1200, 500],
                "Taux interet": [10, 2],
                "Sexe": ["F", "M"],
                "Date derniÃ¨re transaction": ["2026-06-29", "2026-06-29"],
            }
        )

        standardized, _ = build_standardized_dataframe(raw)
        watchlist = build_cycle_watchlist(standardized, "epargne")
        motifs = " | ".join(watchlist["motif_alerte"].astype(str).tolist())

        self.assertIn("DAT sous minimum attendu", motifs)
        self.assertIn("Taux DAT hors référentiel", motifs)
        self.assertIn("Produit femme à confirmer", motifs)

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
