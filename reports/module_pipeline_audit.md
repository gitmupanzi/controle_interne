# Audit des modules de nettoyage et de compilation

Le catalogue détaillé des signatures, lignes, appels et indicateurs de risque est enregistré dans `reports/module_function_catalog.json`.

## Responsabilités actuelles

- `colonne_filtrage.py` : filtres génériques, fenêtres de dates et nullité.
- `colonne_fusion.py` : fusion de colonnes et jointures, y compris correspondances approchées.
- `colonne_nettoyage.py` : normalisation des en-têtes, alias, renommage Excel et contrôle des colonnes.
- `colonne_suppression.py` : diagnostic et suppression explicite de colonnes.
- `valeurs_completude.py` : complétude et valeurs manquantes.
- `valeurs_nettoyage.py` : texte, téléphone, e-mail, nombres, dates et remplacements Excel.
- `valeurs_suppression.py` : détection et traitement configurable des doublons.
- `fichiers_compilation.py` : lecture multi-fichiers, harmonisation, provenance, collisions et export.
- `fichiers_nommage.py` : génération et interprétation contrôlée des noms de fichiers.

## Utilisation dans le pipeline

L'application principale appelle `charger_fichiers_excel` pour la compilation. Celui-ci réutilise les fonctions de `colonne_nettoyage` et de fusion, conserve un journal de colonnes et expose les collisions dans `DataFrame.attrs`. Le domaine appelle les fonctions de normalisation des colonnes et de valeurs lors de la préparation standard.

## Risques observés

- Plusieurs fonctions dépassent 100 lignes et mélangent validation, transformation, journalisation et export.
- Des captures générales d'exception subsistent dans les utilitaires historiques ; le chemin principal de compilation est désormais strict et remonte les fichiers rejetés.
- Les fonctions d'export présentes dans les modules historiques conservent des conventions issues d'anciens projets épidémiologiques.
- Un couplage différé existe entre `colonne_nettoyage` et `colonne_fusion`.
- Les opérations de correspondance approchée et certaines boucles ligne par ligne peuvent devenir coûteuses sur les gros fichiers.
- Les suppressions et fusions avancées ne sont pas toutes appelées par l'application Streamlit actuelle ; elles restent disponibles comme bibliothèque historique.

## Mesures appliquées

- Rejet explicite d'une feuille absente ou d'un fichier incompatible au lieu de l'ignorer.
- Traçabilité `source_fichier`, `source_feuille` et `numero_ligne_source` lors d'une compilation.
- Validation de compatibilité du cycle, de la feuille et du recouvrement de schéma avant compilation générique.
- Validation des règles Excel vides ou contradictoires.
- Cache invalidé par date de modification pour `Replace_values.xlsx`.
