# Solution Numérique — Clients

Le cockpit `Clients` mesure la base client, l'activation et les opportunités de suivi commercial à partir des sources Solution Numérique.

## Sources utilisées

| Source | Rôle |
|---|---|
| `Customers` | Référentiel des clients connus et date de création client. |
| `Transactions` | Activité réelle observée sur la période. |
| `Savings Account` | Comptes ouverts, DAT et positions d'épargne rattachées au client. |
| `Loans Account` | Présence crédit et encours crédit. |
| `G2` | Source facultative pour enrichir le nom ou contrôler certaines écritures. |
| `Clients Perfect` | Source facultative pour croiser Perfect Vision avec la Solution Numérique. |

## Analyses principales

Le cockpit Clients mesure :

- les clients chargés depuis `Customers` ;
- les clients connus à la date de fin ;
- les clients actifs sur la période ;
- les créations de clients ;
- les nouveaux clients et comptes créés sur la période ;
- l'activité transactionnelle des nouveaux clients ;
- les soldes de compte ouvert et DAT par devise ;
- les tranches d'encours par famille (`compte_ouvert`, `dat`, `credit`) et par devise ;
- les croisements avec G2 et Clients Perfect lorsqu'ils sont disponibles.

Le cockpit doit être lu d'abord à l'écran. Après le paramétrage de la période, de la fréquence et des seuils, l'utilisateur clique sur `Actualiser les clients`. Les KPI, tableaux et listes se mettent alors à jour en ligne.

L'Excel n'est pas préparé automatiquement : le bloc `Export du cockpit Clients` sert de support secondaire pour retraiter ou partager les listes uniquement lorsque l'utilisateur clique sur `Préparer l'Excel Clients`.

## Volets de l'interface

| Volet | Contenu principal |
|---|---|
| `Vue d'ensemble` | KPI clients et qualité des données. |
| `Activité et activation` | Activité observée, inactivité, acquisition et activation. |
| `Nouveaux clients et comptes` | Nouveaux clients, comptes ouverts et DAT créés sur la période. |
| `Client 360 et segmentation` | Produits détenus, présence épargne/DAT/crédit, tranches d'encours et segmentation. |
| `Opportunités` | DAT sans crédit actif et listes commerciales prudentes. |

## Nouveaux clients et comptes actifs

La table `Nouveaux clients et comptes actifs par devise` répond à une question de pilotage : un client ou un compte récemment créé est-il réellement utilisé ?

Elle croise :

- `Customers` pour la date de création client ;
- `Transactions` pour l'activité consolidée ;
- `Savings Account` pour les positions compte ouvert et DAT.

Les montants restent toujours séparés entre CDF et USD.

## Feuilles clés du cockpit Excel Clients

Dans le fichier Excel généré, les onglets prioritaires sont colorés en rouge. Cette couleur signifie `à lire en priorité`; elle ne signifie pas automatiquement qu'il y a une anomalie.

Pour rendre le cockpit opérationnel, les feuilles clés écartent les colonnes purement techniques : fichiers sources, clés internes, colonnes brutes, ordres d'import, traces de calcul et identifiants intermédiaires. Elles conservent les informations utiles à l'action : client, téléphone, devise, statut, dates, activité, segment, score, solde, encours et commentaire.

| Priorité | Feuille | Lecture recommandée |
|---:|---|---|
| 1 | `Clients_KPI` | Porte d'entrée du cockpit : clients chargés, clients connus, clients actifs, nouveaux clients et indicateurs de synthèse. |
| 2 | `Clients_Acquisition` | Suivi des créations et de l'activation des clients sur la période. |
| 3 | `Nouveaux_Clients_Actifs` | Vérifie si les nouveaux clients réalisent effectivement des opérations après leur création. |
| 4 | `Clients_Actifs` | Liste opérationnelle des clients qui utilisent réellement la Solution Numérique sur la période. |
| 5 | `Clients_Sans_Mouvement` | Clients connus ou créés mais sans mouvement observé : base de relance ou de diagnostic. |
| 6 | `Clients_Multi_Produits` | Clients utilisant plusieurs produits : compte ouvert, DAT, crédit ou activité transactionnelle. |
| 7 | `DAT_Sans_Credit` | Clients avec DAT mais sans crédit actif : opportunités commerciales prudentes, jamais une décision automatique d'octroi. |

Lecture Direction : commencer par `Clients_KPI`, puis lire `Clients_Acquisition`, `Nouveaux_Clients_Actifs` et `Clients_Sans_Mouvement`. Ces feuilles répondent à la question simple : la base client grandit-elle et devient-elle active ?

## À retenir

- Un client actif est un client avec une activité observée dans `Transactions`, pas seulement un client présent dans `Customers`.
- Le numéro de téléphone normalisé reste la clé terrain principale de recherche.
- Les opportunités commerciales restent prudentes : elles aident à prioriser une revue humaine, pas à automatiser une décision.
