# Clients, épargnes et crédits

## Clients

Le cockpit Clients mesure :

- clients chargés depuis `Customers` ;
- clients actifs sur la période ;
- créations de clients ;
- nouveaux clients et comptes créés sur la période, avec activité transactionnelle, nombre de transactions, solde du compte ouvert et montant DAT par devise ;
- croisements avec G2 et Clients Perfect lorsqu'ils sont disponibles.

La table `Nouveaux clients et comptes actifs par devise` répond à une question de pilotage : un client ou un compte récemment créé est-il réellement utilisé ? Elle croise `Customers` pour la date de création client, `Transactions` pour l'activité consolidée et `Savings Account` pour les positions compte ouvert et DAT. Les montants restent toujours séparés entre CDF et USD.

## Épargnes

Le cockpit Épargnes repose sur `Savings Account`.

Analyses principales :

- comptes ouverts ;
- comptes bloqués / DAT ;
- encours par devise ;
- statuts ;
- DAT échus ou bientôt à terme ;
- intérêts calculés ou à estimer.

Les colonnes visibles doivent être en français, sans accents ni espaces lorsque cela sert aux traitements techniques.

## Crédits

Le cockpit Crédits repose sur `Loans Account` et, pour les remboursements observés, sur `Transactions`.

Analyses principales :

- nouveaux crédits ;
- encours ;
- remboursements ;
- échéances ;
- crédits actifs, terminés, en retard ou à surveiller ;
- rapprochement crédit / épargne lorsque le `savings_account_id` est disponible.

## Séparation des lectures

Épargne et crédit ne doivent pas être mélangés dans l'extrait client. Le détail transactionnel montre le compte ouvert ; les DAT et remboursements ont leurs blocs dédiés.
