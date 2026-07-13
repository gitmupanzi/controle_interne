from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
from collections.abc import Iterable, Mapping

import pandas as pd


def canonical_column_key(value: object) -> str:
    """Return a stable key used only to compare heterogeneous headers."""
    text = unicodedata.normalize("NFKD", str(value).replace("\ufeff", "").replace("\xa0", " "))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^0-9a-z]+", "_", text.casefold()).strip("_")


@dataclass(frozen=True)
class DataSchema:
    name: str
    required: frozenset[str] = field(default_factory=frozenset)
    optional: frozenset[str] = field(default_factory=frozenset)
    aliases: Mapping[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class SchemaValidationResult:
    source: str
    schema_name: str
    missing: tuple[str, ...]
    available: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.missing

    def user_message(self) -> str:
        if self.is_valid:
            return f"{self.source} : schéma valide."
        available = ", ".join(self.available) if self.available else "aucune"
        return (
            f"{self.source} : colonnes obligatoires manquantes : {', '.join(self.missing)}. "
            f"Colonnes disponibles : {available}."
        )


class DataSchemaError(ValueError):
    def __init__(self, result: SchemaValidationResult):
        self.result = result
        super().__init__(result.user_message())


def _alias_lookup(schema: DataSchema) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical in (*schema.required, *schema.optional, *schema.aliases.keys()):
        lookup[canonical_column_key(canonical)] = canonical
    for canonical, aliases in schema.aliases.items():
        for alias in aliases:
            lookup[canonical_column_key(alias)] = canonical
    return lookup


def normalize_dataframe_headers(dataframe: pd.DataFrame, schema: DataSchema) -> pd.DataFrame:
    """Normalize known headers while preserving unknown source columns verbatim."""
    frame = dataframe.copy()
    lookup = _alias_lookup(schema)
    normalized = [lookup.get(canonical_column_key(column), str(column).strip()) for column in frame.columns]
    frame.columns = normalized

    # Coalesce aliases resolving to the same business column, without discarding values.
    if frame.columns.duplicated().any():
        columns: list[pd.Series] = []
        names: list[str] = []
        for name in dict.fromkeys(frame.columns):
            matching = frame.loc[:, frame.columns == name]
            series = matching.bfill(axis=1).iloc[:, 0]
            columns.append(series)
            names.append(name)
        frame = pd.concat(columns, axis=1)
        frame.columns = names
    return frame


def validate_dataframe_schema(
    dataframe: pd.DataFrame,
    schema: DataSchema,
    source: str,
    *,
    raise_on_missing: bool = False,
) -> SchemaValidationResult:
    available = tuple(str(column) for column in dataframe.columns)
    available_keys = {canonical_column_key(column) for column in available}
    aliases = _alias_lookup(schema)
    resolved = {aliases.get(key, key) for key in available_keys}
    missing = tuple(sorted(column for column in schema.required if column not in resolved))
    result = SchemaValidationResult(source, schema.name, missing, available)
    if raise_on_missing and missing:
        raise DataSchemaError(result)
    return result


def schema(
    name: str,
    required: Iterable[str],
    optional: Iterable[str] = (),
    aliases: Mapping[str, tuple[str, ...]] | None = None,
) -> DataSchema:
    return DataSchema(name, frozenset(required), frozenset(optional), aliases or {})


MPESA_TRANSACTIONS_SCHEMA = schema(
    "Transactions M-PESA",
    {
        "id", "customer_id", "msisdn1", "account_type", "reference_id", "currency_code",
        "dr", "cr", "bal_before", "bal_after", "ref_no", "description", "created_at",
    },
)
CURRENT_SAVINGS_SCHEMA = schema(
    "Épargne courante",
    {"customer_id", "msisdn", "product_name", "account_type", "balance", "currency_code", "created_at", "updated_at"},
)
FIXED_SAVINGS_SCHEMA = schema(
    "DAT",
    {"customer_id", "msisdn", "product_name", "account_type", "balance", "currency_code", "date_approved", "maturity_date"},
    {"created_at"},
)
G2_TRANSACTIONS_SCHEMA = schema(
    "Transactions G2",
    {"Receipt No", "Currency", "Opposite Party"},
    {
        "Completion Time", "Initiation Time", "Transaction Status", "Transaction Amount",
        "Paid In", "Withdrawn", "Balance", "Details", "Operation", "Reason Type",
        "Linked Transaction ID",
    },
    {
        "Receipt No": ("receipt_no", "Receipt No."),
        "Opposite Party": ("opposite_party",),
        "Currency": ("currency_code",),
    },
)
PERFECT_CLIENTS_SCHEMA = schema(
    "Clients Perfect",
    {"Phone_Prefixe"},
    {
        "id_client", "code_client", "num_manuel", "nom_complet", "sexe",
        "Phone_Brut", "Phone_243", "Statut_phone", "Is_phone_staff",
        "Tel_chiffres", "Commentaire_phone", "type_piece_identite",
        "numero_piece_identite", "type_client", "categorie_client",
        "gestionnaire", "client_perfect", "collecteur",
    },
    {
        "Phone_Prefixe": ("phone_prefixe", "Phone Prefixe", "Telephone normalise"),
    },
)
CUSTOMERS_SCHEMA = schema("Clients", {"msisdn1", "created_at"})
LOANS_SCHEMA = schema("Crédits", {"loan_id", "customer_id"})


SQL_OPERATIONS_SCHEMA = schema(
    "Opérations SQL",
    {"ID"},
    {"ID_TYPE_OPERATION", "DATE_OPERATION", "MONTANT_OPERATION", "ID_DEVISE", "ID_POINT_SERVICE", "ID_POINT_SERIVCE"},
)
SQL_OPERATIONS_API_SCHEMA = schema(
    "Opérations API SQL",
    {"CODE"},
    {"ID_TYPE_OPERATION", "DATE_OPERATION", "MONTANT_OPERATION", "ID_DEVISE", "ID_POINT_SERVICE", "ID_POINT_SERIVCE"},
)
SQL_HDPM_SCHEMA = schema(
    "Historique des mouvements SQL",
    {"ID_OPERATION"},
    {"ID_COMPTE", "MONTANT_OPERATION", "DATE_OPERATION", "DATE_VALEUR", "SENS"},
)
SQL_ADHERENTS_SCHEMA = schema(
    "Adhérents SQL",
    set(),
    {"ID_ADHERENT", "ID_COMPTE", "ID_POINT_SERIVCE"},
)

SQL_ROLE_SCHEMAS: dict[str, DataSchema] = {
    "operations": SQL_OPERATIONS_SCHEMA,
    "operations_api": SQL_OPERATIONS_API_SCHEMA,
    "hdpm": SQL_HDPM_SCHEMA,
    "hdpm_api": SQL_HDPM_SCHEMA,
    "adherents": SQL_ADHERENTS_SCHEMA,
}
