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
| Clients Turbo | `msisdn1`, `created_at` | Date de création du compte et recherche client |
| Clients Perfect | `Phone_Prefixe` | Identité Perfect et contrôle de présence des clients M-PESA |

Les colonnes facultatives et alias acceptés sont définis dans `credit_app/data_schema.py`.

## Formats G2 acceptés

Accepter les deux structures suivantes sans modifier le fichier source :

1. Format avec `Transaction Amount`, éventuellement accompagné de `Details`, `Reason Type`, `Transaction Status`, `Completion Time` et `Balance`.
2. Format relevé organisation avec montant éclaté dans `Paid In` et `Withdrawn`, solde dans `Balance` et nature dans `Details`.

Règles de montant et de sens :

- utiliser `Paid In` comme montant d'entrée lorsqu'il est non nul;
- utiliser `Withdrawn` comme montant de sortie lorsqu'il est non nul;
- utiliser le signe de `Transaction Amount` comme repli si les colonnes éclatées sont absentes;
- conserver `balance_numeric` comme solde du relevé G2, sans le confondre avec un mouvement;
- convertir les dates et montants avec erreurs contrôlées et conserver la colonne source utilisée.

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
4. Contrôler ensuite :
   - téléphone G2 extrait de `Opposite Party` contre `msisdn1`;
   - devise G2 contre les devises du groupe Portal;
   - montant absolu G2 contre le mouvement du compte M-PESA Portal;
   - date G2 contre la journée de l'écriture Portal.
5. Produire `Rapproche exact`, `Rapproche avec ecart` ou `Non rapproche`.

Ne pas considérer le nombre d'écritures Portal comme le nombre d'opérations clients. Une opération peut produire plusieurs lignes `MPESA ACCOUNT`, `NORMAL SAVINGS`, `FIXED SAVINGS` ou comptes de prêt.

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

Ne jamais utiliser une sortie comme candidate DAT. Conserver `Autre entree`, `Autre sortie` ou `Flux a verifier` lorsque la nature reste indéterminée.

## Inclusion et anomalies

- Inclure dans les synthèses les statuts vides ou terminés reconnus (`Completed`, `Successful` et variantes normalisées).
- Exclure des synthèses les statuts explicitement non terminés, mais les conserver dans le détail.
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

La population de départ contient les téléphones observés dans au moins une source M-PESA. Perfect enrichit cette population mais ne crée pas, à lui seul, une ligne dans la synthèse.

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
- utiliser `clients_trois_systemes` pour la vue prioritaire et la feuille Excel `Clients_3_Systemes`;
- conserver la population générale dans `Perfect_Clients` et les opérations G2/Turbo dans `Perfect_Operations`;
- ne pas attribuer d'opérations financières à Perfect, car l'export 122 décrit les clients et la qualité de leurs téléphones.

Populations attendues :

| Dataset | Condition | Feuille Excel |
|---|---|---|
| `clients_perfect_dans_mpesa` | `present_dans_g2` et `present_dans_perfect` | `Perfect_M_PESA` |
| `clients_perfect_dans_turbo` | `present_dans_turbo` et `present_dans_perfect` | `Perfect_Turbo` |
| `clients_perfect_dans_turbo_et_mpesa` | `present_dans_turbo`, `present_dans_g2` et `present_dans_perfect` | `Perfect_Turbo_M_PESA` |

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
- Calculer la fidélisation par téléphone, mois de base et devise.
- Laisser les taux M+1 ou 90 jours vides tant que la fenêtre complète n'est pas observable.
- Exclure de la fidélisation les opérations internes, téléphones invalides et statuts en échec/annulés/inversés.

## Fonctions à privilégier

- Préparation : `prepare_transactions`, `prepare_current_savings`, `prepare_fixed_savings`, `prepare_loans`, `prepare_g2_transactions`, `prepare_customers`, `prepare_perfect_clients`.
- Extrait : `build_mpesa_statement`, `build_customer_summary`, `build_diagnostics`.
- G2/DAT : `build_g2_dat_crosscheck`, `build_g2_entry_report`, `build_g2_daily_savings_report`, `build_g2_retention_report`.
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
