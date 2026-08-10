from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from typing import Any

import pandas as pd

from credit_app.colonne_valeur.colonne_nettoyage import (
    load_excel_column_mapping,
    normalize_column_label,
)


USER_COLUMN_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


MPESA_CLIENT_USER_COLUMN_ALIASES: dict[str, str] = {
    "client_key": "cle_client",
    "customer_id": "id_client",
    "present_customers": "present_dans_referentiel_clients",
    "date_creation_customers": "date_creation_referentiel_clients",
    "date_creation_client": "date_creation_client",
    "date_premiere_observation": "date_premiere_observation",
    "date_derniere_operation_observee": "date_derniere_operation",
    "date_derniere_operation_periode": "date_derniere_operation_periode",
    "date_premiere_operation_periode": "date_premiere_operation_periode",
    "jours_depuis_derniere_operation": "jours_depuis_derniere_operation",
    "nombre_operations": "nombre_operations",
    "nombre_operations_total": "nombre_total_operations",
    "nombre_periodes_actives": "nombre_periodes_actives",
    "actif_periode": "actif_sur_periode",
    "nouveau_client": "nouveau_client",
    "nouveau_client_actif": "nouveau_client_actif",
    "sans_mouvement_periode": "sans_mouvement_sur_periode",
    "historique_insuffisant": "historique_insuffisant",
    "inactif_observe": "inactif_observe",
    "presence_epargne": "presence_epargne",
    "presence_dat": "presence_dat",
    "presence_credit": "presence_credit",
    "presence_transaction": "presence_transaction",
    "multi_produits": "multi_produits",
    "segment_produit": "segment_produit",
    "segment_client": "segment_client",
    "nombre_comptes_compte_ouvert": "nombre_comptes_ouverts",
    "nombre_comptes_dat": "nombre_dat",
    "nombre_comptes_credit": "nombre_credits",
    "comptes_solde_positif_compte_ouvert": "nombre_comptes_ouverts_positifs",
    "comptes_solde_positif_dat": "nombre_dat_positifs",
    "comptes_solde_positif_credit": "nombre_credits_actifs",
    "solde_compte_ouvert": "solde_compte_ouvert",
    "solde_dat": "solde_dat",
    "solde_credit": "encours_credit",
    "sources_client": "sources_client",
    "source_identite": "source_identite",
    "methode_rapprochement": "methode_rapprochement",
    "statut_confiance": "statut_confiance",
    "clients_referentiel": "clients_referentiel",
    "clients_connus_solution_numerique": "clients_connus_solution_numerique",
    "clients_actifs": "clients_actifs",
    "taux_clients_actifs": "taux_clients_actifs",
    "nouveaux_clients": "nouveaux_clients",
    "nouveaux_clients_actifs": "nouveaux_clients_actifs",
    "taux_activation_nouveaux_clients": "taux_activation_nouveaux_clients",
    "clients_sans_mouvement": "clients_sans_mouvement",
    "taux_activation_pct": "taux_activation_pourcentage",
    "nombre_transactions": "nombre_transactions",
    "volume_transactions_observe": "volume_transactions_observe",
    "date_premiere_transaction": "date_premiere_transaction",
    "date_derniere_transaction": "date_derniere_transaction",
    "statut_activation": "statut_activation",
    "nouveau_compte_ouvert_periode": "nouveau_compte_ouvert_periode",
    "nouveau_dat_periode": "nouveau_dat_periode",
    "nombre_compte_ouvert": "nombre_compte_ouvert",
    "nombre_dat": "nombre_dat",
    "nouveaux_compte_ouvert_periode": "nouveaux_comptes_ouverts_periode",
    "nouveaux_dat_periode": "nouveaux_dat_periode",
    "date_premier_compte_ouvert_cree_periode": "date_premier_compte_ouvert_cree_periode",
    "date_dernier_compte_ouvert_cree_periode": "date_dernier_compte_ouvert_cree_periode",
    "date_premier_dat_cree_periode": "date_premier_dat_cree_periode",
    "date_dernier_dat_cree_periode": "date_dernier_dat_cree_periode",
    "loan_id": "numero_pret",
    "loan_product_id": "produit_credit",
    "savings_account_id": "id_compte_epargne",
    "loan_amount": "montant_credit",
    "loan_balance": "encours_credit",
    "amount_paid": "montant_deja_rembourse",
    "outstanding_principle": "capital_restant_du",
    "outstanding_principal": "capital_restant_du",
    "outstanding_setup_fees": "frais_dossier_restants",
    "outstanding_interest": "interets_restants",
    "outstanding_penalty_fees": "penalites_restantes",
    "interest_earned": "interets_gagnes",
    "status_name": "statut_credit",
    "defaulted": "defaut",
    "is_rollover": "rollover",
    "is_grace_period": "periode_grace",
    "due_date": "date_echeance",
    "last_repayment_date": "date_dernier_remboursement",
    "repayment_installments": "nombre_echeances",
    "repayment_period": "periode_remboursement",
    "repayment_period_unit": "unite_periode_remboursement",
    "nombre_prets": "nombre_prets",
    "nombre_prets_actifs": "nombre_prets_actifs",
    "nombre_emprunteurs_actifs": "nombre_emprunteurs_actifs",
    "montant_credit_initial": "montant_credit_initial",
    "pret_actif": "pret_actif",
    "jours_retard": "jours_retard",
    "jours_avant_echeance": "jours_avant_echeance",
    "tranche_echeance": "tranche_echeance",
    "par_simplifie_1j": "par_simplifie_1j",
    "par_simplifie_7j": "par_simplifie_7j",
    "par_simplifie_30j": "par_simplifie_30j",
    "tranche_encours": "tranche_encours",
    "famille_encours": "famille_encours",
    "encours_total": "encours_total",
    "part_encours_pct": "part_encours_pct",
    "prets_defaulted": "prets_en_defaut",
    "prets_rollover": "prets_rollover",
    "prets_grace_period": "prets_en_periode_grace",
    "prets_avec_penalite": "prets_avec_penalite",
    "prets_sans_dernier_remboursement": "prets_sans_dernier_remboursement",
    "prets_par_simplifie_30j": "prets_par_simplifie_30j",
    "encours_moyen_par_pret": "encours_moyen_par_pret",
    "encours_moyen_par_emprunteur": "encours_moyen_par_emprunteur",
    "famille_statut": "famille_statut",
    "valeur_statut": "valeur_statut",
    "cohorte_creation": "cohorte_creation",
    "taux_prets_defaulted_pct": "taux_prets_en_defaut_pct",
    "taux_prets_par_simplifie_30j_pct": "taux_prets_par_simplifie_30j_pct",
    "catalogue_kpi": "catalogue_kpi",
    "data_gap": "data_gap",
    "savings_id": "numero_compte",
    "product_id": "id_produit_epargne",
    "product_name": "produit_epargne",
    "product_description": "description_produit_epargne",
    "account_type": "type_compte",
    "currency_code": "devise",
    "balance": "solde",
    "status": "statut_compte",
    "date_closed": "date_cloture",
    "date_approved": "date_approbation",
    "date_activated": "date_activation",
    "maturity_date": "date_echeance",
    "interest_earned": "interet_constate",
    "is_interest_calculated": "interet_calcule",
    "last_interest_calculation_date": "date_dernier_calcul_interet",
    "next_interest_calculation_date": "date_prochain_calcul_interet",
    "voda_interest": "interet_vodacom",
    "fees_due": "frais_a_payer",
    "locked_balance": "solde_bloque",
    "date_locked": "date_blocage",
    "famille_epargne": "famille_epargne",
    "date_creation_compte": "date_creation_compte",
    "solde_positif": "solde_positif",
    "solde_nul": "solde_nul",
    "date_situation": "date_situation",
    "duree_contractuelle_jours": "duree_contractuelle_jours",
    "interet_estime": "interet_estime",
    "capital_plus_interet_estime": "capital_plus_interet_estime",
    "source_position": "source_position",
    "encours_actuel": "encours_actuel",
    "solde_moyen": "solde_moyen",
    "solde_median": "solde_median",
    "interet_constate": "interet_constate",
    "interet_vodacom": "interet_vodacom",
    "solde_bloque_technique": "solde_bloque_technique",
    "montant_depots_compte_ouvert": "montant_depots_compte_ouvert",
    "montant_depots_dat": "montant_depots_dat",
    "montant_depots_total": "montant_depots_total",
    "montant_retraits": "montant_retraits",
    "montant_remboursements_depuis_compte_ouvert": "montant_remboursements_depuis_compte_ouvert",
    "nombre_remboursements_depuis_compte_ouvert": "nombre_remboursements_depuis_compte_ouvert",
    "retours_dat": "retours_dat",
    "depot_moyen": "depot_moyen",
    "retrait_moyen": "retrait_moyen",
    "flux_net_epargne": "flux_net_epargne",
    "clients_actifs_observes": "clients_actifs_observes",
    "statut_activite_observee": "statut_activite_observee",
    "jours_inactivite_observee": "jours_inactivite_observee",
    "nouveaux_comptes": "nouveaux_comptes",
    "comptes_actives": "comptes_actives",
    "taux_activation_nouveaux_comptes_pct": "taux_activation_nouveaux_comptes_pct",
    "part_top_5_clients_pct": "part_top_5_clients_pct",
    "part_top_10_clients_pct": "part_top_10_clients_pct",
    "part_top_20_clients_pct": "part_top_20_clients_pct",
    "capital_bloque": "capital_bloque",
    "seuil_forte_epargne": "seuil_forte_epargne",
    "opportunite": "opportunite",
    "lecture": "lecture",
    "nombre_depots": "nombre_depots",
    "clients_depots": "clients_depots",
    "nombre_retraits": "nombre_retraits",
    "clients_retraits": "clients_retraits",
    "nombre_operations_epargne": "nombre_operations_epargne",
}


def normalize_user_column_name(value: Any) -> str:
    """Return a stable French-style snake_case column name for user-facing tables."""

    text = "" if value is None else str(value).strip()
    if any(token in text for token in ("Ãƒ", "Ã‚", "Ã¢â‚¬â„¢", "Ã¢â‚¬")):
        try:
            text = text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass

    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        return "colonne"
    if not re.match(r"^[a-z0-9]", text):
        return f"colonne_{text}"
    return text


def _build_user_column_lookup() -> dict[str, str]:
    lookup = {
        normalized_source: normalize_user_column_name(target)
        for normalized_source, target in load_excel_column_mapping().items()
        if normalized_source and str(target).strip()
    }
    lookup.update(
        {
            normalize_column_label(source): normalize_user_column_name(target)
            for source, target in MPESA_CLIENT_USER_COLUMN_ALIASES.items()
        }
    )
    return lookup


def resolve_user_column_mapping(columns: list[Any] | pd.Index) -> dict[Any, str]:
    """Map original columns to visible user-facing names without losing duplicates."""

    lookup = _build_user_column_lookup()
    resolved: dict[Any, str] = {}
    used: set[str] = set()

    for column in columns:
        normalized_source = normalize_column_label(column)
        candidate = lookup.get(normalized_source) or normalize_user_column_name(column)
        candidate = normalize_user_column_name(candidate)
        unique_candidate = candidate
        if unique_candidate in used:
            suffix_source = normalize_user_column_name(column)
            unique_candidate = f"{candidate}_{suffix_source}" if suffix_source != candidate else f"{candidate}_2"
            counter = 2
            while unique_candidate in used:
                counter += 1
                unique_candidate = f"{candidate}_{counter}"
        used.add(unique_candidate)
        resolved[column] = unique_candidate

    return resolved


def prepare_dataframe_with_user_columns(
    frame: pd.DataFrame,
    *,
    enabled: bool = True,
) -> tuple[pd.DataFrame, dict[Any, str]]:
    """Rename only the visible copy of a DataFrame when the sidebar option is active."""

    if not enabled or not isinstance(frame, pd.DataFrame):
        return frame, {}

    mapping = resolve_user_column_mapping(frame.columns)
    return frame.rename(columns=mapping), mapping


def prepare_dataframe_for_display(frame: pd.DataFrame, *, enabled: bool = True) -> pd.DataFrame:
    return prepare_dataframe_with_user_columns(frame, enabled=enabled)[0]


def validate_user_column_names(columns: list[Any] | pd.Index) -> list[str]:
    return [
        str(column)
        for column in columns
        if not USER_COLUMN_NAME_PATTERN.fullmatch(str(column))
    ]


def translate_column_config_for_user_columns(
    column_config: Mapping[Any, Any] | None,
    column_mapping: Mapping[Any, str],
) -> Mapping[Any, Any] | None:
    if not column_config or not column_mapping:
        return column_config
    return {
        column_mapping.get(column, column): config
        for column, config in column_config.items()
    }
