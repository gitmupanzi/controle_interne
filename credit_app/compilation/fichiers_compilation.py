# -*- coding: utf-8 -*-

# credit_app/compilation/fichiers_compilation.py


import pandas as pd
import os
import logging
import re
from typing import List, Optional,Union, Dict, Tuple
from collections import Counter, defaultdict
from credit_app.colonne_valeur.colonne_nettoyage import *
from datetime import datetime
from pathlib import Path
import fnmatch



logger = logging.getLogger(__name__)

# Chemins des fichiers
base_dir = Path(__file__).resolve().parents[2]
mapping_file_path = base_dir / "data" / "Rename_columns.xlsx"


def _construire_provenance_colonnes(
    colonnes_brutes: List[str],
    colonnes_nettoyees: List[str],
    fichier_path: Path,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Construit un index de provenance par colonne nettoyee.
    """
    provenance_par_colonne: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for colonne_brute, colonne_nettoyee in zip(colonnes_brutes, colonnes_nettoyees):
        provenance_par_colonne[colonne_nettoyee].append(
            {
                "fichier": fichier_path.name,
                "provenance": fichier_path.stem,
                "chemin": str(fichier_path),
                "colonne_originale": str(colonne_brute),
                "colonne_standardisee": str(colonne_nettoyee),
            }
        )

    return dict(provenance_par_colonne)


def _fusionner_provenances_colonnes(
    provenance_existante: Dict[str, List[Dict[str, str]]],
    nouvelle_provenance: Dict[str, List[Dict[str, str]]],
) -> Dict[str, List[Dict[str, str]]]:
    """
    Fusionne les metadonnees de provenance en evitant les doublons exacts.
    """
    fusion = {col: list(details) for col, details in provenance_existante.items()}

    for colonne, details in nouvelle_provenance.items():
        existants = fusion.setdefault(colonne, [])
        signatures = {
            (
                item.get("fichier"),
                item.get("provenance"),
                item.get("chemin"),
                item.get("colonne_originale"),
                item.get("colonne_standardisee"),
            )
            for item in existants
        }

        for item in details:
            signature = (
                item.get("fichier"),
                item.get("provenance"),
                item.get("chemin"),
                item.get("colonne_originale"),
                item.get("colonne_standardisee"),
            )
            if signature not in signatures:
                existants.append(item)
                signatures.add(signature)

    return fusion


def _construire_log_collisions_colonnes(
    colonnes_brutes: List[str],
    colonnes_warning: List[str],
    colonnes_preparees: List[str],
    colonnes_finales: List[str],
    fichier_path: Path,
    renommer_variable: bool,
    variables_brute: bool,
) -> pd.DataFrame:
    """
    Construit un log detaille des collisions de noms de colonnes apres preparation.

    Une collision correspond a plusieurs colonnes sources qui aboutissent au meme
    nom prepare avant l'ajout des suffixes `_01`, `_02`, etc.
    """
    compteur_colonnes = Counter(colonnes_preparees)
    rows = []

    for index, (colonne_brute, colonne_warning, colonne_preparee, colonne_finale) in enumerate(
        zip(colonnes_brutes, colonnes_warning, colonnes_preparees, colonnes_finales),
        start=1,
    ):
        if compteur_colonnes[colonne_preparee] <= 1:
            continue

        rows.append(
            {
                "fichier": fichier_path.name,
                "provenance": fichier_path.stem,
                "chemin": str(fichier_path),
                "ordre_colonne_source": index,
                "colonne_originale": "" if pd.isna(colonne_brute) else str(colonne_brute),
                "colonne_affichee_warning": colonne_warning,
                "colonne_preparee": colonne_preparee,
                "colonne_finale": colonne_finale,
                "renommer_variable": renommer_variable,
                "variables_brute": variables_brute,
            }
        )

    return pd.DataFrame(rows)


def _concatener_logs_dataframes(logs: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatene une liste de logs DataFrame en ignorant les elements vides.
    """
    logs_valides = [df for df in logs if df is not None and not df.empty]
    if not logs_valides:
        return pd.DataFrame()
    return pd.concat(logs_valides, ignore_index=True)


def extraire_attr_dataframe(value) -> pd.DataFrame:
    """
    Retourne un DataFrame a partir d'une valeur stockee dans `attrs`.

    Utile pour recuperer les journaux stockes dans `attrs` sous forme de
    liste de dictionnaires ou de DataFrame.
    """
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    return pd.DataFrame(value)


def _preparer_noms_pour_warning_doublons(
    colonnes_brutes: List[str],
    variables_brute: bool,
) -> List[str]:
    """
    Prepare les noms affiches dans le warning de doublons.

    Regle appliquee dans le pipeline :
    - `variables_brute=False` : le warning affiche les noms de colonnes bruts
      tels qu'ils existent dans le fichier source.
    - `variables_brute=True` : le warning affiche les noms apres
      `standardiser_noms_colonnes(..., mapping_file=None)`.
    """
    colonnes_brutes_str = ["" if pd.isna(colonne) else str(colonne) for colonne in colonnes_brutes]

    if not variables_brute:
        return colonnes_brutes_str

    df_reference = pd.DataFrame(columns=colonnes_brutes_str)
    return list(standardiser_noms_colonnes(df_reference, mapping_file=None).columns)


def _preparer_colonnes_attendues(
    colonnes_attendues: List[str],
    renommer_variable: bool = True,
    variables_brute: bool = False,
    mapping_colonnes: Optional[Union[str, Path]] = mapping_file_path,
) -> List[str]:
    """
    Aligne les colonnes attendues sur le meme pipeline de preparation que les donnees chargees.

    Cette fonction est utile pour que `verifier_colonnes(...)` compare des noms
    de reference prepares de la meme maniere que les colonnes chargees.

    Regles appliquees :
    - `variables_brute=True` : les colonnes attendues restent en brut.
    - `variables_brute=False` et `renommer_variable=False` :
      `standardiser_noms_colonnes(..., mapping_file=None)` est appliquee.
    - `variables_brute=False` et `renommer_variable=True` :
      `clean_all_column_names(..., mapping_file=mapping_colonnes)` est appliquee.
    """
    colonnes_brutes = ["" if pd.isna(colonne) else str(colonne) for colonne in colonnes_attendues]

    if variables_brute:
        return colonnes_brutes

    df_reference = pd.DataFrame(columns=colonnes_brutes)
    if renommer_variable:
        return list(clean_all_column_names(df_reference, mapping_file=mapping_colonnes).columns)

    return list(standardiser_noms_colonnes(df_reference, mapping_file=None).columns)


def _preparer_dataframe_colonnes(
    df: pd.DataFrame,
    fichier_path: Path,
    renommer_variable: bool = True,
    variables_brute: bool = False,
    colonne_source: Optional[str] = "Provenance",
    mapping_colonnes: Optional[Union[str, Path]] = mapping_file_path,
    suffixer_doublons: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, List[Dict[str, str]]], Dict[str, str], pd.DataFrame]:
    """
    Prepare un DataFrame selon le pipeline de colonnes demande et retourne :
    - le DataFrame prepare ;
    - les metadonnees de provenance colonne par colonne ;
    - un dictionnaire de transformations utilise pour le log.
    - un log detaille des collisions de colonnes.

    La preparation reutilise explicitement les fonctions du sous-module
    `credit_app.colonne_valeur.colonne_nettoyage` :
    - `standardiser_noms_colonnes(..., mapping_file=None)` pour la standardisation seule ;
    - `clean_all_column_names(..., mapping_file=mapping_colonnes)` pour la
      standardisation suivie du renommage via le fichier de mapping.

    Comportement :
    - `variables_brute=True` : conserve les noms bruts du fichier ;
    - `variables_brute=False` et `renommer_variable=False` :
      standardise sans mapping ;
    - `variables_brute=False` et `renommer_variable=True` :
      standardise puis renomme selon `mapping_colonnes`.

    Si plusieurs colonnes aboutissent au meme nom prepare, un warning est emis.
    Si `suffixer_doublons=True`, des suffixes `_01`, `_02`, etc. sont ajoutes
    temporairement pour conserver des noms uniques.
    """
    provenance = fichier_path.stem
    colonnes_brutes = list(df.columns)
    if variables_brute:
        df_prepare = df.copy()
        colonnes_preparees = ["" if pd.isna(colonne) else str(colonne) for colonne in colonnes_brutes]
        operations: List[Optional[str]] = [None for _ in colonnes_preparees]
    else:
        df_standardise = standardiser_noms_colonnes(df.copy(), mapping_file=None)
        if renommer_variable:
            df_prepare = clean_all_column_names(df.copy(), mapping_file=mapping_colonnes)
        else:
            df_prepare = df_standardise

        colonnes_preparees = list(df_prepare.columns)
        colonnes_standardisees = list(df_standardise.columns)
        operations = []
        for colonne_brute, colonne_standardisee, colonne_preparee in zip(
            colonnes_brutes,
            colonnes_standardisees,
            colonnes_preparees,
        ):
            nom_brut = "" if pd.isna(colonne_brute) else str(colonne_brute)
            if renommer_variable and colonne_preparee != colonne_standardisee:
                operations.append("renommage")
            elif nom_brut != colonne_preparee:
                operations.append("standardisation")
            else:
                operations.append(None)

    colonnes_warning = _preparer_noms_pour_warning_doublons(
        colonnes_brutes=colonnes_brutes,
        variables_brute=variables_brute,
    )
    if suffixer_doublons:
        colonnes_finales = rendre_colonnes_uniques(colonnes_preparees)
        mapping_affichage = {colonne: colonne for colonne in colonnes_finales}
    else:
        colonnes_finales, mapping_affichage = rendre_colonnes_uniques_techniques(colonnes_preparees)
    df_collisions = _construire_log_collisions_colonnes(
        colonnes_brutes=colonnes_brutes,
        colonnes_warning=colonnes_warning,
        colonnes_preparees=colonnes_preparees,
        colonnes_finales=colonnes_finales,
        fichier_path=fichier_path,
        renommer_variable=renommer_variable,
        variables_brute=variables_brute,
    )
    if df_collisions.empty:
        df_prepare.columns = colonnes_finales
    else:
        details_doublons = []
        regroupement_doublons: Dict[str, List[str]] = defaultdict(list)
        compteur_colonnes = Counter(colonnes_preparees)
        for colonne_warning, colonne_preparee in zip(colonnes_warning, colonnes_preparees):
            if compteur_colonnes[colonne_preparee] > 1:
                regroupement_doublons[colonne_preparee].append(colonne_warning)

        for colonne_preparee, colonnes_sources in regroupement_doublons.items():
            details_doublons.append(
                f"{colonne_preparee} <- {', '.join(colonnes_sources)}"
            )

        logger.warning(
            "⚠️ Colonnes dupliquees apres preparation dans %s : %s",
            fichier_path.name,
            " ; ".join(details_doublons),
        )

        df_prepare.columns = colonnes_finales
        if suffixer_doublons:
            for index, (avant, apres) in enumerate(zip(colonnes_preparees, colonnes_finales)):
                if avant != apres:
                    operations[index] = "dedoublonnage"

    provenance_df = _construire_provenance_colonnes(
        colonnes_brutes=colonnes_brutes,
        colonnes_nettoyees=colonnes_preparees,
        fichier_path=fichier_path,
    )

    if colonne_source is not None:
        df_prepare[colonne_source] = provenance

    col_funcs = {
        colonne_finale: operation
        for colonne_finale, operation in zip(colonnes_finales, operations)
        if operation is not None
    }

    if colonne_source is not None:
        col_funcs[colonne_source] = "ajout_colonne_source"

    df_prepare.attrs["_display_columns_map"] = mapping_affichage
    df_prepare.attrs["_display_columns"] = list(colonnes_preparees) + (
        [colonne_source] if colonne_source is not None else []
    )

    return df_prepare, provenance_df, col_funcs, df_collisions

"""
Fonctions utilitaires simples / basiques
- lister_fichiers_excel
- lire_fichiers_excel
- detecter_doublons_standardises
- rendre_colonnes_uniques

"""
# Lister les fichiers Excel valides dans un dossier donné
def lister_fichiers_excel(dossier_racine, motif_fichier="*LL_Rougeole.xlsx", sensible_a_la_casse=False):
    if not motif_fichier or not str(motif_fichier).strip():
        raise ValueError("motif_fichier ne peut pas être vide.")

    dossier = Path(dossier_racine)
    if not dossier.exists():
        raise ValueError(f"Dossier inexistant : {dossier_racine}")
    if not dossier.is_dir():
        raise ValueError(f"Le chemin fourni n'est pas un dossier : {dossier_racine}")

    fichiers_trouves = []
    for fichier in sorted(dossier.rglob("*.xlsx"), key=lambda p: str(p).lower()):  # récursif, uniquement fichiers Excel
        if fichier.name.startswith("~$"):  # exclusion fichiers temporaires Excel
            continue

        nom_fichier = fichier.name
        if not sensible_a_la_casse:
            if fnmatch.fnmatch(nom_fichier.lower(), motif_fichier.lower()):
                fichiers_trouves.append(fichier)
        else:
            if fnmatch.fnmatch(nom_fichier, motif_fichier):
                fichiers_trouves.append(fichier)

    logger.info(
        f"{len(fichiers_trouves)} fichiers trouvés avec motif '{motif_fichier}' "
        f"(sensible_a_la_casse={sensible_a_la_casse}) dans {dossier_racine}."
    )

    return fichiers_trouves

#  Lire les fichiers Excel 
def lire_fichiers_excel(
    liste_fichiers,
    sheet_name="Feuille1",
    sensible_a_la_casse=False,
    strict=True,
):
    """
    Lit les fichiers Excel fournis et retourne un dictionnaire de DataFrames.
    
    :param liste_fichiers: Liste des chemins de fichiers Excel.
    :param sheet_name: Nom de la feuille à lire.
    :param sensible_a_la_casse: Booléen pour activer la sensibilité à la casse (False par défaut).
    :return: Dictionnaire {nom_fichier: DataFrame}.
    """
    if not liste_fichiers:
        return {}

    donnees = {}
    erreurs: list[str] = []
    for chemin in liste_fichiers:
        chemin = Path(chemin)
        if not chemin.exists() or not chemin.is_file():
            logger.warning("❌ Fichier introuvable ou invalide : %s", chemin)
            erreurs.append(f"{chemin.name} : fichier introuvable ou invalide")
            continue
        if chemin.name.startswith("~$"):
            continue

        nom_fichier = chemin.name
        try:
            with pd.ExcelFile(chemin) as xl:
                feuilles = xl.sheet_names

                if sensible_a_la_casse:
                    feuille_choisie = sheet_name if sheet_name in feuilles else None
                else:
                    feuilles_lower = [f.lower() for f in feuilles]
                    try:
                        idx = feuilles_lower.index(sheet_name.lower())
                        feuille_choisie = feuilles[idx]
                    except ValueError:
                        feuille_choisie = None

                if feuille_choisie is None:
                    raise ValueError(f"Feuille '{sheet_name}' non trouvée dans {nom_fichier}")

                df = xl.parse(sheet_name=feuille_choisie)
            donnees[chemin] = df
            logger.info(f"✅ Lu : {nom_fichier} - feuille : {feuille_choisie}")
        except Exception as e:
            logger.warning(f"❌ Erreur avec {nom_fichier} : {e}")
            erreurs.append(f"{nom_fichier} : {e}")

    if strict and erreurs:
        raise ValueError("Chargement refusé. " + " | ".join(erreurs))

    return donnees

# detecter_doublons_standardises
def detecter_doublons_standardises(df: pd.DataFrame, provenance: str) -> List[str]:
    """
    Détecte les noms de colonnes qui, une fois standardisés, apparaissent plusieurs fois.
    Utile pour identifier les problèmes de duplication silencieuse.

    Args:
        df: DataFrame à analyser.
        provenance: Nom du fichier ou identifiant du DataFrame.

    Returns:
        Liste des noms standardisés en doublon.
    """
    noms_standards = [standardiser_nom(c) for c in df.columns]
    compteur = defaultdict(int)
    for nom in noms_standards:
        compteur[nom] += 1
    doublons = [nom for nom, count in compteur.items() if count > 1]
    if doublons:
        logger.warning(f"[{provenance}] Colonnes standardisées en doublon détectées : {doublons}")
    return doublons

# Rendre les noms de colonnes uniques
def rendre_colonnes_uniques(cols: List[str]) -> List[str]:
    """
    Rend une liste de noms de colonnes unique en ajoutant des suffixes _01, _02...

    Args:
        cols: Liste de noms (souvent standardisés).

    Returns:
        Liste avec noms uniques.
    """
    compteur = defaultdict(int)
    noms_uniques = []
    for col in cols:
        compteur[col] += 1
        if compteur[col] == 1:
            noms_uniques.append(col)
        else:
            noms_uniques.append(f"{col}_{compteur[col]-1:02d}")
    return noms_uniques


def rendre_colonnes_uniques_techniques(
    cols: List[str],
    suffixe_technique: str = "__dup",
) -> Tuple[List[str], Dict[str, str]]:
    """
    Rend des noms techniquement uniques tout en memorisant le nom a afficher.

    Contrairement a `rendre_colonnes_uniques(...)`, les doublons supplementaires
    recoivent un suffixe interne peu probable (`__dup01`, `__dup02`, ...),
    destine a la concatenation pandas. Les noms visibles peuvent ensuite etre
    restaures pour afficher les doublons tels quels dans le DataFrame final.
    """
    compteur = defaultdict(int)
    noms_uniques = []
    mapping_affichage: Dict[str, str] = {}

    for col in cols:
        compteur[col] += 1
        if compteur[col] == 1:
            nom_technique = col
        else:
            nom_technique = f"{col}{suffixe_technique}{compteur[col]-1:02d}"

        noms_uniques.append(nom_technique)
        mapping_affichage[nom_technique] = col

    return noms_uniques, mapping_affichage

""" 
Fonctions de traitement / transformation des données

- renommer_colonnes_avec_provenance
- afficher_colonnes_standardisees
- fusionner_colonnes_similaires
- comparer_colonnes_multiples

"""

# Renommer les colonnes avec la nouvelle colonne : provenance
def renommer_colonnes_avec_provenance(df: pd.DataFrame, provenance: str, colonnes_a_renommer: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Renomme certaines colonnes d'un DataFrame en ajoutant la provenance comme suffixe.

    Args:
        df: DataFrame original.
        provenance: Suffixe à ajouter.
        colonnes_a_renommer: Colonnes ciblées (par défaut toutes sauf "Provenance").

    Returns:
        DataFrame avec colonnes renommées.
    """
    if colonnes_a_renommer is None:
        colonnes_a_renommer = [col for col in df.columns if col != "Provenance"]

    new_cols = {}
    for col in colonnes_a_renommer:
        new_cols[col] = f"{col}_{provenance}"
    return df.rename(columns=new_cols)

# Afficher les colonnes standardisées
def afficher_colonnes_standardisees(dataframes: List[pd.DataFrame]) -> None:
    """
    Affiche dans les logs les colonnes preparees pour chaque DataFrame.

    Args:
        dataframes (List[pd.DataFrame]): Liste de DataFrames.
    """
    logger.info("Affichage des colonnes preparees par fichier :")
    for i, df in enumerate(dataframes):
        provenance = (
            df["Provenance"].iloc[0]
            if "Provenance" in df.columns
            else f"Fichier_{i + 1}"
        )
        colonnes_affichees = df.attrs.get("_display_columns", list(df.columns))
        logger.info(f"Fichier : {provenance} - Colonnes : {list(colonnes_affichees)}")
 
# Fusionner les colonnes similaires
def fusionner_colonnes_similaires(
    dataframes: List[pd.DataFrame],
    standardiser_colonnes: bool = True,
    fusionner_colonnes_suffixees: bool = True,
    restaurer_noms_dupliques: bool = False,
) -> pd.DataFrame:
    """
    Fusionne plusieurs DataFrames en harmonisant les colonnes suffixees.

    La fonction peut :
    - standardiser de nouveau les noms de colonnes si `standardiser_colonnes=True` ;
    - ou conserver tels quels les noms deja prepares si `standardiser_colonnes=False`.

    Les colonnes dedoublonnees par `rendre_colonnes_uniques(...)` sous la forme
    `nom`, `nom_01`, `nom_02`, etc. peuvent etre reconciliees en recopiant les
    valeurs non nulles vers la colonne de base, puis les colonnes suffixees sont
    supprimees.

    Args:
        dataframes (List[pd.DataFrame]): Liste de DataFrames à fusionner.
        standardiser_colonnes (bool): Reapplique `standardiser_nom` avant fusion.
            Utiliser `False` lorsque les colonnes ont deja ete preparees en amont.
        fusionner_colonnes_suffixees (bool): Si True, fusionne les colonnes
            suffixees selon le motif de dedoublonnage `_01`, `_02`, etc.
        restaurer_noms_dupliques (bool): Si True, restaure les noms visibles
            potentiellement dupliques apres la concatenation technique.

    Returns:
        pd.DataFrame: DataFrame fusionné avec colonnes unifiées.
    """

    dataframes_renommes = []
    mapping_affichage_global: Dict[str, str] = {}

    # --- Standardisation optionnelle et vérification des doublons ---
    for df in dataframes:
        provenance = df["Provenance"].iloc[0] if "Provenance" in df.columns else "inconnu"
        df_renamed = df.copy()
        mapping_affichage_df = df.attrs.get("_display_columns_map", {})

        if standardiser_colonnes:
            noms_std = [standardiser_nom(c) for c in df.columns]
            noms_uniques = rendre_colonnes_uniques(noms_std)
            df_renamed.columns = noms_uniques
            mapping_affichage_df = {colonne: colonne for colonne in noms_uniques}
        else:
            mapping_affichage_df = {
                str(colonne): str(mapping_affichage_df.get(colonne, colonne))
                for colonne in df_renamed.columns
            }

        colonnes_dupliquees = df_renamed.columns[df_renamed.columns.duplicated()].tolist()
        if colonnes_dupliquees:
            raise ValueError(f"Colonnes dupliquées après renommage dans '{provenance}' : {colonnes_dupliquees}")

        dataframes_renommes.append(df_renamed)
        for colonne in df_renamed.columns:
            mapping_affichage_global.setdefault(
                str(colonne),
                str(mapping_affichage_df.get(colonne, colonne)),
            )

    # --- Concaténation des DataFrames renommés ---
    df_fusionne = pd.concat(dataframes_renommes, ignore_index=True)

    # --- Regroupement et fusion des colonnes suffixées ---
    if fusionner_colonnes_suffixees:
        groupes = {}
        for col in df_fusionne.columns:
            match = re.match(r"^(?P<base>.+)_(?P<suffix>\d{2,})$", str(col))
            if not match:
                continue

            base = match.group("base")
            if base not in df_fusionne.columns:
                continue

            groupes.setdefault(base, []).append(col)

        for base, cols in groupes.items():
            for col in cols:
                masque_remplacement = df_fusionne[base].isna() & df_fusionne[col].notna()
                if masque_remplacement.any():
                    df_fusionne.loc[masque_remplacement, base] = df_fusionne.loc[masque_remplacement, col]
            df_fusionne.drop(columns=cols, inplace=True)

    if restaurer_noms_dupliques:
        df_fusionne.columns = [
            mapping_affichage_global.get(str(colonne), str(colonne))
            for colonne in df_fusionne.columns
        ]

    # --- Suppression des colonnes vides et lignes entièrement vides ---
    colonnes_a_supprimer = [c for c in df_fusionne.columns if c.startswith("Unnamed") and df_fusionne[c].isnull().all()]
    if colonnes_a_supprimer:
        df_fusionne.drop(columns=colonnes_a_supprimer, inplace=True)

    df_fusionne.dropna(how='all', inplace=True)

    return df_fusionne

# Comparer les colonnes entre plusieurs DataFrames
def comparer_colonnes_multiples(
    dfs: Dict[str, pd.DataFrame],
    valeur_absente: Union[str, None] = "-"
) -> pd.DataFrame:
    """
    Compare les colonnes entre plusieurs DataFrames et retourne une table croisée
    indiquant la présence ou l'absence de chaque colonne.

    Args:
        dfs (Dict[str, pd.DataFrame]): 
            Dictionnaire où les clés sont les noms de jeux de données, 
            et les valeurs sont les DataFrames à comparer.
        
        valeur_absente (Union[str, None], optional): 
            Valeur à afficher si une colonne est absente dans un DataFrame. 
            Par défaut "-". Peut aussi être None ou tout autre indicateur.

    Returns:
        pd.DataFrame: 
            Tableau croisé listant toutes les colonnes uniques et indiquant 
            leur présence ou absence dans chaque DataFrame.

    Exemple :
        >>> dfs = {
        ...     "fichier_jaune": pd.DataFrame(columns=["Nom", "Age"]),
        ...     "fichier_vert": pd.DataFrame(columns=["Nom", "Sexe"]),
        ... }
        >>> resultat = comparer_colonnes_multiples(dfs)
        >>> print(resultat.to_markdown(index=False))
    """
    # Récupérer toutes les colonnes distinctes de tous les DataFrames
    toutes_colonnes = sorted(set(col for df in dfs.values() for col in df.columns))
    
    # Construire le tableau
    tableau = []
    for col in toutes_colonnes:
        ligne = {"Colonne": col}
        for nom_df, df in dfs.items():
            ligne[nom_df] = col if col in df.columns else valeur_absente
        tableau.append(ligne)

    return pd.DataFrame(tableau)

# ------------------------------------------------
# Fonction(s) principale(s) d’orchestration
# ------------------------------------------------
# Charger plusieurs fichiers Excel, nettoyer les colonnes, ajouter la provenance, et fusionner les données
def charger_fichiers_excel(
    dossier_racine: Optional[str] = None,
    liste_fichiers: Optional[List[str]] = None,
    motif_fichier: str = "*LL_Rougeole.xlsx",
    sheet_name: str = "LL_Rougeole",
    colonnes_attendues: Optional[List[str]] = None,
    sensible_a_la_casse: bool = False,
    colonne_source: Optional[str] = "Provenance",   # 🔹 peut être None
    renommer_variable: bool = True,
    variables_brute: bool = False,
    suffixer_doublons: bool = False,
    mapping_colonnes: Optional[Union[str, Path]] = mapping_file_path,
    sheet_log: bool = False,
    dossier_sortie: Optional[str] = None,
    log_only_changed: bool = False,
    strict: bool = True,
    verifier_compatibilite: bool = False,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Charge plusieurs fichiers Excel et compile les donnees dans un seul DataFrame.

    Le pipeline de preparation des colonnes est pilote par `renommer_variable`
    et `variables_brute`, en s'appuyant sur les fonctions du sous-module
    `credit_app.colonne_valeur.colonne_nettoyage`.

    Comportement des colonnes :
    - `variables_brute=True` : les noms de colonnes restent bruts ;
    - `variables_brute=False` et `renommer_variable=False` :
      les noms sont standardises via `standardiser_noms_colonnes(..., mapping_file=None)` ;
    - `variables_brute=False` et `renommer_variable=True` :
      les noms sont standardises puis renommes via
      `clean_all_column_names(..., mapping_file=mapping_colonnes)`.
    - si plusieurs colonnes aboutissent au meme nom prepare,
      `suffixer_doublons` permet de choisir si des suffixes temporaires
      `_01`, `_02`, etc. doivent etre ajoutes ou non.

    Une colonne de provenance peut etre ajoutee. En sortie, le DataFrame porte
    aussi deux attributs utiles pour l'audit :
    - `df.attrs["column_provenance"]` : provenance des colonnes ;
    - `df.attrs["column_collisions"]` : log detaille des collisions de noms,
      stocke sous forme de liste de dictionnaires, convertible via
      `extraire_attr_dataframe(...)`.

    Si `sheet_log=True`, la fonction retourne aussi un log detaille des
    transformations de colonnes sous la forme :
    `(df_compilation, df_log)`.

    Args:
        dossier_racine (str, optionnel): Chemin vers un dossier contenant les fichiers Excel.
        liste_fichiers (List[str], optionnel): Liste de chemins de fichiers Excel à charger directement.
        motif_fichier (str): Motif de recherche des fichiers Excel dans le dossier 
            (par défaut "*LL_Rougeole.xlsx").
        sheet_name (str): Nom de la feuille Excel à lire (par défaut "LL_Rougeole").
        colonnes_attendues (List[str], optionnel): Liste des colonnes attendues dans les fichiers. 
            Si fournie, une vérification est effectuée après la fusion.
        sensible_a_la_casse (bool): Indique si la recherche des colonnes doit être sensible à la casse 
            (par défaut False).
        colonne_source (str | None): Nom de la colonne ajoutée pour indiquer la provenance des données.
            Si None, aucune colonne n’est ajoutée. (par défaut "Provenance").
        renommer_variable (bool): Active le renommage via le fichier de mapping
            apres standardisation des noms.
        variables_brute (bool): Si True, bypass la standardisation et conserve les
            noms de colonnes bruts du fichier source.
        suffixer_doublons (bool): Si True, ajoute des suffixes temporaires
            `_01`, `_02`, etc. lorsque plusieurs colonnes renommées aboutissent
            au meme nom. Si False, la sortie finale conserve les noms dupliques
            tels quels pour permettre une fusion metier ulterieure.
        mapping_colonnes (str | Path | None): Fichier Excel de mapping a utiliser
            avec `clean_all_column_names` lorsque `renommer_variable=True`.
        sheet_log (bool): Si True, retourne aussi un DataFrame de log des
            transformations de colonnes.
        dossier_sortie (str | None): Dossier d'export du log. Si renseigne avec
            `sheet_log=True`, exporte le log et la feuille `Collisions` si besoin.
        log_only_changed (bool): Si True, filtre le log pour ne garder que les
            colonnes modifiees.

    Returns:
        pd.DataFrame: DataFrame fusionné contenant toutes les données nettoyées.

    Raises:
        ValueError: Si aucun fichier valide n'est trouvé ou chargé.

    Exemples:
        >>> df1 = charger_fichiers_excel(
        ...     dossier_racine="Cholera",
        ...     motif_fichier="*_LL_Cholera*.xlsx",
        ...     sheet_name="LL_Cholera",
        ...     colonne_source="Fichier_origine"   # ajoute une colonne "Fichier_origine"
        ... )
        >>> df2 = charger_fichiers_excel(
        ...     dossier_racine="Cholera",
        ...     motif_fichier="*_LL_Cholera*.xlsx",
        ...     sheet_name="LL_Cholera",
        ...     colonne_source=None   # aucune colonne ajoutée
        ... )
        >>> df3 = charger_fichiers_excel(
        ...     dossier_racine="Ebola",
        ...     motif_fichier="*.xlsx",
        ...     sheet_name="LL_Ebola",
        ...     renommer_variable=False,
        ...     variables_brute=False,
        ... )
        >>> df4, df_log = charger_fichiers_excel(
        ...     dossier_racine="Ebola",
        ...     motif_fichier="*.xlsx",
        ...     sheet_name="LL_Ebola",
        ...     sheet_log=True,
        ...     dossier_sortie="output/",
        ...     colonne_source="Provenance",
        ... )
    """
    if liste_fichiers is None:
        if dossier_racine is None:
            raise ValueError("Il faut fournir soit un dossier_racine, soit une liste_fichiers.")
        liste_fichiers = lister_fichiers_excel(
            dossier_racine, motif_fichier, sensible_a_la_casse
        )
    else:
        liste_fichiers = sorted({Path(f) for f in liste_fichiers}, key=lambda p: str(p).lower())

    donnees_brutes = lire_fichiers_excel(
        liste_fichiers,
        sheet_name=sheet_name,
        sensible_a_la_casse=sensible_a_la_casse,
        strict=strict,
    )
    if verifier_compatibilite and len(donnees_brutes) >= 2:
        from credit_app.services.data_pipeline import assess_compilation_compatibility

        assessment = assess_compilation_compatibility(
            [
                (Path(path).name, frame.columns, (sheet_name,))
                for path, frame in donnees_brutes.items()
            ]
        )
        if not assessment.compatible:
            raise ValueError("Compilation refusée. " + " ".join(assessment.reasons))

    dataframes = []
    logs = []
    logs_collisions = []
    provenance_colonnes: Dict[str, List[Dict[str, str]]] = {}
    erreurs_traitement: list[str] = []
    for fichier, df in donnees_brutes.items():
        try:
            fichier_path = Path(fichier)
            provenance = fichier_path.stem
            df_orig = df.copy()
            df = df.copy()
            df["source_fichier"] = fichier_path.name
            df["source_feuille"] = sheet_name
            df["numero_ligne_source"] = pd.RangeIndex(start=2, stop=len(df) + 2)
            df, provenance_df, col_funcs, df_collisions = _preparer_dataframe_colonnes(
                df=df,
                fichier_path=fichier_path,
                renommer_variable=renommer_variable,
                variables_brute=variables_brute,
                colonne_source=colonne_source,
                mapping_colonnes=mapping_colonnes,
                suffixer_doublons=suffixer_doublons,
            )
            provenance_colonnes = _fusionner_provenances_colonnes(
                provenance_colonnes,
                provenance_df,
            )

            detecter_doublons_standardises(df, provenance)
            dataframes.append(df)
            logs_collisions.append(df_collisions)
            if sheet_log:
                logs.append(log_colonnes(df_orig, df, col_funcs=col_funcs, fichier=fichier_path.name))

        except Exception as e:
            logger.warning(f"Erreur lors du traitement de {Path(fichier).name} : {e}")
            erreurs_traitement.append(f"{Path(fichier).name} : {e}")

    if strict and erreurs_traitement:
        raise ValueError("Compilation refusée. " + " | ".join(erreurs_traitement))

    if not dataframes:
        raise ValueError("Aucun fichier valide n’a été chargé.")

    afficher_colonnes_standardisees(dataframes)
    df_fusionne = fusionner_colonnes_similaires(
        dataframes,
        standardiser_colonnes=False,
        fusionner_colonnes_suffixees=suffixer_doublons,
        restaurer_noms_dupliques=not suffixer_doublons,
    )
    df_fusionne.attrs["column_provenance"] = provenance_colonnes
    df_fusionne.attrs["column_collisions"] = _concatener_logs_dataframes(logs_collisions).to_dict(orient="records")

    if colonnes_attendues:
        verifier_colonnes(
            df_fusionne,
            _preparer_colonnes_attendues(
                colonnes_attendues=colonnes_attendues,
                renommer_variable=renommer_variable,
                variables_brute=variables_brute,
                mapping_colonnes=mapping_colonnes,
            ),
        )

    if not sheet_log:
        return df_fusionne

    df_log_final = _concatener_logs_dataframes(logs)
    df_log_final.attrs["column_collisions"] = df_fusionne.attrs["column_collisions"]

    if log_only_changed and not df_log_final.empty:
        df_log_final = df_log_final[df_log_final["changed"] == True].reset_index(drop=True)
        df_log_final.attrs["column_collisions"] = df_fusionne.attrs["column_collisions"]

    if dossier_sortie:
        base_nom_log = f"log_{standardiser_nom(sheet_name)}" if sheet_name else "log_chargement"
        df_collisions_final = extraire_attr_dataframe(df_fusionne.attrs["column_collisions"])
        contenu_export_log: Union[pd.DataFrame, Dict[str, pd.DataFrame]]
        if df_collisions_final.empty:
            contenu_export_log = df_log_final
        else:
            contenu_export_log = {
                "Log": df_log_final,
                "Collisions": df_collisions_final,
            }
        fichiers_log = exporter_dataframe_excel(
            df=contenu_export_log,
            dossier=dossier_sortie,
            base_nom=base_nom_log,
            sheet_name="Log",
        )
        logger.info(f"Log exporte : {fichiers_log}")

    return df_fusionne, df_log_final

def exporter_dataframe_excel(
    df: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
    dossier: str,
    base_nom: str,
    sheet_name: str = "Feuille1",
    split: bool = False,
    colonne_split: str = "Div_Prov",
    supprimer_na: bool = True,
    creer_sous_dossiers: bool = True,
    inclure_horodatage: bool = True,
    une_feuille_par_groupe: bool = False,
    ecrire_index: bool = False,
) -> list:
    """
    Exporte un DataFrame pandas, ou un dictionnaire de DataFrames, vers un ou plusieurs fichiers Excel.

    Cette fonction est conçue pour les bases de surveillance épidémiologique
    (listes linéaires : Mpox, Choléra, Rougeole, Polio, etc.) et permet
    plusieurs stratégies d’export adaptées aux besoins opérationnels.

    --------------------------------------------------------------------
    MODES D’EXPORT
    --------------------------------------------------------------------
    1) EXPORT NATIONAL
        split=False
        → Un seul fichier Excel contenant toute la base.

    2) EXPORT MULTI-FICHIERS
        split=True
        → Un fichier Excel par groupe (ex : 26 provinces).

    3) EXPORT MULTI-FEUILLES
        split=True + une_feuille_par_groupe=True
        → Un seul fichier Excel contenant plusieurs feuilles
          (une feuille par province / ZS / AS).

    --------------------------------------------------------------------
    PARAMÈTRES
    --------------------------------------------------------------------
    df : pd.DataFrame | dict[str, pd.DataFrame]
        DataFrame source à exporter.
        Si un dictionnaire est fourni, chaque clé devient un nom de feuille.
        Ce mode est compatible uniquement avec `split=False`.

    dossier : str
        Dossier de sortie. Il est créé automatiquement s’il n’existe pas.

    base_nom : str
        Préfixe du nom du fichier (ex : "LLMpox_2026_SE05").

    sheet_name : str, défaut="Feuille1"
        Nom de la feuille Excel utilisée pour l’export national.
        Ignoré si `df` est un dictionnaire.

    split : bool, défaut=False
        Active le découpage du DataFrame selon une colonne.

    colonne_split : str, défaut="Div_Prov"
        Nom de la colonne utilisée pour séparer les données
        (ex : Province, Zone_Sante, Aire_Sante, DPS_Residence_Cas).

    supprimer_na : bool, défaut=True
        Supprime les lignes dont la valeur de la colonne de découpage est NA.

    creer_sous_dossiers : bool, défaut=True
        True  → crée un dossier par groupe (outputs/Kinshasa/)
        False → tous les fichiers sont écrits dans le même dossier.

    inclure_horodatage : bool, défaut=True
        True  → ajoute la date et l'heure dans le nom du fichier.
        False → nom fixe. Un système anti-écrasement (_v2, _v3...) est appliqué.

    une_feuille_par_groupe : bool, défaut=False
        True  → crée un seul fichier Excel avec plusieurs feuilles.
        False → crée plusieurs fichiers Excel (un par groupe).

    ecrire_index : bool, défaut=False
        Écrit l’index pandas dans le fichier Excel.

    --------------------------------------------------------------------
    RETOUR
    --------------------------------------------------------------------
    list[str]
        Liste complète des chemins des fichiers Excel générés.

    --------------------------------------------------------------------
    EXEMPLES
    --------------------------------------------------------------------
    Export national :
        exporter_dataframe_excel(df, "outputs", "LLMpox")

    Export par province :
        exporter_dataframe_excel(df, "outputs", "LLMpox", split=True)

    Un seul fichier avec 26 feuilles :
        exporter_dataframe_excel(
            df, "outputs", "LLMpox",
            split=True,
            une_feuille_par_groupe=True
        )
    """

    # ==========================================================
    # OUTILS INTERNES
    # ==========================================================

    def nettoyer_nom(val) -> str:
        """Nettoie un texte pour un usage sûr comme nom de fichier Windows."""
        if pd.isna(val):
            return "NA"
        s = str(val).strip()
        s = re.sub(r'[\\/*?:"<>|]', "_", s)
        s = s.rstrip(". ")
        s = re.sub(r"\s+", "_", s)
        return s if s else "VIDE"

    def sheet_safe(name: str) -> str:
        """Rend un nom compatible Excel (max 31 caractères)."""
        name = str(name)
        name = re.sub(r"[\[\]:*?/\\]", "_", name)
        return name[:31]

    def chemin_unique(path):
        """Empêche l'écrasement d'un fichier existant."""
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        i = 2
        while True:
            new_path = f"{base}_v{i}{ext}"
            if not os.path.exists(new_path):
                return new_path
            i += 1

    # ==========================================================
    # PRÉPARATION
    # ==========================================================

    if isinstance(df, dict):
        if split:
            raise ValueError("Le mode dictionnaire de DataFrames n'est pas compatible avec split=True.")
        if not df:
            raise ValueError("Le dictionnaire de DataFrames à exporter ne peut pas être vide.")
        feuilles_invalides = [nom for nom, valeur in df.items() if not isinstance(valeur, pd.DataFrame)]
        if feuilles_invalides:
            raise TypeError(
                "Toutes les valeurs du dictionnaire doivent être des DataFrames pandas. "
                f"Feuilles invalides : {feuilles_invalides}"
            )

    os.makedirs(dossier, exist_ok=True)
    logger.info(f"Dossier de sortie : {os.path.abspath(dossier)}")

    horodatage = datetime.now().strftime("%Y_%m_%d_%H_%M_%S") if inclure_horodatage else ""
    base_nom_clean = nettoyer_nom(base_nom) if base_nom else "export"

    fichiers = []

    # ==========================================================
    # EXPORT NATIONAL
    # ==========================================================
    if not split:

        logger.info("Mode : EXPORT NATIONAL")

        nom_fichier = (
            f"{base_nom_clean}_{horodatage}.xlsx"
            if inclure_horodatage
            else f"{base_nom_clean}.xlsx"
        )

        chemin = chemin_unique(os.path.join(dossier, nom_fichier))

        if isinstance(df, dict):
            with pd.ExcelWriter(chemin, engine="xlsxwriter") as writer:
                total_lignes = 0
                for feuille_nom, df_feuille in df.items():
                    df_feuille.to_excel(
                        writer,
                        index=ecrire_index,
                        sheet_name=sheet_safe(feuille_nom),
                    )
                    total_lignes += len(df_feuille)
                    logger.info(f"Feuille créée : {sheet_safe(feuille_nom)} ({len(df_feuille)} lignes)")
            logger.info(f"Fichier multi-feuilles créé : {chemin}")
            logger.info(f"Total lignes exportées : {total_lignes}")
        else:
            df.to_excel(chemin, index=ecrire_index, sheet_name=sheet_safe(sheet_name))

            logger.info(f"Fichier créé : {chemin}")
            logger.info(f"Lignes exportées : {len(df)}")

        fichiers.append(chemin)
        return fichiers

    # ==========================================================
    # EXPORT PAR GROUPE
    # ==========================================================

    logger.info(f"Mode : EXPORT PAR {colonne_split}")

    if colonne_split not in df.columns:
        logger.error(f"Colonne introuvable : {colonne_split}")
        raise ValueError(f"La colonne '{colonne_split}' n'existe pas dans le DataFrame")

    data = df.copy()

    if supprimer_na:
        avant = len(data)
        data = data[~data[colonne_split].isna()].copy()
        logger.info(f"Lignes NA supprimées : {avant - len(data)}")

    data[colonne_split] = data[colonne_split].astype(str)
    valeurs = sorted(data[colonne_split].unique())

    logger.info(f"{len(valeurs)} groupes détectés")

    # ==========================================================
    # MODE MULTI-FEUILLES
    # ==========================================================
    if une_feuille_par_groupe:

        logger.info("Mode : UN SEUL FICHIER AVEC PLUSIEURS FEUILLES")

        nom_fichier = (
            f"{base_nom_clean}_{colonne_split}_ALL_{horodatage}.xlsx"
            if inclure_horodatage
            else f"{base_nom_clean}_{colonne_split}_ALL.xlsx"
        )

        chemin = chemin_unique(os.path.join(dossier, nom_fichier))

        with pd.ExcelWriter(chemin, engine="xlsxwriter") as writer:

            for valeur in valeurs:
                df_g = data[data[colonne_split] == valeur]
                if df_g.empty:
                    continue

                feuille = sheet_safe(valeur)
                df_g.to_excel(writer, sheet_name=feuille, index=ecrire_index)

                logger.info(f"Feuille : {feuille} ({len(df_g)} lignes)")

        logger.info(f"Fichier multi-feuilles créé : {chemin}")
        fichiers.append(chemin)
        return fichiers

    # ==========================================================
    # MODE MULTI-FICHIERS
    # ==========================================================
    for valeur in valeurs:

        df_g = data[data[colonne_split] == valeur]
        if df_g.empty:
            continue

        valeur_clean = nettoyer_nom(valeur)

        dossier_final = (
            os.path.join(dossier, valeur_clean)
            if creer_sous_dossiers
            else dossier
        )

        if creer_sous_dossiers:
            os.makedirs(dossier_final, exist_ok=True)

        nom_fichier = (
            f"{base_nom_clean}_{colonne_split}_{valeur_clean}_{horodatage}.xlsx"
            if inclure_horodatage
            else f"{base_nom_clean}_{colonne_split}_{valeur_clean}.xlsx"
        )

        chemin = chemin_unique(os.path.join(dossier_final, nom_fichier))

        df_g.to_excel(
            chemin,
            index=ecrire_index,
            sheet_name=sheet_safe(valeur_clean)
        )

        fichiers.append(chemin)
        logger.info(f"{valeur_clean} : {len(df_g)} lignes exportées")

    logger.info(f"Export terminé : {len(fichiers)} fichiers générés")
    return fichiers

def fusionner_fichiers_homogenes(
    fichiers: List[Union[str, pd.DataFrame]],
    chemin_sortie: str = None,
    avec_source: bool = False,
    colonne_source: Optional[str] = "Provenance",
    reset_index: bool = True,
    colonnes_communes_only: bool = False,
    exporter: bool = False 
) -> pd.DataFrame:
    """
    Fusionne plusieurs fichiers (ou DataFrames) avec gestion automatique de la provenance.
    Si `exporter=True`, enregistre le résultat au format CSV/XLSX avec un horodatage.

    Args:
        fichiers (List[Union[str, pd.DataFrame]]): Chemins ou DataFrames à fusionner.
        chemin_sortie (str, optional): Chemin pour sauvegarder le résultat.
        avec_source (bool): Ajouter une colonne indiquant le fichier source.
        colonne_source (str | None): Nom de la colonne de provenance. Si None, aucune colonne n’est ajoutée.
        reset_index (bool): Réinitialiser l'index.
        colonnes_communes_only (bool): Si True, ne garde que les colonnes communes.
        exporter (bool): ✅ Si True, sauvegarde le fichier fusionné. Par défaut False.

    Returns:
        pd.DataFrame: DataFrame fusionné.
    """
    df_liste = []
    horodatage_str = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")

    for fichier in fichiers:
        if isinstance(fichier, pd.DataFrame):
            df = fichier.copy()
            nom_source = "DataFrame"
        elif isinstance(fichier, str):
            try:
                if not os.path.exists(fichier):
                    logger.error(f"[Fichier introuvable] {fichier}")
                    continue

                ext = os.path.splitext(fichier)[1].lower()
                if ext == ".csv":
                    df = pd.read_csv(fichier)
                elif ext in [".xls", ".xlsx"]:
                    df = pd.read_excel(fichier)
                else:
                    logger.warning(f"[Ignore] Format non supporté: {fichier}")
                    continue

                nom_source = os.path.basename(fichier)
            except Exception as e:
                logger.error(f"[Erreur lecture] {fichier} : {e}")
                continue
        else:
            logger.warning(f"[Ignore] Type non supporté : {type(fichier)}")
            continue

        # ✅ Gestion colonne source uniquement si demandé ET si colonne_source n’est pas None
        if avec_source and colonne_source is not None:
            colonnes_existantes = df.columns
            nouvelle_colonne = colonne_source

            if colonne_source in colonnes_existantes:
                i = 2
                while f"{colonne_source}_fusion_{i}" in colonnes_existantes:
                    i += 1
                nouvelle_colonne = f"{colonne_source}_fusion_{i}"

            df[nouvelle_colonne] = nom_source
            logger.info(f"[Provenance] Colonne '{nouvelle_colonne}' ajoutée avec valeur '{nom_source}'")

        df_liste.append(df)

    if not df_liste:
        raise ValueError("Aucun fichier valide n’a été chargé.")

    colonnes_bases = set(df_liste[0].columns)

    if colonnes_communes_only:
        for df in df_liste[1:]:
            colonnes_bases &= set(df.columns)

        if not colonnes_bases:
            raise ValueError("Aucune colonne commune entre les fichiers.")

        colonnes_utilisees = sorted(colonnes_bases)
        df_liste = [df[colonnes_utilisees].copy() for df in df_liste]
        logger.info(f"[Fusion - colonnes communes] Colonnes fusionnées : {colonnes_utilisees}")
    else:
        for i, df in enumerate(df_liste[1:], 1):
            if set(df.columns) != colonnes_bases:
                logger.error(f"[Colonnes divergentes] Fichier #{i} ne correspond pas.")
                raise ValueError("Tous les fichiers doivent avoir les mêmes colonnes. Utilisez 'colonnes_communes_only=True' pour forcer l'intersection.")
        colonnes_utilisees = sorted(colonnes_bases)
        logger.info(f"[Fusion - colonnes identiques] Colonnes fusionnées : {colonnes_utilisees}")

    df_final = pd.concat(df_liste, axis=0, ignore_index=reset_index)

    # ✅ Sauvegarde conditionnelle uniquement si exporter=True
    if exporter and chemin_sortie:
        base, ext = os.path.splitext(chemin_sortie)
        if horodatage_str not in base:
            chemin_sortie = f"{base}_{horodatage_str}{ext}"

        dossier = os.path.dirname(chemin_sortie)
        if dossier and not os.path.exists(dossier):
            os.makedirs(dossier, exist_ok=True)

        try:
            if ext == ".csv":
                df_final.to_csv(chemin_sortie, index=False)
            elif ext in [".xls", ".xlsx"]:
                df_final.to_excel(chemin_sortie, index=False)
            else:
                logger.warning(f"[Sauvegarde ignorée] Format non supporté: {chemin_sortie}")
        except Exception as e:
            logger.error(f"[Erreur sauvegarde] {chemin_sortie} : {e}")
        else:
            logger.info(f"[Fichier sauvegardé] {chemin_sortie}")
    elif exporter:
        logger.warning("[Exporter=True] mais aucun chemin de sauvegarde fourni.")
    else:
        logger.info("[Fusion sans export] Résultat retourné uniquement en mémoire.")

    logger.info(f"[Fusion réussie] {len(df_liste)} fichiers fusionnés, total : {df_final.shape[0]} lignes.")
    return df_final

# Fonction charger fichier avec log
def log_colonnes(df_orig: pd.DataFrame, df_apres: pd.DataFrame, col_funcs: Optional[Dict[str, str]] = None, fichier: str = "") -> pd.DataFrame:
    """
    Construit un journal simple des transformations de colonnes pour un fichier.

    Le log compare l'ordre et les noms des colonnes avant/apres traitement, puis
    annote chaque colonne avec une operation eventuelle comme :
    `standardisation`, `renommage`, `dedoublonnage` ou `ajout_colonne_source`.
    """
    col_funcs = col_funcs or {}
    rows = []
    cols_orig = list(df_orig.columns)
    cols_apres = list(df_apres.columns)
    taille_max = max(len(cols_orig), len(cols_apres))

    for i in range(taille_max):
        orig_col = cols_orig[i] if i < len(cols_orig) else pd.NA
        after_col = cols_apres[i] if i < len(cols_apres) else pd.NA
        fonction_nettoyage = None if pd.isna(after_col) else col_funcs.get(after_col)
        changed = (
            pd.isna(orig_col)
            or pd.isna(after_col)
            or str(orig_col) != str(after_col)
            or fonction_nettoyage is not None
        )
        rows.append({
            "variable": after_col,
            "before": orig_col,
            "after": after_col,
            "changed": changed,
            "fonction_nettoyage": fonction_nettoyage,
            "fichier": fichier
        })
    return pd.DataFrame(rows)
