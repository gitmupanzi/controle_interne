# -*- coding: utf-8 -*-
# credit_app/colonne_valeur/valeur_completude.py

import re
import unicodedata
import logging
from typing import Any, Iterable, Dict, Optional, Sequence

import pandas as pd

from .valeurs_nettoyage import _is_na_like


logger = logging.getLogger(__name__)


def _iter_normalized_mapping(values: Iterable[Any]) -> Dict[str, Any]:
    mapping: Dict[str, Any] = {}
    for value in values or []:
        key = normaliser_valeur(value)
        if key is not None and key not in mapping:
            mapping[key] = value
    return mapping


def _build_completude_result(
    ref_norm: Dict[str, Any],
    df_norm: Dict[str, Any],
    seuil_min: int,
    include_extra: bool = True,
) -> dict:
    keys_ref = set(ref_norm.keys())
    keys_df = set(df_norm.keys())

    nb_attendus = len(keys_ref)
    nb_recus = len(keys_ref & keys_df)
    completude = nb_recus / nb_attendus if nb_attendus > 0 else 0.0
    completude_pct = round(completude * 100, 2)

    result = {
        "nb_attendus": nb_attendus,
        "nb_reçus": nb_recus,
        "completude_%": completude_pct,
        "manquantes": [ref_norm[k] for k in sorted(keys_ref - keys_df)],
        "seuil_min": seuil_min,
        "respecte_seuil": completude_pct >= seuil_min,
    }

    if include_extra:
        result["en_trop"] = [df_norm[k] for k in sorted(keys_df - keys_ref)]
        result["correspondances"] = {df_norm[k]: ref_norm[k] for k in (keys_df & keys_ref)}

    return result

def normaliser_valeur(s):
    """Nettoie et met en forme une valeur texte :
    - ignore None / NaN / chaîne vide
    - strip espaces
    - remplace - et _ par espace
    - réduit les espaces multiples
    - enlève les accents
    - met la première lettre de chaque mot en majuscule
    """
    if s is None or pd.isna(s):
        return None

    s = str(s).replace("\u00A0", " ").strip()
    if not s:
        return None
    if s.lower() == "nan":
        return None

    # Remplacer - et _ par espace
    s = re.sub(r"[-_]", " ", s)
    # Réduire les espaces multiples
    s = re.sub(r"\s+", " ", s)

    # Enlever les accents
    s_norm = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s_norm if not unicodedata.combining(c))

    # Majuscule en début de mot
    s = s.title()
    return s


def comparer_listes(ref_list, df_list, seuil_min: int = 0):
    """
    Compare deux listes avec correction automatique de casse, d'espaces, etc.
    
    Paramètres
    ----------
    ref_list : list
        Liste de référence (ex : provinces attendues).
    df_list : list
        Liste observée dans les données (ex : provinces présentes).
    seuil_min : int, optionnel (par défaut 0)
        Seuil minimal de complétude attendu, en pourcentage.
    
    Retour
    ------
    dict avec les clés :
        - manquantes : éléments attendus absents
        - en_trop : éléments présents non attendus
        - correspondances : mapping {valeur_dans_df : valeur_dans_ref}
        - nb_attendus : nombre total d’éléments attendus
        - nb_reçus : nombre d’éléments attendus trouvés
        - completude_% : pourcentage de complétude (float)
        - seuil_min : seuil utilisé
        - respecte_seuil : bool, True si complétude >= seuil_min
    """
    if not 0 <= seuil_min <= 100:
        raise ValueError("seuil_min doit être compris entre 0 et 100.")

    ref_norm = _iter_normalized_mapping(ref_list)
    df_norm = _iter_normalized_mapping(df_list)
    result = _build_completude_result(ref_norm, df_norm, seuil_min, include_extra=True)
    logger.info(
        "Comparaison complétude : %s/%s éléments attendus trouvés (%.2f%%).",
        result["nb_reçus"],
        result["nb_attendus"],
        result["completude_%"],
    )
    return result


def calculer_completude(ref_list, df_list, seuil_min: int = 0):
    """
    Calcule la complétude et liste les manquants après normalisation.

    Paramètres
    ----------
    ref_list : list
        Liste de référence (ex : provinces attendues).
    df_list : list
        Liste observée dans les données.
    seuil_min : int, optionnel (par défaut 0)
        Seuil minimal de complétude attendu, en pourcentage.

    Retour
    ------
    dict avec les clés :
        - nb_attendus : nombre total d’éléments attendus
        - nb_reçus : nombre d’éléments attendus trouvés
        - completude_% : pourcentage de complétude
        - manquantes : liste des éléments attendus non trouvés
        - seuil_min : seuil utilisé
        - respecte_seuil : bool, True si complétude >= seuil_min
    """
    if not 0 <= seuil_min <= 100:
        raise ValueError("seuil_min doit être compris entre 0 et 100.")

    ref_norm = _iter_normalized_mapping(ref_list)
    df_norm = _iter_normalized_mapping(df_list)
    result = _build_completude_result(ref_norm, df_norm, seuil_min, include_extra=False)
    logger.info(
        "Complétude calculée : %s/%s éléments attendus trouvés (%.2f%%).",
        result["nb_reçus"],
        result["nb_attendus"],
        result["completude_%"],
    )
    return result


def _decision_missing(
    pct_missing: float,
    *,
    colonne_absente: bool,
    seuil_acceptable: float,
    seuil_surveillance: float,
) -> str:
    """Retourne un libellé simple selon le niveau de missing."""
    if colonne_absente:
        return "Colonne absente"
    if pct_missing == 0:
        return "OK"
    if pct_missing <= seuil_acceptable:
        return "Acceptable"
    if pct_missing <= seuil_surveillance:
        return "A surveiller"
    return "Prioritaire"


def _normaliser_nom_cle(colonne: str) -> str:
    texte = unicodedata.normalize("NFKD", str(colonne))
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return texte.strip().casefold()


def _resoudre_nom_colonne_specification(
    spec_df: pd.DataFrame,
    nom_attendu: str,
    *,
    obligatoire: bool = False,
) -> Optional[str]:
    colonnes_normalisees = {
        _normaliser_nom_cle(col): col
        for col in spec_df.columns
    }
    nom_resolu = colonnes_normalisees.get(_normaliser_nom_cle(nom_attendu))

    if obligatoire and nom_resolu is None:
        raise ValueError(
            f"La spécification doit contenir la colonne '{nom_attendu}'."
        )

    return nom_resolu


def analyser_missing_colonnes(
    df: pd.DataFrame,
    colonnes: Optional[Sequence[str]] = None,
    *,
    considerer_na_like: bool = True,
    seuil_acceptable: float = 5.0,
    seuil_surveillance: float = 20.0,
    observations: Optional[dict[str, str]] = None,
    arrondi: int = 2,
) -> pd.DataFrame:
    """
    Analyse les valeurs manquantes des colonnes choisies.

    Si `colonnes=None`, la fonction analyse directement toutes les colonnes
    présentes dans le DataFrame fourni.

    Retourne un DataFrame avec les colonnes :
    - Variable
    - Présence colonne
    - Total lignes
    - Renseignées
    - Manquantes
    - % missing
    - Décision / observation

    Exemples
    --------
    1) Analyse sur colonnes DHIS2 brutes :
        analyser_missing_colonnes(
            df=df_dhis2_brut,
            colonnes=["Source_alerte", "N_alerte", "N_epid"]
        )

    2) Analyse sur colonnes renommées / standardisées :
        analyser_missing_colonnes(
            df=df_final,
            colonnes=["Provenance", "Nom_complet", "Date_notification"]
        )

    3) Analyse sur toutes les colonnes du DataFrame :
        analyser_missing_colonnes(df=df_final)
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df doit être un DataFrame pandas.")

    if seuil_acceptable < 0 or seuil_surveillance < 0:
        raise ValueError("Les seuils de missing doivent être positifs.")
    if seuil_acceptable > seuil_surveillance:
        raise ValueError("seuil_acceptable ne peut pas être supérieur à seuil_surveillance.")

    observations = observations or {}
    total_lignes = len(df)

    if colonnes is None:
        colonnes_a_analyser = df.columns.tolist()
    elif isinstance(colonnes, str):
        colonnes_a_analyser = [colonnes]
    else:
        colonnes_a_analyser = list(dict.fromkeys(colonnes))

    colonnes_presentes = {col for col in colonnes_a_analyser if col in df.columns}

    resultats = []
    for colonne in colonnes_a_analyser:
        colonne_absente = colonne not in colonnes_presentes

        if colonne_absente:
            nb_manquantes = total_lignes
            nb_renseignees = 0
        else:
            serie = df[colonne]
            masque_missing = serie.map(_is_na_like) if considerer_na_like else serie.isna()
            nb_manquantes = int(masque_missing.sum())
            nb_renseignees = int(total_lignes - nb_manquantes)

        pct_missing = round((nb_manquantes / total_lignes) * 100, arrondi) if total_lignes > 0 else 0.0
        decision = _decision_missing(
            pct_missing,
            colonne_absente=colonne_absente,
            seuil_acceptable=seuil_acceptable,
            seuil_surveillance=seuil_surveillance,
        )

        resultats.append(
            {
                "Variable": colonne,
                "Présence colonne": "Présente" if not colonne_absente else "Absente",
                "Total lignes": total_lignes,
                "Renseignées": nb_renseignees,
                "Manquantes": nb_manquantes,
                "% missing": pct_missing,
                "Décision / observation": observations.get(colonne, decision),
            }
        )

    resultat = pd.DataFrame(resultats)
    logger.info(
        "Analyse missing colonnes terminée : %s colonne(s) suivie(s), %s ligne(s).",
        len(resultat),
        total_lignes,
    )
    return resultat


def analyser_missing_colonnes_modele(
    df: pd.DataFrame,
    specification: pd.DataFrame | Sequence[dict[str, Any]],
    *,
    colonne_variable: str = "Variable clé",
    colonne_bloc: str = "Bloc",
    colonne_priorite: str = "Priorité",
    colonne_type_variable: str = "Type variable",
    colonne_source: str = "Colonne source",
    considerer_na_like: bool = True,
    seuil_acceptable: float = 5.0,
    seuil_surveillance: float = 20.0,
    arrondi: int = 2,
) -> pd.DataFrame:
    """
    Analyse le missing à partir d'une table de spécification de colonnes.

    La spécification peut être :
    - un DataFrame
    - une liste de dictionnaires

    Colonnes attendues au minimum :
    - `colonne_variable` (par défaut "Variable clé")

    Colonnes facultatives conservées si présentes :
    - `colonne_bloc`
    - `colonne_priorite`
    - `colonne_type_variable`
    - `colonne_source`
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df doit être un DataFrame pandas.")

    if isinstance(specification, pd.DataFrame):
        spec_df = specification.copy()
    else:
        spec_df = pd.DataFrame(list(specification))

    if spec_df.empty:
        raise ValueError("La spécification des colonnes ne peut pas être vide.")

    colonne_variable_resolue = _resoudre_nom_colonne_specification(
        spec_df,
        colonne_variable,
        obligatoire=True,
    )
    colonne_bloc_resolue = _resoudre_nom_colonne_specification(spec_df, colonne_bloc)
    colonne_priorite_resolue = _resoudre_nom_colonne_specification(spec_df, colonne_priorite)
    colonne_type_variable_resolue = _resoudre_nom_colonne_specification(spec_df, colonne_type_variable)
    colonne_source_resolue = _resoudre_nom_colonne_specification(spec_df, colonne_source)

    colonnes_a_suivre = (
        spec_df[colonne_variable_resolue]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )
    if not colonnes_a_suivre:
        raise ValueError("Aucune variable valide trouvée dans la spécification.")

    base_missing = analyser_missing_colonnes(
        df=df,
        colonnes=colonnes_a_suivre,
        considerer_na_like=considerer_na_like,
        seuil_acceptable=seuil_acceptable,
        seuil_surveillance=seuil_surveillance,
        arrondi=arrondi,
    )

    spec_df = spec_df.copy()
    spec_df[colonne_variable_resolue] = (
        spec_df[colonne_variable_resolue]
        .astype("string")
        .str.strip()
    )

    resultat = spec_df.merge(
        base_missing,
        how="left",
        left_on=colonne_variable_resolue,
        right_on="Variable",
    )

    resultat["Présence colonne"] = resultat[colonne_variable_resolue].map(
        lambda col: "Présente" if col in df.columns else "Absente"
    )

    colonnes_ordre = [
        col for col in [
            colonne_bloc_resolue,
            colonne_priorite_resolue,
            colonne_variable_resolue,
            colonne_type_variable_resolue,
        ]
        if col in resultat.columns
    ]
    colonnes_ordre.extend(
        [
            "Présence colonne",
            colonne_source_resolue,
            "Total lignes",
            "Renseignées",
            "Manquantes",
            "% missing",
            "Décision / observation",
        ]
    )

    colonnes_ordre = [col for col in colonnes_ordre if col in resultat.columns]
    return resultat[colonnes_ordre].copy()


def analyser_valeurs_manquantes_colonnes(
    df: pd.DataFrame,
    colonnes: Optional[Sequence[str]] = None,
    **kwargs,
) -> pd.DataFrame:
    """Alias francophone de `analyser_missing_colonnes`."""
    return analyser_missing_colonnes(df=df, colonnes=colonnes, **kwargs)


def analyser_valeurs_manquantes_colonnes_modele(
    df: pd.DataFrame,
    specification: pd.DataFrame | Sequence[dict[str, Any]],
    **kwargs,
) -> pd.DataFrame:
    """Alias francophone de `analyser_missing_colonnes_modele`."""
    return analyser_missing_colonnes_modele(df=df, specification=specification, **kwargs)
