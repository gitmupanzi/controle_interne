---
name: solution-mpesa
description: Importer, normaliser, contrôler et rapprocher les fichiers Excel de la Solution M-PESA avec l'épargne courante, les DAT, les crédits, les transactions G2 et les clients; construire des extraits clients, soldes, rapports journaliers et diagnostics sans mélanger les devises. Utiliser pour toute question ou modification liée à M-PESA, Bisou Bisou Digital, G2, Receipt No., DAT, épargne, rapprochements clients ou rapports M-PESA du projet Streamlit.
---

# Solution M-PESA

Réutiliser les contrats de données et fonctions métier existants. Préserver la traçabilité de chaque source et séparer strictement CDF et USD.

## Procédure de travail

1. Identifier les fichiers disponibles et le livrable demandé.
2. Lire [references/data-contracts.md](references/data-contracts.md) pour les colonnes, clés et règles de rapprochement.
3. Vérifier les contrats courants avec `scripts/inspect_mpesa_contracts.py` avant de modifier un import.
4. Normaliser avec les fonctions `prepare_*` de `credit_app/services/mpesa_analysis.py`; ne pas dupliquer cette logique dans l'interface.
5. Valider les colonnes obligatoires et afficher les colonnes manquantes et disponibles.
6. Effectuer les rapprochements par clés documentées, en conservant indicateurs de correspondance et motifs d'écart.
7. Calculer chaque solde et agrégat par devise. Ne jamais sommer CDF et USD.
8. Tester les cas nominal, source facultative absente, doublon, référence non trouvée et solde d'ouverture manquant.

## Règles métier essentielles

- Considérer Transactions M-PESA comme la source minimale pour un extrait client.
- Traiter épargne courante, DAT, crédits, G2 et clients comme sources complémentaires selon le rapport.
- Rapprocher `Receipt No.` de G2 avec `ref_no` M-PESA en priorité lorsque le rapport le prévoit.
- Utiliser `customer_id` comme identifiant canonique après résolution; utiliser MSISDN ou référence seulement selon les règles existantes.
- Présenter un cumul relatif, et non un solde réel, si le solde d'ouverture M-PESA n'est pas fourni.
- Conserver les lignes non rapprochées dans les diagnostics; ne pas les supprimer silencieusement.
- Ne pas modifier les fichiers Excel sources pendant l'analyse.

## Architecture à respecter

- Contrats : `credit_app/data_schema.py`
- Calculs et rapprochements : `credit_app/services/mpesa_analysis.py`
- Interface : `credit_app/tabs/solution_mpesa.py`
- Tests : `tests/test_mpesa_analysis.py`

Placer les règles déterministes dans le service, le rendu dans l'onglet Streamlit et les nouveaux cas métier dans les tests.

## Validation

Exécuter au minimum :

```powershell
python skills/solution-mpesa/scripts/inspect_mpesa_contracts.py
python -m pytest tests/test_mpesa_analysis.py -q
```

Pour une nouvelle extraction, documenter les sources, clés, granularité, devise, période, écarts non rapprochés et hypothèses de solde.
