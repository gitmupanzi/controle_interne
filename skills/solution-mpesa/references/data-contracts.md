# Contrats de données M-PESA

La source de vérité exécutable reste `credit_app/data_schema.py`. Les règles de calcul et d'export se trouvent dans `credit_app/services/mpesa_analysis.py`.

## Sommaire

- [Sources](#sources)
- [Chargement de plusieurs fichiers](#chargement-de-plusieurs-fichiers)
- [Formats G2 acceptés](#formats-g2-acceptés)
- [Source maître Savings Account et contrôle DAT](#source-maître-savings-account-et-contrôle-dat)
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

## Interface refactorisée des téléversements

L'interface Streamlit utilise désormais ce parcours :

| Niveau | Téléversement | Rôle |
|---|---|---|
| Turbo principal | `Transactions` | Journal des écritures et mouvements |
| Turbo principal | `Savings Account` | Source maître de l'épargne courante et des DAT |
| Turbo principal | `Loans Account` | Crédits, encours, échéances et remboursements |
| Turbo principal | `Customers` | Téléphone et date de création client |
| Facultatif | `Transactions G2` multiple | Entrées 1441, sorties 15558, noms et contrôle indépendant |
| Facultatif | `Clients_Perfect` | Contrôle et adoption intersystèmes |

`Customers with Current Savings Account` et `Customers with Fixed Savings Account` n'ont pas de widgets séparés. Ils peuvent être sélectionnés ensemble dans l'emplacement multiple `Savings Account` lorsque la source complète n'est pas disponible. L'interface doit alors avertir que seuls les soldes positifs sont couverts. Si le fichier complet est aussi présent, il est seul retenu. Les quatre emplacements Turbo principaux doivent produire les mêmes comptes, soldes, devises, statuts et dates que la source maître validée lorsque celle-ci est fournie.

Règles de montant et de sens :

- utiliser `Paid In` comme montant d'entrée lorsqu'il est non nul;
- utiliser `Withdrawn` comme montant de sortie lorsqu'il est non nul;
- utiliser le signe de `Transaction Amount` comme repli si les colonnes éclatées sont absentes;
- conserver `balance_numeric` comme solde du relevé G2, sans le confondre avec un mouvement;
- convertir les dates et montants avec erreurs contrôlées et conserver la colonne source utilisée.

Pour Transactions Turbo, ne pas appliquer ces règles G2. Utiliser `dr` comme sortie du compte `MPESA ACCOUNT` et `cr` comme entrée, puis regrouper les écritures techniques par `ref_no` pour le rapprochement.

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
- Affecter `compte = 1441` aux entrées et `compte = 15558` aux sorties. Conserver `devise` dans chaque ligne de l'extrait.
- Autoriser `currency = ALL` dans le Word. Dans ce mode, garder une seule annexe transactionnelle mais produire une ligne de synthèse distincte pour CDF et USD; laisser les totaux globaux multidevises vides.
- Les critères Word affichent `Devise : CDF`, `Devise : USD` ou `Devise : ALL (CDF, USD)` et n'affichent plus `Compte :`.
- Le périmètre par défaut comprend `Sortie M-PESA_Turbo vers epargne`, `Sortie M-PESA_Turbo vers DAT`, `Entree M-PESA_Turbo depuis epargne` pour les retraits client, `Decaissement de credit`, `Remboursement de credit` et `Remboursement avec penalite`. Pour `Retrait Vers M-Pesa` sans `ref_no`, une transaction unique est définie par `customer_id + currency_code + created_at + reference_id`; les lignes `MPESA ACCOUNT` et `NORMAL SAVINGS` sont deux faces de cette même transaction.
- Le nom du Word Turbo seul suit `extrait_compte_<customer_id>_<telephone>_<devise>_<debut>_<fin>.docx`. Avec G2 chargé, insérer `Nom_client` entre `customer_id` et le téléphone. Le contenu du Word officiel ne porte pas de suffixe `[Turbo]` et n'imprime pas l'ancien avertissement de solde d'ouverture; `Cumul net` continue d'indiquer qu'aucun solde réel n'a été fourni.
- Le Word client exclut `Synthese du comportement observe`, `Positions observees et rapprochement des soldes` et `Jalons du parcours financier`. Il conserve `Detail des transactions` et utilise `Solution Bisou Bisou Digital` dans son pied de page.
- Le titre Word inclut le nom seulement lorsqu'il est réellement disponible. Sans nom, il suit `Extrait de compte - <telephone> - <devise>` et n'affiche ni `NON DISPONIBLE` ni un séparateur vide.
- Dans l'Extrait client, filtrer `g2_dat` sur le `customer_id` sélectionné avant affichage et export, même sans fichier DAT.
- Construire `dat_en_cours_client` depuis les `FIXED SAVINGS` à solde positif du client dans `Savings Account`. Cette position est filtrée par client et devise, mais pas par la période ni la référence des transactions.
- Fixer `date_situation` depuis `updated_at` ou `date_locked`, à défaut depuis la dernière transaction Turbo du client, puis depuis `created_at` ou `date_approved`. Ne jamais utiliser G2 pour dater ou valoriser un DAT.
- Estimer l'intérêt par `balance × taux / 100 × durée_contractuelle_jours / 365`, avec 11 % par défaut. Restituer `savings_id`, produit, approbation, échéance, jours restants, devise, capital, taux, intérêt estimé, capital avec intérêt estimé et situation client. L'estimation n'est pas une écriture comptable.
- Construire la synthèse et le détail des remboursements depuis les seuls événements Turbo `Remboursement de credit` et `Remboursement avec penalite`. Restituer date, référence, devise, montant payé, principal, intérêts, pénalités et mode observé. Exclure les décaissements, la dette créée et les positions de crédit de l'Extrait client.
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

Trier par `currency_code` croissant, puis `date` décroissante. Le Word doit reprendre un seul tableau en orientation paysage, avec les mêmes colonnes et le même ordre que l'écran.

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

L'interface réunit le pilotage financier et la comptabilité observée dans un seul sous-onglet principal `Finance Turbo`. Une période et une sélection de devises alimentent les six volets `Vue direction`, `Flux et activité`, `Crédit, épargne et DAT`, `Balances et journaux`, `Risques et contrôles` et `Export`. Les deux rapports sont construits avant le rendu des volets et mis en cache; les exports de pilotage et de comptabilité conservent des contrats séparés.

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

## Fonctions à privilégier

- Préparation : `prepare_transactions`, `prepare_savings_accounts`, `prepare_current_savings`, `prepare_fixed_savings_from_accounts`, `prepare_fixed_savings`, `prepare_loans`, `prepare_g2_transactions`, `prepare_customers`, `prepare_perfect_clients`.
- Contrôle épargne/DAT : `build_savings_accounts_reconciliation`.
- Extrait : `build_mpesa_statement`, `build_customer_summary`, `build_diagnostics`.
- G2/DAT : `build_g2_dat_crosscheck`, `build_g2_entry_report`, `build_g2_daily_savings_report`, `build_g2_transaction_time_analysis`, `build_g2_retention_report`.
- Pilotage : `build_turbo_operation_events`, `build_mpesa_turbo_financial_analysis`, `build_mpesa_management_dashboard`, `build_mpesa_credit_risk_analysis`, `build_loan_savings_reconciliation`, `build_mpesa_dat_maturity_analysis`.
- Comptabilité : `build_mpesa_accounting_analysis`.
- Perfect : `build_perfect_client_crosscheck`.
- Recherche : `search_customers`, `resolve_customer_id`.
- Export : `create_excel_export`, `create_g2_dat_word`.

## Conditions d'interprétation

- Sans solde d'ouverture, le mouvement cumulé M-PESA n'est pas un solde réel.
- Une absence de correspondance est un résultat de contrôle, pas une ligne à supprimer.
- Un fichier facultatif absent doit réduire le rapport proprement sans bloquer les analyses encore possibles.
- Toute synthèse financière doit afficher la devise et éviter un total multidevise.
- Le Word reste la restitution modifiable destinée à la Direction générale. L'Extrait client propose aussi un PDF natif CDF, USD ou ALL reprenant le même périmètre filtré, les mêmes comptes et la séparation stricte des devises. Les deux formats intègrent le logo officiel Bisou Bisou.
- Le Word et le PDF de l'Extrait client ajoutent avant le détail transactionnel `DAT en cours` et `Remboursements observés`. L'Excel client utilise `DAT_En_Cours` et `Remboursements_Turbo` et n'exporte plus les feuilles d'intérêts DAT échus ou de crédit.
- L'Excel écrit uniquement les feuilles explicitement demandées par l'appelant afin de réduire le temps et la taille de génération.
