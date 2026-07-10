from __future__ import annotations

import logging
from collections.abc import Iterable

import pandas as pd

from credit_app.colonne_valeur.colonne_nettoyage import (
    build_effective_column_mapping,
    get_reference_mapping_count,
    normalize_column_label,
    resolve_standard_column_name,
)
from credit_app.colonne_valeur.valeurs_nettoyage import (
    DEFAULT_MAPPING_FILE as VALUE_MAPPING_FILE,
    replace_specific_values_critere,
)
from credit_app.core import safe_divide
from credit_app.cycles import get_cycle_analysis_preset

logger = logging.getLogger(__name__)

NUMERIC_COLUMNS = [
    "montant_demande",
    "montant_accorde",
    "revenu_mensuel",
    "charge_mensuelle",
    "duree_credit_mois",
    "taux_interet",
    "score_credit",
    "retard_jours",
    "age",
    "montant_operation",
    "solde_initial",
    "solde_final",
    "montant_debit",
    "montant_credit",
    "solde_compte",
    "encaisse_fin_jour",
    "ecart_caisse",
    "solde_banque",
    "ecart_rapprochement",
    "salaire",
]

DATE_COLUMNS = [
    "date_demande",
    "date_decision",
    "date_operation",
    "date_saisie",
    "date_entree",
    "date_activation",
    "date_revocation",
    "date_sauvegarde",
]
STATUS_FLOW_ORDER = [
    "Reçu",
    "À compléter",
    "En analyse",
    "Approuvé",
    "Décaissé",
    "En remboursement",
    "En retard",
    "Clôturé",
    "Rejeté",
]

STATUS_DOSSIER_MAP = {
    "recu": "Reçu",
    "reçu": "Reçu",
    "en analyse": "En analyse",
    "en cours": "En analyse",
    "a completer": "À compléter",
    "à completer": "À compléter",
    "approuve": "Approuvé",
    "approuvé": "Approuvé",
    "accorde": "Approuvé",
    "rejete": "Rejeté",
    "rejeté": "Rejeté",
    "refuse": "Rejeté",
    "refusé": "Rejeté",
    "decaisse": "Décaissé",
    "décaissé": "Décaissé",
    "en remboursement": "En remboursement",
    "en retard": "En retard",
    "cloture": "Clôturé",
    "clôturé": "Clôturé",
}

STATUS_REMBOURSEMENT_MAP = {
    "a jour": "À jour",
    "à jour": "À jour",
    "normal": "À jour",
    "non decaisse": "Non décaissé",
    "non décaissé": "Non décaissé",
    "non decaissé": "Non décaissé",
    "en retard": "En retard",
    "impaye": "En retard",
    "impayé": "En retard",
    "solde": "Soldé",
    "soldé": "Soldé",
    "cloture": "Soldé",
    "clôturé": "Soldé",
}

SEX_VALUE_MAP = {
    "m": "Masculin",
    "masculin": "Masculin",
    "male": "Masculin",
    "homme": "Masculin",
    "h": "Masculin",
    "f": "Féminin",
    "feminin": "Féminin",
    "female": "Féminin",
    "femme": "Féminin",
}

RISK_LEVEL_MAP = {
    "faible": "Faible",
    "moyen": "Moyen",
    "eleve": "Élevé",
    "non renseigne": "Non renseigné",
}

CYCLE_DATE_PRIORITY = {
    "credit": ["date_demande", "date_decision"],
    "likelemba": ["date_demande", "date_decision"],
    "epargne": ["date_operation", "date_demande"],
    "operations_depot_retrait": ["date_operation"],
    "crm_clients": ["date_operation"],
    "caisse": ["date_operation"],
    "tresorerie": ["date_operation"],
    "comptable": ["date_operation"],
    "money_provider": ["date_operation"],
    "rh_admin": ["date_entree", "date_operation"],
    "si": ["date_activation", "date_revocation"],
    "continuite": ["date_sauvegarde"],
}

VALUE_CLEANING_CRITERIA = {
    "sexe": "Sexe",
    "activite_economique": "Profession",
    "zone_geographique": "Province",
    "unite_age": "Unite_age",
    "statut_test_reprise": "Boolean",
    "incident_majeur": "Boolean",
}

EPARGNE_DAT_MINIMUM_USD_PHYSIQUE = 500.0
EPARGNE_DAT_MINIMUM_USD_MORALE = 5000.0

CREDIT_PRODUCT_RULES: dict[str, dict[str, float | bool | None]] = {
    "lisungi": {"min_amount": 100.0, "max_amount": 80000.0, "min_duration": 2.0, "max_duration": 12.0, "min_rate": 2.5, "max_rate": 4.0, "garantie_required": True},
    "salaire": {"min_amount": 100.0, "max_amount": 10000.0, "min_duration": 2.0, "max_duration": 24.0, "min_rate": 2.5, "max_rate": 2.5, "garantie_required": True},
    "personnel": {"min_amount": 100.0, "max_amount": 15000.0, "min_duration": 2.0, "max_duration": 24.0, "min_rate": 2.5, "max_rate": 2.5, "garantie_required": True},
    "avance_salaire": {"min_amount": 0.0, "max_amount": None, "min_duration": 1.0, "max_duration": 1.0, "min_rate": 5.0, "max_rate": 5.0, "garantie_required": True},
    "dare_dare": {"min_amount": 100.0, "max_amount": 10000.0, "min_duration": None, "max_duration": None, "min_rate": 2.0, "max_rate": 2.0, "garantie_required": True},
    "pepsi": {"min_amount": 100.0, "max_amount": 10000.0, "min_duration": None, "max_duration": None, "min_rate": 2.0, "max_rate": 2.0, "garantie_required": True},
    "auto": {"min_amount": 5000.0, "max_amount": 20000.0, "min_duration": 12.0, "max_duration": 24.0, "min_rate": 2.5, "max_rate": 2.5, "garantie_required": True},
    "collectif": {"min_amount": 100.0, "max_amount": 10000.0, "min_duration": 2.0, "max_duration": 12.0, "min_rate": 2.5, "max_rate": 4.0, "garantie_required": True},
    "likelemba": {"min_amount": 100.0, "max_amount": 10000.0, "min_duration": None, "max_duration": None, "min_rate": 2.5, "max_rate": 2.5, "garantie_required": True},
}


def normalize_text(value: object) -> str:
    return normalize_column_label(value)


def _classify_credit_product(value: object) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    if "avance" in text and "salaire" in text:
        return "avance_salaire"
    if "likelemba" in text:
        return "likelemba"
    if "lisungi" in text:
        return "lisungi"
    if "dare" in text:
        return "dare_dare"
    if "pepsi" in text:
        return "pepsi"
    if "auto" in text:
        return "auto"
    if "collectif" in text:
        return "collectif"
    if "personnel" in text:
        return "personnel"
    if "salaire" in text:
        return "salaire"
    return None


def _classify_epargne_product(value: object) -> str | None:
    text = normalize_text(value)
    if not text:
        return None
    if "dat" in text or "depot a terme" in text or "dépôt à terme" in text:
        return "dat"
    if "maman" in text:
        return "femme"
    if "elenge" in text or "jeunesse" in text:
        return "jeunesse"
    if "likelemba" in text or "tontine" in text:
        return "likelemba"
    if "courant" in text:
        return "courant"
    return "autre"


def _is_corporate_client(value: object) -> bool:
    text = normalize_text(value)
    corporate_markers = {"personne morale", "pm", "societe", "société", "pme", "institution", "entreprise"}
    return any(marker in text for marker in corporate_markers)


def _apply_reference_value_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    active_criteria = {
        column_name: variable_name
        for column_name, variable_name in VALUE_CLEANING_CRITERIA.items()
        if column_name in df.columns
    }
    if not active_criteria:
        return df

    try:
        return replace_specific_values_critere(
            df,
            critere=active_criteria,
            mapping_file=VALUE_MAPPING_FILE,
            regex_mode=True,
            clean_before=True,
            strip_lower=True,
        )
    except FileNotFoundError:
        logger.warning("Fichier de nettoyage des valeurs introuvable : %s", VALUE_MAPPING_FILE)
    except Exception:
        logger.exception("Le nettoyage des valeurs depuis %s a échoué.", VALUE_MAPPING_FILE)
    return df


def standardize_column_name(column_name: str) -> str:
    return resolve_standard_column_name(column_name, REFERENCE_COLUMN_LOOKUP)


REFERENCE_COLUMN_LOOKUP = build_effective_column_mapping()


def get_reference_column_count() -> int:
    return get_reference_mapping_count()


def _coerce_numeric(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        series = (
            series.astype(str)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
    return pd.to_numeric(series, errors="coerce")


def _numeric_series_or_zero(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(0, index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").fillna(0)


def _coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    if not df.columns.duplicated().any():
        return df

    coalesced_columns: dict[str, pd.Series] = {}
    ordered_columns: list[str] = []
    for column in df.columns:
        if column in coalesced_columns:
            continue
        same_name = df.loc[:, df.columns == column]
        ordered_columns.append(column)
        if isinstance(same_name, pd.Series) or same_name.shape[1] == 1:
            coalesced_columns[column] = same_name.iloc[:, 0] if isinstance(same_name, pd.DataFrame) else same_name
        else:
            coalesced_columns[column] = same_name.apply(
                lambda row: row.dropna().iloc[0] if row.notna().any() else pd.NA,
                axis=1,
            )

    return pd.DataFrame(coalesced_columns, index=df.index)[ordered_columns]


def _normalize_series_values(series: pd.Series, mapping: dict[str, str]) -> pd.Series:
    return series.apply(
        lambda value: mapping.get(normalize_text(value), str(value).strip()) if pd.notna(value) else value
    )


def derive_risk_level(row: pd.Series) -> str:
    explicit_level = row.get("niveau_risque")
    if pd.notna(explicit_level) and str(explicit_level).strip():
        normalized_level = normalize_text(explicit_level)
        return RISK_LEVEL_MAP.get(normalized_level, str(explicit_level).strip().title())

    score = row.get("score_credit")
    if pd.notna(score):
        if score >= 80:
            return "Faible"
        if score >= 50:
            return "Moyen"
        return "Élevé"

    debt_ratio = row.get("taux_endettement")
    if pd.notna(debt_ratio):
        if debt_ratio <= 0.30:
            return "Faible"
        if debt_ratio <= 0.50:
            return "Moyen"
        return "Élevé"

    delay = row.get("retard_jours")
    if pd.notna(delay):
        if delay <= 0:
            return "Faible"
        if delay <= 30:
            return "Moyen"
        return "Élevé"

    return "Non renseigné"


def build_standardized_dataframe(
    df: pd.DataFrame,
    *,
    standardize_columns: bool = True,
) -> tuple[pd.DataFrame, dict[str, str]]:
    standardized = df.copy()
    mapping = (
        {column: standardize_column_name(column) for column in standardized.columns}
        if standardize_columns
        else {column: column for column in standardized.columns}
    )
    if standardize_columns:
        standardized = standardized.rename(columns=mapping)
    standardized = _coalesce_duplicate_columns(standardized)
    standardized = _apply_reference_value_cleaning(standardized)

    if standardize_columns and "client_id" not in standardized.columns and "code_client" in standardized.columns:
        standardized["client_id"] = standardized["code_client"]
    if standardize_columns and "devise" not in standardized.columns and "code_devise" in standardized.columns:
        standardized["devise"] = standardized["code_devise"]

    for column in NUMERIC_COLUMNS:
        if column in standardized.columns:
            standardized[column] = _coerce_numeric(standardized[column])

    for column in DATE_COLUMNS:
        if column in standardized.columns:
            standardized[column] = pd.to_datetime(standardized[column], errors="coerce")

    if "statut_dossier" in standardized.columns:
        standardized["statut_dossier"] = _normalize_series_values(
            standardized["statut_dossier"], STATUS_DOSSIER_MAP
        )

    if "statut_remboursement" in standardized.columns:
        standardized["statut_remboursement"] = _normalize_series_values(
            standardized["statut_remboursement"], STATUS_REMBOURSEMENT_MAP
        )

    if "sexe" in standardized.columns:
        standardized["sexe"] = _normalize_series_values(standardized["sexe"], SEX_VALUE_MAP)

    if "telephone" in standardized.columns and "Portable" in standardized.columns:
        portable_series = standardized["Portable"].astype("string").str.strip()
        telephone_series = standardized["telephone"].astype("string").str.strip()
        standardized["telephone"] = telephone_series.mask(
            telephone_series.fillna("").eq(""),
            portable_series,
        )

    if "nom_client" in standardized.columns:
        nom_series = standardized["nom_client"].astype("string").str.strip()
        if "Client Name" in standardized.columns:
            client_name_series = standardized["Client Name"].astype("string").str.strip()
            nom_series = nom_series.mask(nom_series.fillna("").eq(""), client_name_series)
            nom_series = client_name_series.mask(client_name_series.fillna("").ne(""), client_name_series).fillna(nom_series)
        elif "Prénom" in standardized.columns:
            prenom_series = standardized["Prénom"].astype("string").str.strip().fillna("")
            full_name_series = (prenom_series + " " + nom_series.fillna("")).str.strip()
            nom_series = nom_series.mask(nom_series.fillna("").eq(""), full_name_series)
        standardized["nom_client"] = nom_series.replace("", pd.NA)

    if {"revenu_mensuel", "charge_mensuelle"}.issubset(standardized.columns):
        standardized["capacite_remboursement"] = (
            standardized["revenu_mensuel"] - standardized["charge_mensuelle"]
        )

    if {"charge_mensuelle", "revenu_mensuel"}.issubset(standardized.columns):
        standardized["taux_endettement"] = standardized.apply(
            lambda row: safe_divide(row["charge_mensuelle"], row["revenu_mensuel"]),
            axis=1,
        )

    if {"montant_accorde", "duree_credit_mois"}.issubset(standardized.columns):
        standardized["mensualite_estimee"] = standardized.apply(
            lambda row: safe_divide(row["montant_accorde"], row["duree_credit_mois"]),
            axis=1,
        )

    standardized["niveau_risque_calcule"] = standardized.apply(derive_risk_level, axis=1)

    if "date_demande" in standardized.columns:
        standardized["mois_demande"] = standardized["date_demande"].dt.to_period("M").astype("string")

    return standardized, mapping


def build_mapping_frame(mapping: dict[str, str]) -> pd.DataFrame:
    rows = [
        {"colonne_source": source, "colonne_standard": target}
        for source, target in mapping.items()
    ]
    return pd.DataFrame(rows).sort_values(by=["colonne_standard", "colonne_source"]).reset_index(drop=True)


def build_missing_values_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["colonne", "valeurs_manquantes", "taux_manquant"])
    rows = []
    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        rows.append(
            {
                "colonne": column,
                "valeurs_manquantes": missing_count,
                "taux_manquant": missing_count / len(df),
            }
        )
    return pd.DataFrame(rows).sort_values(
        by=["valeurs_manquantes", "colonne"], ascending=[False, True]
    ).reset_index(drop=True)


def build_quality_checks(df: pd.DataFrame) -> pd.DataFrame:
    checks: list[dict[str, object]] = []

    def add_check(label: str, mask: pd.Series) -> None:
        count = int(mask.fillna(False).sum()) if not df.empty else 0
        checks.append(
            {
                "controle": label,
                "nombre_lignes": count,
                "taux_lignes": (count / len(df)) if len(df) else 0.0,
            }
        )

    if "client_id" in df.columns:
        add_check("Clients sans identifiant", df["client_id"].isna() | (df["client_id"].astype(str).str.strip() == ""))
    if "dossier_id" in df.columns:
        duplicate_mask = df["dossier_id"].duplicated(keep=False) & df["dossier_id"].notna()
        add_check("Dossiers dupliqués", duplicate_mask)
        add_check(
            "Dossiers sans identifiant",
            df["dossier_id"].isna() | (df["dossier_id"].astype(str).str.strip() == ""),
        )
    if "statut_dossier" in df.columns:
        add_check(
            "Dossiers sans statut",
            df["statut_dossier"].isna() | (df["statut_dossier"].astype(str).str.strip() == ""),
        )
    if "montant_demande" in df.columns:
        add_check("Montants demandés négatifs", df["montant_demande"] < 0)
    if "montant_accorde" in df.columns:
        add_check("Montants accordés négatifs", df["montant_accorde"] < 0)
    if {"montant_demande", "montant_accorde"}.issubset(df.columns):
        add_check("Montants accordés supérieurs au demandé", df["montant_accorde"] > df["montant_demande"])
    if {"revenu_mensuel", "charge_mensuelle"}.issubset(df.columns):
        add_check(
            "Données financières manquantes",
            df["revenu_mensuel"].isna() | df["charge_mensuelle"].isna(),
        )
    if "retard_jours" in df.columns:
        add_check("Retards négatifs", df["retard_jours"] < 0)
    if "capacite_remboursement" in df.columns:
        add_check("Capacité de remboursement négative", df["capacite_remboursement"] < 0)

    return pd.DataFrame(checks)


def build_monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    if "date_demande" not in df.columns:
        return pd.DataFrame(columns=["mois_demande", "nombre_dossiers", "montant_demande_total"])

    base = df.dropna(subset=["date_demande"]).copy()
    if base.empty:
        return pd.DataFrame(columns=["mois_demande", "nombre_dossiers", "montant_demande_total"])

    base["mois_demande"] = base["date_demande"].dt.to_period("M").astype(str)
    return (
        base.groupby("mois_demande", dropna=False)
        .agg(
            nombre_dossiers=("mois_demande", "size"),
            montant_demande_total=("montant_demande", "sum"),
        )
        .reset_index()
        .sort_values("mois_demande")
    )


def _first_existing_column(
    df: pd.DataFrame,
    candidates: Iterable[str],
) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def get_first_existing_column(
    df: pd.DataFrame,
    candidates: Iterable[str],
) -> str | None:
    return _first_existing_column(df, candidates)


def get_cycle_primary_date_column(df: pd.DataFrame, cycle_key: str | None = None) -> str | None:
    cycle_candidates = CYCLE_DATE_PRIORITY.get(str(cycle_key or ""), [])
    generic_candidates = [
        "date_demande",
        "date_operation",
        "date_decision",
        "date_entree",
        "date_activation",
        "date_revocation",
        "date_sauvegarde",
    ]
    return _first_existing_column(df, [*cycle_candidates, *generic_candidates])


def build_period_series(
    df: pd.DataFrame,
    date_column: str,
    amount_column: str | None = None,
) -> pd.DataFrame:
    empty = pd.DataFrame(columns=["periode", "nombre_lignes", "montant_total"])
    empty.attrs["date_column"] = date_column
    empty.attrs["amount_column"] = amount_column

    if date_column not in df.columns:
        return empty

    base = df.copy()
    base[date_column] = pd.to_datetime(base[date_column], errors="coerce")
    base = base.dropna(subset=[date_column])
    if base.empty:
        return empty

    base["periode"] = base[date_column].dt.to_period("M").astype(str)
    if amount_column and amount_column in base.columns:
        grouped = (
            base.groupby("periode", dropna=False)
            .agg(
                nombre_lignes=("periode", "size"),
                montant_total=(amount_column, "sum"),
            )
            .reset_index()
            .sort_values("periode")
        )
    else:
        grouped = (
            base.groupby("periode", dropna=False)
            .agg(nombre_lignes=("periode", "size"))
            .reset_index()
            .sort_values("periode")
        )
        grouped["montant_total"] = pd.NA

    grouped.attrs["date_column"] = date_column
    grouped.attrs["amount_column"] = amount_column if amount_column in base.columns else None
    return grouped


def build_cycle_period_series(df: pd.DataFrame, cycle_key: str | None = None) -> pd.DataFrame:
    date_column = get_cycle_primary_date_column(df, cycle_key)
    if not date_column:
        empty = pd.DataFrame(columns=["periode", "nombre_lignes", "montant_total"])
        empty.attrs["date_column"] = None
        empty.attrs["amount_column"] = None
        return empty

    amount_candidates = [
        "montant_demande",
        "montant_operation",
        "montant_accorde",
        "montant_debit",
        "montant_credit",
        "salaire",
    ]
    amount_column = _first_existing_column(df, amount_candidates)
    return build_period_series(df, date_column=date_column, amount_column=amount_column)


def filter_dataframe(
    df: pd.DataFrame,
    statuses: Iterable[str] | None = None,
    agencies: Iterable[str] | None = None,
    products: Iterable[str] | None = None,
    start_date: object | None = None,
    end_date: object | None = None,
    date_column: str | None = "date_demande",
    column_filters: dict[str, Iterable[str] | None] | None = None,
) -> pd.DataFrame:
    filtered = df.copy()

    effective_filters: dict[str, Iterable[str] | None] = {}
    if column_filters:
        effective_filters.update(column_filters)
    if statuses:
        effective_filters["statut_dossier"] = statuses
    if agencies:
        effective_filters["agence"] = agencies
    if products:
        effective_filters["type_produit"] = products

    for column_name, selected_values in effective_filters.items():
        if selected_values and column_name in filtered.columns:
            filtered = filtered[filtered[column_name].isin(selected_values)]

    if date_column and date_column in filtered.columns and start_date is not None:
        filtered = filtered[filtered[date_column].dt.date >= start_date]

    if date_column and date_column in filtered.columns and end_date is not None:
        filtered = filtered[filtered[date_column].dt.date <= end_date]

    return filtered.reset_index(drop=True)


def build_summary_metrics(df: pd.DataFrame) -> dict[str, object]:
    approved_statuses = {"Approuvé", "Décaissé", "En remboursement", "En retard", "Clôturé"}

    approved_count = int(
        df["statut_dossier"].isin(approved_statuses).sum()
    ) if "statut_dossier" in df.columns else 0
    delayed_count = 0

    if "statut_remboursement" in df.columns:
        delayed_count = int(df["statut_remboursement"].eq("En retard").sum())
    elif "retard_jours" in df.columns:
        delayed_count = int((df["retard_jours"] > 0).sum())

    return {
        "nombre_dossiers": len(df),
        "nombre_clients": int(df["client_id"].nunique()) if "client_id" in df.columns else None,
        "montant_demande_total": float(df["montant_demande"].sum()) if "montant_demande" in df.columns else None,
        "montant_accorde_total": float(df["montant_accorde"].sum()) if "montant_accorde" in df.columns else None,
        "taux_approbation": safe_divide(approved_count, len(df)),
        "taux_retard": safe_divide(delayed_count, len(df)),
        "retard_moyen_jours": (
            float(df["retard_jours"].dropna().mean())
            if "retard_jours" in df.columns and not df["retard_jours"].dropna().empty
            else None
        ),
        "taux_endettement_moyen": (
            float(df["taux_endettement"].dropna().mean())
            if "taux_endettement" in df.columns and not df["taux_endettement"].dropna().empty
            else None
        ),
    }


def build_grouped_amounts(
    df: pd.DataFrame,
    group_column: str,
    amount_column: str = "montant_demande",
    top_n: int = 10,
) -> pd.DataFrame:
    if group_column not in df.columns or amount_column not in df.columns:
        return pd.DataFrame(columns=[group_column, amount_column])

    base = df.dropna(subset=[group_column]).copy()
    if base.empty:
        return pd.DataFrame(columns=[group_column, amount_column])

    grouped = (
        base.groupby(group_column, dropna=False)[amount_column]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
    )
    return grouped


def build_risk_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if "niveau_risque_calcule" not in df.columns:
        return pd.DataFrame(columns=["niveau_risque_calcule", "nombre_dossiers"])
    return (
        df.groupby("niveau_risque_calcule", dropna=False)
        .size()
        .reset_index(name="nombre_dossiers")
        .sort_values("nombre_dossiers", ascending=False)
    )


def build_status_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if "statut_dossier" not in df.columns:
        return pd.DataFrame(columns=["statut_dossier", "nombre_dossiers"])
    return (
        df.groupby("statut_dossier", dropna=False)
        .size()
        .reset_index(name="nombre_dossiers")
        .sort_values("nombre_dossiers", ascending=False)
    )


def build_frequency_table(df: pd.DataFrame, column: str, top_n: int | None = None) -> pd.DataFrame:
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "nombre_lignes", "part_lignes"])

    base = (
        df[column]
        .fillna("Non renseigné")
        .astype("string")
        .str.strip()
        .replace("", "Non renseigné")
        .value_counts(dropna=False)
        .reset_index()
    )
    base.columns = [column, "nombre_lignes"]
    total = max(len(df), 1)
    base["part_lignes"] = base["nombre_lignes"] / total
    if top_n is not None:
        base = base.head(int(top_n))
    return base


def build_sex_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if "sexe" not in df.columns:
        return pd.DataFrame(columns=["sexe", "nombre_lignes", "part_lignes"])

    distribution = build_frequency_table(df, "sexe")
    if distribution.empty:
        return distribution

    distribution["sexe"] = distribution["sexe"].replace({"Non renseigne": "Inconnu", "Non renseigné": "Inconnu"})
    order_map = {"Masculin": 0, "Féminin": 1, "Inconnu": 2}
    distribution["_ordre"] = distribution["sexe"].map(order_map).fillna(99)
    return (
        distribution.sort_values(["_ordre", "nombre_lignes"], ascending=[True, False])
        .drop(columns="_ordre")
        .reset_index(drop=True)
    )


def build_age_bucket_table(df: pd.DataFrame) -> pd.DataFrame:
    if "age" not in df.columns:
        return pd.DataFrame(columns=["tranche_age", "nombre_lignes", "part_lignes"])

    ages = pd.to_numeric(df["age"], errors="coerce")
    labels = pd.Series("Non renseigné", index=df.index, dtype="string")
    labels = labels.mask((ages >= 0) & (ages <= 17), "0-17")
    labels = labels.mask((ages >= 18) & (ages <= 24), "18-24")
    labels = labels.mask((ages >= 25) & (ages <= 34), "25-34")
    labels = labels.mask((ages >= 35) & (ages <= 44), "35-44")
    labels = labels.mask((ages >= 45) & (ages <= 54), "45-54")
    labels = labels.mask((ages >= 55) & (ages <= 64), "55-64")
    labels = labels.mask(ages >= 65, "65+")

    distribution = build_frequency_table(pd.DataFrame({"tranche_age": labels}), "tranche_age")
    if distribution.empty:
        return distribution

    order_map = {
        "0-17": 0,
        "18-24": 1,
        "25-34": 2,
        "35-44": 3,
        "45-54": 4,
        "55-64": 5,
        "65+": 6,
        "Non renseigné": 7,
    }
    distribution["_ordre"] = distribution["tranche_age"].map(order_map).fillna(99)
    return (
        distribution.sort_values(["_ordre", "nombre_lignes"], ascending=[True, False])
        .drop(columns="_ordre")
        .reset_index(drop=True)
    )


def build_age_sex_pyramid_table(df: pd.DataFrame) -> pd.DataFrame:
    if "age" not in df.columns or "sexe" not in df.columns:
        return pd.DataFrame(columns=["tranche_age", "Masculin", "Féminin"])

    age_distribution = build_age_bucket_table(df)
    if age_distribution.empty:
        return pd.DataFrame(columns=["tranche_age", "Masculin", "Féminin"])

    age_order = age_distribution["tranche_age"].tolist()
    base = df.copy()
    ages = pd.to_numeric(base["age"], errors="coerce")
    labels = pd.Series("Non renseigné", index=base.index, dtype="string")
    labels = labels.mask((ages >= 0) & (ages <= 17), "0-17")
    labels = labels.mask((ages >= 18) & (ages <= 24), "18-24")
    labels = labels.mask((ages >= 25) & (ages <= 34), "25-34")
    labels = labels.mask((ages >= 35) & (ages <= 44), "35-44")
    labels = labels.mask((ages >= 45) & (ages <= 54), "45-54")
    labels = labels.mask((ages >= 55) & (ages <= 64), "55-64")
    labels = labels.mask(ages >= 65, "65+")
    base["tranche_age"] = pd.Categorical(labels, categories=age_order, ordered=True)

    base["sexe_pyramide"] = (
        base["sexe"]
        .fillna("Inconnu")
        .astype("string")
        .replace({"Non renseigne": "Inconnu"})
        .where(lambda s: s.isin(["Masculin", "Féminin"]), "Inconnu")
    )

    grouped = (
        base.groupby(["tranche_age", "sexe_pyramide"], observed=False)
        .size()
        .reset_index(name="nombre_lignes")
    )
    if grouped.empty:
        return pd.DataFrame(columns=["tranche_age", "Masculin", "Féminin"])

    pivot = (
        grouped.pivot(index="tranche_age", columns="sexe_pyramide", values="nombre_lignes")
        .fillna(0)
        .reset_index()
    )
    for column in ["Masculin", "Féminin"]:
        if column not in pivot.columns:
            pivot[column] = 0
    return pivot[["tranche_age", "Masculin", "Féminin"]]


def build_epargne_dormancy_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["classe_inactivite", "nombre_lignes", "part_lignes"]
    if "date_operation" not in df.columns:
        return pd.DataFrame(columns=columns)

    dates = pd.to_datetime(df["date_operation"], errors="coerce")
    valid_dates = dates.dropna()
    if valid_dates.empty:
        return pd.DataFrame(columns=columns)

    reference_date = valid_dates.max()
    inactivity_days = (reference_date - dates).dt.days
    classes = pd.Series("Non documenté", index=df.index, dtype="string")
    non_null_mask = inactivity_days.notna()
    classes.loc[non_null_mask] = pd.cut(
        inactivity_days.loc[non_null_mask],
        bins=[-1, 30, 90, 180, 365, float("inf")],
        labels=["<= 30 j", "31-90 j", "91-180 j", "181-365 j", "> 365 j"],
        include_lowest=True,
    ).astype("string")

    summary = (
        classes.fillna("Non documenté")
        .value_counts(dropna=False)
        .rename_axis("classe_inactivite")
        .reset_index(name="nombre_lignes")
    )
    summary["part_lignes"] = summary["nombre_lignes"] / max(len(df), 1)
    summary["_ordre"] = summary["classe_inactivite"].map(
        {
            "<= 30 j": 0,
            "31-90 j": 1,
            "91-180 j": 2,
            "181-365 j": 3,
            "> 365 j": 4,
            "Non documenté": 5,
        }
    ).fillna(99)
    return summary.sort_values("_ordre").drop(columns="_ordre").reset_index(drop=True)


def build_epargne_multi_account_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["classe_comptes", "nombre_clients", "part_clients"]
    if not {"client_id", "compte_id"}.issubset(df.columns):
        return pd.DataFrame(columns=columns)

    account_counts = (
        df.dropna(subset=["client_id", "compte_id"])
        .groupby("client_id")["compte_id"]
        .nunique()
    )
    if account_counts.empty:
        return pd.DataFrame(columns=columns)

    classes = account_counts.apply(
        lambda value: (
            "1 compte"
            if value <= 1
            else "2 comptes"
            if value == 2
            else "3-4 comptes"
            if value <= 4
            else "5+ comptes"
        )
    )
    summary = (
        classes.value_counts()
        .rename_axis("classe_comptes")
        .reset_index(name="nombre_clients")
    )
    summary["part_clients"] = summary["nombre_clients"] / max(len(account_counts), 1)
    summary["_ordre"] = summary["classe_comptes"].map(
        {"1 compte": 0, "2 comptes": 1, "3-4 comptes": 2, "5+ comptes": 3}
    ).fillna(99)
    return summary.sort_values("_ordre").drop(columns="_ordre").reset_index(drop=True)


def build_epargne_multi_account_clients(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    columns = ["client_id", "nom_client", "nombre_comptes", "solde_total"]
    if not {"client_id", "compte_id"}.issubset(df.columns):
        return pd.DataFrame(columns=columns)

    working_df = df.dropna(subset=["client_id", "compte_id"]).copy()
    if working_df.empty:
        return pd.DataFrame(columns=columns)

    aggregations: dict[str, tuple[str, object]] = {
        "nombre_comptes": ("compte_id", "nunique"),
        "solde_total": (
            "solde_compte",
            lambda series: pd.to_numeric(series, errors="coerce").fillna(0).sum(),
        ),
    }
    if "nom_client" in working_df.columns:
        aggregations["nom_client"] = (
            "nom_client",
            lambda series: (
                series.dropna().astype("string").str.strip().loc[lambda values: values.ne("")].iloc[0]
                if not series.dropna().astype("string").str.strip().loc[lambda values: values.ne("")].empty
                else pd.NA
            ),
        )

    grouped = (
        working_df.groupby("client_id", dropna=False)
        .agg(**aggregations)
        .reset_index()
        .sort_values(["nombre_comptes", "solde_total"], ascending=[False, False])
    )
    if "nom_client" not in grouped.columns:
        grouped["nom_client"] = pd.NA
    grouped = grouped[columns]
    return grouped.head(top_n).reset_index(drop=True)


def build_epargne_product_concentration_table(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    columns = ["type_produit", "nombre_comptes", "solde_total", "part_solde"]
    if "type_produit" not in df.columns or "solde_compte" not in df.columns:
        return pd.DataFrame(columns=columns)

    working_df = df.dropna(subset=["type_produit"]).copy()
    if working_df.empty:
        return pd.DataFrame(columns=columns)

    grouped = (
        working_df.assign(solde_compte=pd.to_numeric(working_df["solde_compte"], errors="coerce").fillna(0))
        .groupby("type_produit", dropna=False)
        .agg(
            nombre_comptes=("type_produit", "size"),
            solde_total=("solde_compte", "sum"),
        )
        .reset_index()
        .sort_values("solde_total", ascending=False)
    )
    total_balance = grouped["solde_total"].sum()
    grouped["part_solde"] = grouped["solde_total"].apply(
        lambda value: safe_divide(value, total_balance) if total_balance else 0.0
    )
    return grouped.head(top_n).reset_index(drop=True)


def build_epargne_agent_portfolio_table(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    columns = ["agent_credit", "nombre_comptes", "nombre_clients", "solde_total", "solde_moyen"]
    if "agent_credit" not in df.columns:
        return pd.DataFrame(columns=columns)

    working_df = df.dropna(subset=["agent_credit"]).copy()
    if working_df.empty:
        return pd.DataFrame(columns=columns)

    grouped = (
        working_df.assign(solde_compte=_numeric_series_or_zero(working_df, "solde_compte"))
        .groupby("agent_credit", dropna=False)
        .agg(
            nombre_comptes=("agent_credit", "size"),
            nombre_clients=("client_id", "nunique") if "client_id" in working_df.columns else ("agent_credit", "size"),
            solde_total=("solde_compte", "sum"),
        )
        .reset_index()
        .sort_values(["solde_total", "nombre_comptes"], ascending=[False, False])
    )
    grouped["solde_moyen"] = grouped.apply(
        lambda row: safe_divide(row["solde_total"], row["nombre_comptes"]),
        axis=1,
    )
    return grouped.head(top_n).reset_index(drop=True)


def build_epargne_phone_quality_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["qualite_telephone", "nombre_lignes", "part_lignes"]
    if "telephone" not in df.columns:
        return pd.DataFrame(columns=columns)

    phone_series = df["telephone"].astype("string")
    digits = phone_series.fillna("").str.replace(r"\D", "", regex=True)
    quality = pd.Series("Autre format", index=df.index, dtype="string")
    quality.loc[phone_series.isna() | phone_series.fillna("").str.strip().eq("")] = "Manquant"
    quality.loc[digits.str.match(r"^243\d{9}$", na=False)] = "Format international"
    quality.loc[digits.str.match(r"^0\d{9}$", na=False)] = "Format local"

    summary = (
        quality.value_counts(dropna=False)
        .rename_axis("qualite_telephone")
        .reset_index(name="nombre_lignes")
    )
    summary["part_lignes"] = summary["nombre_lignes"] / max(len(df), 1)
    summary["_ordre"] = summary["qualite_telephone"].map(
        {
            "Format international": 0,
            "Format local": 1,
            "Autre format": 2,
            "Manquant": 3,
        }
    ).fillna(99)
    return summary.sort_values("_ordre").drop(columns="_ordre").reset_index(drop=True)


def build_epargne_kyc_completeness_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["classe_completude", "nombre_lignes", "part_lignes"]
    tracked_fields = [
        column_name
        for column_name in ["telephone", "zone_geographique", "sexe", "categorie", "date_operation"]
        if column_name in df.columns
    ]
    if not tracked_fields:
        return pd.DataFrame(columns=columns)

    missing_counts = df[tracked_fields].isna().sum(axis=1)
    classes = missing_counts.apply(
        lambda value: (
            "0 champ manquant"
            if value == 0
            else "1 champ manquant"
            if value == 1
            else "2 champs manquants"
            if value == 2
            else "3+ champs manquants"
        )
    )
    summary = (
        classes.value_counts()
        .rename_axis("classe_completude")
        .reset_index(name="nombre_lignes")
    )
    summary["part_lignes"] = summary["nombre_lignes"] / max(len(df), 1)
    summary["_ordre"] = summary["classe_completude"].map(
        {
            "0 champ manquant": 0,
            "1 champ manquant": 1,
            "2 champs manquants": 2,
            "3+ champs manquants": 3,
        }
    ).fillna(99)
    return summary.sort_values("_ordre").drop(columns="_ordre").reset_index(drop=True)


def build_provenance_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = ["Provenance", "nombre_lignes", "nombre_clients", "nombre_comptes", "solde_total"]
    if "Provenance" not in df.columns:
        return pd.DataFrame(columns=columns)

    working_df = df.dropna(subset=["Provenance"]).copy()
    if working_df.empty:
        return pd.DataFrame(columns=columns)

    grouped = (
        working_df.assign(solde_compte=_numeric_series_or_zero(working_df, "solde_compte"))
        .groupby("Provenance", dropna=False)
        .agg(
            nombre_lignes=("Provenance", "size"),
            nombre_clients=("client_id", "nunique") if "client_id" in working_df.columns else ("Provenance", "size"),
            nombre_comptes=("compte_id", "nunique") if "compte_id" in working_df.columns else ("Provenance", "size"),
            solde_total=("solde_compte", "sum"),
        )
        .reset_index()
        .sort_values("nombre_lignes", ascending=False)
    )
    return grouped.reset_index(drop=True)


def build_group_summary_table(
    df: pd.DataFrame,
    group_column: str,
    top_n: int = 8,
) -> pd.DataFrame:
    if group_column not in df.columns or df.empty:
        return pd.DataFrame(
            columns=[
                group_column,
                "dossiers",
                "montant_demande_total",
                "montant_accorde_total",
                "taux_retard",
                "risque_eleve",
            ]
        )

    base = df.dropna(subset=[group_column]).copy()
    if base.empty:
        return pd.DataFrame(
            columns=[
                group_column,
                "dossiers",
                "montant_demande_total",
                "montant_accorde_total",
                "taux_retard",
                "risque_eleve",
            ]
        )

    delayed_mask = (
        base["statut_remboursement"].eq("En retard")
        if "statut_remboursement" in base.columns
        else base.get("retard_jours", pd.Series(0, index=base.index)).fillna(0) > 0
    )
    elevated_risk_mask = (
        base["niveau_risque_calcule"].eq("Élevé")
        if "niveau_risque_calcule" in base.columns
        else pd.Series(False, index=base.index)
    )

    summary = (
        base.assign(
            _delayed=delayed_mask.astype(int),
            _elevated_risk=elevated_risk_mask.astype(int),
        )
        .groupby(group_column, dropna=False)
        .agg(
            dossiers=(group_column, "size"),
            montant_demande_total=("montant_demande", "sum"),
            montant_accorde_total=("montant_accorde", "sum"),
            taux_retard=("_delayed", "mean"),
            risque_eleve=("_elevated_risk", "sum"),
        )
        .reset_index()
        .sort_values(["montant_demande_total", "dossiers"], ascending=[False, False])
        .head(top_n)
    )
    return summary


def _build_amount_reference_frame(
    df: pd.DataFrame,
    amount_columns: Iterable[str] | None = None,
    derived_name: str = "_montant_reference",
) -> tuple[pd.DataFrame, str | None]:
    present_columns = [column for column in (amount_columns or []) if column in df.columns]
    if not present_columns:
        return df, None
    if len(present_columns) == 1:
        return df, present_columns[0]

    amount_frame = df.copy()
    amount_frame[derived_name] = (
        amount_frame[present_columns]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .sum(axis=1)
    )
    return amount_frame, derived_name


def build_activity_table(
    df: pd.DataFrame,
    group_column: str,
    amount_columns: Iterable[str] | None = None,
    alert_index: pd.Index | None = None,
    top_n: int = 8,
) -> pd.DataFrame:
    if group_column not in df.columns or df.empty:
        return pd.DataFrame(columns=[group_column, "lignes", "montant_total", "alertes"])

    base = df.dropna(subset=[group_column]).copy()
    if base.empty:
        return pd.DataFrame(columns=[group_column, "lignes", "montant_total", "alertes"])

    working_df, amount_column = _build_amount_reference_frame(base, amount_columns)
    if alert_index is None:
        working_df["_alerte"] = 0
    else:
        working_df["_alerte"] = working_df.index.isin(alert_index).astype(int)

    aggregations: dict[str, tuple[str, str]] = {
        "lignes": (group_column, "size"),
        "alertes": ("_alerte", "sum"),
    }
    if amount_column:
        aggregations["montant_total"] = (amount_column, "sum")

    summary = (
        working_df.groupby(group_column, dropna=False)
        .agg(**aggregations)
        .reset_index()
    )
    if "montant_total" not in summary.columns:
        summary["montant_total"] = pd.NA

    sort_columns = ["montant_total", "alertes", "lignes"] if amount_column else ["alertes", "lignes"]
    return summary.sort_values(sort_columns, ascending=False).head(top_n).reset_index(drop=True)


def build_status_flow_table(df: pd.DataFrame) -> pd.DataFrame:
    if "statut_dossier" not in df.columns or df.empty:
        return pd.DataFrame(columns=["statut_dossier", "nombre_dossiers"])

    flow = (
        df["statut_dossier"]
        .fillna("Non renseigné")
        .astype("string")
        .value_counts(dropna=False)
        .rename_axis("statut_dossier")
        .reset_index(name="nombre_dossiers")
    )

    order_map = {label: index for index, label in enumerate(STATUS_FLOW_ORDER)}
    flow["_ordre"] = flow["statut_dossier"].map(order_map).fillna(len(order_map))
    return flow.sort_values(["_ordre", "nombre_dossiers"], ascending=[True, False]).drop(columns="_ordre")


def build_delay_bucket_table(df: pd.DataFrame) -> pd.DataFrame:
    if "retard_jours" not in df.columns or df.empty:
        return pd.DataFrame(columns=["classe_retard", "nombre_dossiers"])

    delays = pd.to_numeric(df["retard_jours"], errors="coerce")
    labels = pd.Series("Non renseigné", index=df.index, dtype="string")
    labels = labels.mask(delays.fillna(-1) <= 0, "À jour")
    labels = labels.mask((delays > 0) & (delays <= 7), "1-7 jours")
    labels = labels.mask((delays > 7) & (delays <= 30), "8-30 jours")
    labels = labels.mask((delays > 30) & (delays <= 90), "31-90 jours")
    labels = labels.mask(delays > 90, "Plus de 90 jours")

    counts = (
        labels.value_counts(dropna=False)
        .rename_axis("classe_retard")
        .reset_index(name="nombre_dossiers")
    )
    order = {
        "À jour": 0,
        "1-7 jours": 1,
        "8-30 jours": 2,
        "31-90 jours": 3,
        "Plus de 90 jours": 4,
        "Non renseigné": 5,
    }
    counts["_ordre"] = counts["classe_retard"].map(order).fillna(99)
    return counts.sort_values(["_ordre", "nombre_dossiers"], ascending=[True, False]).drop(columns="_ordre")


def build_risk_group_table(df: pd.DataFrame, group_column: str, top_n: int = 8) -> pd.DataFrame:
    if group_column not in df.columns or df.empty:
        return pd.DataFrame(
            columns=[group_column, "dossiers", "risque_eleve", "retard", "montant_demande_total", "score_credit_moyen"]
        )

    base = df.dropna(subset=[group_column]).copy()
    if base.empty:
        return pd.DataFrame(
            columns=[group_column, "dossiers", "risque_eleve", "retard", "montant_demande_total", "score_credit_moyen"]
        )

    base["_risque_eleve"] = base.get("niveau_risque_calcule", pd.Series("", index=base.index)).eq("Élevé").astype(int)
    if "statut_remboursement" in base.columns:
        base["_retard"] = base["statut_remboursement"].eq("En retard").astype(int)
    elif "retard_jours" in base.columns:
        base["_retard"] = (base["retard_jours"].fillna(0) > 0).astype(int)
    else:
        base["_retard"] = 0

    return (
        base.groupby(group_column, dropna=False)
        .agg(
            dossiers=(group_column, "size"),
            risque_eleve=("_risque_eleve", "sum"),
            retard=("_retard", "sum"),
            montant_demande_total=("montant_demande", "sum"),
            score_credit_moyen=("score_credit", "mean"),
        )
        .reset_index()
        .sort_values(["risque_eleve", "retard", "montant_demande_total"], ascending=[False, False, False])
        .head(top_n)
    )


def build_operational_snapshot(df: pd.DataFrame) -> dict[str, object]:
    metrics = build_summary_metrics(df)

    high_risk_count = (
        int(df["niveau_risque_calcule"].eq("Élevé").sum())
        if "niveau_risque_calcule" in df.columns
        else 0
    )
    medium_risk_count = (
        int(df["niveau_risque_calcule"].eq("Moyen").sum())
        if "niveau_risque_calcule" in df.columns
        else 0
    )
    negative_capacity_count = (
        int((df["capacite_remboursement"].fillna(0) < 0).sum())
        if "capacite_remboursement" in df.columns
        else 0
    )
    incomplete_financial_count = (
        int((df["revenu_mensuel"].isna() | df["charge_mensuelle"].isna()).sum())
        if {"revenu_mensuel", "charge_mensuelle"}.issubset(df.columns)
        else 0
    )
    delayed_count = (
        int(df["statut_remboursement"].eq("En retard").sum())
        if "statut_remboursement" in df.columns
        else int((df["retard_jours"].fillna(0) > 0).sum()) if "retard_jours" in df.columns else 0
    )
    overdue_30_count = (
        int((df["retard_jours"].fillna(0) > 30).sum())
        if "retard_jours" in df.columns
        else 0
    )

    def top_label(column: str) -> str:
        freq = build_frequency_table(df, column, top_n=1)
        if freq.empty:
            return "Non renseigné"
        return str(freq.iloc[0][column])

    montant_moyen_demande = (
        float(df["montant_demande"].dropna().mean())
        if "montant_demande" in df.columns and not df["montant_demande"].dropna().empty
        else None
    )

    return {
        **metrics,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "negative_capacity_count": negative_capacity_count,
        "incomplete_financial_count": incomplete_financial_count,
        "delayed_count": delayed_count,
        "overdue_30_count": overdue_30_count,
        "top_agence": top_label("agence"),
        "top_produit": top_label("type_produit"),
        "top_agent": top_label("agent_credit"),
        "top_statut": top_label("statut_dossier"),
        "montant_moyen_demande": montant_moyen_demande,
    }


def build_priority_actions(df: pd.DataFrame) -> list[str]:
    snapshot = build_operational_snapshot(df)
    actions: list[str] = []

    if snapshot["overdue_30_count"]:
        actions.append(
            f"Traiter en priorite {snapshot['overdue_30_count']} dossier(s) avec plus de 30 jours de retard."
        )
    if snapshot["high_risk_count"]:
        actions.append(
            f"Revoir les {snapshot['high_risk_count']} dossier(s) classés en risque élevé avant nouvelle décision."
        )
    if snapshot["negative_capacity_count"]:
        actions.append(
            f"Vérifier les {snapshot['negative_capacity_count']} dossier(s) avec capacité de remboursement négative."
        )
    if snapshot["incomplete_financial_count"]:
        actions.append(
            f"Compléter les informations financières manquantes sur {snapshot['incomplete_financial_count']} dossier(s)."
        )
    if snapshot["taux_retard"] is not None and snapshot["taux_retard"] >= 0.15:
        actions.append("Renforcer le suivi du recouvrement sur le périmètre courant en raison d'un taux de retard élevé.")
    if snapshot["top_agence"] != "Non renseigné":
        actions.append(f"Contrôler en premier le portefeuille de l'agence {snapshot['top_agence']}.")

    if not actions:
        actions.append("Aucun signal critique majeur n'est détecté sur le périmètre courant.")
    return actions[:6]


def build_cycle_priority_actions(df: pd.DataFrame, cycle_key: str) -> list[str]:
    if cycle_key in {"credit", "likelemba"}:
        return build_priority_actions(df)

    watchlist = build_cycle_watchlist(df, cycle_key)
    actions: list[str] = []

    if not watchlist.empty and "motif_alerte" in watchlist.columns:
        exploded_reasons = (
            watchlist["motif_alerte"]
            .astype("string")
            .str.split("; ")
            .explode()
            .dropna()
        )
        exploded_reasons = exploded_reasons[exploded_reasons.ne("")]
        for reason, count in exploded_reasons.value_counts().head(4).items():
            actions.append(f"Traiter {int(count)} ligne(s) marquées : {reason.lower()}.")

    preset = get_cycle_analysis_preset(cycle_key)
    top_group_column = _first_existing_column(df, preset.get("group_columns", []))
    if top_group_column:
        top_group = build_frequency_table(df, top_group_column, top_n=1)
        if not top_group.empty:
            actions.append(
                f"Prioriser la revue du périmètre `{top_group_column}` le plus actif : {top_group.iloc[0][top_group_column]}."
            )

    if not actions:
        actions.append("Aucun signal critique majeur n'est détecté sur le périmètre courant.")
    return actions[:6]


def build_overview_narrative(df: pd.DataFrame) -> str:
    snapshot = build_operational_snapshot(df)
    if df.empty:
        return "Aucune donnée n'est disponible pour produire une synthèse."

    parts = [
        f"Le perimetre courant couvre {snapshot['nombre_dossiers']} dossier(s)",
    ]

    if snapshot["montant_demande_total"] is not None:
        parts.append(
            f"pour un montant demande total de {int(round(float(snapshot['montant_demande_total']))):,}".replace(",", " ")
        )

    if snapshot["taux_approbation"] is not None:
        parts.append(f"avec un taux d'approbation de {snapshot['taux_approbation'] * 100:.1f}%")

    parts.append(".")

    if snapshot["top_agence"] != "Non renseigné":
        parts.append(f"L'agence la plus active est {snapshot['top_agence']}.")
    if snapshot["top_produit"] != "Non renseigné":
        parts.append(f"Le produit dominant est {snapshot['top_produit']}.")
    if snapshot["top_agent"] != "Non renseigné":
        parts.append(f"L'agent le plus exposé dans le périmètre est {snapshot['top_agent']}.")

    risk_sentence = []
    if snapshot["high_risk_count"]:
        risk_sentence.append(f"{snapshot['high_risk_count']} dossier(s) sont en risque élevé")
    if snapshot["medium_risk_count"]:
        risk_sentence.append(f"{snapshot['medium_risk_count']} sont en risque moyen")
    if snapshot["delayed_count"]:
        risk_sentence.append(f"{snapshot['delayed_count']} présentent déjà un retard")
    if risk_sentence:
        parts.append("Sur le plan du risque, " + ", ".join(risk_sentence) + ".")

    if snapshot["incomplete_financial_count"]:
        parts.append(
            f"{snapshot['incomplete_financial_count']} dossier(s) ont des informations financières incomplètes."
        )

    return " ".join(parts)


def build_watchlist(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    watch_mask = pd.Series(False, index=df.index)
    alert_reasons = pd.Series("", index=df.index, dtype="string")
    extra_watchlist_columns: dict[str, pd.Series] = {}

    def mark(mask: pd.Series, label: str) -> None:
        nonlocal watch_mask, alert_reasons
        if not isinstance(mask, pd.Series):
            normalized_mask = pd.Series(bool(mask), index=df.index)
        elif pd.api.types.is_bool_dtype(mask):
            normalized_mask = mask.reindex(df.index).fillna(False)
        elif pd.api.types.is_numeric_dtype(mask):
            normalized_mask = pd.to_numeric(mask.reindex(df.index), errors="coerce").fillna(0).ne(0)
        else:
            text_mask = mask.reindex(df.index).astype("string").str.strip().str.lower()
            normalized_mask = text_mask.isin({"1", "true", "vrai", "yes", "oui", "y", "o"})
        normalized_mask = normalized_mask.astype(bool)
        watch_mask = watch_mask | normalized_mask
        alert_reasons = alert_reasons.mask(normalized_mask, alert_reasons + label + "; ")

    def missing_text(column: str) -> pd.Series:
        if column not in df.columns:
            return pd.Series(False, index=df.index)
        return df[column].isna() | df[column].astype("string").str.strip().fillna("").eq("")

    if "niveau_risque_calcule" in df.columns:
        high_risk_mask = df["niveau_risque_calcule"].eq("Élevé")
        mark(high_risk_mask, "Risque élevé")
    if "retard_jours" in df.columns:
        overdue_mask = df["retard_jours"].fillna(0) > 30
        mark(overdue_mask, "Retard > 30 jours")
    if "capacite_remboursement" in df.columns:
        negative_capacity_mask = df["capacite_remboursement"].fillna(0) < 0
        mark(negative_capacity_mask, "Capacité négative")
    if {"revenu_mensuel", "charge_mensuelle"}.issubset(df.columns):
        incomplete_financial_mask = df["revenu_mensuel"].isna() | df["charge_mensuelle"].isna()
        mark(incomplete_financial_mask, "Données financières incomplètes")

    if "type_produit" in df.columns:
        product_keys = df["type_produit"].astype("string").map(_classify_credit_product)
        extra_watchlist_columns["produit_reference"] = product_keys

        if "garantie" in df.columns:
            garantie_missing_mask = product_keys.notna() & missing_text("garantie")
            mark(garantie_missing_mask, "Garantie non renseignée")

        if "montant_demande" in df.columns:
            amount_series = pd.to_numeric(df["montant_demande"], errors="coerce")
            extra_watchlist_columns["montant_demande"] = amount_series
            for product_key, rules in CREDIT_PRODUCT_RULES.items():
                product_mask = product_keys.eq(product_key)
                min_amount = rules.get("min_amount")
                max_amount = rules.get("max_amount")
                outside_amount_mask = pd.Series(False, index=df.index)
                if min_amount is not None:
                    outside_amount_mask = outside_amount_mask | amount_series.lt(float(min_amount))
                if max_amount is not None:
                    outside_amount_mask = outside_amount_mask | amount_series.gt(float(max_amount))
                mark(product_mask & outside_amount_mask, "Montant hors référentiel produit")

            if "revenu_mensuel" in df.columns:
                revenu_series = pd.to_numeric(df["revenu_mensuel"], errors="coerce")
                advance_mask = product_keys.eq("avance_salaire") & revenu_series.gt(0)
                mark(advance_mask & amount_series.gt(revenu_series / 3.0), "Avance sur salaire > 1/3 du salaire")

        if "duree_credit_mois" in df.columns:
            duration_series = pd.to_numeric(df["duree_credit_mois"], errors="coerce")
            extra_watchlist_columns["duree_credit_mois"] = duration_series
            for product_key, rules in CREDIT_PRODUCT_RULES.items():
                min_duration = rules.get("min_duration")
                max_duration = rules.get("max_duration")
                if min_duration is None and max_duration is None:
                    continue
                product_mask = product_keys.eq(product_key)
                outside_duration_mask = pd.Series(False, index=df.index)
                if min_duration is not None:
                    outside_duration_mask = outside_duration_mask | duration_series.lt(float(min_duration))
                if max_duration is not None:
                    outside_duration_mask = outside_duration_mask | duration_series.gt(float(max_duration))
                mark(product_mask & outside_duration_mask, "Durée hors référentiel produit")

        if "taux_interet" in df.columns:
            rate_series = pd.to_numeric(df["taux_interet"], errors="coerce")
            extra_watchlist_columns["taux_interet"] = rate_series
            for product_key, rules in CREDIT_PRODUCT_RULES.items():
                min_rate = rules.get("min_rate")
                max_rate = rules.get("max_rate")
                if min_rate is None and max_rate is None:
                    continue
                product_mask = product_keys.eq(product_key)
                outside_rate_mask = pd.Series(False, index=df.index)
                if min_rate is not None:
                    outside_rate_mask = outside_rate_mask | rate_series.lt(float(min_rate))
                if max_rate is not None:
                    outside_rate_mask = outside_rate_mask | rate_series.gt(float(max_rate))
                mark(product_mask & outside_rate_mask, "Taux hors référentiel produit")

    columns = [
        column
        for column in [
            "client_id",
            "nom_client",
            "dossier_id",
            "agence",
            "type_produit",
            "montant_demande",
            "montant_accorde",
            "statut_dossier",
            "statut_remboursement",
            "retard_jours",
            "niveau_risque_calcule",
            "garantie",
            "duree_credit_mois",
            "taux_interet",
            "revenu_mensuel",
        ]
        if column in df.columns
    ]
    columns.append("motif_alerte")

    watchlist = df.loc[watch_mask, [column for column in columns if column != "motif_alerte"]].copy()
    for column_name, values in extra_watchlist_columns.items():
        watchlist[column_name] = values.loc[watchlist.index]
    watchlist["motif_alerte"] = (
        alert_reasons.loc[watchlist.index].astype("string").str.rstrip("; ").replace("", "A surveiller")
    )
    sort_columns = [column for column in ["retard_jours", "montant_accorde"] if column in columns]
    if sort_columns:
        return watchlist.sort_values(by=sort_columns, ascending=False)
    return watchlist


def build_cycle_watchlist(df: pd.DataFrame, cycle_key: str) -> pd.DataFrame:
    if cycle_key in {"credit", "likelemba"}:
        return build_watchlist(df)
    if df.empty:
        return df

    watch_mask = pd.Series(False, index=df.index)
    alert_reasons = pd.Series("", index=df.index, dtype="string")
    extra_watchlist_columns: dict[str, pd.Series] = {}

    def mark(mask: pd.Series, label: str) -> None:
        nonlocal watch_mask, alert_reasons
        if not isinstance(mask, pd.Series):
            normalized_mask = pd.Series(bool(mask), index=df.index)
        elif pd.api.types.is_bool_dtype(mask):
            normalized_mask = mask.reindex(df.index).fillna(False)
        elif pd.api.types.is_numeric_dtype(mask):
            normalized_mask = pd.to_numeric(mask.reindex(df.index), errors="coerce").fillna(0).ne(0)
        else:
            text_mask = mask.reindex(df.index).astype("string").str.strip().str.lower()
            normalized_mask = text_mask.isin({"1", "true", "vrai", "yes", "oui", "y", "o"})
        normalized_mask = normalized_mask.astype(bool)
        watch_mask = watch_mask | normalized_mask
        alert_reasons = alert_reasons.mask(normalized_mask, alert_reasons + label + "; ")

    def missing_text(column: str) -> pd.Series:
        if column not in df.columns:
            return pd.Series(False, index=df.index)
        return df[column].isna() | df[column].astype("string").str.strip().fillna("").eq("")

    if "niveau_risque_calcule" in df.columns:
        mark(df["niveau_risque_calcule"].eq("Élevé"), "Risque élevé")

    if cycle_key == "crm_clients":
        if "client_id" in df.columns:
            mark(missing_text("client_id"), "Identifiant client manquant")
        if "nom_client" in df.columns:
            mark(missing_text("nom_client"), "Nom client manquant")
        if "agent_credit" in df.columns:
            mark(missing_text("agent_credit"), "Gestionnaire non renseigné")
        if "compte_id" in df.columns:
            compte_text = df["compte_id"].astype("string").str.strip()
            mark(compte_text.fillna("").isin({"", "0"}), "Numéro de compte client manquant")
        if "Numéro de la pièce d’identité" in df.columns:
            piece_text = df["Numéro de la pièce d’identité"].astype("string").str.strip()
            piece_missing_mask = piece_text.fillna("").isin({"", "0"})
            extra_watchlist_columns["Numéro de la pièce d’identité"] = piece_text
            mark(piece_missing_mask, "Pièce d'identité manquante")
            if "client_id" in df.columns:
                pieces_par_client = (
                    df.loc[~piece_missing_mask & df["client_id"].notna(), ["client_id", "Numéro de la pièce d’identité"]]
                    .drop_duplicates()
                    .groupby("Numéro de la pièce d’identité")["client_id"]
                    .nunique()
                )
                piece_duplicate_mask = piece_text.map(pieces_par_client).fillna(0).gt(1)
                mark(piece_duplicate_mask, "Pièce d'identité partagée")
        if "date_operation" in df.columns:
            dates = pd.to_datetime(df["date_operation"], errors="coerce")
            extra_watchlist_columns["date_operation"] = dates
            if dates.notna().any():
                reference_date = dates.max()
                jours_inactivite = (reference_date - dates).dt.days
                extra_watchlist_columns["jours_inactivite"] = jours_inactivite
                mark(dates.isna(), "Dernière activité non renseignée")
                mark(dates.notna() & jours_inactivite.ge(90), "Aucune activité récente >= 90 j")
                mark(dates.notna() & jours_inactivite.ge(180), "Aucune activité récente >= 180 j")

        phone_candidates = [column_name for column_name in ["telephone", "Portable"] if column_name in df.columns]
        if phone_candidates:
            phone_text = pd.Series(pd.NA, index=df.index, dtype="string")
            for column_name in phone_candidates:
                candidate = df[column_name].astype("string").str.strip()
                phone_text = phone_text.fillna(candidate.mask(candidate.fillna("").eq(""), pd.NA))
            phone_digits = phone_text.fillna("").str.replace(r"\D", "", regex=True)
            extra_watchlist_columns["telephone"] = phone_text
            phone_missing_mask = phone_text.fillna("").eq("")
            phone_invalid_mask = ~phone_missing_mask & ~phone_digits.str.match(r"^(243\d{9}|0\d{9})$", na=False)
            mark(phone_missing_mask, "Téléphone manquant")
            mark(phone_invalid_mask, "Téléphone non fiable")
            if "client_id" in df.columns:
                clients_par_telephone = (
                    pd.DataFrame({"client_id": df["client_id"], "telephone": phone_digits})
                    .loc[lambda frame: frame["client_id"].notna() & frame["telephone"].ne("")]
                    .drop_duplicates()
                    .groupby("telephone")["client_id"]
                    .nunique()
                )
                telephone_shared_mask = phone_digits.map(clients_par_telephone).fillna(0).gt(1)
                mark(telephone_shared_mask, "Téléphone partagé")

        if "E-mail" in df.columns:
            email_text = df["E-mail"].astype("string").str.strip()
            extra_watchlist_columns["E-mail"] = email_text
            email_missing_mask = email_text.fillna("").eq("")
            email_invalid_mask = ~email_missing_mask & ~email_text.str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", na=False)
            mark(email_invalid_mask, "E-mail non fiable")
            if phone_candidates:
                mark(email_missing_mask & phone_missing_mask, "Contact client insuffisant")

        if "Locked" in df.columns:
            locked_mask = df["Locked"].apply(
                lambda value: bool(value) if isinstance(value, bool) else normalize_text(value) in {"true", "oui", "1", "locked"}
            ).fillna(False)
            extra_watchlist_columns["Locked"] = locked_mask
            mark(locked_mask, "Fiche verrouillée")
        if "Rejet des mails" in df.columns:
            rejet_mail_mask = df["Rejet des mails"].apply(
                lambda value: bool(value) if isinstance(value, bool) else normalize_text(value) in {"true", "oui", "1"}
            ).fillna(False)
            extra_watchlist_columns["Rejet des mails"] = rejet_mail_mask
            mark(rejet_mail_mask, "Rejet des mails actif")
        if "Mode Désabonné" in df.columns:
            mode_text = df["Mode Désabonné"].astype("string").str.strip()
            extra_watchlist_columns["Mode Désabonné"] = mode_text
            mark(mode_text.fillna("").ne(""), "Client désabonné")
    elif cycle_key == "epargne":
        if "compte_id" in df.columns:
            mark(missing_text("compte_id"), "Compte non renseigné")
        if "type_operation" in df.columns:
            mark(missing_text("type_operation"), "Type d'opération manquant")
        if "type_produit" in df.columns:
            mark(missing_text("type_produit"), "Produit d'épargne manquant")
            product_keys = df["type_produit"].astype("string").map(_classify_epargne_product)
            extra_watchlist_columns["produit_reference"] = product_keys
        else:
            product_keys = pd.Series(pd.NA, index=df.index, dtype="object")
        if "statut_compte" in df.columns:
            sensitive_statuses = {"bloque", "bloqué", "dormant", "inactif"}
            status_mask = df["statut_compte"].apply(
                lambda value: normalize_text(value) in sensitive_statuses if pd.notna(value) else False
            )
            mark(status_mask, "Compte sensible")
        if "solde_compte" in df.columns:
            solde_compte = pd.to_numeric(df["solde_compte"], errors="coerce")
            extra_watchlist_columns["solde_compte"] = solde_compte
            mark(solde_compte < 0, "Solde négatif")
            if "type_client" in df.columns:
                dat_minimum = df["type_client"].apply(
                    lambda value: EPARGNE_DAT_MINIMUM_USD_MORALE if _is_corporate_client(value) else EPARGNE_DAT_MINIMUM_USD_PHYSIQUE
                )
                extra_watchlist_columns["seuil_minimum_produit"] = dat_minimum
                mark(product_keys.eq("dat") & solde_compte.lt(dat_minimum), "DAT sous minimum attendu")
        if "taux_interet" in df.columns:
            taux_interet = pd.to_numeric(df["taux_interet"], errors="coerce")
            extra_watchlist_columns["taux_interet"] = taux_interet
            mark(product_keys.eq("dat") & (taux_interet.lt(0) | taux_interet.gt(8)), "Taux DAT hors référentiel")
        if {"type_produit", "sexe"}.issubset(df.columns):
            sexe_normalise = df["sexe"].astype("string").map(normalize_text)
            mark(product_keys.eq("femme") & sexe_normalise.eq("masculin"), "Produit femme à confirmer")
        if "date_operation" in df.columns:
            dates = pd.to_datetime(df["date_operation"], errors="coerce")
            extra_watchlist_columns["date_operation"] = dates
            if dates.notna().any():
                reference_date = dates.max()
                jours_inactivite = (reference_date - dates).dt.days
                extra_watchlist_columns["jours_inactivite"] = jours_inactivite
                inactive_90_mask = dates.notna() & (jours_inactivite >= 90)
                inactive_180_mask = dates.notna() & (jours_inactivite >= 180)
                mark(inactive_90_mask, "Compte inactif >= 90 j")
                mark(inactive_180_mask, "Compte très inactif >= 180 j")
                if "solde_compte" in df.columns:
                    positive_balances = solde_compte[solde_compte > 0]
                    if not positive_balances.empty:
                        threshold = float(positive_balances.quantile(0.90))
                        mark(inactive_90_mask & solde_compte.ge(threshold), "Dormance sur solde significatif")
        if "telephone" in df.columns:
            phone_text = df["telephone"].astype("string")
            phone_digits = phone_text.fillna("").str.replace(r"\D", "", regex=True)
            extra_watchlist_columns["telephone"] = phone_text
            phone_missing_mask = missing_text("telephone")
            phone_invalid_mask = ~phone_missing_mask & ~phone_digits.str.match(r"^(243\d{9}|0\d{9})$", na=False)
            mark(phone_missing_mask, "Téléphone manquant")
            mark(phone_invalid_mask, "Téléphone non fiable")
        tracked_kyc_fields = [
            column_name
            for column_name in ["telephone", "zone_geographique", "sexe", "categorie", "date_operation"]
            if column_name in df.columns
        ]
        if tracked_kyc_fields:
            champs_kyc_manquants = pd.Series(0, index=df.index, dtype="int64")
            for column_name in tracked_kyc_fields:
                if column_name == "date_operation":
                    champs_kyc_manquants = champs_kyc_manquants.add(
                        pd.to_datetime(df[column_name], errors="coerce").isna().astype("int64"),
                        fill_value=0,
                    )
                else:
                    champs_kyc_manquants = champs_kyc_manquants.add(
                        missing_text(column_name).astype("int64"),
                        fill_value=0,
                    )
            extra_watchlist_columns["champs_kyc_manquants"] = champs_kyc_manquants
            mark(champs_kyc_manquants >= 2, "KYC incomplet (2+ champs)")
        if {"client_id", "compte_id"}.issubset(df.columns):
            comptes_par_client = (
                df.dropna(subset=["client_id", "compte_id"])
                .groupby("client_id")["compte_id"]
                .nunique()
            )
            nombre_comptes_client = df["client_id"].map(comptes_par_client).fillna(0)
            extra_watchlist_columns["nombre_comptes_client"] = nombre_comptes_client
            mark(nombre_comptes_client >= 3, "Client multi-comptes (>= 3)")
        if {"sexe", "categorie"}.issubset(df.columns):
            sexe_normalise = df["sexe"].astype("string").map(normalize_text)
            categorie_normalisee = (
                df["categorie"]
                .astype("string")
                .map(normalize_text)
                .replace({"f": "feminin", "m": "masculin"})
            )
            incoherence_mask = (
                sexe_normalise.notna()
                & categorie_normalisee.notna()
                & sexe_normalise.ne("")
                & categorie_normalisee.ne("")
                & sexe_normalise.ne(categorie_normalisee)
            )
            mark(incoherence_mask, "Incohérence sexe / catégorie")
        if {"Provenance", "compte_id"}.issubset(df.columns):
            extractions_par_compte = (
                df.dropna(subset=["Provenance", "compte_id"])
                .groupby("compte_id")["Provenance"]
                .nunique()
            )
            nombre_extractions_compte = df["compte_id"].map(extractions_par_compte).fillna(0)
            extra_watchlist_columns["nombre_extractions_compte"] = nombre_extractions_compte
            mark(nombre_extractions_compte > 1, "Compte présent dans plusieurs extractions")
    elif cycle_key == "caisse":
        if "caissier" in df.columns:
            mark(missing_text("caissier"), "Caissier non renseigné")
        if "ecart_caisse" in df.columns:
            mark(pd.to_numeric(df["ecart_caisse"], errors="coerce").fillna(0).ne(0), "Écart de caisse")
        if "encaisse_fin_jour" in df.columns:
            mark(pd.to_numeric(df["encaisse_fin_jour"], errors="coerce") < 0, "Encaisse négative")
    elif cycle_key == "tresorerie":
        if "banque" in df.columns:
            mark(missing_text("banque"), "Banque non renseignée")
        if "compte_bancaire" in df.columns:
            mark(missing_text("compte_bancaire"), "Compte bancaire manquant")
        if "ecart_rapprochement" in df.columns:
            mark(
                pd.to_numeric(df["ecart_rapprochement"], errors="coerce").fillna(0).ne(0),
                "Écart de rapprochement",
            )
        if "solde_banque" in df.columns:
            mark(pd.to_numeric(df["solde_banque"], errors="coerce") < 0, "Solde bancaire négatif")
    elif cycle_key == "comptable":
        if "piece_id" in df.columns:
            mark(missing_text("piece_id"), "Pièce comptable manquante")
        if "journal" in df.columns:
            mark(missing_text("journal"), "Journal non renseigné")
        if {"montant_debit", "montant_credit"}.issubset(df.columns):
            debit = pd.to_numeric(df["montant_debit"], errors="coerce").fillna(0)
            credit = pd.to_numeric(df["montant_credit"], errors="coerce").fillna(0)
            mark((debit - credit).abs() > 0.01, "Écriture non équilibrée")
    elif cycle_key == "rh_admin":
        if "agent_id" in df.columns:
            mark(missing_text("agent_id"), "Agent non renseigné")
        if "fonction" in df.columns:
            mark(missing_text("fonction"), "Fonction manquante")
        if "salaire" in df.columns:
            salaire = pd.to_numeric(df["salaire"], errors="coerce")
            mark(salaire.isna() | (salaire <= 0), "Salaire non documenté")
    elif cycle_key == "si":
        if "agent_id" in df.columns:
            mark(missing_text("agent_id"), "Agent non renseigné")
        if "profil_acces" in df.columns:
            mark(missing_text("profil_acces"), "Profil d'accès manquant")
        if "niveau_habilitation" in df.columns:
            mark(missing_text("niveau_habilitation"), "Niveau d'habilitation manquant")
    elif cycle_key == "continuite":
        if "type_sauvegarde" in df.columns:
            mark(missing_text("type_sauvegarde"), "Type de sauvegarde manquant")
        if "support_sauvegarde" in df.columns:
            mark(missing_text("support_sauvegarde"), "Support non renseigné")
        if "statut_test_reprise" in df.columns:
            mark(missing_text("statut_test_reprise"), "Test de reprise non documenté")
        if "incident_majeur" in df.columns:
            incident_text = df["incident_majeur"].astype("string").str.strip().fillna("")
            mark(incident_text.ne("") & incident_text.ne("Non"), "Incident majeur déclaré")
    elif cycle_key == "money_provider":
        if "numero_reference" in df.columns:
            mark(missing_text("numero_reference"), "Référence manquante")
        if "operateur" in df.columns:
            mark(missing_text("operateur"), "Opérateur non renseigné")
        if "tresorier" in df.columns:
            mark(missing_text("tresorier"), "Trésorier non renseigné")
        if "telephone" in df.columns:
            mark(missing_text("telephone"), "Téléphone non renseigné")
        if "journal_transaction" in df.columns:
            mark(missing_text("journal_transaction"), "Journal de transaction manquant")
        if "solde_final" in df.columns:
            mark(pd.to_numeric(df["solde_final"], errors="coerce") < 0, "Solde final négatif")
    elif cycle_key == "operations_depot_retrait":
        if "operation_non_validee" in df.columns:
            mark(df["operation_non_validee"].fillna(False), "Opération non validée")
        if "saisie_tardive" in df.columns:
            mark(df["saisie_tardive"].fillna(False), "Saisie tardive")
        if "validation_incoherente" in df.columns:
            mark(df["validation_incoherente"].fillna(False), "Validation incohérente")
        if "auto_validation" in df.columns:
            mark(df["auto_validation"].fillna(False), "Auto-validation")
        if "annule" in df.columns:
            mark(df["annule"].fillna(False), "Opération annulée")
        if "operateur" in df.columns:
            mark(missing_text("operateur"), "Utilisateur non renseigné")
        if "agence" in df.columns:
            mark(missing_text("agence"), "Point de service manquant")
        if "type_operation" in df.columns:
            mark(missing_text("type_operation"), "Type d'opération manquant")
        if "numero_reference" in df.columns:
            duplicate_ref_mask = (
                df["numero_reference"]
                .astype("string")
                .str.strip()
                .replace("", pd.NA)
                .map(
                    df["numero_reference"]
                    .astype("string")
                    .str.strip()
                    .replace("", pd.NA)
                    .value_counts(dropna=True)
                )
                .fillna(0)
                .gt(1)
            )
            mark(duplicate_ref_mask, "Référence dupliquée")
        if "numero_recu" in df.columns:
            duplicate_receipt_mask = (
                df["numero_recu"]
                .astype("string")
                .str.strip()
                .replace("", pd.NA)
                .map(
                    df["numero_recu"]
                    .astype("string")
                    .str.strip()
                    .replace("", pd.NA)
                    .value_counts(dropna=True)
                )
                .fillna(0)
                .gt(1)
            )
            mark(duplicate_receipt_mask, "Reçu dupliqué")
        if "equilibre_comptable_ok" in df.columns:
            mark(~df["equilibre_comptable_ok"].fillna(False), "Écriture déséquilibrée")
        if "ecarts_date_valeur" in df.columns:
            mark(pd.to_numeric(df["ecarts_date_valeur"], errors="coerce").fillna(0).gt(0), "Date de valeur différente")
        if "lignes_sens_absent" in df.columns:
            mark(pd.to_numeric(df["lignes_sens_absent"], errors="coerce").fillna(0).gt(0), "Sens comptable absent")
        if "lignes_montant_non_positif" in df.columns:
            mark(pd.to_numeric(df["lignes_montant_non_positif"], errors="coerce").fillna(0).gt(0), "Montant comptable non positif")
        if "kyc_missing_count" in df.columns:
            mark(pd.to_numeric(df["kyc_missing_count"], errors="coerce").fillna(0).gt(0), "KYC client à compléter")

    if not bool(watch_mask.any()):
        return pd.DataFrame(columns=["motif_alerte"])

    preset = get_cycle_analysis_preset(cycle_key)
    candidate_columns = [
        *preset.get("id_columns", []),
        *preset.get("group_columns", []),
        *preset.get("actor_columns", []),
        *preset.get("status_columns", []),
        *preset.get("amount_columns", []),
        "niveau_risque_calcule",
        "commentaire",
    ]
    if cycle_key == "epargne":
        candidate_columns.extend(["nom_client", "telephone", "Provenance"])
    elif cycle_key == "crm_clients":
        candidate_columns.extend(
            [
                "nom_client",
                "telephone",
                "Portable",
                "E-mail",
                "zone_geographique",
                "Numéro de la pièce d’identité",
                "Source de données",
                "Origine du Prospect",
            ]
        )
    elif cycle_key == "operations_depot_retrait":
        candidate_columns.extend(
            [
                "nom_client",
                "type_mouvement",
                "source_mouvement",
                "code_devise",
                "agence",
                "numero_recu",
                "date_saisie",
                "date_validation",
                "delai_saisie_jours",
            ]
        )
    candidate_columns.extend(extra_watchlist_columns.keys())
    columns = [column for column in dict.fromkeys(candidate_columns) if column in df.columns]
    watchlist = df.loc[watch_mask, columns].copy()
    for column_name, values in extra_watchlist_columns.items():
        watchlist[column_name] = values.loc[watchlist.index]
    watchlist["motif_alerte"] = (
        alert_reasons.loc[watchlist.index].astype("string").str.rstrip("; ").replace("", "A surveiller")
    )

    if cycle_key == "epargne":
        watchlist["_abs_solde_compte"] = pd.to_numeric(
            watchlist.get("solde_compte"),
            errors="coerce",
        ).abs()
        epargne_sort_columns = [
            column_name
            for column_name in ["jours_inactivite", "_abs_solde_compte", "nombre_comptes_client"]
            if column_name in watchlist.columns
        ]
        if epargne_sort_columns:
            watchlist = watchlist.sort_values(by=epargne_sort_columns, ascending=False)
        return watchlist.drop(columns="_abs_solde_compte", errors="ignore")
    if cycle_key == "crm_clients":
        crm_sort_columns = [
            column_name
            for column_name in ["jours_inactivite", "revenu_mensuel"]
            if column_name in watchlist.columns
        ]
        if crm_sort_columns:
            return watchlist.sort_values(by=crm_sort_columns, ascending=[False] * len(crm_sort_columns))
        return watchlist

    numeric_sort_candidates = [
        column
        for column in [
            "montant_demande",
            "montant_accorde",
            "montant_operation",
            "solde_final",
            "solde_banque",
            "encaisse_fin_jour",
        ]
        if column in watchlist.columns
    ]
    if numeric_sort_candidates:
        return watchlist.sort_values(by=numeric_sort_candidates[0], ascending=False)
    return watchlist
