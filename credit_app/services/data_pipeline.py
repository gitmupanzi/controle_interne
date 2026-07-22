from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from collections.abc import Iterable

import pandas as pd

from credit_app.domain import (
    build_mapping_frame,
    build_missing_values_frame,
    build_quality_checks,
    build_standardized_dataframe,
)


@dataclass(frozen=True)
class CycleDetection:
    cycle_key: str | None
    confidence: float
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class CompilationAssessment:
    compatible: bool
    cycle_key: str | None
    reasons: tuple[str, ...]


CYCLE_NAME_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("conformite", ("cycle_conformite", "conformite_lbc_ft", "lbc_ft", "conformite")),
    ("operations_depot_retrait", ("operations_depot_retrait", "depots_et_retraits", "depot_retrait")),
    ("credit", ("cycle_credit", "credit_dashboard", "prets", "credit")),
    ("epargne", ("cycle_epargne", "epargne", "dat")),
    ("crm_clients", ("crm_clients", "cycle_crm", "crm")),
    ("caisse", ("caisse_et_guichet", "caisse_guichet", "caisse")),
    ("tresorerie", ("tresorerie_et_banque", "tresorerie", "banque")),
    ("comptable", ("comptable_et_financier", "comptable", "financier")),
    ("si", ("securite_systeme_information", "securite_si")),
    ("likelemba", ("likelemba",)),
    ("money_provider", ("money_provider", "mpesa", "mobile_money")),
)

CYCLE_COLUMN_HINTS: dict[str, frozenset[str]] = {
    "conformite": frozenset({"numero_alerte", "type_alerte", "etat_alerte", "statut_couverture", "source_declaration"}),
    "credit": frozenset({"dossier_id", "montant_accorde", "encours_credit", "par30", "date_decaissement"}),
    "epargne": frozenset({"compte_id", "solde_compte", "solde_epargne", "date_derniere_transaction"}),
    "crm_clients": frozenset({"client_id", "telephone", "email", "statut_client"}),
    "operations_depot_retrait": frozenset({"operation_id", "date_operation", "type_operation", "montant_operation"}),
    "caisse": frozenset({"caissier", "solde_theorique", "solde_physique", "ecart_caisse"}),
    "tresorerie": frozenset({"compte_bancaire", "solde_banque", "ecart_rapprochement"}),
    "comptable": frozenset({"journal", "debit", "credit", "numero_piece"}),
    "si": frozenset({"utilisateur", "profil_acces", "date_derniere_connexion"}),
    "likelemba": frozenset({"groupe_id", "nombre_membres", "cycle_groupe"}),
    "money_provider": frozenset({"numero_reference", "telephone", "type_operation", "montant_operation"}),
}


def normalize_filename(filename: str) -> str:
    stem = Path(filename).stem.replace("\ufeff", "")
    text = unicodedata.normalize("NFKD", stem)
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^0-9a-z]+", "_", text.casefold()).strip("_")


def detect_cycle(filename: str, columns: Iterable[object] = ()) -> CycleDetection:
    normalized_name = normalize_filename(filename)
    name_matches: list[tuple[str, str]] = []
    for cycle_key, patterns in CYCLE_NAME_PATTERNS:
        for pattern in patterns:
            if re.search(rf"(?:^|_){re.escape(pattern)}(?:_|$)", normalized_name):
                name_matches.append((cycle_key, pattern))
                break

    unique_name_cycles = {cycle for cycle, _ in name_matches}
    if len(unique_name_cycles) == 1:
        cycle_key = next(iter(unique_name_cycles))
        evidence = tuple(pattern for cycle, pattern in name_matches if cycle == cycle_key)
        return CycleDetection(cycle_key, 1.0, evidence)
    strong_matches = [
        (cycle, pattern)
        for cycle, pattern in name_matches
        if pattern.startswith("cycle_") or pattern == "operations_depot_retrait"
    ]
    if len({cycle for cycle, _ in strong_matches}) == 1 and strong_matches:
        cycle_key = strong_matches[0][0]
        return CycleDetection(cycle_key, 0.95, tuple(pattern for _, pattern in strong_matches))

    normalized_columns = {normalize_filename(str(column)) for column in columns}
    scores = {
        cycle_key: len(hints.intersection(normalized_columns))
        for cycle_key, hints in CYCLE_COLUMN_HINTS.items()
    }
    best_score = max(scores.values(), default=0)
    best_cycles = [cycle for cycle, score in scores.items() if score == best_score and score > 0]
    if len(best_cycles) == 1 and best_score >= 2:
        cycle_key = best_cycles[0]
        matched = tuple(sorted(CYCLE_COLUMN_HINTS[cycle_key].intersection(normalized_columns)))
        return CycleDetection(cycle_key, min(0.9, 0.5 + 0.1 * best_score), matched)

    evidence = tuple(sorted({pattern for _, pattern in name_matches}))
    return CycleDetection(None, 0.0, evidence)


def assess_compilation_compatibility(
    files: Iterable[tuple[str, Iterable[object], Iterable[str]]],
    *,
    minimum_schema_overlap: float = 0.6,
) -> CompilationAssessment:
    descriptors = [
        (filename, tuple(columns), tuple(sheets), detect_cycle(filename, columns))
        for filename, columns, sheets in files
    ]
    if len(descriptors) < 2:
        return CompilationAssessment(False, None, ("Au moins deux fichiers sont nécessaires.",))

    ambiguous = [filename for filename, _, _, detection in descriptors if detection.cycle_key is None]
    if ambiguous:
        return CompilationAssessment(
            False,
            None,
            ("Cycle non déterminé pour : " + ", ".join(ambiguous),),
        )
    cycles = {detection.cycle_key for _, _, _, detection in descriptors}
    if len(cycles) != 1:
        return CompilationAssessment(False, None, ("Les fichiers appartiennent à des cycles différents.",))
    cycle_key = next(iter(cycles))

    sheet_sets = [set(sheets) for _, _, sheets, _ in descriptors if sheets]
    if sheet_sets and not set.intersection(*sheet_sets):
        return CompilationAssessment(False, cycle_key, ("Aucune feuille Excel commune n'a été détectée.",))

    schemas = [{normalize_filename(str(column)) for column in columns} for _, columns, _, _ in descriptors]
    reference = schemas[0]
    overlaps: list[float] = []
    for candidate in schemas[1:]:
        denominator = max(min(len(reference), len(candidate)), 1)
        overlaps.append(len(reference.intersection(candidate)) / denominator)
    if overlaps and min(overlaps) < float(minimum_schema_overlap):
        return CompilationAssessment(
            False,
            cycle_key,
            (f"Les schémas de colonnes ne sont pas assez proches ({min(overlaps):.0%} de correspondance).",),
        )
    return CompilationAssessment(True, cycle_key, ())


def prepare_payload_from_dataframe(
    raw_df: pd.DataFrame,
    *,
    standardize_columns: bool = True,
) -> dict[str, pd.DataFrame]:
    standardized_df, mapping = build_standardized_dataframe(raw_df, standardize_columns=standardize_columns)
    return {
        "raw_df": raw_df,
        "standardized_df": standardized_df,
        "quality_df": build_quality_checks(standardized_df),
        "missing_df": build_missing_values_frame(standardized_df),
        "mapping_df": build_mapping_frame(mapping),
    }


def build_preparation_summary(
    payload: dict[str, object],
    *,
    file_count: int = 1,
    compiled_file_count: int = 0,
    expected_columns: Iterable[str] = (),
) -> dict[str, object]:
    raw_df = payload.get("raw_df")
    standardized_df = payload.get("standardized_df")
    quality_df = payload.get("quality_df")
    mapping_df = payload.get("mapping_df")
    if not isinstance(raw_df, pd.DataFrame) or not isinstance(standardized_df, pd.DataFrame):
        raise TypeError("Le résumé de préparation exige des DataFrames bruts et standardisés.")

    renamed_columns = 0
    if isinstance(mapping_df, pd.DataFrame) and not mapping_df.empty:
        renamed_columns = int(
            mapping_df["colonne_source"].astype(str).str.strip().ne(
                mapping_df["colonne_standard"].astype(str).str.strip()
            ).sum()
        )
    anomaly_count = 0
    if isinstance(quality_df, pd.DataFrame) and not quality_df.empty and "nombre_lignes" in quality_df:
        anomaly_count = int(pd.to_numeric(quality_df["nombre_lignes"], errors="coerce").fillna(0).sum())
    duplicate_count = int(raw_df.duplicated().sum())
    expected = tuple(dict.fromkeys(expected_columns))
    missing_expected = tuple(column for column in expected if column not in standardized_df.columns)
    blocking_errors = ("Aucune ligne exploitable après préparation.",) if standardized_df.empty else ()
    warnings: list[str] = []
    if duplicate_count:
        warnings.append(f"{duplicate_count} doublon(s) exact(s) nécessitent une vérification.")
    if missing_expected:
        warnings.append(f"{len(missing_expected)} champ(s) métier attendu(s) ne sont pas disponibles.")

    return {
        "file_count": max(int(file_count), 0),
        "compiled_file_count": max(int(compiled_file_count), 0),
        "raw_rows": int(len(raw_df)),
        "ready_rows": int(len(standardized_df)),
        "renamed_columns": renamed_columns,
        "duplicate_count": duplicate_count,
        "anomaly_count": anomaly_count,
        "ignored_rows": max(int(len(raw_df) - len(standardized_df)), 0),
        "missing_expected": missing_expected,
        "warnings": tuple(warnings),
        "blocking_errors": blocking_errors,
        "status": "correction_required" if blocking_errors else ("warning" if warnings else "ready"),
    }
