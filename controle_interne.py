from __future__ import annotations

from datetime import date

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
from credit_app.cycles import (
    DEFAULT_CYCLE_KEY,
    build_cycle_coverage_summary,
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
    get_reference_column_count,
    normalize_text,
)
from credit_app.tabs.analyste_credit import render_analyste_credit_tab
from credit_app.tabs.export import render_export_tab
from credit_app.tabs.methodology import render_methodology_tab
from credit_app.tabs.overview import render_overview_tab
from credit_app.tabs.portfolio import render_portfolio_tab
from credit_app.tabs.quality import render_quality_tab
from credit_app.tabs.risk import render_risk_tab
from credit_app.tabs.surveillance import render_surveillance_tab
from credit_app.ui import (
    format_context_value,
    inject_professional_credit_css,
    render_context_row,
    render_footer,
    render_panel_title,
    render_professional_header,
    render_summary_box,
)

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
    for key in [
        "credit_status_sel",
        "credit_agency_sel",
        "credit_product_sel",
        "credit_filter_use_period",
        "credit_period_range",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def _reset_display_options() -> None:
    for key in [
        "credit_annot_vals",
        "credit_annot_min",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def main() -> None:
    configure_page()
    render_professional_header()

    available_files = list_available_line_list_files()
    cycle_options = list_cycle_keys()
    default_cycle_index = cycle_options.index(DEFAULT_CYCLE_KEY) if DEFAULT_CYCLE_KEY in cycle_options else 0
    st.sidebar.header("Référentiel de contrôle")
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

    st.sidebar.header("Source des données")
    source_mode = st.sidebar.selectbox(
        "Source de données",
        ["Téléverser un fichier", "Charger un fichier inclus"],
        index=1 if available_files else 0,
        key="credit_source_mode",
    )

    uploaded_file = None
    selected_local_path = None
    sheet_name = None
    filename = None

    if source_mode == "Téléverser un fichier":
        uploaded_file = st.sidebar.file_uploader(
            "Base crédit",
            type=["xlsx", "xls", "csv"],
            help="Formats acceptés : Excel ou CSV.",
        )
    else:
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

    with st.sidebar.expander("Référence et stockage", expanded=False):
        st.caption(
            f"Référence de renommage active : `data/Rename_columns.xlsx` ({get_reference_column_count()} alias)"
        )
        st.caption("Vous pouvez déposer vos fichiers de travail dans `line_list/` pour les relire ensuite sans téléversement.")

    if source_mode == "Téléverser un fichier" and uploaded_file is None:
        selected_local_path = None

    if source_mode == "Téléverser un fichier":
        source_ready = uploaded_file is not None
    else:
        source_ready = selected_local_path is not None

    if not source_ready:
        render_context_row(
            [
                ("Cycle", selected_cycle["label"]),
                ("Source", "Aucun fichier chargé"),
                ("Formats", "Excel ou CSV"),
                ("Analyses", "Portefeuille, risque, qualité"),
                ("Mode", "Téléversement ou fichier inclus"),
            ]
        )
        render_summary_box(
            "Base attendue",
            [
                selected_cycle["summary"],
                "Chargez un fichier Excel ou CSV ou utilisez un fichier déjà placé dans line_list/.",
                "L'application reconnaît automatiquement plusieurs variantes de colonnes métier.",
                "Le renommage externe de data/Rename_columns.xlsx est aussi pris en compte.",
            ],
        )
        st.markdown(
            """
### Colonnes utiles

- `client_id`, `code_client`, `id client`
- `dossier_id`, `numero_dossier`, `reference dossier`
- `montant_demande`, `montant_accorde`
- `revenu_mensuel`, `charge_mensuelle`
- `score_credit`, `retard_jours`
- `statut_dossier`, `statut_remboursement`
- `agence`, `agent_credit`, `type_produit`
- `date_demande`, `date_decision`
            """
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
    else:
        with st.spinner("Préparation de la base en cours..."):
            payload = prepare_dataset_from_path(str(selected_local_path), sheet_name)

    raw_df = payload["raw_df"]
    standardized_df = payload["standardized_df"]
    source_label = "Téléversement" if source_mode == "Téléverser un fichier" else "Fichier inclus"
    cycle_coverage = build_cycle_coverage_summary(standardized_df, selected_cycle_key)

    render_context_row(
        [
            ("Cycle", selected_cycle["label"]),
            ("Source", filename),
            ("Mode", source_label),
            ("Lignes brutes", f"{len(raw_df):,}".replace(",", " ")),
            ("Colonnes source", str(raw_df.shape[1])),
            ("Référence", "Rename_columns.xlsx"),
        ]
    )
    with st.expander("Source analytique et fichiers utilisés", expanded=False):
        st.write(f"Mode de chargement : **{source_label}**")
        st.write(f"Fichier actif : **{filename}**")
        if source_mode == "Charger un fichier inclus" and selected_local_path is not None:
            st.write(f"Chemin local : `{selected_local_path}`")
        if sheet_name:
            st.write(f"Feuille active : **{sheet_name}**")
        st.write(
            f"Référence de renommage : **data/Rename_columns.xlsx** avec **{get_reference_column_count()}** alias chargés."
        )
        st.write(f"Cycle actif : **{selected_cycle['label']}**")
        st.write(f"Couverture du référentiel : **{cycle_coverage['detected_count']}/{cycle_coverage['total']}** champs clés détectés.")

    st.sidebar.header("Filtres")
    st.sidebar.button("Réinitialiser les filtres", key="credit_reset_filters", on_click=_reset_sidebar_filters, width="stretch")

    status_options = sorted(
        value for value in standardized_df.get("statut_dossier", pd.Series(dtype="object")).dropna().unique()
    )
    status_widget_options = _normalize_multiselect_with_all("credit_status_sel", status_options)
    selected_status_values = st.sidebar.multiselect(
        f"Statut du dossier ({len(status_options)})",
        status_widget_options,
        key="credit_status_sel",
    )
    selected_status = _resolve_multiselect_selection(selected_status_values)

    agency_options = sorted(
        value for value in standardized_df.get("agence", pd.Series(dtype="object")).dropna().unique()
    )
    agency_widget_options = _normalize_multiselect_with_all("credit_agency_sel", agency_options)
    selected_agencies_values = st.sidebar.multiselect(
        f"Agence ({len(agency_options)})",
        agency_widget_options,
        key="credit_agency_sel",
    )
    selected_agencies = _resolve_multiselect_selection(selected_agencies_values)

    product_options = sorted(
        value for value in standardized_df.get("type_produit", pd.Series(dtype="object")).dropna().unique()
    )
    product_widget_options = _normalize_multiselect_with_all("credit_product_sel", product_options)
    selected_products_values = st.sidebar.multiselect(
        f"Produit ({len(product_options)})",
        product_widget_options,
        key="credit_product_sel",
    )
    selected_products = _resolve_multiselect_selection(selected_products_values)

    st.sidebar.header("Période")
    start_date = None
    end_date = None
    use_period_filter = st.sidebar.checkbox(
        "Filtrer sur la période de demande",
        value=True,
        key="credit_filter_use_period",
    )
    if "date_demande" in standardized_df.columns:
        valid_dates = standardized_df["date_demande"].dropna()
        if not valid_dates.empty:
            default_range = (valid_dates.min().date(), valid_dates.max().date())
            picked_range = st.sidebar.date_input(
                "Période de demande",
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
                f"Couverture disponible : {default_range[0].isoformat()} -> {default_range[1].isoformat()}"
            )

    filtered_df = filter_dataframe(
        standardized_df,
        statuses=selected_status,
        agencies=selected_agencies,
        products=selected_products,
        start_date=start_date,
        end_date=end_date,
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

    recognized_columns = sum(
        1
        for source_column, standardized_column in payload["mapping_df"][["colonne_source", "colonne_standard"]].itertuples(index=False)
        if str(source_column).strip() != str(standardized_column).strip()
    )
    render_context_row(
        [
            ("Source", filename),
            ("Lignes brutes", f"{len(raw_df):,}".replace(",", " ")),
            ("Lignes analysées", f"{len(filtered_df):,}".replace(",", " ")),
            ("Colonnes standardisées", format_context_value(standardized_df.shape[1])),
            ("Colonnes reconnues", format_context_value(recognized_columns)),
        ]
    )
    st.caption(
        f"Fichier source : {filename} | Lignes brutes : {len(raw_df):,} | Lignes analysées : {len(filtered_df):,}"
    )

    with st.sidebar.expander("Résumé des filtres actifs", expanded=True):
        st.write(f"Fichier : **{filename}**")
        st.write(f"Cycle : **{selected_cycle['label']}**")
        st.write(f"Lignes analysées : **{len(filtered_df):,}**".replace(",", " "))
        st.write(
            "Statut : **"
            + ("Toutes" if selected_status is None else ", ".join(selected_status[:4]))
            + "**"
        )
        st.write(
            "Agence : **"
            + ("Toutes" if selected_agencies is None else ", ".join(selected_agencies[:4]))
            + "**"
        )
        st.write(
            "Produit : **"
            + ("Toutes" if selected_products is None else ", ".join(selected_products[:4]))
            + "**"
        )
        if start_date and end_date:
            st.write(f"Période : **{start_date.isoformat()} -> {end_date.isoformat()}**")
        else:
            st.write("Période : **toute la base**")

    with st.sidebar.expander("Couverture du cycle", expanded=False):
        st.write(cycle_coverage["summary"])
        if cycle_coverage["missing_fields"]:
            st.caption(
                "Champs encore absents : "
                + ", ".join(cycle_coverage["missing_fields"][:8])
                + (" ..." if len(cycle_coverage["missing_fields"]) > 8 else "")
            )

    with st.sidebar.expander("Périmètre actif", expanded=False):
        st.write(f"Clients uniques : **{standardized_df['client_id'].nunique():,}**".replace(",", " ") if "client_id" in standardized_df.columns else "Clients uniques : **-**")
        st.write(f"Agences détectées : **{len(agency_options)}**")
        st.write(f"Produits détectés : **{len(product_options)}**")
        st.write(f"Statuts détectés : **{len(status_options)}**")

    with st.sidebar.expander("Options d'affichage", expanded=False):
        st.checkbox(
            "Afficher annotations (valeurs)",
            value=True,
            key="credit_annot_vals",
            help="Affiche les valeurs directement sur les graphiques lorsque l'espace visuel le permet.",
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
            "Réinitialiser les options d'affichage",
            key="credit_reset_display_options",
            on_click=_reset_display_options,
            width="stretch",
        )

    render_panel_title("Synthèse standard")
    render_summary_box(
        f"Référentiel actif : {selected_cycle['label']}",
        [
            selected_cycle["summary"],
            selected_cycle["control_objective"],
            cycle_coverage["summary"],
            "Le filtre cycle est appliqué directement sur les données standardisées." if cycle_filter_applied else "Le cycle pilote actuellement la lecture métier et s'appliquera aussi au filtrage dès qu'une colonne `cycle_activite` sera disponible.",
        ],
    )
    render_overview_tab(filtered_df, filtered_monthly_df)

    render_panel_title("Analyses détaillées par onglet")
    tabs = st.tabs(
        [
            "Vue d'ensemble active",
            "Notions importantes",
            "Surveillance",
            "Portefeuille",
            "Risque",
            "Qualité",
            "Export",
            "Méthodologie",
        ]
    )

    with tabs[0]:
        render_summary_box(
            "Vue d'ensemble déjà affichée",
            [
                "La synthèse principale est conservée plus haut dans la page.",
                "Cet onglet confirme que les KPI et graphiques standard restent visibles pendant la navigation.",
                "Les blocs de suivi opérationnel sont regroupés dans l'onglet Surveillance.",
            ],
        )
    with tabs[1]:
        render_analyste_credit_tab(selected_cycle_key, standardized_df)
    with tabs[2]:
        render_surveillance_tab(filtered_df)
    with tabs[3]:
        render_portfolio_tab(filtered_df)
    with tabs[4]:
        render_risk_tab(filtered_df)
    with tabs[5]:
        render_quality_tab(
            raw_df=raw_df,
            standardized_df=standardized_df,
            quality_df=payload["quality_df"],
            missing_df=payload["missing_df"],
            mapping_df=payload["mapping_df"],
        )
    with tabs[6]:
        render_export_tab(filtered_df, payload["quality_df"], payload["mapping_df"])
    with tabs[7]:
        render_methodology_tab(selected_cycle_key, standardized_df)

    render_footer()


if __name__ == "__main__":
    main()
