# -*- coding: utf-8 -*-
# credit_app/colonne_valeur/valeurs_nettoyage.py

"""
Boîte à outils pour nettoyer les valeurs d'un DataFrame (texte, NA, types, dates, mapping Excel).
- Gestion robuste des valeurs manquantes (NA-like)
- Normalisation texte (espaces, underscores, tirets, accents, casse)
- Conversions (numériques, dates FR/EN)
- Remplacements via mapping Excel (exact ou regex, par variable)
"""

from __future__ import annotations

# Standard library
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, List, Union, Optional

# Third-party libraries
import numpy as np
import pandas as pd
from dateutil import parser


# ---------------------------------------------------------------------
# Logging (ne PAS configurer basicConfig ici si module importé ailleurs)
# ---------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Chemin mapping (par défaut)
# ---------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MAPPING_FILE = BASE_DIR / "data" / "Replace_values.xlsx"


# ---------------------------------------------------------------------
# Constantes NA-like
# ---------------------------------------------------------------------
# Stocker en minuscules + comparaison via casefold() pour robustesse.
NA_VALUES = {
    "", " ", "-", "n/a", "na", "nan", "null", "none",
    "<na>", "<nat>", "<null>",
    "inconnu", "non renseigné", "non renseigne", "aucun", "aucune",
    "aucune information", "aucune donnée", "aucune donnee",
    "aucune donnée renseignée", "aucune donnee renseignee",
}


def _is_na_like(val: object) -> bool:
    """Retourne True si val est un NA-like (pd.NA/NaN ou texte NA_VALUES)."""
    if val is None or pd.isna(val):
        return True
    if isinstance(val, str):
        return val.strip().casefold() in NA_VALUES
    return False


def _to_clean_string_series(s: pd.Series) -> pd.Series:
    """
    Convertit une série en dtype 'string' sans casser les NA (évite NaN -> "nan").
    """
    s = s.astype("string")
    # normalise espaces
    s = s.str.strip()
    # vider les chaînes vides et NA texte
    # NB: on ne remplace pas tout NA_VALUES ici (parfois "non" peut être un vrai texte),
    # on garde la stratégie au niveau des fonctions.
    return s


def _read_mapping_dataframe(mapping_file: Union[str, Path], *, require_variable: bool = False) -> pd.DataFrame:
    mapping_path = Path(mapping_file)
    if not mapping_path.exists():
        raise FileNotFoundError(f"Fichier de mapping introuvable : {mapping_path}")

    mapping_df = pd.read_excel(mapping_path, dtype=str)
    mapping_df.columns = [str(c).strip().lower() for c in mapping_df.columns]

    required_cols = {"original", "renamed"}
    if require_variable:
        required_cols.add("variable")

    if not required_cols.issubset(set(mapping_df.columns)):
        raise ValueError(f"Fichier mapping invalide. Colonnes requises : {required_cols}")

    for col in required_cols:
        mapping_df[col] = mapping_df[col].astype("string").str.strip()

    mapping_df = mapping_df.dropna(subset=list(required_cols))
    return mapping_df


# ----------------------------------------------------------
# Utilitaire colonnes cibles
# ----------------------------------------------------------
def get_target_columns(
    df: pd.DataFrame,
    cols: Union[str, List[str], None],
    allow_all_if_none: bool = True
) -> List[str]:
    """
    Résout les colonnes cibles :
    - None => toutes les colonnes (si allow_all_if_none) sinon []
    - str  => [str] si présent
    - list => filtre celles présentes
    """
    if cols is None:
        return df.columns.tolist() if allow_all_if_none else []

    if isinstance(cols, str):
        if cols in df.columns:
            return [cols]
        logger.warning(f"❗ Colonne '{cols}' non trouvée dans le DataFrame.")
        return []

    if isinstance(cols, (tuple, set, pd.Index)):
        cols = list(cols)

    if not isinstance(cols, list):
        raise TypeError("cols doit être None, une chaîne ou une liste de colonnes.")

    cols = list(dict.fromkeys(cols))
    present = [c for c in cols if c in df.columns]
    missing = sorted(set(cols) - set(present))
    if missing:
        logger.warning(f"❗ Colonnes non trouvées : {missing}")
    return present


# ----------------------------------------------------------
# Accents
# ----------------------------------------------------------
def strip_accents(text: object) -> object:
    """
    Supprime les accents d'une chaîne.
    Si text est None/pd.NA/non-str => retourne tel quel.
    """
    if text is None or pd.isna(text) or not isinstance(text, str):
        return text
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


# ----------------------------------------------------------
# Nettoyage valeurs vides (SAFE)
# ----------------------------------------------------------
def nettoyer_valeurs_vides(df: pd.DataFrame, log: bool = False) -> pd.DataFrame:
    """
    Remplace uniquement les valeurs équivalentes à NA par pd.NA,
    sans altérer le texte (pas de normalisation, pas de casse).
    Puis :
      - colonnes texte => NA -> ''
      - colonnes numériques => NA conservé (pd.NA)
    """
    out = df.copy()

    if log:
        logger.setLevel(logging.INFO)

    valeurs_equivalentes = {"<na>", "<NA>", "NaN", "nan", "NAN", "None", "NONE", "none"}

    # Ne traiter que texte
    text_cols = out.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        s = _to_clean_string_series(out[col])
        # remplacer strict
        out[col] = s.where(~s.str.strip().isin(valeurs_equivalentes), other=pd.NA)

    if log:
        logger.info("Remplacement strict des valeurs équivalentes à NA effectué.")

    # texte -> '' (sans normaliser le texte)
    out[text_cols] = out[text_cols].fillna("")

    if log:
        logger.info("Nettoyage des valeurs vides terminé (SAFE).")

    return out


# ----------------------------------------------------------
# Normalisation numéro de téléphone
# ----------------------------------------------------------
def clean_phone_number(
    value: Any,
    country_code: str = "243",
    add_prefix: bool = False,
    return_mode: str = "first",   # "first" | "join" | "list"
    join_sep: str = "; ",
    max_numbers: Optional[int] = None
) -> Union[str, List[str], pd._libs.missing.NAType]:
    """
    Nettoie et normalise des numéros de téléphone de manière CONSERVATIVE (RDC),
    en évitant de perdre des numéros lorsqu'il y en a plusieurs dans une cellule.

    Principes
    ----------
    - Corrige uniquement les erreurs évidentes (espaces, points, parenthèses, tirets, etc.).
    - N'invente PAS de chiffres manquants.
    - Détecte 1+ numéros dans une cellule (séparateurs: / ; , "ou", espaces, etc.).
    - Normalise vers:
        * local (9 chiffres) si add_prefix=False
        * international (+243XXXXXXXXX) si add_prefix=True
    - Retourne pd.NA seulement si aucun numéro RDC valide n'est détectable.

    Validation (RDC)
    ----------------
    Formats acceptés en entrée (après extraction/cleanup) :
      - XXXXXXXXX            (9 chiffres)
      - 0XXXXXXXXX           (10 chiffres)
      - 243XXXXXXXXX         (12 chiffres)
      - +243XXXXXXXXX        (13 avec +, mais on retire le + au parsing)

    Paramètres
    ----------
    value : Any
        Valeur brute (int, str, NaN…)
    country_code : str
        Code pays sans '+' (défaut '243')
    add_prefix : bool
        False => retourne local (9 chiffres)
        True  => retourne +243 + local
    return_mode : str
        "first" => retourne le premier numéro valide (comme ta fonction actuelle)
        "join"  => retourne tous les numéros valides concaténés (join_sep)
        "list"  => retourne une liste de numéros valides
    join_sep : str
        Séparateur si return_mode="join"
    max_numbers : int | None
        Limiter le nombre de numéros retournés (ex: 2). None => pas de limite.

    Retour
    ------
    str | list[str] | pd.NA
    """

    if value is None or pd.isna(value):
        return pd.NA

    s = str(value).strip().replace("\xa0", " ")
    if s == "":
        return pd.NA

    # Petites corrections non destructives (O -> 0 au début d'un bloc, points/parenthèses, etc.)
    # (utile pour des cas comme "O997195079")
    s = re.sub(r"(?<!\w)[oO](?=\d)", "0", s)

    # Extraire blocs candidats: on permet +, digits, espaces, /, ;, -, (, ), .
    # Puis on extraira les sous-séquences numériques.
    candidates = re.findall(r"[+\d][\d\s()/\-.]{6,}", s)

    # Si rien trouvé, fallback: chercher directement des séquences de chiffres
    if not candidates:
        candidates = [s]

    found: List[str] = []
    seen = set()

    def normalize_digits(digits: str) -> Optional[str]:
        """Retourne local 9 chiffres ou None si invalide."""
        # 243XXXXXXXXX
        if digits.startswith(country_code) and len(digits) == 12:
            return digits[len(country_code):]
        # 0XXXXXXXXX
        if digits.startswith("0") and len(digits) == 10:
            return digits[1:]
        # XXXXXXXXX
        if len(digits) == 9:
            return digits
        return None

    for block in candidates:
        # Dans chaque bloc, on récupère toutes les séquences de 7 à 15 chiffres (avec + optionnel)
        subs = re.findall(r"\+?\d{7,15}", block)
        for sub in subs:
            digits = re.sub(r"\D", "", sub)
            local = normalize_digits(digits)
            if local is None:
                continue

            out_num = f"+{country_code}{local}" if add_prefix else local

            # dédoublonnage conservateur
            if out_num not in seen:
                seen.add(out_num)
                found.append(out_num)

            if max_numbers is not None and len(found) >= max_numbers:
                break
        if max_numbers is not None and len(found) >= max_numbers:
            break

    if not found:
        return pd.NA

    if return_mode == "first":
        return found[0]
    if return_mode == "join":
        return join_sep.join(found)
    if return_mode == "list":
        return found

    raise ValueError("return_mode doit être 'first', 'join' ou 'list'")

# ----------------------------------------------------------
# Normalisation  Email
# ----------------------------------------------------------
def clean_email_address(
    value: Any,
    return_mode: str = "first",          # "first" | "join" | "list"
    join_sep: str = "; ",
    max_emails: Optional[int] = None,
    allow_domain_completion: bool = False
) -> Union[str, List[str], pd._libs.missing.NAType]:
    """
    Nettoie et corrige une adresse email de manière CONSERVATIVE, sans supprimer
    les emails valides, et en gérant le cas de plusieurs emails dans une cellule.

    Principes
    ----------
    - Corrige uniquement les erreurs manifestes et fréquentes (espaces, ponctuations finales,
      fautes typiques de frappe sur gmail, séparateurs, etc.).
    - Ne supprime JAMAIS une adresse email valide.
    - Par défaut, N'INVENTE PAS de domaine (ex: ne complète pas '@gmail' en '@gmail.com').
      -> Si tu veux activer la complétion ciblée, mets allow_domain_completion=True.
    - Si plusieurs emails sont présents, tu peux :
        * return_mode="first" : retourner le 1er email valide
        * return_mode="join"  : retourner tous les emails valides concaténés
        * return_mode="list"  : retourner une liste d’emails valides
    - Retourne pd.NA uniquement si aucun email valide n'est détectable.

    Corrections appliquées (non destructives)
    ----------------------------------------
    - Trim, lower, suppression des espaces invisibles (\\xa0)
    - Normalisation des séparateurs : <>, /, ;, "," et "ou"
    - Corrections de typos courantes :
        * "gmail,com"  -> "gmail.com"
        * "gma il.com" -> "gmail.com"
        * "gamil.com"  -> "gmail.com"
        * "gamail.com" -> "gmail.com"
        * "gmqil.com"  -> "gmail.com"
        * "ygmail.com" -> "gmail.com"
        * "@gmail.co"  -> "@gmail.com"
        * ponctuations finales: ".", ",", ";", ")", "]", "}" ...
    - Optionnel (allow_domain_completion=True) :
        * "nellyayela66@ com gmail" -> "nellyayela66@gmail.com"
        * "x@gmail" -> "x@gmail.com"
        (complétion UNIQUEMENT pour gmail)

    Paramètres
    ----------
    value : Any
        Valeur brute (str, NaN…)
    return_mode : str
        "first" | "join" | "list"
    join_sep : str
        séparateur si return_mode="join"
    max_emails : int | None
        limite du nombre d’emails retournés
    allow_domain_completion : bool
        Active la complétion ciblée pour gmail (False par défaut)

    Retour
    ------
    str | list[str] | pd.NA
    """

    # ------------------------------------------------------------------
    # 0) Valeurs manquantes
    # ------------------------------------------------------------------
    if value is None or pd.isna(value):
        return pd.NA

    s = str(value).strip().lower().replace("\xa0", " ")
    if s == "":
        return pd.NA

    # ------------------------------------------------------------------
    # 1) Normalisation des séparateurs / wrappers
    # ------------------------------------------------------------------
    s = re.sub(r"[<>]", " ", s)
    s = re.sub(r"\s+ou\s+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"[;/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # ------------------------------------------------------------------
    # 2) Corrections ciblées NON destructives (typos fréquentes)
    # ------------------------------------------------------------------
    corrections = [
        (r"\s*@\s*", "@"),
        (r"\s*\.\s*", "."),
        (r"\s*,\s*", ","),
        (r",com\b", ".com"),
        (r"@gmail\.co\b", "@gmail.com"),
        (r"gma\s*il\.com\b", "gmail.com"),
        (r"gamil\.com\b", "gmail.com"),
        (r"gamail\.com\b", "gmail.com"),
        (r"gmqil\.com\b", "gmail.com"),
        (r"ygmail\.com\b", "gmail.com"),
    ]

    for pattern, repl in corrections:
        s = re.sub(pattern, repl, s, flags=re.IGNORECASE)

    # ------------------------------------------------------------------
    # 3) Complétion TRÈS ciblée (gmail uniquement, optionnelle)
    # ------------------------------------------------------------------
    if allow_domain_completion:
        s = re.sub(r"@?\s*com\s+gmail\b", "@gmail.com", s, flags=re.IGNORECASE)
        s = re.sub(r"@\s*gmail\b", "@gmail.com", s, flags=re.IGNORECASE)
        s = re.sub(r"@gmail\b(?!\.)", "@gmail.com", s, flags=re.IGNORECASE)

    # ------------------------------------------------------------------
    # 4) Suppression générique des TLD dupliqués
    #    ex: .com.com, .org.org, .co.co → .com / .org / .co
    # ------------------------------------------------------------------
    s = re.sub(r"(\.[a-z]{2,})(?:\1)+\b", r"\1", s, flags=re.IGNORECASE)

    # ------------------------------------------------------------------
    # 5) Nettoyage des ponctuations finales parasites
    # ------------------------------------------------------------------
    s = re.sub(r"[\s\)\]\}\>,;]+$", "", s)

    # ------------------------------------------------------------------
    # 6) Extraction des emails valides
    # ------------------------------------------------------------------
    email_pattern = r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}"
    emails = re.findall(email_pattern, s)

    if not emails:
        return pd.NA

    # ------------------------------------------------------------------
    # 7) Déduplication conservative + sécurité TLD
    # ------------------------------------------------------------------
    seen = set()
    cleaned: List[str] = []

    for e in emails:
        e = e.strip().strip(".,;:")
        e = re.sub(r"(\.[a-z]{2,})(?:\1)+\b", r"\1", e, flags=re.IGNORECASE)

        if e and e not in seen:
            seen.add(e)
            cleaned.append(e)

        if max_emails is not None and len(cleaned) >= max_emails:
            break

    if not cleaned:
        return pd.NA

    # ------------------------------------------------------------------
    # 8) Format de sortie
    # ------------------------------------------------------------------
    if return_mode == "first":
        return cleaned[0]

    if return_mode == "join":
        return join_sep.join(cleaned)

    if return_mode == "list":
        return cleaned

    raise ValueError("return_mode doit être 'first', 'join' ou 'list'")

# ----------------------------------------------------------
# Normalisation texte (vectorisée)
# ----------------------------------------------------------
def normaliser_values(
    df: pd.DataFrame,
    cols: Union[str, List[str]],
    case_option: str = "title",
    remove_accents: bool = False,
    log: bool = True
) -> pd.DataFrame:
    """
    Normalise des colonnes texte :
    1. Supprime les espaces en début/fin
    2. Remplace '-' et '_' par un espace
    3. Réduit les espaces multiples à un seul
    4. Capitalisation selon style :
       - "upper" : tout en majuscule
       - "lower" : tout en minuscule
       - "capitalize" : première lettre du texte en majuscule
       - "title" : première lettre de chaque mot en majuscule (par défaut)
    5. Supprime les accents si remove_accents=True
    
    """
    out = df.copy()
    cols_list = get_target_columns(out, cols)

    valid_case = {"upper", "lower", "capitalize", "title", "none"}
    if case_option not in valid_case:
        raise ValueError(f"case_option doit être dans {valid_case}")

    for col in cols_list:
        s = _to_clean_string_series(out[col])

        # préserver NA
        mask_na = s.isna()

        s = s.str.replace(r"[-_]", " ", regex=True)
        s = s.str.replace(r"\s+", " ", regex=True)

        if remove_accents:
            s = s.map(lambda x: strip_accents(x) if isinstance(x, str) else x)

        if case_option == "upper":
            s = s.str.upper()
        elif case_option == "lower":
            s = s.str.lower()
        elif case_option == "capitalize":
            s = s.str.capitalize()
        elif case_option == "title":
            s = s.str.title()
        else:  # none
            pass

        s = s.where(~mask_na, other=pd.NA)
        out[col] = s

        if log:
            logger.info(f"Colonne '{col}' normalisée.")

    return out


# ----------------------------------------------------------
# Mapping Excel (simple)
# ----------------------------------------------------------
def replace_specific_values(
    df: pd.DataFrame,
    mapping_file: Union[str, Path] = DEFAULT_MAPPING_FILE,
    log: bool = True
) -> pd.DataFrame:
    """
    Remplace des valeurs dans toutes les colonnes texte selon un mapping Excel.
    Mapping attendu : 2 premières colonnes = (original, renamed)
    """
    mapping_df = _read_mapping_dataframe(mapping_file, require_variable=False)
    replace_dict = dict(zip(mapping_df["original"], mapping_df["renamed"]))

    out = df.copy()
    text_cols = out.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        out[col] = out[col].replace(replace_dict)

    if log:
        logger.info(f"Mapping (simple) appliqué sur {len(text_cols)} colonnes texte.")

    return out


# ----------------------------------------------------------
# Vérifier regex mapping par variable
# ----------------------------------------------------------
def verifier_regex_mapping(
    fichier_mapping: Union[str, Path] = DEFAULT_MAPPING_FILE,
    variable: str = ""
) -> None:
    df_map = _read_mapping_dataframe(fichier_mapping, require_variable=True)
    if variable:
        df_var = df_map[df_map["variable"].astype(str).str.lower() == str(variable).lower()]
    else:
        df_var = df_map

    valides, invalides = [], []
    for _, row in df_var.iterrows():
        pattern = str(row["original"]).strip()
        try:
            re.compile(pattern)
            valides.append(pattern)
        except re.error as e:
            invalides.append((pattern, str(e)))

    logger.info(f"✔️ Regex valides ({len(valides)}):")
    for p in valides:
        logger.info(f"  - {p}")

    if invalides:
        logger.warning(f"❌ Regex invalides ({len(invalides)}):")
        for p, err in invalides:
            logger.warning(f"  - {p} → {err}")
    else:
        logger.info("✅ Toutes les regex sont valides.")


# ----------------------------------------------------------
# Mapping Excel par critère (exact ou regex)
# ----------------------------------------------------------
def replace_specific_values_critere(
    df: pd.DataFrame,
    mapping_file: Union[str, Path] = DEFAULT_MAPPING_FILE,
    critere: Optional[Dict[str, str]] = None,
    regex_mode: bool = False,
    clean_before: bool = True,
    strip_lower: bool = True,
    verifier_regex_avant: bool = False,
    log_clean_preview: bool = False
) -> pd.DataFrame:
    """
    Remplace les valeurs selon un mapping Excel avec colonnes:
      - original
      - renamed
      - variable

    critere : dict {colonne_df: variable_mapping}
    regex_mode : si True => mapping regex (fullmatch)
    clean_before : strip / option lower avant matching
    """
    critere = critere or {}
    mapping_df = _read_mapping_dataframe(mapping_file, require_variable=True)

    if regex_mode and verifier_regex_avant:
        for var in set(critere.values()):
            verifier_regex_mapping(mapping_file, var)

    out = df.copy()

    for col_df, variable_mapping in critere.items():
        if col_df not in out.columns:
            logger.warning(f"[Nettoyage ignoré] Colonne '{col_df}' absente du DataFrame.")
            continue

        sous_mapping = mapping_df[mapping_df["variable"].astype(str).str.lower() == str(variable_mapping).lower()]
        if sous_mapping.empty:
            logger.warning(f"[Nettoyage ignoré] Aucun mapping trouvé pour '{variable_mapping}'.")
            continue

        logger.info(f"[Nettoyage] '{col_df}' → variable '{variable_mapping}' ({len(sous_mapping)} lignes)")

        s = out[col_df]

        if clean_before:
            s = _to_clean_string_series(s)
            if strip_lower:
                s = s.str.lower()

            if log_clean_preview:
                apercu = s.dropna().unique()[:5]
                logger.info(f"[Prétraitement] Exemples '{col_df}': {apercu}")

        # Mapping exact
        if not regex_mode:
            keys = sous_mapping["original"].astype(str).str.strip()
            vals = sous_mapping["renamed"].astype(str).str.strip()

            if strip_lower:
                keys = keys.str.lower()

            replace_dict = dict(zip(keys, vals))
            s = s.replace(replace_dict)

            logger.info(f"[Mapping exact] {len(replace_dict)} correspondances appliquées à '{col_df}'")

        # Mapping regex (fullmatch)
        else:
            patterns = []
            erreurs = 0
            for _, row in sous_mapping.iterrows():
                original = str(row["original"]).strip()
                renamed = str(row["renamed"]).strip()
                try:
                    patterns.append((re.compile(original, re.IGNORECASE), renamed))
                except re.error as e:
                    erreurs += 1
                    logger.warning(f"[Regex ignorée] '{original}' → {e}")

            def apply_regex(v):
                if v is None or pd.isna(v):
                    return pd.NA
                v_str = str(v).strip()
                for pat, rep in patterns:
                    if pat.fullmatch(v_str):
                        return rep
                return v

            s = s.map(apply_regex)

            logger.info(f"[Mapping regex] {len(patterns)} patterns valides appliqués à '{col_df}'")
            if erreurs:
                logger.warning(f"[Mapping regex] {erreurs} regex invalides ignorées pour '{variable_mapping}'")

        out[col_df] = s

    return out


# ----------------------------------------------------------
# Nettoyages simples (casse) via NA_VALUES
# ----------------------------------------------------------
def clean_first_letter_values(df: pd.DataFrame, cols: Union[str, List[str], None] = None) -> pd.DataFrame:
    out = df.copy()
    cols_list = get_target_columns(out, cols)

    for col in cols_list:
        s = _to_clean_string_series(out[col])
        s = s.map(lambda v: "" if _is_na_like(v) else str(v).strip().title())
        out[col] = s

    return out


def clean_first_letter_only_values(df: pd.DataFrame, cols: Union[str, List[str], None] = None) -> pd.DataFrame:
    out = df.copy()
    cols_list = get_target_columns(out, cols)

    for col in cols_list:
        s = out[col]

        def f(v):
            if isinstance(v, (list, dict, pd.Series)):
                v = str(v)
            if _is_na_like(v):
                return ""
            return str(v).strip().capitalize()

        out[col] = s.map(f)

    return out


def clean_uppercase_values(df: pd.DataFrame, cols: Union[str, List[str], None] = None) -> pd.DataFrame:
    out = df.copy()
    cols_list = get_target_columns(out, cols)

    for col in cols_list:
        s = _to_clean_string_series(out[col])
        s = s.map(lambda v: pd.NA if _is_na_like(v) else str(v).strip().upper())
        out[col] = s.astype("string")

    return out


# ----------------------------------------------------------
# Nettoyage global (flexible)
# ----------------------------------------------------------
def clean_all_values(
    df: pd.DataFrame,
    cols: Union[str, List[str], None] = None,
    case_option: str = "none",
    remove_accents: bool = False,
    convert_type: bool = True,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Nettoie les valeurs d'un DataFrame sur les colonnes spécifiées (ou toutes si None).

    - Remplace les NA-like par pd.NA
    - strip + espaces multiples
    - option: supprimer accents
    - option: transformer casse
    - option: convertir numériques et dates (par cellule, donc plus lent)
    """
    out = df.copy()

    valid_case_options = {"none", "upper", "capitalize", "lower", "title"}
    if case_option not in valid_case_options:
        raise ValueError(f"case_option doit être l'un de {valid_case_options}")

    case_transforms = {
        "upper": str.upper,
        "capitalize": str.capitalize,
        "lower": str.lower,
        "title": str.title,
        "none": lambda x: x
    }

    cols_list = get_target_columns(out, cols)

    def clean_val(v):
        if _is_na_like(v):
            return pd.NA

        v_str = str(v).strip()
        v_str = re.sub(r"\s+", " ", v_str)

        if remove_accents:
            v_str = strip_accents(v_str)

        v_str = case_transforms[case_option](v_str)

        if convert_type:
            # numérique
            try:
                num = pd.to_numeric(v_str)
                return num
            except Exception:
                if verbose:
                    logger.info(f"Conversion numérique échouée : {v_str}")

            # date (retour en datetime64 normalisé pour cohérence pandas)
            try:
                dt = pd.to_datetime(v_str, errors="coerce", dayfirst=True)
                if pd.notna(dt):
                    return pd.Timestamp(dt).normalize()
            except Exception:
                if verbose:
                    logger.info(f"Conversion date échouée : {v_str}")

        return v_str

    for col in cols_list:
        if verbose:
            logger.info(f"Traitement de la colonne : {col}")
        out[col] = out[col].map(clean_val)

        # tentative conversion int si float sans décimales
        if convert_type and pd.api.types.is_numeric_dtype(out[col]):
            if pd.api.types.is_float_dtype(out[col]):
                try:
                    out[col] = out[col].astype("Int64")
                except Exception as e:
                    if verbose:
                        logger.info(f"Conversion Int64 échouée sur {col} : {e}")

    return out


# ----------------------------------------------------------
# Conversions dates
# ----------------------------------------------------------
def convert_column_to_date(
    df: pd.DataFrame,
    colonnes: Union[str, List[str]],
    lang: str = "en",
    output: str = "datetime"
) -> pd.DataFrame:
    """
    Convertit une ou plusieurs colonnes contenant des dates hétérogènes
    vers un format interne universel basé sur pandas (ISO-8601).

    -------------------------------------------------------------------
    🧠 PHILOSOPHIE GÉNÉRALE (BEST PRACTICE)
    -------------------------------------------------------------------
    - Les données d'entrée peuvent être locales, humaines et ambiguës :
        * formats FR (12/01/2026)
        * formats EN (01/12/2026)
        * dates Excel (45234)
        * formats ISO (2026-01-12)
        * dates textuelles
    - La représentation interne DOIT être :
        * universelle
        * non ambiguë
        * indépendante de la langue
        → pandas datetime64[ns] (ISO-8601)

    -------------------------------------------------------------------
    PARAMÈTRES
    -------------------------------------------------------------------
    df : pd.DataFrame
        DataFrame source

    colonnes : str ou list[str]
        Nom(s) des colonnes à convertir

    lang : {"fr", "en", "all"}, default="en"
        Sert UNIQUEMENT à l'interprétation de l'entrée.
        - "fr"  : privilégie JJ/MM/YYYY
        - "en"  : privilégie MM/DD/YYYY
        - "all" : accepte les deux mais bloque les ambiguïtés

    output : {"datetime", "pandas_date", "date"}, default="datetime"
        Format de sortie :
        - "datetime"    -> pandas datetime64[ns] (STANDARD, recommandé)
        - "pandas_date" -> datetime64[ns] normalisé à minuit
        - "date"        -> python datetime.date (pour export)

    -------------------------------------------------------------------
    RETOUR
    -------------------------------------------------------------------
    pd.DataFrame
        DataFrame avec colonnes converties
    """
    out = df.copy()
    cols = get_target_columns(out, colonnes, allow_all_if_none=False)
    if not cols:
        return out

    if lang not in {"fr", "en", "all"}:
        raise ValueError("lang doit être 'fr', 'en' ou 'all'.")
    if output not in {"datetime", "pandas_date", "date"}:
        raise ValueError("output doit être 'datetime', 'pandas_date' ou 'date'.")

    # Formats numériques explicites (STRICTS → évitent les inversions)
    formats_fr = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]
    formats_en = ["%m/%d/%Y", "%m-%d-%Y", "%m.%d.%Y"]

    if lang == "fr":
        formats_to_try = formats_fr
        dayfirst = True
    elif lang == "en":
        formats_to_try = formats_en
        dayfirst = False
    else:
        formats_to_try = formats_fr + formats_en
        dayfirst = True  # par défaut, on favorise FR mais on reste strict

    month_map_fr_to_en = {
        "janvier": "january",
        "janv": "jan",
        "fevrier": "february",
        "fevr": "feb",
        "fev": "feb",
        "mars": "march",
        "avril": "april",
        "avr": "apr",
        "mai": "may",
        "juin": "june",
        "juillet": "july",
        "juil": "jul",
        "aout": "august",
        "septembre": "september",
        "sept": "sep",
        "octobre": "october",
        "novembre": "november",
        "decembre": "december",
        "dec": "dec",
    }
    month_pattern = re.compile(
        r"\b(" + "|".join(sorted(month_map_fr_to_en, key=len, reverse=True)) + r")\.?\b"
    )
    pattern_numeric_date = re.compile(
        r"^\s*\d{1,4}[./-]\d{1,2}[./-]\d{1,4}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?\s*$"
    )

    def normalize_date_text(x: str) -> str:
        """Normalise les mois FR et quelques variantes avant parsing."""
        x_norm = strip_accents(x).lower().strip()
        x_norm = re.sub(r"\b1er\b", "1", x_norm)
        x_norm = re.sub(r"\s+", " ", x_norm)
        return month_pattern.sub(lambda m: month_map_fr_to_en[m.group(1)], x_norm)

    def expand_year_token(token: str) -> int:
        """
        Répare les années courtes:
        - %y suit le pivot standard de Python/pandas
        - 206 -> 2026 (heuristique utile sur les saisies modernes tronquées)
        """
        year = int(token)
        if len(token) == 2:
            return 2000 + year if year <= 68 else 1900 + year
        if len(token) == 3:
            reference_year = pd.Timestamp.today().year
            candidates = []
            for candidate in range(1900, 2101):
                candidate_str = str(candidate)
                for idx in range(len(candidate_str)):
                    if candidate_str[:idx] + candidate_str[idx + 1:] == token:
                        candidates.append(candidate)
                        break
            if candidates:
                return min(candidates, key=lambda candidate: abs(candidate - reference_year))
            return 2000 + year
        return year

    def build_timestamp(
        year_token: str,
        month_token: str,
        day_token: str,
        hour_token: Optional[str] = None,
        minute_token: Optional[str] = None,
        second_token: Optional[str] = None,
    ):
        try:
            return pd.Timestamp(
                year=expand_year_token(year_token),
                month=int(month_token),
                day=int(day_token),
                hour=int(hour_token or 0),
                minute=int(minute_token or 0),
                second=int(second_token or 0),
            )
        except Exception:
            return pd.NaT

    def parse_numeric_date(x: str):
        """
        Parse strict des dates numériques avec gestion:
        - FR/EN
        - YYYY-MM-DD
        - suffixe heure
        - années tronquées du type 206 -> 2026
        """
        match = re.fullmatch(
            r"\s*(\d{1,4})[./-](\d{1,2})[./-](\d{1,4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?\s*",
            x,
        )
        if not match:
            return pd.NaT

        a, b, c, hh, mm, ss = match.groups()

        if len(a) >= 3 and len(c) <= 2:
            return build_timestamp(a, b, c, hh, mm, ss)

        if lang == "fr":
            candidates = [(c, b, a), (c, a, b)]
        elif lang == "en":
            candidates = [(c, a, b), (c, b, a)]
        else:
            if int(a) > 12 and int(b) <= 12:
                candidates = [(c, b, a)]
            elif int(b) > 12 and int(a) <= 12:
                candidates = [(c, a, b)]
            else:
                return parse_numeric_date(x)

        for year_token, month_token, day_token in candidates:
            dt = build_timestamp(year_token, month_token, day_token, hh, mm, ss)
            if pd.notna(dt):
                return dt

        return pd.NaT

    for col in cols:
        if col not in out.columns:
            logger.warning(f"Colonne '{col}' non trouvée. Ignorée.")
            continue

        try:
            # ------------------------------------------------------------
            # 0) Nettoyage de base (espaces, NA, chaînes)
            # ------------------------------------------------------------
            s = _to_clean_string_series(out[col])
            s = s.map(lambda v: pd.NA if _is_na_like(v) else v)
            s_normalized = s.map(normalize_date_text, na_action="ignore")

            # ------------------------------------------------------------
            # 1) Détection et conversion des dates Excel (serial)
            # ------------------------------------------------------------
            s_num = pd.to_numeric(s, errors="coerce")
            mask_excel = s_num.notna() & s_num.between(20000, 80000)

            dt_excel = pd.to_datetime(
                s_num.where(mask_excel),
                unit="D",
                origin="1899-12-30",
                errors="coerce"
            )

            # ------------------------------------------------------------
            # 2) Dates numériques ambiguës JJ/MM/YYYY ou MM/JJ/YYYY
            #    → conversion STRICTE uniquement
            # ------------------------------------------------------------
            mask_numeric = s_normalized.str.match(pattern_numeric_date, na=False)

            temp = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

            def parse_strict(x: str):
                """Essaye uniquement les formats autorisés (STRICT)."""
                for fmt in formats_to_try:
                    try:
                        return pd.to_datetime(x, format=fmt, errors="raise")
                    except Exception:
                        pass
                return pd.NaT

            temp.loc[mask_numeric] = pd.to_datetime(
                s_normalized.loc[mask_numeric].map(parse_numeric_date),
                errors="coerce"
            )

            # ------------------------------------------------------------
            # 3) Fallback générique (ISO, timestamps, texte NON ambigu)
            #    ⚠️ INTERDIT pour dates numériques ambiguës
            # ------------------------------------------------------------
            mask_fallback = (
                temp.isna() &
                s.notna() &
                (~mask_excel) &
                (~mask_numeric)
            )

            def parse_generic(x: str):
                """Fallback sûr pour ISO, timestamps, textes."""
                # pandas d'abord (rapide, ISO-friendly)
                dt = pd.to_datetime(x, errors="coerce", dayfirst=dayfirst)
                if pd.notna(dt):
                    return pd.Timestamp(dt)
                # dateutil en dernier recours
                try:
                    return pd.Timestamp(parser.parse(x, dayfirst=dayfirst))
                except Exception:
                    return pd.NaT

            if mask_fallback.any():
                fallback_parsed = s_normalized.loc[mask_fallback].map(parse_generic)
                temp.loc[mask_fallback] = pd.to_datetime(fallback_parsed, errors="coerce")

            # ------------------------------------------------------------
            # 4) Priorité ABSOLUE aux dates Excel
            # ------------------------------------------------------------
            temp.loc[mask_excel] = dt_excel.loc[mask_excel]

            # ------------------------------------------------------------
            # 5) Format de sortie
            # ------------------------------------------------------------
            if output == "datetime":
                out[col] = temp
            elif output == "pandas_date":
                out[col] = temp.dt.normalize()
            elif output == "date":
                out[col] = temp.dt.date
            else:
                raise ValueError("output doit être 'datetime', 'pandas_date' ou 'date'")

            nb_ok = out[col].notna().sum()
            logger.info(
                f"Colonne '{col}' convertie "
                f"({nb_ok}/{len(out[col])} valeurs valides)."
            )

        except Exception as e:
            logger.error(
                f"Erreur lors de la conversion de la colonne '{col}': {e}"
            )

    return out

def convert_column_to_time(
    df: pd.DataFrame,
    colonnes: Union[str, List[str]],
    output: str = "time"  # "time" | "string"
) -> pd.DataFrame:
    """
    Nettoie et convertit une ou plusieurs colonnes heure en format standard.

    Formats supportés :
    - 08:30, 8:30
    - 08:30:15
    - 8h30, 8H30
    - 0830, 830

    output:
        - "time"   -> datetime.time
        - "string" -> "HH:MM:SS"
    """

    out = df.copy()
    cols = get_target_columns(out, colonnes, allow_all_if_none=False)
    if not cols:
        return out
    if output not in {"time", "string"}:
        raise ValueError("output doit être 'time' ou 'string'.")

    def clean_time(val):
        if pd.isna(val):
            return pd.NaT

        v = str(val).strip().lower()

        # ----------------------------
        # 1. Normalisation de base
        # ----------------------------
        v = v.replace("h", ":")
        v = re.sub(r"[^\d:]", "", v)  # garder chiffres + :

        # ----------------------------
        # 2. Cas type 0830 ou 830
        # ----------------------------
        if re.match(r"^\d{3,4}$", v):
            v = v.zfill(4)
            v = f"{v[:2]}:{v[2:]}"

        # ----------------------------
        # 3. Ajouter secondes si absentes
        # ----------------------------
        if re.match(r"^\d{1,2}:\d{2}$", v):
            v = f"{v}:00"

        # ----------------------------
        # 4. Validation finale
        # ----------------------------
        try:
            t = pd.to_datetime(v, format="%H:%M:%S", errors="coerce")
            if pd.isna(t):
                return parse_numeric_date(x)
            return t.time()
        except Exception:
            return pd.NaT

    for col in cols:
        if col not in out.columns:
            logger.warning(f"Colonne '{col}' non trouvée.")
            continue

        out[col] = out[col].apply(clean_time)

        if output == "string":
            out[col] = out[col].map(lambda x: x.strftime("%H:%M:%S") if pd.notna(x) else pd.NA).astype("string")

        nb_ok = out[col].notna().sum()
        logger.info(f"Colonne '{col}' nettoyée ({nb_ok}/{len(out[col])})")

    return out

# ----------------------------------------------------------
# Conversions numériques
# ----------------------------------------------------------
def convert_float_to_int(df: pd.DataFrame, cols: Union[str, List[str], None] = None) -> pd.DataFrame:
    """Convertit float en Int64 nullable (sans arrondi : 12.0 -> 12 ; 12.7 -> 12 si cast possible)."""
    out = df.copy()
    cols_list = get_target_columns(out, cols)

    for col in cols_list:
        s = pd.to_numeric(out[col], errors="coerce")
        out[col] = s.map(lambda x: int(x) if pd.notna(x) else pd.NA).astype("Int64")

    return out


def convert_float_to_int_arrondi(df: pd.DataFrame, cols: Union[str, List[str], None] = None) -> pd.DataFrame:
    """Convertit float en Int64 nullable avec arrondi."""
    out = df.copy()
    cols_list = get_target_columns(out, cols)

    for col in cols_list:
        s = pd.to_numeric(out[col], errors="coerce")
        out[col] = s.map(lambda x: int(round(x)) if pd.notna(x) else pd.NA).astype("Int64")

    return out


def convertir_en_int(df: pd.DataFrame, colonnes: Union[str, List[str], None] = None) -> pd.DataFrame:
    """Convertit colonnes en Int64 nullable en arrondissant avant conversion."""
    out = df.copy()
    cols_list = get_target_columns(out, colonnes)

    for col in cols_list:
        serie = out[col]
        serie_num = pd.to_numeric(serie, errors="coerce")
        out[col] = serie_num.round(0).astype("Int64")

    return out


# ----------------------------------------------------------
# Nettoyage tirets/espaces + chiffres romains
# ----------------------------------------------------------
def nettoyer_tiret_et_espaces(texte: str) -> Optional[str]:
    if not texte:
        return None

    texte = texte.replace("-", " ")
    texte = re.sub(r"\s+", " ", texte).strip()

    romain_map = {r"\bI\b": "1", r"\bII\b": "2", r"\bIII\b": "3"}
    for romain, arabe in romain_map.items():
        texte = re.sub(romain, arabe, texte, flags=re.IGNORECASE)

    return texte


# ----------------------------------------------------------
# Underscores / espaces
# ----------------------------------------------------------
def remplacer_underscores(df: pd.DataFrame, colonnes: Union[str, List[str]]) -> pd.DataFrame:
    """
    Remplace '_' et '-' par des espaces, puis lower().title().
    Conserve les NA.
    """
    out = df.copy()
    cols_list = [colonnes] if isinstance(colonnes, str) else list(colonnes)

    for col in cols_list:
        if col not in out.columns:
            continue

        s = _to_clean_string_series(out[col])
        out[col] = s.map(
            lambda v: pd.NA if _is_na_like(v) else str(v).replace("_", " ").replace("-", " ").strip().lower().title()
        )

    return out


def remplacer_espaces_par_underscores(df: pd.DataFrame, colonnes: Union[str, List[str]]) -> pd.DataFrame:
    """
    Remplace espaces (même multiples) par underscore, supprime underscores multiples,
    puis capitalize chaque morceau séparé par underscore.
    Conserve les NA.
    """
    out = df.copy()
    cols_list = [colonnes] if isinstance(colonnes, str) else list(colonnes)

    for col in cols_list:
        if col not in out.columns:
            continue

        s = _to_clean_string_series(out[col])

        def transformer(v):
            if _is_na_like(v):
                return pd.NA
            val = str(v).strip()
            val = re.sub(r"\s+", "_", val)
            val = re.sub(r"_+", "_", val)
            mots = [m.capitalize() for m in val.split("_") if m]
            return "_".join(mots)

        out[col] = s.map(transformer)

    return out


# ----------------------------------------------------------
# Découpage valeurs (prefixe/nom/suffixe)
# ----------------------------------------------------------
def trouve_caractere(provenance: str, valeur_avant: str, valeur_apres: str) -> str:
    """Extrait la sous-chaîne entre valeur_avant et valeur_apres."""
    try:
        start = provenance.index(valeur_avant) + len(valeur_avant)
        end = provenance.index(valeur_apres, start)
        return provenance[start:end]
    except ValueError:
        return ""


def extraire_prefixe(texte: str, longueur: int = 1, mode: str = "mot") -> Optional[str]:
    if not texte:
        return None
    texte = texte.strip()

    if mode == "mot":
        mots = texte.split()
        return " ".join(mots[:longueur]) if mots else None
    if mode == "caractere":
        return texte[:longueur]
    raise ValueError("Le paramètre 'mode' doit être 'mot' ou 'caractere'")


def extraire_nom_generique(texte: str) -> Optional[str]:
    """
    Extrait le nom générique : supprime 1er mot (préfixe) et suffixes connus.
    """
    if not texte:
        return None

    mots = texte.strip().split()
    if len(mots) <= 2:
        return None

    mots = mots[1:]  # enlever préfixe

    suffixes = {
        "province",
        "zone de santé", "zone de sante",
        "aire de santé", "aire de sante",
        "centre de santé", "centre de sante",
        "dispensaire",
        "centre de santé de référence",
    }

    while mots:
        max_len = min(4, len(mots))
        removed = False
        for l in range(max_len, 0, -1):
            fin = " ".join(mots[-l:]).lower()
            if fin in suffixes:
                del mots[-l:]
                removed = True
                break
        if not removed:
            break

    return " ".join(mots) if mots else None


def extraire_suffixe(texte: str, longueur: int = 1, mode: str = "mot") -> Optional[str]:
    if not texte:
        return None
    texte = texte.strip()

    if mode == "mot":
        mots = texte.split()
        return " ".join(mots[-longueur:]) if mots else None
    if mode == "caractere":
        return texte[-longueur:] if texte else None
    raise ValueError("Le paramètre 'mode' doit être 'mot' ou 'caractere'")


# ----------------------------------------------------------
# Extraction texte/nombre (âge etc.)
# ----------------------------------------------------------
def extraire_texte_et_nombre(
    cellule: Union[str, int, float, List[Union[str, int, float]]],
    valeur_par_defaut: str = "mois",
    detecter_annee: bool = True,
    normaliser_texte: bool = True,
    mode: str = "both"  # "texte", "nombre", "both"
) -> Union[str, int, dict, List[Union[str, int, dict]]]:

    def detecter_unite_et_nombre(elem_str: str):
        elem_str = elem_str.lower().strip()

        pattern_annee = r"\b(an|ans|année|années|a)\b"
        pattern_mois = r"\b(mois|moi|m)\b"
        pattern_jour = r"\b(jour|jours|jr|jrs|j)\b"

        if detecter_annee and re.search(pattern_annee, elem_str):
            unite = "ans" if normaliser_texte else re.search(pattern_annee, elem_str).group(0)
        elif re.search(pattern_mois, elem_str):
            unite = "mois"
        elif re.search(pattern_jour, elem_str):
            unite = "jours"
        else:
            match_abrev = re.search(r"(\d+)\s*([amj])\b", elem_str)
            if match_abrev:
                lettre = match_abrev.group(2)
                unite = {"a": "ans", "m": "mois", "j": "jours"}.get(lettre, valeur_par_defaut)
            else:
                unite = valeur_par_defaut

        match_nombre = re.search(r"\d+", elem_str)
        nombre = int(match_nombre.group(0)) if match_nombre else None

        if elem_str.isdigit():
            unite = valeur_par_defaut
            nombre = int(elem_str)

        return unite, nombre

    def traiter_element(elem):
        if elem is None or pd.isna(elem):
            texte = valeur_par_defaut
            nombre = None
        else:
            elem_str = str(elem).strip()
            texte, nombre = detecter_unite_et_nombre(elem_str)

        logger.info(f"[Extraction] Valeur brute: {elem!r} | Texte: {texte} | Nombre: {nombre}")

        if mode == "texte":
            return texte
        if mode == "nombre":
            return nombre
        return {"texte": texte, "nombre": nombre}

    if isinstance(cellule, list):
        return [traiter_element(e) for e in cellule]
    return traiter_element(cellule)


# ----------------------------------------------------------
# Pipeline principal
# ----------------------------------------------------------
def clean_all_values_names(
    df: pd.DataFrame,
    mapping_file: Union[str, Path] = DEFAULT_MAPPING_FILE,
    apply_mapping: bool = True,
    case_option: str = "none",
    remove_accents: bool = False,
    convert_type: bool = True
) -> pd.DataFrame:
    """
    Pipeline :
    1) mapping Excel (option)
    2) nettoyage global (espaces, NA-like, casse, accents, conversions)
    """
    out = df.copy()
    if apply_mapping:
        out = replace_specific_values(out, mapping_file=mapping_file, log=True)
    out = clean_all_values(
        out,
        cols=None,
        case_option=case_option,
        remove_accents=remove_accents,
        convert_type=convert_type,
        verbose=False
    )
    return out

