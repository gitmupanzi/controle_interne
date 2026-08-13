# Solution Numérique — Crédits

Le cockpit `Crédits` pilote le portefeuille crédit, les remboursements observés, les échéances, le risque et les opportunités de suivi.

## Sources utilisées

| Source | Rôle |
|---|---|
| `Loans Account` | Source principale du portefeuille crédit actuel : prêts, encours, statuts, échéances, défauts et frais. |
| `Transactions` | Source des remboursements observés et des décaissements détectables sur la période. |
| `Savings Account` | Mise en regard analytique entre crédit, compte ouvert et DAT. |
| `G2` | Source facultative d'identité ou de contrôle ; elle ne modifie pas les montants crédit. |

## Analyses principales

Le cockpit Crédits mesure :

- les nouveaux crédits ;
- les montants accordés ;
- les encours ;
- les remboursements observés ;
- les échéances ;
- les crédits actifs, terminés, en retard ou à surveiller ;
- les crédits avec pénalités ;
- la concentration par client, produit et tranche d'encours ;
- le rapprochement crédit / épargne lorsque le `savings_account_id` est disponible.

Les montants restent toujours séparés par devise. Un prêt USD et un prêt CDF ne doivent pas être additionnés dans une même valeur monétaire globale.

## Volets de l'interface

| Volet | Contenu principal |
|---|---|
| `Vue d'ensemble` | KPI du portefeuille crédit par devise. |
| `Production et remboursements` | Décaissements et remboursements observés sur la période. |
| `Portefeuille et échéances` | Position Loans Account, échéances, maturité et cohortes à date. |
| `Risques et concentration` | PAR simplifié, prêts à surveiller, top expositions et concentration. |
| `Crédit et épargne` | Rapprochement analytique crédit, compte ouvert et DAT. |
| `Opportunités et qualité` | Opportunités crédit, contrôles qualité, KPI non calculables et limites. |

## Portefeuille et remboursements

Deux lectures doivent rester séparées :

- `Loans Account` donne la position actuelle du prêt : encours, statut, échéance, intérêts, frais et pénalités.
- `Transactions` donne les remboursements réellement observés sur la période.

Un remboursement observé dans `Transactions` ne doit pas être mélangé avec l'encours instantané de `Loans Account` sans rappeler qu'il s'agit de deux grains différents.

## Feuilles clés du cockpit Excel Crédits

Dans le fichier Excel généré, les onglets prioritaires sont colorés en rouge. Cette couleur signifie `à lire en priorité`; elle ne signifie pas automatiquement qu'il y a une anomalie.

Pour rendre le cockpit opérationnel, les feuilles clés écartent les colonnes purement techniques : fichiers sources, clés internes, colonnes brutes, ordres d'import, traces de calcul et identifiants intermédiaires. Elles conservent les informations utiles à l'action : client, téléphone, devise, crédit, statut, montant accordé, encours, remboursement, échéance, retard, risque, tranche, ratio et commentaire.

| Priorité | Feuille | Lecture recommandée |
|---:|---|---|
| 1 | `Credit_Vue_Ensemble` | Synthèse générale du portefeuille crédit par devise. |
| 2 | `Credit_Encours_A_Date` | Liste opérationnelle des encours crédits à la date de situation, avec client, numéro, devise, produit, statut, échéance et risque. |
| 3 | `Credit_Risque_Synthese` | Lecture rapide des risques : retards, PAR simplifié, défauts et signaux de surveillance. |
| 4 | `Credit_Echeances` | Synthèse des prochaines échéances et retards utiles au suivi opérationnel. |
| 5 | `Liste_Prets_Echus` | Liste concrète des prêts échus avec encours à suivre. |
| 6 | `Liste_Prets_PAR30` | Prêts en retard simplifié de 30 jours : utile pour le recouvrement. |
| 7 | `Liste_Prets_Penalites` | Prêts avec pénalités : dossiers sensibles à prioriser. |
| 8 | `Liste_Prets_Defaulted` | Crédits marqués en défaut dans la source, à vérifier par les opérations. |
| 9 | `Credit_Top_Clients` | Concentration des crédits par client. |
| 10 | `Credit_Tranches_Clients` | Répartition par tranche d'encours client afin de lire l'exposition par niveau de montant. |
| 11 | `Credit_Epargne_Clients_360` | Mise en regard crédit + épargne + DAT, sans compensation comptable. |

Lecture Direction : commencer par `Credit_Vue_Ensemble`, `Credit_Encours_A_Date` et `Credit_Risque_Synthese`. Les feuilles `Liste_Prets_Echus`, `Liste_Prets_PAR30`, `Liste_Prets_Penalites` et `Liste_Prets_Defaulted` sont surtout destinées au suivi opérationnel du recouvrement. Les grands détails techniques restent réservés au diagnostic et ne sont pas exportés par défaut dans le cockpit partagé.

## À retenir

- `Loans Account` est un instantané du portefeuille crédit.
- Les remboursements de période viennent des événements consolidés de `Transactions`.
- L'épargne est mise en regard du crédit pour l'analyse, mais elle n'est pas compensée avec l'encours crédit sans preuve contractuelle.
