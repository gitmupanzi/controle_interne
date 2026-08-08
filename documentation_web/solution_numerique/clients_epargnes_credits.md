# Clients, épargnes et crédits

## Clients

Le cockpit Clients mesure :

- clients chargés depuis `Customers` ;
- clients actifs sur la période ;
- créations de clients ;
- croisements avec G2 et Clients Perfect lorsqu'ils sont disponibles.

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
