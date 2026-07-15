# Contrats de données M-PESA

La source de vérité exécutable reste `credit_app/data_schema.py`. Les règles de calcul et d'export se trouvent dans `credit_app/services/mpesa_analysis.py`.

## Sources

| Source | Colonnes obligatoires principales | Rôle |
|---|---|---|
| Transactions M-PESA Portal/Turbo | `id`, `customer_id`, `msisdn1`, `account_type`, `reference_id`, `currency_code`, `dr`, `cr`, `bal_before`, `bal_after`, `ref_no`, `description`, `created_at` | Mouvements, extrait client, classification et contrôle G2 |
| Épargne courante | `customer_id`, `msisdn`, `product_name`, `account_type`, `balance`, `currency_code`, `created_at`, `updated_at` | Solde d'épargne courant et date de création de repli |
| DAT | `customer_id`, `msisdn`, `product_name`, `account_type`, `balance`, `currency_code`, `date_approved`, `maturity_date`; `created_at` facultatif | Dépôts à terme, durée, création et échéance |
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
| Épargne courante | client × devise × compte × produit × création | `updated_at` le plus récent |
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

Un changement de date civile reste `Conforme - passage de date` si l'écart absolu ne dépasse pas 120 minutes; conserver alors les dates G2/Turbo dans `Observation`. Au-delà, produire `Ecart de date`. Un délai de traitement G2 négatif est toujours une anomalie.

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
- Extraire le téléphone et le nom G2 depuis `Opposite Party`.
- Enrichir les rapports Turbo avec `Nom_client` par téléphone; utiliser la référence G2/Portal lorsqu'elle est disponible et pertinente.
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

## Fonctions à privilégier

- Préparation : `prepare_transactions`, `prepare_current_savings`, `prepare_fixed_savings`, `prepare_loans`, `prepare_g2_transactions`, `prepare_customers`, `prepare_perfect_clients`.
- Extrait : `build_mpesa_statement`, `build_customer_summary`, `build_diagnostics`.
- G2/DAT : `build_g2_dat_crosscheck`, `build_g2_entry_report`, `build_g2_daily_savings_report`, `build_g2_transaction_time_analysis`, `build_g2_retention_report`.
- Pilotage : `build_mpesa_management_dashboard`, `build_mpesa_credit_risk_analysis`, `build_mpesa_liquidity_analysis`, `build_mpesa_client_activity_analysis`, `build_mpesa_savings_conversion_analysis`, `build_mpesa_transaction_concentration_analysis`, `build_mpesa_transaction_quality_analysis`, `build_mpesa_dat_maturity_analysis`, `build_mpesa_perfect_adoption_analysis`.
- Perfect : `build_perfect_client_crosscheck`.
- Recherche : `search_customers`, `resolve_customer_id`.
- Export : `create_excel_export`, `create_g2_dat_word`.

## Conditions d'interprétation

- Sans solde d'ouverture, le mouvement cumulé M-PESA n'est pas un solde réel.
- Une absence de correspondance est un résultat de contrôle, pas une ligne à supprimer.
- Un fichier facultatif absent doit réduire le rapport proprement sans bloquer les analyses encore possibles.
- Toute synthèse financière doit afficher la devise et éviter un total multidevise.
- Le Word est la restitution modifiable destinée à la Direction générale et contient `Transactions`; aucun export PDF n'est généré dans l'interface.
- L'Excel écrit uniquement les feuilles explicitement demandées par l'appelant afin de réduire le temps et la taille de génération.
