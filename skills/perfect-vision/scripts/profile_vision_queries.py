from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import pyodbc


ROOT = Path(__file__).resolve().parents[3]
QUERIES = ROOT / "data" / "modelisation" / "requetes.sql"
QUERY_HEADER_PATTERN = re.compile(r"^\s*(\d{1,3})\.\s+(.+?)\s*$")


@dataclass
class ColumnProfile:
    position: int
    name: str
    internal_name: str
    sql_type: str
    profiled_rows: int
    empty_count: int
    empty_rate: float
    distinct_non_empty: int
    unique_rate_non_empty: float
    dominant_value: str | None
    dominant_rate_non_empty: float
    sample_values: list[str]


def read_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8"
    return raw.decode(encoding, errors="replace").splitlines()


def extract_queries(path: Path) -> list[dict[str, Any]]:
    lines = read_lines(path)
    headers: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = QUERY_HEADER_PATTERN.match(line.strip(" /*"))
        if match:
            headers.append((index, int(match.group(1)), match.group(2)))

    queries: list[dict[str, Any]] = []
    for position, (start, number, title) in enumerate(headers):
        end = headers[position + 1][0] if position + 1 < len(headers) else len(lines)
        block = lines[start:end]
        comment_end = next(
            (index for index, line in enumerate(block) if "*/" in line),
            None,
        )
        sql_lines = block[comment_end + 1 :] if comment_end is not None else block
        while sql_lines and not sql_lines[-1].strip():
            sql_lines.pop()
        if sql_lines and sql_lines[-1].strip() == "/*":
            sql_lines.pop()
        queries.append(
            {
                "number": number,
                "title": title,
                "start_line": start + 1,
                "end_line": end,
                "sql": "\n".join(sql_lines).strip(),
            }
        )
    return queries


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return isinstance(value, str) and not value.strip()


def display_value(value: Any, max_length: int = 120) -> str:
    if value is None:
        return "<NULL>"
    if isinstance(value, (datetime, date)):
        text = value.isoformat()
    elif isinstance(value, bytes):
        text = value.hex()
    else:
        text = str(value)
    text = text.replace("\r", " ").replace("\n", " ")
    return text if len(text) <= max_length else f"{text[: max_length - 1]}…"


def exact_token(value: Any) -> str:
    if is_empty(value):
        return "<EMPTY>"
    if isinstance(value, Decimal):
        return f"decimal:{value.normalize()}"
    if isinstance(value, float):
        return f"float:{value:.15g}"
    if isinstance(value, (datetime, date)):
        return f"date:{value.isoformat()}"
    if isinstance(value, bytes):
        return f"bytes:{value.hex()}"
    return f"{type(value).__name__}:{value}"


def normalized_token(value: Any) -> str:
    if is_empty(value):
        return "<EMPTY>"
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex().casefold()
    return " ".join(str(value).split()).casefold()


def digest_tokens(tokens: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for token in tokens:
        encoded = token.encode("utf-8", errors="replace")
        digest.update(len(encoded).to_bytes(8, "little"))
        digest.update(encoded)
    return digest.hexdigest()


def profile_result_set(
    cursor: pyodbc.Cursor,
    max_rows: int,
    fetch_size: int,
) -> tuple[list[ColumnProfile], list[dict[str, Any]], int, bool]:
    description = cursor.description or []
    original_names = [str(column[0]) for column in description]
    name_counts: dict[str, int] = defaultdict(int)
    internal_names: list[str] = []
    for name in original_names:
        name_counts[name.casefold()] += 1
        suffix = name_counts[name.casefold()]
        internal_names.append(name if suffix == 1 else f"{name}__{suffix}")

    values_by_column: list[list[Any]] = [[] for _ in description]
    profiled_rows = 0
    truncated = False

    while profiled_rows < max_rows:
        batch = cursor.fetchmany(min(fetch_size, max_rows - profiled_rows))
        if not batch:
            break
        for row in batch:
            for index, value in enumerate(row):
                values_by_column[index].append(value)
        profiled_rows += len(batch)

    if profiled_rows >= max_rows:
        extra = cursor.fetchone()
        truncated = extra is not None

    column_profiles: list[ColumnProfile] = []
    signatures: list[dict[str, Any]] = []
    for index, values in enumerate(values_by_column):
        empty_count = sum(is_empty(value) for value in values)
        non_empty_tokens = [normalized_token(value) for value in values if not is_empty(value)]
        frequencies: dict[str, int] = defaultdict(int)
        samples: list[str] = []
        seen_samples: set[str] = set()
        for value, token in zip((value for value in values if not is_empty(value)), non_empty_tokens):
            frequencies[token] += 1
            shown = display_value(value)
            if shown not in seen_samples and len(samples) < 5:
                seen_samples.add(shown)
                samples.append(shown)

        distinct = len(frequencies)
        non_empty_count = len(non_empty_tokens)
        if frequencies:
            dominant_token, dominant_count = max(frequencies.items(), key=lambda item: item[1])
            dominant_value = dominant_token
            dominant_rate = dominant_count / non_empty_count
        else:
            dominant_value = None
            dominant_rate = 0.0

        sql_type = getattr(description[index][1], "__name__", str(description[index][1]))
        column_profiles.append(
            ColumnProfile(
                position=index + 1,
                name=original_names[index],
                internal_name=internal_names[index],
                sql_type=sql_type,
                profiled_rows=profiled_rows,
                empty_count=empty_count,
                empty_rate=(empty_count / profiled_rows) if profiled_rows else 0.0,
                distinct_non_empty=distinct,
                unique_rate_non_empty=(distinct / non_empty_count) if non_empty_count else 0.0,
                dominant_value=dominant_value,
                dominant_rate_non_empty=dominant_rate,
                sample_values=samples,
            )
        )
        signatures.append(
            {
                "position": index,
                "exact": digest_tokens(exact_token(value) for value in values),
                "normalized": digest_tokens(normalized_token(value) for value in values),
                "values": values,
            }
        )

    redundant_pairs: list[dict[str, Any]] = []
    if profiled_rows == 0:
        return column_profiles, redundant_pairs, profiled_rows, truncated

    exact_groups: dict[str, list[int]] = defaultdict(list)
    normalized_groups: dict[str, list[int]] = defaultdict(list)
    for signature in signatures:
        exact_groups[signature["exact"]].append(signature["position"])
        normalized_groups[signature["normalized"]].append(signature["position"])

    exact_pairs: set[tuple[int, int]] = set()
    for positions in exact_groups.values():
        if len(positions) < 2:
            continue
        for left_offset, left in enumerate(positions):
            for right in positions[left_offset + 1 :]:
                left_values = signatures[left]["values"]
                right_values = signatures[right]["values"]
                if not any(
                    not is_empty(a) or not is_empty(b)
                    for a, b in zip(left_values, right_values)
                ):
                    continue
                if all(exact_token(a) == exact_token(b) for a, b in zip(left_values, right_values)):
                    exact_pairs.add((left, right))
                    redundant_pairs.append(
                        {
                            "column_a": internal_names[left],
                            "column_b": internal_names[right],
                            "relationship": "identiques",
                            "match_rate": 1.0,
                        }
                    )

    for positions in normalized_groups.values():
        if len(positions) < 2:
            continue
        for left_offset, left in enumerate(positions):
            for right in positions[left_offset + 1 :]:
                if (left, right) in exact_pairs:
                    continue
                left_values = signatures[left]["values"]
                right_values = signatures[right]["values"]
                if not any(
                    not is_empty(a) or not is_empty(b)
                    for a, b in zip(left_values, right_values)
                ):
                    continue
                if all(normalized_token(a) == normalized_token(b) for a, b in zip(left_values, right_values)):
                    redundant_pairs.append(
                        {
                            "column_a": internal_names[left],
                            "column_b": internal_names[right],
                            "relationship": "identiques_apres_normalisation",
                            "match_rate": 1.0,
                        }
                    )

    return column_profiles, redundant_pairs, profiled_rows, truncated


def build_batch(query_sql: str, args: argparse.Namespace) -> str:
    return f"""
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET LOCK_TIMEOUT {args.lock_timeout_ms};
DECLARE @date_debut date = '{args.date_start}';
DECLARE @date_fin date = '{args.date_end}';
DECLARE @seuil_5k_usd_cdf float = {args.threshold_5k_cdf};
DECLARE @seuil_10k_usd_cdf float = {args.threshold_10k_cdf};
DECLARE @id_devise_reporting int = NULL;
DECLARE @taux_usd_cdf decimal(19,6) = {args.usd_cdf_rate};
{query_sql}
"""


def parse_numbers(text: str | None, available: set[int]) -> list[int]:
    if not text:
        return sorted(available)
    selected: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = (int(value.strip()) for value in part.split("-", 1))
            selected.update(range(start, end + 1))
        else:
            selected.add(int(part))
    unknown = sorted(selected - available)
    if unknown:
        raise SystemExit(f"Numéros de requête inconnus : {unknown}")
    return sorted(selected)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exécute et profile les colonnes des requêtes BB_VISION_PRO sans modifier la base."
    )
    parser.add_argument("--server", default="localhost")
    parser.add_argument("--database", default="BB_VISION_PRO_TEST")
    parser.add_argument("--date-start", default="2026-06-01")
    parser.add_argument("--date-end", default="2026-06-30")
    parser.add_argument("--threshold-5k-cdf", type=float, default=11_375_000)
    parser.add_argument("--threshold-10k-cdf", type=float, default=22_750_000)
    parser.add_argument("--usd-cdf-rate", type=float, default=2_275)
    parser.add_argument("--queries", help="Exemples : 1-20,38,149-156. Par défaut : toutes.")
    parser.add_argument("--max-rows", type=int, default=20_000)
    parser.add_argument("--fetch-size", type=int, default=1_000)
    parser.add_argument("--query-timeout", type=int, default=600)
    parser.add_argument("--lock-timeout-ms", type=int, default=30_000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports" / "sql_column_profile",
    )
    args = parser.parse_args()

    queries = extract_queries(QUERIES)
    query_by_number = {query["number"]: query for query in queries}
    selected_numbers = parse_numbers(args.queries, set(query_by_number))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={args.server};DATABASE={args.database};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )
    results: list[dict[str, Any]] = []
    column_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []

    started_at = datetime.now()
    print(
        f"Profilage de {len(selected_numbers)} requête(s), base={args.database}, "
        f"période={args.date_start}..{args.date_end}, plafond={args.max_rows} lignes.",
        flush=True,
    )

    for sequence, number in enumerate(selected_numbers, start=1):
        query = query_by_number[number]
        started = time.perf_counter()
        status = "ok"
        error = None
        profiles: list[ColumnProfile] = []
        pairs: list[dict[str, Any]] = []
        row_count = 0
        truncated = False
        result_set_count = 0

        try:
            with pyodbc.connect(connection_string, autocommit=True) as connection:
                connection.timeout = args.query_timeout
                cursor = connection.cursor()
                cursor.execute(build_batch(query["sql"], args))
                while cursor.description is None:
                    if not cursor.nextset():
                        break
                if cursor.description is not None:
                    result_set_count = 1
                    profiles, pairs, row_count, truncated = profile_result_set(
                        cursor,
                        max_rows=args.max_rows,
                        fetch_size=args.fetch_size,
                    )
                else:
                    status = "sans_resultset"
        except Exception as exc:  # noqa: BLE001 - le rapport doit conserver toute erreur SQL/ODBC
            status = "erreur"
            error = str(exc)

        duration = time.perf_counter() - started
        empty_columns = sum(profile.empty_rate == 1.0 for profile in profiles)
        constant_columns = sum(
            profile.distinct_non_empty <= 1 and profile.empty_rate < 1.0 for profile in profiles
        ) if row_count else 0
        low_information_columns = sum(
            profile.dominant_rate_non_empty >= 0.99
            and profile.distinct_non_empty > 1
            for profile in profiles
        )

        result = {
            "query_number": number,
            "title": query["title"],
            "status": status,
            "duration_seconds": round(duration, 3),
            "profiled_rows": row_count,
            "truncated": truncated,
            "result_set_count": result_set_count,
            "column_count": len(profiles),
            "empty_column_count": empty_columns,
            "constant_column_count": constant_columns,
            "low_information_column_count": low_information_columns,
            "redundant_pair_count": len(pairs),
            "error": error,
            "start_line": query["start_line"],
            "end_line": query["end_line"],
        }
        results.append(result)

        for profile in profiles:
            row = asdict(profile)
            row["query_number"] = number
            row["query_title"] = query["title"]
            column_rows.append(row)
        for pair in pairs:
            pair_rows.append(
                {
                    "query_number": number,
                    "query_title": query["title"],
                    **pair,
                    "profiled_rows": row_count,
                    "truncated": truncated,
                }
            )

        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "database": args.database,
            "parameters": {
                "date_start": args.date_start,
                "date_end": args.date_end,
                "threshold_5k_cdf": args.threshold_5k_cdf,
                "threshold_10k_cdf": args.threshold_10k_cdf,
                "usd_cdf_rate": args.usd_cdf_rate,
                "id_devise_reporting": None,
                "max_rows_per_query": args.max_rows,
            },
            "queries": results,
            "columns": column_rows,
            "redundant_pairs": pair_rows,
        }
        (args.output_dir / "profile.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(
            f"[{sequence:03d}/{len(selected_numbers):03d}] Q{number:03d} {status} "
            f"{duration:.1f}s, lignes={row_count}{'+' if truncated else ''}, "
            f"colonnes={len(profiles)}, vides={empty_columns}, constantes={constant_columns}, "
            f"paires={len(pairs)}",
            flush=True,
        )

    write_csv(
        args.output_dir / "query_summary.csv",
        results,
        [
            "query_number",
            "title",
            "status",
            "duration_seconds",
            "profiled_rows",
            "truncated",
            "result_set_count",
            "column_count",
            "empty_column_count",
            "constant_column_count",
            "low_information_column_count",
            "redundant_pair_count",
            "error",
            "start_line",
            "end_line",
        ],
    )
    write_csv(
        args.output_dir / "column_profile.csv",
        column_rows,
        [
            "query_number",
            "query_title",
            "position",
            "name",
            "internal_name",
            "sql_type",
            "profiled_rows",
            "empty_count",
            "empty_rate",
            "distinct_non_empty",
            "unique_rate_non_empty",
            "dominant_value",
            "dominant_rate_non_empty",
            "sample_values",
        ],
    )
    write_csv(
        args.output_dir / "redundant_pairs.csv",
        pair_rows,
        [
            "query_number",
            "query_title",
            "column_a",
            "column_b",
            "relationship",
            "match_rate",
            "profiled_rows",
            "truncated",
        ],
    )
    elapsed = datetime.now() - started_at
    print(f"Terminé en {elapsed}. Résultats : {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
