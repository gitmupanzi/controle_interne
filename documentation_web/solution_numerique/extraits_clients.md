# Extraits clients

## Objectif métier

Produire un relevé bancaire professionnel centré sur le compte ouvert du client, tout en présentant les éléments utiles sur DAT, crédits en cours, remboursements et prochains remboursements.

## Règle du détail transactionnel

Le détail des transactions doit reprendre les opérations qui touchent réellement le compte ouvert :

- dépôt ;
- retrait ;
- retrait de DAT avant échéance ;
- retour du montant principal du DAT ;
- rentrée des intérêts sur DAT ;
- remboursement d'un crédit depuis le compte ouvert.

## Synthèse financière par devise

La synthèse attendue par devise contient :

| Colonne | Lecture |
|---|---|
| Devise | CDF ou USD |
| Ouverture | Solde d'ouverture du compte ouvert |
| Entrées | Flux entrants sur le compte ouvert |
| Sorties | Flux sortants sur le compte ouvert |
| Clôture | Solde de clôture reconstitué ou observé |
| Compte ouvert | Dernière position du compte ouvert |
| Compte bloqué | Dernière position DAT / compte bloqué |

## Positions à date

Le format complet ajoute des blocs de situation séparés du détail transactionnel :

| Bloc | Source | Lecture |
|---|---|---|
| DAT en cours - situation au ... | `Savings Account` | DAT positifs du client, échéance, jours restants, capital bloqué et capital + intérêt estimé |
| Crédit en cours - situation au ... | `Loans Account` | Crédits encore en cours, montant accordé, montant payé, encours, montant à rembourser, échéance et situation |

Ces positions ne sont pas des lignes du compte ouvert. Elles permettent au lecteur de comprendre l'exposition du client sans modifier les colonnes `Entrées`, `Sorties` et `Solde` du relevé bancaire.

## Exports

Les exports existent en formats complet et minimal. Le nom du fichier peut distinguer les variantes, mais le texte interne doit rester standard.

Les documents Word utilisent des marges gauche et droite de 2 cm.
