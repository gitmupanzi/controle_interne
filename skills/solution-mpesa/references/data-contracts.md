# Contrats de données M-PESA

La source de vérité exécutable reste `credit_app/data_schema.py`. Les règles de calcul et d'export se trouvent dans `credit_app/services/mpesa_analysis.py`.

## Sommaire

- [Sources](#sources)
- [Chargement de plusieurs fichiers](#chargement-de-plusieurs-fichiers)
- [Formats G2 acceptés](#formats-g2-acceptés)
- [Source maître Savings Account et contrôle DAT](#source-maître-savings-account-et-contrôle-dat)
- [Cockpit Épargnes](#cockpit-épargnes)
- [Interface refactorisée des téléversements](#interface-refactorisée-des-téléversements)
- [Grain, clés et rapprochement](#grain-et-clés)
- [Classification, statuts et anomalies](#classification-des-opérations)
- [Client, extrait et rapprochement Perfect](#client-nom-et-compte-créé)
- [Filtres et fidélisation](#filtres-et-fidélisation)
- [Rapprochement crédits et épargne](#rapprochement-crédits-et-épargne)
- [Échéances et remboursements DAT](#échéances-et-remboursements-dat)
- [Finance Turbo sur une période](#finance-turbo-sur-une-période)
- [Balance et analyses comptables Turbo](#balance-et-analyses-comptables-turbo)
- [Fonctions à privilégier](#fonctions-à-privilégier)
- [Conditions d'interprétation](#conditions-dinterprétation)

## Sources

| Source | Colonnes obligatoires principales | Rôle |
|---|---|---|
| Transactions M-PESA Portal/Turbo | `id`, `customer_id`, `msisdn1`, `account_type`, `reference_id`, `currency_code`, `dr`, `cr`, `bal_before`, `bal_after`, `ref_no`, `description`, `created_at` | Mouvements, extrait client, classification et contrôle G2 |
| `Savings Account` complet | `savings_id`, `customer_id`, `msisdn1`, `product_name`, `product_description`, `balance`, `currency_code`; dates et statut selon l'export | Source maître scindée en épargne courante et DAT actifs/historiques |
| Épargne courante résumée (historique) | `customer_id`, `msisdn`, `product_name`, `account_type`, `balance`, `currency_code`, `created_at`, `updated_at` | Repli partiel avec le résumé DAT dans l'emplacement multiple `Savings Account`; comptes positifs uniquement |
| DAT résumé (historique) | `customer_id`, `msisdn`, `product_name`, `account_type`, `balance`, `currency_code`, `date_approved`, `maturity_date`; `created_at` facultatif | Repli partiel avec le résumé Current dans l'emplacement multiple `Savings Account`; DAT positifs uniquement |
| Crédits | `loan_id`, `customer_id` | Crédits rattachés au client et enrichissement du nom G2 |
| Transactions G2 | `Receipt No`, `Currency`, `Opposite Party` | Entrées, sorties, client, référence et rapport journalier |
| `Clients_Turbo` | `msisdn1`, `created_at` | Date de création du compte et recherche client |
| `Clients_Perfect` | `Phone_Prefixe` | Identité Perfect et contrôle de présence des clients transactionnels Turbo/G2 |

Les colonnes facultatives et alias acceptés sont définis dans `credit_app/data_schema.py`.

## Chargement de plusieurs fichiers

Chaque source peut recevoir plusieurs exports. Ajouter le nom du fichier source avant la normalisation, puis supprimer les chevauchements sans supprimer des opérations distinctes :

| Source | Clé de déduplication prioritaire | Version conservée |
|---|---|---|
| Transactions Turbo | `id`; sinon référence × compte × client × devise × `dr` × `cr` × date | écriture la plus récente |
| `Savings Account` | `savings_id`; sinon client × devise × compte × produit × création | `updated_at` le plus récent |
| DAT | client × devise × compte × approbation × échéance | dernier fichier chargé en cas de même compte |
| Crédits | `loan_id`, puis `id` | `updated_at` le plus récent |
| `Clients_Turbo` | `customer_id`, puis téléphone × création | version la plus récente |
| `Clients_Perfect` | `id_client`, `code_client`, puis identifiant manuel × nom | dernier fichier chargé |
| Transactions G2 | `Receipt No` | statut terminé prioritaire, puis date la plus récente |

Conserver la liste des fichiers ayant fourni un enregistrement canonique. Le nombre de fichiers chargés doit rester visible dans le contrôle d'importation.

## Formats G2 acceptés

Accepter les deux structures suivantes sans modifier le fichier source. Plusieurs relevés d'entrées et de sorties peuvent être chargés ensemble; conserver leur nom dans `fichier_source_g2` avant l'unification :

1. Format avec `Transaction Amount`, éventuellement accompagné de `Details`, `Reason Type`, `Transaction Status`, `Completion Time` et `Balance`.
2. Format relevé organisation avec montant éclaté dans `Paid In` et `Withdrawn`, solde dans `Balance` et nature dans `Details`.

Le relevé peut commencer directement par `Receipt No., Completion Time, Initiation Time, Details, Transaction Status, Currency, Paid In, Withdrawn, Balance, Reason Type, Opposite Party, Linked Transaction ID`. Si cinq lignes descriptives précèdent ces colonnes, détecter et promouvoir la vraie ligne d'en-tête par `fichier_source_g2`; ne jamais demander une suppression manuelle comme prérequis.

## Source maître Savings Account et contrôle DAT

- Normaliser `msisdn1` vers `msisdn` sans perdre la colonne source.
- Classer `Open Savings` / `Current account` en `NORMAL SAVINGS`.
- Classer tout produit ou description `Fixed Account` en `FIXED SAVINGS`.
- Conserver les comptes courants et les DAT à solde positif ou nul dans la source maître; les analyses d'encours et d'échéance peuvent ensuite limiter explicitement leur périmètre aux soldes positifs.
- Le téléversement multiple `Savings Account` accepte aussi les deux vues résumées Current et Fixed ensemble. Marquer ce repli comme partiel : il ne permet pas de reconstruire les comptes à solde nul ni tout l'historique.
- Lorsque la source maître et une ou deux vues résumées sont chargées ensemble, conserver uniquement les fichiers contenant `savings_id`; la source complète est prioritaire et les synthèses ne doivent pas être recomptées.
- Si l'export Current Savings résumé est chargé, le rapprocher avec les comptes courants positifs de la source maître sur `customer_id`, téléphone, produit, devise, solde, `created_at` et `updated_at`.
- Si l'export DAT résumé est chargé, le rapprocher avec les DAT positifs de la source maître sur `customer_id`, `currency_code`, `date_approved`, `maturity_date` et `balance`.
- Cas réel du 17 juillet 2026 : 80 791 comptes dans la source maître, dont 77 084 courants et 3 707 fixes. Les 862 comptes courants positifs correspondent exactement aux 862 lignes du résumé Current Savings; les 76 222 autres comptes courants ont un solde nul. Les 1 214 DAT positifs correspondent exactement aux 1 214 lignes du résumé Fixed Savings; les 2 493 autres DAT ont un solde nul.

## Cockpit Épargnes

L'onglet `Épargnes` s'appuie sur `build_mpesa_savings_cockpit`. Il ne crée pas de source parallèle : il assemble les positions `Savings Account`, les événements `build_turbo_operation_events`, les flux `activite_epargne_clients`, les échéances `build_mpesa_dat_maturity_analysis` et les rapprochements crédit/épargne existants.

Contrat de lecture :

- `Savings Account` = stock actuel : comptes ouverts, DAT, soldes, statuts, produits, dates contractuelles, intérêts et frais fournis par la source.
- `Transactions [Solution Numérique]` = flux de période : dépôts, retraits, transferts DAT, retours DAT, remboursements depuis compte ouvert.
- `G2` = contrôle et identité seulement; il ne pilote pas les KPI d'épargne.
- Un seul instantané `Savings Account` ne permet pas de tracer l'évolution historique de l'encours. Les tendances autorisées concernent les flux Transactions et les créations/activations de comptes.
- Les comptes à solde nul sont conservés lorsque la source complète `Savings Account` est disponible.
- L'activité observée vient des mouvements, pas du seul statut du compte.
- L'inactivité est analytique, non réglementaire, et doit devenir `historique_insuffisant` lorsque l'historique disponible ne couvre pas le seuil.
- Le taux annuel DAT par défaut reste 11 %, avec 0 % autorisé pour désactiver l'estimation.
- Les KPI non démontrables restent en `data_gap` : renouvellement DAT, churn certifié, dormance réglementaire, part digitale et historique d'encours.
- Les opportunités `DAT sans crédit actif` et `forte épargne sans crédit` sont commerciales et prudentes, jamais des décisions d'éligibilité.
- Tous les montants et ratios monétaires restent séparés par devise.

Exports Excel principaux : `Epargne_Vue_Ensemble`, `Epargne_Portefeuille`, `Epargne_Detail`, `Epargne_Flux`, `Epargne_Evolution_Flux`, `Epargne_Activite`, `Epargne_Produits`, `Epargne_Concentration`, `Epargne_Top_Clients`, `Epargne_DAT`, `Epargne_Echeances_DAT`, `Epargne_Opportunites`, `Epargne_Qualite`, `Epargne_Catalogue_KPI` et les listes d'action appelées par l'écran.

## Interface refactorisée des téléversements

Dans l'interface utilisateur, l'ancienne appellation `Turbo` est remplacée par `Solution Numérique` chaque fois que le libellé est destiné au métier. `Turbo` reste autorisé dans les noms de fonctions, colonnes, feuilles Excel, clés de cache et tests historiques lorsque cela évite de casser un contrat technique. `G2` désigne le rapport de contrôle du canal M-Pesa; il ne constitue pas un canal financier additionnel et ne doit jamais être additionné séparément à M-Pesa.

L'interface Streamlit utilise désormais ce parcours :

| Niveau | Téléversement | Rôle |
|---|---|---|
| Solution Numérique principale | `Transactions` | Journal des écritures et mouvements |
| Solution Numérique principale | `Savings Account` | Source maître de l'épargne courante et des DAT |
| Solution Numérique principale | `Loans Account` | Crédits, encours, échéances et remboursements |
| Solution Numérique principale | `Customers` | Téléphone et date de création client |
| Facultatif | `Rapport G2 M-Pesa` multiple | Entrées 1441, sorties 15558, noms et contrôle indépendant |
| Facultatif | `Clients_Perfect` | Contrôle et adoption intersystèmes |

`Customers with Current Savings Account` et `Customers with Fixed Savings Account` n'ont pas de widgets séparés. Ils peuvent être sélectionnés ensemble dans l'emplacement multiple `Savings Account` lorsque la source complète n'est pas disponible. L'interface doit alors avertir que seuls les soldes positifs sont couverts. Si le fichier complet est aussi présent, il est seul retenu. Les quatre emplacements Turbo principaux doivent produire les mêmes comptes, soldes, devises, statuts et dates que la source maître validée lorsque celle-ci est fournie.

Les sous-onglets principaux de Solution M-PESA suivent l'ordre `Importation et contrôle`, `Extraits clients`, `Finance et comptabilité`, `Épargnes`, `Crédits`, `Solution Numérique / M-Pesa`, `Perfect Client`, `Statistiques`, `Projections`. `Controle des donnees` est integre dans `Importation et contrôle` afin de regrouper chargement, validation des colonnes, composition Savings Account et anomalies Transactions [Turbo].

Le contrat de `Projections` reste strictement Solution Numérique-first. Les séries monétaires sont construites et évaluées par `currency_code`; aucune prévision CDF et USD ne peut être totalisée. Les événements de Transactions [Solution Numérique] alimentent clients actifs, opérations, volumes, décaissements et remboursements; Customers alimente les créations de clients; Savings Account alimente les créations de comptes et l'échéancier DAT; Loans Account alimente les créations et montants de crédits. Les rapports G2 M-Pesa et Perfect restent exclus du modèle. Les échéances DAT sont des calculs contractuels déterministes. Les positions de solde et d'encours provenant d'instantanés ne sont pas extrapolées sans historique de plusieurs arrêtés.

Règles de montant et de sens :

- utiliser `Paid In` comme montant d'entrée lorsqu'il est non nul;
- utiliser `Withdrawn` comme montant de sortie lorsqu'il est non nul;
- utiliser le signe de `Transaction Amount` comme repli si les colonnes éclatées sont absentes;
- conserver `balance_numeric` comme solde du relevé G2, sans le confondre avec un mouvement;
- convertir les dates et montants avec erreurs contrôlées et conserver la colonne source utilisée.

Pour Transactions Turbo, ne pas appliquer ces règles G2. Utiliser `dr` comme sortie du compte `MPESA ACCOUNT` et `cr` comme entrée, puis regrouper les écritures techniques par `ref_no` pour le rapprochement.

## Colonnes visibles utilisateur

Le contrat metier interne conserve les colonnes techniques de `credit_app/data_schema.py` et de `credit_app/services/mpesa_analysis.py`. Le renommage utilisateur ne doit intervenir qu'au moment de rendre un tableau Streamlit ou d'ecrire un export Excel.

Lorsque l'option globale `credit_standardize_columns` du sidebar est active (`Reference et stockage > Preparation des donnees > Renommer automatiquement les colonnes`), les noms visibles doivent respecter les regles suivantes :

| Regle | Attendu |
|---|---|
| Convention | francais, minuscules, sans accents, `snake_case` |
| Expression valide | `^[a-z0-9_]+$` |
| Source de correspondance | `data/Rename_columns.xlsx` |
| Colonnes non referencees | conversion automatique lisible en `snake_case` |
| Collision | conserver toutes les colonnes avec suffixe stable |
| Option desactivee | conserver les noms techniques originaux |

Exemples attendus : `customer_id` -> `id_client`, `msisdn1` -> `numero_telephone`, `currency_code` -> `devise`, `created_at` -> `date_creation`, `loan_amount` -> `montant_credit`, `dr` -> `debit`, `cr` -> `credit`, `bal_before` -> `solde_avant`, `bal_after` -> `solde_apres`, `Receipt No.` -> `reference`.

Ce contrat ne modifie ni les fichiers Excel sources, ni les calculs, ni les cles de jointure. Les tests doivent couvrir au minimum le mapping explicite, le repli automatique, les collisions et l'export Excel.

## Grain et clés

| Objet | Grain | Clé ou règle |
|---|---|---|
| Transaction G2 analytique | Une ligne par reçu | `receipt_no` normalisé |
| Écritures Portal/Turbo | Plusieurs lignes comptables possibles par opération | `ref_no` |
| Client Turbo | Une ou plusieurs fiches/comptes | `customer_id`, puis téléphone normalisé |
| Client Perfect | Une ou plusieurs identités possibles par téléphone | `Phone_Prefixe` normalisé |
| Synthèse financière | Devise × sens × type d'opération | Ne jamais agréger plusieurs devises ensemble |

Pour un `Receipt No.` dupliqué, sélectionner comme ligne canonique une ligne terminée en priorité, puis la plus récente. Conserver `nombre_lignes_g2_reference`, les valeurs sources observées et `doublon_receipt_no`.

## Rapprochement G2 avec le Portal/Turbo

1. Normaliser `Receipt No.` et `ref_no`.
2. Regrouper les écritures Portal par `ref_no` sans sommer plusieurs fois les mouvements miroir.
3. Joindre G2 sur `receipt_no = ref_no_portal`, même si la devise diffère, afin de pouvoir détecter l'écart de devise.
4. Pour une sortie `BisouBisouB2C` non retrouvée par la clé principale, rechercher uniquement les groupes Turbo `Retrait Vers M-Pesa` au grain `reference_id + created_at`. Exiger téléphone, devise et montant identiques, ainsi qu'un écart absolu maximal de 120 minutes. `reference_id` seul ne constitue pas une clé de transaction, car il peut être réutilisé pour plusieurs retraits du même compte.
5. Contrôler ensuite :
   - téléphone G2 extrait de `Opposite Party` contre `msisdn1`;
   - devise G2 contre les devises du groupe Portal;
   - montant absolu G2 contre le mouvement du compte M-PESA Portal;
   - création G2 `Initiation Time` contre `created_at` Turbo; si `Initiation Time` manque, utiliser `Completion Time` comme repli tracé;
   - finalisation `Completion Time` et délai `Completion Time - Initiation Time` séparément.
6. Produire `Rapproche exact`, `Rapproche avec ecart`, `Non rapproche` ou `Non applicable - operation interne`.

Le contrôle de date utilise un seuil de 60 minutes, distinct de la fenêtre de recherche B2C de 120 minutes. Une différence absolue supérieure à 60 minutes produit `Ecart de date`, même le même jour, et doit apparaître dans `Anomalies_G2`. Un changement de date civile reste `Conforme - passage de date` si l'écart ne dépasse pas 60 minutes; conserver alors les dates G2/Turbo dans `Observation`. Un délai de traitement G2 négatif est toujours une anomalie.

Colonnes de traçabilité du repli sortie : `reference_sortie_turbo`, `cle_sortie_turbo`, `cle_rapprochement_turbo`, `methode_rapprochement_turbo`, `nombre_candidats_sortie_turbo` et `operation_turbo_confirmee`. Plus d'un candidat déclenche une revue et ne doit pas être présenté comme un rapprochement exact.

Ne pas considérer le nombre d'écritures Portal comme le nombre d'opérations clients. Une opération peut produire plusieurs lignes `MPESA ACCOUNT`, `NORMAL SAVINGS`, `FIXED SAVINGS` ou comptes de prêt.

### Mode G2/DAT sans fichier G2

Lorsque `Transactions M-PESA_G2` est absent, limiter le rapport aux opérations prouvées par Turbo :

1. regrouper les lignes portant un `ref_no` et retenir les groupes classables en `Depot normal`, `DAT` ou `Remboursement prets`;
2. regrouper les lignes `Retrait Vers M-Pesa` au grain `reference_id + created_at` et les classer en `Paiement client B2C`;
3. prendre le montant absolu d'une ligne comptable représentative du groupe, sans sommer les miroirs;
4. utiliser `created_at` pour la date et l'heure, `Comptabilisee Turbo` pour le libellé de périmètre et `Turbo seul` pour la source analytique;
5. renseigner `Non applicable - Turbo seul` pour les contrôles téléphone, devise, montant et dates G2/Turbo, ainsi que pour le statut de rapprochement;
6. ne pas déduire les sorties G2 `Demande de credit`, les opérations internes, le nom client G2, le statut G2, le solde G2 ou les dates G2 si ces informations ne sont pas présentes dans Turbo.

Si un fichier G2 est chargé, ne pas concaténer ce proxy aux transactions G2 : le pipeline canonique G2 et ses contrôles redeviennent prioritaires.

## Classification des opérations

Pour une entrée avec référence Portal retrouvée, appliquer cette priorité :

1. compte ou description contenant `LOAN ACCOUNT`, `LOAN PORTFOLIO`, `PRINCIPLE`, `repayment` ou `remboursement` → `Remboursement prets`;
2. `FIXED SAVINGS` ou `Depot Bloque` → `DAT`;
3. `NORMAL SAVINGS` ou `Epargne depot` → `Depot normal`.

Sans référence Portal, utiliser les règles G2 :

| Valeur G2 indicative | Sens | Classification |
|---|---|---|
| `BisouBisouC2B` | Entrée | `Depot normal`, sauf DAT identifié par le repli documenté |
| `BisouBisouC2BRepayment` ou `BisouBisouRepayment` | Entrée | `Remboursement prets` |
| `BisouBisouB2C` | Sortie | `Paiement client B2C` |
| `BisouBisouLoanRequest` ou `Loan payement` | Sortie | `Demande de credit` |
| `Super Transaction` | Selon `Paid In`/`Withdrawn` | `Operation interne Bisou` |

Une sortie B2C confirmée par Turbo conserve `Paiement client B2C` comme classification G2 et reçoit `Retrait epargne vers M-PESA` dans `operation_turbo_confirmee`. Ne jamais utiliser une sortie comme candidate DAT. Conserver `Autre entree`, `Autre sortie` ou `Flux a verifier` lorsque la nature reste indéterminée.

## Inclusion et anomalies

- Si la colonne contient au moins un statut, inclure dans les synthèses uniquement les statuts terminés reconnus (`Completed`, `Successful` et variantes normalisées).
- Si l'ancien export ne contient aucun statut exploitable, conserver toutes ses lignes pour compatibilité. Dans un export moderne à statuts mixtes, traiter une valeur vide comme `Non renseigne` et l'exclure des analyses.
- Normaliser les statuts de contrôle en `Completed`, `Declined`, `Cancelled`, `Expired`, `Pending`, `Non renseigne` ou `Autre`; conserver la valeur source.
- Exclure les statuts non terminés des analyses financières, temporelles, DAT, Perfect et du Word, mais les conserver dans `Statuts_G2`, le détail Excel et les anomalies.
- Créer une anomalie pour : reçu manquant ou dupliqué, statut non terminé, référence Portal absente, écart de téléphone/devise/montant/date ou opération non classée.
- Exporter les anomalies dans `Anomalies_G2` et les afficher dans G2/DAT.

## Client, nom et compte créé

- Normaliser les numéros vers le format `243...` avant toute comparaison.
- Construire l'extrait client depuis Transactions M-PESA_Turbo sans exiger G2. Le mode `Turbo seul` conserve la recherche par `customer_id` ou téléphone, les filtres, la synthèse et les exports.
- Extraire le téléphone et le nom G2 depuis `Opposite Party`.
- Considérer Portal Turbo comme source financière principale et G2 comme vérification facultative et complément de nom. Enrichir les rapports Turbo avec `Nom_client` par téléphone; utiliser la référence G2/Portal lorsqu'elle est disponible et pertinente, sans substituer les montants, dates, soldes ou mouvements G2 aux données Turbo.
- Dans l'extrait officiel écran/Word, alimenter `Description` avec toutes les valeurs distinctes de `description` Turbo partageant `customer_id + devise + created_at + operation_reference`. Conserver l'ordre Turbo, puis ajouter le téléphone et `Nom_client` s'ils sont disponibles. `Details`, `Reason Type` et les autres libellés G2 restent des colonnes de contrôle et ne remplacent jamais cette description.
- Inverser le sens comptable Turbo uniquement dans la restitution officielle client : `dr`/`sortie_mpesa` correspond à une entrée Bisou Bisou et `cr`/`entree_mpesa` à une sortie Bisou Bisou. Ne pas modifier les colonnes techniques Turbo sources.
- Pour un octroi de crédit, identifier dans le même événement Turbo le crédit `MPESA ACCOUNT` comme prêt brut et le débit `MPESA ACCOUNT` comme intérêt retenu. Le taux de référence Bisou Bisou est 7 % : `interet_reference = pret_brut × 0,07`, `taux_observe = interet_preleve / pret_brut × 100` et `net_verse = pret_brut - interet_preleve`. L'extrait client utilise le net versé comme sortie et décrit séparément le brut, l'intérêt, le taux et le net.
- Exiger les deux lignes `MPESA ACCOUNT` avant d'afficher ce détail. Si le débit d'intérêt est absent, l'export est insuffisant pour calculer un net contractuel : conserver le mouvement brut observé et ne pas injecter automatiquement 7 % dans les montants officiels.
- Conserver le crédit brut dans `Finance Turbo > Nouveaux crédits` et la ligne `INTEREST EARNED` dans les produits financiers. Produire aussi `produits_financiers_detail` au grain de l'écriture Turbo avec date, client, devise, compte et références, afin de retrouver les 0,35 USD du scénario sans confondre ce montant avec le total de la période. Ne pas déduire l'intérêt du montant accordé dans le portefeuille et ne pas l'ajouter une seconde fois au net client.
- Ne jamais utiliser `reference_id` seul comme grain d'un événement crédit. Séparer au minimum par client, devise et `created_at`, puis par `ref_no` lorsqu'il existe. Référence de non-régression : `PRET_TEST_001` comporte 12 écritures d'octroi à `2026-07-22 16:17:16` et 4 écritures de remboursement portant ce `reference_id` à `2026-07-22 16:26:43`. Deux lignes techniques supplémentaires `NORMAL SAVINGS`/`FIXED SAVINGS` sans ce `reference_id` portent le même `ref_no` de remboursement; l'événement de remboursement contient donc 6 écritures.
- Réserver le solde du portefeuille M-PESA aux analyses internes lorsqu'il serait présenté comme bloc séparé. Dans l'aperçu, le Word et le PDF, présenter un relevé bancaire unique dans `Synthèse financière par devise`, avec les mouvements du compte ouvert et les positions `Compte ouvert` / `Compte bloqué` issues de `Savings Account`, sans compenser ces positions avec le crédit.
- Ne plus exposer deux familles `vue Bisou Bisou` et `vue client` dans l'Extrait client. Les restitutions visibles sont seulement `global` et `minimal`. Dans le contenu visible des Word/PDF, ne jamais afficher `vue client`, `vue Bisou Bisou`, `point de vue Bisou Bisou` ou `Synthèse de la position client`; conserver les titres neutres `Extrait de compte`, `Extrait minimal de compte` et `Synthèse financière par devise`.
- Dans un événement de remboursement depuis `NORMAL SAVINGS`, ignorer pour la position DAT la ligne technique `FIXED SAVINGS` portant le même libellé; elle ne prouve pas une sortie du compte bloqué.
- Commencer la restitution financière Word/PDF par le titre sobre `Synthèse financière par devise`, suivi d'un tableau limité à `Devise`, `Ouverture`, `Entrée`, `Sorties`, `Cloture`, `Compte ouvert` et `Compte bloqué`. Ne pas afficher `Flux net externe`. Ne pas ajouter `point de vue Bisou Bisou` au titre ni de phrase explicative sous le tableau. Ne pas produire de tableau séparé `Situation de l'épargne` ou `Situation financière actuelle du client`; l'ouverture et la clôture restent dans la synthèse.
- Affecter `compte = 1441` aux entrées et `compte = 15558` aux sorties. Conserver `devise` dans chaque ligne de l'extrait.
- Autoriser `currency = ALL` dans le Word. Dans ce mode, garder une seule annexe transactionnelle mais produire une ligne de synthèse distincte pour CDF et USD; laisser les totaux globaux multidevises vides.
- Les critères Word affichent `Devise : CDF`, `Devise : USD` ou `Devise : ALL (CDF, USD)` et n'affichent plus `Compte :`.
- Le périmètre par défaut comprend `Sortie M-PESA_Turbo vers epargne`, `Sortie M-PESA_Turbo vers DAT`, `Entree M-PESA_Turbo depuis epargne` pour les retraits client, `Decaissement de credit`, `Remboursement de credit` et `Remboursement avec penalite`. Pour `Retrait Vers M-Pesa` sans `ref_no`, une transaction unique est définie par `customer_id + currency_code + created_at + reference_id`; les lignes `MPESA ACCOUNT` et `NORMAL SAVINGS` sont deux faces de cette même transaction.
- Le nom du Word Turbo seul suit `extrait_compte_<customer_id>_<telephone>_<devise>_<debut>_<fin>.docx`. Avec G2 chargé, insérer `Nom_client` entre `customer_id` et le téléphone. Le contenu du Word officiel ne porte pas de suffixe `[Turbo]`. Dans le détail, nommer `operation_reference` `Référence Turbo` et utiliser les colonnes `Entrées`, `Sorties` et `Solde`; réserver `Receipt No.` au rapprochement G2. Le tableau `Détail des transactions` couvre les opérations bancaires utiles au compte client : dépôt, retrait, retrait de DAT avant échéance, retour du montant principal du DAT, entrée des intérêts sur DAT et remboursement d'un crédit depuis le compte ouvert. Exclure les décaissements de prêt, car ils passent du compte prêt Bisou Bisou vers le compte M-PESA du client sans toucher le compte ouvert. Exclure aussi les dépôts DAT initiaux, qui appartiennent au compte bloqué et restent dans les blocs DAT. Ce solde exclut toujours l'ouverture client et ne constitue jamais un solde réel; l'ouverture et la clôture sont affichées dans `Synthèse financière par devise`.
- Le format minimal exclut `Synthese du comportement observe`, `Positions observees et rapprochement des soldes`, `Jalons du parcours financier` et les blocs analytiques complémentaires. Il conserve `Detail des transactions` et utilise `Solution Bisou Bisou Digital` dans son pied de page.
- Le titre Word inclut le nom seulement lorsqu'il est réellement disponible. Sans nom, il suit `Extrait de compte - <telephone> - <devise>` et n'affiche ni `NON DISPONIBLE` ni un séparateur vide.
- Dans l'Extrait client, filtrer `g2_dat` sur le `customer_id` sélectionné avant affichage et export, même sans fichier DAT.
- Construire `dat_en_cours_client` depuis les `FIXED SAVINGS` à solde positif du client dans `Savings Account`. Cette position est filtrée par client et devise, mais pas par la période ni la référence des transactions.
- Fixer `date_situation` depuis `updated_at` ou `date_locked`, à défaut depuis la dernière transaction Turbo du client, puis depuis `created_at` ou `date_approved`. Ne jamais utiliser G2 pour dater ou valoriser un DAT.
- Estimer l'intérêt par `balance × taux / 100 × durée_contractuelle_jours / 365`, avec 11 % par défaut. Afficher le taux annuel DAT dans les critères du document. Limiter le tableau `DAT en cours` à `DAT`, `Souscription`, `Échéance`, `Jours restants`, `Devise`, `Capital bloqué`, `Situation` et `Capital + intérêt estimé`. L'estimation n'est pas une écriture comptable.
- Construire la synthèse et le détail des remboursements depuis les seuls événements Turbo `Remboursement de credit` et `Remboursement avec penalite`. Limiter le tableau Word/PDF à la date, la référence, la devise, le montant payé, les intérêts, l'origine du paiement et les pénalités. Exclure le principal, le mode observé, les décaissements, la dette créée et les positions de crédit de l'Extrait client.
- Dans le format global de l'Extrait client, ajouter un bloc `Prochains remboursements sur la période` construit uniquement depuis `Loans Account [Turbo]`. Filtrer par client, devise et `due_date` comprise entre `Date de debut` et `Date de fin`; afficher la date prévue, le crédit, la devise, le montant à rembourser, le principal, les intérêts, les pénalités et le statut. Ne pas inclure ce bloc dans le format minimal.
- Lorsqu'un remboursement est financé par `NORMAL SAVINGS`, le conserver dans `Remboursements observés`, l'exclure des entrées externes et des sorties externes, puis le conserver dans `Détail des transactions` parce qu'il débite effectivement le compte ouvert du client. Il s'agit d'un transfert interne entre l'épargne ouverte et le crédit, pas d'une nouvelle trésorerie reçue.
- Produire `elements_extrait_client_turbo` et sa synthèse avec les familles de couverture utiles, notamment `Depot normal`, `Dépôt à terme (DAT)`, `Retrait`, `Remboursement d'un credit depuis le compte M-PESA`, `Remboursement d'un credit depuis le compte ouvert`, `Retour du capital mis en DAT` et `Entree des interets du capital mis en DAT`. Dans `Détail des transactions`, retenir seulement les six opérations de relevé : dépôt, retrait, retrait de DAT avant échéance, retour du montant principal du DAT, entrée des intérêts sur DAT et remboursement d'un crédit depuis le compte ouvert.
- Construire `Dépôt à terme (DAT)` depuis les événements `Sortie M-PESA_Turbo vers DAT`. Dans les Word/PDF, le présenter dans `Éléments couverts par l'extrait client` et dans `DAT en cours` lorsque `Savings Account` confirme la position, puis l'omettre du tableau `Détail des transactions` parce qu'il concerne le compte bloqué et non le compte ouvert. Ne pas le transformer en position `DAT en cours` sans `Savings Account`.
- Pour un remboursement, retenir `Compte ouvert` lorsqu'une ligne `NORMAL SAVINGS` du même événement porte un libellé de remboursement de compte; sinon retenir le mouvement `MPESA ACCOUNT`. Le montant payé suit cette source avant tout repli sur le montant global de l'événement.
- Construire les retours de capital DAT depuis `Retrait Compte Bloque` dans Transactions Turbo. Pour chaque retour, exposer `date_creation_dat` et `date_fin_dat` : résoudre la référence depuis la ligne `FIXED SAVINGS` de l'événement, lire la création du `Savings Account` exactement correspondant, puis utiliser l'horodatage du dépôt bloqué Turbo portant le même `reference_id` en repli. Un DAT unique du même client et de la même devise peut servir de dernier repli; avec plusieurs candidats sans référence exacte, laisser la création non déterminée. Construire les entrées d'intérêts DAT uniquement depuis `Savings Account.interest_earned` sur les DAT arrivés à échéance et dénoués. Ces deux familles peuvent alimenter `Détail des transactions` comme entrées de relevé lorsqu'elles reviennent au compte client, même sans ligne `MPESA ACCOUNT` correspondante.
- Dans les Word/PDF du relevé global, ne restituer pour l'intérêt DAT que l'échéance, le `savings_id`, la devise, le capital placé, `interet_client_constate` et `montant_echeance_client`; exclure `voda_interest`, `statut_tracabilite` et les autres colonnes techniques.
- Rechercher `compte_cree` dans cet ordre : `Clients.created_at`, épargne courante `created_at`, DAT `created_at` ou `date_approved`.
- Résoudre vers `customer_id` avant de construire l'extrait client.
- Permettre la recherche de l'extrait par `customer_id`, téléphone et nom G2 lorsque le fichier G2 est chargé.
- Agréger Perfect par `Phone_Prefixe` avant la jointure et conserver `nb_clients_perfect` ainsi que les noms Perfect concaténés.
- Matérialiser `present_dans_turbo`, `present_dans_g2`, `present_dans_perfect` et `present_dans_les_3_systemes` au grain d'un téléphone normalisé. Le dataset `clients_trois_systemes` ne conserve que l'intersection stricte G2–Turbo–Perfect.

## Rapprochement Perfect_client

La population de départ contient les téléphones observés dans au moins une source Turbo ou G2. Perfect enrichit cette population mais ne crée pas, à lui seul, une ligne dans la synthèse.

| Indicateur | Condition |
|---|---|
| `present_dans_turbo` | Téléphone valide observé dans Transactions, Clients, épargne courante, DAT ou Crédits Turbo |
| `present_dans_g2` | Téléphone valide extrait de `Opposite Party` dans Transactions G2 |
| `present_dans_perfect` | Au moins une fiche de l'export 122 retrouvée après normalisation de `Phone_Prefixe` |
| `present_dans_les_3_systemes` | Les trois indicateurs précédents valent vrai |

Règles de restitution :

- conserver une ligne de synthèse par téléphone normalisé;
- agréger les fiches Perfect partageant le même téléphone avant la jointure;
- conserver les noms, identifiants, codes clients, gestionnaires et collecteurs Perfect concaténés;
- utiliser `clients_trois_systemes` pour la vue prioritaire et la feuille Excel `Clients_Perfect_3_Systemes`;
- conserver la population générale dans `Clients_Perfect` et les opérations G2/Turbo dans `Operations_Turbo_G2`;
- ne pas attribuer d'opérations financières à Perfect, car l'export 122 décrit les clients et la qualité de leurs téléphones.

Populations attendues :

| Dataset | Condition | Feuille Excel |
|---|---|---|
| `clients_perfect_dans_mpesa` | `present_dans_g2` et `present_dans_perfect` | `Clients_Perfect_G2` |
| `clients_perfect_dans_turbo` | `present_dans_turbo` et `present_dans_perfect` | `Clients_Perfect_Turbo` |
| `clients_perfect_dans_turbo_et_mpesa` | `present_dans_turbo`, `present_dans_g2` et `present_dans_perfect` | `Clients_Perfect_Turbo_G2` |

Les deux premières populations incluent les clients de la troisième. Compter les fiches Perfect avec la somme de `nb_clients_perfect`, mais conserver une seule ligne par téléphone dans les tableaux.

## Tableau Transactions classées

Utiliser la constante `G2_CLASSIFIED_TRANSACTION_COLUMNS` comme contrat partagé entre Streamlit et Word :

```text
date
receipt_no
currency_code
details_rapport
opposite_party
duree
compte_cree
montant
montant_entree
montant_sortie
balance_numeric
```

Trier par `currency_code` croissant, puis `date` décroissante. Le Word doit reprendre un seul tableau en A4 portrait, avec les mêmes colonnes et le même ordre que l'écran. Adapter les largeurs et la taille de police au portrait sans supprimer de colonne. Reprendre le logo officiel et la mise en forme de l'Extrait client dans l'en-tête du rapport G2/DAT. Les critères présentent deux bornes séparées : `Date du :` avec l'horodatage de début du filtre et `Au :` avec l'horodatage de fin; ne pas les condenser dans une ligne `Période`.

Le bloc Word `Synthese des flux G2 par devise` utilise `rapport_journalier_pivot`. Ce pivot appartient au contexte Word même s'il n'est pas écrit comme feuille Excel. S'il manque, le générateur doit le reconstruire avec `build_entry_pivot(rapport_journalier_detail)`.

## Filtres et fidélisation

- Appliquer d'abord les bornes inclusives de date et d'heure de `Completion Time`, puis le multisélecteur de sens. Sans heure explicite, conserver toute la journée de début et de fin.
- Interpréter une sélection vide ou toutes les valeurs sélectionnées comme tous les flux.
- Appliquer le même périmètre à la synthèse, au détail, au contrôle et aux exports.
- Agréger le jour de semaine de `Completion Time` de lundi à dimanche, avec les jours sans transaction à zéro; l'indicateur du jour le plus actif utilise le cumul de chaque jour de semaine sur toute la période filtrée.
- Calculer la fidélisation par téléphone, mois de base et devise.
- Laisser les taux M+1 ou 90 jours vides tant que la fenêtre complète n'est pas observable.
- Exclure de la fidélisation les opérations internes, téléphones invalides et statuts en échec/annulés/inversés.

## Rapprochement crédits et épargne

- `Loans Account` reste la source de vérité pour `loan_id`, le montant accordé, l'encours, les remboursements, le principal, les intérêts, les frais, les pénalités, l'échéance et le statut. Ces données ne sont pas reconstructibles depuis `Savings Account`.
- Tenter d'abord la liaison directe `Loans.savings_account_id = Savings Account.id` ou `Savings Account.savings_id`. Exiger une seule correspondance et contrôler ensuite client, devise et téléphone.
- Lorsque l'identifiant direct est vide, autoriser uniquement le repli `customer_id + currency_code` si un seul compte `NORMAL SAVINGS` est candidat. Conserver `savings_id_correspondant`, `methode_rapprochement_epargne`, `statut_controle` et `motif_controle`.
- Un identifiant direct introuvable, aucun compte courant, plusieurs comptes candidats ou un écart de client, devise ou téléphone produit `A revoir`. L'absence totale de Savings Account produit `Non calculable`, pas une anomalie opérationnelle.
- Construire la restitution consolidée au grain `customer_id x currency_code`. Agréger les prêts, puis joindre une seule fois la position du ou des comptes courants et les DAT à solde positif du client afin de ne pas multiplier l'épargne lorsqu'il existe plusieurs prêts.
- Afficher séparément montant accordé, montant remboursé, encours, principal, intérêts, pénalités, épargne courante et DAT. `epargne_totale_observee` additionne uniquement l'épargne courante et les DAT de la même devise; elle ne compense jamais l'encours et ne prouve pas une garantie.
- Cas réel du 17 juillet 2026 : 2 213 crédits, 594 clients et aucun `savings_account_id` renseigné. Le repli unique client x devise rapproche 1 740 / 1 740 crédits CDF et 472 / 473 crédits USD; le crédit USD restant n'a pas de compte courant correspondant.

## Échéances et remboursements DAT

- Utiliser les DAT `FIXED SAVINGS` de `Savings Account` dont le solde est strictement positif.
- Classer les comptes selon `maturity_date - date_analyse` : échu, aujourd'hui, 0–7, 8–30, 31–60, 61–90 ou plus de 90 jours. Inclure tous les échus et les échéances comprises dans l'horizon de préparation, fixé à 30 jours par défaut et réglable jusqu'à 90 jours.
- Utiliser 11 % comme taux annuel DAT Bisou Bisou par défaut. Autoriser la modification du taux dans la barre latérale et la valeur 0 pour désactiver l'estimation.
- Estimer l'intérêt simple à l'échéance par `balance × taux / 100 × durée_contractuelle_jours / 365`, avec `durée_contractuelle_jours = maturity_date - date_approved`.
- Afficher `savings_id`, client, nom G2 disponible, téléphone, devise, produit, statut, capital, approbation, échéance, durée estimée, jours restants, action de remboursement, intérêt estimé et capital plus intérêt.
- Calculer les indicateurs et montants séparément par devise. Ne jamais additionner CDF et USD et ne jamais présenter l'estimation comme une écriture officielle.
- Distinguer l'échéancier prévisionnel des écritures d'intérêts échus : le premier estime à 11 % les DAT positifs à préparer; les secondes utilisent exclusivement `interest_earned` sur les DAT dénoués et restent hors du solde M-PESA.

## Finance Turbo sur une période

L'interface réunit le pilotage financier et la comptabilité observée dans un seul sous-onglet principal `Finance et comptabilité`. Une période et une sélection de devises alimentent les six volets `Vue direction`, `Flux et activité`, `Crédit, épargne et DAT`, `Balances et journaux`, `Risques et contrôles` et `Export`. Les deux rapports sont construits avant le rendu des volets et mis en cache; les exports de pilotage et de comptabilité conservent des contrats séparés.

- Utiliser `build_turbo_operation_events` pour consolider une seule fois Transactions M-PESA_Turbo au grain événement. La clé prioritaire est `ref_no`; sans référence, utiliser `customer_id + currency_code + created_at` et conserver les ventilations techniques dans le même événement.
- Utiliser `build_mpesa_turbo_financial_analysis` ou `build_mpesa_management_dashboard` avec `date_start`, `date_end` et `frequency`. Les deux bornes sont incluses; `frequency` accepte le jour, la semaine ou le mois.
- Ne jamais lire les montants G2 pour le pilotage. La ligne de source G2 doit porter `intervient_dans_les_montants = False` et le rôle `Identité et preuve de rapprochement uniquement`.
- Construire `flux_synthese` et `flux_evolution` depuis `montant_entree_bisou`, `montant_sortie_bisou`, les dépôts d'épargne, les dépôts DAT, les retraits, les décaissements et les remboursements observés.
- Construire `remboursements_synthese` et `remboursements_detail` uniquement avec `Remboursement de credit` et `Remboursement avec penalite`. Conserver principal, intérêt, pénalité, mode observé et contrôle des écritures miroir.
- Construire `nouveaux_credits_synthese` depuis les décaissements Transactions Turbo et les comptes `Loans Account` créés dans la période. Rapprocher les totaux par devise sans prétendre à une affectation ligne à ligne.
- Utiliser `credit_synthese`, `credit_detail`, `par_tranches_montant`, `concentration_credit_synthese` et `concentration_credit_clients` pour l'encours, le PAR simplifié, les tranches et les concentrations. La source reste l'instantané Loans Account.
- Utiliser `activite_epargne_clients`, `depots_frequents_hebdo`, `tranches_depots`, `dat_echeances_detail`, `dat_sans_credit_actif` et `credits_epargne_disponible` pour les analyses d'épargne et de DAT. Ne jamais compenser comptablement l'épargne et le crédit.
- Produire `concentration_transactions_synthese`, `alertes_transactions`, `controles_operations` et `mouvements_comptes_inactifs`. Les alertes couvrent les contrôles Turbo, transactions importantes, fractionnement potentiel et activité inhabituelle comparée aux 90 jours précédents; elles sont des signaux de revue.
- Valeurs par défaut des seuils : fractionnement à 14 000 000 CDF ou 5 000 USD; transaction importante à 28 000 000 CDF ou 10 000 USD. Autoriser leur modification dans le formulaire du cockpit.
- Adapter les requêtes Perfect Vision de niveau 9 ou 10 seulement lorsque les quatre sources Turbo démontrent les champs requis. Sans plan d'amortissement détaillé, calculer un PAR simplifié depuis `due_date` mais ne pas reproduire les échéanciers, provisions ou retards de versement exacts.
- Conserver le journal d'événements en cache par empreinte des fichiers, puis le rapport par période et seuils. Tous les onglets internes du cockpit sont construits lors du premier calcul; changer d'onglet ne relance pas le moteur.

Cas réel du 16 juillet 2026 avec les exports du 17 juillet : 135 événements, dont 48 CDF et 87 USD. Les remboursements observés sont 284 910 CDF et 194,54 USD; les nouveaux crédits décaissés sont 122 200 CDF et 99 USD. Les décaissements et les comptes de crédit créés se rapprochent exactement dans les deux devises pour ce cas.

## Cockpit Crédits

L'onglet `Crédits` utilise `build_mpesa_credit_cockpit`. Il assemble les briques existantes sans créer de source parallèle :

- `Loans Account` reste l'instantané actuel du portefeuille : encours, statuts, `defaulted`, `is_rollover`, `is_grace_period`, `due_date`, dernier remboursement et pénalités restantes.
- `Transactions` fournit uniquement les flux observés sur la période : production de crédit, décaissements, remboursements, intérêts et pénalités. Les écritures brutes ne sont jamais comptées comme opérations.
- `Savings Account` permet la mise en regard analytique crédit/épargne au grain client x devise. L'épargne n'est jamais compensée avec l'encours et ne doit pas être appelée garantie sans preuve contractuelle.
- `G2` reste une source facultative de contrôle et d'identité; il ne calcule ni l'encours, ni les montants du prêt, ni les remboursements.

Les volets attendus sont simplifiés en six blocs : `Vue d'ensemble`, `Production et remboursements`, `Portefeuille et échéances`, `Risques et concentration`, `Crédit et épargne`, `Opportunités et qualité`. Les analyses de production, portefeuille, remboursements, risque, échéances, concentration, crédit/épargne, cohortes, opportunités et qualité restent disponibles dans ces blocs regroupés.

Le `PAR simplifié` est calculé depuis `due_date` et l'encours disponible (`loan_balance` prioritaire, sinon composantes `outstanding_*`). Il doit être libellé comme simplifié et ne remplace pas un PAR réglementaire issu d'un échéancier détaillé. Les KPI suivants restent en `data_gap` sans source fiable : PAR réglementaire détaillé, PAR90/PAR180 exacts, aging détaillé, provision, garantie/caution, collection efficiency, write-off, restructuration, coût du risque et rendement sur encours moyen.

Les listes d'action minimales sont : prêts échus avec encours, prêts `defaulted`, prêts avec pénalités, prêts PAR simplifié 30 jours, fortes expositions, prêts arrivant à échéance dans 30 jours et rapprochements épargne ambigus.

## Statistiques Turbo

- `Statistiques` est un cockpit operationnel Solution Numérique-first distinct de `Finance et comptabilité`. Il sert a suivre la croissance, l'activite, le volume, le chiffre d'affaires observe, l'epargne/DAT, le credit et les meilleurs clients.
- L'ecran `Statistiques` est classe par blocs decisionnels repliables/depliables : `Clients`, `Comptes ouverts et comptes bloques`, `Credits` et `Transactions`. Chaque bloc regroupe ses KPI, graphiques et tableaux afin de faciliter la lecture par la direction et d'eviter une page trop longue.
- Les sources sont hierarchisees ainsi : `Transactions [Turbo]` indispensable, `Savings Account [Turbo]` indispensable, `Loans Account [Turbo]` tres important, `Customers [Turbo]` important, `Transactions [G2]` facultatif utile, `Clients_Perfect` facultatif analytique.
- Le bloc `Transactions` contient une section de contrôle `Qualité du rapprochement G2`. La couverture est complète lorsque les entrées 1441 et les sorties 15558 sont toutes deux présentes; elle est partielle lorsqu'un seul circuit est chargé. L'absence de G2 ne bloque jamais les statistiques Turbo.
- Construire `g2_qualite_rapprochement` par circuit et devise : opérations observées, terminées, rapprochées, non rapprochées, taux et méthode attendue. Les entrées et remboursements 1441 utilisent la clé directe `Receipt No. = ref_no`; les sorties B2C 15558 utilisent téléphone, devise, montant et heure avec les tolérances du rapprochement G2/Turbo.
- Construire `g2_statuts` par devise et conserver `g2_non_rapprochees` uniquement pour les opérations terminées réellement comparables. Une opération interne n'est pas une anomalie de rapprochement.
- Classer `BisouBisouLoanRequest` dans `Versements de prêts [15558]`. Ces opérations ne participent ni au dénominateur des sorties B2C ni à leur nombre de non-rapprochements. Elles exigent un contrôle séparé du prêt brut Turbo, de l'intérêt observé de 7 % et du net versé dans G2.
- Construire `g2_comparaison_hebdomadaire` sur les deux fenêtres déterminées par `Période de comparaison`, par devise, pour le taux global comparable, les entrées 1441 et les sorties B2C 15558. Conserver ce nom de dataset pour compatibilité, même lorsque l'horizon n'est pas hebdomadaire. L'écart entre deux taux est restitué en points de pourcentage.
- Les filtres de l'onglet sont `Date de debut`, `Date de fin`, `Frequence`, `Devises affichees` et `Top clients affiches`. Le bloc de barre latérale `Référence et stockage`, section `Paramètres de calcul`, ajoute `Période de comparaison M_PESA` et `Périmètre annuel M_PESA`; ne pas créer un bloc latéral concurrent. Les KPI, graphiques, tableaux et l'export Word doivent reprendre ces périmètres.
- `Périmètre annuel M_PESA` accepte `Ensemble des années`, `Année unique` et `Plage d'années`. La valeur par défaut conserve l'ensemble des données. Une année ou une plage produit une vue non destructive : Transactions Turbo/G2 sont filtrées strictement entre les bornes annuelles; les instantanés Savings, DAT, Loans et Customers conservent toute position créée/activée avant ou à la fin du périmètre, même si elle est antérieure à l'année de début, ainsi que les lignes sans date. Perfect reste inchangé lorsqu'aucune date métier fiable n'est disponible. L'onglet `Importation` contrôle toujours les sources complètes.
- Les champs `Date de debut` et `Date de fin` définissent ensuite une période plus fine à l'intérieur de la vue annuelle. Le Word Statistiques restitue `Périmètre annuel` dans le tableau des critères. Un instantané unique ne permet pas de reconstituer un solde historique à la clôture d'une ancienne année.
- Dans `Statistiques`, le `compte client` correspond au numero de telephone normalise. Un compte client peut porter plusieurs produits : epargne ouverte, DAT / compte bloque et credit. Les libelles du Word, de l'Excel et de l'ecran doivent donc parler de `Comptes clients ...` pour la base client, puis de `Produits ...` pour les comptes ouverts, DAT et credits.
- `Comptes clients actifs` correspond aux comptes clients ayant au moins une operation Transactions [Turbo] dans la periode, avec le telephone comme cle prioritaire lorsque disponible. Le compteur global reste dans `clients_indicateurs`. Dans `vue_ensemble`, `clients_turbo_actifs` est le compteur propre à la devise de la ligne et `clients_turbo_actifs_global` conserve le total global pour audit, afin de ne pas répéter un total global comme s'il était propre à CDF ou USD. `Comptes clients connus` vient de `Customers [Turbo]` quand la source est chargee; sinon il est degrade depuis les comptes clients observes dans les sources Turbo disponibles.
- La courbe d'evolution des comptes clients utilise `Customers [Turbo].created_at` lorsque disponible. En absence de Customers, elle utilise la premiere observation Turbo connue du compte client.
- `Chiffre d'affaires observe` est prudent et non certifie : interets + penalites + part Bisou detectes dans Transactions [Turbo], toujours separes par devise. G2 et Perfect ne doivent jamais contribuer aux montants.
- `Période de comparaison` accepte quatre valeurs : `7 jours glissants`, `15 jours glissants`, `30 jours glissants` et `Période filtrée`. Le mode par défaut est `7 jours glissants`; `Semaine microfinance (lundi)` n'est plus proposé. Les horizons glissants utilisent deux fenêtres consécutives de même durée. `Période filtrée` compare exactement `Date de début - Date de fin` à la période immédiatement précédente de même nombre de jours.
- Construire `comparaison_annee_precedente` automatiquement depuis les mêmes `Date de debut` et `Date de fin`, décalées d'une année calendaire. Le dataset reprend le bloc, l'indicateur, la devise, les deux valeurs, l'écart, l'évolution, l'unité, la source, les quatre dates et la couverture. Il couvre les clients actifs/nouveaux, les comptes ouverts/DAT créés, les crédits créés et montants accordés, les remboursements, dépôts DAT, opérations, volumes et chiffre d'affaires observé.
- Les histogrammes N/N-1 sont groupés par indicateur. Séparer les graphiques de nombres des graphiques de montants et produire un graphique monétaire distinct par devise. N'afficher dans le graphique que les comparaisons à couverture complète; conserver les couvertures partielles dans les cartes, le tableau et le Word.
- Interpréter `comparaison_annee_precedente` comme une tendance saisonnière indicative, pas comme une norme ni une preuve causale. Une hypothèse de rentrée scolaire ou d'événement externe doit être documentée séparément et validée; Turbo démontre la variation des indicateurs, pas sa cause. Pour parler d'une plage saisonnière habituelle, rechercher idéalement au moins trois années comparables.
- Le contrat de restitution comparative contient le bloc, l'indicateur, la devise, les deux valeurs, l'écart absolu, l'évolution en pourcentage, l'unité, la source, les quatre bornes de date, le mode `periode_comparaison` et le statut de couverture. L'interface affiche `Période analysée` et `Période de référence`; elle ne doit pas afficher `Semaine analysée` pour un horizon de 15 jours, 30 jours ou la période filtrée.
- Les comptes clients actifs et les operations sont calcules depuis les evenements consolides Transactions [Turbo]. Les nouveaux numeros clients utilisent `Customers.created_at`, sinon la premiere observation Turbo. Les nouveaux produits d'epargne ouverte et DAT utilisent `date_activated`, puis `date_approved`, puis `created_at`. Les nouveaux produits credit utilisent `Loans Account.created_at`; les remboursements utilisent les evenements Turbo.
- Les volumes, remboursements, depots DAT, credits accordes et chiffre d'affaires observe restent strictement separes par `currency_code`. Les nombres de comptes clients, produits, credits ou operations peuvent etre presentes globalement.
- `depots_reguliers_synthese` et `depots_reguliers_clients` mesurent les clients qui déposent régulièrement sur le compte ouvert. La source est Transactions [Solution Numérique] au grain événement consolidé; retenir uniquement `NORMAL SAVINGS` / `Epargne depot`. Le score est `jours avec depot / nombre de jours de la periode * 100`, par client et devise. Les catégories sont `Très régulier` (>= 70 %), `Régulier` (>= 40 %), `Occasionnel` (>= 10 %) et `Faible activité` (< 10 %). G2 peut enrichir le nom mais ne calcule ni score ni montant.
- Un fichier `Savings Account` ou `Loans Account` unique est un instantane. Il autorise la comparaison des creations/activations entre semaines, mais pas une variation historique fiable du solde total, du compte bloque, du compte ouvert ou de l'encours. Les indicateurs comparatifs d'encours epargne ouverte, epargne bloquee/DAT et credits reprennent donc le solde instantane des produits crees/actives dans chaque fenetre. Le rapport ajoute aussi les produits epargne/DAT sans produit credit actif, les DAT arrivant a echeance en volume et en encours, ainsi que le taux de conversion DAT en credit, defini comme comptes clients avec produit DAT positif et produit credit actif rapportes aux comptes clients avec produit DAT positif de la meme devise. Une variation historique complete exige plusieurs instantanes dates.
- Une référence comparative nulle produit `Nouvelle activité` lorsque la valeur courante est positive. Une source sans dates exploitables produit `Non calculable`; une plage qui ne couvre pas intégralement les deux fenêtres comparées produit `Partielle`.
- L'export Word du rapport statistiques inclut le logo, les criteres, une synthese executive, puis un rapport professionnel par blocs : `Clients`, `Comptes ouverts et comptes bloques`, `Credits` et `Transactions`. Les analyses textuelles récurrentes sont accompagnées de tableaux synthétiques compacts : analyse, devise, valeur, ratio ou commentaire. Les tableaux doivent éviter les cellules vides nombreuses; lorsqu'un indicateur n'a pas la même structure qu'un autre, le restituer sur une ligne indicateur-valeur plutôt que dans une grille large. Chaque bloc conserve des commentaires textuels courts pour guider la lecture des décideurs. Lorsque G2 est chargé, ajouter `Qualité du rapprochement G2` après l'analyse transactionnelle, avec couverture, taux par circuit et devise, versements de prêts à contrôler séparément, statuts et évolution selon la période de comparaison sélectionnée. Le Word affiche le mode et les quatre bornes comparatives récentes, puis les quatre bornes N-1; chaque bloc commente les valeurs courantes, N-1 et leurs pourcentages sans attribuer automatiquement une cause. Il doit presenter les chiffres, ratios et pourcentages utiles a la direction, sans graphiques dans le Word, puis conserver seulement les annexes utiles au rapport final, notamment la vue d'ensemble. Les listes détaillées volumineuses, comme les clients déposant régulièrement, sont destinées à l'export Excel. Le Word reprend exactement le perimetre filtre de l'onglet. Aucun KPI ecran ni bloc Word ne doit totaliser les montants, volumes, soldes, credits ou chiffre d'affaires entre CDF et USD; seuls les compteurs non monetaires peuvent etre consolides globalement.

## Balance et analyses comptables Turbo

- La source des mouvements est exclusivement Transactions M-PESA_Turbo. G2 ne fournit que le nom client et le contrôle direct `Receipt No = ref_no`.
- La balance auxiliaire client retient `NORMAL SAVINGS` comme épargne courante, `FIXED SAVINGS` comme DAT et `PRINCIPLE` comme principal du crédit. Son grain est `customer_id x devise x famille de position`.
- Une opération utilise `ref_no` comme clé prioritaire. Sans `ref_no`, regrouper les écritures du même `customer_id`, de la même devise et du même `created_at`; ne pas utiliser le nombre de lignes comme nombre d'opérations.
- Conserver séparément : la balance client, la balance auxiliaire par produit, la balance des mouvements par `account_type`, le journal regroupé, le journal brut, les contrôles de symétrie, les contrôles de variation de solde, les flux `MPESA ACCOUNT`, les produits financiers observés, les positions des instantanés et le contrôle G2.
- Le contrôle de variation compare l'amplitude du mouvement à l'amplitude du solde : `abs(bal_after - bal_before)` contre `abs(dr) + abs(cr)`. Un écart est un signal de revue et non une preuve automatique d'erreur.
- Les comptes `INTEREST EARNED`, `LOAN PENALTY FEES`, `BISOU COLLECTION` et `VODA COLLECTION A/C` sont présentés séparément. Ne pas produire un total de revenu sans preuve que ces lignes ne sont pas des ventilations du même produit.
- Les soldes Current Savings, Fixed Savings et Loans sont des instantanés de référence. Ne pas les forcer dans la clôture d'une journée antérieure; afficher leur date disponible et leur source.
- Sans plan comptable complet et soldes d'ouverture officiels, employer `balance observée`, `position observée` et `solde de mouvement`; ne jamais annoncer une balance générale certifiée, un bilan ou un compte de résultat officiel.
- Toutes les colonnes monétaires, tous les ratios et tous les contrôles sont calculés par devise.
- Le volet `Balances et journaux` propose directement `balance_observee_turbo_<debut>_<fin>.docx` et `.pdf`. Les deux documents intègrent le logo, la période, une synthèse par devise et la balance client; ils sont générés en A4 portrait avec des colonnes compactes. Ne pas y afficher le paragraphe `Source des montants...`, la phrase de limite de certification ni le tableau `Balance des mouvements par type de compte`. La balance par `account_type` reste disponible à l'écran et dans les exports comptables techniques.
- Remplacer l'ancien aperçu/export `balance par date` par le `Suivi des dépôts et retraits par client [Turbo]`, inspiré de l'état des mouvements Vodacom. Le tableau croisé contient une ligne `Depot` et une ligne `Retrait` par client et devise, une colonne par jour de la période filtrée, puis `Total`, `Solde` et `Score`. Les montants viennent uniquement de `NORMAL SAVINGS` : `Epargne depot` pour les dépôts et `Retrait Vers M-Pesa` pour les retraits. `Solde` correspond au solde du compte ouvert lorsqu'il est disponible; sinon utiliser le solde net dépôt/retrait de la période. Le `Score` correspond au nombre d'opérations de dépôt ou de retrait rapporté au nombre de jours de la période. Si G2 est téléversé, enrichir seulement le nom du client; ne pas utiliser G2 pour les montants. L'export opérationnel de ce suivi est Excel, avec filtre et ligne d'en-tête gelée, afin de permettre le traitement du tableau large; ne pas privilégier le PDF pour ce suivi.

## Exports Word

- Tous les documents Word de Solution M-PESA utilisent des marges gauche et droite de 2 cm. Préserver l'A4 portrait lorsqu'il est contractuel, puis compacter les colonnes, les largeurs et les polices au lieu de réduire ces marges.

### Cas de référence clôturé du 16 juillet 2026

Utiliser ce cas comme test de non-régression lorsque les mêmes exports sont disponibles. Il décrit le résultat observé dans les fichiers du 17 juillet portant sur les opérations du 16 juillet; il ne définit ni un seuil de performance ni une balance officielle.

Périmètre Turbo attendu : 549 écritures, 75 clients, 135 opérations regroupées et deux devises.

| Devise | Écritures | Clients | Opérations | Débits | Crédits | Opérations symétriques | Opérations à revoir | Variations de solde conformes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CDF | 231 | 28 | 48 | 2 359 892,00 | 2 269 330,00 | 39 / 48 (81,25 %) | 9 | 98,2684 % |
| USD | 318 | 50 | 87 | 9 318,68 | 9 258,01 | 67 / 87 (77,0115 %) | 20 | 96,2264 % |

Avec les fichiers G2 d'entrées 1441 et de sorties 15558, le contrôle direct attend 35 références CDF retrouvées sur 49 transactions G2 terminées (71,4286 %) et 50 références USD sur 83 (60,2410 %). Les sorties B2C rapprochées par téléphone, devise, montant et heure restent distinctes de ce taux direct. La couverture des noms clients Turbo attend 100 % en CDF et 98 % en USD. G2 ne modifie aucun débit, crédit ou solde Turbo.

Les instantanés de portefeuille de référence sont affichés à part :

| Devise | Épargne courante | DAT | Dépôts | Crédits | Crédits / dépôts |
|---|---:|---:|---:|---:|---:|
| CDF | 14 588 636,60 | 74 568 365,74 | 89 157 002,34 | 77 461 721,46 | 86,8824 % |
| USD | 46 463,25 | 156 586,19 | 203 049,44 | 30 555,78 | 15,0484 % |

Les produits financiers observés restent séparés : CDF — intérêts 8 554, pénalités 4 200, part Bisou 64 082, part Voda 27 422; USD — intérêts 6,93, pénalités 0,72, part Bisou 50,01, part Voda 20,31. Ne pas les sommer comme revenu sans preuve supplémentaire.

L'export comptable de référence contient exactement les 12 feuilles suivantes : `Compta_Synthese_Turbo`, `Balance_Clients_Turbo`, `Positions_Clients_Turbo`, `Balance_Comptes_Turbo`, `Journal_Operations_Turbo`, `Journal_Ecritures_Turbo`, `Controles_Operations_Turbo`, `Controles_Soldes_Turbo`, `Flux_MPESA_Turbo`, `Produits_Financiers_Turbo`, `Positions_Portefeuille_Turbo` et `Controle_G2_Turbo`.

### Cas de validation du 21 juillet 2026

Avec `Transactions 20260722_084058.xlsx` présent dans le dossier de test, le journal contient 97 743 écritures et 85 événements le 21 juillet : 25 en CDF et 60 en USD. Le cas comporte 68 lignes client × devise dans la balance et 22 lignes devise × type de compte. Le client `31476` démontre un retour de capital DAT de 200 USD depuis `Retrait Compte Bloque`, conservé hors du solde M-PESA; ses exports client et les exports Word/PDF de balance doivent être générables sans G2 dans les montants.

Cas réel de validation du cycle DAT dans `bdd Solution M_PESA` : le téléphone `243839993536`, client Turbo `22443`, possède le DAT `FAFXZ2Q4RC` de 4 500 000 CDF. `Savings Account` et le dépôt bloqué Turbo donnent une création le 19/12/2025 à 14:04:58; `Retrait Compte Bloque` donne une fin observée le 19/01/2026 à 05:17:09. Le bloc `Retours du capital mis en DAT` doit restituer ces deux horodatages sur la même ligne.

## Fonctions à privilégier

- Préparation : `prepare_transactions`, `prepare_savings_accounts`, `prepare_current_savings`, `prepare_fixed_savings_from_accounts`, `prepare_fixed_savings`, `prepare_loans`, `prepare_g2_transactions`, `prepare_customers`, `prepare_perfect_clients`.
- Contrôle épargne/DAT : `build_savings_accounts_reconciliation`.
- Extrait : `build_mpesa_statement`, `build_customer_summary`, `build_diagnostics`.
- G2/DAT : `build_g2_dat_crosscheck`, `build_g2_entry_report`, `build_g2_daily_savings_report`, `build_g2_transaction_time_analysis`, `build_g2_retention_report`.
- Pilotage : `build_turbo_operation_events`, `build_mpesa_turbo_financial_analysis`, `build_mpesa_management_dashboard`, `build_mpesa_savings_cockpit`, `build_mpesa_credit_cockpit`, `build_mpesa_credit_risk_analysis`, `build_loan_savings_reconciliation`, `build_mpesa_dat_maturity_analysis`.
- Comptabilité : `build_mpesa_accounting_analysis`.
- Perfect : `build_perfect_client_crosscheck`.
- Recherche : `search_customers`, `resolve_customer_id`.
- Export : `create_excel_export`, `create_g2_dat_word`.

## Conditions d'interprétation

- Sans solde d'ouverture, le mouvement cumulé M-PESA n'est pas un solde réel.
- L'Extrait client affiche le solde d'ouverture et la clôture dans `Synthèse financière par devise` lorsqu'ils peuvent être observés depuis Turbo, Savings Account ou saisis dans l'onglet client. Le `Solde` du bloc `Détail des transactions` reprend `Ouverture`, puis suit les opérations affichées jusqu'à `Cloture`.
- Une absence de correspondance est un résultat de contrôle, pas une ligne à supprimer.
- Le tableau `Anomalies Transactions [Turbo]` conserve la ligne Turbo source et ajoute `raison_anomalie`. Détailler les contrôles transactionnels en alerte pour `customer_id` ou `reference_id` manquant, date invalide, `dr = cr = 0`, `dr > 0` et `cr > 0`, solde négatif, devise ou type de compte manquant/inconnu, doublon exact et groupe répété. Appliquer les filtres `statut` et `controle` à la synthèse comme à la liste. La valeur d'un contrôle correspond au nombre de lignes Turbo détaillables; pour les répétitions, le nombre de groupes figure dans `detail`. Avec un filtre `controle`, `raison_anomalie` ne contient que les motifs sélectionnés; sans ce filtre, elle concatène les motifs d'une même ligne.
- Un fichier facultatif absent doit réduire le rapport proprement sans bloquer les analyses encore possibles.
- Toute synthèse financière doit afficher la devise et éviter un total multidevise.
- Le Word reste la restitution modifiable destinée à la Direction générale. L'Extrait client propose aussi un PDF natif CDF, USD ou ALL reprenant le même périmètre filtré, les mêmes comptes et la séparation stricte des devises. Les deux formats intègrent le logo officiel Bisou Bisou.
- Le Word et le PDF de l'Extrait client utilisent l'A4 portrait. Conserver un seul tableau DAT, un seul tableau `Crédit en cours` et un seul tableau de remboursements avec les colonnes compactes contractuelles; compacter le détail transactionnel et autoriser le renvoi à la ligne de la description. Dans G2/DAT, toutes les sections Word et PDF, y compris l'annexe `Transactions`, ainsi que la mise en page d'impression des feuilles Excel, utilisent également le portrait.
- Le Word et le PDF distinguent les mouvements du compte ouvert, l'ouverture/clôture et la situation de l'épargne dans les colonnes du tableau unique `Synthèse financière par devise`, puis présentent les remboursements observés dans leur bloc dédié pour le format global. Ils ne présentent aucun solde du portefeuille M-PESA comme bloc séparé et ne compensent jamais épargne, DAT et crédit.
- Le format minimal de l'Extrait client garde seulement l'en-tête, les critères, `Synthèse financière par devise` avec ouverture/clôture, puis `Détail des transactions`. Les blocs `Éléments couverts par l'extrait client`, `DAT en cours`, `Crédit en cours`, `Remboursements observés`, retours DAT et intérêts DAT crédités restent réservés au format global.
- Les exports du relevé existent en Word et PDF, en format global et minimal. Le détail reste centré sur le compte ouvert : il ne doit pas afficher le prêt net ni le dépôt DAT comme lignes de compte ouvert. Le scénario Benjamin `243000000000` attend 0,00 USD en compte ouvert et 10,00 USD en compte bloqué, et non un solde de 10,35 USD, car les 0,35 USD sont des frais/intérêts de crédit.
- Tout bloc `DAT en cours` présenté dans un export de l'Extrait client doit inclure `Jours restants`, quel que soit le format global ou la feuille Excel `DAT_En_Cours`.
- Tous les tableaux de l'Extrait client doivent rester uniformes visuellement. `Synthèse financière par devise` suit le même style de tableau que les autres blocs du même format : grille, en-tête, police, taille, espacements et alignements cohérents; aucun tableau ne doit avoir une apparence isolée sans raison métier.
- Le Word et le PDF de l'Extrait client ajoutent avant le détail transactionnel la synthèse des sept familles attendues, `DAT en cours`, `Crédit en cours`, `Remboursements observés`, `Retours du capital mis en DAT` et les `Entrées des intérêts du capital mis en DAT` réellement constatées. Le bloc `Crédit en cours` vient de `Loans Account` et expose une situation de stock séparée des transactions du compte ouvert : crédit, octroi, échéance, devise, montant accordé, montant payé, encours, montant à rembourser et situation. Le tableau des retours présente `Création du DAT` et `Fin du DAT` avec la date et l'heure. Le taux DAT apparaît dans les critères. L'Excel client utilise `DAT_En_Cours`, `Credit_En_Cours`, `Remboursements_Turbo`, `Elements_Extrait_Turbo` et `Interets_DAT_Credites`; il n'exporte plus l'ancienne feuille `Interets_DAT_Echus` ni l'ancien détail technique `Credit_Client_Turbo`.
- L'Excel écrit uniquement les feuilles explicitement demandées par l'appelant afin de réduire le temps et la taille de génération.
