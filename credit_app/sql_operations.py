from __future__ import annotations

from pathlib import Path

import pandas as pd


SQL_BUNDLE_ROLE_ALIASES = {
    "dbo_operations": "operations",
    "dbo_operations_api": "operations_api",
    "dbo_hdpm": "hdpm",
    "dbo_hdpm_api": "hdpm_api",
    "dbo_adherants": "adherents",
    "dbo_adherents": "adherents",
}

SQL_BUNDLE_REQUIRED_ROLES = {"operations", "hdpm", "adherents"}
SQL_BUNDLE_OPTIONAL_ROLES = {"operations_api", "hdpm_api"}
DEVIS_CODE_MAP = {1: "USD", 2: "CDF"}


def infer_sql_bundle_role(filename: str) -> str | None:
    stem = Path(filename).stem.lower()
    for alias, role in sorted(SQL_BUNDLE_ROLE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in stem:
            return role
    return None


def has_minimum_sql_bundle(file_names: list[str] | tuple[str, ...]) -> bool:
    roles = {infer_sql_bundle_role(name) for name in file_names}
    return SQL_BUNDLE_REQUIRED_ROLES.issubset({role for role in roles if role})


def missing_sql_bundle_roles(file_names: list[str] | tuple[str, ...]) -> list[str]:
    roles = {infer_sql_bundle_role(name) for name in file_names}
    detected = {role for role in roles if role}
    return sorted(SQL_BUNDLE_REQUIRED_ROLES - detected)


def _coerce_number(series: pd.Series) -> pd.Series:
    if series.dtype == object:
        series = (
            series.astype("string")
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
    return pd.to_numeric(series, errors="coerce")


def _coerce_bool(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.lower()
    return normalized.isin({"1", "true", "vrai", "oui"})


def _coerce_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _first_notna(values: pd.Series) -> object:
    non_null = values.dropna()
    return non_null.iloc[0] if not non_null.empty else pd.NA


def _ensure_client_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "operation_id" not in work.columns:
        if "id_operation" in work.columns:
            work["operation_id"] = work["id_operation"]
        elif "numero_reference" in work.columns:
            work["operation_id"] = work["numero_reference"]
        elif "NUM_TRANSACTION" in work.columns:
            work["operation_id"] = work["NUM_TRANSACTION"]
        elif "compte_id" in work.columns:
            work["operation_id"] = work["compte_id"]
        else:
            work["operation_id"] = pd.Series(
                [f"ligne_{index}" for index in work.index],
                index=work.index,
                dtype="object",
            )
    if "source_mouvement" not in work.columns:
        work["source_mouvement"] = pd.Series("NON_RENSEIGNE", index=work.index, dtype="object")
    if "type_operation" not in work.columns:
        if "ID_TYPE_OPERATION" in work.columns:
            work["type_operation"] = work["ID_TYPE_OPERATION"].astype("string")
        elif "type_mouvement" in work.columns:
            reverse_map = {
                "Depot": "DEPO",
                "Retrait": "RETR",
                "Depot mobile": "MOB_DEPO",
                "Retrait mobile": "MOB_RETR",
            }
            work["type_operation"] = work["type_mouvement"].map(reverse_map).fillna(
                work["type_mouvement"].astype("string")
            )
        else:
            work["type_operation"] = pd.Series(pd.NA, index=work.index, dtype="object")
    if "type_mouvement" not in work.columns:
        forward_map = {
            "DEPO": "Depot",
            "RETR": "Retrait",
            "MOB_DEPO": "Depot mobile",
            "MOB_RETR": "Retrait mobile",
        }
        work["type_mouvement"] = work["type_operation"].map(forward_map).fillna(
            work["type_operation"].astype("string")
        )
    if "date_operation" not in work.columns:
        if "DATE_OPERATION" in work.columns:
            work["date_operation"] = work["DATE_OPERATION"]
        elif "date_saisie" in work.columns:
            work["date_operation"] = work["date_saisie"]
        elif "date_validation" in work.columns:
            work["date_operation"] = work["date_validation"]
        else:
            work["date_operation"] = pd.Series(pd.NaT, index=work.index)
    if "montant_operation" not in work.columns:
        if "MONTANT_OPERATION" in work.columns:
            work["montant_operation"] = work["MONTANT_OPERATION"]
        elif "montant_reporting_cdf" in work.columns:
            work["montant_operation"] = work["montant_reporting_cdf"]
        else:
            work["montant_operation"] = pd.Series(0.0, index=work.index)
    if "code_devise" not in work.columns:
        if "ID_DEVISE" in work.columns:
            work["code_devise"] = work["ID_DEVISE"].map(DEVIS_CODE_MAP).fillna(
                work["ID_DEVISE"].astype("string")
            )
        else:
            work["code_devise"] = pd.Series("", index=work.index, dtype="object")
    if "agence" not in work.columns:
        if "ID_POINT_SERVICE" in work.columns:
            work["agence"] = work["ID_POINT_SERVICE"]
        elif "agence_client" in work.columns:
            work["agence"] = work["agence_client"]
        else:
            work["agence"] = pd.Series(pd.NA, index=work.index, dtype="object")
    if "annule" not in work.columns:
        work["annule"] = pd.Series(False, index=work.index)
    if "compte_id" not in work.columns:
        if "ID_COMPTE" in work.columns:
            work["compte_id"] = work["ID_COMPTE"]
        else:
            work["compte_id"] = pd.Series(pd.NA, index=work.index, dtype="object")
    work["montant_operation"] = _coerce_number(work["montant_operation"]).fillna(0.0)
    work["date_operation"] = _coerce_date(work["date_operation"])
    work["type_operation"] = work["type_operation"].astype("string")
    work["type_mouvement"] = work["type_mouvement"].astype("string")
    work["source_mouvement"] = work["source_mouvement"].astype("string")
    work["code_devise"] = work["code_devise"].astype("string")
    work["agence"] = work["agence"].astype("string")
    work["nb_ecritures"] = pd.to_numeric(
        work.get("nb_ecritures", pd.Series(1, index=work.index)),
        errors="coerce",
    ).fillna(1)
    if "total_debit" not in work.columns:
        sens_series = work.get("SENS", pd.Series(index=work.index, dtype="object")).astype("string").str.upper()
        work["total_debit"] = work["montant_operation"].where(sens_series.eq("D"), 0.0)
    else:
        work["total_debit"] = _coerce_number(work["total_debit"]).fillna(0.0)
    if "total_credit" not in work.columns:
        sens_series = work.get("SENS", pd.Series(index=work.index, dtype="object")).astype("string").str.upper()
        work["total_credit"] = work["montant_operation"].where(sens_series.eq("C"), 0.0)
    else:
        work["total_credit"] = _coerce_number(work["total_credit"]).fillna(0.0)
    if "client_id" not in work.columns:
        if "compte_id" in work.columns:
            work["client_id"] = work["compte_id"]
        elif "operation_id" in work.columns:
            work["client_id"] = work["operation_id"]
        else:
            work["client_id"] = pd.Series(pd.NA, index=work.index, dtype="object")
    if "nom_client" not in work.columns:
        work["nom_client"] = pd.Series(pd.NA, index=work.index, dtype="object")
    work["nom_client"] = work["nom_client"].fillna("Client non rattaché")
    for column_name, default_value in {
        "type_client": pd.NA,
        "agence_client": pd.NA,
        "agent_credit": pd.NA,
        "est_valide": False,
        "droit_paye": False,
        "kyc_missing_count": 0,
    }.items():
        if column_name not in work.columns:
            work[column_name] = default_value
    return work


def normalize_operations_analysis_frame(df: pd.DataFrame) -> pd.DataFrame:
    return _ensure_client_analysis_columns(df)


def _normalize_named_frames(named_frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    normalized: dict[str, pd.DataFrame] = {}
    for filename, frame in named_frames.items():
        role = infer_sql_bundle_role(filename)
        if role:
            normalized[role] = frame.copy()
    return normalized


def _prepare_hdpm_summary(
    df: pd.DataFrame,
    operation_key: str,
    known_account_ids: set[str] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[operation_key])

    work = df.copy()
    known_accounts = {str(value) for value in (known_account_ids or set()) if pd.notna(value)}
    work["MONTANT_OPERATION"] = _coerce_number(work.get("MONTANT_OPERATION", pd.Series(index=work.index)))
    work["DATE_OPERATION"] = _coerce_date(work.get("DATE_OPERATION", pd.Series(index=work.index)))
    work["DATE_VALEUR"] = _coerce_date(work.get("DATE_VALEUR", pd.Series(index=work.index)))
    work["SENS"] = work.get("SENS", pd.Series(index=work.index, dtype="object")).astype("string").str.strip().str.upper()
    work["ID_COMPTE_STR"] = work.get("ID_COMPTE", pd.Series(index=work.index, dtype="object")).astype("string")
    work["compte_adherent_candidat"] = work["ID_COMPTE_STR"].where(work["ID_COMPTE_STR"].isin(known_accounts))
    work["MONTANT_ABS"] = work["MONTANT_OPERATION"].abs()
    work["DEBIT"] = work["MONTANT_ABS"].where(work["SENS"].eq("D"), 0.0)
    work["CREDIT"] = work["MONTANT_ABS"].where(work["SENS"].eq("C"), 0.0)
    work["date_valeur_diff"] = (
        work["DATE_VALEUR"].notna()
        & work["DATE_OPERATION"].notna()
        & work["DATE_VALEUR"].dt.date.ne(work["DATE_OPERATION"].dt.date)
    )
    work["sens_missing"] = work["SENS"].fillna("").eq("")
    work["ligne_non_positive"] = work["MONTANT_OPERATION"].fillna(0).le(0)

    summary = (
        work.groupby(operation_key, dropna=False)
        .agg(
            nb_ecritures=("ID", "size"),
            montant_operation=("MONTANT_ABS", "max"),
            total_debit=("DEBIT", "sum"),
            total_credit=("CREDIT", "sum"),
            compte_id_adherent=("compte_adherent_candidat", _first_notna),
            compte_id_fallback=("ID_COMPTE_STR", _first_notna),
            id_devise=("ID_DEVISE", _first_notna),
            agence_comptable=("ID_POINT_SERVICE", _first_notna),
            type_operation_comptable=("ID_TYPE_OPERATION", _first_notna),
            ecarts_date_valeur=("date_valeur_diff", "sum"),
            lignes_sens_absent=("sens_missing", "sum"),
            lignes_montant_non_positif=("ligne_non_positive", "sum"),
        )
        .reset_index()
    )
    summary["compte_id"] = summary["compte_id_adherent"].fillna(summary["compte_id_fallback"])
    summary = summary.drop(columns=["compte_id_adherent", "compte_id_fallback"])
    summary["ecart_debit_credit"] = (summary["total_debit"] - summary["total_credit"]).abs()
    summary["equilibre_comptable_ok"] = summary["ecart_debit_credit"].fillna(0).le(0.01)
    summary["code_devise"] = summary["id_devise"].map(DEVIS_CODE_MAP).fillna(summary["id_devise"].astype("string"))
    return summary


def _prepare_adherents(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ID_COMPTE_ADHERENT"])

    work = df.copy()
    rename_map = {
        "CODE": "client_id",
        "NOM_ADHERENT": "nom_client",
        "ID_COMPTE_ADHERENT": "compte_adherent_join",
        "ID_TYPE_ADHERENT": "type_client",
        "ID_GESTIONNAIRE": "agent_credit",
        "ID_POINT_SERVICE": "agence_client",
        "DROIT_PAYE": "droit_paye",
        "EST_VALIDE": "est_valide",
        "ID": "adherent_pk",
        "ID_CATEGORIE_ADHERENT": "categorie_adherent",
    }
    work = work.rename(columns={col: rename for col, rename in rename_map.items() if col in work.columns})
    for col in ["DATE_INSCRIPTION", "DATE_LAST_MODIFIED"]:
        if col in work.columns:
            work[col] = _coerce_date(work[col])
    for col in ["droit_paye", "est_valide", "EST_TONTINE", "EST_PERFECT"]:
        if col in work.columns:
            work[col] = _coerce_bool(work[col])
    if "compte_adherent_join" not in work.columns:
        work["compte_adherent_join"] = pd.NA
    work["kyc_missing_count"] = 0
    for field_name in ["client_id", "nom_client", "type_client", "agence_client", "agent_credit"]:
        if field_name in work.columns:
            work["kyc_missing_count"] = work["kyc_missing_count"] + (
                work[field_name].isna() | work[field_name].astype("string").str.strip().fillna("").eq("")
            ).astype(int)
    if "est_valide" in work.columns:
        work["kyc_missing_count"] = work["kyc_missing_count"] + (~work["est_valide"].fillna(False)).astype(int)
    if "droit_paye" in work.columns:
        work["kyc_missing_count"] = work["kyc_missing_count"] + (~work["droit_paye"].fillna(False)).astype(int)
    keep_columns = [
        "compte_adherent_join",
        "client_id",
        "nom_client",
        "type_client",
        "agent_credit",
        "agence_client",
        "droit_paye",
        "est_valide",
        "categorie_adherent",
        "kyc_missing_count",
        "adherent_pk",
    ]
    return work[[column for column in keep_columns if column in work.columns]].drop_duplicates("compte_adherent_join")


def _prepare_operations_table(
    operations_df: pd.DataFrame,
    hdpm_summary_df: pd.DataFrame,
    adherents_df: pd.DataFrame,
    *,
    source_label: str,
    operation_key: str,
    api_mode: bool,
) -> pd.DataFrame:
    if operations_df.empty:
        return pd.DataFrame()

    work = operations_df.copy()
    if api_mode:
        join_key = "CODE"
    else:
        join_key = "ID"
    work[join_key] = work[join_key].astype("string")
    if "ID_TYPE_OPERATION" in work.columns:
        allowed_types = ["MOB_DEPO", "MOB_RETR"] if api_mode else ["DEPO", "RETR"]
        work = work.loc[work["ID_TYPE_OPERATION"].astype("string").isin(allowed_types)].copy()
    if work.empty:
        return pd.DataFrame()
    for col in ["DATE_OPERATION", "DATE_SAISIE", "DATE_VALIDATION", "DATE_VALIDE"]:
        if col in work.columns:
            work[col] = _coerce_date(work[col])
    if "ANNULE" in work.columns:
        work["ANNULE"] = _coerce_bool(work["ANNULE"])
    else:
        work["ANNULE"] = False

    merged = work.merge(hdpm_summary_df, left_on=join_key, right_on=operation_key, how="left")
    if not adherents_df.empty:
        merged = merged.merge(adherents_df, left_on="compte_id", right_on="compte_adherent_join", how="left")

    type_map = {
        "DEPO": "Depot",
        "RETR": "Retrait",
        "MOB_DEPO": "Depot mobile",
        "MOB_RETR": "Retrait mobile",
    }
    merged["source_mouvement"] = source_label
    merged["type_operation"] = merged.get("ID_TYPE_OPERATION", pd.Series(index=merged.index, dtype="object")).astype("string")
    merged["type_mouvement"] = merged["type_operation"].map(type_map).fillna(merged["type_operation"])
    merged["date_operation"] = merged.get("DATE_OPERATION")
    merged["date_saisie"] = merged.get("DATE_SAISIE")
    merged["date_validation"] = merged.get("DATE_VALIDATION")
    merged["date_valide"] = merged.get("DATE_VALIDE")
    merged["agence"] = merged.get("ID_POINT_SERVICE").fillna(merged.get("agence_comptable"))
    merged["numero_reference"] = merged.get("NUM_TRANSACTION")
    merged["numero_recu"] = merged.get("NUMERO_RECU")
    merged["operateur"] = merged.get("ID_UTILISATEUR").astype("string") if "ID_UTILISATEUR" in merged.columns else pd.Series(pd.NA, index=merged.index, dtype="string")
    merged["validateur"] = merged.get("ID_UTILISATEUR_VALIDE").astype("string") if "ID_UTILISATEUR_VALIDE" in merged.columns else pd.Series(pd.NA, index=merged.index, dtype="string")
    merged["montant_operation"] = _coerce_number(merged.get("montant_operation", pd.Series(index=merged.index)))
    merged["delai_saisie_jours"] = (
        (pd.to_datetime(merged["date_saisie"], errors="coerce").dt.normalize() - pd.to_datetime(merged["date_operation"], errors="coerce").dt.normalize()).dt.days
    )
    merged["saisie_tardive"] = merged["delai_saisie_jours"].fillna(0).gt(0)
    merged["validation_incoherente"] = (
        (
            pd.to_datetime(merged["date_valide"], errors="coerce").notna()
            & pd.to_datetime(merged["date_saisie"], errors="coerce").notna()
            & pd.to_datetime(merged["date_valide"], errors="coerce").lt(pd.to_datetime(merged["date_saisie"], errors="coerce"))
        )
        | (
            pd.to_datetime(merged["date_validation"], errors="coerce").notna()
            & pd.to_datetime(merged["date_operation"], errors="coerce").notna()
            & pd.to_datetime(merged["date_validation"], errors="coerce").lt(pd.to_datetime(merged["date_operation"], errors="coerce"))
        )
    )
    merged["operation_non_validee"] = (~merged["ANNULE"].fillna(False)) & (
        pd.to_datetime(merged["date_validation"], errors="coerce").isna()
        | pd.to_datetime(merged["date_valide"], errors="coerce").isna()
    )
    merged["auto_validation"] = (
        merged["operateur"].fillna("").ne("")
        & merged["validateur"].fillna("").ne("")
        & merged["operateur"].eq(merged["validateur"])
    )
    merged["annule"] = merged["ANNULE"].fillna(False)
    merged["cycle_activite"] = "operations_depot_retrait"
    merged["balance_nette"] = merged.get("total_credit", 0).fillna(0) - merged.get("total_debit", 0).fillna(0)
    merged["montant_reporting_cdf"] = merged["montant_operation"]
    merged["droit_paye"] = merged.get("droit_paye", pd.Series(False, index=merged.index))
    merged["est_valide"] = merged.get("est_valide", pd.Series(False, index=merged.index))

    selected_columns = [
        join_key,
        "source_mouvement",
        "date_operation",
        "date_saisie",
        "date_validation",
        "date_valide",
        "type_operation",
        "type_mouvement",
        "agence",
        "numero_reference",
        "numero_recu",
        "operateur",
        "validateur",
        "montant_operation",
        "code_devise",
        "id_devise",
        "compte_id",
        "client_id",
        "nom_client",
        "type_client",
        "agent_credit",
        "agence_client",
        "droit_paye",
        "est_valide",
        "kyc_missing_count",
        "annule",
        "operation_non_validee",
        "saisie_tardive",
        "delai_saisie_jours",
        "validation_incoherente",
        "auto_validation",
        "nb_ecritures",
        "total_debit",
        "total_credit",
        "equilibre_comptable_ok",
        "ecart_debit_credit",
        "ecarts_date_valeur",
        "lignes_sens_absent",
        "lignes_montant_non_positif",
        "DESCRIPTION",
        "MODE_PAIEMENT",
        "ID_OPERATION_ANNULE",
        "ID_OPERATION_MERE",
        "cycle_activite",
    ]
    dataset = merged[[column for column in selected_columns if column in merged.columns]].copy()
    dataset = dataset.rename(
        columns={
            join_key: "operation_id",
            "DESCRIPTION": "commentaire",
            "MODE_PAIEMENT": "mode_paiement",
            "ID_OPERATION_ANNULE": "id_operation_annulee",
            "ID_OPERATION_MERE": "id_operation_mere",
        }
    )
    return dataset


def build_operations_depot_retrait_dataset(named_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = _normalize_named_frames(named_frames)
    missing_roles = sorted(SQL_BUNDLE_REQUIRED_ROLES - set(frames))
    if missing_roles:
        raise ValueError(
            "Bundle SQL incomplet. Fichiers requis manquants : " + ", ".join(missing_roles)
        )

    operations = frames.get("operations", pd.DataFrame())
    operations_api = frames.get("operations_api", pd.DataFrame())
    hdpm = frames.get("hdpm", pd.DataFrame())
    hdpm_api = frames.get("hdpm_api", pd.DataFrame())
    adherents = _prepare_adherents(frames.get("adherents", pd.DataFrame()))

    known_account_ids = set(adherents.get("compte_adherent_join", pd.Series(dtype="object")).dropna().astype(str))
    hdpm_summary = _prepare_hdpm_summary(hdpm, "ID_OPERATION", known_account_ids)
    hdpm_api_summary = _prepare_hdpm_summary(hdpm_api, "ID_OPERATION", known_account_ids)

    parts = [
        _prepare_operations_table(
            operations,
            hdpm_summary,
            adherents,
            source_label="BACK_OFFICE",
            operation_key="ID_OPERATION",
            api_mode=False,
        )
    ]
    if not operations_api.empty and not hdpm_api.empty:
        parts.append(
            _prepare_operations_table(
                operations_api,
                hdpm_api_summary,
                adherents,
                source_label="API_MOBILE",
                operation_key="ID_OPERATION",
                api_mode=True,
            )
        )

    parts = [part for part in parts if part is not None and not part.empty]
    if not parts:
        return pd.DataFrame()
    dataset = pd.concat(parts, ignore_index=True)
    if "operation_id" in dataset.columns:
        dataset["operation_id"] = dataset["operation_id"].astype("string")
    return dataset


def apply_reporting_conversion(df: pd.DataFrame, conversion_rate: float) -> pd.DataFrame:
    work = df.copy()
    code_devise = work.get("code_devise", pd.Series(index=work.index, dtype="object")).astype("string").str.upper()
    montant = _coerce_number(work.get("montant_operation", pd.Series(index=work.index))).fillna(0.0)
    work["montant_reporting_cdf"] = montant.where(code_devise.eq("CDF"), montant * float(conversion_rate))
    return work


def build_lbcft_reporting_table(df: pd.DataFrame, conversion_rate: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["section", "ligne_excel", "rubrique", "nombre", "volume_cdf", "commentaire"])

    work = apply_reporting_conversion(df.loc[~df.get("annule", pd.Series(False, index=df.index)).fillna(False)].copy(), conversion_rate)
    work = _ensure_client_analysis_columns(work)
    threshold_5k = float(conversion_rate) * 5000.0
    threshold_10k = float(conversion_rate) * 10000.0

    def summarize(mask: pd.Series, section: str, line_no: int, rubrique: str, comment: str) -> dict[str, object]:
        subset = work.loc[mask].copy()
        return {
            "section": section,
            "ligne_excel": line_no,
            "rubrique": rubrique,
            "nombre": int(len(subset)),
            "volume_cdf": float(subset["montant_reporting_cdf"].sum()) if not subset.empty else 0.0,
            "commentaire": comment,
        }

    rows = [
        summarize(
            work["type_mouvement"].isin(["Depot", "Depot mobile"]),
            "1. ACTIVITE",
            25,
            "Total Depots",
            "Alimente la ligne Total Dépôts du reporting.",
        ),
        summarize(
            work["type_mouvement"].isin(["Retrait", "Retrait mobile"]),
            "1. ACTIVITE",
            26,
            "Total Retraits",
            "Lecture complémentaire utile pour le suivi des sorties.",
        ),
        summarize(
            work["type_mouvement"].isin(["Depot", "Depot mobile"]) & work["montant_reporting_cdf"].ge(threshold_10k),
            "3. PRODUIT - SERVICE - OPERATIONS",
            53,
            "Depot >= 10k USD",
            "Seuil converti en CDF selon le taux retenu dans la barre latérale.",
        ),
        summarize(
            work["type_mouvement"].isin(["Retrait", "Retrait mobile"]) & work["montant_reporting_cdf"].ge(threshold_10k),
            "3. PRODUIT - SERVICE - OPERATIONS",
            54,
            "Retrait >= 10k USD",
            "Seuil converti en CDF selon le taux retenu dans la barre latérale.",
        ),
        summarize(
            work["type_mouvement"].isin(["Depot", "Depot mobile"])
            & work["montant_reporting_cdf"].ge(threshold_5k)
            & work["montant_reporting_cdf"].lt(threshold_10k),
            "3. PRODUIT - SERVICE - OPERATIONS",
            55,
            "Depot >= 5k USD et < 10k USD",
            "Aide à suivre les opérations proches du seuil élevé.",
        ),
        summarize(
            work["type_mouvement"].isin(["Retrait", "Retrait mobile"])
            & work["montant_reporting_cdf"].ge(threshold_5k)
            & work["montant_reporting_cdf"].lt(threshold_10k),
            "3. PRODUIT - SERVICE - OPERATIONS",
            56,
            "Retrait >= 5k USD et < 10k USD",
            "Aide à suivre les retraits proches du seuil élevé.",
        ),
        summarize(
            work["source_mouvement"].eq("API_MOBILE"),
            "4. CANAUX DE DISTRIBUTION",
            132,
            "Operations effectuees par Mobile Banking",
            "Regroupe les dépôts et retraits mobiles.",
        ),
        summarize(
            work["type_operation"].eq("MOB_DEPO"),
            "4. CANAUX DE DISTRIBUTION",
            134,
            "Wallet to Bank",
            "Approximation basée sur les dépôts mobiles.",
        ),
    ]
    return pd.DataFrame(rows).sort_values("ligne_excel").reset_index(drop=True)


def build_fractionnement_table(df: pd.DataFrame, conversion_rate: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = apply_reporting_conversion(df.loc[~df.get("annule", pd.Series(False, index=df.index)).fillna(False)].copy(), conversion_rate)
    work = _ensure_client_analysis_columns(work)
    threshold_10k = float(conversion_rate) * 10000.0
    grouped = (
        work.groupby(["date_operation", "client_id", "nom_client", "type_mouvement", "code_devise"], dropna=False)
        .agg(
            nb_operations=("operation_id", "nunique"),
            montant_cumule_cdf=("montant_reporting_cdf", "sum"),
            montant_max_unitaire_cdf=("montant_reporting_cdf", "max"),
        )
        .reset_index()
    )
    result = grouped[
        grouped["nb_operations"].ge(2)
        & grouped["montant_max_unitaire_cdf"].lt(threshold_10k)
        & grouped["montant_cumule_cdf"].ge(threshold_10k)
    ].copy()
    if result.empty:
        return result
    result["lecture"] = "Plusieurs mouvements unitaires sous le seuil élevé mais cumul journalier supérieur au seuil 10k USD."
    return result.sort_values("montant_cumule_cdf", ascending=False)


def build_unusual_operations_table(df: pd.DataFrame, conversion_rate: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = apply_reporting_conversion(df.loc[~df.get("annule", pd.Series(False, index=df.index)).fillna(False)].copy(), conversion_rate)
    work = _ensure_client_analysis_columns(work)
    threshold_10k = float(conversion_rate) * 10000.0
    current_start = pd.to_datetime(work["date_operation"], errors="coerce").max()
    if pd.isna(current_start):
        return pd.DataFrame()
    current_start = pd.Timestamp(current_start).normalize() - pd.Timedelta(days=89)
    current_period = work.loc[pd.to_datetime(work["date_operation"], errors="coerce").ge(current_start)].copy()
    historical = work.loc[pd.to_datetime(work["date_operation"], errors="coerce").lt(current_start)].copy()
    current_agg = (
        current_period.groupby(["client_id", "nom_client"], dropna=False)
        .agg(nb_operations_periode=("operation_id", "nunique"), volume_periode_cdf=("montant_reporting_cdf", "sum"))
        .reset_index()
    )
    historical_daily = (
        historical.groupby(["client_id", "date_operation"], dropna=False)["montant_reporting_cdf"]
        .sum()
        .reset_index(name="volume_jour_cdf")
    )
    historical_avg = (
        historical_daily.groupby("client_id", dropna=False)["volume_jour_cdf"]
        .mean()
        .reset_index(name="moyenne_journaliere_historique_cdf")
    )
    result = current_agg.merge(historical_avg, on="client_id", how="left")
    result["multiple_vs_moyenne_historique"] = result["volume_periode_cdf"] / result["moyenne_journaliere_historique_cdf"]
    result = result[
        result["volume_periode_cdf"].ge(threshold_10k)
        & (
            result["moyenne_journaliere_historique_cdf"].isna()
            | result["volume_periode_cdf"].ge(3 * result["moyenne_journaliere_historique_cdf"].fillna(0))
        )
    ].copy()
    return result.sort_values("volume_periode_cdf", ascending=False)


def build_high_activity_kyc_table(df: pd.DataFrame, conversion_rate: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = apply_reporting_conversion(df.loc[~df.get("annule", pd.Series(False, index=df.index)).fillna(False)].copy(), conversion_rate)
    work = _ensure_client_analysis_columns(work)
    threshold_10k = float(conversion_rate) * 10000.0
    grouped = (
        work.groupby(["client_id", "nom_client"], dropna=False)
        .agg(
            nb_operations=("operation_id", "nunique"),
            volume_lignes_cdf=("montant_reporting_cdf", "sum"),
            type_client=("type_client", _first_notna),
            agence_client=("agence_client", _first_notna),
            agent_credit=("agent_credit", _first_notna),
            est_valide=("est_valide", "max"),
            droit_paye=("droit_paye", "max"),
            kyc_missing_count=("kyc_missing_count", "max"),
        )
        .reset_index()
    )
    result = grouped[
        grouped["volume_lignes_cdf"].ge(threshold_10k)
        & (
            grouped["client_id"].isna()
            | grouped["nom_client"].astype("string").str.strip().fillna("").eq("")
            | grouped["type_client"].isna()
            | grouped["agence_client"].isna()
            | grouped["agent_credit"].isna()
            | grouped["est_valide"].fillna(False).eq(False)
            | grouped["droit_paye"].fillna(False).eq(False)
            | grouped["kyc_missing_count"].fillna(0).gt(0)
        )
    ].copy()
    result["lecture"] = "Client à forte activité avec identité ou rattachement incomplet."
    return result.sort_values("volume_lignes_cdf", ascending=False)


def build_client_movement_summary_table(df: pd.DataFrame, conversion_rate: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = apply_reporting_conversion(df.loc[~df.get("annule", pd.Series(False, index=df.index)).fillna(False)].copy(), conversion_rate)
    work = _ensure_client_analysis_columns(work)
    summary = (
        work.groupby(["client_id", "nom_client"], dropna=False)
        .agg(
            nb_depots=("type_mouvement", lambda s: int(s.isin(["Depot", "Depot mobile"]).sum())),
            volume_depots_cdf=("montant_reporting_cdf", lambda s: float(work.loc[s.index, "montant_reporting_cdf"][work.loc[s.index, "type_mouvement"].isin(["Depot", "Depot mobile"])].sum())),
            nb_retraits=("type_mouvement", lambda s: int(s.isin(["Retrait", "Retrait mobile"]).sum())),
            volume_retraits_cdf=("montant_reporting_cdf", lambda s: float(work.loc[s.index, "montant_reporting_cdf"][work.loc[s.index, "type_mouvement"].isin(["Retrait", "Retrait mobile"])].sum())),
            nb_operations=("operation_id", "nunique"),
            volume_total_cdf=("montant_reporting_cdf", "sum"),
        )
        .reset_index()
    )
    summary["lecture"] = summary.apply(
        lambda row: "Dépôts plus élevés que les retraits." if row["volume_depots_cdf"] >= row["volume_retraits_cdf"] else "Retraits plus élevés que les dépôts.",
        axis=1,
    )
    return summary.sort_values("volume_total_cdf", ascending=False)


def build_top_clients_table(df: pd.DataFrame, conversion_rate: float, top_n: int = 50) -> pd.DataFrame:
    summary = build_client_movement_summary_table(df, conversion_rate)
    if summary.empty:
        return summary
    active_df = _ensure_client_analysis_columns(
        apply_reporting_conversion(
            df.loc[~df.get("annule", pd.Series(False, index=df.index)).fillna(False)].copy(),
            conversion_rate,
        )
    )
    max_operation = (
        active_df
        .groupby(["client_id", "nom_client"], dropna=False)["montant_reporting_cdf"]
        .max()
        .reset_index(name="plus_grosse_operation_cdf")
    )
    result = summary.merge(max_operation, on=["client_id", "nom_client"], how="left")
    return result.head(int(top_n))


def build_cancelled_operations_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "annule" not in df.columns:
        return pd.DataFrame()
    result = df.loc[df["annule"].fillna(False)].copy()
    if result.empty:
        return result
    result["lecture"] = "Opération annulée à rapprocher de la pièce, du motif et de l'opération d'origine."
    return result.sort_values("date_operation", ascending=False)


def build_risky_users_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "operateur" not in df.columns:
        return pd.DataFrame()
    working = df.copy()
    for flag_column in ["annule", "saisie_tardive", "auto_validation"]:
        if flag_column not in working.columns:
            working[flag_column] = False
    grouped = (
        working.groupby("operateur", dropna=False)
        .agg(
            nb_operations=("operation_id", "nunique"),
            nb_annulations=("annule", lambda s: int(s.fillna(False).sum())),
            nb_saisies_tardives=("saisie_tardive", lambda s: int(s.fillna(False).sum())),
            nb_auto_validations=("auto_validation", lambda s: int(s.fillna(False).sum())),
            nb_points_service=("agence", pd.Series.nunique),
            nb_types_operation=("type_operation", pd.Series.nunique),
        )
        .reset_index()
    )
    result = grouped[
        grouped["nb_operations"].ge(50)
        | grouped["nb_annulations"].gt(0)
        | grouped["nb_saisies_tardives"].ge(10)
        | grouped["nb_auto_validations"].gt(0)
    ].copy()
    if result.empty:
        return result
    result["lecture"] = result.apply(
        lambda row: "Présente des annulations, saisies tardives ou auto-validations à relire.",
        axis=1,
    )
    return result.sort_values(["nb_annulations", "nb_saisies_tardives", "nb_operations"], ascending=False)


def build_point_service_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "agence" not in df.columns:
        return pd.DataFrame()
    grouped = (
        df.groupby(["agence", "type_operation"], dropna=False)
        .agg(
            nb_operations=("operation_id", "nunique"),
            nb_annulations=("annule", lambda s: int(s.fillna(False).sum())),
            nb_saisies_tardives=("saisie_tardive", lambda s: int(s.fillna(False).sum())),
        )
        .reset_index()
        .sort_values("nb_operations", ascending=False)
    )
    grouped["lecture"] = grouped.apply(
        lambda row: "Point de service actif à relire en priorité." if row["nb_operations"] >= grouped["nb_operations"].quantile(0.9) else "Activité à comparer au reste du réseau.",
        axis=1,
    )
    return grouped


def build_mobile_banking_summary_table(df: pd.DataFrame, conversion_rate: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    work = apply_reporting_conversion(df.loc[df.get("source_mouvement", pd.Series(index=df.index)).eq("API_MOBILE")].copy(), conversion_rate)
    work = _ensure_client_analysis_columns(work)
    if work.empty:
        return work
    grouped = (
        work.groupby(
            [
                "type_operation",
                pd.to_datetime(work["date_operation"], errors="coerce").dt.to_period("M").astype("string"),
                "agence",
            ],
            dropna=False,
        )
        .agg(
            nb_operations=("operation_id", "nunique"),
            nb_lignes_comptables=("nb_ecritures", "sum"),
            total_debit=("total_debit", "sum"),
            total_credit=("total_credit", "sum"),
            nb_annulees=("annule", lambda s: int(s.fillna(False).sum())),
        )
        .reset_index()
    )
    grouped.columns = [
        "type_operation",
        "mois",
        "agence",
        "nb_operations",
        "nb_lignes_hdpm_api",
        "total_debit",
        "total_credit",
        "nb_annulees",
    ]
    return grouped.sort_values(["mois", "type_operation", "agence"])
