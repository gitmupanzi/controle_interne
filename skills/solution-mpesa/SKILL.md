---
name: solution-mpesa
description: Importer, normaliser, contrôler et rapprocher les fichiers Excel M-PESA de G2, Turbo et Perfect; construire les sous-onglets G2/DAT, Extrait client, Crédits et Perfect_client, enrichir les noms clients, segmenter Perfect dans G2, Turbo et leur intersection, classifier les entrées et sorties, détecter les anomalies et produire les exports Excel ciblés et Word sans mélanger les devises. Utiliser pour toute question ou modification liée à Solution M-PESA, Bisou Bisou Digital, Portal/Turbo, G2, Perfect, Phone_Prefixe, Receipt No/ref_no, DAT, épargne, crédit, fidélisation, rapprochement client ou rapport M-PESA du projet Streamlit.
---

# Solution M-PESA

Réutiliser les contrats et fonctions métier existants. Préserver la traçabilité des sources, le grain des opérations et la séparation stricte des devises.

## Procédure de travail

1. Identifier les fichiers disponibles, la période, le sens des flux et le livrable demandé.
2. Lire [references/data-contracts.md](references/data-contracts.md) pour sélectionner les colonnes, clés, classifications et règles de dégradation.
3. Exécuter `scripts/inspect_mpesa_contracts.py` avant de modifier un import ou un alias.
4. Normaliser avec les fonctions `prepare_*` de `credit_app/services/mpesa_analysis.py`; ne pas reproduire cette logique dans Streamlit.
5. Valider les colonnes obligatoires et afficher les colonnes manquantes ainsi que les colonnes réellement disponibles.
6. Construire les rapprochements et classifications dans le service, puis limiter l'interface au filtrage et au rendu.
7. Conserver les indicateurs de correspondance, motifs d'écart, lignes non rapprochées et sources facultatives absentes.
8. Calculer chaque solde, total et taux par devise. Ne jamais sommer CDF et USD.
9. Tester les cas nominal, source absente, format G2 alternatif, doublon, référence inconnue, contrôle en écart et solde d'ouverture manquant.

## Invariants G2/DAT

- Conserver une ligne analytique canonique par `Receipt No.`; signaler tout reçu dupliqué et ne pas le compter deux fois.
- Rapprocher d'abord `Receipt No.` avec `ref_no` du Portal/Turbo. Agréger les écritures techniques du même `ref_no` sans additionner les miroirs comptables comme plusieurs opérations G2.
- Classifier les entrées rapprochées avec `account_type` et `description` du Portal : `FIXED SAVINGS`/`Depot Bloque` = `DAT`, `NORMAL SAVINGS`/`Epargne depot` = `Depot normal`, compte prêt/principal/portefeuille = `Remboursement prets`.
- Utiliser les règles G2 comme repli lorsque le Portal ne contient pas la référence; classifier les sorties B2C, demandes de crédit et opérations internes selon `Details`, `Reason Type`, `Paid In` et `Withdrawn`.
- Contrôler séparément téléphone, devise, montant et date. Distinguer `Rapproche exact`, `Rapproche avec ecart` et `Non rapproche`.
- Retenir uniquement les statuts G2 terminés dans les synthèses financières, tout en conservant les autres lignes dans le détail et les anomalies.
- Utiliser `G2_CLASSIFIED_TRANSACTION_COLUMNS` comme ordre commun du tableau `Transactions` à l'écran et dans le Word : `date`, `receipt_no`, `currency_code`, `details_rapport`, `opposite_party`, `duree`, `compte_cree`, `montant`, `montant_entree`, `montant_sortie`, `balance_numeric`.
- Appliquer les bornes inclusives de date et d'heure de `Completion Time`, puis le filtre de sens, avant les synthèses, contrôles et exports; une sélection vide du multisélecteur de sens signifie tous les flux.

## Règles client et sources facultatives

- Considérer Transactions M-PESA Turbo comme la source minimale de l'extrait client.
- Enrichir Turbo avec le nom G2 par téléphone normalisé et, quand disponible, par `Receipt No = ref_no`.
- Résoudre vers `customer_id` après rapprochement; utiliser MSISDN ou référence uniquement selon les règles documentées.
- Rechercher `compte_cree` dans Clients Turbo, puis l'épargne courante, puis le DAT.
- Agréger Perfect par `Phone_Prefixe` avant la jointure et conserver le nombre d'identités associées au numéro.
- Construire l'intersection G2–Turbo–Perfect au grain d'un téléphone normalisé, avec `present_dans_turbo`, `present_dans_g2`, `present_dans_perfect`, `present_dans_les_3_systemes` et le dataset `clients_trois_systemes`.
- Produire trois populations inclusives : `clients_perfect_dans_mpesa` pour Perfect∩G2, `clients_perfect_dans_turbo` pour Perfect∩Turbo et `clients_perfect_dans_turbo_et_mpesa` pour Perfect∩Turbo∩G2.
- Réduire proprement le rapport lorsqu'une source facultative manque; ne jamais provoquer un `KeyError` en indexant une source absente.
- Présenter un cumul relatif, et non un solde réel, si le solde d'ouverture M-PESA n'est pas fourni.
- Ne jamais modifier les fichiers Excel sources pendant l'analyse.

## Exports

- Générer uniquement les feuilles Excel demandées par le contexte; ne jamais ajouter automatiquement toutes les feuilles vides du module.
- Pour G2/DAT, conserver la synthèse, les comptages, le détail, `Anomalies_G2`, `G2_DAT`, `Retention_Mensuelle` et `Retention_Detail`.
- Garder le Word modifiable et ajouter en annexe le tableau unique `Transactions`, dans le même ordre que l'écran et en orientation paysage.
- Transmettre `rapport_journalier_pivot` au Word même lorsqu'il est exclu de l'Excel compact; reconstruire la synthèse par devise depuis le détail si le pivot manque.
- Répéter les en-têtes Word sur plusieurs pages et conserver toutes les lignes du périmètre filtré.
- Vérifier qu'un export client reprend les filtres de l'extrait sans perdre les feuilles contextuelles du client.
- Exporter les trois populations Perfect dans `Perfect_M_PESA`, `Perfect_Turbo` et `Perfect_Turbo_M_PESA`.

## Architecture à respecter

- Contrats : `credit_app/data_schema.py`
- Calculs, rapprochements et exports : `credit_app/services/mpesa_analysis.py`
- Interface : `credit_app/tabs/solution_mpesa.py`
- Tests : `tests/test_mpesa_analysis.py`

Placer les règles déterministes dans le service, le rendu dans l'onglet Streamlit et chaque nouveau cas métier dans les tests.

## Validation

Exécuter au minimum avec l'environnement Python du projet :

```powershell
& $PYTHON skills/solution-mpesa/scripts/inspect_mpesa_contracts.py
& $PYTHON -m pytest tests/test_mpesa_analysis.py -q
```

Pour un changement G2/DAT ou Word, tester aussi un fichier réel sans l'écrire dans le dépôt et vérifier le nombre de reçus, l'ordre des colonnes, les devises, les totaux et les anomalies. Vérifier également que chaque Excel contient seulement les feuilles prévues. Pour `Perfect_client`, vérifier les trois populations inclusives et leurs trois feuilles Excel avec un export 122 réel.
