# -*- coding: utf-8 -*-
# credit_app/colonne_valeur/colonne_suppression.py

# Notice : Pour la suppression des colonnes de df

import logging
from typing import Any, Dict, List, Optional

import pandas as pd


# Configuration du logger par defaut
logger = logging.getLogger(__name__)


def _indexer_provenance_colonnes(
    provenance_colonnes: Optional[Dict[str, Any]]
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """
    Cree un index de provenance par nom de colonne standardise et d'origine.
    """
    index = {"standardisee": {}, "originale": {}}

    if not provenance_colonnes:
        return index

    for colonne_standardisee, details in provenance_colonnes.items():
        if not isinstance(details, list):
            continue

        details_valides = [detail for detail in details if isinstance(detail, dict)]
        if not details_valides:
            continue

        index["standardisee"][str(colonne_standardisee)] = details_valides

        for detail in details_valides:
            colonne_originale = detail.get("colonne_originale")
            if colonne_originale in (None, ""):
                continue
            index["originale"].setdefault(str(colonne_originale), []).append(detail)

    return index


def _formater_provenance_colonne(details: Optional[List[Dict[str, Any]]]) -> str:
    """
    Formate la provenance d'une colonne pour l'affichage du rapport.
    """
    if not details:
        return ""

    fichiers = sorted(
        {
            detail.get("fichier") or detail.get("provenance") or "inconnu"
            for detail in details
        }
    )
    colonnes_originales = sorted(
        {
            str(detail.get("colonne_originale"))
            for detail in details
            if detail.get("colonne_originale") not in (None, "")
        }
    )

    morceaux = []
    if fichiers:
        morceaux.append(f"fichier(s): {', '.join(fichiers)}")
    if colonnes_originales:
        morceaux.append(f"nom(s) d'origine: {', '.join(colonnes_originales)}")

    if not morceaux:
        return ""

    return " [" + " | ".join(morceaux) + "]"


# ==========================================================
# AFFICHAGE LISIBLE DU RAPPORT
# ==========================================================
def afficher_rapport_colonnes(audit: dict) -> str:
    """
    Affiche proprement le rapport d'audit sous forme verticale.
    """
    lignes: List[str] = []
    provenance_colonnes = audit.get("provenance_colonnes", {})

    def afficher_liste(
        titre: str,
        liste: List[str],
        details_provenance: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> None:
        lignes.append("")
        lignes.append("=" * 60)
        lignes.append(f"{titre} ({len(liste)})")
        lignes.append("=" * 60)

        if not liste:
            lignes.append("  Aucune")
            return

        for i, col in enumerate(sorted(liste), 1):
            suffixe = _formater_provenance_colonne((details_provenance or {}).get(col))
            lignes.append(f"  {i:02d}. {col}{suffixe}")

    afficher_liste(
        "COLONNES EN TROP",
        audit["colonnes_en_trop"],
        details_provenance=provenance_colonnes,
    )
    afficher_liste("COLONNES MANQUANTES", audit["colonnes_manquantes"])

    if audit.get("colonnes_vides_df"):
        afficher_liste("COLONNES VIDES (toutes NaN)", audit["colonnes_vides_df"])

    if audit.get("colonnes_unnamed_df"):
        afficher_liste("COLONNES TECHNIQUES EXCEL (Unnamed)", audit["colonnes_unnamed_df"])

    rapport = "\n".join(lignes).strip()
    if rapport:
        logger.info("\n%s", rapport)
    return rapport


def colonnes_en_trop(
    df: pd.DataFrame,
    colonnes_attendues: List[str],
    *,
    ignorer_unnamed: bool = True,
    ignorer_vides: bool = True,
    normaliser_espaces: bool = True,
    case_insensitive: bool = False,
    log: bool = False,
) -> Dict[str, Any]:
    """
    Compare les colonnes d'un DataFrame avec une liste de reference.

    Retour
    ------
    dict contenant :
        - colonnes_en_trop
        - colonnes_manquantes
        - colonnes_vides_df
        - colonnes_unnamed_df
        - mapping_normalisation
        - provenance_colonnes
    """
    df_cols_raw = list(df.columns)
    colonnes_unnamed_df = [c for c in df_cols_raw if str(c).startswith("Unnamed")]
    colonnes_vides_df = df.columns[df.isnull().all()].tolist() if ignorer_vides else []

    provenance_index = _indexer_provenance_colonnes(
        df.attrs.get("column_provenance")
        if hasattr(df, "attrs")
        else None
    )

    def _norm(x: str) -> str:
        s = str(x)
        if normaliser_espaces:
            s = " ".join(s.strip().split())
        if case_insensitive:
            s = s.lower()
        return s

    df_cols_filtrees = []
    for c in df_cols_raw:
        if ignorer_unnamed and str(c).startswith("Unnamed"):
            continue
        if ignorer_vides and c in colonnes_vides_df:
            continue
        df_cols_filtrees.append(c)

    expected_norm_set = {_norm(c) for c in colonnes_attendues}
    df_norm = {_norm(c): c for c in df_cols_filtrees}

    colonnes_en_trop_norm = [k for k in df_norm.keys() if k not in expected_norm_set]
    colonnes_en_trop_list = [df_norm[k] for k in colonnes_en_trop_norm]

    df_norm_set = set(df_norm.keys())
    colonnes_manquantes_norm = [k for k in expected_norm_set if k not in df_norm_set]

    expected_norm_to_original = {_norm(c): c for c in colonnes_attendues}
    colonnes_manquantes_list = [
        expected_norm_to_original[k]
        for k in colonnes_manquantes_norm
        if k in expected_norm_to_original
    ]

    provenance_colonnes = {}
    for colonne in colonnes_en_trop_list:
        details = provenance_index["standardisee"].get(str(colonne))
        if not details:
            details = provenance_index["originale"].get(str(colonne), [])
        if details:
            provenance_colonnes[colonne] = details

    mapping_normalisation = {}
    if normaliser_espaces or case_insensitive:
        mapping_normalisation = {c: _norm(c) for c in df_cols_raw}

    if log:
        if colonnes_en_trop_list:
            logger.info("Colonnes en trop (%s): %s", len(colonnes_en_trop_list), colonnes_en_trop_list)
        else:
            logger.info("Aucune colonne en trop detectee.")

        if colonnes_manquantes_list:
            logger.warning(
                "Colonnes manquantes (%s): %s",
                len(colonnes_manquantes_list),
                colonnes_manquantes_list,
            )
        else:
            logger.info("Aucune colonne manquante detectee.")

    return {
        "colonnes_en_trop": colonnes_en_trop_list,
        "colonnes_manquantes": colonnes_manquantes_list,
        "colonnes_vides_df": colonnes_vides_df,
        "colonnes_unnamed_df": colonnes_unnamed_df,
        "mapping_normalisation": mapping_normalisation,
        "provenance_colonnes": provenance_colonnes,
    }
