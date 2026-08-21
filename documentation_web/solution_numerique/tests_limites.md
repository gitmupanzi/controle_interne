# Tests et limites Solution Numérique

## Tests automatisés

| Fichier | Rôle |
|---|---|
| `tests/test_mpesa_analysis.py` | Règles d'analyse, extraits, statistiques et calculs |
| `tests/test_mpesa_clients.py` | Analyses clients |
| `tests/test_solution_mpesa_uploads.py` | Téléversements et contrats de fichiers |
| `tests/test_streamlit_date_format.py` | Format français des dates |
| `tests/test_ui_charts.py` | Paramétrage visuel des graphiques |
| `tests/test_text_encoding.py` | Encodage texte |

## Jeux de test métier

Les dossiers de test locaux servent à valider les cas réels avant stabilisation :

- `Documents\Test Controle interne\Test Solution M_PESA`
- `Documents\Test Controle interne\bdd Solution M_PESA`
- `Downloads\Test Benjamin`

Les données individuelles ne doivent pas être publiées dans la documentation web.

## Limites

- Un snapshot unique ne permet pas toujours de reconstituer tout l'historique.
- G2 peut être absent ou hors période.
- Le plan d'amortissement détaillé peut manquer pour certaines projections crédit.
- Les colonnes disponibles varient selon le fichier exporté.
- Les montants CDF et USD restent séparés.

## Limites constatées par fichier

Ces limites ne remettent pas en cause l'utilité des fichiers. Elles indiquent simplement ce que chaque source permet de démontrer directement, et ce qui doit être reconstitué avec prudence.

| Fichier | Ce qu'il couvre bien | Limites constatées | Conséquence pour l'analyse |
|---|---|---|---|
| `Transactions` | Journal des écritures et des flux de période : dépôts, retraits, transferts DAT, retours DAT, remboursements depuis compte ouvert. Les colonnes clés sont `reference_id` (référence interne), `ref_no` (référence opération), `account_type` (type de compte), `dr` (débit / sortie), `cr` (crédit / entrée), `bal_before` (solde avant), `bal_after` (solde après) et `created_at` (date de création). | Une opération métier peut générer plusieurs lignes comptables. Le prêt décaissé ne touche pas toujours le compte ouvert du client, car le versement peut passer du compte prêt vers le compte M-Pesa. Certaines écritures internes ne doivent donc pas apparaître dans le relevé bancaire du compte ouvert. | Construire des événements canoniques avant d'analyser. Ne pas assimiler une ligne comptable à une opération client. Pour l'extrait client, ne retenir dans le détail transactionnel que les opérations qui touchent réellement le compte ouvert : dépôt, retrait, retrait DAT avant échéance, retour du capital DAT, intérêts DAT et remboursement de crédit depuis compte ouvert. |
| `Savings Account` | Source principale des comptes d'épargne ouverts et bloqués / DAT. Elle porte les soldes, produits, statuts, dates d'activation, échéances DAT, intérêts constatés et frais. Les colonnes clés sont `savings_id` (numéro de compte épargne), `customer_id` (identifiant client), `msisdn1` (numéro client), `product_name` (produit), `currency_code` (devise), `balance` (solde), `maturity_date` (date d'échéance), `interest_earned` (intérêt constaté) et `voda_interest` (intérêt Vodacom). | C'est principalement un instantané à date. Un seul export ne permet pas de reconstituer l'évolution historique complète des encours. Les fichiers résumés `Customers with Current Savings Account` et `Customers with Fixed Savings Account` ne couvrent que les comptes à solde positif et ne remplacent pas la source complète. | Utiliser `Savings Account` pour les encours à date, les DAT échus/proches de l'échéance, les comptes ouverts et les opportunités prudentes. Pour les évolutions historiques de solde, demander plusieurs instantanés ou s'appuyer sur `Transactions` lorsque le mouvement est identifiable. |
| `Loans Account` | Source principale des crédits à date : montant accordé, encours, montant payé, frais, intérêts, pénalités, échéance et statut. Les colonnes clés sont `loan_id` (numéro de prêt), `customer_id` (identifiant client), `msisdn1` (numéro client), `currency_code` (devise), `loan_amount` (montant accordé), `loan_balance` (solde crédit), `amount_paid` (montant payé), `outstanding_interest` (intérêts restants), `outstanding_setup_fees` (frais restants), `outstanding_penalty_fees` (pénalités restantes), `interest_earned` (intérêt gagné), `due_date` (date d'échéance) et `status_name` (statut). | Le fichier ne donne pas toujours le plan d'amortissement détaillé. Il permet de lire une position à date, mais pas toujours la chronologie précise des remboursements. La part Vodacom du crédit n'est pas toujours isolée comme une colonne native : les intérêts globaux sont visibles, mais la ventilation Bisou Bisou / Vodacom doit être calculée par règle métier ou confirmée par les écritures. | Utiliser `Loans Account` pour l'encours crédit, PAR simplifié, crédits en retard, crédits actifs, crédits sans épargne et indicateurs de risque. Pour retracer les remboursements ou la part Vodacom effectivement comptabilisée, croiser avec `Transactions` et signaler les estimations comme telles. |
| `Customers` | Base des comptes clients connus par la Solution Numérique. Le numéro client est porté par `msisdn1` (numéro client) et la date de création par `created_at` (date de création). | Le fichier peut contenir peu de colonnes métier. Il ne suffit pas à mesurer l'activité réelle du client, ni à connaître ses produits, ses soldes ou ses crédits. | Utiliser `Customers` pour la base connue et les créations de comptes clients. L'activité doit venir de `Transactions`; les produits viennent de `Savings Account` et `Loans Account`. |
| `Rapports G2` | Source de contrôle et d'enrichissement : preuve M-Pesa, statut, nom/partie opposée et référence. Les colonnes clés sont `Receipt No.` (numéro reçu G2), `Completion Time` (date de finalisation), `Transaction Status` (statut), `Paid In` (entrée), `Withdrawn` (sortie), `Opposite Party` (partie opposée) et `Linked Transaction ID` (transaction liée). | G2 peut être absent, incomplet ou s'arrêter avant la période analysée dans la Solution Numérique. Les heures peuvent différer de celles de la Solution Numérique. G2 ne doit pas piloter les montants, les soldes, les DAT, les crédits ou les remboursements lorsque la source Solution Numérique est disponible. | Utiliser G2 pour enrichir l'identité du client et contrôler les écritures. Si G2 ne couvre pas la période, conserver les opérations Solution Numérique et les classer comme à vérifier avec le motif de couverture G2 indisponible. |
| `Clients_Perfect` | Source facultative de rapprochement avec Perfect Vision par numéro de téléphone. | Ce fichier n'est pas nécessaire au cœur financier de la Solution Numérique. Les formats et les noms de colonnes peuvent varier selon l'export. | Utiliser comme enrichissement analytique ou vue 360 client. Ne jamais modifier les montants de la Solution Numérique avec cette source. |

## Points de vigilance métier

- La Solution Numérique est la source opérationnelle principale des montants, soldes, DAT, crédits et remboursements.
- G2 enrichit l'identité et fournit une preuve de rapprochement, mais ne remplace pas les montants de la Solution Numérique.
- Les fichiers `Savings Account` et `Loans Account` sont des positions à date. Une comparaison historique fiable des encours nécessite plusieurs instantanés ou une règle confirmée de lecture des transactions.
- Pour les crédits, `Loans Account` permet de suivre les intérêts globaux, mais pas toujours de retracer directement la part Vodacom. La ventilation doit être confirmée par les écritures ou calculée avec une règle métier documentée.
- Pour les DAT, `Savings Account.voda_interest` (intérêt Vodacom) est la source la plus directe lorsque la colonne est disponible.
- Un compte client correspond au numéro de téléphone. Ce compte peut avoir plusieurs produits : épargne ouverte, DAT et crédit.
- Les devises doivent toujours rester séparées. Les montants CDF et USD ne doivent jamais être additionnés dans un même indicateur financier.

## Performance Streamlit Cloud

La Solution Numérique peut charger des fichiers Excel volumineux. Pour limiter les risques de crash :

- l'analyse en ligne est prioritaire : les KPI, alertes, tableaux et graphiques doivent être consultables dans Streamlit avant de produire un fichier ;
- les sources communes sont préparées une fois après téléversement ;
- les sous-onglets principaux utilisent une navigation dynamique : seul le sous-onglet ouvert rend son contenu ;
- les paramètres locaux des sous-onglets lourds sont regroupés dans des formulaires et ne déclenchent les calculs qu'après clic sur un bouton `Actualiser` ;
- la période proposée par défaut dans les onglets analytiques lourds est limitée à trois mois maximum, même si l'historique chargé est plus large ;
- après un nouveau téléversement, les validations précédentes ne sont pas réutilisées automatiquement : l'utilisateur doit relancer l'analyse voulue avec `Actualiser` ;
- les rapports lourds sont conservés dans des caches bornés ;
- le cache de lecture Excel doit couvrir le paquet réel de fichiers chargés, y compris les historiques `Transactions` et les deux rapports G2 `1441` / `15558`, afin d'éviter une relecture réseau à chaque rerun ;
- les exports Word/PDF/Excel sont générés à la demande et gardent peu d'entrées en cache ;
- les exports Excel volumineux suivent le parcours `Préparer` puis `Télécharger`, afin d'éviter la construction automatique des classeurs au chargement de la page ;
- les analyses récurrentes doivent réutiliser le journal d'événements consolidé plutôt que recalculer les transactions dans chaque onglet.

Cette règle ne change pas les calculs métier : elle limite seulement les calculs cachés et la mémoire conservée.
