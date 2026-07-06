from __future__ import annotations

import html
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

try:
    from streamlit.components.v2 import manifest_scanner as _streamlit_manifest_scanner
except Exception:
    _streamlit_manifest_scanner = None
else:
    if not getattr(_streamlit_manifest_scanner, "_credit_safe_patch_applied", False):
        def _safe_is_likely_streamlit_component_package(dist: object) -> bool:
            try:
                name = getattr(dist, "name", None)
                metadata = getattr(dist, "metadata", None)
                if not isinstance(name, str) or not name.strip():
                    return False
                normalized_name = name.lower()

                summary = ""
                if metadata is not None:
                    if hasattr(metadata, "get"):
                        summary_value = metadata.get("Summary")
                    elif "Summary" in metadata:
                        summary_value = metadata["Summary"]
                    else:
                        summary_value = None
                    if isinstance(summary_value, str):
                        summary = summary_value.lower()

                if "streamlit" in normalized_name or "streamlit" in summary:
                    return True

                requires_dist = []
                if metadata is not None and hasattr(metadata, "get_all"):
                    requires_dist = metadata.get_all("Requires-Dist") or []
                for requirement in requires_dist:
                    if isinstance(requirement, str) and "streamlit" in requirement.lower():
                        return True

                return normalized_name.startswith(("streamlit-", "streamlit_", "st-", "st_"))
            except Exception:
                return False

        _streamlit_manifest_scanner._is_likely_streamlit_component_package = _safe_is_likely_streamlit_component_package
        _streamlit_manifest_scanner._credit_safe_patch_applied = True

import streamlit as st

from credit_app.app_loader import (
    get_excel_sheet_names,
    get_excel_sheet_names_from_path,
    list_available_line_list_files,
    load_dataframe_from_bytes,
    load_dataframe_from_path,
)
from credit_app.compilation.fichiers_compilation import (
    charger_fichiers_excel,
    extraire_attr_dataframe,
)
from credit_app.cycles import (
    DEFAULT_CYCLE_KEY,
    build_cycle_coverage_summary,
    get_cycle_analysis_preset,
    get_cycle_spec,
    list_cycle_keys,
)
from credit_app.domain import (
    build_mapping_frame,
    build_missing_values_frame,
    build_monthly_series,
    build_quality_checks,
    build_standardized_dataframe,
    filter_dataframe,
    get_cycle_primary_date_column,
    get_reference_column_count,
    normalize_text,
)
from credit_app.tabs.audit_control import render_analyste_credit_tab
from credit_app.tabs.crm_clients import render_crm_clients_tab
from credit_app.tabs.export import render_export_tab
from credit_app.tabs.methodology import render_methodology_tab
from credit_app.tabs.overview import render_overview_tab
from credit_app.tabs.portfolio import (
    build_epargne_bundles_from_standardized_frames,
    render_portfolio_tab,
)
from credit_app.tabs.quality import render_quality_tab
from credit_app.tabs.risk import render_risk_tab
from credit_app.tabs.surveillance import render_surveillance_tab
import credit_app.ui as credit_ui

format_context_value = credit_ui.format_context_value
inject_professional_credit_css = credit_ui.inject_professional_credit_css
render_context_row = credit_ui.render_context_row
render_footer = credit_ui.render_footer
render_panel_title = credit_ui.render_panel_title
render_professional_header = credit_ui.render_professional_header
render_summary_box = credit_ui.render_summary_box


def _fallback_render_sidebar_intro_card(
    kicker: str,
    title: str,
    lines: list[str],
    *,
    container: object | None = None,
) -> None:
    target = container or st.sidebar
    rendered_lines = "".join(f"<div>{html.escape(str(line))}</div>" for line in lines)
    target.markdown(
        f"""
<div style="padding:0.95rem 1rem;border-radius:18px;background:linear-gradient(125deg,#0b2c63 0%,#1553a1 100%);color:#fff;margin-bottom:0.8rem;">
  <div style="font-size:0.68rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:800;opacity:0.82;margin-bottom:0.25rem;">{html.escape(str(kicker))}</div>
  <div style="font-size:1rem;font-weight:800;line-height:1.15;margin-bottom:0.3rem;">{html.escape(str(title))}</div>
  <div style="font-size:0.78rem;line-height:1.35;opacity:0.95;">{rendered_lines}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def _fallback_render_sidebar_section(
    title: str,
    subtitle: str | None = None,
    *,
    container: object | None = None,
) -> None:
    target = container or st.sidebar
    subtitle_html = f"<div style='color:#55708f;font-size:0.75rem;line-height:1.3;margin-bottom:0.28rem;'>{html.escape(str(subtitle))}</div>" if subtitle else ""
    target.markdown(
        f"""
<div style="margin:0.7rem 0 0.45rem;">
  <div style="color:#0b2c63;font-size:0.88rem;text-transform:uppercase;letter-spacing:0.08em;font-weight:800;margin-bottom:0.12rem;">{html.escape(str(title))}</div>
  {subtitle_html}
</div>
        """,
        unsafe_allow_html=True,
    )


def _fallback_render_sidebar_stat_grid(
    items: list[tuple[str, str]],
    *,
    container: object | None = None,
) -> None:
    target = container or st.sidebar
    blocks = "".join(
        f"""
<div style="background:rgba(255,255,255,0.80);border:1px solid rgba(11,44,99,0.08);border-radius:16px;padding:0.55rem 0.65rem;">
  <div style="color:#5d7390;font-size:0.62rem;text-transform:uppercase;letter-spacing:0.08em;font-weight:800;margin-bottom:0.18rem;">{html.escape(str(label))}</div>
  <div style="color:#0b2c63;font-size:0.95rem;font-weight:800;line-height:1.1;">{html.escape(str(value))}</div>
</div>
"""
        for label, value in items
    )
    target.markdown(
        f"<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.45rem;margin-bottom:0.65rem;'>{blocks}</div>",
        unsafe_allow_html=True,
    )


render_sidebar_intro_card = getattr(credit_ui, "render_sidebar_intro_card", _fallback_render_sidebar_intro_card)
render_sidebar_section = getattr(credit_ui, "render_sidebar_section", _fallback_render_sidebar_section)
render_sidebar_stat_grid = getattr(credit_ui, "render_sidebar_stat_grid", _fallback_render_sidebar_stat_grid)

def configure_page() -> None:
    st.set_page_config(
        page_title="Contrôle interne IMF",
        page_icon="CI",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_professional_credit_css()


@st.cache_data(show_spinner=False)
def prepare_dataset(file_bytes: bytes, filename: str, sheet_name: str | None) -> dict:
    raw_df = load_dataframe_from_bytes(file_bytes, filename, sheet_name)
    return _prepare_payload_from_dataframe(raw_df)


@st.cache_data(show_spinner=False)
def prepare_dataset_from_path(file_path: str, sheet_name: str | None) -> dict:
    raw_df = load_dataframe_from_path(file_path, sheet_name)
    return _prepare_payload_from_dataframe(raw_df)


@st.cache_data(show_spinner=False)
def prepare_compiled_dataset_from_paths(file_paths: tuple[str, ...], sheet_name: str) -> dict:
    raw_df, compilation_log_df = charger_fichiers_excel(
        liste_fichiers=list(file_paths),
        sheet_name=sheet_name,
        colonne_source="Provenance",
        suffixer_doublons=False,
        renommer_variable=True,
        variables_brute=False,
        sheet_log=True,
        log_only_changed=True,
    )
    payload = _prepare_payload_from_dataframe(raw_df)
    payload["compilation_log_df"] = compilation_log_df
    payload["compiled_files"] = list(file_paths)
    payload["column_collisions_df"] = extraire_attr_dataframe(raw_df.attrs.get("column_collisions", []))
    payload["column_provenance"] = raw_df.attrs.get("column_provenance", {})
    return payload


@st.cache_data(show_spinner=False)
def prepare_compiled_dataset_from_uploads(uploaded_items: tuple[tuple[str, bytes], ...], sheet_name: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="controle_interne_compile_") as temp_dir:
        temp_paths: list[str] = []
        for filename, file_bytes in uploaded_items:
            temp_path = Path(temp_dir) / filename
            temp_path.write_bytes(file_bytes)
            temp_paths.append(str(temp_path))
        payload = prepare_compiled_dataset_from_paths(tuple(temp_paths), sheet_name)
    payload["compiled_files"] = [filename for filename, _ in uploaded_items]
    return payload


@st.cache_data(show_spinner=False)
def prepare_epargne_bundles_from_uploads(
    uploaded_items: tuple[tuple[str, bytes], ...],
    sheet_name: str | None,
) -> list[dict[str, object]]:
    frames: list[tuple[str, pd.DataFrame]] = []
    for filename, file_bytes in uploaded_items:
        raw_df = load_dataframe_from_bytes(file_bytes, filename, sheet_name)
        standardized_df, _ = build_standardized_dataframe(raw_df)
        frames.append((filename, standardized_df))
    return build_epargne_bundles_from_standardized_frames(frames)


@st.cache_data(show_spinner=False)
def prepare_epargne_bundles_from_paths(
    file_paths: tuple[str, ...],
    sheet_name: str | None,
) -> list[dict[str, object]]:
    frames: list[tuple[str, pd.DataFrame]] = []
    for file_path in file_paths:
        raw_df = load_dataframe_from_path(file_path, sheet_name)
        standardized_df, _ = build_standardized_dataframe(raw_df)
        frames.append((Path(file_path).name, standardized_df))
    return build_epargne_bundles_from_standardized_frames(frames)


def _prepare_payload_from_dataframe(raw_df: pd.DataFrame) -> dict:
    standardized_df, mapping = build_standardized_dataframe(raw_df)
    quality_df = build_quality_checks(standardized_df)
    missing_df = build_missing_values_frame(standardized_df)
    mapping_df = build_mapping_frame(mapping)
    return {
        "raw_df": raw_df,
        "standardized_df": standardized_df,
        "quality_df": quality_df,
        "missing_df": missing_df,
        "mapping_df": mapping_df,
    }


def _get_common_excel_sheets(file_paths: list[Path]) -> list[str]:
    common_sheets: set[str] | None = None
    for file_path in file_paths:
        if file_path.suffix.lower() not in {".xlsx", ".xls"}:
            continue
        try:
            sheet_names = set(get_excel_sheet_names_from_path(file_path))
        except Exception:
            continue
        common_sheets = sheet_names if common_sheets is None else (common_sheets & sheet_names)
    return sorted(common_sheets or [])


def _get_common_excel_sheets_from_uploads(uploaded_items: list[tuple[str, bytes]]) -> list[str]:
    common_sheets: set[str] | None = None
    for _, file_bytes in uploaded_items:
        try:
            sheet_names = set(get_excel_sheet_names(file_bytes))
        except Exception:
            continue
        common_sheets = sheet_names if common_sheets is None else (common_sheets & sheet_names)
    return sorted(common_sheets or [])


def _preferred_included_file_index(file_names: list[str]) -> int:
    if not file_names:
        return 0
    for index, name in enumerate(file_names):
        if "base_donnees_brute_credit" in name.lower():
            return index
    return 0


def _normalize_multiselect_with_all(
    key: str,
    options: list[str],
    default_to_all: bool = True,
) -> list[str]:
    normalized_options = ["Toutes"] + options if options else ["Toutes"]
    current_value = st.session_state.get(key)
    if not isinstance(current_value, list) or any(value not in normalized_options for value in current_value):
        st.session_state[key] = ["Toutes"] if default_to_all else []
    if not st.session_state[key] and default_to_all:
        st.session_state[key] = ["Toutes"]
    return normalized_options


def _resolve_multiselect_selection(values: list[str]) -> list[str] | None:
    if not values or "Toutes" in values:
        return None
    return values


def _reset_sidebar_filters() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("credit_filter_sel_") or key in {
            "credit_filter_use_period",
            "credit_period_range",
        }:
            if key in st.session_state:
                del st.session_state[key]


def _reset_display_options() -> None:
    for key in [
        "credit_annot_vals",
        "credit_annot_min",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def _date_filter_label(date_column: str | None) -> str:
    labels = {
        "date_demande": "Période de demande",
        "date_decision": "Période de décision",
        "date_operation": "Période d'opération",
        "date_entree": "Période d'entrée",
        "date_activation": "Période d'activation",
        "date_revocation": "Période de révocation",
        "date_sauvegarde": "Période de sauvegarde",
    }
    return labels.get(str(date_column), "Période analytique")


def _filter_column_label(column_name: str) -> str:
    labels = {
        "statut_dossier": "Statut du dossier",
        "statut_remboursement": "Statut de remboursement",
        "agence": "Agence",
        "type_produit": "Produit",
        "agent_credit": "Agent de crédit",
        "nom_groupe": "Groupe",
        "activite_economique": "Activité économique",
        "statut_compte": "Statut du compte",
        "type_operation": "Type d'opération",
        "compte_id": "Compte",
        "caissier": "Caissier",
        "banque": "Banque",
        "compte_bancaire": "Compte bancaire",
        "devise": "Devise",
        "journal": "Journal",
        "compte_comptable": "Compte comptable",
        "centre_cout": "Centre de coût",
        "fonction": "Fonction",
        "statut_agent": "Statut de l'agent",
        "application_source": "Application",
        "profil_acces": "Profil d'accès",
        "niveau_habilitation": "Niveau d'habilitation",
        "type_sauvegarde": "Type de sauvegarde",
        "support_sauvegarde": "Support de sauvegarde",
        "statut_test_reprise": "Statut du test de reprise",
        "operateur": "Opérateur",
        "tresorier": "Trésorier",
        "type_client": "Type de client",
        "zone_geographique": "Zone géographique",
        "categorie": "Catégorie",
        "sexe": "Sexe",
        "compte_id": "Compte",
    }
    return labels.get(column_name, column_name.replace("_", " ").capitalize())


def _build_cycle_sidebar_filters(
    df: pd.DataFrame,
    cycle_key: str,
) -> dict[str, list[str] | None]:
    preset = get_cycle_analysis_preset(cycle_key)
    candidate_columns = preset.get("filter_columns", [])
    selected_filters: dict[str, list[str] | None] = {}

    for column_name in candidate_columns:
        if column_name not in df.columns:
            continue
        options = sorted(value for value in df[column_name].dropna().unique())
        if not options:
            continue
        widget_key = f"credit_filter_sel_{column_name}"
        widget_options = _normalize_multiselect_with_all(widget_key, options)
        selected_values = st.sidebar.multiselect(
            f"{_filter_column_label(column_name)} ({len(options)})",
            widget_options,
            key=widget_key,
        )
        selected_filters[column_name] = _resolve_multiselect_selection(selected_values)
    return selected_filters


def _count_active_sidebar_filters(selected_filters: dict[str, list[str] | None]) -> int:
    return sum(1 for values in selected_filters.values() if values)


def main() -> None:
    configure_page()
    render_professional_header()

    available_files = list_available_line_list_files()
    available_excel_files = [
        path for path in available_files if path.suffix.lower() in {".xlsx", ".xls"}
    ]
    cycle_options = list_cycle_keys()
    default_cycle_index = cycle_options.index(DEFAULT_CYCLE_KEY) if DEFAULT_CYCLE_KEY in cycle_options else 0
    render_sidebar_intro_card(
        "Pilotage",
        "Centre de contrôle",
        [
            "Choisissez un cycle, chargez une base et appliquez les filtres métier du périmètre actif.",
            "Les KPI standard et les analyses détaillées se synchronisent automatiquement avec le cycle sélectionné.",
        ],
    )
    render_sidebar_section("Référentiel de contrôle", "Sélection du cycle à analyser.")
    selected_cycle_key = st.sidebar.selectbox(
        "Type de cycle",
        options=cycle_options,
        index=default_cycle_index,
        format_func=lambda key: get_cycle_spec(key)["label"],
        key="credit_cycle_key",
    )
    selected_cycle = get_cycle_spec(selected_cycle_key)
    with st.sidebar.expander("Repère du cycle", expanded=False):
        st.caption(selected_cycle["summary"])
        st.caption(selected_cycle["control_objective"])

    render_sidebar_section("Source des données", "Téléversez un fichier ou utilisez une base déjà stockée.")
    if "credit_source_mode" not in st.session_state:
        st.session_state["credit_source_mode"] = "Téléverser un fichier"
    source_mode = st.sidebar.selectbox(
        "Source de données",
        [
            "Téléverser un fichier",
            "Téléverser plusieurs fichiers",
            "Charger un fichier inclus",
            "Compiler plusieurs fichiers inclus",
        ],
        index=0,
        key="credit_source_mode",
    )

    uploaded_file = None
    uploaded_files = []
    selected_local_path = None
    selected_compilation_paths: list[Path] = []
    sheet_name = None
    filename = None

    if source_mode == "Téléverser un fichier":
        uploaded_file = st.sidebar.file_uploader(
            "Base crédit",
            type=["xlsx", "xls", "csv"],
            help="Formats acceptés : Excel ou CSV.",
        )
    elif source_mode == "Téléverser plusieurs fichiers":
        uploaded_files = st.sidebar.file_uploader(
            "Bases à compiler",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            help="Sélectionnez plusieurs fichiers Excel détaillés partageant la même feuille métier.",
        ) or []
        if uploaded_files:
            common_sheets = _get_common_excel_sheets_from_uploads(
                [(file.name, file.getvalue()) for file in uploaded_files]
            )
            if common_sheets:
                sheet_name = st.sidebar.selectbox(
                    "Feuille commune",
                    common_sheets,
                    index=0,
                    key="credit_upload_compile_sheet_name",
                )
            else:
                sheet_name = st.sidebar.text_input(
                    "Nom de la feuille commune",
                    value="",
                    key="credit_upload_compile_sheet_name_manual",
                    help="À renseigner uniquement si la feuille n'a pas pu être détectée automatiquement.",
                ).strip() or None
            filename = f"Compilation de {len(uploaded_files)} fichiers téléversés"
            st.sidebar.caption(
                f"{len(uploaded_files)} fichier(s) téléversé(s) pour une compilation unique."
            )
        else:
            st.sidebar.caption("Téléversez au moins deux fichiers Excel détaillés pour lancer une compilation.")
    elif source_mode == "Charger un fichier inclus":
        if available_files:
            available_names = [path.name for path in available_files]
            selected_name = st.sidebar.selectbox(
                "Fichier inclus",
                available_names,
                index=_preferred_included_file_index(available_names),
                key="credit_included_file",
            )
            selected_local_path = next(path for path in available_files if path.name == selected_name)
            filename = selected_local_path.name
            if filename.lower().endswith((".xlsx", ".xls")):
                local_sheets = get_excel_sheet_names_from_path(selected_local_path)
                if local_sheets:
                    sheet_name = st.sidebar.selectbox("Feuille Excel", local_sheets, index=0, key="local_sheet_name")
        else:
            st.sidebar.warning("Aucun fichier `.xlsx`, `.xls` ou `.csv` n'a été trouvé dans `line_list/`.")
    else:
        if len(available_excel_files) >= 2:
            compile_filter = st.sidebar.text_input(
                "Filtre nom fichier",
                value="",
                key="credit_compile_filter",
                help="Permet de limiter la liste avant sélection des fichiers à compiler.",
            )
            filtered_compile_paths = [
                path
                for path in available_excel_files
                if compile_filter.strip().lower() in path.name.lower()
            ]
            selected_compile_names = st.sidebar.multiselect(
                "Fichiers à compiler",
                [path.name for path in filtered_compile_paths],
                key="credit_compile_files",
                help="Sélectionnez au moins deux fichiers Excel détaillés partageant la même feuille métier.",
            )
            selected_compilation_paths = [
                path for path in filtered_compile_paths if path.name in selected_compile_names
            ]
            if selected_compilation_paths:
                common_sheets = _get_common_excel_sheets(selected_compilation_paths)
                if common_sheets:
                    sheet_name = st.sidebar.selectbox(
                        "Feuille commune",
                        common_sheets,
                        index=0,
                        key="credit_compile_sheet_name",
                    )
                else:
                    sheet_name = st.sidebar.text_input(
                        "Nom de la feuille commune",
                        value="",
                        key="credit_compile_sheet_name_manual",
                        help="À renseigner uniquement si la feuille n'a pas pu être détectée automatiquement.",
                    ).strip() or None
                filename = f"Compilation de {len(selected_compilation_paths)} fichiers"
                st.sidebar.caption(
                    f"{len(selected_compilation_paths)} fichier(s) sélectionné(s) pour une compilation unique."
                )
            else:
                st.sidebar.caption("Sélectionnez plusieurs fichiers détaillés pour créer une base compilée.")
        elif available_excel_files:
            st.sidebar.warning("Au moins deux fichiers Excel sont nécessaires pour lancer une compilation.")
        else:
            st.sidebar.warning("Aucun fichier Excel n'a été trouvé dans `line_list/` pour la compilation.")

    with st.sidebar.expander("Référence et stockage", expanded=False):
        st.caption(
            f"Référence de renommage active : `data/Rename_columns.xlsx` ({get_reference_column_count()} alias)"
        )
        st.caption("Vous pouvez déposer vos fichiers de travail dans `line_list/` pour les relire ensuite sans téléversement.")

    if source_mode == "Téléverser un fichier" and uploaded_file is None:
        selected_local_path = None

    if source_mode == "Téléverser un fichier":
        source_ready = uploaded_file is not None
    elif source_mode == "Téléverser plusieurs fichiers":
        source_ready = len(uploaded_files) >= 2 and bool(sheet_name)
    elif source_mode == "Charger un fichier inclus":
        source_ready = selected_local_path is not None
    else:
        source_ready = len(selected_compilation_paths) >= 2 and bool(sheet_name)

    if not source_ready:
        render_context_row(
            [
                ("Cycle", selected_cycle["label"]),
                ("Source", "Aucun fichier"),
                ("Formats", "Excel, CSV ou compilation Excel"),
                ("Analyses", "Vue d'ensemble, portefeuille, risque, qualité"),
                ("Mode", "Fichier unique, plusieurs fichiers ou compilation"),
            ]
        )
        render_summary_box(
            "Pour commencer",
            [
                selected_cycle["summary"],
                "Chargez un fichier Excel ou CSV, utilisez un fichier déjà disponible pour les tests, ou regroupez plusieurs bases détaillées.",
                "L'application reconnaît automatiquement plusieurs variantes de colonnes métier.",
                "Le fichier `data/Rename_columns.xlsx` est aussi pris en compte pour harmoniser les noms de colonnes.",
            ],
        )
        render_footer()
        return

    if source_mode == "Téléverser un fichier":
        file_bytes = uploaded_file.getvalue()
        filename = uploaded_file.name
        sheet_name = None

        if filename.lower().endswith((".xlsx", ".xls")):
            sheets = get_excel_sheet_names(file_bytes)
            if sheets:
                sheet_name = st.sidebar.selectbox("Feuille Excel", sheets, index=0)

        with st.spinner("Préparation de la base en cours..."):
            payload = prepare_dataset(file_bytes, filename, sheet_name)
    elif source_mode == "Téléverser plusieurs fichiers":
        uploaded_items = tuple((file.name, file.getvalue()) for file in uploaded_files)
        with st.spinner("Compilation et préparation des fichiers téléversés en cours..."):
            payload = prepare_compiled_dataset_from_uploads(uploaded_items, sheet_name or "")
    elif source_mode == "Charger un fichier inclus":
        with st.spinner("Préparation de la base en cours..."):
            payload = prepare_dataset_from_path(str(selected_local_path), sheet_name)
    else:
        compiled_paths = tuple(str(path) for path in selected_compilation_paths)
        with st.spinner("Compilation et préparation des bases en cours..."):
            payload = prepare_compiled_dataset_from_paths(compiled_paths, sheet_name or "")

    raw_df = payload["raw_df"]
    standardized_df = payload["standardized_df"]
    if source_mode == "Téléverser un fichier":
        source_label = "Téléversement"
    elif source_mode == "Téléverser plusieurs fichiers":
        source_label = "Téléversement multi-fichiers"
    elif source_mode == "Charger un fichier inclus":
        source_label = "Fichier inclus"
    else:
        source_label = "Compilation multi-fichiers"
    cycle_coverage = build_cycle_coverage_summary(standardized_df, selected_cycle_key)

    render_context_row(
        [
            ("Cycle", selected_cycle["label"]),
            ("Source", filename),
            ("Mode", source_label),
        ]
    )
    with st.expander("Données utilisées", expanded=False):
        st.write(f"Mode de chargement : **{source_label}**")
        st.write(f"Fichier utilisé : **{filename}**")
        if source_mode == "Charger un fichier inclus" and selected_local_path is not None:
            st.write(f"Chemin local : `{selected_local_path}`")
        if source_mode in {"Téléverser plusieurs fichiers", "Compiler plusieurs fichiers inclus"}:
            st.write(f"Fichiers regroupés : **{len(payload.get('compiled_files', []))}**")
            for compiled_file in payload.get("compiled_files", []):
                st.write(f"- `{compiled_file}`")
        if sheet_name:
            st.write(f"Feuille active : **{sheet_name}**")
        st.write(
            f"Référence de renommage : **data/Rename_columns.xlsx** avec **{get_reference_column_count()}** correspondances chargées."
        )
        st.write(f"Cycle analysé : **{selected_cycle['label']}**")
        st.write(f"Couverture du référentiel : **{cycle_coverage['detected_count']}/{cycle_coverage['total']}** champs clés reconnus.")
        compilation_log_df = payload.get("compilation_log_df")
        if isinstance(compilation_log_df, pd.DataFrame) and not compilation_log_df.empty:
            st.write(f"Journal de compilation : **{len(compilation_log_df)}** modification(s) de colonnes.")
        collision_df = payload.get("column_collisions_df")
        if isinstance(collision_df, pd.DataFrame) and not collision_df.empty:
            st.write(f"Collisions de colonnes détectées : **{len(collision_df)}**")

    render_sidebar_section("Filtres métier", "Les filtres proposés dépendent du cycle choisi.")
    st.sidebar.button("Réinitialiser les filtres", key="credit_reset_filters", on_click=_reset_sidebar_filters, width="stretch")

    selected_column_filters = _build_cycle_sidebar_filters(standardized_df, selected_cycle_key)

    render_sidebar_section("Période", "Filtrez les données selon la date principale du cycle.")
    start_date = None
    end_date = None
    selected_date_column = get_cycle_primary_date_column(standardized_df, selected_cycle_key)
    use_period_filter = st.sidebar.checkbox(
        f"Filtrer sur {_date_filter_label(selected_date_column).lower()}",
        value=False,
        key="credit_filter_use_period",
    )
    if selected_date_column and selected_date_column in standardized_df.columns:
        valid_dates = pd.to_datetime(standardized_df[selected_date_column], errors="coerce").dropna()
        if not valid_dates.empty:
            default_range = (valid_dates.min().date(), valid_dates.max().date())
            picked_range = st.sidebar.date_input(
                _date_filter_label(selected_date_column),
                value=st.session_state.get("credit_period_range", default_range),
                min_value=default_range[0],
                max_value=default_range[1],
                key="credit_period_range",
                disabled=not use_period_filter,
            )
            if use_period_filter:
                if isinstance(picked_range, tuple) and len(picked_range) == 2:
                    start_date, end_date = picked_range
                elif isinstance(picked_range, date):
                    start_date = picked_range
                    end_date = picked_range
            st.sidebar.caption(
                f"Période disponible : {default_range[0].isoformat()} -> {default_range[1].isoformat()}"
            )

    filtered_df = filter_dataframe(
        standardized_df,
        start_date=start_date,
        end_date=end_date,
        date_column=selected_date_column,
        column_filters=selected_column_filters,
    )
    cycle_filter_applied = False
    if "cycle_activite" in filtered_df.columns:
        selected_cycle_normalized_values = {
            normalize_text(selected_cycle["label"]),
            normalize_text(selected_cycle_key),
            normalize_text(str(selected_cycle["label"]).replace("Cycle ", "")),
        }
        cycle_mask = filtered_df["cycle_activite"].apply(
            lambda value: normalize_text(value) in selected_cycle_normalized_values if pd.notna(value) else False
        )
        if bool(cycle_mask.any()):
            filtered_df = filtered_df.loc[cycle_mask].reset_index(drop=True)
            cycle_filter_applied = True
    filtered_monthly_df = build_monthly_series(filtered_df)
    epargne_bundles: list[dict[str, object]] | None = None
    epargne_source_label: str | None = None

    if selected_cycle_key == "epargne":
        epargne_source_label = source_label
        if source_mode == "Téléverser un fichier":
            epargne_bundles = build_epargne_bundles_from_standardized_frames([(filename, standardized_df)])
        elif source_mode == "Téléverser plusieurs fichiers":
            uploaded_items = tuple((file.name, file.getvalue()) for file in uploaded_files)
            epargne_bundles = prepare_epargne_bundles_from_uploads(uploaded_items, sheet_name)
        elif source_mode == "Charger un fichier inclus" and selected_local_path is not None:
            epargne_bundles = prepare_epargne_bundles_from_paths((str(selected_local_path),), sheet_name)
        elif source_mode == "Compiler plusieurs fichiers inclus":
            compiled_paths = tuple(str(path) for path in selected_compilation_paths)
            epargne_bundles = prepare_epargne_bundles_from_paths(compiled_paths, sheet_name)

    recognized_columns = sum(
        1
        for source_column, standardized_column in payload["mapping_df"][["colonne_source", "colonne_standard"]].itertuples(index=False)
        if str(source_column).strip() != str(standardized_column).strip()
    )
    render_context_row(
        [
            ("Lignes brutes", f"{len(raw_df):,}".replace(",", " ")),
            ("Lignes retenues", f"{len(filtered_df):,}".replace(",", " ")),
            ("Colonnes source",str(raw_df.shape[1])),
            ("Colonnes reconnues", format_context_value(recognized_columns)),
            ("Colonnes standardisées", format_context_value(standardized_df.shape[1])),
            
        ]
    )
    st.caption(
        f"Fichier : {filename} | Lignes brutes : {len(raw_df):,} | Lignes retenues : {len(filtered_df):,}"
    )

    with st.sidebar.expander("Résumé des filtres", expanded=True):
        active_filter_count = _count_active_sidebar_filters(selected_column_filters)
        cycle_filter_columns = [
            column
            for column in get_cycle_analysis_preset(selected_cycle_key).get("filter_columns", [])
            if column in standardized_df.columns
        ]
        render_sidebar_stat_grid(
            [
                ("Lignes", f"{len(filtered_df):,}".replace(",", " ")),
                ("Filtres", str(active_filter_count)),
                ("Cycle", selected_cycle["label"]),
                ("Source", source_label),
            ],
            container=st,
        )
        st.write(f"Fichier : **{filename}**")
        st.write(f"Cycle : **{selected_cycle['label']}**")
        st.write(f"Lignes retenues : **{len(filtered_df):,}**".replace(",", " "))
        for column_name in cycle_filter_columns:
            selected_values = selected_column_filters.get(column_name)
            if selected_values is None:
                summary_value = "Toutes"
            else:
                summary_value = ", ".join(selected_values[:4])
                if len(selected_values) > 4:
                    summary_value += " ..."
            st.write(f"{_filter_column_label(column_name)} : **{summary_value}**")
        if start_date and end_date:
            st.write(f"Période : **{start_date.isoformat()} -> {end_date.isoformat()}**")
        else:
            st.write("Période : **toute la base**")

    with st.sidebar.expander("Couverture du cycle", expanded=False):
        render_sidebar_stat_grid(
            [
                ("Champs détectés", f"{cycle_coverage['detected_count']}/{cycle_coverage['total']}"),
                ("Couverture", f"{cycle_coverage['coverage_rate'] * 100:.0f}%"),
            ],
            container=st,
        )
        st.write(cycle_coverage["summary"])
        if cycle_coverage["missing_fields"]:
            st.caption(
                "Champs encore manquants : "
                + ", ".join(cycle_coverage["missing_fields"][:8])
                + (" ..." if len(cycle_coverage["missing_fields"]) > 8 else "")
            )

    with st.sidebar.expander("Périmètre actif", expanded=False):
        perimeter_items = []
        if "client_id" in standardized_df.columns:
            perimeter_items.append(("Clients", f"{standardized_df['client_id'].nunique():,}".replace(",", " ")))
        perimeter_items.append(("Colonnes", str(standardized_df.shape[1])))
        perimeter_items.append(("Lignes", f"{len(standardized_df):,}".replace(",", " ")))
        render_sidebar_stat_grid(perimeter_items[:4], container=st)
        st.write(
            f"Clients uniques : **{standardized_df['client_id'].nunique():,}**".replace(",", " ")
            if "client_id" in standardized_df.columns
            else "Clients uniques : **-**"
        )
        for column_name in cycle_filter_columns[:4]:
            detected_count = int(standardized_df[column_name].dropna().nunique()) if column_name in standardized_df.columns else 0
            st.write(f"{_filter_column_label(column_name)} détectés : **{detected_count:,}**".replace(",", " "))

    with st.sidebar.expander("Options d'affichage", expanded=False):
        render_sidebar_section("Affichage", "Réglez l'affichage des valeurs et la lisibilité des graphiques.", container=st)
        if selected_cycle_key == "epargne":
            st.number_input(
                "Taux CDF/USD (1 USD = x CDF)",
                min_value=1.0,
                max_value=100000.0,
                value=float(st.session_state.get("credit_epargne_fx_rate", 2300.0)),
                step=50.0,
                key="credit_epargne_fx_rate",
                help="Exemple : 2300 signifie que 1 USD = 2300,00 CDF. Ce taux sert à convertir les montants en CDF en équivalent USD dans le rapport épargne.",
            )
        st.checkbox(
            "Afficher annotations (valeurs)",
            value=True,
            key="credit_annot_vals",
            help="Affiche directement les valeurs sur les graphiques lorsque l'espace le permet.",
        )
        st.number_input(
            "Seuil d'affichage des annotations (valeur >)",
            min_value=0,
            max_value=1_000_000,
            value=1,
            step=1,
            key="credit_annot_min",
            disabled=not st.session_state.get("credit_annot_vals", False),
        )
        st.button(
            "Réinitialiser l'affichage",
            key="credit_reset_display_options",
            on_click=_reset_display_options,
            width="stretch",
        )

    render_panel_title("Synthèse standard")
    render_summary_box(
        f"Cycle actif : {selected_cycle['label']}",
        [
            selected_cycle["summary"],
            selected_cycle["control_objective"],
            cycle_coverage["summary"],
        ],
    )
    render_overview_tab(filtered_df, filtered_monthly_df, selected_cycle_key)

    render_panel_title("Analyses détaillées")
    tab_labels = [
        "Rappel de la vue d'ensemble",
        "Audit et contrôle",
    ]
    if selected_cycle_key == "crm_clients":
        tab_labels.append("Actions CRM")
    tab_labels.extend(
        [
            "Surveillance",
            "Portefeuille",
            "Risque",
            "Qualité",
            "Export",
            "Méthode",
        ]
    )
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        render_summary_box(
            "Vue d'ensemble déjà affichée",
            [
                "La synthèse principale est conservée plus haut dans la page.",
                "Les éléments de suivi détaillé sont regroupés dans les onglets.",
            ],
        )
    with tabs[1]:
        render_analyste_credit_tab(selected_cycle_key, standardized_df)
    tab_index = 2
    if selected_cycle_key == "crm_clients":
        with tabs[tab_index]:
            render_crm_clients_tab(filtered_df)
        tab_index += 1
    with tabs[tab_index]:
        render_surveillance_tab(filtered_df, selected_cycle_key)
    with tabs[tab_index + 1]:
        render_portfolio_tab(
            filtered_df,
            selected_cycle_key,
            conversion_rate=float(st.session_state.get("credit_epargne_fx_rate", 2300.0)),
            epargne_bundles=epargne_bundles,
            epargne_source_label=epargne_source_label,
        )
    with tabs[tab_index + 2]:
        render_risk_tab(filtered_df, selected_cycle_key)
    with tabs[tab_index + 3]:
        render_quality_tab(
            raw_df=raw_df,
            standardized_df=standardized_df,
            quality_df=payload["quality_df"],
            missing_df=payload["missing_df"],
            mapping_df=payload["mapping_df"],
            cycle_key=selected_cycle_key,
        )
    with tabs[tab_index + 4]:
        render_export_tab(filtered_df, payload["quality_df"], payload["mapping_df"])
    with tabs[tab_index + 5]:
        render_methodology_tab(selected_cycle_key, standardized_df)

    render_footer()


if __name__ == "__main__":
    main()
