from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pyodbc

from profile_vision_queries import (
    QUERIES,
    build_batch,
    digest_tokens,
    exact_token,
    extract_queries,
    is_empty,
    normalized_token,
)


ROOT = Path(__file__).resolve().parents[3]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile la requête 156 par bloc d'analyse sans conserver les données nominatives."
    )
    parser.add_argument("--server", default="localhost")
    parser.add_argument("--database", default="BB_VISION_PRO_TEST")
    parser.add_argument("--date-start", default="2026-06-01")
    parser.add_argument("--date-end", default="2026-06-30")
    parser.add_argument("--threshold-5k-cdf", type=float, default=11_375_000)
    parser.add_argument("--threshold-10k-cdf", type=float, default=22_750_000)
    parser.add_argument("--usd-cdf-rate", type=float, default=2_275)
    parser.add_argument("--query-timeout", type=int, default=600)
    parser.add_argument("--lock-timeout-ms", type=int, default=30_000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports" / "sql_column_profile_2026_06" / "q156_segments",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    query = next(query for query in extract_queries(QUERIES) if query["number"] == 156)
    connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={args.server};DATABASE={args.database};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )

    with pyodbc.connect(connection_string, autocommit=True) as connection:
        connection.timeout = args.query_timeout
        cursor = connection.cursor()
        cursor.execute(build_batch(query["sql"], args))
        while cursor.description is None:
            if not cursor.nextset():
                raise RuntimeError("La requête 156 n'a retourné aucun jeu de résultats.")
        names = [str(column[0]) for column in cursor.description]
        rows = [tuple(row) for row in cursor.fetchall()]

    analysis_column = "analyse" if "analyse" in names else "analyse_source"
    line_type_column = "type_element" if "type_element" in names else "type_ligne"
    try:
        analysis_index = names.index(analysis_column)
        line_type_index = names.index(line_type_column)
    except ValueError as exc:
        raise RuntimeError(
            "Les colonnes analyse_source et type_ligne sont requises pour segmenter la requête 156."
        ) from exc

    grouped_rows: dict[tuple[str, str], list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        key = (str(row[analysis_index]), str(row[line_type_index]))
        grouped_rows[key].append(row)

    segment_rows: list[dict[str, Any]] = []
    column_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []

    for (analysis_source, line_type), group in sorted(grouped_rows.items()):
        row_count = len(group)
        segment_rows.append(
            {
                "analyse_source": analysis_source,
                "type_ligne": line_type,
                "row_count": row_count,
                "column_count": len(names),
            }
        )
        exact_groups: dict[str, list[int]] = defaultdict(list)
        normalized_groups: dict[str, list[int]] = defaultdict(list)
        values_by_position: list[list[Any]] = []

        for position, name in enumerate(names):
            values = [row[position] for row in group]
            values_by_position.append(values)
            non_empty = [value for value in values if not is_empty(value)]
            normalized = [normalized_token(value) for value in non_empty]
            frequencies: dict[str, int] = defaultdict(int)
            for token in normalized:
                frequencies[token] += 1
            dominant_rate = (
                max(frequencies.values()) / len(non_empty)
                if frequencies and non_empty
                else 0.0
            )
            column_rows.append(
                {
                    "analyse_source": analysis_source,
                    "type_ligne": line_type,
                    "column_position": position + 1,
                    "column_name": name,
                    "row_count": row_count,
                    "non_empty_count": len(non_empty),
                    "non_empty_rate": len(non_empty) / row_count if row_count else 0.0,
                    "distinct_non_empty": len(frequencies),
                    "dominant_rate_non_empty": dominant_rate,
                }
            )
            exact_groups[digest_tokens(exact_token(value) for value in values)].append(position)
            normalized_groups[
                digest_tokens(normalized_token(value) for value in values)
            ].append(position)

        exact_pairs: set[tuple[int, int]] = set()
        for positions in exact_groups.values():
            if len(positions) < 2:
                continue
            for left_offset, left in enumerate(positions):
                for right in positions[left_offset + 1 :]:
                    left_values = values_by_position[left]
                    right_values = values_by_position[right]
                    if not any(
                        not is_empty(a) or not is_empty(b)
                        for a, b in zip(left_values, right_values)
                    ):
                        continue
                    if all(
                        exact_token(a) == exact_token(b)
                        for a, b in zip(left_values, right_values)
                    ):
                        exact_pairs.add((left, right))
                        pair_rows.append(
                            {
                                "analyse_source": analysis_source,
                                "type_ligne": line_type,
                                "column_a": names[left],
                                "column_b": names[right],
                                "relationship": "identiques",
                                "row_count": row_count,
                            }
                        )

        for positions in normalized_groups.values():
            if len(positions) < 2:
                continue
            for left_offset, left in enumerate(positions):
                for right in positions[left_offset + 1 :]:
                    if (left, right) in exact_pairs:
                        continue
                    left_values = values_by_position[left]
                    right_values = values_by_position[right]
                    if not any(
                        not is_empty(a) or not is_empty(b)
                        for a, b in zip(left_values, right_values)
                    ):
                        continue
                    if all(
                        normalized_token(a) == normalized_token(b)
                        for a, b in zip(left_values, right_values)
                    ):
                        pair_rows.append(
                            {
                                "analyse_source": analysis_source,
                                "type_ligne": line_type,
                                "column_a": names[left],
                                "column_b": names[right],
                                "relationship": "identiques_apres_normalisation",
                                "row_count": row_count,
                            }
                        )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "database": args.database,
        "date_start": args.date_start,
        "date_end": args.date_end,
        "total_rows": len(rows),
        "column_count": len(names),
        "segments": segment_rows,
        "columns": column_rows,
        "redundant_pairs": pair_rows,
    }
    (args.output_dir / "profile.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(
        args.output_dir / "segment_summary.csv",
        segment_rows,
        ["analyse_source", "type_ligne", "row_count", "column_count"],
    )
    write_csv(
        args.output_dir / "segment_column_profile.csv",
        column_rows,
        [
            "analyse_source",
            "type_ligne",
            "column_position",
            "column_name",
            "row_count",
            "non_empty_count",
            "non_empty_rate",
            "distinct_non_empty",
            "dominant_rate_non_empty",
        ],
    )
    write_csv(
        args.output_dir / "segment_redundant_pairs.csv",
        pair_rows,
        [
            "analyse_source",
            "type_ligne",
            "column_a",
            "column_b",
            "relationship",
            "row_count",
        ],
    )
    print(
        f"Requête 156 : {len(rows)} lignes, {len(names)} colonnes, "
        f"{len(segment_rows)} segment(s), {len(pair_rows)} paire(s) identique(s)."
    )


if __name__ == "__main__":
    main()
