from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from credit_app.data_schema import (  # noqa: E402
    CURRENT_SAVINGS_SCHEMA,
    CUSTOMERS_SCHEMA,
    FIXED_SAVINGS_SCHEMA,
    G2_TRANSACTIONS_SCHEMA,
    LOANS_SCHEMA,
    MPESA_TRANSACTIONS_SCHEMA,
)


SCHEMAS = (
    MPESA_TRANSACTIONS_SCHEMA,
    CURRENT_SAVINGS_SCHEMA,
    FIXED_SAVINGS_SCHEMA,
    LOANS_SCHEMA,
    G2_TRANSACTIONS_SCHEMA,
    CUSTOMERS_SCHEMA,
)


def main() -> None:
    payload = []
    for item in SCHEMAS:
        payload.append(
            {
                "source": item.name,
                "colonnes_obligatoires": sorted(item.required),
                "colonnes_facultatives": sorted(item.optional),
                "alias_acceptes": {key: list(values) for key, values in sorted(item.aliases.items())},
            }
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
