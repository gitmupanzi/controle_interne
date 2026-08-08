# Sources et schéma SQL Perfect Vision

## Fichiers de référence

| Fichier | Rôle |
|---|---|
| `data/modelisation/BB_VISION_PRO.sql` | Script SQL Server du schéma `BB_VISION_PRO` |
| `data/modelisation/requetes.sql` | Catalogue des requêtes de contrôle et de reporting |
| `skills/perfect-vision/references/sources.md` | Règles de lecture métier et sources prioritaires |

## Objets SQL observés

Le script `BB_VISION_PRO.sql` contient un schéma large : plus de 800 tables déclarées et plusieurs vues de synthèse.

Objets métiers fréquemment rencontrés dans les analyses :

| Objet | Lecture métier |
|---|---|
| `ADHERENTS` | Référentiel clients / adhérents |
| `COMPTES` et `COMPTES_ADHERENT` | Comptes et rattachement aux clients |
| `OPERATIONS`, `OPERATIONS_API` | Opérations back-office et API |
| `HDPM`, `HDPM_API` | Écritures comptables |
| `PRETS`, `DOSSIERS_CREDIT`, `CYCLES_PRET` | Crédit, dossiers et cycles |
| `TABAMOR` | Tableau d'amortissement |
| `PRODUITS_CRD`, `PRODUITS_EPG` | Produits crédit et épargne |
| `DEVISES` | Devise de reporting |
| `extra_clients_view`, `extra_credits_view`, `extra_epargnes_view` | Vues métier utilisées pour simplifier les restitutions |

## Précaution

Le schéma Perfect Vision est volumineux. La documentation privilégie les tables et vues réellement utilisées par les requêtes, les KPI et les tableaux de bord. Un dictionnaire exhaustif des 800+ tables serait moins utile qu'une documentation orientée contrôles et décisions.
