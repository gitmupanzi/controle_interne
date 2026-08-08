# Tableau de bord Streamlit Perfect Vision

## Rôle

Le tableau de bord Streamlit permet de consulter les synthèses par cycle, les contrôles, le portefeuille, les risques, la qualité, la surveillance, les exports et la méthode.

## Fichiers applicatifs

| Fichier | Rôle |
|---|---|
| `controle_interne.py` | Point d'entrée Streamlit |
| `credit_app/cycles.py` | Définition des cycles |
| `credit_app/domain.py` | Domaine métier et colonnes de référence |
| `credit_app/tabs/*.py` | Onglets fonctionnels |
| `credit_app/components/preparation.py` | Préparation des données |
| `credit_app/display_columns.py` | Libellés affichés à l'utilisateur |

## Règles d'interface

- Les noms visibles doivent être compréhensibles par le métier.
- Les filtres doivent privilégier les sélections multiples lorsque c'est utile.
- Les dates sont affichées en format français.
- Les sous-onglets doivent rester sobres, professionnels, avec navigation clavier visible.

## Cache et performance

Le tableau de bord peut charger plusieurs blocs au démarrage. Les calculs coûteux doivent être isolés et mis en cache lorsque le résultat dépend clairement des mêmes entrées.
