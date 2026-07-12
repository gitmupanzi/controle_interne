from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
import sys
from time import perf_counter

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from credit_app.cycles import get_cycle_spec
from credit_app.domain import (
    build_cycle_period_series,
    build_cycle_watchlist,
    build_summary_metrics,
    filter_dataframe,
    get_cycle_primary_date_column,
)
from credit_app.services.data_pipeline import detect_cycle, prepare_payload_from_dataframe


CASES = {
    "credit": "123_cycle_credit_streamlit.xlsx",
    "epargne": "124_cycle_epargne_streamlit.xlsx",
    "crm_clients": "125_cycle_crm_clients_streamlit.xlsx",
    "operations_depot_retrait": "126_cycle_operations_depot_retrait_streamlit.xlsx",
    "caisse": "127_cycle_caisse_et_guichet_streamlit.xlsx",
    "tresorerie": "128_cycle_tresorerie_et_banque_streamlit.xlsx",
    "comptable": "129_cycle_comptable_et_financier_streamlit.xlsx",
    "si": "131_cycle_securite_systeme_information_streamlit.xlsx",
    "likelemba": "133_cycle_likelemba_streamlit.xlsx",
}


def run_case(cycle_key: str, filename: str) -> dict[str, object]:
    path = ROOT / "line_list" / filename
    started = perf_counter()
    frame = pd.read_excel(path, sheet_name=0, nrows=2000)
    loaded_seconds = perf_counter() - started
    detected = detect_cycle(filename, frame.columns)

    prepared_started = perf_counter()
    payload = prepare_payload_from_dataframe(frame)
    standardized = payload["standardized_df"]
    preparation_seconds = perf_counter() - prepared_started

    watchlist = build_cycle_watchlist(standardized, cycle_key)
    summary = build_summary_metrics(standardized)
    period = build_cycle_period_series(standardized, cycle_key)
    date_column = get_cycle_primary_date_column(standardized, cycle_key)
    filtered = filter_dataframe(standardized, date_column=date_column)

    export_buffer = BytesIO()
    with pd.ExcelWriter(export_buffer, engine="xlsxwriter") as writer:
        filtered.head(2000).to_excel(writer, sheet_name="donnees", index=False)
        payload["quality_df"].to_excel(writer, sheet_name="qualite", index=False)
        payload["mapping_df"].to_excel(writer, sheet_name="mapping", index=False)

    return {
        "cycle": cycle_key,
        "expected_label": get_cycle_spec(cycle_key)["label"],
        "file": filename,
        "detected_cycle": detected.cycle_key,
        "rows_tested": int(len(frame)),
        "columns_source": int(frame.shape[1]),
        "columns_standardized": int(standardized.shape[1]),
        "watchlist_rows": int(len(watchlist)),
        "period_rows": int(len(period)),
        "filtered_rows": int(len(filtered)),
        "summary_metrics": int(len(summary)),
        "quality_checks": int(len(payload["quality_df"])),
        "excel_export_bytes": int(len(export_buffer.getvalue())),
        "load_seconds": round(loaded_seconds, 3),
        "preparation_seconds": round(preparation_seconds, 3),
        "status": "ok" if detected.cycle_key == cycle_key else "cycle_mismatch",
    }


def main() -> None:
    results: list[dict[str, object]] = []
    for cycle_key, filename in CASES.items():
        try:
            results.append(run_case(cycle_key, filename))
        except Exception as exc:
            results.append(
                {
                    "cycle": cycle_key,
                    "file": filename,
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                }
            )
    output = ROOT / "reports" / "cycle_functional_results.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(result["status"] != "ok" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
