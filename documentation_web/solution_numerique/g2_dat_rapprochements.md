# G2, DAT et rapprochements

## Rôle de G2

G2 est un rapport de contrôle M-Pesa. Il sert principalement à :

- enrichir le nom du client ;
- vérifier une écriture ;
- rapprocher les délais et statuts ;
- détecter des anomalies entre le portail opérationnel et M-Pesa.

G2 ne pilote pas les montants, les soldes, les DAT ou les remboursements.

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
