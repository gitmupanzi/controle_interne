from __future__ import annotations

import pandas as pd
import streamlit as st

from credit_app.ui import render_kpi_cards, render_panel_title, render_summary_box


def _pick_first_phone(df: pd.DataFrame) -> pd.Series:
    phone = pd.Series(pd.NA, index=df.index, dtype="string")
    for column_name in ["telephone", "Portable"]:
        if column_name in df.columns:
            candidate = df[column_name].astype("string").str.strip()
            phone = phone.fillna(candidate.mask(candidate.fillna("").eq(""), pd.NA))
    return phone


def _pick_first_email(df: pd.DataFrame) -> pd.Series:
    if "E-mail" not in df.columns:
        return pd.Series(pd.NA, index=df.index, dtype="string")
    return df["E-mail"].astype("string").str.strip().replace("", pd.NA)


def _build_crm_action_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    work = df.copy()
    work["telephone_contact"] = _pick_first_phone(work)
    work["email_contact"] = _pick_first_email(work)
    work["piece_identite"] = work.get("Numéro de la pièce d’identité", pd.Series(pd.NA, index=work.index, dtype="object"))
    work["compte_client"] = work.get("compte_id", pd.Series(pd.NA, index=work.index, dtype="object"))
    work["date_operation"] = pd.to_datetime(work.get("date_operation"), errors="coerce")

    phone_missing = work["telephone_contact"].fillna("").eq("")
    email_missing = work["email_contact"].fillna("").eq("")
    phone_digits = work["telephone_contact"].fillna("").str.replace(r"\D", "", regex=True)
    phone_invalid = ~phone_missing & ~phone_digits.str.match(r"^(243\d{9}|0\d{9})$", na=False)
    email_invalid = ~email_missing & ~work["email_contact"].str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", na=False)
    piece_missing = work["piece_identite"].astype("string").str.strip().fillna("").isin({"", "0"})
    compte_missing = work["compte_client"].astype("string").str.strip().fillna("").isin({"", "0"})
    manager_missing = (
        work["agent_credit"].astype("string").str.strip().fillna("").eq("")
        if "agent_credit" in work.columns
        else pd.Series(False, index=work.index)
    )
    zone_missing = (
        work["zone_geographique"].astype("string").str.strip().fillna("").eq("")
        if "zone_geographique" in work.columns
        else pd.Series(False, index=work.index)
    )
    category_missing = (
        work["categorie"].astype("string").str.strip().fillna("").eq("")
        if "categorie" in work.columns
        else pd.Series(False, index=work.index)
    )
    last_activity_missing = work["date_operation"].isna()
    if work["date_operation"].notna().any():
        reference_date = work["date_operation"].max()
        work["jours_inactivite"] = (reference_date - work["date_operation"]).dt.days
    else:
        work["jours_inactivite"] = pd.NA

    shared_phone = pd.Series(False, index=work.index)
    valid_phone_rows = phone_digits.ne("")
    if valid_phone_rows.any() and "client_id" in work.columns:
        phone_counts = (
            pd.DataFrame({"client_id": work["client_id"], "telephone": phone_digits})
            .loc[lambda frame: frame["client_id"].notna() & frame["telephone"].ne("")]
            .drop_duplicates()
            .groupby("telephone")["client_id"]
            .nunique()
        )
        shared_phone = phone_digits.map(phone_counts).fillna(0).gt(1)

    shared_piece = pd.Series(False, index=work.index)
    valid_piece = ~piece_missing
    if valid_piece.any() and "client_id" in work.columns:
        piece_counts = (
            pd.DataFrame({"client_id": work["client_id"], "piece": work["piece_identite"].astype("string").str.strip()})
            .loc[lambda frame: frame["client_id"].notna() & frame["piece"].fillna("").ne("")]
            .drop_duplicates()
            .groupby("piece")["client_id"]
            .nunique()
        )
        shared_piece = work["piece_identite"].astype("string").str.strip().map(piece_counts).fillna(0).gt(1)

    locked_mask = (
        work["Locked"].fillna(False).astype(bool)
        if "Locked" in work.columns
        else pd.Series(False, index=work.index)
    )
    unsubscribed_mask = (
        work["Mode Désabonné"].astype("string").str.strip().fillna("").ne("")
        if "Mode Désabonné" in work.columns
        else pd.Series(False, index=work.index)
    )
    mail_reject_mask = (
        work["Rejet des mails"].fillna(False).astype(bool)
        if "Rejet des mails" in work.columns
        else pd.Series(False, index=work.index)
    )

    def build_reading(row: pd.Series) -> str:
        reasons: list[str] = []
        if bool(phone_missing.loc[row.name]):
            reasons.append("ajouter le téléphone")
        elif bool(phone_invalid.loc[row.name]):
            reasons.append("corriger le téléphone")
        if bool(email_missing.loc[row.name]):
            reasons.append("ajouter l'e-mail")
        elif bool(email_invalid.loc[row.name]):
            reasons.append("corriger l'e-mail")
        if bool(piece_missing.loc[row.name]):
            reasons.append("ajouter la pièce")
        if bool(compte_missing.loc[row.name]):
            reasons.append("renseigner le compte client")
        if bool(manager_missing.loc[row.name]):
            reasons.append("affecter un gestionnaire")
        if bool(zone_missing.loc[row.name]):
            reasons.append("compléter la province")
        if bool(category_missing.loc[row.name]):
            reasons.append("compléter la catégorie")
        if bool(last_activity_missing.loc[row.name]):
            reasons.append("mettre à jour la dernière activité")
        elif pd.notna(row.get("jours_inactivite")) and float(row["jours_inactivite"]) >= 180:
            reasons.append("relancer le client inactif")
        if bool(shared_phone.loc[row.name]):
            reasons.append("vérifier le téléphone partagé")
        if bool(shared_piece.loc[row.name]):
            reasons.append("vérifier la pièce partagée")
        if bool(locked_mask.loc[row.name]):
            reasons.append("vérifier la fiche verrouillée")
        if bool(unsubscribed_mask.loc[row.name]):
            reasons.append("revoir le désabonnement")
        if bool(mail_reject_mask.loc[row.name]):
            reasons.append("contrôler le rejet d'e-mail")
        return "; ".join(reasons) if reasons else "Aucune action prioritaire."

    priority_mask = (
        phone_missing
        | phone_invalid
        | email_invalid
        | piece_missing
        | compte_missing
        | manager_missing
        | last_activity_missing
        | shared_phone
        | shared_piece
        | locked_mask
        | unsubscribed_mask
        | mail_reject_mask
    )

    action_df = work.loc[priority_mask].copy()
    if action_df.empty:
        return pd.DataFrame()

    action_df["Lecture"] = action_df.apply(build_reading, axis=1)
    display_columns = [
        "client_id",
        "nom_client",
        "agent_credit",
        "Origine du Prospect",
        "zone_geographique",
        "categorie",
        "telephone_contact",
        "email_contact",
        "piece_identite",
        "compte_client",
        "date_operation",
        "jours_inactivite",
        "Lecture",
    ]
    available_columns = [column for column in display_columns if column in action_df.columns]
    action_df = action_df[available_columns].copy()
    return action_df.rename(
        columns={
            "client_id": "Client",
            "nom_client": "Nom client",
            "agent_credit": "Gestionnaire",
            "Origine du Prospect": "Origine",
            "zone_geographique": "Province",
            "categorie": "Catégorie",
            "telephone_contact": "Téléphone",
            "email_contact": "E-mail",
            "piece_identite": "Pièce d'identité",
            "compte_client": "Compte client",
            "date_operation": "Dernière activité",
            "jours_inactivite": "Jours sans activité",
        }
    )


def render_crm_clients_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.warning("Aucune donnée n'est disponible pour le suivi CRM.")
        return

    action_df = _build_crm_action_table(df)
    phone_series = _pick_first_phone(df)
    email_series = _pick_first_email(df)
    last_activity = pd.to_datetime(df.get("date_operation"), errors="coerce")

    phone_missing = int(phone_series.fillna("").eq("").sum())
    email_missing = int(email_series.fillna("").eq("").sum())
    piece_missing = int(
        df.get("Numéro de la pièce d’identité", pd.Series(dtype="object"))
        .astype("string")
        .str.strip()
        .fillna("")
        .isin({"", "0"})
        .sum()
    )
    locked_count = int(df.get("Locked", pd.Series(dtype="bool")).fillna(False).astype(bool).sum()) if "Locked" in df.columns else 0
    inactive_90 = 0
    if last_activity.notna().any():
        inactive_90 = int(((last_activity.max() - last_activity).dt.days >= 90).fillna(False).sum())

    render_panel_title("Actions CRM")
    render_summary_box(
        "À retenir",
        [
            "Cet onglet rassemble les fiches clients CRM qui demandent une correction ou une relance rapide.",
            "L'objectif est de réduire les informations manquantes, les contacts non fiables et les fiches inactives.",
            "Les tableaux ci-dessous peuvent servir de liste de travail opérationnelle pour l'équipe CRM ou commerciale.",
        ],
    )

    render_kpi_cards(
        [
            ("Fiches à corriger", f"{len(action_df):,}".replace(",", " "), "Liste de travail active", "slate"),
            ("Téléphones manquants", f"{phone_missing:,}".replace(",", " "), "Clients sans contact mobile", "slate"),
            ("E-mails manquants", f"{email_missing:,}".replace(",", " "), "Contacts à compléter", "slate"),
            ("Pièces manquantes", f"{piece_missing:,}".replace(",", " "), "KYC à compléter", "slate"),
            ("Fiches verrouillées", f"{locked_count:,}".replace(",", " "), "À débloquer ou revoir", "slate"),
            ("Inactifs 90 j+", f"{inactive_90:,}".replace(",", " "), "Clients à relancer", "slate"),
        ]
    )

    if action_df.empty:
        st.success("Aucune action CRM prioritaire n'a été détectée sur ce périmètre.")
        return

    top_left, top_right = st.columns((1, 1))
    with top_left:
        render_panel_title("Corrections prioritaires")
        st.dataframe(action_df.head(200), width="stretch", hide_index=True)
    with top_right:
        render_panel_title("Relances inactivité / blocage")
        relance_mask = (
            action_df["Lecture"].astype("string").str.contains("inactif|verrouillée|désabonnement", case=False, na=False)
            if "Lecture" in action_df.columns
            else pd.Series(False, index=action_df.index)
        )
        relance_df = action_df.loc[relance_mask].head(200)
        if relance_df.empty:
            st.info("Aucune relance spécifique n'est actuellement isolée sur ce périmètre.")
        else:
            st.dataframe(relance_df, width="stretch", hide_index=True)
