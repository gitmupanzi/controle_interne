# credit_app/colonne_valeur/__init__.py
"""
Initialisation du package credit_app/colonne_valeur.
"""

import logging

logger = logging.getLogger(__name__)


def _importer_optionnel(instruction_import: str, dependance: str) -> None:
    try:
        exec(instruction_import, globals())
    except ModuleNotFoundError as exc:
        if exc.name == dependance:
            logger.warning(
                "Import optionnel ignoré dans credit_app.colonne_valeur car la dépendance '%s' est absente.",
                dependance,
            )
        else:
            raise


_importer_optionnel("from .colonne_comparaison import *", "rapidfuzz")
from .colonne_filtrage import *
_importer_optionnel("from .colonne_fusion import *", "Levenshtein")
from .colonne_nettoyage import *
from .colonne_suppression import *
from .valeurs_completude import *
from .valeurs_nettoyage import *
from .valeurs_suppression import *
