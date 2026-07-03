# -*- coding: utf-8 -*-
# credit_app/colonne_valeur/colonne_fusion.py

# Notice : Pour la fusion des colonnes de df

import pandas as pd
import logging
from Levenshtein import ratio
from credit_app.colonne_valeur.colonne_nettoyage import verifier_colonnes
import os
from typing import List, Union
from rapidfuzz import process, fuzz
from typing import Optional, Callable, List


logger = logging.getLogger(__name__)

# Fusionner les colonnes 
def fusionner_ligne(
    df_cols: pd.DataFrame,
    type_fusion: str = "concat",
    separateur: str = " "
) -> pd.Series:
    """
    Fusionne les valeurs d'une ligne selon une logique définie.

    type_fusion:
      - "concat" : concatène toutes les valeurs non vides
      - "first_non_null" : retourne la première valeur non vide

    Gère proprement :
    - NaN / None / <NA>
    - chaînes vides
    - espaces multiples

    Returns:
        pd.Series
    """

    if type_fusion == "concat":
        return df_cols.apply(
            lambda row: separateur.join(
                v.strip()
                for v in row.astype("string")
                if pd.notna(v) and v.strip()
            ),
            axis=1
        ).replace("", pd.NA)

    elif type_fusion == "first_non_null":
        return df_cols.apply(
            lambda row: next(
                (v for v in row if pd.notna(v) and str(v).strip()),
                pd.NA
            ),
            axis=1
        )

    else:
        raise ValueError("type_fusion doit être 'concat' ou 'first_non_null'")

# Fonction générique pour fusionner des colonnes similaires ou des groupes de colonnes
def fusionner_colonnes_similaires_ou_groupes(
    df: pd.DataFrame,
    method: str = "similarity",
    groupes_colonnes: dict = None,
    type_fusion: str = "concat",
    seuil_similarite: float = 0.9,
    separateur: str = ' ',
    drop: bool = True
) -> pd.DataFrame:
    """
    Fonction générique pour fusionner des colonnes :
    - Soit en utilisant des groupes définis manuellement ("manual")
    - Soit en détectant les colonnes similaires automatiquement ("similarity")

    Args:
        df (pd.DataFrame): Le DataFrame d'entrée.
        method (str): Méthode pour identifier les colonnes à fusionner :
            - "manual" : utiliser un dictionnaire explicite via `groupes_colonnes`
            - "similarity" : détecter automatiquement les colonnes similaires
        groupes_colonnes (dict, optional): Dictionnaire de regroupement si method="manual".
            Exemple:
                colonnes_age = ['Age', 'Âge', 'age_en_annees']
                colonnes_identite = ['Nom', 'Prenom', 'Nom complet']
                colonnes_sexe = ['Sexe', 'Genre']
                groupes_colonnes = {
                    'age': colonnes_age,
                    'identite': colonnes_identite,
                    'sexe': colonnes_sexe
                }
        type_fusion (str): Type de fusion à appliquer :
            - "concat" : concatène les valeurs ligne par ligne
            - "first_non_null" : prend la première valeur non vide
        seuil_similarite (float): Seuil de similarité pour mode "similarity".
        separateur (str): Séparateur utilisé pour concaténation si "concat".
        drop (bool): Supprimer les colonnes fusionnées après fusion.

    Returns:
        pd.DataFrame: DataFrame avec colonnes fusionnées.
    """
    # --- Corps de la fonction ici ---

    df_result = df.copy()

    if method == "similarity":
        colonnes = list(df_result.columns)
        deja_vus = set()
        groupes = []

        for i, col1 in enumerate(colonnes):
            if i in deja_vus:
                continue
            groupe = [i]
            for j, col2 in enumerate(colonnes[i + 1:], start=i + 1):
                if j not in deja_vus and ratio(str(col1).lower(), str(col2).lower()) >= seuil_similarite:
                    groupe.append(j)
            if len(groupe) > 1:
                groupes.append(groupe)
                deja_vus.update(groupe)

        if groupes:
            nb_colonnes_initiales = len(colonnes)
            index_a_supprimer = set()

            for groupe in groupes:
                noms_groupe = [colonnes[idx] for idx in groupe]
                nom_col_fusion = noms_groupe[0] + "_fusion"
                df_result[nom_col_fusion] = fusionner_ligne(df_result.iloc[:, groupe], type_fusion, separateur)
                logger.warning(f"[Fusion - similarity] {noms_groupe} => {nom_col_fusion}")
                if drop:
                    index_a_supprimer.update(groupe)

            if drop and index_a_supprimer:
                positions_originales = [
                    idx for idx in range(nb_colonnes_initiales)
                    if idx not in index_a_supprimer
                ]
                positions_fusion = list(range(nb_colonnes_initiales, df_result.shape[1]))
                df_result = df_result.iloc[:, positions_originales + positions_fusion]

    elif method == "manual":
        if not groupes_colonnes:
            raise ValueError("Le paramètre groupes_colonnes est requis pour le mode 'manual'.")

        for nom_fusion, colonnes in groupes_colonnes.items():
            # Vérification explicite des colonnes
            verifier_colonnes(df_result, colonnes,afficher="manquantes")

            nom_col_fusion = nom_fusion + "_fusion"
            colonnes_valides = [col for col in colonnes if col in df_result.columns]

            if len(colonnes_valides) < 2:
                logger.warning(f"[Fusion ignorée] Moins de 2 colonnes valides pour '{nom_fusion}'")
                continue

            df_result[nom_col_fusion] = fusionner_ligne(
                df_result[colonnes_valides], type_fusion, separateur
            )
            logger.warning(f"[Fusion - manual] {colonnes_valides} => {nom_col_fusion}")

            if drop:
                df_result.drop(columns=colonnes_valides, inplace=True)

    else:
        raise ValueError("method doit être 'similarity' ou 'manual'.")

    # Supprimer suffixe '_fusion' des colonnes fusionnées pour nettoyage final
    colonnes_fusion = [col for col in df_result.columns if col.endswith("_fusion")]
    if colonnes_fusion:
        renommage = {col: col[:-7] for col in colonnes_fusion}  # len("_fusion") == 7
        df_result.rename(columns=renommage, inplace=True)
        logger.info(f"[Renommage] Colonnes fusionnées renommées : {renommage}")

    return df_result


def fusionner_fichiers_par_jointure(
    fichiers: List[Union[str, pd.DataFrame]],
    on: Union[str, List[str]] = None,
    how: str = "inner",
    suffixes: tuple = ("_gauche", "_droite"),
    avec_source: bool = False
) -> pd.DataFrame:
    """
    Fusionne plusieurs fichiers (ou DataFrames) par jointure sur une ou plusieurs colonnes.

    Args:
        fichiers (List[Union[str, pd.DataFrame]]): Liste de chemins ou de DataFrames.
        on (str or List[str]): Nom(s) des colonnes sur lesquelles faire la jointure.
        how (str): Type de jointure : "inner", "outer", "left", "right".
        suffixes (tuple): Suffixes pour les colonnes dupliquées.
        avec_source (bool): Ajouter une colonne de provenance pour chaque DataFrame (utile pour debug).

    Returns:
        pd.DataFrame: Résultat de la jointure progressive.
    """

    if not fichiers or len(fichiers) < 2:
        raise ValueError("Il faut au moins deux fichiers pour une jointure.")

    def charger_fichier(fichier, index):
        if isinstance(fichier, pd.DataFrame):
            df = fichier.copy()
        elif isinstance(fichier, str):
            if not os.path.exists(fichier):
                raise FileNotFoundError(f"Fichier introuvable : {fichier}")
            ext = os.path.splitext(fichier)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(fichier)
            elif ext in [".xls", ".xlsx"]:
                df = pd.read_excel(fichier)
            else:
                raise ValueError(f"Format non supporté : {fichier}")
        else:
            raise TypeError(f"Type non supporté : {type(fichier)}")

        if avec_source:
            df["Source"] = f"df_{index}"

        return df

    # Charger les fichiers
    df_liste = []
    for i, f in enumerate(fichiers):
        try:
            df_liste.append(charger_fichier(f, i))
        except Exception as e:
            logger.error(f"Erreur lors du chargement du fichier {i}: {e}")
            continue

    if len(df_liste) < 2:
        raise ValueError("Moins de deux fichiers valides chargés pour fusion.")

    # Faire la jointure progressive
    df_final = df_liste[0]
    for i in range(1, len(df_liste)):
        logger.info(f"[Jointure] df_0 avec df_{i} sur {on}, type={how}")
        try:
            df_final = df_final.merge(
                df_liste[i],
                on=on,
                how=how,
                suffixes=suffixes
            )
        except Exception as e:
            logger.error(f"Erreur lors de la jointure avec df_{i} : {e}")
            raise

    logger.info(f"[Fusion réussie] {len(df_liste)} fichiers fusionnés par jointure.")
    return df_final

def fusionner_fichiers_par_jointure_avance(
    fichiers: List[Union[str, pd.DataFrame]],
    on: Union[str, List[str]],
    how: str = "inner",
    suffixes: tuple = ("_gauche", "_droite"),
    avec_source: bool = False,
    seuil_approx: int = 100
) -> pd.DataFrame:
    """
    Fusionne plusieurs fichiers (ou DataFrames) par jointure exacte ou approximative.
    
    Cette fonction est construite sur le modèle de `nettoyer_colonnes`, avec :
    - une structure claire et commentée
    - des contrôles robustes
    - une logique étape par étape
    - des logs explicites pour chaque fusion

    Paramètres
    ----------
    fichiers : list[str | pd.DataFrame]
        Liste de chemins de fichiers Excel/CSV ou de DataFrames à fusionner.
    on : str | list[str]
        Nom(s) des colonnes clés pour la jointure.
    how : str, par défaut "inner"
        Type de jointure ("inner", "outer", "left", "right").
    suffixes : tuple, par défaut ("_gauche", "_droite")
        Suffixes appliqués aux colonnes dupliquées.
    avec_source : bool, par défaut False
        Si True, ajoute une colonne indiquant la provenance de chaque fichier.
    seuil_approx : int, par défaut 100
        Pourcentage de similarité minimal pour les jointures approximatives (0–100).
        100 = jointure exacte.

    Retour
    ------
    pd.DataFrame
        DataFrame résultant de la jointure progressive de tous les fichiers.
    """

    # -------------------------------
    # 1️⃣ Validation des entrées
    # -------------------------------
    if not fichiers or len(fichiers) < 2:
        raise ValueError("⚠️ Il faut au moins deux fichiers ou DataFrames pour une jointure.")

    cols_on = [on] if isinstance(on, str) else list(on)
    if not cols_on:
        raise ValueError("⚠️ Vous devez spécifier au moins une colonne de jointure via le paramètre 'on'.")

    if seuil_approx < 0 or seuil_approx > 100:
        raise ValueError("⚠️ Le seuil_approx doit être compris entre 0 et 100.")

    # -------------------------------
    # 2️⃣ Chargement des fichiers
    # -------------------------------
    def charger_fichier(fichier, index):
        """Charge un fichier CSV ou Excel, ou retourne le DataFrame."""
        if isinstance(fichier, pd.DataFrame):
            df = fichier.copy()
        elif isinstance(fichier, str):
            if not os.path.exists(fichier):
                raise FileNotFoundError(f"Fichier introuvable : {fichier}")
            ext = os.path.splitext(fichier)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(fichier)
            elif ext in [".xls", ".xlsx"]:
                df = pd.read_excel(fichier)
            else:
                raise ValueError(f"Format non supporté : {fichier}")
        else:
            raise TypeError(f"Type non supporté : {type(fichier)}")

        if avec_source:
            df["Source"] = f"df_{index}"

        return df

    df_liste = []
    for i, f in enumerate(fichiers):
        try:
            df_liste.append(charger_fichier(f, i))
        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement du fichier {i}: {e}")
            continue

    if len(df_liste) < 2:
        raise ValueError("⚠️ Moins de deux fichiers valides chargés pour la fusion.")

    # -------------------------------
    # 3️⃣ Fonction de jointure approximative
    # -------------------------------
    def approx_merge(df1, df2, cols, seuil):
        """Jointure approximative basée sur RapidFuzz."""
        df1_copy = df1.copy()
        df2_copy = df2.copy()

        for col in cols:
            if col not in df1_copy.columns or col not in df2_copy.columns:
                logger.warning(f"⚠️ Colonne manquante pour jointure approximative : {col}")
                continue

            def trouver_match(val):
                if pd.isna(val):
                    return None
                match = process.extractOne(val, df2_copy[col].dropna().unique(), scorer=fuzz.token_sort_ratio)
                return match[0] if match and match[1] >= seuil else None

            df1_copy[col + "_match"] = df1_copy[col].apply(trouver_match)

        merge_cols = [c + "_match" for c in cols]
        df_merged = df1_copy.merge(df2_copy, left_on=merge_cols, right_on=cols, how=how, suffixes=suffixes)
        df_merged.drop(columns=merge_cols, inplace=True, errors="ignore")
        return df_merged

    # -------------------------------
    # 4️⃣ Fusion progressive
    # -------------------------------
    df_final = df_liste[0]

    for i, df_next in enumerate(df_liste[1:], start=1):
        logger.info(f"🔄 Fusion en cours : df_0 ↔ df_{i} | colonnes={cols_on} | how={how} | seuil={seuil_approx}%")
        try:
            if seuil_approx == 100:
                df_final = df_final.merge(df_next, on=cols_on, how=how, suffixes=suffixes)
            else:
                df_final = approx_merge(df_final, df_next, cols_on, seuil_approx)
        except Exception as e:
            logger.error(f"❌ Erreur lors de la fusion df_0 ↔ df_{i}: {e}")

    logger.info(f"✅ Fusion réussie : {len(df_liste)} fichiers fusionnés avec how='{how}' et seuil={seuil_approx}%")
    return df_final

# Fusion des compilés
from typing import Optional, Callable, List
import logging
import pandas as pd
import inspect


def construire_df_final(
    df_clean: Optional[pd.DataFrame] = None,
    df_compile: Optional[pd.DataFrame] = None,
    fusionner_func: Optional[Callable[[List[pd.DataFrame]], pd.DataFrame]] = None,
) -> pd.DataFrame:
    """
    Construit le DataFrame final à partir de deux sources possibles :
    une base nettoyée (df_clean) et une base compilée (df_compile).

    Logique :
    - si df_clean est présent et non vide, et df_compile est présent et non vide :
        → fusion des deux via `fusionner_func([df_clean, df_compile])`
    - si df_clean est présent et non vide, mais df_compile est absent ou vide :
        → df_final = copie de df_clean
    - si df_compile est présent et non vide, mais df_clean est absent ou vide :
        → df_final = copie de df_compile
    - si les deux sont absents ou vides :
        → df_final = DataFrame vide
    """
    df_clean_exists = isinstance(df_clean, pd.DataFrame) and not df_clean.empty
    df_compile_exists = isinstance(df_compile, pd.DataFrame) and not df_compile.empty

    if df_clean_exists and df_compile_exists:
        if fusionner_func is None:
            raise ValueError(
                "Vous devez fournir `fusionner_func` pour fusionner les deux DataFrames "
                "lorsque df_clean et df_compile sont tous les deux disponibles."
            )
        df_final = fusionner_func([df_clean, df_compile])
        logger.info("Fusion de df_clean et df_compile → df_final (2 sources).")

    elif df_clean_exists and not df_compile_exists:
        df_final = df_clean.copy()
        logger.info("Seul df_clean est disponible → df_final = df_clean.")

    elif df_compile_exists and not df_clean_exists:
        df_final = df_compile.copy()
        logger.info("Seul df_compile est disponible → df_final = df_compile.")

    else:
        df_final = pd.DataFrame()
        logger.info(
            "Ni df_clean ni df_compile ne sont disponibles ou contiennent des données. "
            "df_final est un DataFrame vide."
        )

    return df_final


def construire_df_final_depuis_noms(
    df_clean_name: str = "df_clean_2025",
    df_compile_name: str = "df_compile",
    fusionner_func: Optional[Callable[[List[pd.DataFrame]], pd.DataFrame]] = None,
) -> pd.DataFrame:
    """
    Variante pratique de `construire_df_final` qui récupère les DataFrames
    à partir de leurs noms dans l'environnement de l'appelant (notebook ou script).

    Au lieu d'utiliser globals() du module (qui ne voit pas les variables du notebook),
    on utilise le frame appelant via `inspect`.

    Logique :
    - lit `df_clean_name` et `df_compile_name` dans les variables de l'appelant
      (locals puis globals)
    - délègue la logique métier à `construire_df_final`

    Paramètres
    ----------
    df_clean_name : str, défaut "df_clean_2025"
        Nom de la variable correspondant au DataFrame « propre » chez l'appelant.
    df_compile_name : str, défaut "df_compile"
        Nom de la variable correspondant au DataFrame compilé chez l'appelant.
    fusionner_func : Optional[Callable[[List[pd.DataFrame]], pd.DataFrame]], défaut None
        Fonction utilisée pour fusionner les deux DataFrames lorsqu'ils sont présents.

    Retour
    ------
    pd.DataFrame
        Le DataFrame final construit selon la logique de `construire_df_final`.
    """
    # Récupérer le frame de l'appelant (là où tu appelles la fonction)
    caller_frame = inspect.currentframe().f_back
    caller_locals = caller_frame.f_locals
    caller_globals = caller_frame.f_globals

    # Chercher d'abord dans locals(), puis dans globals() de l'appelant
    df_clean = caller_locals.get(df_clean_name, caller_globals.get(df_clean_name, None))
    df_compile = caller_locals.get(df_compile_name, caller_globals.get(df_compile_name, None))

    return construire_df_final(
        df_clean=df_clean,
        df_compile=df_compile,
        fusionner_func=fusionner_func,
    )
