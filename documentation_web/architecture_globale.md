# Architecture globale

La documentation couvre trois chaînes de valeur complémentaires.

```mermaid
flowchart LR
    PV[Perfect Vision<br/>BB_VISION_PRO]
    SQL[Catalogue SQL<br/>requetes.sql]
    RPT[BB_VISION_REPORTING]
    PBI[Perfect Power BI<br/>PBIP / TMDL / DAX]

    SN[Solution Numérique]
    T[Transactions]
    S[Savings Account]
    L[Loans Account]
    C[Customers]
    G2[G2 M-Pesa<br/>1441 / 15558]
    CP[Clients Perfect<br/>facultatif]

    PV --> SQL
    PV --> RPT
    SQL --> RPT
    RPT --> PBI

    T --> SN
    S --> SN
    L --> SN
    C --> SN
    G2 -. contrôle et identité .-> SN
    CP -. enrichissement analytique .-> SN
```

## Responsabilités

| Sujet | Perfect Vision | Perfect Power BI | Solution Numérique |
|---|---|---|---|
| Données métier microfinance | Source opérationnelle historique | Consommées via reporting | Hors périmètre principal |
| Reporting décisionnel | Fournit les règles et données | Produit les KPI et visuels | Peut fournir une lecture digitale séparée |
| Transactions numériques | Peut servir au rapprochement selon disponibilité | Non source principale | Source principale via Transactions |
| G2 M-Pesa | Contrôle éventuel | Généralement non pilotant | Contrôle secondaire et enrichissement d'identité |
| Devises | Séparées | Séparées | Séparées |

## Règle de non-confusion

Un même libellé de KPI ne signifie pas forcément le même calcul. Par exemple, un indicateur de crédit peut exister dans Perfect Vision, dans Power BI et dans la Solution Numérique, mais la source, le grain et les champs disponibles peuvent différer.
