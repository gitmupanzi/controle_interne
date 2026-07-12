from __future__ import annotations

import streamlit as st

from credit_app.ui import render_kpi_cards, render_panel_title, render_summary_box


def render_preparation_status(summary: dict[str, object]) -> None:
    render_panel_title("Préparation des données")
    status = str(summary.get("status", "warning"))
    status_label = {
        "ready": "Prêt pour l’analyse",
        "warning": "Prêt avec vérifications",
        "correction_required": "Correction nécessaire",
    }.get(status, "À vérifier")
    color = {"ready": "green", "warning": "orange", "correction_required": "red"}.get(status, "slate")
    render_kpi_cards(
        [
            ("État final", status_label, "Résultat de la préparation", color),
            ("Fichiers détectés", str(summary.get("file_count", 0)), "Sources sélectionnées", "blue"),
            ("Fichiers regroupés", str(summary.get("compiled_file_count", 0)), "Compilation", "navy"),
            ("Lignes prêtes", f"{int(summary.get('ready_rows', 0)):,}".replace(",", " "), "Après préparation", "green"),
            ("Colonnes harmonisées", str(summary.get("renamed_columns", 0)), "Renommage contrôlé", "slate"),
            ("Doublons", str(summary.get("duplicate_count", 0)), "À vérifier", "orange"),
        ]
    )

    messages: list[str] = []
    compiled_count = int(summary.get("compiled_file_count", 0))
    if compiled_count:
        messages.append(f"{compiled_count} fichier(s) compatible(s) ont été regroupé(s).")
    renamed = int(summary.get("renamed_columns", 0))
    messages.append(f"{renamed} nom(s) de colonne ont été harmonisé(s).")
    messages.extend(str(message) for message in summary.get("warnings", ()))
    messages.extend(str(message) for message in summary.get("blocking_errors", ()))
    messages.append(f"État final : {status_label.lower()}.")
    render_summary_box("Résultat de la préparation", messages)

    with st.expander("Voir le rapport technique de préparation", expanded=False):
        st.write(f"Lignes source : **{int(summary.get('raw_rows', 0)):,}**".replace(",", " "))
        st.write(f"Lignes ignorées : **{int(summary.get('ignored_rows', 0)):,}**".replace(",", " "))
        st.write(f"Anomalies remontées par les contrôles : **{int(summary.get('anomaly_count', 0)):,}**".replace(",", " "))
        missing = tuple(summary.get("missing_expected", ()))
        if missing:
            st.write("Champs métier attendus non détectés :")
            st.code(", ".join(map(str, missing)), language="text")
