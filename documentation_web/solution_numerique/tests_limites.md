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

## Performance Streamlit Cloud

La Solution Numérique peut charger des fichiers Excel volumineux. Pour limiter les risques de crash :

- l'analyse en ligne est prioritaire : les KPI, alertes, tableaux et graphiques doivent être consultables dans Streamlit avant de produire un fichier ;
- les sources communes sont préparées une fois après téléversement ;
- les sous-onglets principaux utilisent une navigation dynamique : seul le sous-onglet ouvert rend son contenu ;
- les paramètres locaux des sous-onglets lourds sont regroupés dans des formulaires et ne déclenchent les calculs qu'après clic sur un bouton `Actualiser` ;
- la période proposée par défaut dans les onglets analytiques lourds est limitée à trois mois maximum, même si l'historique chargé est plus large ;
- après un nouveau téléversement, les validations précédentes ne sont pas réutilisées automatiquement : l'utilisateur doit relancer l'analyse voulue avec `Actualiser` ;
- les rapports lourds sont conservés dans des caches bornés ;
- les exports Word/PDF/Excel sont générés à la demande et gardent peu d'entrées en cache ;
- les exports Excel volumineux suivent le parcours `Préparer` puis `Télécharger`, afin d'éviter la construction automatique des classeurs au chargement de la page ;
- les analyses récurrentes doivent réutiliser le journal d'événements consolidé plutôt que recalculer les transactions dans chaque onglet.

Cette règle ne change pas les calculs métier : elle limite seulement les calculs cachés et la mémoire conservée.
