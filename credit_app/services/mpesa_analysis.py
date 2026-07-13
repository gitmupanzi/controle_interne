from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import re
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
    DataSchema,
    validate_dataframe_schema,
)


TRANSACTION_REQUIRED_COLUMNS = set(MPESA_TRANSACTIONS_SCHEMA.required)
CURRENT_SAVINGS_REQUIRED_COLUMNS = set(CURRENT_SAVINGS_SCHEMA.required)
FIXED_SAVINGS_REQUIRED_COLUMNS = set(FIXED_SAVINGS_SCHEMA.required)
G2_TRANSACTION_REQUIRED_COLUMNS = set(G2_TRANSACTIONS_SCHEMA.required)
CUSTOMERS_REQUIRED_COLUMNS = set(CUSTOMERS_SCHEMA.required)

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


@dataclass(frozen=True)
class MpesaPreparedData:
    transactions: pd.DataFrame
    current_savings: pd.DataFrame
    fixed_savings: pd.DataFrame
    loans: pd.DataFrame
    load_report: pd.DataFrame
    g2_transactions: pd.DataFrame = field(default_factory=pd.DataFrame)
    customers: pd.DataFrame = field(default_factory=pd.DataFrame)


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
) -> pd.DataFrame:
    """Filtre les transactions G2 sur Completion Time, bornes journalieres incluses."""
    if not isinstance(dataframe, pd.DataFrame) or dataframe.empty:
        return pd.DataFrame() if dataframe is None else dataframe.copy()
    if "completion_time" not in dataframe.columns:
        return dataframe.copy()

    frame = dataframe.copy()
    completion_time = pd.to_datetime(frame["completion_time"], errors="coerce")
    mask = completion_time.notna()
    if start_date is not None:
        mask &= completion_time.ge(pd.Timestamp(start_date).normalize())
    if end_date is not None:
        mask &= completion_time.lt(pd.Timestamp(end_date).normalize() + pd.Timedelta(days=1))
    return frame.loc[mask].reset_index(drop=True)


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


def build_g2_dat_crosscheck(prepared: MpesaPreparedData, customer_id: str | None = None) -> pd.DataFrame:
    g2 = prepared.g2_transactions
    fixed = prepared.fixed_savings
    transactions = prepared.transactions
    if g2.empty:
        return pd.DataFrame()

    output = g2.copy()
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
    details = normalize_label(row.get("details", ""))
    reference_dat = str(row.get("reference_dat_operation", "") or "").strip()
    references = normalize_label(row.get("references_transactions", ""))
    account_types = normalize_label(row.get("account_types_transactions", ""))
    descriptions = normalize_label(row.get("descriptions_transactions", ""))
    text = f"{references} {account_types} {descriptions}"
    if "bisoubisourepayment" in details:
        return "Remboursement prets"
    if reference_dat:
        return "DAT"
    if "ln" in references or "loan" in account_types or "principle" in account_types or "remboursement" in text:
        return "Remboursement prets"
    return "Depot normal"


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

    preferred_details = ["DAT", "Depot normal", "Remboursement prets"]
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

    ordered = ["currency_code"]
    for detail_name in preferred_details:
        ordered.extend([f"montant_{detail_name}", f"nombre_{detail_name}"])
    ordered.extend(["montant_total", "nombre_total"])
    rest = [column for column in pivot.columns if column not in ordered]
    return pivot[ordered + rest].sort_values("currency_code").reset_index(drop=True)


def build_entry_count_summary(detail: pd.DataFrame) -> pd.DataFrame:
    """Compte les DAT, depots normaux et remboursements, separement par devise."""
    columns = [
        "currency_code",
        "Nombre de DAT",
        "Nombre de depot normal",
        "Nombre de remboursement de pret",
        "Nombre total",
    ]
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
    for category in ["DAT", "Depot normal", "Remboursement prets"]:
        if category not in grouped.columns:
            grouped[category] = 0
    summary = grouped[["DAT", "Depot normal", "Remboursement prets"]].reset_index()
    summary = summary.rename(
        columns={
            "DAT": "Nombre de DAT",
            "Depot normal": "Nombre de depot normal",
            "Remboursement prets": "Nombre de remboursement de pret",
        }
    )
    summary["Nombre total"] = summary[
        ["Nombre de DAT", "Nombre de depot normal", "Nombre de remboursement de pret"]
    ].sum(axis=1)
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
    categories = ["DAT", "Depot normal", "Remboursement prets"]
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
        "details_rapport",
        "opposite_party",
        "Nom_client",
        "duree",
        "compte_cree",
        "montant",
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
        report.groupby(["currency_code", "details_rapport"], as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
        .sort_values(["currency_code", "details_rapport"])
    )
    totals = (
        report.groupby("currency_code", as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
    )
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
            "synthese": pd.DataFrame(),
            "pivot": pd.DataFrame(),
            "vertical_summary": pd.DataFrame(),
            "comptages": build_entry_count_summary(pd.DataFrame()),
        }

    report = g2.copy()
    report["receipt_no"] = clean_identifier(report.get("receipt_no", pd.Series("", index=report.index)))
    report["date"] = pd.to_datetime(report.get("completion_time"), errors="coerce")
    report["montant"] = numeric_column(report, "transaction_amount_numeric").abs()
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

    is_repayment = report.get("details", pd.Series("", index=report.index)).apply(normalize_label).str.contains(
        "bisoubisourepayment", regex=False, na=False
    )
    is_dat = report["dat_customer_id"].astype("string").fillna("").ne("") & ~is_repayment
    report["details_rapport"] = np.select(
        [is_repayment, is_dat],
        ["Remboursement prets", "DAT"],
        default="Depot normal",
    )
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
        ~is_dat
        & has_same_day_dat_phone
        & ~report.apply(lambda row: _is_round_savings_amount(row.get("montant"), row.get("currency_code")), axis=1)
    )
    report.loc[unusual_same_day_dat_amount, "details_rapport"] = "Remboursement prets"

    detail_columns = [
        "date",
        "receipt_no",
        "details_rapport",
        "opposite_party",
        "Nom_client",
        "phone_prefixe",
        "duree",
        "compte_cree",
        "montant",
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
    ]
    detail_columns = [column for column in detail_columns if column in report.columns]
    detail = report[detail_columns].sort_values(["currency_code", "date"], ascending=[True, False]).reset_index(drop=True)

    synthese = (
        detail.groupby(["currency_code", "details_rapport"], as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
        .sort_values(["currency_code", "details_rapport"])
    )
    totals = (
        detail.groupby("currency_code", as_index=False, dropna=False)
        .agg(nombre=("receipt_no", "count"), montant=("montant", "sum"))
    )
    totals["details_rapport"] = "Total " + totals["currency_code"].astype("string").fillna("")
    synthese = concat_frames_stable([synthese, totals[synthese.columns]]).reset_index(drop=True)
    return {
        "detail": detail,
        "synthese": synthese,
        "pivot": build_entry_pivot(detail),
        "vertical_summary": build_entry_vertical_summary(detail),
        "comptages": build_entry_count_summary(detail),
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


def create_excel_export(report: dict[str, Any]) -> bytes:
    sheets = {
        "Synthese": report.get("synthese", pd.DataFrame()),
        "Extrait_MPESA": report.get("extrait", pd.DataFrame()),
        "DAT_Final": report.get("dat_final", pd.DataFrame()),
        "Forts_DAT": report.get("forts_dat", pd.DataFrame()),
        "Portefeuille_DAT": report.get("portefeuille_dat", pd.DataFrame()),
        "Mouvements_DAT": report.get("mouvements_dat", pd.DataFrame()),
        "Mouvements_Epargne": report.get("mouvements_epargne", pd.DataFrame()),
        "Credits": report.get("credits", pd.DataFrame()),
        "G2_DAT": report.get("g2_dat", pd.DataFrame()),
        "Rapport_G2_Pivot": report.get("rapport_g2_pivot", pd.DataFrame()),
        "Rapport_G2_Comptages": report.get("rapport_g2_comptages", pd.DataFrame()),
        "Rapport_G2_Vertical": report.get("rapport_g2_vertical", pd.DataFrame()),
        "Rapport_G2_Synthese": report.get("rapport_g2_synthese", pd.DataFrame()),
        "Rapport_G2_Detail": report.get("rapport_g2_detail", pd.DataFrame()),
        "Rapport_Journalier_Pivot": report.get("rapport_journalier_pivot", pd.DataFrame()),
        "Rapport_Journalier_Comptages": report.get("rapport_journalier_comptages", pd.DataFrame()),
        "Rapport_Journalier_Vertical": report.get("rapport_journalier_vertical", pd.DataFrame()),
        "Rapport_Journalier_Synthese": report.get("rapport_journalier_synthese", pd.DataFrame()),
        "Rapport_Journalier_Detail": report.get("rapport_journalier_detail", pd.DataFrame()),
        "Diagnostics": report.get("diagnostics", pd.DataFrame()),
    }
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
