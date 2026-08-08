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
