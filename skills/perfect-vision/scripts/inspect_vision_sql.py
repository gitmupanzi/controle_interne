from __future__ import annotations

import argparse
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "data" / "vision" / "BB_VISION_PRO.sql"
QUERIES = ROOT / "data" / "vision" / "requetes.sql"


def read_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8"
    return raw.decode(encoding, errors="replace").splitlines()


def print_matches(path: Path, term: str, context: int, limit: int) -> int:
    lines = read_lines(path)
    needle = term.casefold()
    indexes = [index for index, line in enumerate(lines) if needle in line.casefold()]
    for number, index in enumerate(indexes[:limit], start=1):
        start = max(0, index - context)
        end = min(len(lines), index + context + 1)
        print(f"\n--- {path.name} | occurrence {number} | ligne {index + 1} ---")
        for line_number in range(start, end):
            print(f"{line_number + 1:>7}: {lines[line_number]}")
    if len(indexes) > limit:
        print(f"\n{len(indexes) - limit} occurrence(s) supplémentaire(s) non affichée(s).")
    return len(indexes)


def list_queries() -> None:
    pattern = re.compile(r"^\s*(\d{1,3})\.\s+(.+?)\s*$")
    for line in read_lines(QUERIES):
        match = pattern.match(line.strip(" /*"))
        if match:
            print(f"{int(match.group(1)):03d} | {match.group(2)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Recherche ciblée dans le schéma et les requêtes Perfect Vision.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--table", help="Nom exact ou partiel d'une table à chercher dans le schéma.")
    group.add_argument("--query", help="Terme métier, table ou colonne à chercher dans le catalogue et le schéma.")
    group.add_argument("--list-queries", action="store_true", help="Lister les titres numérotés du catalogue.")
    parser.add_argument("--context", type=int, default=8, help="Nombre de lignes de contexte.")
    parser.add_argument("--limit", type=int, default=12, help="Nombre maximal d'occurrences par fichier.")
    args = parser.parse_args()

    if args.list_queries:
        list_queries()
        return
    if args.table:
        count = print_matches(SCHEMA, args.table, args.context, args.limit)
        print(f"\nTotal schéma : {count} occurrence(s).")
        return

    query_count = print_matches(QUERIES, args.query, args.context, args.limit)
    schema_count = print_matches(SCHEMA, args.query, args.context, args.limit)
    print(f"\nTotaux : requêtes={query_count}, schéma={schema_count}.")


if __name__ == "__main__":
    main()
