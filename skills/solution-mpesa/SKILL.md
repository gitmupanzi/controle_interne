---
name: solution-mpesa
description: Importer, normaliser, contrôler et rapprocher les fichiers Excel M-PESA de G2, Turbo et Perfect; construire les sous-onglets Pilotage Turbo + G2, G2/DAT, Extrait client, Crédits et Perfect_client, mesurer risque crédit, liquidité, activité client, conversion DAT, concentration, qualité et adoption, détecter les anomalies et produire les exports Excel ciblés et Word sans mélanger les devises. Utiliser pour toute question ou modification liée à Solution M-PESA, Bisou Bisou Digital, Portal/Turbo, G2, Perfect, Phone_Prefixe, Receipt No/ref_no, DAT, épargne, crédit, fidélisation, rapprochement client ou rapport M-PESA du projet Streamlit.
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

Tous les téléversements de Solution M-PESA peuvent recevoir plusieurs fichiers. Conserver leur provenance, supprimer les chevauchements avec la clé métier propre à chaque source et ne jamais additionner plusieurs instantanés du même compte, crédit ou client.

Dans tous les libellés destinés aux utilisateurs, ajouter `[Turbo]`, `[G2]` ou `[Turbo + G2]` selon la source effective. Réserver `Solution M-PESA` au nom global du module; ne jamais utiliser `M-PESA` seul comme source d'un indicateur.

## Invariants G2/DAT

- Autoriser G2/DAT sans fichier G2 lorsque Transactions M-PESA_Turbo est disponible. Dans ce mode, construire une ligne analytique par `ref_no` pour les dépôts/DAT/remboursements et par `reference_id + created_at` pour `Retrait Vers M-Pesa`; utiliser `created_at` comme date d'analyse et tracer `source_analytique = Turbo seul`.
- En mode Turbo seul, ne jamais inventer `Opposite Party`, nom, statut, solde, `Initiation Time` ou `Completion Time` G2. Marquer les contrôles indépendants G2/Turbo et le rapprochement comme `Non applicable - Turbo seul`. Si G2 est chargé, conserver G2 comme source principale et ne pas ajouter les opérations proxy Turbo.
- Conserver une ligne analytique canonique par `Receipt No.`; signaler tout reçu dupliqué et ne pas le compter deux fois.
- Accepter plusieurs relevés G2 simultanément, notamment les fichiers d'entrées et de sorties; conserver le fichier source avant de les unifier.
- Compter les transactions terminees par date, jour de semaine et heure de `Completion Time`, sur des grilles completes de lundi a dimanche et de 00h a 23h; conserver la separation par devise et par sens et afficher les periodes sans activite a zero.
- Rapprocher d'abord `Receipt No.` avec `ref_no` du Portal/Turbo. Agréger les écritures techniques du même `ref_no` sans additionner les miroirs comptables comme plusieurs opérations G2.
- Pour une sortie `BisouBisouB2C` sans `ref_no`, autoriser le repli uniquement vers `Retrait Vers M-Pesa` avec téléphone, devise et montant identiques et un écart maximal de 120 minutes. Identifier l'opération Turbo par `reference_id + created_at`; ne jamais utiliser `reference_id` seul, car il peut désigner un compte réutilisé.
- Classifier les entrées rapprochées avec `account_type` et `description` du Portal : `FIXED SAVINGS`/`Depot Bloque` = `DAT`, `NORMAL SAVINGS`/`Epargne depot` = `Depot normal`, compte prêt/principal/portefeuille = `Remboursement prets`.
- Utiliser les règles G2 comme repli lorsque le Portal ne contient pas la référence; classifier les sorties B2C, demandes de crédit et opérations internes selon `Details`, `Reason Type`, `Paid In` et `Withdrawn`.
- Comparer la création avec `Initiation Time` G2 contre `created_at` Turbo; utiliser `Completion Time` seulement comme repli de création, puis comme date de finalisation et source du délai de traitement. Tolérer un passage de date jusqu'à 120 minutes en conservant les deux dates dans `Observation`; au-delà, signaler un écart de date. Un délai G2 négatif est une anomalie.
- Contrôler séparément téléphone, devise, montant et date. Distinguer `Rapproche exact`, `Rapproche avec ecart`, `Non rapproche` et `Non applicable - operation interne`. Une `Super Transaction` non rapprochée ne constitue pas, à elle seule, une anomalie client.
- Dès qu'un export fournit des statuts, retenir uniquement les statuts G2 explicitement terminés dans les synthèses financières, le rapprochement DAT, Perfect_client et le Word; conserver les autres lignes dans la répartition des statuts, le détail Excel et les anomalies. Un ancien export sans aucun statut reste compatible.
- Utiliser `G2_CLASSIFIED_TRANSACTION_COLUMNS` comme ordre du noyau métier du tableau `Transactions` et du Word : `date`, `receipt_no`, `currency_code`, `details_rapport`, `opposite_party`, `duree`, `compte_cree`, `montant`, `montant_entree`, `montant_sortie`, `balance_numeric`. L'écran peut ajouter le fichier source et le statut comme colonnes de contrôle.
- Appliquer les bornes inclusives de date et d'heure de `Completion Time`, puis le filtre de sens, avant les synthèses, contrôles et exports; une sélection vide du multisélecteur de sens signifie tous les flux.

## Règles client et sources facultatives

- Considérer Transactions M-PESA Turbo comme la source minimale de l'extrait client.
- Enrichir Turbo avec le nom G2 par téléphone normalisé et, quand disponible, par `Receipt No = ref_no`.
- Résoudre vers `customer_id` après rapprochement; utiliser MSISDN ou référence uniquement selon les règles documentées.
- Rechercher `compte_cree` dans `Clients_Turbo`, puis l'épargne courante, puis le DAT.
- Agréger Perfect par `Phone_Prefixe` avant la jointure et conserver le nombre d'identités associées au numéro.
- Construire l'intersection G2–Turbo–Perfect au grain d'un téléphone normalisé, avec `present_dans_turbo`, `present_dans_g2`, `present_dans_perfect`, `present_dans_les_3_systemes` et le dataset `clients_trois_systemes`.
- Dans les libellés utilisateur, distinguer `Clients_Turbo`, `Clients_Perfect` et les clients transactionnels déduits de Turbo/G2; ne jamais appeler ces derniers `Clients_Turbo` sans preuve dans le fichier correspondant.
- Produire trois populations inclusives : `clients_perfect_dans_mpesa` pour Perfect∩G2, `clients_perfect_dans_turbo` pour Perfect∩Turbo et `clients_perfect_dans_turbo_et_mpesa` pour Perfect∩Turbo∩G2.
- Réduire proprement le rapport lorsqu'une source facultative manque; ne jamais provoquer un `KeyError` en indexant une source absente.
- Présenter un cumul relatif, et non un solde réel, si le solde d'ouverture M-PESA n'est pas fourni.
- Ne jamais modifier les fichiers Excel sources pendant l'analyse.

## Invariants Pilotage Turbo + G2

- Pour Transactions Turbo, conserver la sémantique comptable : `dr` = sortie du compte M-PESA et `cr` = entrée. Ne jamais appliquer les règles G2 `Paid In`/`Withdrawn` aux fichiers Turbo.
- Dédupliquer les transactions Turbo par `id`, les crédits par `loan_id`, les clients par identifiant ou téléphone/date, les comptes d'épargne et DAT par leur clé de compte; conserver la version la plus récente et la liste des fichiers sources.
- Utiliser la derniere date operationnelle chargee comme date d'analyse par defaut; ne pas utiliser une echeance future comme date de fraicheur.
- Calculer le PAR 1/7/30 uniquement depuis `due_date` et un encours credit disponible. Laisser le taux vide si un encours actif n'a pas d'echeance.
- Dedupliquer les credits par `loan_id` et les operations G2/Turbo par reference, avec priorite au recu G2 canonique.
- Classer l'activite client au grain telephone x devise : actif 30 jours, dormant 31-60 jours, dormant 61-90 jours ou inactif au-dela de 90 jours.
- Presenter la conversion Depot normal vers DAT comme une conversion observee dans la periode, jamais comme une affectation comptable certaine.
- Traiter les montants eleves, horaires rares et rafales d'operations comme des alertes de revue et non comme des preuves de fraude.
- Produire l'echeancier DAT par tranche et devise. Mesurer l'adoption Perfect uniquement sur les `Phone_Prefixe` valides.

## Exports

- Générer uniquement les feuilles Excel demandées par le contexte; ne jamais ajouter automatiquement toutes les feuilles vides du module.
- Pour G2/DAT, conserver la synthèse, les comptages, le détail, les analyses temporelles et la fidélisation. Nommer les feuilles de contrôle `Statuts_G2`, `Anomalies_G2`, `G2_DAT` en mode G2 et `Statuts_Turbo`, `Anomalies_Turbo`, `Turbo_DAT` en mode Turbo seul.
- Garder le Word modifiable et ajouter en annexe le tableau unique `Transactions`, dans le même ordre que l'écran et en orientation paysage.
- Transmettre `rapport_journalier_pivot` au Word même lorsqu'il est exclu de l'Excel compact; reconstruire la synthèse par devise depuis le détail si le pivot manque.
- Répéter les en-têtes Word sur plusieurs pages et conserver toutes les lignes `Completed` du périmètre filtré; garder les autres statuts dans l'Excel de contrôle.
- Calculer la ligne `Activite` de la synthèse exécutive Word directement depuis le détail `Completed` filtré par date, heure et sens; ne jamais la reprendre du dernier mois de fidélisation.
- Vérifier qu'un export client reprend les filtres de l'extrait sans perdre les feuilles contextuelles du client.
- Exporter les trois populations `Clients_Perfect` dans `Clients_Perfect_G2`, `Clients_Perfect_Turbo` et `Clients_Perfect_Turbo_G2`.
- Dans l'export de pilotage mixte, suffixer aussi chaque feuille par sa source : `_Turbo`, `_G2` ou `_Turbo_G2`.
- Generer l'Excel du cockpit uniquement sur demande et limiter ses feuilles aux syntheses et listes d'action utiles.

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
