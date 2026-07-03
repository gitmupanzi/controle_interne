# -*- coding: utf-8 -*-

# dataminsante/compilation/fichiers_nommage.py

import logging
import re
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

def generer_nom_fichier(
    province_code: str,
    zone: Optional[str] = None,
    type_fichier: str = "LL",
    maladie: str = "Rougeole",
    fusion: bool = False,
    extension: str = "xlsx",
    date: Optional[str] = None  # format "2025-07-27"
) -> str:
    """
    Génère un nom de fichier normalisé pour les fichiers épidémiologiques.

    Exemple : BAS_BASANKUSU_LL_Rougeole.xlsx ou BAS_LL_Rougeole_2025-07-27.xlsx

    Args:
        province_code (str): Code de la province (ex: "BAS").
        zone (str, optional): Nom de la zone de santé.
        type_fichier (str): Type de fichier (LL, RS, etc.).
        maladie (str): Nom de la maladie (ex: "Rougeole").
        fusion (bool): True si fichier fusionné.
        extension (str): Type de fichier (xlsx, csv...).
        date (str, optional): Date à inclure (format ISO).

    Returns:
        str: Nom de fichier standardisé.
    """
    if fusion:
        if not province_code:
            raise ValueError("Le code province est requis pour un fichier fusionné.")
        nom = f"{province_code.upper()}_{type_fichier.upper()}_{maladie.capitalize()}"
    else:
        if not (province_code and zone):
            raise ValueError("Province et zone sont obligatoires pour un fichier non fusionné.")
        nom = f"{province_code.upper()}_{zone.upper()}_{type_fichier.upper()}_{maladie.capitalize()}"

    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("La date doit être au format 'YYYY-MM-DD'.")
        nom += f"_{date}"

    nom_complet = f"{nom}.{extension.lower()}"
    logger.debug(f"Nom de fichier généré : {nom_complet}")
    return nom_complet


def generer_nom_feuille(type_fichier="LL", maladie="Rougeole") -> str:
    """
    Génère un nom de feuille Excel standardisé (ex: LL_Rougeole).
    """
    feuille = f"{type_fichier.upper()}_{maladie.capitalize()}"
    logger.debug(f"Nom de feuille généré : {feuille}")
    return feuille


def est_nom_fichier_valide(nom: str, types_fichiers: Optional[List[str]] = None) -> bool:
    """
    Vérifie si un nom de fichier respecte la convention standard : 
    Exemple : BAS_BASANKUSU_LL_Rougeole.xlsx ou BAS_LL_Rougeole_2025-07-27.csv
    """
    if types_fichiers is None:
        types_fichiers = ["LL", "RS"]
    types_pattern = "|".join(types_fichiers)
    pattern = rf"^[A-Z]{{3}}(_[A-Z0-9_-]+)?_({types_pattern})_[A-Z][a-zA-Zéèêôà\s-]+(_\d{{4}}-\d{{2}}(-\d{{2}})?|_S[Ee]?\d{{1,2}})?\.(xlsx|csv)$"
    try:
        return bool(re.match(pattern, nom))
    except re.error as e:
        logger.error(f"Erreur dans le pattern de validation : {e}")
        return False


def normaliser_zone_texte(zone: str) -> str:
    """
    Normalise une chaîne représentant une zone (espace, underscore, tiret).
    Ex: 'zone-de_sante ouest' -> 'Zone_De_Sante_Ouest'
    """
    segments = re.split(r'[_\-\s]', zone)
    return "_".join(s.capitalize() for s in segments if s)


def extraire_infos_nom_fichier(nom_fichier: str) -> Optional[Dict[str, Optional[str]]]:
    """
    Extrait les composantes d'un nom de fichier épidémiologique.
    Normalise :
    - province en minuscules
    - zone et maladie en Capitalized (gestion underscore/tiret)
    - garde le type et la période tels quels

    Retourne un dict avec au moins : province, zone (peut être None), type, maladie, periode (peut être None).

    Gère les structures avec ou sans zone, avec ou sans période,
    ainsi que le cas spécial double underscore pour zone vide.
    """
    nom_sans_ext = nom_fichier.rsplit('.', 1)[0]

    patterns = [
        # Double underscore zone vide (ex: md_LL__Rougeole_2024-05.xlsx)
        r'^(?P<province>[a-zA-Z]{1,3})_(?P<type>[A-Z]+)__(?P<maladie>[A-Z][a-zA-Zéèêôà\s\-_]+)(_(?P<periode>\d{4}-\d{2}(-\d{2})?|S[Ee]?\d{1,2}))?$',

        # province_zone_type_maladie_periode
        r'^(?P<province>[a-zA-Z]{1,3})_(?P<zone>[A-Za-z0-9_\-\s]+)_(?P<type>[A-Z]+)_(?P<maladie>[A-Z][a-zA-Zéèêôà\s\-_]+)_(?P<periode>\d{4}-\d{2}(-\d{2})?|S[Ee]?\d{1,2})$',

        # province_zone_type_maladie
        r'^(?P<province>[a-zA-Z]{1,3})_(?P<zone>[A-Za-z0-9_\-\s]+)_(?P<type>[A-Z]+)_(?P<maladie>[A-Z][a-zA-Zéèêôà\s\-_]+)$',

        # province_type_zone_maladie_periode
        r'^(?P<province>[a-zA-Z]{1,3})_(?P<type>[A-Z]+)_(?P<zone>[A-Za-z0-9_\-\s]+)_(?P<maladie>[A-Z][a-zA-Zéèêôà\s\-_]+)_(?P<periode>\d{4}-\d{2}(-\d{2})?|S[Ee]?\d{1,2})$',

        # province_type_zone_maladie
        r'^(?P<province>[a-zA-Z]{1,3})_(?P<type>[A-Z]+)_(?P<zone>[A-Za-z0-9_\-\s]+)_(?P<maladie>[A-Z][a-zA-Zéèêôà\s\-_]+)$',

        # province_type_maladie_periode (sans zone)
        r'^(?P<province>[a-zA-Z]{1,3})_(?P<type>[A-Z]+)_(?P<maladie>[A-Z][a-zA-Zéèêôà\s\-_]+)_(?P<periode>\d{4}-\d{2}(-\d{2})?|S[Ee]?\d{1,2})$',

        # province_type_maladie (sans zone)
        r'^(?P<province>[a-zA-Z]{1,3})_(?P<type>[A-Z]+)_(?P<maladie>[A-Z][a-zA-Zéèêôà\s\-_]+)$',
    ]

    for pattern in patterns:
        try:
            match = re.match(pattern, nom_sans_ext, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Erreur regex sur le pattern : {e}")
            continue

        if match:
            groupes = match.groupdict()

            # Normalisation
            groupes['province'] = groupes['province'].lower()

            groupes['zone'] = (
                normaliser_zone_texte(groupes['zone']) if groupes.get('zone') else None
            )

            groupes['maladie'] = groupes['maladie'].capitalize()

            if groupes.get('periode'):
                # Nettoyage SE/Sxx -> SE
                if re.match(r'^s[eE]?\d{1,2}$', groupes['periode'], re.IGNORECASE):
                    val = groupes['periode'].upper()
                    if val.startswith("S") and not val.startswith("SE"):
                        val = "SE" + val[1:]
                    groupes['periode'] = val

                # Validation ISO date
                if re.match(r'^\d{4}(-\d{2}(-\d{2})?)?$', groupes['periode']):
                    try:
                        parts = groupes['periode'].split('-')
                        y = int(parts[0])
                        m = int(parts[1]) if len(parts) > 1 else 1
                        d = int(parts[2]) if len(parts) > 2 else 1
                        datetime(y, m, d)
                    except Exception:
                        logger.warning(f"Date invalide détectée dans période: {groupes['periode']} pour fichier {nom_fichier}")

            return groupes

    logger.warning(f"Nom fichier non conforme ou non reconnu : {nom_fichier}")
    return None
