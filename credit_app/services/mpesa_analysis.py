from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from io import BytesIO
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unicodedata
from typing import Any, Iterable

import numpy as np
import pandas as pd
from openpyxl.styles import Font, PatternFill

from credit_app.data_schema import (
    CURRENT_SAVINGS_SCHEMA,
    CUSTOMERS_SCHEMA,
    FIXED_SAVINGS_SCHEMA,
    G2_TRANSACTIONS_SCHEMA,
    LOANS_SCHEMA,
    MPESA_TRANSACTIONS_SCHEMA,
    PERFECT_CLIENTS_SCHEMA,
    DataSchema,
    validate_dataframe_schema,
)


TRANSACTION_REQUIRED_COLUMNS = set(MPESA_TRANSACTIONS_SCHEMA.required)
CURRENT_SAVINGS_REQUIRED_COLUMNS = set(CURRENT_SAVINGS_SCHEMA.required)
FIXED_SAVINGS_REQUIRED_COLUMNS = set(FIXED_SAVINGS_SCHEMA.required)
G2_TRANSACTION_REQUIRED_COLUMNS = set(G2_TRANSACTIONS_SCHEMA.required)
CUSTOMERS_REQUIRED_COLUMNS = set(CUSTOMERS_SCHEMA.required)
PERFECT_CLIENTS_REQUIRED_COLUMNS = set(PERFECT_CLIENTS_SCHEMA.required)

LOAN_USEFUL_COLUMNS = {
    "loan_id",
    "customer_id",
    "Nom_client",
    "customer",
    "msisdn1",
    "currency_code",
    "loan_amount",
    "loan_balance",
    "amount_paid",
    "outstanding_principle",
    "outstanding_interest",
    "outstanding_penalty_fees",
    "status_name",
    "due_date",
    "last_repayment_date",
    "created_at",
    "updated_at",
}

TEXT_COLUMNS = [
    "customer_id",
    "msisdn",
    "msisdn1",
    "account_type",
    "reference_id",
    "ref_no",
    "currency_code",
    "description",
    "loan_id",
    "customer",
    "product_name",
    "status_name",
]

DATE_COLUMNS = [
    "created_at",
    "updated_at",
    "date_approved",
    "maturity_date",
    "due_date",
    "last_repayment_date",
]

NUMERIC_COLUMNS = [
    "dr",
    "cr",
    "bal_before",
    "bal_after",
    "balance",
    "loan_amount",
    "loan_balance",
    "amount_paid",
    "outstanding_principle",
    "outstanding_interest",
    "outstanding_penalty_fees",
]

KNOWN_ACCOUNT_TYPES = {
    "MPESA ACCOUNT",
    "NORMAL SAVINGS",
    "FIXED SAVINGS",
}

G2_OPERATION_CATEGORIES = [
    "DAT",
    "Depot normal",
    "Remboursement prets",
    "Paiement client B2C",
    "Demande de credit",
    "Operation interne Bisou",
    "Autre entree",
    "Autre sortie",
    "Flux a verifier",
]

G2_CLASSIFIED_TRANSACTION_COLUMNS = [
    "date",
    "receipt_no",
    "currency_code",
    "details_rapport",
    "opposite_party",
    "duree",
    "compte_cree",
    "montant",
    "montant_entree",
    "montant_sortie",
    "balance_numeric",
]


@dataclass(frozen=True)
class MpesaPreparedData:
    transactions: pd.DataFrame
    current_savings: pd.DataFrame
    fixed_savings: pd.DataFrame
    loans: pd.DataFrame
    load_report: pd.DataFrame
    g2_transactions: pd.DataFrame = field(default_factory=pd.DataFrame)
    customers: pd.DataFrame = field(default_factory=pd.DataFrame)
    perfect_clients: pd.DataFrame = field(default_factory=pd.DataFrame)


def _is_empty_text(value: Any) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() in {"", "nan", "<na>", "none", "null"}


def normalize_label(value: Any) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def classify_g2_business_operation(row: pd.Series, *, dat_matched: bool = False) -> str:
    """Classe une transaction G2 apres determination independante de son sens."""
    direction = normalize_label(row.get("sens_flux", ""))
    details = normalize_label(row.get("details", ""))
    reason_type = normalize_label(row.get("reason_type", ""))
    text = f"{reason_type} {details}"

    if "super transaction" in text or "supertransaction" in text:
        return "Operation interne Bisou"
    if direction not in {"entree", "sortie"}:
        return "Flux a verifier"
    if direction == "sortie":
        if any(token in text for token in ["bisoubisouloanrequest", "loan request", "loan payment", "loan payement"]):
            return "Demande de credit"
        if "bisoubisoub2c" in text or "b2c payment" in text:
            return "Paiement client B2C"
        return "Autre sortie"
    if "bisoubisouc2brepayment" in text or "bisoubisourepayment" in text or "repayment" in text:
        return "Remboursement prets"
    if dat_matched:
        return "DAT"
    if "bisoubisouc2b" in text or direction == "entree":
        return "Depot normal"
    return "Autre entree"


def clean_identifier(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace({"nan": "", "<NA>": "", "None": ""})
    )


def normalize_phone(series: pd.Series) -> pd.Series:
    digits = series.astype("string").fillna("").str.replace(r"\D+", "", regex=True)
    digits = digits.str.replace(r"^2430", "243", regex=True)
    digits = digits.str.replace(r"^0", "243", regex=True)
    needs_prefix = digits.ne("") & ~digits.str.startswith("243", na=False)
    digits = digits.where(~needs_prefix, "243" + digits)
    return digits.replace({"": pd.NA})


def clean_text(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").str.strip()


def _normalize_column_name(column: object) -> str:
    text = str(column).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_business_column_key(column: object) -> str:
    text = normalize_label(_normalize_column_name(column))
    text = re.sub(r"[^0-9a-z]+", "_", text).strip("_")
    return text


def concat_unique(values: Iterable[object]) -> str:
    result: list[str] = []
    for value in values:
        if _is_empty_text(value):
            continue
        text = str(value).strip()
        if text not in result:
            result.append(text)
    return " | ".join(result)


def first_non_empty(values: Iterable[object]) -> object:
    for value in values:
        if not _is_empty_text(value):
            return str(value).strip()
    return pd.NA


def extract_prefixed_reference(value: object, prefix: str) -> str:
    if _is_empty_text(value):
        return ""
    parts = [part.strip() for part in str(value).split("|")]
    matches = [part for part in parts if part.upper().startswith(prefix.upper())]
    return " | ".join(matches)


def concat_frames_stable(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    prepared_frames: list[pd.DataFrame] = []
    expected_columns: list[object] = []

    for frame in frames:
        if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        for column in frame.columns:
            if column not in expected_columns:
                expected_columns.append(column)
        # Pandas warns when all-NA columns participate in dtype inference.
        # Drop them for concatenation, then restore the full column set below.
        useful_frame = frame.dropna(axis=1, how="all")
        if useful_frame.empty:
            continue
        prepared_frames.append(useful_frame)

    if not prepared_frames:
        return pd.DataFrame(columns=expected_columns)

    concatenated = pd.concat(prepared_frames, ignore_index=True)
    return concatenated.reindex(columns=expected_columns)


def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: set[str],
    file_label: str,
) -> list[str]:
    known_schemas: tuple[DataSchema, ...] = (
        MPESA_TRANSACTIONS_SCHEMA,
        CURRENT_SAVINGS_SCHEMA,
        FIXED_SAVINGS_SCHEMA,
        G2_TRANSACTIONS_SCHEMA,
        CUSTOMERS_SCHEMA,
        LOANS_SCHEMA,
        PERFECT_CLIENTS_SCHEMA,
    )
    matching_schema = next(
        (candidate for candidate in known_schemas if set(candidate.required) == set(required_columns)),
        DataSchema(file_label, frozenset(required_columns)),
    )
    result = validate_dataframe_schema(dataframe, matching_schema, file_label)
    return list(result.missing)


def remove_export_index_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return pd.DataFrame()
    frame = dataframe.copy()
    mask = frame.columns.astype(str).str.match(r"^Unnamed(:|$)", na=False)
    return frame.loc[:, ~mask].copy()


def _normalize_common_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = remove_export_index_columns(dataframe)
    if frame.empty:
        return frame

    frame.columns = [_normalize_column_name(column) for column in frame.columns]
    for column in TEXT_COLUMNS:
        if column in frame.columns:
            frame[column] = clean_text(frame[column])
    for column in ["customer_id", "id", "reference_id", "ref_no", "loan_id"]:
        if column in frame.columns:
            frame[column] = clean_identifier(frame[column])
    for column in ["msisdn", "msisdn1"]:
        if column in frame.columns:
            frame[column] = normalize_phone(frame[column])
    if "currency_code" in frame.columns:
        frame["currency_code"] = clean_text(frame["currency_code"]).str.upper()
    if "account_type" in frame.columns:
        frame["account_type"] = clean_text(frame["account_type"]).str.upper()
    for column in DATE_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in NUMERIC_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def prepare_transactions(dataframe: pd.DataFrame) -> pd.DataFrame:
    frame = _normalize_common_columns(dataframe)
    for column in ["dr", "cr", "bal_before", "bal_after"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    if "created_at" in frame.columns:
        frame = frame.sort_values(["created_at", "id"], na_position="last").reset_index(drop=True)
    return frame


def prepare_current_savings(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    frame = _normalize_common_columns(dataframe if dataframe is not None else pd.DataFrame())
    if "balance" in frame.columns:
        frame["balance"] = pd.to_numeric(frame["balance"], errors="coerce").fillna(0.0)
    return frame


def prepare_fixed_savings(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    frame = _normalize_common_columns(dataframe if dataframe is not None else pd.DataFrame())
    if "balance" in frame.columns:
        frame["balance"] = pd.to_numeric(frame["balance"], errors="coerce").fillna(0.0)
    if "created_at" not in frame.columns and "date_approved" in frame.columns:
        frame["created_at"] = frame["date_approved"]
    return frame


def build_large_dat_summary(
    fixed_savings: pd.DataFrame | None,
    *,
    percentile: float = 0.90,
    as_of_date: Any | None = None,
) -> dict[str, pd.DataFrame]:
    """Classe les clients DAT par devise et identifie les encours les plus eleves."""
    empty_result = {"clients": pd.DataFrame(), "portefeuille": pd.DataFrame()}
    if not isinstance(fixed_savings, pd.DataFrame) or fixed_savings.empty:
        return empty_result

    required = {"customer_id", "currency_code", "balance"}
    if not required.issubset(fixed_savings.columns):
        return empty_result

    percentile = min(max(float(percentile), 0.0), 1.0)
    reporting_date = pd.Timestamp(as_of_date if as_of_date is not None else pd.Timestamp.now()).normalize()
    dat = fixed_savings.copy()
    dat["customer_id"] = clean_identifier(dat["customer_id"])
    dat["currency_code"] = clean_text(dat["currency_code"]).str.upper()
    dat["balance"] = pd.to_numeric(dat["balance"], errors="coerce").fillna(0.0)
    dat = dat.loc[
        dat["customer_id"].ne("")
        & dat["currency_code"].ne("")
        & dat["balance"].gt(0)
    ].copy()
    if dat.empty:
        return empty_result

    for column in ["date_approved", "maturity_date"]:
        dat[column] = pd.to_datetime(dat.get(column, pd.Series(pd.NaT, index=dat.index)), errors="coerce")
    for column in ["Nom_client", "msisdn", "product_name", "account_type"]:
        if column not in dat.columns:
            dat[column] = pd.NA

    dat["dat_echu"] = dat["maturity_date"].notna() & dat["maturity_date"].lt(reporting_date)
    dat["echeance_30j"] = (
        dat["maturity_date"].notna()
        & dat["maturity_date"].ge(reporting_date)
        & dat["maturity_date"].le(reporting_date + pd.Timedelta(days=30))
    )
    dat["solde_dat_echu"] = dat["balance"].where(dat["dat_echu"], 0.0)
    dat["solde_echeance_30j"] = dat["balance"].where(dat["echeance_30j"], 0.0)

    clients = (
        dat.groupby(["customer_id", "currency_code"], as_index=False, dropna=False)
        .agg(
            Nom_client=("Nom_client", concat_unique),
            telephone=("msisdn", concat_unique),
            produits_dat=("product_name", concat_unique),
            types_comptes_dat=("account_type", concat_unique),
            nb_comptes_dat=("balance", "size"),
            solde_dat_total=("balance", "sum"),
            plus_fort_dat=("balance", "max"),
            solde_dat_echu=("solde_dat_echu", "sum"),
            solde_echeance_30j=("solde_echeance_30j", "sum"),
            nb_dat_echus=("dat_echu", "sum"),
            nb_echeances_30j=("echeance_30j", "sum"),
            date_premier_dat=("date_approved", "min"),
            date_dernier_dat=("date_approved", "max"),
            prochaine_echeance=("maturity_date", "min"),
        )
    )
    clients["rang_devise"] = (
        clients.groupby("currency_code")["solde_dat_total"]
        .rank(method="dense", ascending=False)
        .astype("int64")
    )
    clients["total_portefeuille_devise"] = clients.groupby("currency_code")["solde_dat_total"].transform("sum")
    clients["part_portefeuille_pct"] = (
        clients["solde_dat_total"]
        .div(clients["total_portefeuille_devise"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
    )
    clients["seuil_fort_dat"] = clients.groupby("currency_code")["solde_dat_total"].transform(
        lambda values: values.quantile(percentile)
    )
    clients["est_fort_dat"] = clients["solde_dat_total"].ge(clients["seuil_fort_dat"])
    clients = clients.sort_values(
        ["currency_code", "solde_dat_total", "customer_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    clients["part_cumulee_pct"] = clients.groupby("currency_code")["part_portefeuille_pct"].cumsum()

    portefeuille = (
        clients.groupby("currency_code", as_index=False, dropna=False)
        .agg(
            total_dat=("solde_dat_total", "sum"),
            nb_clients_dat=("customer_id", "nunique"),
            nb_comptes_dat=("nb_comptes_dat", "sum"),
            solde_median_client=("solde_dat_total", "median"),
            seuil_fort_dat=("seuil_fort_dat", "first"),
            nb_clients_forts=("est_fort_dat", "sum"),
            solde_dat_echu=("solde_dat_echu", "sum"),
            solde_echeance_30j=("solde_echeance_30j", "sum"),
        )
    )
    concentration = (
        clients.loc[clients["est_fort_dat"]]
        .groupby("currency_code", as_index=False)["solde_dat_total"]
        .sum()
        .rename(columns={"solde_dat_total": "total_clients_forts"})
    )
    portefeuille = portefeuille.merge(concentration, on="currency_code", how="left")
    portefeuille["total_clients_forts"] = portefeuille["total_clients_forts"].fillna(0.0)
    portefeuille["concentration_clients_forts_pct"] = (
        portefeuille["total_clients_forts"]
        .div(portefeuille["total_dat"].replace(0, pd.NA))
        .mul(100)
        .fillna(0.0)
    )
    portefeuille["percentile_fort_dat"] = percentile * 100
    portefeuille["date_analyse"] = reporting_date
    return {"clients": clients, "portefeuille": portefeuille}


def prepare_loans(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    frame = _normalize_common_columns(dataframe if dataframe is not None else pd.DataFrame())
    if not frame.empty and "outstanding_principal" in frame.columns and "outstanding_principle" not in frame.columns:
        frame["outstanding_principle"] = frame["outstanding_principal"]
    for column in NUMERIC_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    return frame


def prepare_customers(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    frame = remove_export_index_columns(dataframe if dataframe is not None else pd.DataFrame())
    frame = _normalize_common_columns(frame)
    return frame


def prepare_perfect_clients(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    """Prepare l'export 122 Perfect sans transformer les numeros invalides en cles de jointure."""
    frame = remove_export_index_columns(dataframe if dataframe is not None else pd.DataFrame())
    if frame.empty:
        return frame

    frame = frame.rename(columns={column: _normalize_business_column_key(column) for column in frame.columns}).copy()
    for column in ["id_client", "code_client", "num_manuel"]:
        if column in frame.columns:
            frame[column] = clean_identifier(frame[column])
    for column in [
        "nom_complet",
        "phone_brut",
        "phone_prefixe",
        "statut_phone",
        "commentaire_phone",
        "type_client",
        "categorie_client",
        "gestionnaire",
        "collecteur",
    ]:
        if column in frame.columns:
            frame[column] = clean_text(frame[column])

    source_phone = frame.get("phone_prefixe", pd.Series(pd.NA, index=frame.index, dtype="string"))
    frame["phone_prefixe_source"] = source_phone
    normalized_phone = normalize_phone(source_phone)
    valid_phone = normalized_phone.astype("string").str.fullmatch(r"243[89]\d{8}", na=False)
    frame["phone_prefixe"] = normalized_phone.where(valid_phone, pd.NA)
    frame["source_perfect"] = "Perfect"
    return frame.reset_index(drop=True)


def _mpesa_identity_source(
    dataframe: pd.DataFrame | None,
    *,
    source: str,
    system: str,
    phone_column: str,
    customer_column: str | None = "customer_id",
    name_column: str = "Nom_client",
) -> pd.DataFrame:
    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return pd.DataFrame()
    frame = dataframe.copy()
    phone_values = frame.get(phone_column, pd.Series(pd.NA, index=frame.index, dtype="string"))
    result = pd.DataFrame(index=frame.index)
    result["phone_prefixe"] = normalize_phone(phone_values)
    valid_phone = result["phone_prefixe"].astype("string").str.fullmatch(r"243[89]\d{8}", na=False)
    result["phone_prefixe"] = result["phone_prefixe"].where(valid_phone, pd.NA)
    result["customer_id_turbo"] = (
        clean_identifier(frame[customer_column])
        if customer_column and customer_column in frame.columns
        else ""
    )
    result["nom_client_mpesa"] = (
        clean_text(frame[name_column]) if name_column in frame.columns else ""
    )
    result["source_mpesa"] = source
    result["systeme_mpesa"] = system
    fallback = (
        result["customer_id_turbo"].where(result["customer_id_turbo"].ne(""), frame.index.astype("string"))
    )
    result["cle_rapprochement"] = result["phone_prefixe"].astype("string")
    no_phone = result["phone_prefixe"].isna()
    result.loc[no_phone, "cle_rapprochement"] = (
        "SANS-TELEPHONE::" + system + "::" + fallback.loc[no_phone].astype("string")
    )
    return result.reset_index(drop=True)


def _build_mpesa_identity_population(prepared: MpesaPreparedData) -> pd.DataFrame:
    frames = [
        _mpesa_identity_source(prepared.transactions, source="Turbo - Transactions", system="Turbo", phone_column="msisdn1"),
        _mpesa_identity_source(prepared.customers, source="Turbo - Clients", system="Turbo", phone_column="msisdn1"),
        _mpesa_identity_source(prepared.current_savings, source="Turbo - Epargne courante", system="Turbo", phone_column="msisdn"),
        _mpesa_identity_source(prepared.fixed_savings, source="Turbo - DAT", system="Turbo", phone_column="msisdn"),
        _mpesa_identity_source(prepared.loans, source="Turbo - Credits", system="Turbo", phone_column="msisdn1"),
        _mpesa_identity_source(
            prepared.g2_transactions,
            source="G2 - Transactions",
            system="G2",
            phone_column="phone_prefixe",
            customer_column=None,
        ),
    ]
    population = concat_frames_stable(frames)
    if population.empty:
        return pd.DataFrame()
    population["present_dans_turbo"] = population["systeme_mpesa"].astype("string").eq("Turbo")
    population["present_dans_g2"] = population["systeme_mpesa"].astype("string").eq("G2")
    output_columns = [
        "cle_rapprochement", "phone_prefixe", "customer_ids_turbo", "noms_clients_mpesa",
        "systemes_mpesa", "sources_mpesa", "present_dans_turbo", "present_dans_g2",
        "nb_lignes_sources_mpesa",
    ]
    key_counts = population.groupby("cle_rapprochement", dropna=False)["cle_rapprochement"].transform("size")
    unique_rows = population.loc[
        key_counts.eq(1),
        [
            "cle_rapprochement", "phone_prefixe", "customer_id_turbo", "nom_client_mpesa",
            "systeme_mpesa", "source_mpesa", "present_dans_turbo", "present_dans_g2",
        ],
    ].rename(
        columns={
            "customer_id_turbo": "customer_ids_turbo",
            "nom_client_mpesa": "noms_clients_mpesa",
            "systeme_mpesa": "systemes_mpesa",
            "source_mpesa": "sources_mpesa",
        }
    )
    unique_rows["nb_lignes_sources_mpesa"] = 1

    duplicates = population.loc[key_counts.gt(1)].copy()
    if duplicates.empty:
        return unique_rows[output_columns].reset_index(drop=True)
    duplicate_summary = (
        duplicates.groupby("cle_rapprochement", as_index=False, dropna=False)
        .agg(
            phone_prefixe=("phone_prefixe", first_non_empty),
            customer_ids_turbo=("customer_id_turbo", concat_unique),
            noms_clients_mpesa=("nom_client_mpesa", concat_unique),
            systemes_mpesa=("systeme_mpesa", concat_unique),
            sources_mpesa=("source_mpesa", concat_unique),
            present_dans_turbo=("present_dans_turbo", "max"),
            present_dans_g2=("present_dans_g2", "max"),
            nb_lignes_sources_mpesa=("source_mpesa", "size"),
        )
    )
    return concat_frames_stable([unique_rows[output_columns], duplicate_summary[output_columns]]).reset_index(drop=True)


def _build_mpesa_operation_detail(prepared: MpesaPreparedData) -> pd.DataFrame:
    blocks: list[pd.DataFrame] = []
    transactions = prepared.transactions
    if isinstance(transactions, pd.DataFrame) and not transactions.empty:
        turbo = transactions.copy()
        if "account_type" in turbo.columns and turbo["account_type"].astype("string").eq("MPESA ACCOUNT").any():
            turbo = turbo.loc[turbo["account_type"].astype("string").eq("MPESA ACCOUNT")].copy()
        turbo["phone_prefixe"] = normalize_phone(turbo.get("msisdn1", pd.Series(pd.NA, index=turbo.index)))
        valid_phone = turbo["phone_prefixe"].astype("string").str.fullmatch(r"243[89]\d{8}", na=False)
        turbo["phone_prefixe"] = turbo["phone_prefixe"].where(valid_phone, pd.NA)
        turbo["customer_id_turbo"] = clean_identifier(
            turbo.get("customer_id", pd.Series("", index=turbo.index))
        )
        turbo["nom_client_mpesa"] = clean_text(
            turbo.get("Nom_client", pd.Series("", index=turbo.index))
        )
        turbo["date_operation"] = pd.to_datetime(turbo.get("created_at"), errors="coerce")
        turbo["operation_reference"] = clean_identifier(
            turbo.get("ref_no", pd.Series("", index=turbo.index))
        )
        fallback_reference = clean_identifier(
            turbo.get("reference_id", pd.Series("", index=turbo.index))
        )
        turbo["operation_reference"] = turbo["operation_reference"].where(
            turbo["operation_reference"].ne(""), fallback_reference
        )
        missing_reference = turbo["operation_reference"].eq("")
        turbo.loc[missing_reference, "operation_reference"] = (
            "TURBO-LIGNE-" + turbo.index[missing_reference].astype("string")
        )
        turbo["currency_code"] = clean_text(
            turbo.get("currency_code", pd.Series("", index=turbo.index))
        ).str.upper()
        turbo["entree_mpesa"] = numeric_column(turbo, "cr")
        turbo["sortie_mpesa"] = numeric_column(turbo, "dr")
        turbo["mouvement_net_mpesa"] = turbo["entree_mpesa"] - turbo["sortie_mpesa"]
        turbo["description_operation"] = clean_text(
            turbo.get("description", pd.Series("", index=turbo.index))
        )
        turbo["type_compte"] = clean_text(
            turbo.get("account_type", pd.Series("", index=turbo.index))
        )
        turbo["source_operation"] = "Turbo"
        turbo["statut_operation"] = ""
        group_keys = [
            "phone_prefixe", "customer_id_turbo", "nom_client_mpesa", "date_operation",
            "operation_reference", "currency_code", "source_operation", "statut_operation",
        ]
        turbo_detail = (
            turbo.groupby(group_keys, as_index=False, dropna=False)
            .agg(
                description_operation=("description_operation", concat_unique),
                type_compte=("type_compte", concat_unique),
                entree_mpesa=("entree_mpesa", "sum"),
                sortie_mpesa=("sortie_mpesa", "sum"),
                mouvement_net_mpesa=("mouvement_net_mpesa", "sum"),
                nb_lignes_source=("operation_reference", "size"),
            )
        )
        turbo_detail["montant_operation"] = turbo_detail["mouvement_net_mpesa"].abs()
        turbo_detail["sens_operation"] = np.select(
            [turbo_detail["mouvement_net_mpesa"].gt(0), turbo_detail["mouvement_net_mpesa"].lt(0)],
            ["Entree M-PESA", "Sortie M-PESA"],
            default="Mouvement nul",
        )
        turbo_detail["type_operation"] = turbo_detail.apply(
            lambda row: classify_mpesa_operation(
                row["description_operation"], row["type_compte"], row["mouvement_net_mpesa"]
            ),
            axis=1,
        )
        blocks.append(turbo_detail)

    if isinstance(prepared.g2_transactions, pd.DataFrame) and not prepared.g2_transactions.empty:
        g2_report = build_g2_daily_savings_report(prepared).get("detail", pd.DataFrame())
        if not g2_report.empty:
            g2 = g2_report.copy()
            g2["phone_prefixe"] = normalize_phone(g2.get("phone_prefixe", pd.Series(pd.NA, index=g2.index)))
            valid_phone = g2["phone_prefixe"].astype("string").str.fullmatch(r"243[89]\d{8}", na=False)
            g2["phone_prefixe"] = g2["phone_prefixe"].where(valid_phone, pd.NA)
            g2["customer_id_turbo"] = ""
            g2["nom_client_mpesa"] = clean_text(g2.get("Nom_client", pd.Series("", index=g2.index)))
            g2["date_operation"] = pd.to_datetime(g2.get("date"), errors="coerce")
            g2["operation_reference"] = clean_identifier(g2.get("receipt_no", pd.Series("", index=g2.index)))
            g2["currency_code"] = clean_text(g2.get("currency_code", pd.Series("", index=g2.index))).str.upper()
            g2["type_operation"] = clean_text(g2.get("details_rapport", pd.Series("", index=g2.index)))
            g2["description_operation"] = g2["type_operation"]
            g2["type_compte"] = "G2"
            g2["montant_operation"] = numeric_column(g2, "montant").abs()
            g2["entree_mpesa"] = np.nan
            g2["sortie_mpesa"] = np.nan
            g2["mouvement_net_mpesa"] = np.nan
            g2["sens_operation"] = clean_text(
                g2.get("sens_flux", pd.Series("Indetermine", index=g2.index))
            ).map({"Entree": "Entree G2", "Sortie": "Sortie G2"}).fillna("Flux G2 a verifier")
            g2["source_operation"] = "G2"
            g2["statut_operation"] = clean_text(
                g2.get("transaction_status", pd.Series("", index=g2.index))
            )
            g2["nb_lignes_source"] = 1
            blocks.append(
                g2[[
                    "phone_prefixe", "customer_id_turbo", "nom_client_mpesa", "date_operation",
                    "operation_reference", "currency_code", "type_operation", "description_operation",
                    "type_compte", "montant_operation", "entree_mpesa", "sortie_mpesa",
                    "mouvement_net_mpesa", "sens_operation", "source_operation",
                    "statut_operation", "nb_lignes_source",
                ]]
            )

    detail = concat_frames_stable(blocks)
    if detail.empty:
        return detail
    detail["cle_rapprochement"] = detail["phone_prefixe"].astype("string")
    no_phone = detail["phone_prefixe"].isna()
    fallback = detail["customer_id_turbo"].astype("string").where(
        detail["customer_id_turbo"].astype("string").ne(""), detail.index.astype("string")
    )
    detail.loc[no_phone, "cle_rapprochement"] = (
        "SANS-TELEPHONE::" + detail.loc[no_phone, "source_operation"].astype("string") + "::" + fallback.loc[no_phone]
    )
    return detail.sort_values(["date_operation", "source_operation"], na_position="last").reset_index(drop=True)


def _aggregate_perfect_clients(perfect_clients: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(perfect_clients, pd.DataFrame) or perfect_clients.empty or "phone_prefixe" not in perfect_clients.columns:
        return pd.DataFrame()
    perfect = perfect_clients.dropna(subset=["phone_prefixe"]).copy()
    if perfect.empty:
        return pd.DataFrame()
    for column in [
        "id_client", "code_client", "num_manuel", "nom_complet", "statut_phone",
        "commentaire_phone", "type_client", "categorie_client", "gestionnaire", "collecteur",
    ]:
        if column not in perfect.columns:
            perfect[column] = ""
    output_map = {
        "id_client": "ids_clients_perfect",
        "code_client": "codes_clients_perfect",
        "num_manuel": "numeros_manuels_perfect",
        "nom_complet": "noms_clients_perfect",
        "statut_phone": "statuts_phone_perfect",
        "commentaire_phone": "commentaires_phone_perfect",
        "type_client": "types_clients_perfect",
        "categorie_client": "categories_clients_perfect",
        "gestionnaire": "gestionnaires_perfect",
        "collecteur": "collecteurs_perfect",
    }
    output_columns = ["phone_prefixe", "nb_clients_perfect", *output_map.values()]
    phone_counts = perfect.groupby("phone_prefixe", dropna=False)["phone_prefixe"].transform("size")

    # La plupart des numeros sont uniques : les copier directement evite des milliers
    # d'appels Python groupby inutiles. Seuls les numeros partages sont agreges.
    unique_rows = perfect.loc[phone_counts.eq(1), ["phone_prefixe", *output_map]].copy()
    unique_rows = unique_rows.rename(columns=output_map)
    unique_rows["nb_clients_perfect"] = 1
    unique_rows = unique_rows[output_columns]

    duplicate_rows = perfect.loc[phone_counts.gt(1)].copy()
    if duplicate_rows.empty:
        return unique_rows.reset_index(drop=True)
    duplicate_summary = (
        duplicate_rows.groupby("phone_prefixe", as_index=False, dropna=False)
        .agg(
            nb_clients_perfect=("id_client", lambda values: max(1, clean_identifier(values).replace("", pd.NA).nunique())),
            ids_clients_perfect=("id_client", concat_unique),
            codes_clients_perfect=("code_client", concat_unique),
            numeros_manuels_perfect=("num_manuel", concat_unique),
            noms_clients_perfect=("nom_complet", concat_unique),
            statuts_phone_perfect=("statut_phone", concat_unique),
            commentaires_phone_perfect=("commentaire_phone", concat_unique),
            types_clients_perfect=("type_client", concat_unique),
            categories_clients_perfect=("categorie_client", concat_unique),
            gestionnaires_perfect=("gestionnaire", concat_unique),
            collecteurs_perfect=("collecteur", concat_unique),
        )
    )
    return concat_frames_stable([unique_rows, duplicate_summary[output_columns]]).reset_index(drop=True)


def _perfect_match_status(frame: pd.DataFrame, perfect_available: bool) -> pd.Series:
    if not perfect_available:
        status = pd.Series("Fichier Perfect absent", index=frame.index, dtype="string")
    else:
        matches = numeric_column(frame, "nb_clients_perfect").astype(int)
        status = pd.Series(
            np.select(
                [matches.eq(1), matches.gt(1)],
                ["Trouve dans Perfect - correspondance unique", "Trouve dans Perfect - plusieurs clients"],
                default="Non trouve dans Perfect",
            ),
            index=frame.index,
            dtype="string",
        )
    return status.where(frame["phone_prefixe"].notna(), "Telephone M-PESA inexploitable")


def _add_system_presence_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les indicateurs de présence Turbo, G2 et Perfect sans modifier le grain."""
    output = frame.copy()
    turbo = (
        output["present_dans_turbo"].astype("boolean").fillna(False).astype(bool)
        if "present_dans_turbo" in output.columns
        else pd.Series(False, index=output.index)
    )
    g2 = (
        output["present_dans_g2"].astype("boolean").fillna(False).astype(bool)
        if "present_dans_g2" in output.columns
        else pd.Series(False, index=output.index)
    )
    perfect = numeric_column(output, "nb_clients_perfect").gt(0)
    output["present_dans_turbo"] = turbo
    output["present_dans_g2"] = g2
    output["present_dans_perfect"] = perfect
    output["present_dans_les_3_systemes"] = turbo & g2 & perfect
    output["statut_presence_systemes"] = np.select(
        [
            turbo & g2 & perfect,
            turbo & g2,
            turbo & perfect,
            g2 & perfect,
            turbo,
            g2,
            perfect,
        ],
        [
            "Present dans G2, Turbo et Perfect",
            "Present dans G2 et Turbo - absent Perfect",
            "Present dans Turbo et Perfect - absent G2",
            "Present dans G2 et Perfect - absent Turbo",
            "Present dans Turbo uniquement",
            "Present dans G2 uniquement",
            "Present dans Perfect uniquement",
        ],
        default="Presence systeme indeterminee",
    )
    return output


def build_perfect_client_crosscheck(prepared: MpesaPreparedData) -> dict[str, pd.DataFrame]:
    """Croise la population M-PESA avec Perfect, une seule ligne de synthese par telephone."""
    population = _build_mpesa_identity_population(prepared)
    operations = _build_mpesa_operation_detail(prepared)
    perfect_by_phone = _aggregate_perfect_clients(prepared.perfect_clients)
    perfect_available = isinstance(prepared.perfect_clients, pd.DataFrame) and not prepared.perfect_clients.empty
    if population.empty:
        return {
            "synthese": pd.DataFrame(),
            "operations": operations,
            "perfect_agrege": perfect_by_phone,
            "clients_perfect_dans_mpesa": pd.DataFrame(),
            "clients_perfect_dans_turbo": pd.DataFrame(),
            "clients_perfect_dans_turbo_et_mpesa": pd.DataFrame(),
            "clients_trois_systemes": pd.DataFrame(),
        }

    if not operations.empty:
        operation_summary = (
            operations.groupby("cle_rapprochement", as_index=False, dropna=False)
            .agg(
                types_operations_mpesa=("type_operation", concat_unique),
                sources_operations=("source_operation", concat_unique),
                devises_operations=("currency_code", concat_unique),
                premiere_operation=("date_operation", "min"),
                derniere_operation=("date_operation", "max"),
                nombre_operations_observees=("operation_reference", "size"),
                references_operations=("operation_reference", concat_unique),
            )
        )
        turbo_counts = operations["source_operation"].eq("Turbo").groupby(operations["cle_rapprochement"]).sum()
        g2_counts = operations["source_operation"].eq("G2").groupby(operations["cle_rapprochement"]).sum()
        operation_summary["nombre_operations_turbo"] = operation_summary["cle_rapprochement"].map(turbo_counts).fillna(0).astype(int)
        operation_summary["nombre_operations_g2"] = operation_summary["cle_rapprochement"].map(g2_counts).fillna(0).astype(int)
        summary = population.merge(operation_summary, on="cle_rapprochement", how="left")
    else:
        summary = population.copy()
        summary["nombre_operations_observees"] = 0
        summary["nombre_operations_turbo"] = 0
        summary["nombre_operations_g2"] = 0

    if not perfect_by_phone.empty:
        summary = summary.merge(perfect_by_phone, on="phone_prefixe", how="left")
    summary["statut_rapprochement_perfect"] = _perfect_match_status(summary, perfect_available)
    summary["nb_clients_perfect"] = numeric_column(summary, "nb_clients_perfect").astype(int)
    summary["trouve_dans_perfect"] = summary["nb_clients_perfect"].gt(0)
    summary = _add_system_presence_columns(summary)

    if not operations.empty:
        identity_columns = [
            "cle_rapprochement", "customer_ids_turbo", "noms_clients_mpesa",
            "systemes_mpesa", "sources_mpesa", "present_dans_turbo", "present_dans_g2",
        ]
        operations = operations.merge(summary[identity_columns], on="cle_rapprochement", how="left")
        if not perfect_by_phone.empty:
            operations = operations.merge(perfect_by_phone, on="phone_prefixe", how="left")
        operations["statut_rapprochement_perfect"] = _perfect_match_status(operations, perfect_available)
        operations["nb_clients_perfect"] = numeric_column(operations, "nb_clients_perfect").astype(int)
        operations = _add_system_presence_columns(operations)

    summary = summary.sort_values(
        ["statut_rapprochement_perfect", "phone_prefixe"], na_position="last"
    ).reset_index(drop=True)
    clients_perfect_dans_mpesa = summary.loc[
        summary["present_dans_g2"] & summary["present_dans_perfect"]
    ].reset_index(drop=True)
    clients_perfect_dans_turbo = summary.loc[
        summary["present_dans_turbo"] & summary["present_dans_perfect"]
    ].reset_index(drop=True)
    clients_perfect_dans_turbo_et_mpesa = summary.loc[
        summary["present_dans_les_3_systemes"]
    ].reset_index(drop=True)
    return {
        "synthese": summary,
        "operations": operations,
        "perfect_agrege": perfect_by_phone,
        "clients_perfect_dans_mpesa": clients_perfect_dans_mpesa,
        "clients_perfect_dans_turbo": clients_perfect_dans_turbo,
        "clients_perfect_dans_turbo_et_mpesa": clients_perfect_dans_turbo_et_mpesa,
        "clients_trois_systemes": clients_perfect_dans_turbo_et_mpesa,
    }


def _parse_money_series(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype("string")
        .fillna("")
        .str.replace(r"[^\d,\.\-]", "", regex=True)
        .str.replace(",", "", regex=False)
        .replace("", pd.NA)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def numeric_column(frame: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    if isinstance(frame, pd.DataFrame) and column in frame.columns:
        return pd.to_numeric(frame[column], errors="coerce").fillna(default)
    index = frame.index if isinstance(frame, pd.DataFrame) else None
    return pd.Series(default, index=index, dtype="float64")


def _extract_phone_from_opposite_party(series: pd.Series) -> pd.Series:
    raw_phone = (
        series.astype("string")
        .fillna("")
        .str.split("-", n=1)
        .str[0]
        .str.replace(r"[\r\n\t]+", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return raw_phone.replace({"": pd.NA})


def _extract_customer_name_from_opposite_party(series: pd.Series) -> pd.Series:
    customer_name = (
        series.astype("string")
        .fillna("")
        .str.split("-", n=1)
        .str[1]
        .str.replace(r"[\r\n\t]+", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return customer_name.replace({"": pd.NA})


def prepare_g2_transactions(dataframe: pd.DataFrame | None) -> pd.DataFrame:
    frame = remove_export_index_columns(dataframe if dataframe is not None else pd.DataFrame())
    if frame.empty:
        return frame

    rename_map: dict[object, str] = {}
    for column in frame.columns:
        key = _normalize_business_column_key(column)
        standard = {
            "receipt_no": "receipt_no",
            "receipt_no_": "receipt_no",
            "completion_time": "completion_time",
            "initiation_time": "initiation_time",
            "details": "details",
            "opposite_party": "opposite_party",
            "transaction_status": "transaction_status",
            "currency": "currency_code",
            "transaction_amount": "transaction_amount",
            "paid_in": "paid_in",
            "withdrawn": "withdrawn",
            "balance": "balance",
            "operation": "operation",
            "reason_type": "reason_type",
            "linked_transaction_id": "linked_transaction_id",
        }.get(key)
        rename_map[column] = standard or key
    frame = frame.rename(columns=rename_map).copy()

    for column in ["receipt_no", "details", "opposite_party", "transaction_status", "currency_code", "operation", "reason_type"]:
        if column in frame.columns:
            frame[column] = clean_text(frame[column])
    if "receipt_no" in frame.columns:
        frame["receipt_no"] = clean_identifier(frame["receipt_no"])
    if "currency_code" in frame.columns:
        frame["currency_code"] = clean_text(frame["currency_code"]).str.upper()
    for column in ["completion_time", "initiation_time"]:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce", format="mixed", dayfirst=True)
    if "opposite_party" in frame.columns:
        frame["phone"] = _extract_phone_from_opposite_party(frame["opposite_party"])
        frame["phone_prefixe"] = normalize_phone(frame["phone"])
        frame["Nom_client"] = _extract_customer_name_from_opposite_party(frame["opposite_party"])
    else:
        frame["phone"] = pd.NA
        frame["phone_prefixe"] = pd.NA
        frame["Nom_client"] = pd.NA
    for column in ["transaction_amount", "paid_in", "withdrawn", "balance"]:
        if column in frame.columns:
            frame[f"{column}_numeric"] = _parse_money_series(frame[column])

    original_amount = frame.get("transaction_amount_numeric", pd.Series(np.nan, index=frame.index, dtype="float64"))
    paid_in = frame.get("paid_in_numeric", pd.Series(np.nan, index=frame.index, dtype="float64"))
    withdrawn = frame.get("withdrawn_numeric", pd.Series(np.nan, index=frame.index, dtype="float64"))
    paid_in_available = paid_in.notna() & (paid_in.ne(0) | withdrawn.isna())
    withdrawn_available = withdrawn.notna() & ~paid_in_available
    derived_amount = paid_in.where(paid_in_available, withdrawn)
    frame["transaction_amount_numeric"] = original_amount.where(original_amount.notna(), derived_amount)
    frame["transaction_amount_source"] = np.select(
        [original_amount.notna(), original_amount.isna() & paid_in_available, original_amount.isna() & withdrawn_available],
        ["Transaction Amount", "Paid In", "Withdrawn"],
        default="Montant absent",
    )
    paid_in_non_zero = paid_in.notna() & paid_in.ne(0)
    withdrawn_non_zero = withdrawn.notna() & withdrawn.ne(0)
    both_directions = paid_in_non_zero & withdrawn_non_zero
    fallback_amount = frame["transaction_amount_numeric"]
    frame["sens_flux"] = np.select(
        [
            both_directions,
            withdrawn_non_zero,
            paid_in_non_zero,
            fallback_amount.lt(0).fillna(False),
            fallback_amount.gt(0).fillna(False),
        ],
        ["A verifier", "Sortie", "Entree", "Sortie", "Entree"],
        default="Indetermine",
    )
    absolute_amount = fallback_amount.abs()
    frame["montant_entree"] = absolute_amount.where(frame["sens_flux"].eq("Entree"), 0.0)
    frame["montant_sortie"] = absolute_amount.where(frame["sens_flux"].eq("Sortie"), 0.0)
    frame["type_operation_g2"] = frame.apply(classify_g2_business_operation, axis=1)
    if "transaction_amount" not in frame.columns:
        frame["transaction_amount"] = derived_amount
    else:
        frame["transaction_amount"] = frame["transaction_amount"].where(original_amount.notna(), derived_amount)
    frame["source_g2"] = "G2"
    sort_columns = [column for column in ["completion_time", "receipt_no"] if column in frame.columns]
    if sort_columns:
        frame = frame.sort_values(sort_columns, na_position="last").reset_index(drop=True)
    return frame


def filter_g2_transactions_by_completion_time(
    dataframe: pd.DataFrame | None,
    start_date: Any | None = None,
    end_date: Any | None = None,
    start_time: Any | None = None,
    end_time: Any | None = None,
) -> pd.DataFrame:
    """Filtre G2 sur Completion Time avec des bornes de date et d'heure inclusives."""
    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return pd.DataFrame() if dataframe is None else dataframe.copy()
    if "completion_time" not in dataframe.columns:
        return dataframe.copy()

    frame = dataframe.copy()
    completion_time = pd.to_datetime(frame["completion_time"], errors="coerce")
    mask = completion_time.notna()
    if start_date is not None:
        start_bound = pd.Timestamp(start_date).normalize()
        if start_time is not None:
            start_bound += pd.Timedelta(
                hours=start_time.hour,
                minutes=start_time.minute,
                seconds=start_time.second,
                microseconds=start_time.microsecond,
            )
        mask &= completion_time.ge(start_bound)
    if end_date is not None:
        end_bound = pd.Timestamp(end_date).normalize()
        if end_time is None:
            mask &= completion_time.lt(end_bound + pd.Timedelta(days=1))
        else:
            end_bound += pd.Timedelta(
                hours=end_time.hour,
                minutes=end_time.minute,
                seconds=end_time.second,
                microseconds=end_time.microsecond,
            )
            mask &= completion_time.le(end_bound)
    return frame.loc[mask].reset_index(drop=True)


def filter_g2_transactions_by_direction(
    dataframe: pd.DataFrame | None,
    directions: str | Iterable[str] | None = None,
) -> pd.DataFrame:
    """Filtre G2 sur Entree/Sortie; None conserve tous les sens et les anomalies."""
    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return pd.DataFrame() if dataframe is None else dataframe.copy()
    if directions is None or "sens_flux" not in dataframe.columns:
        return dataframe.copy()

    requested = [directions] if isinstance(directions, str) else list(directions)
    canonical = {
        "entree": "Entree",
        "entrees": "Entree",
        "sortie": "Sortie",
        "sorties": "Sortie",
    }
    selected = {canonical.get(normalize_label(value), str(value).strip()) for value in requested}
    selected.discard("")
    if not selected:
        return dataframe.copy()
    return dataframe.loc[dataframe["sens_flux"].astype("string").isin(selected)].reset_index(drop=True)


def enrich_turbo_with_g2_customer_names(
    dataframe: pd.DataFrame | None,
    g2_transactions: pd.DataFrame | None,
    *,
    phone_column: str,
    reference_column: str | None = None,
) -> pd.DataFrame:
    """Ajoute le nom G2 a une source Turbo, par telephone puis par reference."""
    result = dataframe.copy() if isinstance(dataframe, pd.DataFrame) else pd.DataFrame()
    if result.empty:
        return result

    existing_name = result.get("Nom_client", pd.Series(pd.NA, index=result.index)).copy()
    has_existing_name = existing_name.astype("string").fillna("").str.strip().ne("")
    result["Nom_client"] = existing_name
    result["mode_rapprochement_nom_client"] = np.where(has_existing_name, "Nom existant Turbo", "Fichier G2 absent")
    if not isinstance(g2_transactions, pd.DataFrame) or g2_transactions.empty or "Nom_client" not in g2_transactions.columns:
        return result

    g2 = g2_transactions.copy()
    g2["__phone_key"] = normalize_phone(
        g2.get("phone_prefixe", g2.get("phone", pd.Series("", index=g2.index)))
    )
    g2["__receipt_key"] = clean_identifier(g2.get("receipt_no", pd.Series("", index=g2.index)))
    g2["Nom_client"] = clean_text(g2["Nom_client"]).replace("", pd.NA)

    phone_rows = g2.dropna(subset=["__phone_key", "Nom_client"])
    if not phone_rows.empty:
        phone_lookup = (
            phone_rows.groupby("__phone_key", as_index=False, dropna=False)
            .agg(__nom_par_telephone=("Nom_client", concat_unique))
        )
    else:
        phone_lookup = pd.DataFrame(columns=["__phone_key", "__nom_par_telephone"])

    reference_rows = g2.loc[g2["__receipt_key"].ne("")].dropna(subset=["Nom_client"])
    if not reference_rows.empty:
        reference_lookup = (
            reference_rows.groupby("__receipt_key", as_index=False, dropna=False)
            .agg(__nom_par_reference=("Nom_client", concat_unique))
        )
    else:
        reference_lookup = pd.DataFrame(columns=["__receipt_key", "__nom_par_reference"])

    result["__row_order"] = np.arange(len(result))
    result["__nom_existant"] = existing_name
    result["__phone_key"] = normalize_phone(result.get(phone_column, pd.Series("", index=result.index)))
    result["__receipt_key"] = clean_identifier(
        result.get(reference_column, pd.Series("", index=result.index))
        if reference_column
        else pd.Series("", index=result.index)
    )
    result = result.merge(phone_lookup, on="__phone_key", how="left")
    result = result.merge(reference_lookup, on="__receipt_key", how="left")

    has_phone_name = result["__nom_par_telephone"].astype("string").fillna("").str.strip().ne("")
    has_reference_name = result["__nom_par_reference"].astype("string").fillna("").str.strip().ne("")
    matched_name = result["__nom_par_telephone"].where(has_phone_name, result["__nom_par_reference"])
    has_existing_name = result["__nom_existant"].astype("string").fillna("").str.strip().ne("")
    result["Nom_client"] = matched_name.where(has_phone_name | has_reference_name, result["__nom_existant"])
    result["mode_rapprochement_nom_client"] = np.select(
        [has_phone_name, ~has_phone_name & has_reference_name, ~has_phone_name & ~has_reference_name & has_existing_name],
        [f"Telephone G2 = {phone_column} Turbo", f"Receipt No G2 = {reference_column} Turbo", "Nom existant Turbo"],
        default="Nom G2 non rapproche",
    )
    return (
        result.sort_values("__row_order")
        .drop(columns=["__row_order", "__nom_existant", "__phone_key", "__receipt_key", "__nom_par_telephone", "__nom_par_reference"])
        .reset_index(drop=True)
    )


def enrich_transactions_with_g2_customer_names(
    transactions: pd.DataFrame | None,
    g2_transactions: pd.DataFrame | None,
) -> pd.DataFrame:
    return enrich_turbo_with_g2_customer_names(
        transactions,
        g2_transactions,
        phone_column="msisdn1",
        reference_column="ref_no",
    )


def build_load_report(files: dict[str, pd.DataFrame], missing: dict[str, list[str]]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label, frame in files.items():
        rows.append(
            {
                "fichier": label,
                "lignes": int(len(frame)) if isinstance(frame, pd.DataFrame) else 0,
                "colonnes": int(frame.shape[1]) if isinstance(frame, pd.DataFrame) else 0,
                "colonnes_manquantes": ", ".join(missing.get(label, [])),
                "statut": "OK" if not missing.get(label) else "Colonnes manquantes",
            }
        )
    return pd.DataFrame(rows)


def classify_mpesa_operation(descriptions: object, account_types: object = "", movement_net: float = 0.0) -> str:
    text = normalize_label(f"{descriptions} {account_types}")
    if "penalite" in text and "remboursement" in text:
        return "Remboursement avec penalite"
    if "montant pret" in text or "decaissement" in text or "loan disbur" in text:
        return "Decaissement de credit"
    if "remboursement" in text or "repayment" in text:
        return "Remboursement de credit"
    if "retrait vers m-pesa" in text or "retrait vers mpesa" in text:
        return "Entree M-PESA depuis epargne"
    if "m-pesa depot" in text or "mpesa depot" in text:
        return "Sortie M-PESA vers epargne"
    if "depot bloque" in text or "depot bloque" in text or "fixed savings" in text or "m-pesa compte" in text:
        return "Sortie M-PESA vers DAT" if movement_net < 0 else "Entree M-PESA depuis DAT"
    if movement_net > 0:
        return "Autre entree M-PESA"
    if movement_net < 0:
        return "Autre sortie M-PESA"
    return "Autre mouvement M-PESA"


def build_account_events(transactions_client: pd.DataFrame, account_type: str) -> pd.DataFrame:
    if transactions_client.empty or "account_type" not in transactions_client.columns:
        return pd.DataFrame(columns=["currency_code", "created_at", "variation", "references", "descriptions"])
    lines = transactions_client.loc[transactions_client["account_type"].eq(account_type)].copy()
    if lines.empty:
        return pd.DataFrame(columns=["currency_code", "created_at", "variation", "references", "descriptions"])
    lines["variation"] = pd.to_numeric(lines["bal_after"], errors="coerce").fillna(0) - pd.to_numeric(
        lines["bal_before"], errors="coerce"
    ).fillna(0)
    event_aggregations: dict[str, tuple[str, object]] = {
        "variation": ("variation", "sum"),
        "references": ("reference_id", concat_unique),
        "descriptions": ("description", concat_unique),
    }
    if "Nom_client" in lines.columns:
        event_aggregations["Nom_client"] = ("Nom_client", concat_unique)
    if "mode_rapprochement_nom_client" in lines.columns:
        event_aggregations["mode_rapprochement_nom_client"] = ("mode_rapprochement_nom_client", concat_unique)
    return (
        lines.groupby(["currency_code", "created_at"], as_index=False, dropna=False)
        .agg(**event_aggregations)
        .sort_values(["currency_code", "created_at"])
    )


def add_reconstructed_balance(
    operations: pd.DataFrame,
    events: pd.DataFrame,
    final_balances: dict[str, float],
    column_name: str,
) -> pd.DataFrame:
    result = operations.copy()
    result[column_name] = np.nan
    result[f"{column_name}_ouverture_estimee"] = np.nan
    if result.empty:
        return result

    blocks: list[pd.DataFrame] = []
    currencies = set(result["currency_code"].dropna().astype(str))
    currencies |= set(str(currency) for currency in final_balances)
    if not events.empty and "currency_code" in events.columns:
        currencies |= set(events["currency_code"].dropna().astype(str))

    for currency in sorted(currencies):
        ops = result.loc[result["currency_code"].astype(str).eq(currency)].sort_values("created_at").copy()
        if ops.empty:
            continue
        ev = events.loc[events["currency_code"].astype(str).eq(currency)].sort_values("created_at").copy() if not events.empty else pd.DataFrame()
        final_balance = float(final_balances.get(currency, 0.0))
        total_variation = float(ev["variation"].sum()) if not ev.empty else 0.0
        opening_estimate = final_balance - total_variation
        ops[f"{column_name}_ouverture_estimee"] = opening_estimate
        if ev.empty:
            ops[column_name] = opening_estimate
        else:
            ev["variation_cumulee"] = pd.to_numeric(ev["variation"], errors="coerce").fillna(0).cumsum()
            ops = pd.merge_asof(
                ops.sort_values("created_at"),
                ev[["created_at", "variation_cumulee"]],
                on="created_at",
                direction="backward",
                allow_exact_matches=True,
            )
            ops[column_name] = opening_estimate + ops["variation_cumulee"].fillna(0)
            ops = ops.drop(columns=["variation_cumulee"])
        blocks.append(ops)

    if not blocks:
        return result
    return concat_frames_stable(blocks).sort_values(["created_at", "operation_reference"]).reset_index(drop=True)


def build_savings_final(current_savings: pd.DataFrame, customer_id: str) -> dict[str, float]:
    required_columns = {"customer_id", "currency_code", "balance"}
    if current_savings.empty or not required_columns.issubset(current_savings.columns):
        return {}
    frame = current_savings.loc[current_savings["customer_id"].eq(customer_id)].copy()
    if frame.empty:
        return {}
    frame["balance"] = numeric_column(frame, "balance")
    return frame.groupby("currency_code", dropna=False)["balance"].sum().to_dict()


def build_dat_final(fixed_savings: pd.DataFrame, customer_id: str) -> dict[str, float]:
    required_columns = {"customer_id", "currency_code", "balance"}
    if fixed_savings.empty or not required_columns.issubset(fixed_savings.columns):
        return {}
    frame = fixed_savings.loc[fixed_savings["customer_id"].eq(customer_id)].copy()
    if frame.empty:
        return {}
    frame["balance"] = numeric_column(frame, "balance")
    return frame.groupby("currency_code", dropna=False)["balance"].sum().to_dict()


def filter_customer_frame(frame: pd.DataFrame, customer_id: str) -> pd.DataFrame:
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty or "customer_id" not in frame.columns:
        return pd.DataFrame()
    return frame.loc[frame["customer_id"].astype("string").eq(str(customer_id))].copy()


def _deduplicate_g2_transactions(g2: pd.DataFrame) -> pd.DataFrame:
    """Conserve une ligne canonique par Receipt No. et trace les doublons sources."""
    if g2.empty:
        return g2.copy()
    frame = g2.copy().reset_index(drop=True)
    frame["receipt_no"] = clean_identifier(frame.get("receipt_no", pd.Series("", index=frame.index)))
    frame["__row_order"] = np.arange(len(frame))
    frame["__receipt_key"] = frame["receipt_no"].where(
        frame["receipt_no"].ne(""),
        "__sans_receipt_" + frame["__row_order"].astype(str),
    )
    status = frame.get("transaction_status", pd.Series("", index=frame.index)).apply(normalize_label)
    frame["__completed_priority"] = status.isin({"completed", "complete", "successful", "success"}).astype(int)
    frame["__completion_sort"] = pd.to_datetime(
        frame.get("completion_time", pd.Series(pd.NaT, index=frame.index)), errors="coerce"
    )

    grouped = frame.groupby("__receipt_key", dropna=False, sort=False)
    frame["nombre_lignes_g2_reference"] = grouped["__receipt_key"].transform("size").astype(int)
    frame["devises_g2_reference"] = grouped["currency_code"].transform(concat_unique) if "currency_code" in frame.columns else ""
    frame["statuts_g2_reference"] = grouped["transaction_status"].transform(concat_unique) if "transaction_status" in frame.columns else ""
    amount_text = numeric_column(frame, "transaction_amount_numeric").map(
        lambda value: "" if pd.isna(value) else f"{float(value):.2f}"
    )
    frame["__amount_text"] = amount_text
    frame["montants_g2_reference"] = grouped["__amount_text"].transform(concat_unique)
    frame["doublon_receipt_no"] = frame["receipt_no"].ne("") & frame["nombre_lignes_g2_reference"].gt(1)

    canonical = (
        frame.sort_values(
            ["__receipt_key", "__completed_priority", "__completion_sort", "__row_order"],
            ascending=[True, False, False, True],
            na_position="last",
        )
        .drop_duplicates("__receipt_key", keep="first")
        .sort_values("__row_order")
        .drop(columns=["__row_order", "__receipt_key", "__completed_priority", "__completion_sort", "__amount_text"])
        .reset_index(drop=True)
    )
    return canonical


def _portal_operation_flags(group: pd.DataFrame) -> tuple[bool, bool, bool]:
    account_types = " ".join(group.get("account_type", pd.Series(dtype="string")).fillna("").astype(str))
    descriptions = " ".join(group.get("description", pd.Series(dtype="string")).fillna("").astype(str))
    text = normalize_label(f"{account_types} {descriptions}")
    has_loan = any(
        token in text
        for token in [
            "loan account",
            "loan portfolio",
            "principle",
            "remboursement",
            "repayment",
        ]
    )
    has_fixed = "fixed savings" in text or "depot bloque" in text
    has_normal = "normal savings" in text or "epargne depot" in text
    return has_loan, has_fixed, has_normal


def _build_portal_reference_controls(transactions: pd.DataFrame) -> pd.DataFrame:
    """Agrège les écritures Portal au grain ref_no sans additionner les miroirs comptables."""
    if transactions.empty or "ref_no" not in transactions.columns:
        return pd.DataFrame()
    tx = transactions.copy()
    tx["ref_no"] = clean_identifier(tx["ref_no"])
    tx = tx.loc[tx["ref_no"].ne("")].copy()
    if tx.empty:
        return pd.DataFrame()
    tx["currency_code"] = clean_text(tx.get("currency_code", pd.Series("", index=tx.index))).str.upper()
    tx["phone_portal_normalise"] = normalize_phone(tx.get("msisdn1", pd.Series("", index=tx.index)))
    tx["created_at"] = pd.to_datetime(tx.get("created_at", pd.Series(pd.NaT, index=tx.index)), errors="coerce")
    line_amounts = pd.concat(
        [
            numeric_column(tx, "dr").abs(),
            numeric_column(tx, "cr").abs(),
            (numeric_column(tx, "bal_after") - numeric_column(tx, "bal_before")).abs(),
        ],
        axis=1,
    )
    tx["montant_ligne_portal"] = line_amounts.max(axis=1)
    tx["est_compte_mpesa"] = clean_text(
        tx.get("account_type", pd.Series("", index=tx.index))
    ).apply(normalize_label).eq("mpesa account")

    rows: list[dict[str, object]] = []
    for ref_no, group in tx.groupby("ref_no", dropna=False, sort=False):
        has_loan, has_fixed, has_normal = _portal_operation_flags(group)
        mpesa_amounts = group.loc[group["est_compte_mpesa"], "montant_ligne_portal"]
        control_amounts = mpesa_amounts.loc[mpesa_amounts.gt(0)]
        if control_amounts.empty:
            control_amounts = group.loc[group["montant_ligne_portal"].gt(0), "montant_ligne_portal"]
        portal_amount = float(control_amounts.max()) if not control_amounts.empty else np.nan
        target_account = (
            "LOAN ACCOUNT / PRINCIPLE / LOAN PORTFOLIO"
            if has_loan
            else "FIXED SAVINGS"
            if has_fixed
            else "NORMAL SAVINGS"
            if has_normal
            else "MPESA ACCOUNT"
        )
        rows.append(
            {
                "ref_no_portal": ref_no,
                "nombre_ecritures_portal": int(len(group)),
                "customer_id_portal": first_non_empty(group.get("customer_id", pd.Series(dtype="string"))),
                "customer_ids_portal": concat_unique(group.get("customer_id", pd.Series(dtype="string"))),
                "telephones_portal": concat_unique(group["phone_portal_normalise"]),
                "devises_portal": concat_unique(group["currency_code"]),
                "account_types_portal": concat_unique(group.get("account_type", pd.Series(dtype="string"))),
                "descriptions_portal": concat_unique(group.get("description", pd.Series(dtype="string"))),
                "references_internes_portal": concat_unique(group.get("reference_id", pd.Series(dtype="string"))),
                "date_portal_min": group["created_at"].min(),
                "date_portal_max": group["created_at"].max(),
                "montant_portal_controle": portal_amount,
                "portal_has_loan": bool(has_loan),
                "portal_has_fixed": bool(has_fixed),
                "portal_has_normal": bool(has_normal),
                "account_type_cible": target_account,
            }
        )
    return pd.DataFrame(rows)


def _contains_pipe_value(values: object, expected: object) -> bool:
    if _is_empty_text(values) or _is_empty_text(expected):
        return False
    expected_text = str(expected).strip()
    return any(part.strip() == expected_text for part in str(values).split("|") if part.strip())


def _enrich_g2_with_portal_controls(g2: pd.DataFrame, transactions: pd.DataFrame) -> pd.DataFrame:
    output = _deduplicate_g2_transactions(g2)
    if output.empty:
        return output
    portal = _build_portal_reference_controls(transactions)
    if not portal.empty:
        output = output.merge(portal, left_on="receipt_no", right_on="ref_no_portal", how="left")
    else:
        for column, default in {
            "ref_no_portal": pd.NA,
            "nombre_ecritures_portal": 0,
            "customer_id_portal": pd.NA,
            "customer_ids_portal": "",
            "telephones_portal": "",
            "devises_portal": "",
            "account_types_portal": "",
            "descriptions_portal": "",
            "references_internes_portal": "",
            "date_portal_min": pd.NaT,
            "date_portal_max": pd.NaT,
            "montant_portal_controle": np.nan,
            "portal_has_loan": False,
            "portal_has_fixed": False,
            "portal_has_normal": False,
            "account_type_cible": "",
        }.items():
            output[column] = default

    output["nombre_ecritures_portal"] = pd.to_numeric(
        output["nombre_ecritures_portal"], errors="coerce"
    ).fillna(0).astype(int)
    has_reference = output["ref_no_portal"].astype("string").fillna("").ne("")
    g2_currency = clean_text(output.get("currency_code", pd.Series("", index=output.index))).str.upper()
    g2_phone = normalize_phone(output.get("phone_prefixe", output.get("phone", pd.Series("", index=output.index))))
    output["controle_devise"] = np.select(
        [
            ~has_reference,
            [
                _contains_pipe_value(values, expected)
                for values, expected in zip(output["devises_portal"], g2_currency)
            ],
        ],
        ["Non controlable", "Conforme"],
        default="Ecart",
    )
    output["controle_telephone"] = np.select(
        [
            ~has_reference,
            [
                _contains_pipe_value(values, expected)
                for values, expected in zip(output["telephones_portal"], g2_phone)
            ],
        ],
        ["Non controlable", "Conforme"],
        default="Ecart",
    )
    g2_amount = numeric_column(output, "transaction_amount_numeric").abs()
    portal_amount = pd.to_numeric(output["montant_portal_controle"], errors="coerce").abs()
    output["ecart_montant"] = g2_amount - portal_amount
    amount_comparable = has_reference & g2_amount.notna() & portal_amount.notna()
    output["controle_montant"] = np.select(
        [
            (~has_reference | ~amount_comparable).fillna(True).astype(bool),
            output["ecart_montant"].abs().le(0.01).fillna(False).astype(bool),
        ],
        ["Non controlable", "Conforme"],
        default="Ecart",
    )
    g2_date = pd.to_datetime(output.get("completion_time", pd.Series(pd.NaT, index=output.index)), errors="coerce")
    portal_date = pd.to_datetime(output["date_portal_min"], errors="coerce")
    output["ecart_date_minutes"] = (g2_date - portal_date).dt.total_seconds() / 60
    date_comparable = has_reference & g2_date.notna() & portal_date.notna()
    output["controle_date"] = np.select(
        [
            (~date_comparable).fillna(True).astype(bool),
            g2_date.dt.date.eq(portal_date.dt.date).fillna(False).astype(bool),
        ],
        ["Non controlable", "Conforme"],
        default="Ecart de date",
    )

    fallback_category = output.apply(
        lambda row: classify_g2_business_operation(row, dat_matched=False), axis=1
    )
    direction = clean_text(output.get("sens_flux", pd.Series("", index=output.index)))
    internal = fallback_category.eq("Operation interne Bisou")
    output["categorie_operation"] = fallback_category
    entry = direction.eq("Entree") & has_reference & ~internal
    portal_has_loan = output["portal_has_loan"].astype("boolean").fillna(False).astype(bool)
    portal_has_fixed = output["portal_has_fixed"].astype("boolean").fillna(False).astype(bool)
    portal_has_normal = output["portal_has_normal"].astype("boolean").fillna(False).astype(bool)
    output.loc[entry & portal_has_loan, "categorie_operation"] = "Remboursement prets"
    output.loc[entry & ~portal_has_loan & portal_has_fixed, "categorie_operation"] = "DAT"
    output.loc[
        entry
        & ~portal_has_loan
        & ~portal_has_fixed
        & portal_has_normal,
        "categorie_operation",
    ] = "Depot normal"
    output["description_metier"] = output["categorie_operation"]

    status = output.get("transaction_status", pd.Series("", index=output.index)).apply(normalize_label)
    explicit_status = status.ne("")
    output["est_transaction_terminee"] = ~explicit_status | status.isin(
        {"completed", "complete", "successful", "success"}
    )
    output["incluse_synthese"] = output["est_transaction_terminee"]
    has_control_gap = (
        output[["controle_devise", "controle_telephone", "controle_montant", "controle_date"]]
        .eq("Ecart")
        .any(axis=1)
        | output["controle_date"].eq("Ecart de date")
    )
    output["statut_rapprochement"] = np.select(
        [~has_reference, has_control_gap],
        ["Non rapproche", "Rapproche avec ecart"],
        default="Rapproche exact",
    )

    def anomaly_reason(row: pd.Series) -> str:
        reasons: list[str] = []
        if _is_empty_text(row.get("receipt_no")):
            reasons.append("Receipt No manquant")
        if bool(row.get("doublon_receipt_no", False)):
            reasons.append(f"Receipt No duplique ({int(row.get('nombre_lignes_g2_reference', 0))} lignes G2)")
        if not bool(row.get("est_transaction_terminee", True)):
            reasons.append(f"Statut G2 non termine : {row.get('transaction_status', '')}")
        if row.get("statut_rapprochement") == "Non rapproche":
            reasons.append("Receipt No non trouve dans ref_no")
        for column, label in [
            ("controle_devise", "Ecart de devise"),
            ("controle_telephone", "Ecart de telephone"),
            ("controle_montant", "Ecart de montant"),
        ]:
            if row.get(column) == "Ecart":
                reasons.append(label)
        if row.get("controle_date") == "Ecart de date":
            reasons.append("Ecart de date")
        if row.get("categorie_operation") in {"Flux a verifier", "Autre entree", "Autre sortie"}:
            reasons.append("Operation non classee")
        return " | ".join(reasons)

    output["motif_anomalie"] = output.apply(anomaly_reason, axis=1)
    output["est_anomalie"] = output["motif_anomalie"].ne("")
    start = pd.to_datetime(output.get("completion_time", pd.Series(pd.NaT, index=output.index)), errors="coerce").min()
    end = pd.to_datetime(output.get("completion_time", pd.Series(pd.NaT, index=output.index)), errors="coerce").max()
    output["source_analytique"] = np.where(has_reference, "G2 + Portal", "G2")
    output["identifiant_lot"] = (
        f"G2_{start:%Y%m%d}_{end:%Y%m%d}" if pd.notna(start) and pd.notna(end) else "G2_sans_periode"
    )
    return output


def build_g2_dat_crosscheck(prepared: MpesaPreparedData, customer_id: str | None = None) -> pd.DataFrame:
    g2 = prepared.g2_transactions
    fixed = prepared.fixed_savings
    transactions = prepared.transactions
    if g2.empty:
        return pd.DataFrame()

    output = _enrich_g2_with_portal_controls(g2, transactions)
    if not transactions.empty and "ref_no" in transactions.columns:
        tx = transactions.copy()
        tx["ref_no"] = clean_identifier(tx["ref_no"])
        tx["currency_code"] = clean_text(tx["currency_code"]).str.upper() if "currency_code" in tx.columns else ""
        tx["reference_dat_ligne"] = tx["reference_id"].apply(lambda value: extract_prefixed_reference(value, "FA")) if "reference_id" in tx.columns else ""
        tx_summary = (
            tx.groupby(["ref_no", "currency_code"], as_index=False, dropna=False)
            .agg(
                customer_id_ref_no=("customer_id", first_non_empty),
                customer_ids_ref_no=("customer_id", concat_unique),
                telephone_ref_no=("msisdn1", first_non_empty),
                telephones_ref_no=("msisdn1", concat_unique),
                references_transactions=("reference_id", concat_unique),
                references_dat_transactions=("reference_dat_ligne", concat_unique),
                account_types_transactions=("account_type", concat_unique),
                descriptions_transactions=("description", concat_unique),
                date_transaction_ref_no=("created_at", "min"),
                nb_lignes_transactions=("ref_no", "size"),
            )
        )
        fixed_tx = tx.loc[tx["account_type"].eq("FIXED SAVINGS")].copy() if "account_type" in tx.columns else pd.DataFrame()
        if not fixed_tx.empty:
            fixed_tx["variation_dat_operation"] = (
                numeric_column(fixed_tx, "bal_after")
                - numeric_column(fixed_tx, "bal_before")
            )
            fixed_tx["reference_dat_operation_ligne"] = fixed_tx["reference_id"].apply(
                lambda value: extract_prefixed_reference(value, "FA")
            ) if "reference_id" in fixed_tx.columns else ""
            fixed_tx_summary = (
                fixed_tx.groupby(["ref_no", "currency_code"], as_index=False, dropna=False)
                .agg(
                    reference_dat_operation=("reference_dat_operation_ligne", concat_unique),
                    solde_dat_operation_avant=("bal_before", "sum"),
                    solde_dat_operation_apres=("bal_after", "sum"),
                    variation_dat_operation=("variation_dat_operation", "sum"),
                    nb_lignes_fixed_savings=("ref_no", "size"),
                    descriptions_dat_operation=("description", concat_unique),
                )
            )
            tx_summary = tx_summary.merge(
                fixed_tx_summary,
                on=["ref_no", "currency_code"],
                how="left",
            )
        else:
            tx_summary["reference_dat_operation"] = ""
            tx_summary["solde_dat_operation_avant"] = np.nan
            tx_summary["solde_dat_operation_apres"] = np.nan
            tx_summary["variation_dat_operation"] = np.nan
            tx_summary["nb_lignes_fixed_savings"] = 0
            tx_summary["descriptions_dat_operation"] = ""
        output = output.merge(
            tx_summary,
            left_on=["receipt_no", "currency_code"],
            right_on=["ref_no", "currency_code"],
            how="left",
        )
    else:
        output["customer_id_ref_no"] = pd.NA
        output["telephone_ref_no"] = pd.NA
        output["references_transactions"] = ""
        output["references_dat_transactions"] = ""
        output["account_types_transactions"] = ""
        output["descriptions_transactions"] = ""
        output["date_transaction_ref_no"] = pd.NaT
        output["nb_lignes_transactions"] = 0
        output["reference_dat_operation"] = ""
        output["solde_dat_operation_avant"] = np.nan
        output["solde_dat_operation_apres"] = np.nan
        output["variation_dat_operation"] = np.nan
        output["nb_lignes_fixed_savings"] = 0
        output["descriptions_dat_operation"] = ""

    if fixed.empty or "msisdn" not in fixed.columns:
        output["customer_id_dat"] = pd.NA
        output["dat_final_client_devise"] = np.nan
        output["nombre_dat_client_devise"] = 0
        output["produits_dat"] = ""
        output["maturites_dat"] = ""
        output["mode_rapprochement"] = np.where(
            output["customer_id_ref_no"].astype("string").fillna("").ne(""),
            "Receipt No = ref_no",
            "Non rapproche",
        )
        output["statut_rapprochement_dat"] = "Fichier DAT absent"
        return output.reset_index(drop=True)

    dat = fixed.copy()
    dat["phone_prefixe"] = normalize_phone(dat["msisdn"])
    dat["balance"] = numeric_column(dat, "balance")
    dat["currency_code"] = clean_text(dat["currency_code"]).str.upper() if "currency_code" in dat.columns else ""
    dat_by_customer = (
        dat.groupby(["customer_id", "currency_code"], as_index=False, dropna=False)
        .agg(
            dat_final_par_ref_no=("balance", "sum"),
            nombre_dat_par_ref_no=("balance", "size"),
            produits_dat_par_ref_no=("product_name", concat_unique),
            maturites_dat_par_ref_no=("maturity_date", concat_unique),
        )
    )
    dat_by_phone = (
        dat.groupby(["phone_prefixe", "currency_code"], as_index=False, dropna=False)
        .agg(
            customer_id_dat_phone=("customer_id", concat_unique),
            dat_final_par_phone=("balance", "sum"),
            nombre_dat_par_phone=("balance", "size"),
            produits_dat_par_phone=("product_name", concat_unique),
            maturites_dat_par_phone=("maturity_date", concat_unique),
        )
    )
    output = output.merge(
        dat_by_customer,
        left_on=["customer_id_ref_no", "currency_code"],
        right_on=["customer_id", "currency_code"],
        how="left",
    )
    if "customer_id" in output.columns:
        output = output.drop(columns=["customer_id"])
    output = output.merge(dat_by_phone, on=["phone_prefixe", "currency_code"], how="left")

    output["nb_lignes_fixed_savings"] = numeric_column(output, "nb_lignes_fixed_savings").astype(int)
    for column in [
        "reference_dat_operation",
        "descriptions_dat_operation",
        "references_dat_transactions",
        "references_transactions",
        "account_types_transactions",
        "descriptions_transactions",
    ]:
        if column in output.columns:
            output[column] = output[column].fillna("")
    has_ref_match = output["customer_id_ref_no"].astype("string").fillna("").ne("")
    has_dat_operation = output["reference_dat_operation"].astype("string").fillna("").ne("") | output["nb_lignes_fixed_savings"].gt(0)
    has_dat_by_ref = pd.to_numeric(output["nombre_dat_par_ref_no"], errors="coerce").fillna(0).gt(0)
    has_phone_match = output["customer_id_dat_phone"].astype("string").fillna("").ne("")
    output["mode_rapprochement"] = np.select(
        [has_ref_match & has_dat_operation, has_ref_match & has_dat_by_ref, has_ref_match, has_phone_match],
        [
            "Receipt No = ref_no + DAT operation",
            "Receipt No = ref_no + DAT final client",
            "Receipt No = ref_no sans DAT",
            "Telephone G2 = telephone DAT",
        ],
        default="Non rapproche",
    )
    output["customer_id_dat"] = output["customer_id_ref_no"].where(has_ref_match, output["customer_id_dat_phone"])
    output["dat_final_client_devise"] = output["dat_final_par_ref_no"].where(has_dat_by_ref, output["dat_final_par_phone"])
    output["nombre_dat_client_devise"] = output["nombre_dat_par_ref_no"].where(has_dat_by_ref, output["nombre_dat_par_phone"])
    output["produits_dat"] = output["produits_dat_par_ref_no"].where(has_dat_by_ref, output["produits_dat_par_phone"])
    output["maturites_dat"] = output["maturites_dat_par_ref_no"].where(has_dat_by_ref, output["maturites_dat_par_phone"])
    output["dat_operation"] = output["reference_dat_operation"].astype("string").fillna("").replace("", pd.NA)
    output["solde_dat_operation"] = pd.to_numeric(output["solde_dat_operation_apres"], errors="coerce")
    output["dat_final"] = pd.to_numeric(output["dat_final_client_devise"], errors="coerce")

    if customer_id is not None:
        customer_text = str(customer_id)
        output = output.loc[
            output["customer_id_dat"].astype("string").fillna("").str.split("|").apply(
                lambda values: any(str(value).strip() == customer_text for value in values)
            )
        ].copy()
    output["nombre_dat_client_devise"] = pd.to_numeric(output["nombre_dat_client_devise"], errors="coerce").fillna(0).astype(int)
    has_ref_match = output["customer_id_ref_no"].astype("string").fillna("").ne("")
    has_dat_operation = output["reference_dat_operation"].astype("string").fillna("").ne("") | output["nb_lignes_fixed_savings"].gt(0)
    output["statut_rapprochement_dat"] = np.select(
        [
            output["customer_id_ref_no"].astype("string").fillna("").eq("") & output["customer_id_dat"].astype("string").fillna("").eq(""),
            has_ref_match & has_dat_operation,
            output["mode_rapprochement"].eq("Receipt No = ref_no sans DAT"),
            pd.to_numeric(output["dat_final_client_devise"], errors="coerce").fillna(0).gt(0),
            output["nombre_dat_client_devise"].gt(0),
        ],
        [
            "Receipt No non trouve dans ref_no et telephone non trouve dans DAT",
            "DAT de l'operation retrouve via ref_no",
            "Receipt No trouve dans ref_no mais aucune ligne FIXED SAVINGS",
            "DAT trouve avec solde",
            "DAT trouve sans solde positif",
        ],
        default="A verifier",
    )
    preferred_columns = [
        "receipt_no",
        "completion_time",
        "currency_code",
        "transaction_amount",
        "transaction_amount_numeric",
        "categorie_operation",
        "description_metier",
        "ref_no_portal",
        "nombre_ecritures_portal",
        "account_types_portal",
        "descriptions_portal",
        "statut_rapprochement",
        "controle_telephone",
        "controle_devise",
        "montant_portal_controle",
        "ecart_montant",
        "controle_montant",
        "ecart_date_minutes",
        "controle_date",
        "nombre_lignes_g2_reference",
        "devises_g2_reference",
        "statuts_g2_reference",
        "montants_g2_reference",
        "doublon_receipt_no",
        "incluse_synthese",
        "motif_anomalie",
        "est_anomalie",
        "balance",
        "balance_numeric",
        "opposite_party",
        "phone",
        "phone_prefixe",
        "ref_no",
        "customer_id_ref_no",
        "customer_ids_ref_no",
        "telephone_ref_no",
        "telephones_ref_no",
        "references_transactions",
        "references_dat_transactions",
        "dat_operation",
        "solde_dat_operation",
        "dat_final",
        "reference_dat_operation",
        "solde_dat_operation_avant",
        "solde_dat_operation_apres",
        "variation_dat_operation",
        "nb_lignes_fixed_savings",
        "descriptions_dat_operation",
        "account_types_transactions",
        "date_transaction_ref_no",
        "customer_id_dat",
        "dat_final_client_devise",
        "nombre_dat_client_devise",
        "produits_dat",
        "maturites_dat",
        "mode_rapprochement",
        "transaction_status",
        "details",
        "operation",
        "statut_rapprochement_dat",
    ]
    present = [column for column in preferred_columns if column in output.columns]
    rest = [column for column in output.columns if column not in present]
    return output[present + rest].reset_index(drop=True)


def classify_g2_entry_report(row: pd.Series) -> str:
    reference_value = row.get("reference_dat_operation", "")
    reference_dat = "" if _is_empty_text(reference_value) else str(reference_value).strip()
    references = normalize_label(row.get("references_transactions", ""))
    account_types = normalize_label(row.get("account_types_transactions", ""))
    descriptions = normalize_label(row.get("descriptions_transactions", ""))
    text = f"{references} {account_types} {descriptions}"
    classified = classify_g2_business_operation(row, dat_matched=bool(reference_dat))
    if classified not in {"Depot normal", "Autre entree"}:
        return classified
    if "ln" in references or "loan" in account_types or "principle" in account_types or "remboursement" in text:
        return "Remboursement prets"
    return classified


def build_entry_pivot(detail: pd.DataFrame) -> pd.DataFrame:
    if detail is None or not isinstance(detail, pd.DataFrame) or detail.empty:
        return pd.DataFrame()
    required_columns = {"currency_code", "details_rapport", "montant"}
    if not required_columns.issubset(detail.columns):
        return pd.DataFrame()

    work = detail.copy()
    work["currency_code"] = clean_text(work["currency_code"]).str.upper()
    work["details_rapport"] = clean_text(work["details_rapport"])
    work["montant"] = numeric_column(work, "montant")
    amount_pivot = (
        work.pivot_table(
            index="currency_code",
            columns="details_rapport",
            values="montant",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    count_pivot = (
        work.pivot_table(
            index="currency_code",
            columns="details_rapport",
            values="montant",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    amount_categories = [column for column in amount_pivot.columns if column != "currency_code"]
    count_categories = [column for column in count_pivot.columns if column != "currency_code"]
    amount_pivot = amount_pivot.rename(columns={column: f"montant_{column}" for column in amount_categories})
    count_pivot = count_pivot.rename(columns={column: f"nombre_{column}" for column in count_categories})
    pivot = amount_pivot.merge(count_pivot, on="currency_code", how="outer").fillna(0)

    preferred_details = G2_OPERATION_CATEGORIES
    for detail_name in preferred_details:
        amount_column = f"montant_{detail_name}"
        count_column = f"nombre_{detail_name}"
        if amount_column not in pivot.columns:
            pivot[amount_column] = 0.0
        if count_column not in pivot.columns:
            pivot[count_column] = 0

    amount_columns = [column for column in pivot.columns if column.startswith("montant_")]
    count_columns = [column for column in pivot.columns if column.startswith("nombre_")]
    pivot["montant_total"] = pivot[amount_columns].sum(axis=1)
    pivot["nombre_total"] = pivot[count_columns].sum(axis=1)

    if "sens_flux" in work.columns:
        flow_summary = (
            work.groupby(["currency_code", "sens_flux"], dropna=False)
            .agg(montant=("montant", "sum"), nombre=("montant", "size"))
            .reset_index()
        )
        flow_amounts = flow_summary.pivot_table(
            index="currency_code", columns="sens_flux", values="montant", aggfunc="sum", fill_value=0
        ).reset_index().rename_axis(None, axis=1)
        flow_counts = flow_summary.pivot_table(
            index="currency_code", columns="sens_flux", values="nombre", aggfunc="sum", fill_value=0
        ).reset_index().rename_axis(None, axis=1)
        flow_amounts = flow_amounts.rename(
            columns={"Entree": "montant_total_entrees", "Sortie": "montant_total_sorties", "A verifier": "montant_flux_a_verifier", "Indetermine": "montant_flux_indetermine"}
        )
        flow_counts = flow_counts.rename(
            columns={"Entree": "nombre_entrees", "Sortie": "nombre_sorties", "A verifier": "nombre_flux_a_verifier", "Indetermine": "nombre_flux_indetermine"}
        )
        pivot = pivot.merge(flow_amounts, on="currency_code", how="left").merge(flow_counts, on="currency_code", how="left")
    for column in ["montant_total_entrees", "montant_total_sorties", "nombre_entrees", "nombre_sorties"]:
        if column not in pivot.columns:
            pivot[column] = 0
    pivot["solde_net_flux"] = numeric_column(pivot, "montant_total_entrees") - numeric_column(pivot, "montant_total_sorties")

    ordered = ["currency_code"]
    for detail_name in preferred_details:
        ordered.extend([f"montant_{detail_name}", f"nombre_{detail_name}"])
    ordered.extend(
        [
            "nombre_entrees", "montant_total_entrees", "nombre_sorties", "montant_total_sorties",
            "solde_net_flux", "montant_total", "nombre_total",
        ]
    )
    rest = [column for column in pivot.columns if column not in ordered]
    return pivot[ordered + rest].sort_values("currency_code").reset_index(drop=True)


def build_entry_count_summary(detail: pd.DataFrame) -> pd.DataFrame:
    """Compte chaque categorie G2, avec entrees et sorties separees par devise."""
    rename_map = {category: f"Nombre de {category.lower()}" for category in G2_OPERATION_CATEGORIES}
    rename_map.update(
        {
            "DAT": "Nombre de DAT",
            "Depot normal": "Nombre de depot normal",
            "Remboursement prets": "Nombre de remboursement de pret",
            "Paiement client B2C": "Nombre de paiement client B2C",
            "Demande de credit": "Nombre de demande de credit",
            "Operation interne Bisou": "Nombre d'operation interne Bisou",
        }
    )
    category_columns = [rename_map[category] for category in G2_OPERATION_CATEGORIES]
    columns = ["currency_code", *category_columns, "Nombre d'entrees", "Nombre de sorties", "Nombre total"]
    if detail is None or not isinstance(detail, pd.DataFrame) or detail.empty:
        return pd.DataFrame(columns=columns)
    if not {"currency_code", "details_rapport"}.issubset(detail.columns):
        return pd.DataFrame(columns=columns)

    work = detail.copy()
    work["currency_code"] = clean_text(work["currency_code"]).str.upper()
    work["details_rapport"] = clean_text(work["details_rapport"])
    grouped = (
        work.groupby(["currency_code", "details_rapport"], dropna=False)
        .size()
        .unstack(fill_value=0)
    )
    for category in G2_OPERATION_CATEGORIES:
        if category not in grouped.columns:
            grouped[category] = 0
    summary = grouped[G2_OPERATION_CATEGORIES].reset_index().rename(columns=rename_map)
    if "sens_flux" in work.columns:
        direction_counts = work.groupby(["currency_code", "sens_flux"]).size().unstack(fill_value=0)
        summary["Nombre d'entrees"] = summary["currency_code"].map(direction_counts.get("Entree", pd.Series(dtype="int64"))).fillna(0).astype(int)
        summary["Nombre de sorties"] = summary["currency_code"].map(direction_counts.get("Sortie", pd.Series(dtype="int64"))).fillna(0).astype(int)
    else:
        summary["Nombre d'entrees"] = summary[category_columns].sum(axis=1)
        summary["Nombre de sorties"] = 0
    summary["Nombre total"] = summary[category_columns].sum(axis=1)
    return summary[columns].sort_values("currency_code").reset_index(drop=True)


def build_entry_vertical_summary(detail: pd.DataFrame) -> pd.DataFrame:
    if detail is None or not isinstance(detail, pd.DataFrame) or detail.empty:
        return pd.DataFrame(columns=["currency_code", "details_rapport", "montant"])
    required_columns = {"currency_code", "details_rapport", "montant"}
    if not required_columns.issubset(detail.columns):
        return pd.DataFrame(columns=["currency_code", "details_rapport", "montant"])

    work = detail.copy()
    work["currency_code"] = clean_text(work["currency_code"]).str.upper()
    work["details_rapport"] = clean_text(work["details_rapport"])
    work["montant"] = numeric_column(work, "montant")
    grouped = (
        work.groupby(["currency_code", "details_rapport"], as_index=False, dropna=False)
        .agg(montant=("montant", "sum"))
    )
    currencies = sorted(value for value in grouped["currency_code"].dropna().astype(str).unique() if value)
    observed_categories = [
        value for value in grouped["details_rapport"].dropna().astype(str).unique() if value not in G2_OPERATION_CATEGORIES
    ]
    categories = [*G2_OPERATION_CATEGORIES, *sorted(observed_categories)]
    rows: list[dict[str, object]] = []
    for currency in currencies:
        currency_group = grouped.loc[grouped["currency_code"].eq(currency)]
        values = {
            str(row["details_rapport"]): float(row["montant"])
            for _, row in currency_group.iterrows()
        }
        for category in categories:
            rows.append(
                {
                    "currency_code": currency,
                    "details_rapport": category,
                    "montant": values.get(category, 0.0),
                }
            )
        rows.append(
            {
                "currency_code": currency,
                "details_rapport": f"Total {currency}",
                "montant": sum(values.values()),
            }
        )
    return pd.DataFrame(rows)


def build_g2_entry_report(prepared: MpesaPreparedData) -> dict[str, pd.DataFrame]:
    detail = build_g2_dat_crosscheck(prepared)
    if detail.empty:
        return {
            "detail": pd.DataFrame(),
            "synthese": pd.DataFrame(),
            "pivot": pd.DataFrame(),
            "vertical_summary": pd.DataFrame(),
            "comptages": build_entry_count_summary(pd.DataFrame()),
        }

    report = detail.copy()
    report["details_rapport"] = report.apply(classify_g2_entry_report, axis=1)
    report["montant"] = numeric_column(report, "transaction_amount_numeric").abs()
    report["sens_flux"] = clean_text(report.get("sens_flux", pd.Series("Indetermine", index=report.index)))
    report["montant_entree"] = report["montant"].where(report["sens_flux"].eq("Entree"), 0.0)
    report["montant_sortie"] = report["montant"].where(report["sens_flux"].eq("Sortie"), 0.0)
    report["date"] = pd.to_datetime(report.get("completion_time"), errors="coerce")
    report["duree"] = np.where(
        report["details_rapport"].eq("DAT"),
        report.get("produits_dat", pd.Series("", index=report.index)).astype("string").fillna(""),
        "-",
    )
    report["compte_cree"] = pd.to_datetime(report.get("date_transaction_ref_no"), errors="coerce")
    report["receipt_no"] = report.get("receipt_no", pd.Series("", index=report.index))
    report["opposite_party"] = report.get("opposite_party", pd.Series("", index=report.index))
    report["currency_code"] = report.get("currency_code", pd.Series("", index=report.index))

    detail_columns = [
        "date",
        "receipt_no",
        "sens_flux",
        "details_rapport",
        "reason_type",
        "opposite_party",
        "Nom_client",
        "duree",
        "compte_cree",
        "montant",
        "montant_entree",
        "montant_sortie",
        "currency_code",
        "customer_id_ref_no",
        "reference_dat_operation",
        "solde_dat_operation_avant",
        "solde_dat_operation_apres",
        "variation_dat_operation",
        "mode_rapprochement",
        "statut_rapprochement_dat",
    ]
    detail_columns = [column for column in detail_columns if column in report.columns]
    report_detail = report[detail_columns].sort_values(["currency_code", "date"], ascending=[True, False]).reset_index(drop=True)

    synthese = (
        report.groupby(["currency_code", "sens_flux", "details_rapport"], as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
        .sort_values(["currency_code", "sens_flux", "details_rapport"])
    )
    totals = (
        report.groupby("currency_code", as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
    )
    totals["sens_flux"] = "Tous flux"
    totals["details_rapport"] = "Total " + totals["currency_code"].astype("string").fillna("")
    synthese = concat_frames_stable([synthese, totals[synthese.columns]]).reset_index(drop=True)

    return {
        "detail": report_detail,
        "synthese": synthese,
        "pivot": build_entry_pivot(report_detail),
        "vertical_summary": build_entry_vertical_summary(report_detail),
        "comptages": build_entry_count_summary(report_detail),
    }


def _is_round_savings_amount(amount: object, currency: object) -> bool:
    value = pd.to_numeric(pd.Series([amount]), errors="coerce").iloc[0]
    if pd.isna(value) or value <= 0:
        return False
    currency_text = str(currency or "").upper()
    if currency_text == "CDF":
        return abs(value % 500) < 0.01 or abs(value % 500 - 500) < 0.01
    if currency_text == "USD":
        return abs(value % 1) < 0.01
    return True


def _best_subset_for_target(items: list[tuple[int, float]], target: float, tolerance: float = 0.01) -> list[int]:
    if not items or pd.isna(target) or target <= 0:
        return []
    best: list[int] = []
    best_diff = float("inf")

    def walk(position: int, selected: list[int], total: float) -> bool:
        nonlocal best, best_diff
        diff = abs(total - target)
        if diff < best_diff:
            best = selected.copy()
            best_diff = diff
        if diff <= tolerance:
            return True
        if position >= len(items) or total > target + tolerance:
            return False
        for index in range(position, len(items)):
            row_index, amount = items[index]
            if walk(index + 1, selected + [row_index], total + amount):
                return True
        return False

    walk(0, [], 0.0)
    return best if best_diff <= tolerance else []


def _build_daily_dat_assignments(g2: pd.DataFrame, fixed: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "receipt_no",
        "dat_customer_id",
        "duree",
        "compte_cree",
        "maturity_date",
        "dat_balance",
        "dat_match_rule",
    ]
    if g2.empty:
        return pd.DataFrame(columns=columns)

    assignments = pd.DataFrame({"receipt_no": g2.get("receipt_no", pd.Series(dtype="string"))})
    for column in columns[1:]:
        assignments[column] = pd.NA
    if fixed.empty or "msisdn" not in fixed.columns:
        return assignments

    dat = fixed.copy()
    dat["phone_prefixe"] = normalize_phone(dat["msisdn"])
    dat["currency_code"] = clean_text(dat.get("currency_code", pd.Series("", index=dat.index))).str.upper()
    dat["balance"] = numeric_column(dat, "balance")
    dat["compte_cree"] = pd.to_datetime(
        dat.get("created_at", dat.get("date_approved", pd.Series(pd.NaT, index=dat.index))),
        errors="coerce",
    )
    if "product_name" not in dat.columns:
        dat["product_name"] = dat.get("account_type", pd.Series("", index=dat.index))
    dat["jour_creation"] = dat["compte_cree"].dt.date

    tx = g2.copy()
    tx["receipt_no"] = clean_identifier(tx.get("receipt_no", pd.Series("", index=tx.index)))
    tx["phone_prefixe"] = normalize_phone(tx.get("phone_prefixe", tx.get("phone", pd.Series("", index=tx.index))))
    tx["currency_code"] = clean_text(tx.get("currency_code", pd.Series("", index=tx.index))).str.upper()
    tx["montant"] = numeric_column(tx, "transaction_amount_numeric").abs()
    tx["date"] = pd.to_datetime(tx.get("completion_time", pd.Series(pd.NaT, index=tx.index)), errors="coerce")
    tx["jour"] = tx["date"].dt.date
    if "sens_flux" in tx.columns:
        tx = tx.loc[tx["sens_flux"].astype("string").eq("Entree")].copy()

    assignment_by_receipt: dict[str, dict[str, object]] = {}
    group_columns = ["phone_prefixe", "currency_code", "jour"]
    for group_key, group in tx.groupby(group_columns, dropna=False):
        phone, currency, day = group_key
        if _is_empty_text(phone) or _is_empty_text(currency) or pd.isna(day):
            continue
        dat_group = dat.loc[
            dat["phone_prefixe"].astype("string").eq(str(phone))
            & dat["currency_code"].astype("string").eq(str(currency))
            & dat["jour_creation"].eq(day)
        ].copy()
        if dat_group.empty:
            continue

        unassigned = {
            int(index): float(value)
            for index, value in group["montant"].items()
            if not pd.isna(value) and float(value) > 0
        }
        dat_group = dat_group.sort_values(["compte_cree", "balance"], ascending=[False, False])
        for dat_index, dat_row in dat_group.iterrows():
            items = sorted(unassigned.items(), key=lambda item: item[1], reverse=True)
            selected_indexes = _best_subset_for_target(items, float(dat_row.get("balance", 0)))
            if not selected_indexes:
                continue
            for tx_index in selected_indexes:
                receipt_no = str(tx.loc[tx_index, "receipt_no"])
                assignment_by_receipt[receipt_no] = {
                    "dat_customer_id": dat_row.get("customer_id", pd.NA),
                    "duree": dat_row.get("product_name", pd.NA),
                    "compte_cree": dat_row.get("compte_cree", pd.NaT),
                    "maturity_date": dat_row.get("maturity_date", pd.NaT),
                    "dat_balance": dat_row.get("balance", np.nan),
                    "dat_match_rule": "telephone + devise + montant DAT du jour",
                }
                unassigned.pop(tx_index, None)

        has_dat_assignment = any(
            str(receipt_no) in assignment_by_receipt
            for receipt_no in group["receipt_no"].astype("string").fillna("")
        )
        if has_dat_assignment:
            latest_dat = dat_group.iloc[0]
            for tx_index, amount in unassigned.items():
                if _is_round_savings_amount(amount, currency):
                    receipt_no = str(tx.loc[tx_index, "receipt_no"])
                    assignment_by_receipt[receipt_no] = {
                        "dat_customer_id": latest_dat.get("customer_id", pd.NA),
                        "duree": latest_dat.get("product_name", pd.NA),
                        "compte_cree": latest_dat.get("compte_cree", pd.NaT),
                        "maturity_date": latest_dat.get("maturity_date", pd.NaT),
                        "dat_balance": latest_dat.get("balance", np.nan),
                        "dat_match_rule": "telephone + devise + DAT du jour + montant arrondi",
                    }

    for index, receipt_no in assignments["receipt_no"].astype("string").fillna("").items():
        match = assignment_by_receipt.get(str(receipt_no))
        if not match:
            continue
        for column, value in match.items():
            assignments.loc[index, column] = value
    return assignments[columns]


def build_g2_daily_savings_report(prepared: MpesaPreparedData) -> dict[str, pd.DataFrame]:
    g2 = prepared.g2_transactions
    if g2.empty:
        return {
            "detail": pd.DataFrame(),
            "anomalies": pd.DataFrame(),
            "synthese": pd.DataFrame(),
            "pivot": pd.DataFrame(),
            "vertical_summary": pd.DataFrame(),
            "comptages": build_entry_count_summary(pd.DataFrame()),
        }

    report = build_g2_dat_crosscheck(prepared)
    if report.empty:
        report = _enrich_g2_with_portal_controls(g2, prepared.transactions)
    report["receipt_no"] = clean_identifier(report.get("receipt_no", pd.Series("", index=report.index)))
    report["date"] = pd.to_datetime(report.get("completion_time"), errors="coerce")
    report["montant"] = numeric_column(report, "transaction_amount_numeric").abs()
    report["sens_flux"] = clean_text(
        report.get("sens_flux", pd.Series("Indetermine", index=report.index))
    )
    report["montant_entree"] = report["montant"].where(report["sens_flux"].eq("Entree"), 0.0)
    report["montant_sortie"] = report["montant"].where(report["sens_flux"].eq("Sortie"), 0.0)
    report["currency_code"] = clean_text(report.get("currency_code", pd.Series("", index=report.index))).str.upper()
    report["phone_prefixe"] = normalize_phone(report.get("phone_prefixe", report.get("phone", pd.Series("", index=report.index))))

    assignments = _build_daily_dat_assignments(report, prepared.fixed_savings)
    if not assignments.empty:
        report = report.merge(assignments, on="receipt_no", how="left")
    else:
        report["dat_customer_id"] = pd.NA
        report["duree"] = pd.NA
        report["compte_cree"] = pd.NaT
        report["maturity_date"] = pd.NaT
        report["dat_balance"] = np.nan
        report["dat_match_rule"] = pd.NA

    has_portal_reference = report.get(
        "ref_no_portal", pd.Series(pd.NA, index=report.index)
    ).astype("string").fillna("").ne("")
    heuristic_dat = (
        ~has_portal_reference
        & report["dat_customer_id"].astype("string").fillna("").ne("")
        & report["sens_flux"].eq("Entree")
    )
    report["details_rapport"] = clean_text(
        report.get("categorie_operation", pd.Series("", index=report.index))
    )
    missing_category = report["details_rapport"].eq("")
    if missing_category.any():
        report.loc[missing_category, "details_rapport"] = report.loc[missing_category].apply(
            lambda row: classify_g2_business_operation(row, dat_matched=False), axis=1
        )
    report.loc[heuristic_dat, "details_rapport"] = "DAT"
    is_dat = report["details_rapport"].eq("DAT") & report["sens_flux"].eq("Entree")
    report["duree"] = report["duree"].where(is_dat, "-")
    report["compte_cree_dat"] = pd.to_datetime(report["compte_cree"], errors="coerce")

    customers = prepared.customers
    if not customers.empty and {"msisdn1", "created_at"}.issubset(customers.columns):
        customer_accounts = customers.copy()
        customer_accounts["phone_prefixe"] = normalize_phone(customer_accounts["msisdn1"])
        customer_accounts["compte_cree_client"] = pd.to_datetime(customer_accounts["created_at"], errors="coerce")
        customer_summary = (
            customer_accounts.dropna(subset=["phone_prefixe", "compte_cree_client"])
            .sort_values("compte_cree_client")
            .groupby("phone_prefixe", as_index=False, dropna=False)
            .agg(compte_cree_client=("compte_cree_client", "min"))
        )
        report = report.merge(customer_summary, on="phone_prefixe", how="left")
    else:
        report["compte_cree_client"] = pd.NaT

    current = prepared.current_savings
    if not current.empty and {"msisdn", "currency_code", "created_at"}.issubset(current.columns):
        current_accounts = current.copy()
        current_accounts["phone_prefixe"] = normalize_phone(current_accounts["msisdn"])
        current_accounts["currency_code"] = clean_text(current_accounts["currency_code"]).str.upper()
        current_accounts["compte_cree_epargne_courante"] = pd.to_datetime(current_accounts["created_at"], errors="coerce")
        current_summary = (
            current_accounts.dropna(subset=["phone_prefixe", "currency_code", "compte_cree_epargne_courante"])
            .sort_values("compte_cree_epargne_courante")
            .groupby(["phone_prefixe", "currency_code"], as_index=False, dropna=False)
            .agg(
                current_customer_id=("customer_id", first_non_empty),
                compte_cree_epargne_courante=("compte_cree_epargne_courante", "min"),
            )
        )
        report = report.merge(current_summary, on=["phone_prefixe", "currency_code"], how="left")
    else:
        report["current_customer_id"] = pd.NA
        report["compte_cree_epargne_courante"] = pd.NaT
    report["compte_cree"] = (
        pd.to_datetime(report["compte_cree_client"], errors="coerce")
        .combine_first(pd.to_datetime(report["compte_cree_epargne_courante"], errors="coerce"))
        .combine_first(report["compte_cree_dat"])
    )

    has_same_day_dat_phone = pd.Series(False, index=report.index)
    fixed = prepared.fixed_savings
    if not fixed.empty and "msisdn" in fixed.columns:
        dat = fixed.copy()
        dat["phone_prefixe"] = normalize_phone(dat["msisdn"])
        dat["currency_code"] = clean_text(dat.get("currency_code", pd.Series("", index=dat.index))).str.upper()
        dat["compte_cree"] = pd.to_datetime(
            dat.get("created_at", dat.get("date_approved", pd.Series(pd.NaT, index=dat.index))),
            errors="coerce",
        )
        dat_keys = set(
            dat.dropna(subset=["phone_prefixe", "currency_code", "compte_cree"])
            .assign(jour=lambda frame: frame["compte_cree"].dt.date)
            [["phone_prefixe", "currency_code", "jour"]]
            .astype("string")
            .itertuples(index=False, name=None)
        )
        tx_keys = (
            report.assign(jour=report["date"].dt.date)[["phone_prefixe", "currency_code", "jour"]]
            .astype("string")
            .itertuples(index=False, name=None)
        )
        has_same_day_dat_phone = pd.Series([key in dat_keys for key in tx_keys], index=report.index)

    unusual_same_day_dat_amount = (
        ~has_portal_reference
        & report["sens_flux"].eq("Entree")
        & report["details_rapport"].eq("Depot normal")
        & ~is_dat
        & has_same_day_dat_phone
        & ~report.apply(lambda row: _is_round_savings_amount(row.get("montant"), row.get("currency_code")), axis=1)
    )
    report.loc[unusual_same_day_dat_amount, "details_rapport"] = "Remboursement prets"

    detail_columns = [
        "date",
        "receipt_no",
        "sens_flux",
        "details_rapport",
        "reason_type",
        "details",
        "opposite_party",
        "Nom_client",
        "phone_prefixe",
        "duree",
        "compte_cree",
        "montant",
        "montant_entree",
        "montant_sortie",
        "currency_code",
        "current_customer_id",
        "dat_customer_id",
        "compte_cree_client",
        "compte_cree_epargne_courante",
        "compte_cree_dat",
        "maturity_date",
        "dat_balance",
        "dat_match_rule",
        "transaction_status",
        "transaction_amount_source",
        "paid_in_numeric",
        "withdrawn_numeric",
        "balance_numeric",
        "ref_no_portal",
        "customer_id_portal",
        "nombre_ecritures_portal",
        "account_types_portal",
        "descriptions_portal",
        "account_type_cible",
        "statut_rapprochement",
        "controle_telephone",
        "controle_devise",
        "montant_portal_controle",
        "ecart_montant",
        "controle_montant",
        "ecart_date_minutes",
        "controle_date",
        "nombre_lignes_g2_reference",
        "devises_g2_reference",
        "statuts_g2_reference",
        "montants_g2_reference",
        "doublon_receipt_no",
        "incluse_synthese",
        "motif_anomalie",
        "est_anomalie",
        "source_analytique",
        "identifiant_lot",
    ]
    detail_columns = [column for column in detail_columns if column in report.columns]
    detail = report[detail_columns].sort_values(["currency_code", "date"], ascending=[True, False]).reset_index(drop=True)

    summary_detail = detail.loc[
        detail.get("incluse_synthese", pd.Series(True, index=detail.index)).fillna(False).astype(bool)
    ].copy()
    synthese = (
        summary_detail.groupby(["currency_code", "sens_flux", "details_rapport"], as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
        .sort_values(["currency_code", "sens_flux", "details_rapport"])
    )
    direction_totals = (
        summary_detail.groupby(["currency_code", "sens_flux"], as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
    )
    direction_totals["details_rapport"] = "Total " + direction_totals["sens_flux"].astype("string").fillna("")
    totals = (
        summary_detail.groupby("currency_code", as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
    )
    totals["sens_flux"] = "Tous flux"
    totals["details_rapport"] = "Total " + totals["currency_code"].astype("string").fillna("")
    synthese = concat_frames_stable(
        [synthese, direction_totals[synthese.columns], totals[synthese.columns]]
    ).reset_index(drop=True)
    return {
        "detail": detail,
        "anomalies": detail.loc[
            detail.get("est_anomalie", pd.Series(False, index=detail.index)).fillna(False).astype(bool)
        ].reset_index(drop=True),
        "synthese": synthese,
        "pivot": build_entry_pivot(summary_detail),
        "vertical_summary": build_entry_vertical_summary(summary_detail),
        "comptages": build_entry_count_summary(summary_detail),
    }


def build_g2_retention_report(
    prepared: MpesaPreparedData,
    daily_detail: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Mesure le retour des clients G2 actifs par mois, devise et operation.

    La retention M+1 exige une activite pendant le mois civil suivant. La
    retention a 90 jours exige au moins une activite dans les 90 jours suivant
    la fin du mois de base. Les taux restent vides tant que la fenetre complete
    n'est pas observable dans le perimetre analyse.
    """
    empty_result = {
        "mensuelle": pd.DataFrame(),
        "operations": pd.DataFrame(),
        "detail_clients": pd.DataFrame(),
        "definitions": pd.DataFrame(
            [
                {
                    "indicateur": "Retention M+1",
                    "definition": "Clients actifs pendant le mois de base et actifs de nouveau pendant le mois civil suivant.",
                    "denominateur": "Telephones clients distincts actifs pendant le mois de base, par devise.",
                    "numerateur": "Clients du denominateur avec au moins une operation eligible le mois suivant.",
                },
                {
                    "indicateur": "Retention 90 jours",
                    "definition": "Clients actifs pendant le mois de base et actifs de nouveau dans les 90 jours suivant la fin de ce mois.",
                    "denominateur": "Telephones clients distincts actifs pendant le mois de base, par devise.",
                    "numerateur": "Clients du denominateur avec au moins une operation eligible avant l'echeance des 90 jours.",
                },
                {
                    "indicateur": "Population eligible",
                    "definition": "Operations G2 avec Completion Time et telephone valides, hors operations internes et statuts explicitement en echec/annules/inverses.",
                    "denominateur": "Toutes les operations du perimetre filtre.",
                    "numerateur": "Operations respectant les criteres d'eligibilite.",
                },
            ]
        ),
    }
    if prepared.g2_transactions.empty:
        return empty_result

    activity = (
        daily_detail.copy()
        if isinstance(daily_detail, pd.DataFrame)
        else build_g2_daily_savings_report(prepared).get("detail", pd.DataFrame()).copy()
    )
    if activity.empty:
        return empty_result

    activity["date"] = pd.to_datetime(activity.get("date"), errors="coerce")
    activity["phone_prefixe"] = normalize_phone(
        activity.get("phone_prefixe", pd.Series("", index=activity.index))
    )
    activity["currency_code"] = clean_text(
        activity.get("currency_code", pd.Series("", index=activity.index))
    ).str.upper()
    activity["details_rapport"] = clean_text(
        activity.get("details_rapport", pd.Series("Non classe", index=activity.index))
    ).replace("", "Non classe")
    activity["transaction_status"] = clean_text(
        activity.get("transaction_status", pd.Series("", index=activity.index))
    )
    rejected_status = activity["transaction_status"].apply(normalize_label).str.contains(
        r"fail|echec|cancel|annul|reverse|revers|reject|rejet",
        regex=True,
        na=False,
    )
    internal_operation = activity["details_rapport"].apply(normalize_label).str.contains(
        "operation interne",
        regex=False,
        na=False,
    )
    activity = activity.loc[
        activity["date"].notna()
        & activity["phone_prefixe"].notna()
        & activity["currency_code"].ne("")
        & ~rejected_status
        & ~internal_operation
    ].copy()
    if activity.empty:
        return empty_result

    activity["receipt_no"] = clean_identifier(
        activity.get("receipt_no", pd.Series("", index=activity.index))
    )
    activity["__transaction_key"] = activity["receipt_no"].where(
        activity["receipt_no"].ne(""),
        "ligne_" + activity.index.astype(str),
    )
    activity = activity.drop_duplicates(
        subset=["currency_code", "__transaction_key", "phone_prefixe", "date"]
    )
    activity["periode"] = activity["date"].dt.to_period("M").dt.to_timestamp()
    observation_start = activity["date"].min()
    observation_end = activity["date"].max()

    rows: list[dict[str, object]] = []
    client_activity = {
        (currency, phone): group.sort_values("date")
        for (currency, phone), group in activity.groupby(
            ["currency_code", "phone_prefixe"], dropna=False, sort=False
        )
    }
    base_groups = activity.groupby(["periode", "currency_code", "phone_prefixe"], dropna=False)
    for (period, currency, phone), base in base_groups:
        period = pd.Timestamp(period)
        month_end = period + pd.offsets.MonthEnd(1)
        next_month_start = period + pd.offsets.MonthBegin(1)
        next_month_end = next_month_start + pd.offsets.MonthEnd(1)
        deadline_90 = month_end + pd.Timedelta(days=90)
        eligible_m1 = observation_end >= next_month_end
        eligible_90 = observation_end >= deadline_90
        client_history = client_activity[(currency, phone)]
        future = client_history.loc[client_history["date"].gt(month_end)]
        first_return = future["date"].min() if not future.empty else pd.NaT
        returned_m1 = bool(
            not future.empty
            and future["date"].between(next_month_start, next_month_end, inclusive="both").any()
        )
        returned_90 = bool(
            not future.empty
            and future["date"].le(deadline_90).any()
        )
        rows.append(
            {
                "periode": period,
                "annee": int(period.year),
                "mois": period.strftime("%Y-%m"),
                "currency_code": currency,
                "phone_prefixe": phone,
                "Nom_client": concat_unique(base.get("Nom_client", pd.Series(dtype="string"))),
                "types_operations": concat_unique(base["details_rapport"]),
                "nombre_operations_mois_base": int(len(base)),
                "montant_entrees_mois_base": float(numeric_column(base, "montant_entree").sum()),
                "montant_sorties_mois_base": float(numeric_column(base, "montant_sortie").sum()),
                "premier_retour": first_return,
                "delai_premier_retour_jours": (
                    int((first_return.normalize() - month_end.normalize()).days)
                    if pd.notna(first_return)
                    else pd.NA
                ),
                "eligible_retention_m1": bool(eligible_m1),
                "retenu_m1": returned_m1 if eligible_m1 else pd.NA,
                "eligible_retention_90j": bool(eligible_90),
                "retenu_90j": returned_90 if eligible_90 else pd.NA,
                "debut_observation": observation_start,
                "fin_observation": observation_end,
            }
        )

    detail = pd.DataFrame(rows).sort_values(
        ["periode", "currency_code", "phone_prefixe"], ascending=[False, True, True]
    ).reset_index(drop=True)

    def _summarize(frame: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
        summary_rows: list[dict[str, object]] = []
        for keys, group in frame.groupby(group_columns, dropna=False, sort=True):
            key_values = keys if isinstance(keys, tuple) else (keys,)
            result = dict(zip(group_columns, key_values))
            clients_base = int(group["phone_prefixe"].nunique())
            eligible_m1 = bool(group["eligible_retention_m1"].all())
            eligible_90 = bool(group["eligible_retention_90j"].all())
            retained_m1 = int(group["retenu_m1"].eq(True).sum()) if eligible_m1 else pd.NA
            retained_90 = int(group["retenu_90j"].eq(True).sum()) if eligible_90 else pd.NA
            result.update(
                {
                    "clients_actifs_mois_base": clients_base,
                    "clients_retenus_m1": retained_m1,
                    "retention_m1_pct": round(100 * retained_m1 / clients_base, 2) if eligible_m1 and clients_base else np.nan,
                    "clients_retenus_90j": retained_90,
                    "retention_90j_pct": round(100 * retained_90 / clients_base, 2) if eligible_90 and clients_base else np.nan,
                    "eligible_retention_m1": eligible_m1,
                    "eligible_retention_90j": eligible_90,
                    "debut_observation": observation_start,
                    "fin_observation": observation_end,
                }
            )
            summary_rows.append(result)
        return pd.DataFrame(summary_rows)

    monthly = _summarize(detail, ["periode", "annee", "mois", "currency_code"])
    monthly = monthly.sort_values(["currency_code", "periode"]).reset_index(drop=True)

    operation_detail = detail.assign(
        details_rapport=detail["types_operations"].str.split(r"\s*\|\s*", regex=True)
    ).explode("details_rapport")
    operation_detail["details_rapport"] = clean_text(operation_detail["details_rapport"]).replace("", "Non classe")
    operations = _summarize(
        operation_detail,
        ["periode", "annee", "mois", "currency_code", "details_rapport"],
    )
    operations = operations.sort_values(
        ["currency_code", "details_rapport", "periode"]
    ).reset_index(drop=True)

    return {
        "mensuelle": monthly,
        "operations": operations,
        "detail_clients": detail,
        "definitions": empty_result["definitions"],
    }


def search_customers(query: object, prepared: MpesaPreparedData) -> pd.DataFrame:
    text = str(query).strip()
    if not text:
        return pd.DataFrame(columns=["customer_id", "Nom_client", "telephone", "source"])
    normalized_phone = normalize_phone(pd.Series([text])).iloc[0]
    frames: list[pd.DataFrame] = []
    source_map = [
        ("Transactions", prepared.transactions, "msisdn1"),
        ("Epargne courante", prepared.current_savings, "msisdn"),
        ("DAT", prepared.fixed_savings, "msisdn"),
        ("Credits", prepared.loans, "msisdn1"),
    ]
    for label, frame, phone_col in source_map:
        if frame.empty or "customer_id" not in frame.columns:
            continue
        columns = ["customer_id"]
        if "Nom_client" in frame.columns:
            columns.append("Nom_client")
        if phone_col in frame.columns:
            columns.append(phone_col)
        tmp = frame[columns].copy().rename(columns={phone_col: "telephone"})
        if "Nom_client" not in tmp.columns:
            tmp["Nom_client"] = pd.NA
        if "telephone" not in tmp.columns:
            tmp["telephone"] = pd.NA
        tmp["source"] = label
        frames.append(tmp)
    if not frames:
        return pd.DataFrame(columns=["customer_id", "Nom_client", "telephone", "source"])
    clients = concat_frames_stable(frames).drop_duplicates()
    mask = clients["customer_id"].astype("string").str.contains(text, case=False, regex=False, na=False)
    normalized_name = normalize_label(text)
    if normalized_name:
        mask = mask | clients["Nom_client"].apply(normalize_label).str.contains(normalized_name, regex=False, na=False)
    if not _is_empty_text(normalized_phone):
        mask = mask | clients["telephone"].astype("string").str.contains(str(normalized_phone), case=False, regex=False, na=False)
    else:
        mask = mask | clients["telephone"].astype("string").str.contains(text, case=False, regex=False, na=False)
    return clients.loc[mask].sort_values(["customer_id", "telephone", "source"]).reset_index(drop=True)


def resolve_customer_id(query: object, prepared: MpesaPreparedData) -> str | None:
    matches = search_customers(query, prepared)
    if matches.empty:
        return None
    unique_ids = matches["customer_id"].dropna().astype(str).unique().tolist()
    if len(unique_ids) == 1:
        return unique_ids[0]
    return None


def _build_dat_direct(transactions_client: pd.DataFrame) -> pd.DataFrame:
    if transactions_client.empty:
        return pd.DataFrame()
    dat_direct = transactions_client.loc[transactions_client["account_type"].eq("FIXED SAVINGS")].copy()
    if dat_direct.empty:
        return pd.DataFrame()
    dat_direct["variation_dat_operation"] = dat_direct["bal_after"] - dat_direct["bal_before"]
    return (
        dat_direct.groupby(["currency_code", "created_at"], as_index=False, dropna=False)
        .agg(
            reference_dat_direct=("reference_id", concat_unique),
            solde_dat_operation_avant=("bal_before", "sum"),
            solde_dat_operation_apres=("bal_after", "sum"),
            variation_dat_operation=("variation_dat_operation", "sum"),
        )
    )


def build_mpesa_statement(
    prepared: MpesaPreparedData,
    customer_id: str,
    opening_balances: dict[str, float | None] | None = None,
    date_start: object | None = None,
    date_end: object | None = None,
) -> dict[str, Any]:
    opening_balances = opening_balances or {}
    transactions = prepared.transactions
    tx_client = transactions.loc[transactions["customer_id"].eq(str(customer_id))].copy()
    dat_client = filter_customer_frame(prepared.fixed_savings, str(customer_id))
    savings_client = filter_customer_frame(prepared.current_savings, str(customer_id))
    loans_client = filter_customer_frame(prepared.loans, str(customer_id))

    if tx_client.empty:
        raise ValueError(f"Aucune transaction trouvee pour le client {customer_id}.")

    if not dat_client.empty:
        situation_date = pd.to_datetime(transactions["created_at"], errors="coerce").max()
        dat_client["statut_dat"] = np.select(
            [
                numeric_column(dat_client, "balance").le(0),
                dat_client.get("maturity_date", pd.Series(pd.NaT, index=dat_client.index)).notna()
                & dat_client.get("maturity_date", pd.Series(pd.NaT, index=dat_client.index)).lt(situation_date),
            ],
            ["Solde nul", "Echu"],
            default="Actif",
        )

    mpesa = tx_client.loc[tx_client["account_type"].eq("MPESA ACCOUNT")].copy()
    if mpesa.empty:
        raise ValueError(f"Aucun mouvement MPESA ACCOUNT trouve pour le client {customer_id}.")

    mpesa["operation_reference"] = mpesa["ref_no"].where(~mpesa["ref_no"].apply(_is_empty_text), mpesa["reference_id"])
    missing_reference = mpesa["operation_reference"].apply(_is_empty_text)
    mpesa.loc[missing_reference, "operation_reference"] = "LIGNE-" + mpesa.loc[missing_reference, "id"].astype("string")

    statement_aggregations: dict[str, tuple[str, object]] = {
        "telephone": ("msisdn1", concat_unique),
        "debit_mpesa": ("dr", "sum"),
        "credit_mpesa": ("cr", "sum"),
        "references_internes": ("reference_id", concat_unique),
        "descriptions": ("description", concat_unique),
        "account_types": ("account_type", concat_unique),
        "nombre_lignes_comptables": ("id", "count"),
    }
    if "Nom_client" in mpesa.columns:
        statement_aggregations["Nom_client"] = ("Nom_client", concat_unique)
    if "mode_rapprochement_nom_client" in mpesa.columns:
        statement_aggregations["mode_rapprochement_nom_client"] = ("mode_rapprochement_nom_client", concat_unique)
    statement = (
        mpesa.groupby(["customer_id", "currency_code", "created_at", "operation_reference"], as_index=False, dropna=False)
        .agg(**statement_aggregations)
        .sort_values(["currency_code", "created_at", "operation_reference"])
    )
    if "Nom_client" not in statement.columns:
        statement["Nom_client"] = pd.NA
    if "mode_rapprochement_nom_client" not in statement.columns:
        statement["mode_rapprochement_nom_client"] = "Nom client non disponible"

    statement["reference_dat_operation"] = statement["references_internes"].apply(lambda value: extract_prefixed_reference(value, "FA"))
    statement["reference_credit_operation"] = statement["references_internes"].apply(lambda value: extract_prefixed_reference(value, "LN"))

    dat_direct = _build_dat_direct(tx_client)
    if not dat_direct.empty:
        statement = statement.merge(dat_direct, on=["currency_code", "created_at"], how="left")
        statement["reference_dat_operation"] = statement["reference_dat_direct"].fillna(statement["reference_dat_operation"])
        statement = statement.drop(columns=["reference_dat_direct"])
    else:
        statement["solde_dat_operation_avant"] = np.nan
        statement["solde_dat_operation_apres"] = np.nan
        statement["variation_dat_operation"] = np.nan

    statement["mouvement_net_mpesa"] = statement["credit_mpesa"] - statement["debit_mpesa"]
    statement["entree_mpesa"] = statement["mouvement_net_mpesa"].clip(lower=0)
    statement["sortie_mpesa"] = (-statement["mouvement_net_mpesa"].clip(upper=0))
    statement["type_operation"] = statement.apply(
        lambda row: classify_mpesa_operation(row["descriptions"], row["account_types"], row["mouvement_net_mpesa"]),
        axis=1,
    )
    statement["cumul_net_depuis_debut_fichier"] = statement.groupby("currency_code")["mouvement_net_mpesa"].cumsum()
    statement["solde_mpesa_avant"] = np.nan
    statement["solde_mpesa_apres"] = np.nan
    statement["solde_mpesa_disponible"] = False

    for currency, index in statement.groupby("currency_code").groups.items():
        opening = opening_balances.get(str(currency))
        if opening is None or pd.isna(opening):
            continue
        opening = float(opening)
        cumulative = statement.loc[index, "cumul_net_depuis_debut_fichier"]
        statement.loc[index, "solde_mpesa_apres"] = opening + cumulative
        statement.loc[index, "solde_mpesa_avant"] = statement.loc[index, "solde_mpesa_apres"] - statement.loc[index, "mouvement_net_mpesa"]
        statement.loc[index, "solde_mpesa_disponible"] = True

    dat_final = build_dat_final(prepared.fixed_savings, str(customer_id))
    savings_final = build_savings_final(prepared.current_savings, str(customer_id))
    savings_events = build_account_events(tx_client, "NORMAL SAVINGS")
    dat_events = build_account_events(tx_client, "FIXED SAVINGS")
    statement = add_reconstructed_balance(statement, savings_events, savings_final, "solde_epargne_au_moment")
    statement = add_reconstructed_balance(statement, dat_events, dat_final, "solde_dat_total_au_moment")
    statement["epargne_courante_finale"] = statement["currency_code"].map(lambda currency: float(savings_final.get(currency, 0.0)))
    statement["dat_final_client"] = statement["currency_code"].map(lambda currency: float(dat_final.get(currency, 0.0)))

    statement = enrich_with_loans(statement, prepared.loans)

    if date_start is not None:
        start = pd.to_datetime(date_start, errors="coerce")
        if pd.notna(start):
            statement = statement.loc[statement["created_at"].ge(start)]
    if date_end is not None:
        end = pd.to_datetime(date_end, errors="coerce")
        if pd.notna(end):
            if not hasattr(date_end, "hour"):
                end = end + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            statement = statement.loc[statement["created_at"].le(end)]

    statement["controle_mouvement"] = np.select(
        [
            statement["mouvement_net_mpesa"].eq(0),
            statement["operation_reference"].astype("string").str.startswith("LIGNE-", na=False),
        ],
        ["Mouvement nul a verifier", "Reference absente"],
        default="OK",
    )
    statement = statement.sort_values(["created_at", "currency_code", "operation_reference"]).reset_index(drop=True)

    summary = build_customer_summary(statement, dat_client, loans_client, str(customer_id))
    diagnostics = build_diagnostics(prepared, str(customer_id), statement)
    g2_dat = build_g2_dat_crosscheck(prepared, str(customer_id))
    return {
        "customer_id": str(customer_id),
        "extrait": format_statement_columns(statement),
        "synthese": summary,
        "dat_final": dat_client,
        "mouvements_dat": dat_events,
        "mouvements_epargne": savings_events,
        "credits": loans_client,
        "g2_dat": g2_dat,
        "diagnostics": diagnostics,
    }


def enrich_with_loans(statement: pd.DataFrame, loans: pd.DataFrame) -> pd.DataFrame:
    result = statement.copy()
    if loans.empty or "loan_id" not in loans.columns:
        for column in [
            "loan_id",
            "loan_amount",
            "loan_balance",
            "amount_paid",
            "outstanding_principle",
            "outstanding_interest",
            "outstanding_penalty_fees",
            "status_name",
            "due_date",
        ]:
            result[column] = np.nan
        return result
    loan_columns = [
        column
        for column in [
            "loan_id",
            "loan_amount",
            "loan_balance",
            "amount_paid",
            "outstanding_principle",
            "outstanding_interest",
            "outstanding_penalty_fees",
            "status_name",
            "due_date",
        ]
        if column in loans.columns
    ]
    loan_frame = loans[loan_columns].drop_duplicates("loan_id").copy()
    return result.merge(loan_frame, left_on="reference_credit_operation", right_on="loan_id", how="left")


def build_customer_summary(statement: pd.DataFrame, dat_client: pd.DataFrame, loans_client: pd.DataFrame, customer_id: str) -> pd.DataFrame:
    if statement.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for currency, group in statement.groupby("currency_code", sort=True, dropna=False):
        real_balance = bool(group["solde_mpesa_disponible"].fillna(False).all())
        loan_balance = 0.0
        loan_count = 0
        if not loans_client.empty and "currency_code" in loans_client.columns:
            loans_currency = loans_client.loc[loans_client["currency_code"].eq(currency)]
            loan_count = int(loans_currency["loan_id"].nunique()) if "loan_id" in loans_currency.columns else len(loans_currency)
            if "loan_balance" in loans_currency.columns:
                loan_balance = float(pd.to_numeric(loans_currency["loan_balance"], errors="coerce").fillna(0).sum())
        rows.append(
            {
                "customer_id": customer_id,
                "Nom_client": concat_unique(group["Nom_client"]) if "Nom_client" in group.columns else "",
                "telephone": concat_unique(group["telephone"]),
                "devise": currency,
                "nombre_operations_mpesa": int(len(group)),
                "premiere_transaction": group["created_at"].min(),
                "derniere_transaction": group["created_at"].max(),
                "total_entrees_mpesa": float(group["entree_mpesa"].sum()),
                "total_sorties_mpesa": float(group["sortie_mpesa"].sum()),
                "mouvement_net": float(group["mouvement_net_mpesa"].sum()),
                "solde_mpesa_final": group["solde_mpesa_apres"].iloc[-1] if real_balance else np.nan,
                "solde_mpesa_est_reel": real_balance,
                "epargne_courante_finale": float(group["epargne_courante_finale"].iloc[-1]),
                "dat_final": float(group["dat_final_client"].iloc[-1]),
                "nombre_dat": int(dat_client["currency_code"].eq(currency).sum()) if not dat_client.empty and "currency_code" in dat_client.columns else 0,
                "nombre_credits": loan_count,
                "solde_credit_total": loan_balance,
            }
        )
    return pd.DataFrame(rows)


def build_diagnostics(prepared: MpesaPreparedData, customer_id: str | None = None, statement: pd.DataFrame | None = None) -> pd.DataFrame:
    tx = prepared.transactions
    diagnostics: list[dict[str, object]] = []

    def add(control: str, value: int | str, status: str, detail: str = "") -> None:
        diagnostics.append({"controle": control, "valeur": value, "statut": status, "detail": detail})

    if tx.empty:
        add("Transactions chargees", 0, "A verifier", "Aucun fichier Transactions exploitable.")
        if not prepared.g2_transactions.empty:
            add("Transactions G2 chargees", int(len(prepared.g2_transactions)), "Information")
        return pd.DataFrame(diagnostics)

    add("Lignes sans customer_id", int(tx["customer_id"].apply(_is_empty_text).sum()) if "customer_id" in tx.columns else len(tx), "A verifier")
    reference_missing = 0
    if "reference_id" in tx.columns:
        reference_missing += int(tx["reference_id"].apply(_is_empty_text).sum())
    add("Lignes sans reference_id", reference_missing, "OK" if reference_missing == 0 else "A verifier")
    ref_no_missing = int(tx["ref_no"].apply(_is_empty_text).sum()) if "ref_no" in tx.columns else len(tx)
    add("Lignes sans ref_no", ref_no_missing, "OK" if ref_no_missing == 0 else "Information")
    invalid_dates = int(pd.to_datetime(tx["created_at"], errors="coerce").isna().sum()) if "created_at" in tx.columns else len(tx)
    add("Dates invalides", invalid_dates, "OK" if invalid_dates == 0 else "A verifier")
    dr_values = numeric_column(tx, "dr")
    cr_values = numeric_column(tx, "cr")
    zero_moves = int((dr_values.eq(0) & cr_values.eq(0)).sum())
    add("Mouvements dr = 0 et cr = 0", zero_moves, "OK" if zero_moves == 0 else "A verifier")
    both_dr_cr = int((dr_values.gt(0) & cr_values.gt(0)).sum())
    add("Lignes avec dr > 0 et cr > 0", both_dr_cr, "OK" if both_dr_cr == 0 else "A verifier")
    negative_balance = int((numeric_column(tx, "bal_before").lt(0) | numeric_column(tx, "bal_after").lt(0)).sum())
    add("Soldes bal_before/bal_after negatifs", negative_balance, "OK" if negative_balance == 0 else "A verifier")
    empty_currency = int(tx["currency_code"].apply(_is_empty_text).sum()) if "currency_code" in tx.columns else len(tx)
    add("currency_code vide", empty_currency, "OK" if empty_currency == 0 else "A verifier")
    unknown_account = int((~tx["account_type"].isin(KNOWN_ACCOUNT_TYPES)).sum()) if "account_type" in tx.columns else 0
    add("account_type inconnu", unknown_account, "OK" if unknown_account == 0 else "A verifier")
    duplicates = int(tx.duplicated(subset=[column for column in ["customer_id", "created_at", "ref_no", "reference_id", "dr", "cr"] if column in tx.columns]).sum())
    add("Doublons potentiels", duplicates, "OK" if duplicates == 0 else "A verifier")
    if not prepared.g2_transactions.empty:
        g2_missing_phone = (
            int(prepared.g2_transactions["phone_prefixe"].isna().sum())
            if "phone_prefixe" in prepared.g2_transactions.columns
            else int(len(prepared.g2_transactions))
        )
        add("Transactions G2 chargees", int(len(prepared.g2_transactions)), "Information")
        add("Transactions G2 sans telephone exploitable", g2_missing_phone, "OK" if g2_missing_phone == 0 else "A verifier")

    if customer_id:
        clients_dat = set(prepared.fixed_savings["customer_id"].dropna().astype(str)) if not prepared.fixed_savings.empty and "customer_id" in prepared.fixed_savings.columns else set()
        clients_savings = set(prepared.current_savings["customer_id"].dropna().astype(str)) if not prepared.current_savings.empty and "customer_id" in prepared.current_savings.columns else set()
        add("Client sans fichier DAT", int(str(customer_id) not in clients_dat), "OK" if str(customer_id) in clients_dat else "Information")
        add("Client sans compte epargne", int(str(customer_id) not in clients_savings), "OK" if str(customer_id) in clients_savings else "Information")
        if statement is not None and not statement.empty:
            dat_refs = statement["reference_dat_operation"].astype("string").fillna("")
            credit_refs = statement["reference_credit_operation"].astype("string").fillna("")
            known_loans = set(prepared.loans["loan_id"].dropna().astype(str)) if not prepared.loans.empty and "loan_id" in prepared.loans.columns else set()
            unknown_credit_refs = int(credit_refs.ne("").sum()) if not known_loans else int((credit_refs.ne("") & ~credit_refs.isin(known_loans)).sum())
            add("References DAT detectees", int(dat_refs.ne("").sum()), "Information")
            add("References credit non reconnues", unknown_credit_refs, "OK" if unknown_credit_refs == 0 else "A verifier")

    return pd.DataFrame(diagnostics)


def format_statement_columns(statement: pd.DataFrame) -> pd.DataFrame:
    ordered = [
        "created_at",
        "customer_id",
        "Nom_client",
        "mode_rapprochement_nom_client",
        "telephone",
        "currency_code",
        "type_operation",
        "operation_reference",
        "references_internes",
        "reference_dat_operation",
        "reference_credit_operation",
        "descriptions",
        "entree_mpesa",
        "sortie_mpesa",
        "mouvement_net_mpesa",
        "solde_mpesa_avant",
        "solde_mpesa_apres",
        "cumul_net_depuis_debut_fichier",
        "solde_epargne_au_moment",
        "solde_dat_operation_avant",
        "solde_dat_operation_apres",
        "variation_dat_operation",
        "solde_dat_total_au_moment",
        "dat_final_client",
        "epargne_courante_finale",
        "loan_id",
        "loan_amount",
        "loan_balance",
        "amount_paid",
        "outstanding_principle",
        "outstanding_interest",
        "outstanding_penalty_fees",
        "status_name",
        "due_date",
        "controle_mouvement",
        "nombre_lignes_comptables",
    ]
    present = [column for column in ordered if column in statement.columns]
    rest = [column for column in statement.columns if column not in present]
    return statement[present + rest].copy()


def _pdf_number(value: Any, *, decimals: int = 0) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if pd.isna(number):
        return "-"
    return f"{number:,.{decimals}f}".replace(",", " ")


def _retention_svg(monthly: pd.DataFrame) -> str:
    if monthly.empty:
        return ""
    charts: list[str] = []
    colors = {"retention_m1_pct": "#17805c", "retention_90j_pct": "#173f73"}
    labels = {"retention_m1_pct": "Retention M+1", "retention_90j_pct": "Retention 90 jours"}
    for currency, frame in monthly.groupby("currency_code", dropna=False):
        frame = frame.sort_values("periode").reset_index(drop=True)
        if frame[["retention_m1_pct", "retention_90j_pct"]].notna().sum().sum() == 0:
            continue
        width, height = 760, 270
        left, right, top, bottom = 55, 22, 35, 48
        plot_width = width - left - right
        plot_height = height - top - bottom
        count = max(len(frame), 1)

        def x_position(index: int) -> float:
            return left + (plot_width / max(count - 1, 1)) * index

        def y_position(value: float) -> float:
            return top + plot_height * (1 - max(0.0, min(100.0, value)) / 100)

        svg_parts = [
            f'<svg class="retention-chart" viewBox="0 0 {width} {height}" role="img" '
            f'aria-label="Evolution de la retention {escape(str(currency))}">',
            f'<text x="{left}" y="20" class="chart-title">Devise {escape(str(currency))}</text>',
        ]
        for tick in [0, 25, 50, 75, 100]:
            y = y_position(float(tick))
            svg_parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
            svg_parts.append(f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" class="axis-label">{tick}%</text>')
        label_step = max(1, int(np.ceil(count / 6)))
        for index, month in enumerate(frame["mois"].astype(str)):
            if index % label_step == 0 or index == count - 1:
                x = x_position(index)
                svg_parts.append(f'<text x="{x:.1f}" y="{height-18}" text-anchor="middle" class="axis-label">{escape(month)}</text>')
        for column in ["retention_m1_pct", "retention_90j_pct"]:
            points: list[tuple[float, float, float]] = []
            for index, value in enumerate(pd.to_numeric(frame[column], errors="coerce")):
                if pd.notna(value):
                    points.append((x_position(index), y_position(float(value)), float(value)))
            if points:
                polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
                svg_parts.append(
                    f'<polyline points="{polyline}" fill="none" stroke="{colors[column]}" stroke-width="3"/>'
                )
                for x, y, value in points:
                    svg_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{colors[column]}"/>')
                    svg_parts.append(
                        f'<text x="{x:.1f}" y="{y-8:.1f}" text-anchor="middle" class="point-label">{value:.0f}%</text>'
                    )
        legend_x = width - 300
        for offset, column in enumerate(["retention_m1_pct", "retention_90j_pct"]):
            x = legend_x + offset * 150
            svg_parts.append(f'<line x1="{x}" y1="18" x2="{x+24}" y2="18" stroke="{colors[column]}" stroke-width="3"/>')
            svg_parts.append(f'<text x="{x+30}" y="22" class="legend">{labels[column]}</text>')
        svg_parts.append("</svg>")
        charts.append("".join(svg_parts))
    return "".join(charts)


def _html_table(frame: pd.DataFrame, columns: list[str], labels: dict[str, str], *, limit: int = 80) -> str:
    present = [column for column in columns if column in frame.columns]
    if frame.empty or not present:
        return '<p class="empty">Aucune donnee disponible.</p>'
    display = frame[present].head(limit).rename(columns=labels).copy()
    for column in display.columns:
        source_name = next((key for key, label in labels.items() if label == column), column)
        if source_name.endswith("_pct"):
            display[column] = pd.to_numeric(display[column], errors="coerce").map(
                lambda value: f"{value:.1f}%" if pd.notna(value) else "-"
            )
        elif any(token in source_name for token in ["montant", "solde", "volume"]):
            display[column] = pd.to_numeric(display[column], errors="coerce").map(
                lambda value: _pdf_number(value, decimals=2)
            )
        else:
            display[column] = display[column].where(display[column].notna(), "-")
    return display.to_html(index=False, escape=True, border=0, classes="report-table")


def _g2_executive_context(report: dict[str, Any]) -> dict[str, Any]:
    daily_pivot = report.get("rapport_journalier_pivot", pd.DataFrame())
    g2_dat = report.get("g2_dat", pd.DataFrame())
    monthly = report.get("retention_mensuelle", pd.DataFrame())

    active_items: list[str] = []
    retention_items: list[str] = []
    latest_retention_rows: list[dict[str, object]] = []
    chart_blocks: list[pd.DataFrame] = []
    if not monthly.empty:
        for currency, frame in monthly.groupby("currency_code", dropna=False):
            frame = frame.sort_values("periode")
            latest = frame.iloc[-1]
            active_items.append(
                f"{currency} : {_pdf_number(latest.get('clients_actifs_mois_base'))} client(s) actif(s)"
            )
            eligible_m1 = frame.dropna(subset=["retention_m1_pct"])
            eligible_90 = frame.dropna(subset=["retention_90j_pct"])
            m1_text = f"{eligible_m1.iloc[-1]['retention_m1_pct']:.1f}%" if not eligible_m1.empty else "non calculable"
            day90_text = f"{eligible_90.iloc[-1]['retention_90j_pct']:.1f}%" if not eligible_90.empty else "non calculable"
            retention_items.append(f"{currency} : M+1 {m1_text}, 90 jours {day90_text}")
            latest_retention_rows.append(
                {
                    "Devise": currency,
                    "Retention M+1": m1_text,
                    "Retention 90 jours": day90_text,
                }
            )
            eligible_periods = int(frame[["retention_m1_pct", "retention_90j_pct"]].notna().any(axis=1).sum())
            if eligible_periods >= 6:
                chart_blocks.append(frame)

    flow_items: list[str] = []
    if not daily_pivot.empty:
        for _, row in daily_pivot.iterrows():
            currency = row.get("currency_code", "-")
            flow_items.append(
                f"{currency} : entrees {_pdf_number(row.get('montant_total_entrees'), decimals=2)}, "
                f"sorties {_pdf_number(row.get('montant_total_sorties'), decimals=2)}, "
                f"net {_pdf_number(row.get('solde_net_flux'), decimals=2)}"
            )

    control_text = ""
    if not g2_dat.empty:
        if "statut_rapprochement" in g2_dat.columns:
            reference_status = g2_dat["statut_rapprochement"].astype("string").fillna("")
            exact = int(reference_status.eq("Rapproche exact").sum())
            with_gap = int(reference_status.eq("Rapproche avec ecart").sum())
            unmatched = int(reference_status.eq("Non rapproche").sum())
            anomalies = int(
                g2_dat.get("est_anomalie", pd.Series(False, index=g2_dat.index))
                .fillna(False)
                .astype(bool)
                .sum()
            )
            total = int(len(g2_dat))
            rate = 100 * exact / total if total else 0
            control_text = (
                f"Rapprochement Receipt No/ref_no : {exact}/{total} exact(s), soit {rate:.1f}%; "
                f"{with_gap} avec ecart, {unmatched} non rapproche(s), {anomalies} anomalie(s) au total."
            )
        else:
            status = g2_dat.get("statut_rapprochement_dat", pd.Series("", index=g2_dat.index)).astype("string")
            dat_absent = bool(status.str.contains("Fichier DAT absent", case=False, na=False).all())
            if dat_absent:
                control_text = "Rapprochement G2/DAT non evalue : fichier DAT non charge."
            else:
                matched = int(
                    g2_dat.get("customer_id_dat", pd.Series(dtype="string"))
                    .astype("string").fillna("").ne("").sum()
                )
                total = int(len(g2_dat))
                rate = 100 * matched / total if total else 0
                control_text = f"Rapprochement G2/DAT : {matched}/{total} entree(s), soit {rate:.1f}%."

    has_retention = bool(
        not monthly.empty
        and monthly[["retention_m1_pct", "retention_90j_pct"]].notna().any().any()
    )
    attention_text = (
        "Les mois les plus recents restent provisoires tant que leur fenetre de suivi n'est pas terminee."
        if has_retention
        else "La fidelisation M+1 et a 90 jours exige un historique couvrant les mois suivants."
    )
    return {
        "active_text": "; ".join(active_items) or "Aucune activite client eligible.",
        "flow_text": "; ".join(flow_items) or "Aucun flux disponible.",
        "retention_text": "; ".join(retention_items) or "Non calculable sur la periode chargee.",
        "control_text": control_text,
        "attention_text": attention_text,
        "has_retention": has_retention,
        "latest_retention": pd.DataFrame(latest_retention_rows),
        "chart_monthly": concat_frames_stable(chart_blocks) if chart_blocks else pd.DataFrame(),
    }


def build_g2_dat_pdf_html(
    report: dict[str, Any],
    *,
    period_text: str,
    direction_label: str,
    generated_at: pd.Timestamp | None = None,
) -> str:
    """Construit la version courte destinee a la Direction generale."""
    daily_pivot = report.get("rapport_journalier_pivot", pd.DataFrame())
    daily_synthese = report.get("rapport_journalier_synthese", pd.DataFrame())
    generated_at = generated_at if generated_at is not None else pd.Timestamp.now()
    context = _g2_executive_context(report)

    flow_table = _html_table(
        daily_pivot,
        ["currency_code", "nombre_entrees", "montant_total_entrees", "nombre_sorties", "montant_total_sorties", "solde_net_flux"],
        {
            "currency_code": "Devise", "nombre_entrees": "Nb entrees", "montant_total_entrees": "Montant entrees",
            "nombre_sorties": "Nb sorties", "montant_total_sorties": "Montant sorties", "solde_net_flux": "Solde net",
        },
    )
    classified = daily_synthese.copy()
    if not classified.empty and "details_rapport" in classified.columns:
        classified = classified.loc[~classified["details_rapport"].astype("string").str.startswith("Total ", na=False)]
    operation_table = _html_table(
        classified,
        ["currency_code", "sens_flux", "details_rapport", "nombre", "montant"],
        {"currency_code": "Devise", "sens_flux": "Sens", "details_rapport": "Operation", "nombre": "Nombre", "montant": "Montant"},
    )
    retention_table = _html_table(
        context["latest_retention"],
        ["Devise", "Retention M+1", "Retention 90 jours"],
        {},
    )
    chart_html = _retention_svg(context["chart_monthly"])
    control_bullet = (
        f'<li><strong>Controle.</strong> {escape(context["control_text"])}</li>'
        if context["control_text"] else ""
    )
    retention_section = (
        f'<h2>Fidelisation</h2><p>{escape(context["retention_text"])}</p>{chart_html}{retention_table}'
        if context["has_retention"]
        else f'<div class="note"><strong>Point de vigilance.</strong> {escape(context["attention_text"])}</div>'
    )

    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Rapport M-PESA - G2/DAT</title>
<style>
@page {{ size: A4; margin: 12mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Arial, Helvetica, sans-serif; color: #18314f; margin: 0; font-size: 9.5pt; line-height: 1.3; }}
h1 {{ font-size: 22pt; color: #12385f; margin: 0 0 3px; }}
h2 {{ font-size: 13.5pt; color: #12385f; margin: 14px 0 6px; border-bottom: 2px solid #dbe6f1; padding-bottom: 3px; page-break-after: avoid; }}
h3 {{ font-size: 11pt; color: #173f73; margin: 10px 0 5px; page-break-after: avoid; }}
p {{ margin: 4px 0 7px; }}
.meta {{ color: #5d7187; margin-bottom: 10px; }}
.summary {{ background: #edf5fb; border-left: 5px solid #2b6ea6; padding: 8px 12px; border-radius: 4px; }}
.summary h2 {{ border: 0; margin: 0 0 5px; font-size: 12.5pt; }}
.summary ul {{ margin: 2px 0; padding-left: 18px; }}
.report-table {{ width: 100%; border-collapse: collapse; margin: 4px 0 9px; font-size: 8.2pt; }}
.report-table th {{ background: #1f4e78; color: white; padding: 5px; text-align: left; }}
.report-table td {{ border-bottom: 1px solid #dce4eb; padding: 4px 5px; }}
.report-table tr {{ page-break-inside: avoid; }}
.retention-chart {{ width: 100%; height: auto; display: block; margin: 3px 0 8px; page-break-inside: avoid; }}
.chart-title {{ font-size: 13px; font-weight: bold; fill: #173f73; }}
.grid {{ stroke: #dfe7ee; stroke-width: 1; }}
.axis-label, .legend {{ font-size: 10px; fill: #5d7187; }}
.point-label {{ font-size: 9px; font-weight: bold; fill: #20364d; }}
.note {{ background: #fff7e8; border-left: 4px solid #d69a25; padding: 7px 9px; margin: 9px 0; }}
.empty {{ color: #6c7d8c; font-style: italic; }}
.footer-note {{ color: #60758a; font-size: 8pt; margin-top: 10px; }}
</style></head><body>
<h1>Rapport M-PESA - G2/DAT</h1>
<p class="meta">{escape(period_text)} | Sens : {escape(direction_label)} | {generated_at:%d/%m/%Y}</p>
<section class="summary"><h2>Synthese executive</h2><ul>
<li><strong>Activite.</strong> {escape(context["active_text"])}</li>
<li><strong>Flux financiers.</strong> {escape(context["flow_text"])}</li>
{control_bullet}
</ul></section>
<h2>Flux par devise</h2>{flow_table}
<h3>Principales operations</h3>{operation_table}
{retention_section}
</body></html>"""


def _find_pdf_browser() -> Path | None:
    candidates = [
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def create_g2_dat_pdf(
    report: dict[str, Any],
    *,
    period_text: str,
    direction_label: str,
) -> bytes:
    """Convertit le rapport G2/DAT statique en PDF via Edge/Chrome headless."""
    browser = _find_pdf_browser()
    if browser is None:
        raise RuntimeError("Microsoft Edge, Google Chrome ou Chromium est requis pour generer le PDF.")
    html_content = build_g2_dat_pdf_html(
        report,
        period_text=period_text,
        direction_label=direction_label,
    )
    with tempfile.TemporaryDirectory(prefix="mpesa_g2_pdf_") as temp_dir:
        temp_path = Path(temp_dir)
        html_path = temp_path / "rapport_g2_dat.html"
        pdf_path = temp_path / "rapport_g2_dat.pdf"
        html_path.write_text(html_content, encoding="utf-8")
        command = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            f"--user-data-dir={temp_path / 'browser_profile'}",
            f"--print-to-pdf={pdf_path}",
            html_path.as_uri(),
        ]
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=90,
            creationflags=creation_flags,
            check=False,
        )
        if completed.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size == 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "conversion sans fichier de sortie"
            raise RuntimeError(f"Impossible de generer le PDF G2/DAT : {message[:300]}")
        return pdf_path.read_bytes()


def create_g2_dat_word(
    report: dict[str, Any],
    *,
    period_text: str,
    direction_label: str,
    generated_at: pd.Timestamp | None = None,
) -> bytes:
    """Genere la version Word courte et editable destinee a la Direction generale."""
    try:
        from docx import Document
        from docx.enum.section import WD_ORIENT, WD_SECTION
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Cm, Pt, RGBColor
    except ImportError as exc:
        raise RuntimeError("La dependance python-docx est requise pour generer le rapport Word.") from exc

    daily_pivot = report.get("rapport_journalier_pivot", pd.DataFrame())
    daily_synthese = report.get("rapport_journalier_synthese", pd.DataFrame())
    transaction_detail = report.get("rapport_journalier_detail", pd.DataFrame())
    if not isinstance(daily_pivot, pd.DataFrame) or daily_pivot.empty:
        daily_pivot = build_entry_pivot(transaction_detail)
    generated_at = generated_at if generated_at is not None else pd.Timestamp.now()
    word_report = dict(report)
    word_report["rapport_journalier_pivot"] = daily_pivot
    context = _g2_executive_context(word_report)

    classified = daily_synthese.copy()
    if not classified.empty and "details_rapport" in classified.columns:
        classified = classified.loc[
            ~classified["details_rapport"].astype("string").str.startswith("Total ", na=False)
        ]

    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(1.2)
    section.bottom_margin = Cm(1.2)
    section.left_margin = Cm(1.25)
    section.right_margin = Cm(1.25)
    section.start_type = WD_SECTION.NEW_PAGE

    styles = document.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9)
    for style_name in ["Title", "Heading 1", "Heading 2"]:
        styles[style_name].font.name = "Aptos Display"
        styles[style_name].font.color.rgb = RGBColor(18, 56, 95)
    styles["Title"].font.size = Pt(22)
    styles["Heading 1"].font.size = Pt(14)
    styles["Heading 2"].font.size = Pt(11)

    title = document.add_paragraph(style="Title")
    title.paragraph_format.space_after = Pt(2)
    title.add_run("Rapport M-PESA - G2/DAT")
    meta = document.add_paragraph()
    meta.paragraph_format.space_after = Pt(7)
    meta_run = meta.add_run(f"{period_text} | Sens : {direction_label} | {generated_at:%d/%m/%Y}")
    meta_run.font.size = Pt(8.5)
    meta_run.font.color.rgb = RGBColor(93, 113, 135)

    document.add_heading("Synthese executive", level=1)

    def add_summary_bullet(label: str, text: str) -> None:
        paragraph = document.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(2)
        bold_run = paragraph.add_run(f"{label}. ")
        bold_run.bold = True
        paragraph.add_run(text)

    add_summary_bullet("Activite", context["active_text"])
    add_summary_bullet("Flux financiers", context["flow_text"])
    if context["control_text"]:
        add_summary_bullet("Controle", context["control_text"])

    def set_cell_shading(cell: Any, fill: str) -> None:
        cell_properties = cell._tc.get_or_add_tcPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), fill)
        cell_properties.append(shading)

    def add_table(
        frame: pd.DataFrame,
        columns: list[str],
        labels: dict[str, str],
        *,
        font_size: float = 8,
        amount_decimals: int = 2,
        column_widths_cm: dict[str, float] | None = None,
    ) -> Any | None:
        present = [column for column in columns if column in frame.columns]
        if frame.empty or not present:
            document.add_paragraph("Aucune donnee disponible.")
            return None
        table = document.add_table(rows=1, cols=len(present))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = column_widths_cm is None
        header_properties = table.rows[0]._tr.get_or_add_trPr()
        repeat_header = OxmlElement("w:tblHeader")
        repeat_header.set(qn("w:val"), "true")
        header_properties.append(repeat_header)
        for index, column in enumerate(present):
            cell = table.rows[0].cells[index]
            cell.text = labels.get(column, column)
            if column_widths_cm and column in column_widths_cm:
                cell.width = Cm(column_widths_cm[column])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_shading(cell, "1F4E78")
            for run in cell.paragraphs[0].runs:
                run.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.size = Pt(font_size)
        for _, row in frame[present].iterrows():
            cells = table.add_row().cells
            for index, column in enumerate(present):
                value = row.get(column)
                if any(token in column for token in ["montant", "solde", "volume"]):
                    text = _pdf_number(value, decimals=amount_decimals)
                elif str(column).endswith("_pct"):
                    text = f"{float(value):.1f}%" if pd.notna(value) else "-"
                elif column in {"retenu_m1", "retenu_90j"}:
                    text = "-" if pd.isna(value) else "Oui" if bool(value) else "Non"
                elif column in {"date", "compte_cree"}:
                    date_value = pd.to_datetime(value, errors="coerce")
                    text = f"{date_value:%d/%m/%Y %H:%M:%S}" if pd.notna(date_value) else "-"
                elif column == "premier_retour":
                    date_value = pd.to_datetime(value, errors="coerce")
                    text = f"{date_value:%d/%m/%Y}" if pd.notna(date_value) else "-"
                else:
                    text = "-" if pd.isna(value) else str(value)
                cells[index].text = text
                if column_widths_cm and column in column_widths_cm:
                    cells[index].width = Cm(column_widths_cm[column])
                cells[index].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                for paragraph in cells[index].paragraphs:
                    paragraph.paragraph_format.space_after = Pt(0)
                    for run in paragraph.runs:
                        run.font.size = Pt(font_size)
        document.add_paragraph().paragraph_format.space_after = Pt(0)
        return table

    document.add_heading("Synthese des flux G2 par devise", level=1)
    add_table(
        daily_pivot,
        ["currency_code", "nombre_entrees", "montant_total_entrees", "nombre_sorties", "montant_total_sorties", "solde_net_flux"],
        {
            "currency_code": "Devise", "nombre_entrees": "Nb entrees", "montant_total_entrees": "Montant entrees",
            "nombre_sorties": "Nb sorties", "montant_total_sorties": "Montant sorties", "solde_net_flux": "Solde net",
        },
    )
    document.add_heading("Principales operations", level=2)
    add_table(
        classified,
        ["currency_code", "sens_flux", "details_rapport", "nombre", "montant"],
        {"currency_code": "Devise", "sens_flux": "Sens", "details_rapport": "Operation", "nombre": "Nombre", "montant": "Montant"},
    )

    if context["has_retention"]:
        document.add_heading("Fidelisation", level=1)
        paragraph = document.add_paragraph(context["retention_text"])
        paragraph.paragraph_format.space_after = Pt(4)
        add_table(
            context["latest_retention"],
            ["Devise", "Retention M+1", "Retention 90 jours"],
            {},
        )
    else:
        document.add_heading("Point de vigilance", level=1)
        warning = document.add_paragraph(context["attention_text"])
        warning.paragraph_format.space_after = Pt(5)
        warning.runs[0].font.color.rgb = RGBColor(156, 103, 10)

    if isinstance(transaction_detail, pd.DataFrame) and not transaction_detail.empty:
        detail = transaction_detail.copy()
        detail["currency_code"] = clean_text(
            detail.get("currency_code", pd.Series("", index=detail.index))
        ).str.upper().replace("", "SANS DEVISE")
        detail["date"] = pd.to_datetime(
            detail.get("date", pd.Series(pd.NaT, index=detail.index)), errors="coerce"
        )
        detail = detail.sort_values(
            ["currency_code", "date"], ascending=[True, False], na_position="last"
        ).reset_index(drop=True)
        detail_section = document.add_section(WD_SECTION.NEW_PAGE)
        detail_section.orientation = WD_ORIENT.LANDSCAPE
        detail_section.page_width, detail_section.page_height = (
            detail_section.page_height,
            detail_section.page_width,
        )
        detail_section.top_margin = Cm(1.0)
        detail_section.bottom_margin = Cm(1.0)
        detail_section.left_margin = Cm(0.5)
        detail_section.right_margin = Cm(0.5)
        document.add_heading("Transactions", level=1)
        # detail_caption.paragraph_format.space_after = Pt(4)
        add_table(
            detail,
            G2_CLASSIFIED_TRANSACTION_COLUMNS,
            {column: column for column in G2_CLASSIFIED_TRANSACTION_COLUMNS},
            font_size=5.5,
            amount_decimals=2,
            column_widths_cm={
                "date": 2.7,
                "receipt_no": 2.1,
                "currency_code": 1.4,
                "details_rapport": 2.3,
                "opposite_party": 6.2,
                "duree": 1.6,
                "compte_cree": 2.7,
                "montant": 1.7,
                "montant_entree": 1.7,
                "montant_sortie": 1.7,
                "balance_numeric": 1.9,
            },
        )

    source = document.add_paragraph()
    source.paragraph_format.space_before = Pt(4)
    # source_run.italic = True
    # source_run.font.size = Pt(8)
    # source_run.font.color.rgb = RGBColor(96, 117, 138)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer.add_run("Rapport de synthese")
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(110, 125, 140)

    document.core_properties.title = "Rapport M-PESA - G2/DAT"
    document.core_properties.subject = "Synthese destinee a la Direction generale"
    document.core_properties.author = "Solution Controle Interne"
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def create_excel_export(report: dict[str, Any]) -> bytes:
    sheet_contract = [
        ("synthese", "Synthese"),
        ("extrait", "Extrait_MPESA"),
        ("dat_final", "DAT_Final"),
        ("forts_dat", "Forts_DAT"),
        ("portefeuille_dat", "Portefeuille_DAT"),
        ("mouvements_dat", "Mouvements_DAT"),
        ("mouvements_epargne", "Mouvements_Epargne"),
        ("credits", "Credits"),
        ("g2_dat", "G2_DAT"),
        ("rapport_g2_pivot", "Rapport_G2_Pivot"),
        ("rapport_g2_comptages", "Rapport_G2_Comptages"),
        ("rapport_g2_vertical", "Rapport_G2_Vertical"),
        ("rapport_g2_synthese", "Rapport_G2_Synthese"),
        ("rapport_g2_detail", "Rapport_G2_Detail"),
        ("rapport_journalier_pivot", "Rapport_Journalier_Pivot"),
        ("rapport_journalier_comptages", "Rapport_Journalier_Comptages"),
        ("rapport_journalier_vertical", "Rapport_Journalier_Vertical"),
        ("rapport_journalier_synthese", "Rapport_Journalier_Synthese"),
        ("rapport_journalier_detail", "Rapport_Journalier_Detail"),
        ("rapport_journalier_anomalies", "Anomalies_G2"),
        ("retention_mensuelle", "Retention_Mensuelle"),
        ("retention_operations", "Retention_Operations"),
        ("retention_detail", "Retention_Detail"),
        ("retention_definitions", "Retention_Definitions"),
        ("perfect_clients", "Perfect_Clients"),
        ("perfect_operations", "Perfect_Operations"),
        ("clients_perfect_dans_mpesa", "Perfect_M_PESA"),
        ("clients_perfect_dans_turbo", "Perfect_Turbo"),
        ("clients_perfect_dans_turbo_et_mpesa", "Perfect_Turbo_M_PESA"),
        ("clients_3_systemes", "Clients_3_Systemes"),
        ("diagnostics", "Diagnostics"),
    ]
    sheets = {
        sheet_name: report[report_key]
        for report_key, sheet_name in sheet_contract
        if report_key in report
    }
    if not sheets:
        sheets = {"Information": pd.DataFrame({"message": ["Aucune donnee a exporter."]})}
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, frame in sheets.items():
            safe_frame = frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()
            safe_frame.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            worksheet = writer.sheets[sheet_name[:31]]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for cell in worksheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(fill_type="solid", fgColor="1F4E78")
            for index, column in enumerate(safe_frame.columns, start=1):
                values = [str(column)] + ["" if pd.isna(value) else str(value) for value in safe_frame[column].head(300)]
                width = min(max(len(value) for value in values) + 2, 45)
                worksheet.column_dimensions[worksheet.cell(row=1, column=index).column_letter].width = width
                name = str(column).lower()
                if "date" in name or "created_at" in name:
                    number_format = "dd/mm/yyyy hh:mm:ss"
                elif any(token in name for token in ["solde", "montant", "entree", "sortie", "mouvement", "balance", "variation", "amount", "loan"]):
                    number_format = '#,##0.00'
                else:
                    number_format = None
                if number_format:
                    for row in range(2, len(safe_frame) + 2):
                        worksheet.cell(row=row, column=index).number_format = number_format
    buffer.seek(0)
    return buffer.getvalue()


def load_excel_file(file_like: Any, sheet_name: str | int | None = 0) -> pd.DataFrame:
    if file_like is None:
        return pd.DataFrame()
    return pd.read_excel(file_like, sheet_name=sheet_name)
