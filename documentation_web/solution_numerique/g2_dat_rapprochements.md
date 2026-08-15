# G2, DAT et rapprochements

## Rôle de G2

G2 est un rapport de contrôle M-Pesa. Il sert principalement à :

- enrichir le nom du client ;
- vérifier une écriture ;
- rapprocher les délais et statuts ;
- détecter des anomalies entre le portail opérationnel et M-Pesa.

G2 ne pilote pas les montants, les soldes, les DAT ou les remboursements.

## Mode d'analyse dans l'onglet

Quand les transactions de la Solution Numérique sont chargées, l'onglet `Solution Numérique / M-Pesa` affiche un menu déroulant `Mode d'analyse` dans le bloc `Période d'analyse`.

| Mode | Quand l'utiliser | Lecture |
|---|---|---|
| `Solution Numérique + rapport G2` | Transactions Solution Numérique chargées et rapport G2 disponible | La période, les montants, les DAT et les remboursements restent pilotés par la Solution Numérique. G2 enrichit le nom client et sert de preuve de contrôle lorsque la période G2 couvre l'opération. |
| `Solution Numérique seule` | Aucun rapport G2 disponible, ou contrôle G2 volontairement ignoré | Le rapport est construit uniquement depuis les transactions Solution Numérique. Les contrôles croisés G2/Solution Numérique sont non applicables. |
| `Rapport G2 seul` | Aucun fichier Transactions Solution Numérique n'est disponible | Le rapport lit le relevé G2 comme source de contrôle, sans recalculer les montants de la Solution Numérique. |

Le rapport Word reprend le mode choisi dans les critères et dans la synthèse de contrôle afin que l'export corresponde exactement au visuel.

En mode `Solution Num?rique + rapport G2`, le commentaire de contr?le du Word doit rester chiffr? : op?rations rapproch?es sur le total, pourcentage de rapprochement, rapprochements exacts, rapprochements avec ?cart, op?rations non rapproch?es et anomalies. Cela permet de retrouver rapidement une lecture du type `100/100 rapproch?es, 0 anomalie` lorsque tout est coh?rent.

## Sources G2

| Rapport | Lecture |
|---|---|
| `ORG_1441` | Entrées |
| `ORG_15558` | Sorties |

Les fichiers G2 peuvent avoir un décalage temporel avec la transaction source ; les règles de rapprochement doivent tenir compte d'un écart possible.

## DAT

Les DAT sont analysés depuis `Savings Account` :

- souscription ;
- échéance ;
- jours restants ;
- capital bloqué ;
- intérêt estimé ;
- situation.

Pour Bisou Bisou, le taux annuel par défaut des DAT est documenté à 11 %, sauf paramètre différent fourni par l'utilisateur.
