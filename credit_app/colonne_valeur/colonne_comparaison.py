# -*- coding: utf-8 -*-
# colonne_valeur/colonne_comparaison.py

# Notice : Des fonctions rapides pour comparer des valeurs des colonnes du df

import pandas as pd
import re
import logging
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Dict, Union, Optional
import numpy as np

try:
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover - fallback environnemental
    fuzz = None
    process = None

logger = logging.getLogger(__name__)


def _nettoyer_cle_comparaison(valeur):
    """Normalise une clé de comparaison pour les jointures exactes."""
    if pd.isnull(valeur):
        return pd.NA
    valeur = re.sub(r"[-_\s]+", "", str(valeur)).upper()
    return valeur if valeur else pd.NA


def _charger_dataframe_comparaison(
    source: Union[str, Path, pd.DataFrame],
    feuille: Optional[Union[str, int]] = 0,
) -> pd.DataFrame:
    """
    Charge un DataFrame depuis un DataFrame existant, un Excel ou un CSV.
    """
    if isinstance(source, pd.DataFrame):
        return source.copy()

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls", ".xlsm"}:
        return pd.read_excel(path, sheet_name=feuille)
    if suffix == ".csv":
        return pd.read_csv(path)

    raise ValueError(
        f"Format non supporté pour la comparaison : {path.suffix}. "
        "Utilise un fichier Excel, CSV, ou un DataFrame."
    )


def _extraire_valeur_dict(donnees: Dict, *cles_possibles, default=None):
    """Récupère la première clé disponible dans un dictionnaire."""
    for cle in cles_possibles:
        if cle in donnees:
            return donnees[cle]
    return default


# --- Comparaison des colonnes ---
def comparer_colonnes_generique(
    df1: pd.DataFrame,
    colonnes_df1: Union[str, List[str]],
    df2: pd.DataFrame,
    colonnes_df2: Union[str, List[str]],
    verbose: bool = True,
    nettoyer: bool = True,
    seuil_similarite: float = 1.0  # 1.0 = égalité stricte
) -> Dict[str, List]:
    """
    Compare des colonnes (ou clés composites) entre deux DataFrames,
    avec nettoyage optionnel.
    Ajout d’un seuil de similarité pour comparaison si seuil < 1.

    Args:
        df1 (pd.DataFrame): Premier DataFrame.
        colonnes_df1 (str ou List[str]): Colonnes à comparer dans df1.
        df2 (pd.DataFrame): Deuxième DataFrame.
        colonnes_df2 (str ou List[str]): Colonnes à comparer dans df2.
        verbose (bool): Active les logs.
        nettoyer (bool): Appliquer nettoyage ou comparer "brut".
        seuil_similarite (float): Seuil de similarité [0-1]. 1 = égalité stricte.

    Returns:
        Dict[str, List]: Dictionnaire avec clés :
            - 'commun' : valeurs ou tuples communs (fuzzy si seuil < 1)
            - 'uniquement_dans_df1' : présents uniquement dans df1
            - 'uniquement_dans_df2' : présents uniquement dans df2
    """

    def nettoyer_texte(valeur):
        if pd.isnull(valeur):
            return None
        return re.sub(r"[-_\s]+", "", str(valeur)).upper()

    # Uniformiser en liste
    if isinstance(colonnes_df1, str):
        colonnes_df1 = [colonnes_df1]
    if isinstance(colonnes_df2, str):
        colonnes_df2 = [colonnes_df2]

    if verbose:
        mode = "nettoyé" if nettoyer else "brut"
        logger.info(f"Traitement {mode} des colonnes {colonnes_df1} du premier DataFrame...")

    def preparer_valeur(row, colonnes):
        valeurs = tuple(row[col] for col in colonnes)
        if nettoyer:
            nettoyes = tuple(nettoyer_texte(v) for v in valeurs)
            if None in nettoyes:
                return None
            return nettoyes if len(nettoyes) > 1 else nettoyes[0]
        else:
            if None in valeurs:
                return None
            return valeurs if len(valeurs) > 1 else valeurs[0]

    # Préparer sets si seuil == 1 (égalité stricte)
    if seuil_similarite == 1.0:
        set1 = set(
            val for val in (
                preparer_valeur(row, colonnes_df1)
                for _, row in df1.dropna(subset=colonnes_df1).iterrows()
            ) if val is not None
        )

        if verbose:
            logger.info(f"Traitement {mode} des colonnes {colonnes_df2} du deuxième DataFrame...")

        set2 = set(
            val for val in (
                preparer_valeur(row, colonnes_df2)
                for _, row in df2.dropna(subset=colonnes_df2).iterrows()
            ) if val is not None
        )

        if verbose:
            logger.info(f"Comparaison stricte des valeurs entre {colonnes_df1} et {colonnes_df2}...")

        commun = set1 & set2
        uniquement_dans_df1 = set1 - set2
        uniquement_dans_df2 = set2 - set1

        if verbose:
            logger.info(f"Valeurs communes : {len(commun)}")
            logger.info(f"Uniquement dans le premier DataFrame : {len(uniquement_dans_df1)}")
            logger.info(f"Uniquement dans le deuxième DataFrame : {len(uniquement_dans_df2)}")

        return {
            "Valeurs communes ": sorted(commun),
            "Uniquement dans le premier DataFrame ": sorted(uniquement_dans_df1),
            "Uniquement dans le deuxième DataFrame": sorted(uniquement_dans_df2),
        }

    # Sinon, fuzzy matching avec rapidfuzz
    else:
        if fuzz is None or process is None:
            raise ImportError(
                "rapidfuzz est requis pour les comparaisons floues "
                "(seuil_similarite < 1.0)."
            )

        seuil_100 = int(seuil_similarite * 100)

        valeurs_df2 = {
            preparer_valeur(row, colonnes_df2)
            for _, row in df2.dropna(subset=colonnes_df2).iterrows()
            if preparer_valeur(row, colonnes_df2) is not None
        }

        if verbose:
            logger.info(f"Recherche fuzzy sur {len(valeurs_df2)} valeurs dans df2 avec seuil {seuil_similarite}")

        commun = []
        uniquement_dans_df1 = []

        for _, row in df1.dropna(subset=colonnes_df1).iterrows():
            val1 = preparer_valeur(row, colonnes_df1)
            if val1 is None:
                continue
            resultat = process.extractOne(
                val1, valeurs_df2, scorer=fuzz.ratio, score_cutoff=seuil_100
            )
            if resultat is None:
                uniquement_dans_df1.append(val1)
            else:
                val2, score, _ = resultat
                commun.append(val1)

        # Trouver uniquement_dans_df2 (valeurs de df2 sans match dans df1)
        valeurs_df1 = {
            preparer_valeur(row, colonnes_df1)
            for _, row in df1.dropna(subset=colonnes_df1).iterrows()
            if preparer_valeur(row, colonnes_df1) is not None
        }

        uniquement_dans_df2 = [
            val2 for val2 in valeurs_df2
            if all(
                fuzz.ratio(val2, val1) < seuil_100
                for val1 in valeurs_df1
            )
        ]

        if verbose:
            logger.info(f"Valeurs communes fuzzy : {len(commun)}")
            logger.info(f"Uniquement dans df1 (fuzzy) : {len(uniquement_dans_df1)}")
            logger.info(f"Uniquement dans df2 (fuzzy) : {len(uniquement_dans_df2)}")

        return {
            "commun": sorted(commun),
            "uniquement_dans_df1": sorted(uniquement_dans_df1),
            "uniquement_dans_df2": sorted(uniquement_dans_df2),
        }
        
# Comparaison en ajoutant RechercheV de Excel
# Pour un affichage propre dans Jupyter / VSCode Notebook
try:
    from IPython.display import display
except ImportError:
    display = print

def associer_colonnes_generique(
    df_sans: pd.DataFrame,
    df_avec: pd.DataFrame,
    col_nom_sans: str = "Nom",
    col_reference: str = "Nom",
    col_resultat: Union[str, List[str]] = "N_Epid",
    seuil: int = 80,
    afficher: bool = True,
    export_excel: Union[str, None, bool] = False,
    logger: Union[logging.Logger, None, bool] = False,
    fusion: bool = False
) -> pd.DataFrame:
    """
        Associe de façon floue les valeurs d'une colonne d'un DataFrame « source »
        (ex. noms sans N_Epid) à une colonne d'un DataFrame de « référence »
        (ex. noms avec N_Epid), puis récupère une ou plusieurs colonnes associées
        à la meilleure correspondance trouvée.

        La comparaison est effectuée avec RapidFuzz (similarité de chaînes), et
        seules les correspondances dont le score est supérieur ou égal à `seuil`
        sont conservées.

        Paramètres
        ----------
        df_sans : pd.DataFrame
            DataFrame contenant les valeurs à associer (ex. liste de noms sans identifiant).
        df_avec : pd.DataFrame
            DataFrame de référence contenant la colonne de comparaison et les colonnes
            à récupérer (ex. noms + N_Epid).
        col_nom_sans : str, par défaut "Nom"
            Nom de la colonne dans `df_sans` contenant les valeurs à rapprocher
            (valeurs « brutes » à associer).
        col_reference : str, par défaut "Nom"
            Nom de la colonne dans `df_avec` utilisée comme référence pour la
            comparaison floue.
        col_resultat : str ou List[str], par défaut "N_Epid"
            Nom ou liste de noms de colonnes de `df_avec` à récupérer pour chaque
            correspondance trouvée (ex. identifiant épidémiologique, code ZS, etc.).
        seuil : int, par défaut 80
            Score minimal de similarité (0–100) pour accepter une correspondance.
        afficher : bool, par défaut True
            Si True, affiche le DataFrame résultat (ou `df_sans` en cas de fusion)
            avec `display()` (pratique en notebook).
        export_excel : str, None ou bool, par défaut False
            - str  : chemin de fichier vers lequel exporter le résultat en Excel.
            - False/None : aucun export n'est effectué.
        logger : logging.Logger, None ou bool, par défaut False
            - logging.Logger : logger existant utilisé pour écrire les messages.
            - False ou None  : désactive complètement les logs (niveau CRITICAL).
        fusion : bool, par défaut False
            - False : renvoie un DataFrame d'association indépendant.
            - True  : fusionne les colonnes résultantes dans `df_sans` sous la forme
            `"{col_resultat}_associe"` et renvoie `df_sans` enrichi.

        Retour
        ------
        pd.DataFrame
            - Si `fusion=False` :
                DataFrame avec au minimum les colonnes :
                ['Valeur_source', 'Valeur_associee', '%_Approximation', ...col_resultat...]
            - Si `fusion=True` :
                `df_sans` d'origine, enrichi avec les colonnes associées
                (une colonne par élément de `col_resultat` suffixée par `_associe`).

        Remarques
        ---------
        - Les valeurs manquantes dans les colonnes utilisées pour la comparaison sont
        ignorées.
        - Si aucune valeur valide n'est trouvée dans la colonne de référence,
        la fonction lève une ValueError.
        - En cas d'erreur ponctuelle sur une valeur (exception RapidFuzz, etc.),
        la valeur est ignorée et, si un logger est actif, un warning est enregistré.
        """

    # --- Vérification des colonnes ---
    if fuzz is None or process is None:
        raise ImportError("rapidfuzz est requis pour associer des colonnes de façon floue.")

    for df, col in [(df_sans, col_nom_sans), (df_avec, col_reference)]:
        if col not in df.columns:
            raise ValueError(f"❌ Colonne '{col}' introuvable dans le DataFrame correspondant.")

    if isinstance(col_resultat, str):
        col_resultat = [col_resultat]

    for col in col_resultat:
        if col not in df_avec.columns:
            raise ValueError(f"❌ Colonne résultat '{col}' introuvable dans df_avec.")

    # --- Initialisation du logger (désactivé si False ou None) ---
    active_log = isinstance(logger, logging.Logger)
    if active_log:
        log = logger
    else:
        log = logging.getLogger(__name__)
        log.setLevel(logging.CRITICAL)  # désactive les logs par défaut

    # --- Préparation des listes ---
    liste_reference = df_avec[col_reference].dropna().astype(str).tolist()
    if not liste_reference:
        raise ValueError(f"⚠️ Aucune valeur valide trouvée dans '{col_reference}' du DataFrame de référence.")

    # --- Traitement principal ---
    resultats = []

    for valeur in df_sans[col_nom_sans].dropna().astype(str):
        match = None
        score = 0
        donnees_associees = {col: "-" for col in col_resultat}

        try:
            resultat = process.extractOne(valeur, liste_reference, scorer=fuzz.token_sort_ratio)
            if resultat:
                match, score, _ = resultat
                if score >= seuil:
                    ligne_associee = df_avec.loc[df_avec[col_reference] == match].iloc[0]
                    donnees_associees = {col: ligne_associee[col] for col in col_resultat}
        except Exception as e:
            if active_log:
                log.warning(f"Erreur lors du traitement de '{valeur}': {e}")

        resultats.append({
            "Valeur_source": valeur,
            "Valeur_associee": match if score >= seuil else "",
            "%_Approximation": score,
            **donnees_associees
        })

        if active_log:
            log.info(f"{valeur} → {match} ({score}%)")

    df_resultat = pd.DataFrame(resultats)

    # --- Export Excel ---
    if isinstance(export_excel, str):
        df_resultat.to_excel(export_excel, index=False)
        if active_log:
            log.info(f"📁 Résultat exporté vers : {export_excel}")

    # --- Fusion directe dans df_sans ---
    if fusion:
        for col in col_resultat:
            df_sans[f"{col}_associe"] = df_resultat[col].reindex(df_sans.index, fill_value="-")
        if afficher:
            display(df_sans)
        return df_sans

    # --- Affichage ---
    if afficher:
        display(df_resultat)

    return df_resultat

def associer_colonnes_generique_fast(
    df_sans: pd.DataFrame,
    df_avec: pd.DataFrame,
    col_nom_sans: str = "Nom",
    col_reference: str = "Nom",
    col_resultat: Union[str, List[str]] = "N_Epid",
    seuil: int = 80,
    afficher: bool = True,
    export_excel: Union[str, None, bool] = False,
    logger: Union[logging.Logger, None, bool] = False,
    fusion: bool = False
) -> pd.DataFrame:
    """
    Associe de façon floue les valeurs d'une colonne d'un DataFrame « source »
    (ex. noms sans N_Epid) à une colonne d'un DataFrame de « référence »
    (ex. noms avec N_Epid), puis récupère une ou plusieurs colonnes associées
    à la meilleure correspondance trouvée.

    La comparaison est effectuée avec RapidFuzz (similarité de chaînes), et
    seules les correspondances dont le score est supérieur ou égal à `seuil`
    sont conservées.

    Paramètres
    ----------
    df_sans : pd.DataFrame
        DataFrame contenant les valeurs à associer (ex. liste de noms sans identifiant).
    df_avec : pd.DataFrame
        DataFrame de référence contenant la colonne de comparaison et les colonnes
        à récupérer (ex. noms + N_Epid).
    col_nom_sans : str, par défaut "Nom"
        Nom de la colonne dans `df_sans` contenant les valeurs à rapprocher
        (valeurs « brutes » à associer).
    col_reference : str, par défaut "Nom"
        Nom de la colonne dans `df_avec` utilisée comme référence pour la
        comparaison floue.
    col_resultat : str ou List[str], par défaut "N_Epid"
        Nom ou liste de noms de colonnes de `df_avec` à récupérer pour chaque
        correspondance trouvée (ex. identifiant épidémiologique, code ZS, etc.).
    seuil : int, par défaut 80
        Score minimal de similarité (0–100) pour accepter une correspondance.
    afficher : bool, par défaut True
        Si True, affiche le DataFrame résultat (ou `df_sans` en cas de fusion)
        avec `display()` (pratique en notebook).
    export_excel : str, None ou bool, par défaut False
        - str  : chemin de fichier vers lequel exporter le résultat en Excel.
        - False/None : aucun export n'est effectué.
    logger : logging.Logger, None ou bool, par défaut False
        - logging.Logger : logger existant utilisé pour écrire les messages.
        - False ou None  : désactive complètement les logs (niveau CRITICAL).
    fusion : bool, par défaut False
        - False : renvoie un DataFrame d'association indépendant.
        - True  : fusionne les colonnes résultantes dans `df_sans` sous la forme
          `"{col_resultat}_associe"` et renvoie `df_sans` enrichi.

    Retour
    ------
    pd.DataFrame
        - Si `fusion=False` :
            DataFrame avec au minimum les colonnes :
            ['Valeur_source', 'Valeur_associee', '%_Approximation', ...col_resultat...]
        - Si `fusion=True` :
            `df_sans` d'origine, enrichi avec les colonnes associées
            (une colonne par élément de `col_resultat` suffixée par `_associe`).

    Remarques
    ---------
    - Les valeurs manquantes dans les colonnes utilisées pour la comparaison sont
      ignorées.
    - Si aucune valeur valide n'est trouvée dans la colonne de référence,
      la fonction lève une ValueError.
    - En cas d'erreur ponctuelle sur une valeur (exception RapidFuzz, etc.),
      la valeur est ignorée et, si un logger est actif, un warning est enregistré.
    """

    # --- Vérifications ---
    for df, col in [(df_sans, col_nom_sans), (df_avec, col_reference)]:
        if col not in df.columns:
            raise ValueError(f"❌ Colonne '{col}' introuvable.")

    if isinstance(col_resultat, str):
        col_resultat = [col_resultat]

    for col in col_resultat:
        if col not in df_avec.columns:
            raise ValueError(f"❌ Colonne résultat '{col}' introuvable dans df_avec.")

    # --- Logger (désactivé si False/None) ---
    active_log = isinstance(logger, logging.Logger)
    if active_log:
        log = logger
    else:
        log = logging.getLogger(__name__)
        log.setLevel(logging.CRITICAL)

    # --- Préparation des listes ---
    valeurs_sans = df_sans[col_nom_sans].dropna().astype(str).tolist()
    valeurs_ref = df_avec[col_reference].dropna().astype(str).tolist()

    if not valeurs_ref:
        raise ValueError(f"⚠️ Aucune valeur valide trouvée dans '{col_reference}'.")

    # --- Calcul vectorisé des scores ---
    scores = process.cdist(valeurs_sans, valeurs_ref, scorer=fuzz.token_sort_ratio)
    max_scores = np.max(scores, axis=1)
    best_indices = np.argmax(scores, axis=1)

    # --- Construction du résultat ---
    resultats = []
    for i, valeur in enumerate(valeurs_sans):
        score = max_scores[i]
        idx = best_indices[i]
        match = valeurs_ref[idx] if score >= seuil else ""
        donnees_associees = {col: "-" for col in col_resultat}

        if score >= seuil:
            ligne_associee = df_avec.iloc[idx]
            donnees_associees = {col: ligne_associee[col] for col in col_resultat}

        resultats.append({
            "Valeur_source": valeur,
            "Valeur_associee": match,
            "%_Approximation": int(score),
            **donnees_associees
        })

        if active_log:
            log.info(f"{valeur} → {match} ({score:.1f}%)")

    df_resultat = pd.DataFrame(resultats)

    # --- Export Excel ---
    if isinstance(export_excel, str):
        df_resultat.to_excel(export_excel, index=False)
        if active_log:
            log.info(f"📁 Exporté vers : {export_excel}")

    # --- Fusion directe ---
    if fusion:
        for col in col_resultat:
            df_sans[f"{col}_associe"] = df_resultat[col].reindex(df_sans.index, fill_value="-")
        if afficher:
            display(df_sans)
        return df_sans

    if afficher:
        display(df_resultat)

    return df_resultat


def _comparer_fichiers_sur_colonne_detail(
    fichier1: Union[str, Path, pd.DataFrame],
    fichier2: Union[str, Path, pd.DataFrame],
    colonne: str = "N_epid",
    feuille1: Optional[Union[str, int]] = 0,
    feuille2: Optional[Union[str, int]] = 0,
    nettoyer: bool = True,
    export_excel: Union[str, Path, None] = None,
    prefixe_fichier1: str = "fichier1",
    prefixe_fichier2: str = "fichier2",
) -> Dict[str, Union[Dict[str, int], List, pd.DataFrame]]:
    """
    Compare deux fichiers/DataFrames sur une même colonne clé.

    Retourne :
    - un résumé des comptes
    - les clés communes / uniquement à gauche / uniquement à droite
    - les lignes communes (merge)
    - les lignes propres à chaque fichier
    """
    df1 = _charger_dataframe_comparaison(fichier1, feuille1)
    df2 = _charger_dataframe_comparaison(fichier2, feuille2)

    if colonne not in df1.columns:
        raise ValueError(f"Colonne '{colonne}' introuvable dans le premier fichier.")
    if colonne not in df2.columns:
        raise ValueError(f"Colonne '{colonne}' introuvable dans le deuxième fichier.")

    cle_temp = f"__cle_compare_{colonne}__"
    df1_cmp = df1.copy()
    df2_cmp = df2.copy()

    if nettoyer:
        df1_cmp[cle_temp] = df1_cmp[colonne].map(_nettoyer_cle_comparaison)
        df2_cmp[cle_temp] = df2_cmp[colonne].map(_nettoyer_cle_comparaison)
    else:
        df1_cmp[cle_temp] = df1_cmp[colonne]
        df2_cmp[cle_temp] = df2_cmp[colonne]

    df1_cmp = df1_cmp.dropna(subset=[cle_temp])
    df2_cmp = df2_cmp.dropna(subset=[cle_temp])

    comparaison_cles = comparer_colonnes_generique(
        df1=df1_cmp,
        colonnes_df1=cle_temp,
        df2=df2_cmp,
        colonnes_df2=cle_temp,
        verbose=False,
        nettoyer=False,
        seuil_similarite=1.0,
    )

    cles_communes = _extraire_valeur_dict(
        comparaison_cles,
        "Valeurs communes ",
        "commun",
        default=[],
    )
    cles_uniques_1 = _extraire_valeur_dict(
        comparaison_cles,
        "Uniquement dans le premier DataFrame ",
        "uniquement_dans_df1",
        default=[],
    )
    cles_uniques_2 = _extraire_valeur_dict(
        comparaison_cles,
        "Uniquement dans le deuxiÃ¨me DataFrame",
        "Uniquement dans le deuxième DataFrame",
        "uniquement_dans_df2",
        default=[],
    )

    lignes_communes = df1_cmp.merge(
        df2_cmp,
        on=cle_temp,
        how="inner",
        suffixes=(f"_{prefixe_fichier1}", f"_{prefixe_fichier2}")
    )
    lignes_uniques_1 = df1_cmp[df1_cmp[cle_temp].isin(cles_uniques_1)].copy()
    lignes_uniques_2 = df2_cmp[df2_cmp[cle_temp].isin(cles_uniques_2)].copy()

    for df_tmp in (lignes_communes, lignes_uniques_1, lignes_uniques_2):
        if cle_temp in df_tmp.columns:
            df_tmp.drop(columns=[cle_temp], inplace=True)

    resume = {
        f"nb_lignes_{prefixe_fichier1}": len(df1),
        f"nb_lignes_{prefixe_fichier2}": len(df2),
        "nb_cles_communes": len(cles_communes),
        f"nb_cles_uniques_{prefixe_fichier1}": len(cles_uniques_1),
        f"nb_cles_uniques_{prefixe_fichier2}": len(cles_uniques_2),
    }

    resultat = {
        "resume": resume,
        "cles_communes": cles_communes,
        f"cles_uniques_{prefixe_fichier1}": cles_uniques_1,
        f"cles_uniques_{prefixe_fichier2}": cles_uniques_2,
        "lignes_communes": lignes_communes,
        f"lignes_uniques_{prefixe_fichier1}": lignes_uniques_1,
        f"lignes_uniques_{prefixe_fichier2}": lignes_uniques_2,
    }

    if export_excel:
        export_path = Path(export_excel)
        with pd.ExcelWriter(export_path) as writer:
            pd.DataFrame([resume]).to_excel(writer, sheet_name="resume", index=False)
            pd.DataFrame({"cle_commune": cles_communes}).to_excel(writer, sheet_name="cles_communes", index=False)
            pd.DataFrame({f"cle_unique_{prefixe_fichier1}": cles_uniques_1}).to_excel(writer, sheet_name=f"cles_uniques_{prefixe_fichier1}"[:31], index=False)
            pd.DataFrame({f"cle_unique_{prefixe_fichier2}": cles_uniques_2}).to_excel(writer, sheet_name=f"cles_uniques_{prefixe_fichier2}"[:31], index=False)
            lignes_communes.to_excel(writer, sheet_name="lignes_communes", index=False)
            lignes_uniques_1.to_excel(writer, sheet_name=f"lignes_uniques_{prefixe_fichier1}"[:31], index=False)
            lignes_uniques_2.to_excel(writer, sheet_name=f"lignes_uniques_{prefixe_fichier2}"[:31], index=False)

    return resultat


def comparer_fichiers_sur_colonne(
    df_1: Union[str, Path, pd.DataFrame],
    df_2: Union[str, Path, pd.DataFrame],
    colonne_commune: Union[str, List[str]] = "N_epid",
    Ajout_cols_df_1: Optional[Union[str, List[str]]] = None,
    Ajout_cols_df_2: Optional[Union[str, List[str]]] = None,
    nettoyer: bool = True,
    export_excel: Union[str, Path, None] = None,
    suffixe_df_1: str = "_df_1",
    suffixe_df_2: str = "_df_2",
    seuil: int = 100,
) -> pd.DataFrame:
    """
    Compare deux DataFrames ou fichiers sur une ou plusieurs colonnes communes,
    puis retourne un DataFrame d'appariement contenant les lignes correspondantes.

    Paramètres
    ----------
    df_1 : pd.DataFrame | str | Path
        Premier DataFrame, ou chemin vers un fichier Excel/CSV.
    df_2 : pd.DataFrame | str | Path
        Deuxième DataFrame, ou chemin vers un fichier Excel/CSV.
    colonne_commune : str | list[str], default="N_epid"
        Colonne unique ou liste de colonnes utilisées comme clé de comparaison.
        Si plusieurs colonnes sont fournies, une clé composite est construite.
    Ajout_cols_df_1 : str | list[str] | None, default=None
        Colonnes supplémentaires à récupérer depuis `df_1`.
        - `None` ou `[]` : toutes les colonnes de `df_1`, sauf celles de
          `colonne_commune`.
        - `str` ou `list[str]` : seules les colonnes demandées sont ajoutées.
    Ajout_cols_df_2 : str | list[str] | None, default=None
        Colonnes supplémentaires à récupérer depuis `df_2`.
        - `None` ou `[]` : toutes les colonnes de `df_2`, sauf celles de
          `colonne_commune`.
        - `str` ou `list[str]` : seules les colonnes demandées sont ajoutées.
    nettoyer : bool, default=True
        Si True, normalise les valeurs utilisées pour comparer les clés
        (espaces, tirets, underscores, casse).
    export_excel : str | Path | None, default=None
        Si renseigné, exporte le résultat final vers le chemin indiqué.
        Si `None`, aucun export n'est réalisé.
    suffixe_df_1 : str, default="_df_1"
        Suffixe appliqué aux colonnes ajoutées provenant de `df_1`.
    suffixe_df_2 : str, default="_df_2"
        Suffixe appliqué aux colonnes ajoutées provenant de `df_2`.
    seuil : int, default=100
        Seuil de similarité entre 0 et 100 appliqué à la clé de comparaison.
        - `100` : appariement strict
        - `< 100` : appariement approximatif sur la meilleure correspondance

    Retour
    ------
    pd.DataFrame
        DataFrame contenant :
        - les colonnes de `colonne_commune`
        - les colonnes demandées dans `Ajout_cols_df_1` suffixées `suffixe_df_1`
        - les colonnes demandées dans `Ajout_cols_df_2` suffixées `suffixe_df_2`

    Affichage
    ---------
    La fonction affiche à la fin un résumé d'exécution avec :
    - le nombre de lignes de `df_1` et `df_2`
    - le nombre de clés valides utilisées
    - le nombre de lignes communes trouvées
    - le seuil de comparaison utilisé
    - le chemin d'export, si fourni
    """

    def _normaliser_liste_colonnes(cols, colonnes_disponibles, colonnes_a_exclure):
        if cols is None or cols == []:
            return [col for col in colonnes_disponibles if col not in colonnes_a_exclure]
        if isinstance(cols, str):
            cols = [cols]
        return list(dict.fromkeys(cols))

    def _normaliser_colonnes_communes(cols) -> List[str]:
        if isinstance(cols, str):
            cols = [cols]
        cols = list(dict.fromkeys(cols))
        if not cols:
            raise ValueError("colonne_commune doit contenir au moins une colonne.")
        return cols

    def _creer_cle_composite(df_source: pd.DataFrame, colonnes: List[str]) -> pd.Series:
        def normaliser_valeur(valeur):
            if pd.isnull(valeur):
                return pd.NA
            if nettoyer:
                return _nettoyer_cle_comparaison(valeur)
            valeur = str(valeur).strip()
            return valeur if valeur else pd.NA

        if len(colonnes) == 1:
            return df_source[colonnes[0]].map(normaliser_valeur)

        def construire_cle(row):
            valeurs = [normaliser_valeur(row[col]) for col in colonnes]
            if any(pd.isna(val) for val in valeurs):
                return pd.NA
            return "||".join(map(str, valeurs))

        return df_source[colonnes].apply(construire_cle, axis=1)

    data_1 = _charger_dataframe_comparaison(df_1)
    data_2 = _charger_dataframe_comparaison(df_2)

    colonnes_communes = _normaliser_colonnes_communes(colonne_commune)
    for col in colonnes_communes:
        if col not in data_1.columns:
            raise ValueError(f"Colonne '{col}' introuvable dans df_1.")
        if col not in data_2.columns:
            raise ValueError(f"Colonne '{col}' introuvable dans df_2.")

    Ajout_cols_df_1 = _normaliser_liste_colonnes(Ajout_cols_df_1, data_1.columns, colonnes_communes)
    Ajout_cols_df_2 = _normaliser_liste_colonnes(Ajout_cols_df_2, data_2.columns, colonnes_communes)

    for col in Ajout_cols_df_1:
        if col not in data_1.columns:
            raise ValueError(f"Colonne '{col}' introuvable dans df_1.")
    for col in Ajout_cols_df_2:
        if col not in data_2.columns:
            raise ValueError(f"Colonne '{col}' introuvable dans df_2.")
    if not isinstance(suffixe_df_1, str) or not isinstance(suffixe_df_2, str):
        raise ValueError("suffixe_df_1 et suffixe_df_2 doivent être des chaînes.")
    if not isinstance(seuil, (int, float)) or seuil < 0 or seuil > 100:
        raise ValueError("seuil doit être compris entre 0 et 100.")

    cle_temp = "__cle_compare_composite__"
    colonnes_left = list(dict.fromkeys([*colonnes_communes, *Ajout_cols_df_1]))
    colonnes_right = list(dict.fromkeys([*colonnes_communes, *Ajout_cols_df_2]))
    left = data_1[colonnes_left].copy()
    right = data_2[colonnes_right].copy()

    left[cle_temp] = _creer_cle_composite(left, colonnes_communes)
    right[cle_temp] = _creer_cle_composite(right, colonnes_communes)

    nb_lignes_df_1 = len(left)
    nb_lignes_df_2 = len(right)
    nb_cles_valides_df_1 = int(left[cle_temp].notna().sum())
    nb_cles_valides_df_2 = int(right[cle_temp].notna().sum())

    left = left.dropna(subset=[cle_temp])
    right = right.dropna(subset=[cle_temp])

    if seuil >= 100:
        left_valid = left.copy()
        right_valid = right.copy()
        left_valid["__idx_left"] = left_valid.index
        right_valid["__idx_right"] = right_valid.index

        paires = left_valid[[cle_temp, "__idx_left"]].merge(
            right_valid[[cle_temp, "__idx_right"]],
            on=cle_temp,
            how="inner"
        )

        matched_left = left_valid.loc[paires["__idx_left"]].reset_index(drop=True)
        matched_right = right_valid.loc[paires["__idx_right"]].reset_index(drop=True)
    else:
        left_valid = left.reset_index(drop=True)
        right_valid = right.reset_index(drop=True)
        if left_valid.empty or right_valid.empty:
            matched_left = left_valid.iloc[0:0].copy()
            matched_right = right_valid.iloc[0:0].copy()
        else:
            cles_left = left_valid[cle_temp].astype(str).tolist()
            cles_right = right_valid[cle_temp].astype(str).tolist()

            if fuzz is not None and process is not None:
                scores = process.cdist(
                    cles_left,
                    cles_right,
                    scorer=fuzz.ratio,
                )
                max_scores = np.max(scores, axis=1)
                best_indices = np.argmax(scores, axis=1)
            else:
                max_scores = []
                best_indices = []
                for cle_left in cles_left:
                    scores_ligne = [
                        SequenceMatcher(None, cle_left, cle_right).ratio() * 100
                        for cle_right in cles_right
                    ]
                    best_indices.append(int(np.argmax(scores_ligne)))
                    max_scores.append(max(scores_ligne))
                max_scores = np.array(max_scores)
                best_indices = np.array(best_indices)

            mask_match = max_scores >= seuil

            matched_left = left_valid.loc[mask_match].reset_index(drop=True)
            matched_right = right_valid.iloc[best_indices[mask_match]].reset_index(drop=True)

    resultat = pd.DataFrame()
    for col in colonnes_communes:
        resultat[col] = matched_left[col].values if col in matched_left.columns else pd.Series(dtype="object")
    for col in Ajout_cols_df_1:
        resultat[f"{col}{suffixe_df_1}"] = matched_left[col].values if col in matched_left.columns else pd.Series(dtype="object")
    for col in Ajout_cols_df_2:
        resultat[f"{col}{suffixe_df_2}"] = matched_right[col].values if col in matched_right.columns else pd.Series(dtype="object")

    nb_lignes_communs = len(resultat)
    colonnes_communes_label = ", ".join(colonnes_communes)
    lignes_exclues_df_1 = nb_lignes_df_1 - nb_cles_valides_df_1
    lignes_exclues_df_2 = nb_lignes_df_2 - nb_cles_valides_df_2
    mode_matching = "strict" if seuil >= 100 else "approx"
    mode_matching_label = "comparaison stricte" if seuil >= 100 else "comparaison approximative"
    resume_export = pd.DataFrame(
        {
            "Indicateur": [
                "Colonnes utilisées pour comparer",
                "Mode de comparaison",
                "Seuil de correspondance",
                "Nettoyage des clés avant comparaison",
                "Nombre total de lignes dans df_1",
                "Nombre total de lignes dans df_2",
                "Nombre de lignes avec une clé exploitable dans df_1",
                "Nombre de lignes avec une clé exploitable dans df_2",
                "Nombre de lignes ignorées dans df_1 faute de clé",
                "Nombre de lignes ignorées dans df_2 faute de clé",
                "Nombre de lignes communes trouvées",
                "Nombre de colonnes dans le résultat final",
            ],
            "Valeur": [
                colonnes_communes_label,
                mode_matching_label,
                f"{seuil}/100 ({mode_matching})",
                nettoyer,
                nb_lignes_df_1,
                nb_lignes_df_2,
                nb_cles_valides_df_1,
                nb_cles_valides_df_2,
                lignes_exclues_df_1,
                lignes_exclues_df_2,
                nb_lignes_communs,
                len(resultat.columns),
            ],
        }
    )

    message_resume = (
        "\n[Résumé de la comparaison des fichiers]"
        f"\nColonnes utilisées pour comparer : {colonnes_communes_label}"
        f"\nMode de comparaison : {mode_matching_label}"
        f"\nSeuil de correspondance : {seuil}/100 ({mode_matching})"
        f"\nNettoyage des clés avant comparaison : {nettoyer}"
        f"\nNombre total de lignes dans df_1 : {nb_lignes_df_1}"
        f"\nNombre total de lignes dans df_2 : {nb_lignes_df_2}"
        f"\nNombre de lignes avec une clé exploitable dans df_1 : {nb_cles_valides_df_1}"
        f"\nNombre de lignes avec une clé exploitable dans df_2 : {nb_cles_valides_df_2}"
        f"\nNombre de lignes ignorées dans df_1 faute de clé : {lignes_exclues_df_1}"
        f"\nNombre de lignes ignorées dans df_2 faute de clé : {lignes_exclues_df_2}"
        f"\nNombre de lignes communes trouvées : {nb_lignes_communs}"
        f"\nNombre de colonnes dans le résultat final : {len(resultat.columns)}"
    )
    if export_excel:
        message_resume += f"\nFichier exporté vers : {export_excel}"
        export_path = Path(export_excel)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(export_path) as writer:
            resultat.to_excel(writer, sheet_name="resultat", index=False)
            resume_export.to_excel(writer, sheet_name="resume", index=False)
    print(message_resume)

    return resultat
