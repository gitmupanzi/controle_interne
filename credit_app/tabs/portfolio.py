from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from credit_app.app_loader import list_available_line_list_files, load_dataframe_from_path
from credit_app.core import format_currency
from credit_app.cycles import get_cycle_analysis_preset, get_cycle_spec
from credit_app.domain import (
    build_activity_table,
    build_cycle_watchlist,
    build_frequency_table,
    build_grouped_amounts,
    build_standardized_dataframe,
    build_status_flow_table,
    get_first_existing_column,
    normalize_text,
)
from credit_app.sql_operations import (
    build_client_movement_summary_table,
    build_lbcft_reporting_table,
    build_mobile_banking_summary_table,
    normalize_operations_analysis_frame,
    build_top_clients_table,
)
from credit_app.ui import (
    render_kpi_cards,
    render_panel_title,
    render_summary_box,
    st_plot,
    style_standard_donut,
    style_standard_vertical_bar,
)

EPARGNE_PRODUCT_ORDER = [
    "Compte courant Bwakisa Carte en USD",
    "Compte courant Ordinaire en USD",
    "Compte Epargne Ordinaire USD",
    "Compte Epargne Ordinaire Groupe USD",
    "Compte Salaire MILTEX USD",
    "Compte Courant Salaire Personnel IMF USD",
    "Compte Courant Payroll Clientèle USD",
    "Dépôts de garantie solidaire LISUNGI USD",
    "Dépôt de garantie Individuelle USD",
    "Compte POS USD",
    "DAT Individu",
    "DAT Société",
    "Totines USD",
    "Compte Epargne Ordinaire Individuelle Likelemba USD",
    "Compte courant Bwakisa Carte en CDF",
    "Compte Courant Ordinaire en CDF",
    "Compte Courant POS CDF",
    "Compte Epargne Ordinaire en CDF",
    "Compte Epargne Ordinaire Groupe CDF",
    "Dépôts de garantie Individuelle en CDF",
    "Dépôts de garantie solidaire LISUNGI CDF",
    "Totines CDF",
    "Compte Epargne Ordinaire Individuelle Likelemba CDF",
]

UTILIZATION_NORMS = {
    "Compte Courant": 0.3,
    "Compte Epargne": 0.7,
    "Bwakisa Carte": 0.0,
    "Dépôts de garantie": 1.0,
    "Dépôt à Terme": 1.0,
}


def _resolve_amount_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def _parse_bundle_date_from_name(file_name: str) -> pd.Timestamp | None:
    match = re.search(r"(\d{2}-\d{2}-\d{4})", file_name)
    if not match:
        return None
    parsed = pd.to_datetime(match.group(1), format="%d-%m-%Y", errors="coerce")
    return None if pd.isna(parsed) else parsed


def _bundle_label(bundle_date: pd.Timestamp | None, fallback_key: str) -> str:
    if bundle_date is None:
        return fallback_key
    return bundle_date.strftime("%d/%m/%Y")


def _infer_file_currency(std_df: pd.DataFrame) -> str:
    if "type_produit" not in std_df.columns:
        return "USD"
    labels = std_df["type_produit"].dropna().astype("string")
    usd_hits = labels.str.contains("USD", case=False, regex=False).sum()
    cdf_hits = labels.str.contains("CDF", case=False, regex=False).sum()
    return "CDF" if cdf_hits > usd_hits else "USD"


def _report_product_label(type_produit: object, type_client: object) -> str:
    product = str(type_produit or "").strip()
    normalized = normalize_text(product)
    client_type = normalize_text(type_client)

    if normalized == "dat":
        if "morale" in client_type or "societe" in client_type or "société" in client_type:
            return "DAT Société"
        return "DAT Individu"

    mapping = {
        "compte courant bwakisa carte usd": "Compte courant Bwakisa Carte en USD",
        "compte courant bwakisa carte cdf": "Compte courant Bwakisa Carte en CDF",
        "compte courant ordinaire usd": "Compte courant Ordinaire en USD",
        "compte courant ordinaire cdf": "Compte Courant Ordinaire en CDF",
        "compte epargne ordinaire usd": "Compte Epargne Ordinaire USD",
        "compte epargne ordinaire cdf": "Compte Epargne Ordinaire en CDF",
        "compte epargne ordinaire groupe usd": "Compte Epargne Ordinaire Groupe USD",
        "compte epargne ordinaire groupe cdf": "Compte Epargne Ordinaire Groupe CDF",
        "compte salaire agent miltex usd": "Compte Salaire MILTEX USD",
        "compte courant salaire personnel imf usd": "Compte Courant Salaire Personnel IMF USD",
        "compte courant payroll clientele usd": "Compte Courant Payroll Clientèle USD",
        "depots de garantie solidaire lisungi usd": "Dépôts de garantie solidaire LISUNGI USD",
        "depots de garantie solidaire lisungi cdf": "Dépôts de garantie solidaire LISUNGI CDF",
        "depot de garantie individuelle usd": "Dépôt de garantie Individuelle USD",
        "depots de garantie individuelle usd": "Dépôt de garantie Individuelle USD",
        "depot de garantie individuelle cdf": "Dépôts de garantie Individuelle en CDF",
        "depots de garantie individuelle cdf": "Dépôts de garantie Individuelle en CDF",
        "compte courant pos usd": "Compte POS USD",
        "compte courant pos cdf": "Compte Courant POS CDF",
        "totines usd": "Totines USD",
        "totines cdf": "Totines CDF",
        "compte epargne ordinaire individuelle likelemba usd": "Compte Epargne Ordinaire Individuelle Likelemba USD",
        "compte epargne ordinaire individuelle likelemba cdf": "Compte Epargne Ordinaire Individuelle Likelemba CDF",
    }
    return mapping.get(normalized, product)


def _format_count(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "-"
    return f"{int(round(float(numeric))):,}".replace(",", " ")


def _format_amount(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "-"
    return f"{float(numeric):,.2f}".replace(",", " ")


def _format_share(value: object) -> str:
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "-"
    return f"{float(numeric) * 100:,.2f}%".replace(",", " ")


def _build_proportion_comment(share: object, is_total: bool = False) -> str:
    if is_total:
        return "Vue globale de la structure du portefeuille."

    numeric = pd.to_numeric(pd.Series([share]), errors="coerce").iloc[0]
    if pd.isna(numeric) or float(numeric) <= 0:
        return "Produit sans poids significatif sur la date analysée."
    if float(numeric) >= 0.25:
        return "Produit très dominant dans le portefeuille."
    if float(numeric) >= 0.10:
        return "Produit important dans le portefeuille."
    if float(numeric) >= 0.03:
        return "Produit secondaire à suivre."
    return "Produit de poids limité dans le portefeuille."


def _build_variation_comment(amount_delta: object, is_total: bool = False) -> str:
    if is_total:
        return "Variation globale du portefeuille entre les deux dates."

    numeric = pd.to_numeric(pd.Series([amount_delta]), errors="coerce").iloc[0]
    if pd.isna(numeric) or float(numeric) == 0:
        return "Niveau stable entre les deux dates."
    if float(numeric) > 0:
        return "Hausse observée par rapport à la date précédente."
    return "Baisse observée par rapport à la date précédente."


def _format_snapshot_display(snapshot_df: pd.DataFrame) -> pd.DataFrame:
    display_df = snapshot_df.copy()
    if "Nbre de compte" in display_df.columns:
        display_df["Nbre de compte"] = display_df["Nbre de compte"].apply(_format_count)
    for column_name in ["CDF", "USD", "Total général en CDF", "Total général en USD"]:
        if column_name in display_df.columns:
            display_df[column_name] = display_df[column_name].apply(_format_amount)
    if "Proportion" in display_df.columns:
        display_df["Proportion"] = display_df["Proportion"].apply(_format_share)
    return display_df


def _format_utilization_display(utilization_df: pd.DataFrame, variation: bool = False) -> pd.DataFrame:
    display_df = utilization_df.copy()
    if "Norme" in display_df.columns:
        display_df["Norme"] = display_df["Norme"].apply(_format_share)
    amount_columns = [
        "Total général en USD",
        "Montant utilisable",
        "Variation Total général en USD",
        "Variation Montant utilisable",
    ]
    for column_name in amount_columns:
        if column_name in display_df.columns:
            display_df[column_name] = display_df[column_name].apply(_format_amount)
    if variation and "Famille" in display_df.columns:
        display_df = display_df.sort_values("Famille").reset_index(drop=True)
    return display_df


def _build_epargne_ratio_table(
    current_snapshot: pd.DataFrame,
    current_use: pd.DataFrame,
    current_df: pd.DataFrame,
) -> pd.DataFrame:
    non_total_snapshot = current_snapshot[current_snapshot["PRODUITS"] != "TOTAL"].copy()
    total_usd = float(current_snapshot.loc[current_snapshot["PRODUITS"] == "TOTAL", "Total général en USD"].sum())
    total_accounts = int(current_snapshot.loc[current_snapshot["PRODUITS"] == "TOTAL", "Nbre de compte"].sum())
    total_usable = float(current_use["Montant utilisable"].sum()) if not current_use.empty else 0.0
    idle_cash = total_usd - total_usable
    avg_deposit = total_usd / total_accounts if total_accounts else 0.0
    dat_usd = float(
        non_total_snapshot.loc[
            non_total_snapshot["PRODUITS"].isin(["DAT Individu", "DAT Société"]),
            "Total général en USD",
        ].sum()
    )
    dat_share = dat_usd / total_usd if total_usd else 0.0
    active_accounts = int(current_df.get("compte_id", pd.Series(dtype="object")).nunique())
    nonzero_accounts = int(
        current_df.loc[
            pd.to_numeric(current_df.get("solde_compte"), errors="coerce").fillna(0.0) != 0,
            "compte_id",
        ].nunique()
    ) if "compte_id" in current_df.columns else 0
    active_managers = int(current_df.get("agent_credit", pd.Series(dtype="object")).dropna().nunique())
    productivity = nonzero_accounts / active_managers if active_managers else 0.0

    return pd.DataFrame(
        [
            ("Total dépôts BCC (USD)", total_usd, "Montant total reconstitué au taux courant."),
            ("Montant utilisable (USD)", total_usable, "Application dynamique des normes BCC par famille."),
            ("Reste à utiliser (USD)", idle_cash, "Écart entre dépôts reconstitués et montant mobilisable."),
            ("Dépôt moyen par compte (USD)", avg_deposit, "Total des dépôts rapporté au nombre de comptes."),
            ("Part des DAT", dat_share, "Poids des dépôts à terme dans le portefeuille."),
            ("Comptes non nuls par gestionnaire", productivity, "Indicateur interne de productivité du portefeuille."),
            ("Comptes actifs détectés", float(active_accounts), "Nombre de comptes distincts présents dans le bundle."),
        ],
        columns=["Indicateur", "Valeur", "Lecture"],
    )


def _format_ratio_display(ratio_df: pd.DataFrame) -> pd.DataFrame:
    display_df = ratio_df.copy()
    display_df["Valeur"] = [
        _format_share(value) if indicator == "Part des DAT"
        else _format_count(value) if indicator == "Comptes actifs détectés"
        else _format_amount(value)
        for indicator, value in zip(display_df["Indicateur"], display_df["Valeur"])
    ]
    return display_df


def _build_epargne_report_snapshot(std_df: pd.DataFrame, conversion_rate: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    if std_df.empty:
        empty_snapshot = pd.DataFrame(
            columns=[
                "REF",
                "PRODUITS",
                "Nbre de compte",
                "CDF",
                "USD",
                "Total général en CDF",
                "Total général en USD",
                "Proportion",
                "Lecture",
            ]
        )
        empty_use = pd.DataFrame(columns=["Famille", "Total général en USD", "Norme", "Montant utilisable"])
        return empty_snapshot, empty_use

    base = std_df.copy()
    base["solde_compte"] = pd.to_numeric(base.get("solde_compte"), errors="coerce").fillna(0.0)
    base["source_currency"] = base.get("source_currency", pd.Series(index=base.index, dtype="object")).fillna("")
    base["devise"] = base["type_produit"].astype("string").str.extract(r"\b(USD|CDF)\b", expand=False)
    fallback_currency = base["source_currency"].replace("", pd.NA)
    base["devise"] = base["devise"].fillna(fallback_currency)
    base["devise"] = base["devise"].fillna("USD")
    base["report_product"] = [
        _report_product_label(product, client_type)
        for product, client_type in zip(base.get("type_produit", []), base.get("type_client", []))
    ]

    grouped = (
        base.groupby(["report_product", "devise"], dropna=False)
        .agg(
            compte_n=("compte_id", "nunique"),
            solde_total=("solde_compte", "sum"),
        )
        .reset_index()
    )

    pivot = grouped.pivot_table(
        index="report_product",
        columns="devise",
        values="solde_total",
        aggfunc="sum",
        fill_value=0.0,
    )
    counts = grouped.groupby("report_product", dropna=False)["compte_n"].sum()
    report = pd.DataFrame(index=sorted(set(pivot.index).union(counts.index)))
    report["Nbre de compte"] = counts.reindex(report.index).fillna(0).astype(int)
    cdf_series = pivot["CDF"] if "CDF" in pivot.columns else pd.Series(index=report.index, dtype="float64")
    usd_series = pivot["USD"] if "USD" in pivot.columns else pd.Series(index=report.index, dtype="float64")
    report["CDF"] = pd.to_numeric(cdf_series, errors="coerce").reindex(report.index).fillna(0.0)
    report["USD"] = pd.to_numeric(usd_series, errors="coerce").reindex(report.index).fillna(0.0)
    rate = conversion_rate if conversion_rate > 0 else 1.0
    report["Total général en CDF"] = report["CDF"] + report["USD"] * rate
    report["Total général en USD"] = report["USD"] + report["CDF"] / rate
    total_usd = float(report["Total général en USD"].sum())
    report["Proportion"] = report["Total général en USD"] / total_usd if total_usd else 0.0
    report["Lecture"] = report["Proportion"].apply(_build_proportion_comment)
    report["REF"] = ""
    report["PRODUITS"] = report.index

    ordered_products = [product for product in EPARGNE_PRODUCT_ORDER if product in report.index]
    other_products = [product for product in report.index if product not in ordered_products]
    report = report.loc[ordered_products + other_products].reset_index(drop=True)

    total_row = pd.DataFrame(
        [
            {
                "REF": "",
                "PRODUITS": "TOTAL",
                "Nbre de compte": int(report["Nbre de compte"].sum()),
                "CDF": float(report["CDF"].sum()),
                "USD": float(report["USD"].sum()),
                "Total général en CDF": float(report["Total général en CDF"].sum()),
                "Total général en USD": float(report["Total général en USD"].sum()),
                "Proportion": float(report["Proportion"].sum()),
                "Lecture": _build_proportion_comment(1.0, is_total=True),
            }
        ]
    )
    report = pd.concat([report[total_row.columns], total_row], ignore_index=True)

    family_df = report[report["PRODUITS"] != "TOTAL"].copy()

    def resolve_family(product_label: str) -> str:
        normalized = normalize_text(product_label)
        if "bwakisa carte" in normalized:
            return "Bwakisa Carte"
        if "garantie" in normalized:
            return "Dépôts de garantie"
        if normalized.startswith("dat "):
            return "Dépôt à Terme"
        if "epargne ordinaire" in normalized or normalized.startswith("totines"):
            return "Compte Epargne"
        return "Compte Courant"

    family_df["Famille"] = family_df["PRODUITS"].apply(resolve_family)
    utilization = (
        family_df.groupby("Famille", dropna=False)["Total général en USD"]
        .sum()
        .rename("Total général en USD")
        .reset_index()
    )
    utilization["Norme"] = utilization["Famille"].map(UTILIZATION_NORMS).fillna(0.0)
    utilization["Montant utilisable"] = utilization["Total général en USD"] * utilization["Norme"]
    utilization["_order"] = utilization["Famille"].map(
        {
            "Compte Courant": 1,
            "Compte Epargne": 2,
            "Bwakisa Carte": 3,
            "Dépôts de garantie": 4,
            "Dépôt à Terme": 5,
        }
    ).fillna(99)
    utilization = utilization.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    return report, utilization


def _build_epargne_report_variation(
    current_snapshot: pd.DataFrame,
    previous_snapshot: pd.DataFrame,
    current_utilization: pd.DataFrame,
    previous_utilization: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    merge_cols = ["PRODUITS", "Nbre de compte", "CDF", "USD", "Total général en CDF", "Total général en USD"]
    current = current_snapshot[merge_cols].copy()
    previous = previous_snapshot[merge_cols].copy()
    merged = current.merge(previous, on="PRODUITS", how="outer", suffixes=("_current", "_previous")).fillna(0)

    variation = pd.DataFrame()
    variation["REF"] = ""
    variation["PRODUITS"] = merged["PRODUITS"]
    variation["Nbre de compte"] = merged["Nbre de compte_current"] - merged["Nbre de compte_previous"]
    variation["CDF"] = merged["CDF_current"] - merged["CDF_previous"]
    variation["USD"] = merged["USD_current"] - merged["USD_previous"]
    variation["Total général en CDF"] = merged["Total général en CDF_current"] - merged["Total général en CDF_previous"]
    variation["Total général en USD"] = merged["Total général en USD_current"] - merged["Total général en USD_previous"]
    variation["Proportion"] = merged.apply(
        lambda row: 0.0
        if float(row["Total général en USD_previous"]) == 0
        else float(row["Total général en USD_current"] - row["Total général en USD_previous"])
        / float(row["Total général en USD_previous"]),
        axis=1,
    )
    variation["Lecture"] = variation["Total général en USD"].apply(_build_variation_comment)

    product_rank = {product: idx for idx, product in enumerate(EPARGNE_PRODUCT_ORDER, start=1)}
    variation["_order"] = variation["PRODUITS"].map(product_rank).fillna(999)
    variation = variation.sort_values("_order").drop(columns="_order").reset_index(drop=True)

    total_row = pd.DataFrame(
        [
            {
                "REF": "",
                "PRODUITS": "TOTAL",
                "Nbre de compte": int(variation.loc[variation["PRODUITS"] != "TOTAL", "Nbre de compte"].sum()),
                "CDF": float(variation.loc[variation["PRODUITS"] != "TOTAL", "CDF"].sum()),
                "USD": float(variation.loc[variation["PRODUITS"] != "TOTAL", "USD"].sum()),
                "Total général en CDF": float(variation.loc[variation["PRODUITS"] != "TOTAL", "Total général en CDF"].sum()),
                "Total général en USD": float(variation.loc[variation["PRODUITS"] != "TOTAL", "Total général en USD"].sum()),
                "Proportion": float(variation.loc[variation["PRODUITS"] != "TOTAL", "Total général en USD"].sum())
                / float(previous_snapshot.loc[previous_snapshot["PRODUITS"] == "TOTAL", "Total général en USD"].sum() or 1.0),
                "Lecture": _build_variation_comment(0.0, is_total=True),
            }
        ]
    )
    variation = pd.concat([variation, total_row], ignore_index=True)

    current_use = current_utilization.rename(
        columns={
            "Total général en USD": "Total général en USD_current",
            "Montant utilisable": "Montant utilisable_current",
        }
    )
    previous_use = previous_utilization.rename(
        columns={
            "Total général en USD": "Total général en USD_previous",
            "Montant utilisable": "Montant utilisable_previous",
        }
    )
    merged_use = current_use.merge(previous_use, on=["Famille", "Norme"], how="outer").fillna(0)
    utilization_variation = pd.DataFrame()
    utilization_variation["Famille"] = merged_use["Famille"]
    utilization_variation["Variation Total général en USD"] = (
        merged_use["Total général en USD_current"] - merged_use["Total général en USD_previous"]
    )
    utilization_variation["Norme"] = merged_use["Norme"]
    utilization_variation["Variation Montant utilisable"] = (
        merged_use["Montant utilisable_current"] - merged_use["Montant utilisable_previous"]
    )
    return variation, utilization_variation


def build_epargne_bundles_from_standardized_frames(
    frames: list[tuple[str, pd.DataFrame]],
) -> list[dict[str, object]]:
    bundle_map: dict[str, dict[str, object]] = {}
    for source_name, standardized_df in frames:
        if standardized_df is None or standardized_df.empty:
            continue
        prepared_df = standardized_df.copy()
        if "source_currency" not in prepared_df.columns:
            prepared_df["source_currency"] = _infer_file_currency(prepared_df)
        else:
            prepared_df["source_currency"] = prepared_df["source_currency"].fillna("")
            if (prepared_df["source_currency"].astype("string").str.strip() == "").all():
                prepared_df["source_currency"] = _infer_file_currency(prepared_df)

        bundle_date = _parse_bundle_date_from_name(source_name)
        bundle_key = bundle_date.strftime("%Y-%m-%d") if bundle_date is not None else Path(source_name).stem
        bundle_entry = bundle_map.setdefault(
            bundle_key,
            {"bundle_key": bundle_key, "bundle_date": bundle_date, "dataframes": [], "files": []},
        )
        bundle_entry["dataframes"].append(prepared_df)
        bundle_entry["files"].append(Path(source_name).name)

    bundles: list[dict[str, object]] = []
    for bundle in bundle_map.values():
        frames_for_bundle = bundle["dataframes"]
        combined_df = pd.concat(frames_for_bundle, ignore_index=True) if frames_for_bundle else pd.DataFrame()
        bundles.append(
            {
                "bundle_key": bundle["bundle_key"],
                "bundle_date": bundle["bundle_date"],
                "files": bundle["files"],
                "df": combined_df,
            }
        )

    bundles.sort(
        key=lambda item: (
            item["bundle_date"] if isinstance(item["bundle_date"], pd.Timestamp) else pd.Timestamp.min,
            item["bundle_key"],
        ),
        reverse=True,
    )
    return bundles


@st.cache_data(show_spinner=False)
def _load_epargne_report_bundles_from_line_list() -> list[dict[str, object]]:
    files = sorted(
        path
        for path in list_available_line_list_files()
        if path.suffix.lower() in {".xlsx", ".xls"} and "Encours des épargnants" in path.name and not path.name.startswith("~$")
    )
    standardized_frames: list[tuple[str, pd.DataFrame]] = []
    for file_path in files:
        raw_df = load_dataframe_from_path(file_path, sheet_name="Sheet0")
        standardized_df, _ = build_standardized_dataframe(raw_df)
        standardized_frames.append((file_path.name, standardized_df))
    return build_epargne_bundles_from_standardized_frames(standardized_frames)


def _render_epargne_reconstructed_report(
    conversion_rate: float,
    bundles: list[dict[str, object]] | None = None,
    source_label: str | None = None,
) -> None:
    active_bundles = bundles or _load_epargne_report_bundles_from_line_list()
    report_source_label = source_label or "Fichiers inclus"
    if not active_bundles:
        st.info(
            "Aucune base brute d'épargne n'est disponible pour reconstituer le rapport. "
            "Téléversez un ou plusieurs fichiers détaillés, ou utilisez un fichier inclus pour les tests."
        )
        return

    current_bundle = active_bundles[0]
    previous_bundle = active_bundles[1] if len(active_bundles) > 1 else None
    current_df = current_bundle["df"]
    current_label = _bundle_label(current_bundle.get("bundle_date"), str(current_bundle.get("bundle_key")))
    current_snapshot, current_use = _build_epargne_report_snapshot(current_df, conversion_rate)
    current_ratios = _build_epargne_ratio_table(current_snapshot, current_use, current_df)
    current_total_usd = float(current_snapshot.loc[current_snapshot["PRODUITS"] == "TOTAL", "Total général en USD"].sum())
    current_total_accounts = int(current_snapshot.loc[current_snapshot["PRODUITS"] == "TOTAL", "Nbre de compte"].sum())
    usable_total = float(current_use["Montant utilisable"].sum()) if not current_use.empty else 0.0
    current_non_total = current_snapshot[current_snapshot["PRODUITS"] != "TOTAL"].copy()
    mix_df = (
        current_non_total.sort_values("Total général en USD", ascending=False)
        .head(10)[["PRODUITS", "Total général en USD", "Proportion"]]
        .copy()
    )
    utilization_chart_df = current_use.copy()
    current_snapshot_display = _format_snapshot_display(current_snapshot)
    current_use_display = _format_utilization_display(current_use)
    current_ratio_display = _format_ratio_display(current_ratios)

    render_panel_title("Rapport d'épargne")
    render_summary_box(
        "À retenir",
        [
            "Cette section reconstitue le rapport d'épargne à partir des fichiers chargés dans la session.",
            f"Source utilisée : {report_source_label}.",
            f"Taux utilisé : `{conversion_rate:,.0f}` CDF pour 1 USD.".replace(",", " "),
            "Les tableaux se mettent à jour automatiquement lorsque vous modifiez le taux dans la barre latérale.",
            f"Date analysée : {current_label} | Fichiers pris en compte : {len(current_bundle.get('files', []))}.",
        ],
    )
    render_kpi_cards(
        [
            ("Date analysée", current_label, "Date du fichier ou du groupe de fichiers", "slate"),
            ("Fichiers chargés", str(len(current_bundle.get("files", []))), "Fichiers pris en compte", "slate"),
            ("Comptes", f"{current_total_accounts:,}".replace(",", " "), "Nombre total", "slate"),
            (
                "Épargne totale (USD)",
                format_currency(current_total_usd),
                "Montant total estimé",
                "slate",
            ),
            ("Montant mobilisable", format_currency(usable_total), "Après application des normes BCC", "slate"),
            (
                "Reste non mobilisé",
                format_currency(current_total_usd - usable_total),
                "Montant encore disponible",
                "slate",
            ),
        ]
    )

    top_left, top_right = st.columns((1.7, 1))
    with top_left:
        render_panel_title(f"RAPPORT SOLDE ÉPARGNE AU {current_label}")
        st.dataframe(current_snapshot_display, width="stretch", hide_index=True)
    with top_right:
        render_panel_title("Utilisation selon la norme BCC")
        st.dataframe(current_use_display, width="stretch", hide_index=True)

    chart_left, chart_right = st.columns((1.15, 1))
    with chart_left:
        if not mix_df.empty:
            render_panel_title("Dépôts par produit")
            fig = px.bar(
                mix_df.sort_values("Total général en USD", ascending=True),
                x="Total général en USD",
                y="PRODUITS",
                orientation="h",
                color="Total général en USD",
                color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
            )
            fig.update_layout(coloraxis_showscale=False)
            st_plot(fig, key="portfolio_epargne_mix_chart", height=420)
    with chart_right:
        if not utilization_chart_df.empty:
            render_panel_title("Montant mobilisable")
            fig = px.bar(
                utilization_chart_df,
                x="Famille",
                y="Montant utilisable",
                color="Montant utilisable",
                color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
            )
            fig.update_layout(coloraxis_showscale=False)
            style_standard_vertical_bar(fig, height=340, tickangle=-20)
            st_plot(fig, key="portfolio_epargne_utilization_chart", height=340)

    ratio_left, ratio_right = st.columns((1, 1.2))
    with ratio_left:
        render_panel_title("Repères clés")
        st.dataframe(current_ratio_display, width="stretch", hide_index=True)
    with ratio_right:
        if not mix_df.empty:
            render_panel_title("Poids des produits")
            donut_df = mix_df.head(6).copy()
            fig = px.pie(
                donut_df,
                names="PRODUITS",
                values="Total général en USD",
                hole=0.58,
                color_discrete_sequence=["#0b2c63", "#2b74ca", "#4f8fdb", "#7fb2ea", "#a5caf2", "#dbe8f9"],
            )
            style_standard_donut(fig, height=380)
            st_plot(fig, key="portfolio_epargne_mix_donut", height=380)

    if previous_bundle is not None:
        previous_df = previous_bundle["df"]
        previous_label = _bundle_label(previous_bundle.get("bundle_date"), str(previous_bundle.get("bundle_key")))
        previous_snapshot, previous_use = _build_epargne_report_snapshot(previous_df, conversion_rate)
        variation_snapshot, variation_use = _build_epargne_report_variation(
            current_snapshot,
            previous_snapshot,
            current_use,
            previous_use,
        )
        previous_total_usd = float(previous_snapshot.loc[previous_snapshot["PRODUITS"] == "TOTAL", "Total général en USD"].sum())
        previous_total_accounts = int(previous_snapshot.loc[previous_snapshot["PRODUITS"] == "TOTAL", "Nbre de compte"].sum())

        render_panel_title("Comparaison des dates")
        render_kpi_cards(
            [
                (
                    "Variation dépôts USD",
                    format_currency(current_total_usd - previous_total_usd),
                    f"{previous_label} -> {current_label}",
                    "slate",
                ),
                (
                    "Variation comptes",
                    f"{current_total_accounts - previous_total_accounts:,}".replace(",", " "),
                    f"{previous_label} -> {current_label}",
                    "slate",
                ),
                (
                    "Variation mobilisable",
                    format_currency(
                        float(current_use["Montant utilisable"].sum()) - float(previous_use["Montant utilisable"].sum())
                    ),
                    "Évolution du montant utilisable",
                    "slate",
                ),
            ]
        )

        prev_left, prev_right = st.columns((1, 1))
        with prev_left:
            render_panel_title(f"RAPPORT SOLDE ÉPARGNE AU {previous_label}")
            st.dataframe(_format_snapshot_display(previous_snapshot), width="stretch", hide_index=True)
        with prev_right:
            render_panel_title(f"VARIATION ENTRE {previous_label} ET {current_label}")
            st.dataframe(_format_snapshot_display(variation_snapshot), width="stretch", hide_index=True)

        render_panel_title("Variation du montant mobilisable")
        st.dataframe(_format_utilization_display(variation_use, variation=True), width="stretch", hide_index=True)
    else:
        st.info(
            "Vous avez chargé des données pour une seule date. "
            "Pour comparer l'évolution, ajoutez aussi un fichier d'une date plus ancienne."
        )


def _render_operations_portfolio_report(df: pd.DataFrame, conversion_rate: float) -> None:
    work = normalize_operations_analysis_frame(
        df.loc[~df.get("annule", pd.Series(False, index=df.index)).fillna(False)].copy()
    )
    if work.empty:
        st.info("Aucune opération active n'est disponible pour construire le rapport dépôts / retraits.")
        return

    reporting_df = build_lbcft_reporting_table(work, conversion_rate)
    client_summary_df = build_client_movement_summary_table(work, conversion_rate).head(20)
    top_clients_df = build_top_clients_table(work, conversion_rate, top_n=20)
    mobile_df = build_mobile_banking_summary_table(work, conversion_rate)

    operation_count = int(work.get("operation_id", pd.Series(dtype="object")).nunique())
    client_count = int(work.get("client_id", pd.Series(dtype="object")).dropna().nunique())
    volume_total = float(pd.to_numeric(work.get("montant_operation"), errors="coerce").fillna(0.0).sum())
    depot_mask = work.get("type_mouvement", pd.Series(index=work.index)).isin(["Depot", "Depot mobile"])
    retrait_mask = work.get("type_mouvement", pd.Series(index=work.index)).isin(["Retrait", "Retrait mobile"])
    depot_volume = float(pd.to_numeric(work.loc[depot_mask, "montant_operation"], errors="coerce").fillna(0.0).sum())
    retrait_volume = float(pd.to_numeric(work.loc[retrait_mask, "montant_operation"], errors="coerce").fillna(0.0).sum())
    mobile_count = int(work.loc[work.get("source_mouvement", pd.Series(index=work.index)).eq("API_MOBILE"), "operation_id"].nunique())

    render_panel_title("Rapport dépôts et retraits")
    render_summary_box(
        "À retenir",
        [
            "Cette section restitue les contrôles transactionnels issus des exports SQL Server.",
            f"Taux de reporting utilisé : `{conversion_rate:,.0f}` CDF pour 1 USD.".replace(",", " "),
            "La synthèse LBC-FT reprend les principales lignes de travail du reporting mensuel.",
        ],
    )
    render_kpi_cards(
        [
            ("Opérations", f"{operation_count:,}".replace(",", " "), "Périmètre actif", "slate"),
            ("Clients", f"{client_count:,}".replace(",", " "), "Clients mouvementés", "slate"),
            ("Volume total", format_currency(volume_total), "Montant observé", "slate"),
            ("Dépôts", format_currency(depot_volume), "Volume dépôts", "slate"),
            ("Retraits", format_currency(retrait_volume), "Volume retraits", "slate"),
            ("Mobile banking", f"{mobile_count:,}".replace(",", " "), "Opérations API mobiles", "slate"),
        ]
    )

    top_left, top_right = st.columns((1.15, 1))
    with top_left:
        render_panel_title("Synthèse LBC-FT")
        if reporting_df.empty:
            st.info("La synthèse LBC-FT n'a pas pu être calculée sur le périmètre courant.")
        else:
            st.dataframe(reporting_df, width="stretch", hide_index=True)
    with top_right:
        render_panel_title("Dépôts et retraits agrégés par client")
        if client_summary_df.empty:
            st.info("Aucun résumé client n'est disponible.")
        else:
            st.dataframe(client_summary_df, width="stretch", hide_index=True)

    chart_left, chart_right = st.columns((1.05, 1))
    with chart_left:
        flux_df = pd.DataFrame(
            {
                "Mouvement": ["Dépôts", "Retraits"],
                "Montant": [depot_volume, retrait_volume],
            }
        )
        render_panel_title("Volumes dépôts / retraits")
        fig = px.bar(
            flux_df,
            x="Mouvement",
            y="Montant",
            color="Mouvement",
            color_discrete_map={"Dépôts": "#2b74ca", "Retraits": "#0b2c63"},
        )
        style_standard_vertical_bar(fig, height=340, tickangle=0)
        st_plot(fig, key="portfolio_operations_flux", height=340)
    with chart_right:
        render_panel_title("Mobile banking")
        if mobile_df.empty:
            st.info("Aucune opération mobile n'est disponible sur le périmètre courant.")
        else:
            mobile_chart_df = (
                mobile_df.groupby("type_operation", dropna=False)
                .agg(nb_operations=("nb_operations", "sum"))
                .reset_index()
                .sort_values("nb_operations", ascending=False)
            )
            fig = px.bar(
                mobile_chart_df,
                x="type_operation",
                y="nb_operations",
                color_discrete_sequence=["#4b84d7"],
            )
            style_standard_vertical_bar(fig, height=340, tickangle=-20)
            st_plot(fig, key="portfolio_operations_mobile", height=340)

    render_panel_title("Top clients par volume")
    if top_clients_df.empty:
        st.info("Aucun classement client n'est disponible.")
    else:
        st.dataframe(top_clients_df, width="stretch", hide_index=True)


def render_portfolio_tab(
    df: pd.DataFrame,
    cycle_key: str = "credit",
    conversion_rate: float = 2300.0,
    epargne_bundles: list[dict[str, object]] | None = None,
    epargne_source_label: str | None = None,
) -> None:
    if cycle_key == "epargne":
        _render_epargne_reconstructed_report(
            conversion_rate,
            bundles=epargne_bundles,
            source_label=epargne_source_label,
        )
        return
    if cycle_key == "operations_depot_retrait":
        _render_operations_portfolio_report(df, conversion_rate)
        return

    if df.empty:
        st.warning("Aucune donnée n'est disponible dans cet onglet.")
        return

    cycle_spec = get_cycle_spec(cycle_key)
    preset = get_cycle_analysis_preset(cycle_key)
    watchlist = build_cycle_watchlist(df, cycle_key)

    group_columns = [column for column in preset.get("group_columns", []) if column in df.columns]
    primary_group = group_columns[0] if group_columns else None
    secondary_group = group_columns[1] if len(group_columns) > 1 else None
    status_column = get_first_existing_column(df, preset.get("status_columns", []))
    actor_column = get_first_existing_column(df, preset.get("actor_columns", []))
    amount_column = _resolve_amount_column(df, preset.get("amount_columns", []))
    primary_count = int(df[primary_group].dropna().nunique()) if primary_group else 0
    secondary_count = int(df[secondary_group].dropna().nunique()) if secondary_group else 0
    actor_count = int(df[actor_column].dropna().nunique()) if actor_column else 0
    amount_total = float(df[amount_column].sum()) if amount_column else None

    render_panel_title("Portefeuille")
    render_kpi_cards(
        [
            (preset["record_label"], f"{len(df):,}".replace(",", " "), "Périmètre courant", "slate"),
            (
                primary_group.replace("_", " ").title() if primary_group else "Dimension 1",
                f"{primary_count:,}".replace(",", " "),
                "Catégories actives",
                "slate",
            ),
            (
                secondary_group.replace("_", " ").title() if secondary_group else "Dimension 2",
                f"{secondary_count:,}".replace(",", " "),
                "Sous-catégories actives",
                "slate",
            ),
            (
                actor_column.replace("_", " ").title() if actor_column else "Acteurs",
                f"{actor_count:,}".replace(",", " "),
                "Acteurs visibles",
                "slate",
            ),
            (
                "Montant total",
                format_currency(amount_total),
                "Montant recensé",
                "slate",
            ),
            (
                "Cas à suivre",
                f"{len(watchlist):,}".replace(",", " "),
                "Liste de suivi",
                "slate",
            ),
        ]
    )
    render_summary_box(
        "À retenir",
        [
            f"Cette section présente les volumes, regroupements et croisements utiles du {cycle_spec['label']}.",
            f"Le regroupement principal utilisé est `{primary_group}`." if primary_group else "Aucun regroupement principal n'a été détecté.",
        ],
    )

    col1, col2 = st.columns(2)

    with col1:
        if primary_group and amount_column:
            primary_amounts = build_grouped_amounts(df, primary_group, amount_column=amount_column)
            if not primary_amounts.empty:
                render_panel_title(f"Répartition par {primary_group.replace('_', ' ')}")
                fig = px.bar(
                    primary_amounts,
                    x=primary_group,
                    y=amount_column,
                    color=amount_column,
                    color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
                )
                fig.update_layout(height=360, coloraxis_showscale=False)
                st_plot(fig, key=f"portfolio_primary_amounts_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement principal par montant n'est disponible.")
        elif primary_group:
            freq_df = build_frequency_table(df, primary_group, top_n=10)
            if not freq_df.empty:
                render_panel_title(f"Répartition par {primary_group.replace('_', ' ')}")
                fig = px.bar(freq_df, x=primary_group, y="nombre_lignes", color_discrete_sequence=["#2b74ca"])
                fig.update_layout(height=360, showlegend=False, xaxis_tickangle=-25)
                st_plot(fig, key=f"portfolio_primary_freq_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement principal n'est disponible.")

    with col2:
        if secondary_group and amount_column:
            secondary_amounts = build_grouped_amounts(df, secondary_group, amount_column=amount_column)
            if not secondary_amounts.empty:
                render_panel_title(f"{secondary_group.replace('_', ' ').title()} par montant")
                fig = px.bar(
                    secondary_amounts,
                    x=secondary_group,
                    y=amount_column,
                    color=amount_column,
                    color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
                )
                fig.update_layout(height=360, coloraxis_showscale=False)
                st_plot(fig, key=f"portfolio_secondary_amounts_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement secondaire par montant n'est disponible.")
        elif secondary_group:
            freq_df = build_frequency_table(df, secondary_group, top_n=10)
            if not freq_df.empty:
                render_panel_title(f"{secondary_group.replace('_', ' ').title()}")
                fig = px.bar(freq_df, x=secondary_group, y="nombre_lignes", color_discrete_sequence=["#4b84d7"])
                fig.update_layout(height=360, showlegend=False, xaxis_tickangle=-25)
                st_plot(fig, key=f"portfolio_secondary_freq_{cycle_key}", height=360)
            else:
                st.info("Aucun regroupement secondaire n'est disponible.")

    lower_left, lower_right = st.columns((1, 1.15))

    with lower_left:
        if cycle_key in {"credit", "likelemba"} and "statut_dossier" in df.columns:
            flow_df = build_status_flow_table(df)
            if not flow_df.empty:
                render_panel_title("Flux des statuts")
                fig = px.bar(
                    flow_df,
                    x="statut_dossier",
                    y="nombre_dossiers",
                    color="nombre_dossiers",
                    color_continuous_scale=["#dbe8f9", "#2b74ca", "#0b2c63"],
                )
                fig.update_layout(height=340, coloraxis_showscale=False)
                st_plot(fig, key=f"portfolio_status_flow_{cycle_key}", height=340)
        elif status_column:
            status_df = build_frequency_table(df, status_column, top_n=10)
            if not status_df.empty:
                render_panel_title(f"Distribution de {status_column.replace('_', ' ')}")
                fig = px.bar(
                    status_df,
                    x=status_column,
                    y="nombre_lignes",
                    color_discrete_sequence=["#2b74ca"],
                )
                fig.update_layout(height=340, showlegend=False, xaxis_tickangle=-25)
                st_plot(fig, key=f"portfolio_status_distribution_{cycle_key}", height=340)

    with lower_right:
        if primary_group:
            summary_df = build_activity_table(
                df,
                primary_group,
                amount_columns=preset.get("amount_columns", []),
                alert_index=watchlist.index if not watchlist.empty else None,
                top_n=8,
            )
            if not summary_df.empty:
                render_panel_title(f"{primary_group.replace('_', ' ').title()}")
                st.dataframe(summary_df, width="stretch", hide_index=True)

    if primary_group and secondary_group and amount_column:
        pivot = pd.pivot_table(
            df,
            index=primary_group,
            columns=secondary_group,
            values=amount_column,
            aggfunc="sum",
            fill_value=0,
        )
        render_panel_title("Lecture croisée")
        st.dataframe(pivot, width="stretch")

    render_panel_title("Cas à suivre")
    if watchlist.empty:
        st.success("Aucun point sensible n'a été détecté avec les règles actuelles.")
    else:
        st.dataframe(watchlist.head(200), width="stretch", hide_index=True)
