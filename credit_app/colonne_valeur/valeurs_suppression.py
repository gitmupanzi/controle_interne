# -*- coding: utf-8 -*-
# credit_app/colonne_valeur/valeurs_suppression.py
# Notice : Module de suppression (doublons) des valeurs

from __future__ import annotations

import logging
import os
from typing import List, Literal, Optional, Union

import pandas as pd

from credit_app.colonne_valeur.valeurs_nettoyage import get_target_columns


# ---------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------
logger_module = logging.getLogger(__name__)


def _normaliser_dataframe_comparaison(
    df_source: pd.DataFrame,
    colonnes: List[str],
    normaliser: bool,
    type_normalisation: Literal["lower", "capitalize", "upper", None],
) -> Optional[pd.DataFrame]:
    """Construit une copie de comparaison pour la detection des doublons."""
    if not normaliser:
        return None

    df_cmp_local = df_source[colonnes].copy()

    for col in colonnes:
        if pd.api.types.is_object_dtype(df_cmp_local[col]) or pd.api.types.is_string_dtype(df_cmp_local[col]):
            s = df_cmp_local[col].astype("string")
            s = s.str.strip()

            if type_normalisation == "lower":
                s = s.str.lower()
            elif type_normalisation == "capitalize":
                s = s.str.capitalize()
            elif type_normalisation == "upper":
                s = s.str.upper()

            df_cmp_local[col] = s

    return df_cmp_local


def _est_manquant(valeur: object) -> bool:
    """Retourne True si la valeur est consideree comme manquante."""
    if pd.isna(valeur):
        return True
    if isinstance(valeur, str):
        return valeur.strip() == ""
    return False


def gerer_doublons (
    df: pd.DataFrame,
    colonnes_inclues: Optional[List[str]] = None,
    colonnes_exclues: Optional[List[str]] = None,
    normaliser: bool = True,
    type_normalisation: Literal["lower", "capitalize", "upper", None] = "capitalize",
    keep: Union[Literal["first", "last"], bool] = "first",
    mode: Literal["afficher", "afficher_tous", "compter_lignes", "compter_groupes", "detail", "detail_complet", "nettoyer"] = "afficher",
    marquer: bool = False,
    supprimer: bool = False,
    export_path: Optional[str] = None,
    colonnes_tri: Optional[Union[str, List[str]]] = None,
    tri_ascendant: bool = True,
    reset_index: bool = True,
    colonnes_missing: Optional[Union[str, List[str]]] = None,
    logger: Optional[logging.Logger] = None,
) -> Union[pd.DataFrame, int, dict]:
    """
    Gere les doublons d'un DataFrame avec detection, affichage, comptage,
    resume detaille et nettoyage.

    Le principe est le suivant :
    - les doublons sont detectes a partir de `colonnes_inclues` ou, a defaut,
      de toutes les colonnes sauf celles listees dans `colonnes_exclues` ;
    - si `normaliser=True`, la comparaison se fait sur une copie interne
      normalisee (strip + gestion de casse) ;
    - les donnees retournees restent les valeurs originales du DataFrame.

    Parametres
    ----------
    df : pd.DataFrame
        DataFrame a analyser.
    colonnes_inclues : list[str] | None, optional
        Colonnes servant a identifier les doublons. Si None, toutes les colonnes
        sauf `colonnes_exclues` sont utilisees.
    colonnes_exclues : list[str] | None, optional
        Colonnes a ignorer lorsque `colonnes_inclues` n'est pas fourni.
    normaliser : bool, default=True
        Applique une normalisation textuelle avant comparaison.
    type_normalisation : {"lower", "capitalize", "upper", None}, default="capitalize"
        Strategie de normalisation de casse utilisee uniquement pour la detection.
    keep : {"first", "last", False}, default="first"
        Regle Pandas indiquant quelle occurrence est consideree comme reference.
    mode : {"afficher", "afficher_tous", "compter_lignes", "compter_groupes",
            "detail", "detail_complet", "nettoyer"}, default="afficher"
        Mode de sortie :
        - "afficher" : retourne uniquement les lignes marquees comme doublons ;
        - "afficher_tous" : retourne toutes les lignes des groupes doublons,
          y compris la premiere occurrence ;
        - "compter_lignes" : retourne le nombre total de lignes dupliquees ;
        - "compter_groupes" : retourne le nombre de groupes doublons ;
        - "detail" : retourne un dictionnaire avec `groupes`
          et `lignes_dupliquees` ;
        - "detail_complet" : retourne un DataFrame resume par groupe avec le
          nombre exact d'occurrences, `lignes_dupliquees` et `nb_missing` ;
        - "nettoyer" : retourne le DataFrame dedoublonne.
    marquer : bool, default=False
        Ajoute `est_doublon` et, en mode `afficher_tous`, `est_dans_groupe_doublon`.
    supprimer : bool, default=False
        Supprime immediatement les lignes doublonnees avant la sortie.
    export_path : str | None, optional
        Chemin d'export des resultats (`.xlsx`, `.csv`, `.txt`).
    colonnes_tri : str | list[str] | None, optional
        Colonnes de tri pour les sorties tabulaires. Si None, le tri suit les
        colonnes de detection des doublons.
    tri_ascendant : bool, default=True
        Sens du tri pour les sorties tabulaires.
    reset_index : bool, default=True
        Reinitialise l'index des DataFrames retournes.
    colonnes_missing : str | list[str] | None, optional
        Colonnes utilisees pour calculer `nb_missing`. Si None, toutes les
        colonnes du DataFrame d'entree sont analysees.
    logger : logging.Logger | None, optional
        Logger personnalise. Si None, utilise le logger du module.

    Retours
    -------
    pd.DataFrame | int | dict
        Le type retourne depend du `mode` choisi. Les sorties tabulaires
        incluent `nombre_occurrences`, `lignes_dupliquees` et `nb_missing`.
    """
    log = logger or logger_module

    if df is None:
        log.warning("Le DataFrame fourni est None.")
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df doit etre un pandas.DataFrame")

    if df.empty:
        log.warning("Le DataFrame fourni est vide.")
        return pd.DataFrame()

    if mode not in {"afficher", "afficher_tous", "compter_lignes", "compter_groupes", "detail", "detail_complet", "nettoyer"}:
        raise ValueError(f"Mode non reconnu : {mode}")

    if keep not in ("first", "last", False):
        raise ValueError("keep doit etre 'first', 'last' ou False")

    if type_normalisation not in ("lower", "capitalize", "upper", None):
        raise ValueError("type_normalisation doit etre 'lower', 'capitalize', 'upper' ou None")

    if colonnes_inclues is not None and not isinstance(colonnes_inclues, list):
        raise TypeError("colonnes_inclues doit etre une liste de str ou None")

    if colonnes_exclues is not None and not isinstance(colonnes_exclues, list):
        raise TypeError("colonnes_exclues doit etre une liste de str ou None")

    if colonnes_tri is not None and not isinstance(colonnes_tri, (str, list, tuple, set, pd.Index)):
        raise TypeError("colonnes_tri doit etre une chaine, une liste de str ou None")

    if colonnes_missing is not None and not isinstance(colonnes_missing, (str, list, tuple, set, pd.Index)):
        raise TypeError("colonnes_missing doit etre une chaine, une liste de str ou None")

    if export_path is not None and not isinstance(export_path, str):
        raise TypeError("export_path doit etre une chaine ou None")

    df_orig = df.copy()

    colonnes_inclues = get_target_columns(df_orig, colonnes_inclues)

    if colonnes_inclues:
        colonnes = colonnes_inclues
    else:
        colonnes = [
            col for col in df_orig.columns
            if not (colonnes_exclues and col in colonnes_exclues)
        ]

    if not colonnes:
        raise ValueError("Aucune colonne cible n'a ete determinee (colonnes_inclues/colonnes_exclues).")

    colonnes_invalides = [col for col in colonnes if col not in df_orig.columns]
    if colonnes_invalides:
        raise ValueError(f"Colonnes invalides : {colonnes_invalides}")

    colonnes_tri_resolues = get_target_columns(df_orig, colonnes_tri, allow_all_if_none=False)
    if colonnes_tri is not None and not colonnes_tri_resolues:
        raise ValueError("Aucune colonne de tri valide n'a ete fournie.")

    if not colonnes_tri_resolues:
        colonnes_tri_resolues = colonnes

    colonnes_missing_resolues = get_target_columns(df_orig, colonnes_missing)
    if colonnes_missing is not None and not colonnes_missing_resolues:
        raise ValueError("Aucune colonne valide n'a ete fournie pour le calcul des missings.")

    def _construire_masques(df_source: pd.DataFrame) -> tuple[Optional[pd.DataFrame], pd.Series, pd.Series]:
        df_cmp_local = _normaliser_dataframe_comparaison(
            df_source,
            colonnes,
            normaliser,
            type_normalisation,
        )
        base_cmp = df_cmp_local if df_cmp_local is not None else df_source
        masque_doublons_local = base_cmp.duplicated(subset=colonnes, keep=keep)
        masque_groupes_local = base_cmp.duplicated(subset=colonnes, keep=False)
        return df_cmp_local, masque_doublons_local, masque_groupes_local

    df_cmp, masque_doublons, masque_groupes_doublons = _construire_masques(df_orig)

    if marquer:
        df_orig = df_orig.copy()
        df_orig["est_doublon"] = masque_doublons
        if mode == "afficher_tous":
            df_orig["est_dans_groupe_doublon"] = masque_groupes_doublons

    if supprimer:
        nb = int(masque_doublons.sum())
        if nb == 0:
            log.warning("Aucun doublon detecte a supprimer.")
        else:
            df_orig = df_orig.loc[~masque_doublons].copy()
            log.info(f"{nb} doublons supprimes via supprimer=True.")

        df_cmp, masque_doublons, masque_groupes_doublons = _construire_masques(df_orig)
        if marquer:
            df_orig["est_doublon"] = masque_doublons
            if mode == "afficher_tous":
                df_orig["est_dans_groupe_doublon"] = masque_groupes_doublons

    doublons = df_orig.loc[masque_doublons].copy()
    doublons_complets = df_orig.loc[masque_groupes_doublons].copy()

    def _enrichir_sortie_lignes(
        df_source: pd.DataFrame,
        df_cmp_source: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        df_sortie = df_source.copy()

        if df_sortie.empty:
            df_sortie["nombre_occurrences"] = pd.Series(dtype="Int64")
            df_sortie["lignes_dupliquees"] = pd.Series(dtype="Int64")
            df_sortie["nb_missing"] = pd.Series(dtype="Int64")
            return df_sortie

        base_cmp_source = df_cmp_source if df_cmp_source is not None else df_source
        nombre_occurrences = (
            base_cmp_source.groupby(colonnes, dropna=False, sort=False)[colonnes[0]]
            .transform("size")
            .astype("Int64")
        )

        df_sortie["nombre_occurrences"] = nombre_occurrences.to_numpy()
        if keep is False:
            df_sortie["lignes_dupliquees"] = df_sortie["nombre_occurrences"]
        else:
            df_sortie["lignes_dupliquees"] = (df_sortie["nombre_occurrences"] - 1).astype("Int64")

        df_sortie["nb_missing"] = df_sortie[colonnes_missing_resolues].apply(
            lambda ligne: sum(_est_manquant(valeur) for valeur in ligne),
            axis=1,
        ).astype("Int64")

        return df_sortie

    df_annote = _enrichir_sortie_lignes(df_orig, df_cmp)
    doublons = df_annote.loc[masque_doublons].copy()
    doublons_complets = df_annote.loc[masque_groupes_doublons].copy()

    def _construire_detail_complet() -> pd.DataFrame:
        colonnes_resume = list(dict.fromkeys(colonnes + [col for col in colonnes_tri_resolues if col not in colonnes]))
        colonnes_disponibles = [col for col in colonnes_resume if col in df_orig.columns]

        if not masque_groupes_doublons.any():
            colonnes_vides = colonnes_disponibles + ["nombre_occurrences", "lignes_dupliquees", "nb_missing"]
            return pd.DataFrame(columns=colonnes_vides)

        base_groupes = (df_cmp if (normaliser and df_cmp is not None) else df_orig[colonnes]).copy()
        base_groupes = base_groupes.loc[masque_groupes_doublons, colonnes].copy()
        base_groupes["__index_orig"] = base_groupes.index

        counts = (
            base_groupes.groupby(colonnes, dropna=False, sort=False)
            .size()
            .rename("nombre_occurrences")
            .reset_index()
        )

        references = (
            base_groupes.groupby(colonnes, dropna=False, sort=False)["__index_orig"]
            .min()
            .reset_index()
        )

        valeurs_reference = (
            df_annote.loc[references["__index_orig"], colonnes_disponibles + ["nb_missing"]]
            .copy()
            .assign(__index_orig=references["__index_orig"].to_numpy())
        )

        resultat = references.merge(counts, on=colonnes, how="left")
        resultat = resultat.drop(columns=colonnes).merge(valeurs_reference, on="__index_orig", how="left")

        if keep is False:
            resultat["lignes_dupliquees"] = resultat["nombre_occurrences"]
        else:
            resultat["lignes_dupliquees"] = resultat["nombre_occurrences"] - 1

        colonnes_sortie = colonnes_disponibles + ["nombre_occurrences", "lignes_dupliquees", "nb_missing"]
        resultat = resultat[colonnes_sortie]

        try:
            resultat = resultat.sort_values(by=colonnes_tri_resolues, ascending=tri_ascendant, kind="mergesort")
        except Exception as e:
            log.warning(f"Tri impossible sur {colonnes_tri_resolues} ({e}). Retour sans tri.")

        return resultat.reset_index(drop=True) if reset_index else resultat

    detail_complet = _construire_detail_complet()

    if mode == "afficher_tous":
        donnees_export = doublons_complets
    elif mode == "detail_complet":
        donnees_export = detail_complet
    else:
        donnees_export = doublons

    if export_path and not donnees_export.empty:
        dirpath = os.path.dirname(export_path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        ext = os.path.splitext(export_path)[1].lower()
        if ext == ".xlsx":
            donnees_export.to_excel(export_path, index=False)
        elif ext in (".csv", ".txt"):
            donnees_export.to_csv(export_path, index=False)
        else:
            donnees_export.to_csv(export_path, index=False)
            log.warning("Extension inconnue. Export effectue en CSV (fallback).")

        log.info(f"Doublons exportes vers : {export_path}")

    if mode == "afficher":
        if doublons.empty:
            return doublons.reset_index(drop=True) if reset_index else doublons

        try:
            resultat = doublons.sort_values(by=colonnes_tri_resolues, ascending=tri_ascendant, kind="mergesort")
        except Exception as e:
            log.warning(f"Tri impossible sur {colonnes_tri_resolues} ({e}). Retour sans tri.")
            resultat = doublons

        return resultat.reset_index(drop=True) if reset_index else resultat

    if mode == "afficher_tous":
        if doublons_complets.empty:
            return doublons_complets.reset_index(drop=True) if reset_index else doublons_complets

        try:
            resultat = doublons_complets.sort_values(by=colonnes_tri_resolues, ascending=tri_ascendant, kind="mergesort")
        except Exception as e:
            log.warning(f"Tri impossible sur {colonnes_tri_resolues} ({e}). Retour sans tri.")
            resultat = doublons_complets

        return resultat.reset_index(drop=True) if reset_index else resultat

    if mode == "compter_lignes":
        return int(masque_doublons.sum())

    if mode == "compter_groupes":
        base = df_cmp if (normaliser and df_cmp is not None) else df_orig
        return int(base.loc[masque_doublons, colonnes].drop_duplicates().shape[0])

    if mode == "detail":
        total = int(masque_doublons.sum())
        base = df_cmp if (normaliser and df_cmp is not None) else df_orig
        groupes = int(base.loc[masque_doublons, colonnes].drop_duplicates().shape[0])
        return {"groupes": groupes, "lignes_dupliquees": total}

    if mode == "detail_complet":
        return detail_complet

    if mode == "nettoyer":
        base = df_cmp if (normaliser and df_cmp is not None) else df_orig

        avant = len(df_orig)
        idx_keep = base.drop_duplicates(subset=colonnes, keep=keep).index
        df_nettoye = df_annote.loc[idx_keep].copy().sort_index()
        apres = len(df_nettoye)

        supprimees = avant - apres
        pct = (supprimees / avant * 100) if avant else 0.0

        log.info(
            f"Nettoyage doublons termine : {supprimees} lignes supprimees ({pct:.2f}%), "
            f"{apres} lignes restantes. Colonnes={colonnes}, keep={keep}, normaliser={normaliser}."
        )

        return df_nettoye.reset_index(drop=True) if reset_index else df_nettoye

    raise ValueError(f"Mode non reconnu : {mode}")


def suggerer_suppression_doublons(
    df: pd.DataFrame,
    colonnes_doublons: List[str],
    colonnes_tri: Optional[Union[str, List[str]]] = None,
    colonnes_missing: Optional[Union[str, List[str]]] = None,
    colonne_resultat_prioritaire: Optional[str] = None,
    valeurs_resultat_prioritaires: Optional[List[str]] = None,
    normaliser: bool = True,
    type_normalisation: Literal["lower", "capitalize", "upper", None] = "capitalize",
    export_path: Optional[str] = None,
    tri_ascendant: bool = True,
    reset_index: bool = True,
    logger: Optional[logging.Logger] = None,
) -> pd.DataFrame:
    """
    Retourne toutes les lignes des groupes doublons avec une suggestion
    de conservation/suppression basee sur :
    - le nombre de valeurs manquantes ;
    - une colonne metier prioritaire optionnelle (ex. `Resultat_final_labo`).

    Regle de suggestion :
    - par groupe doublon, la ligne conservee en priorite est celle avec
      `resultat_prioritaire=True` si une telle ligne existe ;
    - sinon, la ligne avec le moins de missings est privilegiee ;
     - en cas d'egalite, la premiere ligne du groupe est conservee.
    
    Colonnes d'analyse ajoutees :
    - `nombre_occurrences` : taille totale du groupe doublon ;
    - `lignes_dupliquees` : nombre de lignes a supprimer si on garde 1 ligne ;
    - `nb_missing` : nombre de valeurs manquantes sur les colonnes analysees ;
    - `resultat_prioritaire` : indicateur de priorite metier ;
    - `rang_conservation` : ordre de priorite au sein du groupe ;
    - `suggestion` : `Garder` ou `Supprimer` ;
    - `est_a_garder_suggere` / `est_a_supprimer_suggere` : booleens derives
      de la recommandation finale ;
    - `est_doublon` conserve le sens Pandas classique (par rapport a la
      premiere occurrence du groupe), ce qui peut differer de la recommandation
      finale si une autre ligne est priorisee pour etre gardee.
    """
    log = logger or logger_module

    if df is None:
        log.warning("Le DataFrame fourni est None.")
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        raise TypeError("df doit etre un pandas.DataFrame")

    if df.empty:
        log.warning("Le DataFrame fourni est vide.")
        return pd.DataFrame()

    if not isinstance(colonnes_doublons, list) or not colonnes_doublons:
        raise TypeError("colonnes_doublons doit etre une liste non vide de colonnes.")

    if colonnes_tri is not None and not isinstance(colonnes_tri, (str, list, tuple, set, pd.Index)):
        raise TypeError("colonnes_tri doit etre une chaine, une liste de str ou None")

    if colonnes_missing is not None and not isinstance(colonnes_missing, (str, list, tuple, set, pd.Index)):
        raise TypeError("colonnes_missing doit etre une chaine, une liste de str ou None")

    if colonne_resultat_prioritaire is not None and not isinstance(colonne_resultat_prioritaire, str):
        raise TypeError("colonne_resultat_prioritaire doit etre une chaine ou None")

    if valeurs_resultat_prioritaires is not None and not isinstance(valeurs_resultat_prioritaires, list):
        raise TypeError("valeurs_resultat_prioritaires doit etre une liste de str ou None")

    if export_path is not None and not isinstance(export_path, str):
        raise TypeError("export_path doit etre une chaine ou None")

    df_orig = df.copy()
    colonnes_doublons = get_target_columns(df_orig, colonnes_doublons, allow_all_if_none=False)
    if not colonnes_doublons:
        raise ValueError("Aucune colonne valide n'a ete fournie pour detecter les doublons.")

    colonnes_tri_resolues = get_target_columns(df_orig, colonnes_tri, allow_all_if_none=False)
    if colonnes_tri is not None and not colonnes_tri_resolues:
        raise ValueError("Aucune colonne de tri valide n'a ete fournie.")
    if not colonnes_tri_resolues:
        colonnes_tri_resolues = colonnes_doublons

    colonnes_missing_resolues = get_target_columns(df_orig, colonnes_missing)
    if colonnes_missing is not None and not colonnes_missing_resolues:
        raise ValueError("Aucune colonne valide n'a ete fournie pour le calcul des missings.")

    if colonne_resultat_prioritaire is not None and colonne_resultat_prioritaire not in df_orig.columns:
        raise ValueError(f"Colonne resultat prioritaire invalide : {colonne_resultat_prioritaire}")

    if valeurs_resultat_prioritaires is None:
        valeurs_resultat_prioritaires = ["positif"]

    valeurs_resultat_prioritaires_norm = {
        str(val).strip().casefold()
        for val in valeurs_resultat_prioritaires
        if val is not None and str(val).strip() != ""
    }

    df_cmp = _normaliser_dataframe_comparaison(
        df_orig,
        colonnes_doublons,
        normaliser,
        type_normalisation,
    )
    base_cmp = df_cmp if df_cmp is not None else df_orig
    masque_groupes_doublons = base_cmp.duplicated(subset=colonnes_doublons, keep=False)

    if not masque_groupes_doublons.any():
        colonnes_vides = list(df_orig.columns) + [
            "nombre_occurrences",
            "lignes_dupliquees",
            "nb_missing",
            "resultat_prioritaire",
            "rang_conservation",
            "suggestion",
            "est_a_garder_suggere",
            "est_a_supprimer_suggere",
            "est_doublon",
            "est_dans_groupe_doublon",
        ]
        return pd.DataFrame(columns=colonnes_vides)

    resultat = df_orig.loc[masque_groupes_doublons].copy()
    resultat["est_dans_groupe_doublon"] = True
    resultat["est_doublon"] = base_cmp.loc[masque_groupes_doublons].duplicated(subset=colonnes_doublons, keep="first").to_numpy()
    resultat["__index_orig"] = resultat.index

    resultat["nb_missing"] = resultat[colonnes_missing_resolues].apply(
        lambda ligne: sum(_est_manquant(valeur) for valeur in ligne),
        axis=1,
    )

    if colonne_resultat_prioritaire is not None:
        resultat["resultat_prioritaire"] = (
            resultat[colonne_resultat_prioritaire]
            .map(lambda x: str(x).strip().casefold() if pd.notna(x) else "")
            .isin(valeurs_resultat_prioritaires_norm)
        )
    else:
        resultat["resultat_prioritaire"] = False

    base_groupes = base_cmp.loc[masque_groupes_doublons, colonnes_doublons].copy()
    base_groupes["__index_orig"] = base_groupes.index
    counts = (
        base_groupes.groupby(colonnes_doublons, dropna=False, sort=False)
        .size()
        .rename("nombre_occurrences")
        .reset_index()
    )
    colonnes_groupe_norm = {col: f"__groupe_{col}" for col in colonnes_doublons}
    base_groupes = base_groupes.rename(columns=colonnes_groupe_norm)

    resultat = resultat.merge(base_groupes, on="__index_orig", how="left")
    cles_groupe = [colonnes_groupe_norm[col] for col in colonnes_doublons]
    resultat = resultat.merge(
        counts.rename(columns=colonnes_groupe_norm),
        on=cles_groupe,
        how="left",
    )
    resultat["lignes_dupliquees"] = resultat["nombre_occurrences"] - 1

    resultat = resultat.sort_values(
        by=cles_groupe + ["resultat_prioritaire", "nb_missing", "__index_orig"],
        ascending=[True] * len(cles_groupe) + [False, True, True],
        kind="mergesort",
    )

    resultat["rang_conservation"] = resultat.groupby(cles_groupe, dropna=False, sort=False).cumcount() + 1
    resultat["suggestion"] = resultat["rang_conservation"].map(lambda x: "Garder" if x == 1 else "Supprimer")
    resultat["est_a_garder_suggere"] = resultat["suggestion"].eq("Garder")
    resultat["est_a_supprimer_suggere"] = resultat["suggestion"].eq("Supprimer")

    resultat = resultat.drop(columns=cles_groupe)

    try:
        resultat = resultat.sort_values(
            by=colonnes_tri_resolues + ["rang_conservation"],
            ascending=tri_ascendant,
            kind="mergesort",
        )
    except Exception as e:
        log.warning(f"Tri impossible sur {colonnes_tri_resolues} ({e}). Retour sans tri.")

    colonnes_sortie = [col for col in df_orig.columns if col in resultat.columns] + [
        "nombre_occurrences",
        "lignes_dupliquees",
        "nb_missing",
        "resultat_prioritaire",
        "rang_conservation",
        "suggestion",
        "est_a_garder_suggere",
        "est_a_supprimer_suggere",
        "est_doublon",
        "est_dans_groupe_doublon",
    ]
    resultat = resultat[colonnes_sortie]

    if export_path and not resultat.empty:
        dirpath = os.path.dirname(export_path)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        ext = os.path.splitext(export_path)[1].lower()
        if ext == ".xlsx":
            resultat.to_excel(export_path, index=False)
        elif ext in (".csv", ".txt"):
            resultat.to_csv(export_path, index=False)
        else:
            resultat.to_csv(export_path, index=False)
            log.warning("Extension inconnue. Export effectue en CSV (fallback).")

        log.info(f"Suggestion de suppression exportee vers : {export_path}")

    return resultat.reset_index(drop=True) if reset_index else resultat
