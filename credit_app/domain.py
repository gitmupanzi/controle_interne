from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from credit_app.core import safe_divide


COLUMN_ALIASES = {
    "client_id": [
        "client_id",
        "id_client",
        "id client",
        "code_client",
        "numero_client",
        "num_client",
        "reference_client",
    ],
    "dossier_id": [
        "dossier_id",
        "id_dossier",
        "id dossier",
        "numero_dossier",
        "num_dossier",
        "reference_dossier",
        "ref_dossier",
        "numero dossier",
    ],
    "nom_client": [
        "nom_client",
        "nom client",
        "client",
        "nom",
        "nom_complet",
        "full_name",
    ],
    "date_demande": [
        "date_demande",
        "date demande",
        "date_de_demande",
        "date soumission",
        "date dossier",
    ],
    "date_decision": [
        "date_decision",
        "date decision",
        "date_validation",
        "date approbation",
    ],
    "montant_demande": [
        "montant_demande",
        "montant demande",
        "montant sollicite",
        "montant_solicite",
        "montant credit demande",
    ],
    "montant_accorde": [
        "montant_accorde",
        "montant accorde",
        "montant valide",
        "montant decaisse",
        "montant credit accorde",
    ],
    "revenu_mensuel": [
        "revenu_mensuel",
        "revenu mensuel",
        "salaire",
        "revenu",
        "revenus_mensuels",
        "chiffre_affaire_mensuel",
    ],
    "charge_mensuelle": [
        "charge_mensuelle",
        "charge mensuelle",
        "charges_mensuelles",
        "charges",
        "depenses_mensuelles",
    ],
    "duree_credit_mois": [
        "duree_credit_mois",
        "duree_mois",
        "duree",
        "duree_credit",
        "nombre_mois",
    ],
    "taux_interet": [
        "taux_interet",
        "taux interet",
        "interet",
        "taux",
    ],
    "garantie": [
        "garantie",
        "type_garantie",
        "garanties",
        "surete",
    ],
    "score_credit": [
        "score_credit",
        "score credit",
        "score",
        "credit_score",
        "notation",
    ],
    "niveau_risque": [
        "niveau_risque",
        "niveau risque",
        "risque",
        "classe_risque",
    ],
    "retard_jours": [
        "retard_jours",
        "jours_retard",
        "retard",
        "nombre_jours_retard",
        "days_past_due",
    ],
    "statut_dossier": [
        "statut_dossier",
        "statut dossier",
        "decision",
        "etat_dossier",
        "status_dossier",
    ],
    "statut_remboursement": [
        "statut_remboursement",
        "statut remboursement",
        "etat_remboursement",
        "status_remboursement",
        "etat_paiement",
    ],
    "agence": [
        "agence",
        "branch",
        "succursale",
        "bureau",
    ],
    "agent_credit": [
        "agent_credit",
        "agent credit",
        "charge_portefeuille",
        "gestionnaire",
        "officier_credit",
    ],
    "type_produit": [
        "type_produit",
        "produit",
        "type_credit",
        "categorie_produit",
    ],
    "sexe": [
        "sexe",
        "sex",
        "genre",
        "gender",
        "sexe client",
        "sexe_client",
    ],
    "age": [
        "age",
        "age client",
        "age_client",
        "age du client",
    ],
}

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
]

DATE_COLUMNS = ["date_demande", "date_decision"]
STATUS_FLOW_ORDER = [
    "Recu",
    "A completer",
    "En analyse",
    "Approuve",
    "Decaisse",
    "En remboursement",
    "En retard",
    "Cloture",
    "Rejete",
]

STATUS_DOSSIER_MAP = {
    "recu": "Recu",
    "reçu": "Recu",
    "en analyse": "En analyse",
    "en cours": "En analyse",
    "a completer": "A completer",
    "à completer": "A completer",
    "approuve": "Approuve",
    "approuvé": "Approuve",
    "accorde": "Approuve",
    "rejete": "Rejete",
    "rejeté": "Rejete",
    "refuse": "Rejete",
    "refusé": "Rejete",
    "decaisse": "Decaisse",
    "décaissé": "Decaisse",
    "en remboursement": "En remboursement",
    "en retard": "En retard",
    "cloture": "Cloture",
    "clôturé": "Cloture",
}

STATUS_REMBOURSEMENT_MAP = {
    "a jour": "A jour",
    "à jour": "A jour",
    "normal": "A jour",
    "non decaisse": "Non decaisse",
    "non décaissé": "Non decaisse",
    "non decaissé": "Non decaisse",
    "en retard": "En retard",
    "impaye": "En retard",
    "impayé": "En retard",
    "solde": "Solde",
    "soldé": "Solde",
    "cloture": "Solde",
    "clôturé": "Solde",
}

SEX_VALUE_MAP = {
    "m": "Masculin",
    "masculin": "Masculin",
    "male": "Masculin",
    "homme": "Masculin",
    "h": "Masculin",
    "f": "Feminin",
    "feminin": "Feminin",
    "female": "Feminin",
    "femme": "Feminin",
}


def normalize_text(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.replace("_", " ").strip().lower().split())


def _build_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            lookup[normalize_text(alias)] = canonical
    return lookup


ALIAS_LOOKUP = _build_alias_lookup()
RENAME_REFERENCE_PATH = Path("data/Rename_columns.xlsx")


def standardize_column_name(column_name: str) -> str:
    normalized = normalize_text(column_name)
    reference_mapped = REFERENCE_COLUMN_LOOKUP.get(normalized)
    if reference_mapped:
        reference_normalized = normalize_text(reference_mapped)
        return ALIAS_LOOKUP.get(reference_normalized, str(reference_mapped).strip())
    return ALIAS_LOOKUP.get(normalized, column_name.strip())


def _load_reference_column_lookup() -> dict[str, str]:
    if not RENAME_REFERENCE_PATH.exists():
        return {}
    try:
        df = pd.read_excel(RENAME_REFERENCE_PATH)
    except Exception:
        return {}

    required_columns = {"Original", "Renamed"}
    if not required_columns.issubset(df.columns):
        return {}

    lookup: dict[str, str] = {}
    for original, renamed in df[["Original", "Renamed"]].dropna().itertuples(index=False):
        original_key = normalize_text(original)
        renamed_value = str(renamed).strip()
        if original_key and renamed_value:
            lookup[original_key] = renamed_value
    return lookup


REFERENCE_COLUMN_LOOKUP = _load_reference_column_lookup()


def get_reference_column_count() -> int:
    return len(REFERENCE_COLUMN_LOOKUP)


def _coerce_numeric(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        series = (
            series.astype(str)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
    return pd.to_numeric(series, errors="coerce")


def _normalize_series_values(series: pd.Series, mapping: dict[str, str]) -> pd.Series:
    return series.apply(
        lambda value: mapping.get(normalize_text(value), str(value).strip()) if pd.notna(value) else value
    )


def derive_risk_level(row: pd.Series) -> str:
    explicit_level = row.get("niveau_risque")
    if pd.notna(explicit_level) and str(explicit_level).strip():
        return str(explicit_level).strip().title()

    score = row.get("score_credit")
    if pd.notna(score):
        if score >= 80:
            return "Faible"
        if score >= 50:
            return "Moyen"
        return "Eleve"

    debt_ratio = row.get("taux_endettement")
    if pd.notna(debt_ratio):
        if debt_ratio <= 0.30:
            return "Faible"
        if debt_ratio <= 0.50:
            return "Moyen"
        return "Eleve"

    delay = row.get("retard_jours")
    if pd.notna(delay):
        if delay <= 0:
            return "Faible"
        if delay <= 30:
            return "Moyen"
        return "Eleve"

    return "Non renseigne"


def build_standardized_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, str]]:
    standardized = df.copy()
    mapping = {column: standardize_column_name(column) for column in standardized.columns}
    standardized = standardized.rename(columns=mapping)

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
        add_check("Dossiers dupliques", duplicate_mask)
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
        add_check("Montants demandes negatifs", df["montant_demande"] < 0)
    if "montant_accorde" in df.columns:
        add_check("Montants accordes negatifs", df["montant_accorde"] < 0)
    if {"montant_demande", "montant_accorde"}.issubset(df.columns):
        add_check("Montants accordes superieurs au demande", df["montant_accorde"] > df["montant_demande"])
    if {"revenu_mensuel", "charge_mensuelle"}.issubset(df.columns):
        add_check(
            "Donnees financieres manquantes",
            df["revenu_mensuel"].isna() | df["charge_mensuelle"].isna(),
        )
    if "retard_jours" in df.columns:
        add_check("Retards negatifs", df["retard_jours"] < 0)
    if "capacite_remboursement" in df.columns:
        add_check("Capacite de remboursement negative", df["capacite_remboursement"] < 0)

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


def filter_dataframe(
    df: pd.DataFrame,
    statuses: Iterable[str] | None = None,
    agencies: Iterable[str] | None = None,
    products: Iterable[str] | None = None,
    start_date: object | None = None,
    end_date: object | None = None,
) -> pd.DataFrame:
    filtered = df.copy()

    if statuses and "statut_dossier" in filtered.columns:
        filtered = filtered[filtered["statut_dossier"].isin(statuses)]

    if agencies and "agence" in filtered.columns:
        filtered = filtered[filtered["agence"].isin(agencies)]

    if products and "type_produit" in filtered.columns:
        filtered = filtered[filtered["type_produit"].isin(products)]

    if "date_demande" in filtered.columns and start_date is not None:
        filtered = filtered[filtered["date_demande"].dt.date >= start_date]

    if "date_demande" in filtered.columns and end_date is not None:
        filtered = filtered[filtered["date_demande"].dt.date <= end_date]

    return filtered.reset_index(drop=True)


def build_summary_metrics(df: pd.DataFrame) -> dict[str, object]:
    approved_statuses = {"Approuve", "Decaisse", "En remboursement", "En retard", "Cloture"}

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
        .fillna("Non renseigne")
        .astype("string")
        .str.strip()
        .replace("", "Non renseigne")
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

    distribution["sexe"] = distribution["sexe"].replace({"Non renseigne": "Inconnu"})
    order_map = {"Masculin": 0, "Feminin": 1, "Inconnu": 2}
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
    labels = pd.Series("Non renseigne", index=df.index, dtype="string")
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
        "Non renseigne": 7,
    }
    distribution["_ordre"] = distribution["tranche_age"].map(order_map).fillna(99)
    return (
        distribution.sort_values(["_ordre", "nombre_lignes"], ascending=[True, False])
        .drop(columns="_ordre")
        .reset_index(drop=True)
    )


def build_age_sex_pyramid_table(df: pd.DataFrame) -> pd.DataFrame:
    if "age" not in df.columns or "sexe" not in df.columns:
        return pd.DataFrame(columns=["tranche_age", "Masculin", "Feminin"])

    age_distribution = build_age_bucket_table(df)
    if age_distribution.empty:
        return pd.DataFrame(columns=["tranche_age", "Masculin", "Feminin"])

    age_order = age_distribution["tranche_age"].tolist()
    base = df.copy()
    ages = pd.to_numeric(base["age"], errors="coerce")
    labels = pd.Series("Non renseigne", index=base.index, dtype="string")
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
        .where(lambda s: s.isin(["Masculin", "Feminin"]), "Inconnu")
    )

    grouped = (
        base.groupby(["tranche_age", "sexe_pyramide"], observed=False)
        .size()
        .reset_index(name="nombre_lignes")
    )
    if grouped.empty:
        return pd.DataFrame(columns=["tranche_age", "Masculin", "Feminin"])

    pivot = (
        grouped.pivot(index="tranche_age", columns="sexe_pyramide", values="nombre_lignes")
        .fillna(0)
        .reset_index()
    )
    for column in ["Masculin", "Feminin"]:
        if column not in pivot.columns:
            pivot[column] = 0
    return pivot[["tranche_age", "Masculin", "Feminin"]]


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
        base["niveau_risque_calcule"].eq("Eleve")
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


def build_status_flow_table(df: pd.DataFrame) -> pd.DataFrame:
    if "statut_dossier" not in df.columns or df.empty:
        return pd.DataFrame(columns=["statut_dossier", "nombre_dossiers"])

    flow = (
        df["statut_dossier"]
        .fillna("Non renseigne")
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
    labels = pd.Series("Non renseigne", index=df.index, dtype="string")
    labels = labels.mask(delays.fillna(-1) <= 0, "A jour")
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
        "A jour": 0,
        "1-7 jours": 1,
        "8-30 jours": 2,
        "31-90 jours": 3,
        "Plus de 90 jours": 4,
        "Non renseigne": 5,
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

    base["_risque_eleve"] = base.get("niveau_risque_calcule", pd.Series("", index=base.index)).eq("Eleve").astype(int)
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
        int(df["niveau_risque_calcule"].eq("Eleve").sum())
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
            return "Non renseigne"
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
            f"Revoir les {snapshot['high_risk_count']} dossier(s) classes en risque eleve avant nouvelle decision."
        )
    if snapshot["negative_capacity_count"]:
        actions.append(
            f"Verifier les {snapshot['negative_capacity_count']} dossier(s) avec capacite de remboursement negative."
        )
    if snapshot["incomplete_financial_count"]:
        actions.append(
            f"Completer les informations financieres manquantes sur {snapshot['incomplete_financial_count']} dossier(s)."
        )
    if snapshot["taux_retard"] is not None and snapshot["taux_retard"] >= 0.15:
        actions.append("Renforcer le suivi recouvrement sur le perimetre courant en raison d'un taux de retard eleve.")
    if snapshot["top_agence"] != "Non renseigne":
        actions.append(f"Controler en premier le portefeuille de l'agence {snapshot['top_agence']}.")

    if not actions:
        actions.append("Aucun signal critique majeur n'est detecte sur le perimetre courant.")
    return actions[:6]


def build_overview_narrative(df: pd.DataFrame) -> str:
    snapshot = build_operational_snapshot(df)
    if df.empty:
        return "Aucune donnee n'est disponible pour produire une synthese."

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

    if snapshot["top_agence"] != "Non renseigne":
        parts.append(f"L'agence la plus active est {snapshot['top_agence']}.")
    if snapshot["top_produit"] != "Non renseigne":
        parts.append(f"Le produit dominant est {snapshot['top_produit']}.")
    if snapshot["top_agent"] != "Non renseigne":
        parts.append(f"L'agent le plus expose dans le perimetre est {snapshot['top_agent']}.")

    risk_sentence = []
    if snapshot["high_risk_count"]:
        risk_sentence.append(f"{snapshot['high_risk_count']} dossier(s) sont en risque eleve")
    if snapshot["medium_risk_count"]:
        risk_sentence.append(f"{snapshot['medium_risk_count']} sont en risque moyen")
    if snapshot["delayed_count"]:
        risk_sentence.append(f"{snapshot['delayed_count']} presentent deja un retard")
    if risk_sentence:
        parts.append("Sur le plan du risque, " + ", ".join(risk_sentence) + ".")

    if snapshot["incomplete_financial_count"]:
        parts.append(
            f"{snapshot['incomplete_financial_count']} dossier(s) ont des informations financieres incompletes."
        )

    return " ".join(parts)


def build_watchlist(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    watch_mask = pd.Series(False, index=df.index)
    alert_reasons = pd.Series("", index=df.index, dtype="string")

    if "niveau_risque_calcule" in df.columns:
        high_risk_mask = df["niveau_risque_calcule"].eq("Eleve")
        watch_mask = watch_mask | high_risk_mask
        alert_reasons = alert_reasons.mask(high_risk_mask, alert_reasons + "Risque eleve; ")
    if "retard_jours" in df.columns:
        overdue_mask = df["retard_jours"].fillna(0) > 30
        watch_mask = watch_mask | overdue_mask
        alert_reasons = alert_reasons.mask(overdue_mask, alert_reasons + "Retard > 30 jours; ")
    if "capacite_remboursement" in df.columns:
        negative_capacity_mask = df["capacite_remboursement"].fillna(0) < 0
        watch_mask = watch_mask | negative_capacity_mask
        alert_reasons = alert_reasons.mask(
            negative_capacity_mask, alert_reasons + "Capacite negative; "
        )
    if {"revenu_mensuel", "charge_mensuelle"}.issubset(df.columns):
        incomplete_financial_mask = df["revenu_mensuel"].isna() | df["charge_mensuelle"].isna()
        watch_mask = watch_mask | incomplete_financial_mask
        alert_reasons = alert_reasons.mask(
            incomplete_financial_mask, alert_reasons + "Donnees financieres incompletes; "
        )

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
        ]
        if column in df.columns
    ]
    columns.append("motif_alerte")

    watchlist = df.loc[watch_mask, [column for column in columns if column != "motif_alerte"]].copy()
    watchlist["motif_alerte"] = (
        alert_reasons.loc[watchlist.index].astype("string").str.rstrip("; ").replace("", "A surveiller")
    )
    sort_columns = [column for column in ["retard_jours", "montant_accorde"] if column in columns]
    if sort_columns:
        return watchlist.sort_values(by=sort_columns, ascending=False)
    return watchlist
