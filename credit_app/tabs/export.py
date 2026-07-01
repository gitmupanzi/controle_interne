from __future__ import annotations

from io import BytesIO
from datetime import datetime

import pandas as pd
import streamlit as st

from credit_app.ui import render_kpi_cards, render_panel_title, render_summary_box


def _to_excel_bytes(df: pd.DataFrame, quality_df: pd.DataFrame, mapping_df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="donnees_standardisees", index=False)
        quality_df.to_excel(writer, sheet_name="controles_qualite", index=False)
        mapping_df.to_excel(writer, sheet_name="mapping_colonnes", index=False)
    buffer.seek(0)
    return buffer.getvalue()


def render_export_tab(df: pd.DataFrame, quality_df: pd.DataFrame, mapping_df: pd.DataFrame) -> None:
    render_panel_title("Export")

    if df.empty:
        st.warning("Aucune donnee a exporter avec les filtres actuels.")
        return

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    renamed_columns = int((mapping_df["colonne_source"] != mapping_df["colonne_standard"]).sum()) if not mapping_df.empty else 0
    render_kpi_cards(
        [
            ("Lignes exportees", f"{len(df):,}".replace(",", " "), "Perimetre filtre", "blue"),
            ("Colonnes exportees", str(df.shape[1]), "Donnees standardisees", "navy"),
            ("Feuilles Excel", "3", "Donnees, qualite, mapping", "green"),
            ("Colonnes reconnues", str(renamed_columns), "Traitees automatiquement", "orange"),
        ]
    )

    render_summary_box(
        "Pack de restitution",
        [
            "L'export reprend les donnees standardisees, les controles qualite et le mapping des colonnes.",
            f"Horodatage de generation : {generated_at}.",
        ],
    )

    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    excel_bytes = _to_excel_bytes(df, quality_df, mapping_df)

    st.download_button(
        "Telecharger les donnees standardisees (CSV)",
        data=csv_bytes,
        file_name="analyste_credit_donnees_standardisees.csv",
        mime="text/csv",
        width="stretch",
    )

    st.download_button(
        "Telecharger le pack d'analyse (Excel)",
        data=excel_bytes,
        file_name="analyste_credit_pack_analyse.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

    st.markdown(
        """
        Le pack Excel contient :

        - les donnees standardisees filtrees
        - les controles qualite
        - le mapping des colonnes source -> standard
        """
    )
