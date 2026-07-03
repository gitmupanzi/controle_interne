# -*- coding: utf-8 -*-
# credit_app/colonne_valeur/colonne_filtrage.py
# Notice : Des fonctions pour filtrer des DataFrames selon des conditions spécifiques

import logging
import pandas as pd
from typing import List, Union, Optional, Literal
from credit_app.colonne_valeur.valeurs_nettoyage import get_target_columns

# ------------------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------------------
# IMPORTANT : ne pas configurer basicConfig() dans un module de librairie.
# L'application utilisatrice doit configurer le logging.
logger = logging.getLogger(__name__)


def _valider_dataframe(df: pd.DataFrame) -> None:
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df doit être un DataFrame pandas.")


def _valider_semaine_iso(valeur: int, nom_parametre: str) -> None:
    if not isinstance(valeur, int):
        raise TypeError(f"{nom_parametre} doit être un entier.")
    if not 1 <= valeur <= 53:
        raise ValueError(f"{nom_parametre} doit être compris entre 1 et 53.")


# ------------------------------------------------------------------------------
# 1) Filtre générique DataFrame
# ------------------------------------------------------------------------------
def filtrer_df(
    df: pd.DataFrame,
    condition: Optional[Union[pd.Series, list, tuple]] = None,
    colonnes: Optional[list[str]] = None
) -> pd.DataFrame:
    """
    Filtre un DataFrame selon une condition et/ou une liste de colonnes.

    Args:
        df (pd.DataFrame): DataFrame à filtrer.
        condition (pd.Series ou liste/tuple booléens, optionnel): Condition(s) de filtre.
            Peut être une Series booléenne, une liste ou un tuple de booléens, ou None.
            Si None, pas de filtrage sur les lignes.
        colonnes (list[str], optionnel): Liste des colonnes à sélectionner.
            Si None, conserve toutes les colonnes.

    Returns:
        pd.DataFrame: DataFrame filtré.
    """
    _valider_dataframe(df)
    df_filtre = df

    # ------------------------------------------------------------------
    # Appliquer condition sur les lignes
    # ------------------------------------------------------------------
    if condition is not None:
        # Convert list/tuple -> Series alignée sur df.index
        if isinstance(condition, (list, tuple)):
            if len(condition) != len(df):
                raise ValueError(
                    f"[filtrer_df] Longueur de 'condition' ({len(condition)}) "
                    f"différente du nombre de lignes du DataFrame ({len(df)})."
                )
            condition = pd.Series(condition, index=df.index)

        # Series : on aligne sur l'index du df (sécurité)
        if isinstance(condition, pd.Series):
            # Si l'index est différent, on réindexe (fill_value=False)
            if not condition.index.equals(df.index):
                condition = condition.reindex(df.index, fill_value=False)

            # S'assurer que c'est bien booléen
            if condition.dtype != bool:
                # tolérance : convertit True/False "truthy" en bool, autres -> False
                condition = condition.fillna(False).astype(bool)

        else:
            raise TypeError(
                "[filtrer_df] 'condition' doit être une pd.Series, une list ou un tuple de booléens."
            )

        df_filtre = df_filtre.loc[condition]

    # ------------------------------------------------------------------
    # Sélection colonnes
    # ------------------------------------------------------------------
    if colonnes is not None:
        colonnes = list(dict.fromkeys(colonnes))
        colonnes_existantes = [col for col in colonnes if col in df_filtre.columns]
        colonnes_absentes = [col for col in colonnes if col not in df_filtre.columns]

        if colonnes_absentes:
            logger.warning(
                f"[filtrer_df] Colonnes absentes ignorées : {colonnes_absentes}"
            )

        df_filtre = df_filtre.loc[:, colonnes_existantes]

    return df_filtre


# ------------------------------------------------------------------------------
# 2) Filtrer les lignes selon la première date non vide dans une liste de colonnes
# ------------------------------------------------------------------------------
def filtrer_par_premiere_date(
    df: pd.DataFrame,
    colonnes_date: List[str],
    annee: Optional[int] = None,
    garder_colonne: Union[bool, str] = False,
    annee_type: Literal["calendar", "iso"] = "calendar",
    normalize: bool = True,
    min_date: Optional[Union[str, pd.Timestamp]] = None,
    max_date: Optional[Union[str, pd.Timestamp]] = None,
) -> pd.DataFrame:
    """
    Filtre les lignes d'un DataFrame selon la première date non manquante
    (NaT) trouvée dans une liste de colonnes datetime, en respectant un ordre
    de priorité.

    -------------------------------------------------------------------
    PRINCIPE
    -------------------------------------------------------------------
    1) On considère une liste de colonnes (ordre = priorité)
    2) Pour chaque ligne, on prend la première date non-NaT (bfill)
    3) Si annee est précisée → on filtre les lignes dont cette "Premiere_date"
       appartient à l'année demandée
       Si annee=None → aucun filtrage par année (on garde toutes les lignes
       ayant une Premiere_date valide)

    -------------------------------------------------------------------
    PARAMÈTRES
    -------------------------------------------------------------------
    df : pd.DataFrame
        DataFrame source.

    colonnes_date : list[str]
        Colonnes à tester dans l'ordre de priorité.

    annee : int | None
        Année de filtrage.
        - int  : filtre sur l'année
        - None : pas de filtre année

    garder_colonne : bool | str, default False
        - False : supprime la colonne temporaire "Premiere_date"
        - True  : conserve "Premiere_date"
        - str   : conserve et renomme la colonne (ex: "date_reference")

    annee_type : {"calendar","iso"}, default "calendar"
        - "calendar" : df["Premiere_date"].dt.year
        - "iso"      : df["Premiere_date"].dt.isocalendar().year
          (utile autour du 31/12 et 01/01)

    normalize : bool, default True
        Si True, normalise Premiere_date à minuit (00:00:00).
        Utile si tu veux une comparaison "jour" cohérente.

    min_date / max_date : str|Timestamp|None
        Bornes optionnelles : exclure des dates hors plage (données aberrantes, futur, etc.)
        Ex: min_date="2010-01-01", max_date="today"

    -------------------------------------------------------------------
    RETOUR
    -------------------------------------------------------------------
    pd.DataFrame
        DataFrame filtré.
    """
    _valider_dataframe(df)
    if not colonnes_date:
        raise ValueError("colonnes_date ne peut pas être vide.")
    if annee is not None and not isinstance(annee, int):
        raise TypeError("annee doit être un entier ou None.")

    if df.empty:
        return df.copy()

    df_copy = df.copy()

    # 1) garder uniquement les colonnes existantes (et les convertir si nécessaire)
    colonnes_existantes: List[str] = []
    for col in colonnes_date:
        if col in df_copy.columns:
            # Convertit en datetime64[ns] uniquement si nécessaire, sans casser les datetime existants
            if not pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                df_copy[col] = pd.to_datetime(df_copy[col], errors="coerce")
            colonnes_existantes.append(col)
        else:
            logger.warning(f"[FiltrageDate] Colonne '{col}' non trouvée. Ignorée.")

    if not colonnes_existantes:
        logger.error("[FiltrageDate] Aucune des colonnes spécifiées n'existe dans le DataFrame.")
        return df_copy

    # 2) Première date non manquante selon l'ordre de priorité
    premiere_date = df_copy[colonnes_existantes].bfill(axis=1).iloc[:, 0]

    if normalize:
        premiere_date = premiere_date.dt.normalize()

    # 3) Nettoyage optionnel par bornes
    if min_date is not None:
        min_ts = pd.Timestamp(min_date) if str(min_date).lower() != "today" else pd.Timestamp.today().normalize()
        premiere_date = premiere_date.where(premiere_date >= min_ts, pd.NaT)

    if max_date is not None:
        max_ts = pd.Timestamp(max_date) if str(max_date).lower() != "today" else pd.Timestamp.today().normalize()
        premiere_date = premiere_date.where(premiere_date <= max_ts, pd.NaT)

    df_copy["Premiere_date"] = premiere_date

    # 4) Filtre année (calendar vs iso)
    if annee is None:
        # Aucun filtre année → on garde seulement les lignes ayant une date valide
        mask = df_copy["Premiere_date"].notna()
    else:
        if annee_type == "calendar":
            mask = df_copy["Premiere_date"].dt.year.eq(annee)
        elif annee_type == "iso":
            mask = df_copy["Premiere_date"].dt.isocalendar().year.eq(annee)
        else:
            raise ValueError("annee_type doit être 'calendar' ou 'iso'")

    df_filtre = df_copy.loc[mask].copy()

    logger.info(
        f"[FiltrageDate] {len(df_filtre)} lignes conservées | "
        f"annee={annee} ({annee_type}) | colonnes_testées={colonnes_existantes} | total={len(df_copy)}"
    )

    # 5) Gestion de la colonne temporaire
    if isinstance(garder_colonne, str):
        df_filtre = df_filtre.rename(columns={"Premiere_date": garder_colonne})
    elif not garder_colonne:
        df_filtre = df_filtre.drop(columns=["Premiere_date"])

    return df_filtre

# ------------------------------------------------------------------------------
# 3) Filtrer par semaine épidémiologique (flexible)
# ------------------------------------------------------------------------------
def filtrer_par_semaine(
    df: pd.DataFrame,
    colonnes_semaine: Optional[str] = None,
    semaines: Optional[Union[int, list, tuple]] = None,
    condition: Optional[pd.Series] = None,
    colonnes_a_garder: Optional[list[str]] = None,
    tri_par: Optional[Union[str, list[str]]] = None,
    ordre_croissant: bool = True
) -> pd.DataFrame:
    """
    Filtre un DataFrame de façon flexible :
    - par numéro de semaine (avec interprétation intelligente des tuples)
    - par condition booléenne personnalisée
    - avec sélection de colonnes et tri optionnel

    Paramètres
    ----------
    df : pd.DataFrame
        Le DataFrame à filtrer.
    colonnes_semaine : str ou None
        Nom de la colonne contenant le numéro de la semaine (ex: 'Num_semaine_epid').
        Obligatoire si `semaines` est spécifié.
    semaines : int, list, tuple ou None
        - int         : une seule semaine
        - tuple       : (début, fin), (début,), (None, fin), (début, None)
        - list        : liste explicite de semaines
    condition : pd.Series ou None
        Une condition booléenne personnalisée pour filtrer les lignes (ex: df['Province'] == 'Equateur').
        Elle sera automatiquement alignée (reindexée) sur l'index du DataFrame filtré.
    colonnes_a_garder : list[str] ou None
        Colonnes à retourner. Si None, toutes les colonnes sont conservées.
    tri_par : str ou list[str] ou None
        Nom(s) de colonnes pour trier le résultat.
    ordre_croissant : bool
        Tri croissant si True, décroissant sinon.

    Retour
    ------
    pd.DataFrame
        DataFrame filtré, avec colonnes sélectionnées et triées si demandé.
    """
    _valider_dataframe(df)
    df_filtre = df.copy()
    lignes_avant = len(df_filtre)

    # ------------------------------------------------------------------
    # ✅ Filtrage par semaine
    # ------------------------------------------------------------------
    if semaines is not None:
        if colonnes_semaine is None:
            raise ValueError("Le paramètre 'colonnes_semaine' est requis si 'semaines' est spécifié.")
        if colonnes_semaine not in df_filtre.columns:
            raise KeyError(f"La colonne '{colonnes_semaine}' est absente du DataFrame.")

        # Conversion robuste en numérique (évite between() faux si dtype object)
        w = pd.to_numeric(df_filtre[colonnes_semaine], errors="coerce")

        if isinstance(semaines, int):
            _valider_semaine_iso(semaines, "semaines")
            condition_semaine = (w == semaines)
            logger.info(f"✅ Filtrage : semaine == {semaines}")

        elif isinstance(semaines, tuple):
            # Autorise (debut,), (debut, fin), (None, fin), (debut, None)
            if len(semaines) == 1:
                debut = semaines[0]
                if debut is not None:
                    _valider_semaine_iso(debut, "semaines[0]")
                condition_semaine = (w >= debut)
                logger.info(f"✅ Filtrage : semaine >= {debut}")

            elif len(semaines) == 2:
                min_sem, max_sem = semaines

                if min_sem is not None and max_sem is not None:
                    _valider_semaine_iso(min_sem, "semaines[0]")
                    _valider_semaine_iso(max_sem, "semaines[1]")
                    condition_semaine = w.between(min_sem, max_sem)
                    logger.info(f"✅ Filtrage : {min_sem} <= semaine <= {max_sem}")

                elif min_sem is not None:
                    _valider_semaine_iso(min_sem, "semaines[0]")
                    condition_semaine = (w >= min_sem)
                    logger.info(f"✅ Filtrage : semaine >= {min_sem}")

                elif max_sem is not None:
                    _valider_semaine_iso(max_sem, "semaines[1]")
                    condition_semaine = (w <= max_sem)
                    logger.info(f"✅ Filtrage : semaine <= {max_sem}")

                else:
                    condition_semaine = pd.Series(True, index=df_filtre.index)
                    logger.info("⚠️ Tuple semaines (None, None) : pas de filtrage appliqué.")

            else:
                raise ValueError("Tuple 'semaines' invalide : il doit contenir au plus 2 éléments.")

        elif isinstance(semaines, list):
            # Exemple: [1,2,3]
            semaines = [int(s) for s in semaines]
            for i, semaine in enumerate(semaines):
                _valider_semaine_iso(semaine, f"semaines[{i}]")
            condition_semaine = w.isin(semaines)
            logger.info(f"✅ Filtrage : semaines dans {semaines}")

        else:
            raise TypeError("Le paramètre 'semaines' doit être un int, list ou tuple.")

        # Appliquer le filtre semaine (en conservant l'index)
        df_filtre = df_filtre.loc[condition_semaine.fillna(False)]

    # ------------------------------------------------------------------
    # ✅ Filtrage par condition personnalisée (alignement sécurisé)
    # ------------------------------------------------------------------
    if condition is not None:
        if not isinstance(condition, pd.Series):
            raise TypeError("Le paramètre 'condition' doit être une pd.Series booléenne.")

        # Aligner sur l'index courant (après filtre semaine éventuel)
        condition_alignee = condition.reindex(df_filtre.index, fill_value=False)

        # S'assurer booléen
        if condition_alignee.dtype != bool:
            condition_alignee = condition_alignee.fillna(False).astype(bool)

        df_filtre = df_filtre.loc[condition_alignee]
        logger.info("✅ Filtrage par condition personnalisée appliqué.")

    # ------------------------------------------------------------------
    # ✅ Colonnes à garder
    # ------------------------------------------------------------------
    if colonnes_a_garder:
        colonnes_existantes = [col for col in colonnes_a_garder if col in df_filtre.columns]
        colonnes_manquantes = list(set(colonnes_a_garder) - set(colonnes_existantes))

        df_filtre = df_filtre[colonnes_existantes]
        logger.info(f"✅ Colonnes conservées : {colonnes_existantes}")

        if colonnes_manquantes:
            logger.warning(f"⚠️ Colonnes absentes ignorées : {colonnes_manquantes}")
    else:
        logger.info("ℹ️ Aucune colonne spécifiée : toutes les colonnes sont conservées.")

    # ------------------------------------------------------------------
    # ✅ Tri
    # ------------------------------------------------------------------
    if tri_par:
        colonnes_tri = [tri_par] if isinstance(tri_par, str) else tri_par
        colonnes_tri_valides = [col for col in colonnes_tri if col in df_filtre.columns]

        if colonnes_tri_valides:
            df_filtre = df_filtre.sort_values(by=colonnes_tri_valides, ascending=ordre_croissant)
            logger.info(f"✅ Tri appliqué sur {colonnes_tri_valides} (ordre croissant : {ordre_croissant})")
        else:
            logger.warning(f"⚠️ Aucune des colonnes de tri '{tri_par}' n'existe dans le DataFrame.")

    lignes_apres = len(df_filtre)
    logger.info(f"📊 Lignes avant filtrage : {lignes_avant}")
    logger.info(f"📉 Lignes après filtrage : {lignes_apres}")

    return df_filtre


# ------------------------------------------------------------------------------
# 4) Filtrer par nullité / non-nullité (avec get_target_columns)
# ------------------------------------------------------------------------------
def filtrer_par_nullite(
    df: pd.DataFrame,
    colonnes: Union[str, List[str], pd.Series],
    mode: str = "notnull"
) -> pd.DataFrame:
    """
    Retourne les lignes d'un DataFrame selon que les colonnes soient nulles ou non.

    - Utilise get_target_columns pour résoudre la liste de colonnes à utiliser
      (y compris la gestion de colonnes de type 'Unnamed').
    - Mode 'notnull' : conserve les lignes où toutes les colonnes ciblées sont non nulles
    - Mode 'isnull'  : conserve les lignes où au moins une des colonnes ciblées est nulle

    Args:
        df (pd.DataFrame): DataFrame à filtrer.
        colonnes (str | List[str] | pd.Series): Colonnes à tester (ou une Series dont on prend le nom).
        mode (str): "notnull" ou "isnull".

    Returns:
        pd.DataFrame: DataFrame filtré (index réinitialisé).
    """
    _valider_dataframe(df)
    # Si on reçoit une Series → on prend son nom
    if isinstance(colonnes, pd.Series):
        colonnes = colonnes.name

    # Résolution via get_target_columns
    colonnes_valides = get_target_columns(df, colonnes, allow_all_if_none=False)

    if not colonnes_valides:
        logger.warning("⚠️ Aucune colonne valide trouvée pour appliquer le filtre.")
        return df.iloc[0:0].copy()  # DataFrame vide

    # Application du masque
    if mode == "notnull":
        masque = df[colonnes_valides].notnull().all(axis=1)
    elif mode == "isnull":
        masque = df[colonnes_valides].isnull().any(axis=1)
    else:
        raise ValueError("Le paramètre 'mode' doit être 'notnull' ou 'isnull'.")

    result = df.loc[masque].reset_index(drop=True)

    logger.info(
        f"[filtrer_par_nullite] mode={mode}, colonnes={colonnes_valides} : {len(result)} lignes trouvées"
    )

    return result


def filtrer_fenetre_iso(
    df: pd.DataFrame,
    semaine_min: int,
    semaine_max: int,
    annee: int | None = None
) -> pd.DataFrame:
    """
    Filtre un DataFrame sur une plage de semaines épidémiologiques ISO.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame contenant au minimum :
        - Num_semaine_epid
        - Annee_epid (si annee est fourni)
    semaine_min : int
        Numéro minimal de semaine ISO (ex: 1).
    semaine_max : int
        Numéro maximal de semaine ISO (ex: 2).
    annee : int | None, default=None
        Année ISO cible.
        - Si None : filtre uniquement sur les semaines (toutes années confondues)
        - Si défini : filtre sur l'année ISO spécifiée

    Returns
    -------
    pd.DataFrame
        DataFrame filtré.
    """
    _valider_dataframe(df)
    _valider_semaine_iso(semaine_min, "semaine_min")
    _valider_semaine_iso(semaine_max, "semaine_max")
    if semaine_min > semaine_max:
        raise ValueError("semaine_min ne peut pas être supérieure à semaine_max.")
    if "Num_semaine_epid" not in df.columns:
        raise KeyError("La colonne 'Num_semaine_epid' est requise.")
    if annee is not None and "Annee_epid" not in df.columns:
        raise KeyError("La colonne 'Annee_epid' est requise quand annee est fourni.")

    # Sécurisation des types numériques
    semaine = pd.to_numeric(df["Num_semaine_epid"], errors="coerce")
    annee_iso = pd.to_numeric(df.get("Annee_epid"), errors="coerce")

    if annee is not None:
        masque = (annee_iso == annee) & semaine.between(semaine_min, semaine_max)
    else:
        masque = semaine.between(semaine_min, semaine_max)

    result = df.loc[masque].copy()
    logger.info(
        "[filtrer_fenetre_iso] %s lignes conservées | semaines=%s-%s | annee=%s",
        len(result), semaine_min, semaine_max, annee,
    )
    return result

def filtrer_fenetre_iso_cross_year(
    df: pd.DataFrame,
    annee_debut: int,
    semaine_debut: int,
    annee_fin: int,
    semaine_fin: int
) -> pd.DataFrame:
    """
    Filtre une fenêtre de semaines ISO pouvant traverser une année.

    Exemple
    -------
    2025-W52 → 2026-W02

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame contenant :
        - Annee_epid
        - Num_semaine_epid
    annee_debut : int
        Année ISO de début.
    semaine_debut : int
        Semaine ISO de début.
    annee_fin : int
        Année ISO de fin.
    semaine_fin : int
        Semaine ISO de fin.

    Returns
    -------
    pd.DataFrame
        DataFrame filtré sur la fenêtre ISO.
    """
    _valider_dataframe(df)
    if "Num_semaine_epid" not in df.columns or "Annee_epid" not in df.columns:
        raise KeyError("Les colonnes 'Num_semaine_epid' et 'Annee_epid' sont requises.")
    for nom, valeur in [("semaine_debut", semaine_debut), ("semaine_fin", semaine_fin)]:
        _valider_semaine_iso(valeur, nom)
    for nom, valeur in [("annee_debut", annee_debut), ("annee_fin", annee_fin)]:
        if not isinstance(valeur, int):
            raise TypeError(f"{nom} doit être un entier.")
    if (annee_debut, semaine_debut) > (annee_fin, semaine_fin):
        raise ValueError("La fenêtre de début ne peut pas être postérieure à la fenêtre de fin.")

    semaine = pd.to_numeric(df["Num_semaine_epid"], errors="coerce")
    annee = pd.to_numeric(df["Annee_epid"], errors="coerce")

    # Cas 1 : même année ISO
    if annee_debut == annee_fin:
        masque = (
            (annee == annee_debut) &
            semaine.between(semaine_debut, semaine_fin)
        )

    # Cas 2 : passage d'année ISO
    else:
        masque = (
            ((annee == annee_debut) & (semaine >= semaine_debut)) |
            ((annee == annee_fin) & (semaine <= semaine_fin))
        )

    result = df.loc[masque].copy()
    logger.info(
        "[filtrer_fenetre_iso_cross_year] %s lignes conservées | %s-W%02d -> %s-W%02d",
        len(result), annee_debut, semaine_debut, annee_fin, semaine_fin,
    )
    return result
