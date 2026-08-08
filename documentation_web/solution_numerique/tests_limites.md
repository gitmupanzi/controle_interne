# Tests et limites Solution Numérique

## Tests automatisés

| Fichier | Rôle |
|---|---|
| `tests/test_mpesa_analysis.py` | Règles d'analyse, extraits, statistiques et calculs |
| `tests/test_mpesa_clients.py` | Analyses clients |
| `tests/test_solution_mpesa_uploads.py` | Téléversements et contrats de fichiers |
| `tests/test_streamlit_date_format.py` | Format français des dates |
| `tests/test_ui_charts.py` | Paramétrage visuel des graphiques |
| `tests/test_text_encoding.py` | Encodage texte |

## Jeux de test métier

Les dossiers de test locaux servent à valider les cas réels avant stabilisation :

- `Documents\Test Controle interne\Test Solution M_PESA`
- `Documents\Test Controle interne\bdd Solution M_PESA`
- `Downloads\Test Benjamin`

Les données individuelles ne doivent pas être publiées dans la documentation web.

## Limites

- Un snapshot unique ne permet pas toujours de reconstituer tout l'historique.
- G2 peut être absent ou hors période.
- Le plan d'amortissement détaillé peut manquer pour certaines projections crédit.
- Les colonnes disponibles varient selon le fichier exporté.
- Les montants CDF et USD restent séparés.
