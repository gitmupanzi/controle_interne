# Cas pratiques et exercices

Cette page propose des exercices simples pour transformer la documentation en formation active.

## Exercice 1 — Identifier la bonne source

Pour chaque besoin, indiquer la source principale.

| Besoin | Source attendue |
|---|---|
| Lire les mouvements d'un client numérique | |
| Connaître les DAT en cours | |
| Connaître les crédits numériques accordés | |
| Enrichir le nom client depuis M-Pesa | |
| Rapprocher Solution Numérique et Perfect Vision | |

Réponses attendues :

- mouvements : `Transactions` ;
- DAT : `Savings Account` ;
- crédits : `Loans Account` ;
- nom client M-Pesa : `G2 M-Pesa` ;
- rapprochement : numéro de téléphone normalisé.

## Exercice 2 — Lire sans mélanger les devises

Un rapport affiche :

| Devise | Encours DAT |
|---|---:|
| CDF | 10 000 000 |
| USD | 2 000 |

Question : peut-on dire que l'encours DAT total est `10 002 000` 

Réponse : non. CDF et USD ne doivent pas être additionnés sans conversion officielle, datée et documentée.

## Exercice 3 — Comprendre G2

Un utilisateur demande : “Pourquoi le montant G2 est différent du montant calculé dans la Solution Numérique ”

Réponse attendue :

G2 est une source de contrôle et d'identité. Il permet de vérifier les écritures et d'enrichir le nom client, mais la Solution Numérique calcule les montants depuis les fichiers numériques principaux.

## Exercice 4 — Utiliser l'onglet Clients

Étapes :

1. Ouvrir `Solution Numérique > Clients`.
2. Choisir une période raisonnable.
3. Cliquer sur `Actualiser les clients`.
4. Lire `Vue d'ensemble`.
5. Ouvrir `Client 360 et segmentation`.
6. Préparer l'Excel uniquement si la liste doit être partagée ou retraitée.

Question : pourquoi l'analyse ne se lance-t-elle pas automatiquement dès qu'on change la date 

Réponse : pour éviter les recalculs lourds et les risques de lenteur ou de crash.

