# Architecture globale

La documentation couvre trois chaînes de valeur complémentaires.

```mermaid
flowchart LR
    subgraph PV["Perfect Vision"]
        PVDB["BB_VISION_PRO<br/>base métier historique"]
        PVCLIENTS["Clients Perfect Vision<br/>téléphone client"]
        SQL["Catalogue SQL<br/>requetes.sql"]
    end

    subgraph BRIDGE["Pont de rapprochement client"]
        PHONE["Clé commune<br/>numéro de téléphone normalisé"]
        VIEW360["Vue client 360<br/>Perfect Vision x Solution Numérique"]
    end

    subgraph SN["Solution Numérique"]
        T["Transactions<br/>msisdn1 / customer_id"]
        S["Savings Account<br/>msisdn1"]
        L["Loans Account<br/>msisdn1"]
        C["Customers<br/>msisdn1"]
        G2["G2 M-Pesa<br/>nom client et contrôle"]
        SNCORE["Moteur analytique numérique<br/>transactions, épargne, DAT, crédits"]
    end

    RPT["BB_VISION_REPORTING<br/>couche décisionnelle"]
    PBI["Perfect Power BI<br/>PBIP / TMDL / DAX"]

    PVDB --> PVCLIENTS
    PVDB --> SQL
    SQL --> RPT

    T --> SNCORE
    S --> SNCORE
    L --> SNCORE
    C --> SNCORE
    G2 -. enrichit le nom et contrôle .-> SNCORE

    PVCLIENTS --> PHONE
    SNCORE --> PHONE
    PHONE --> VIEW360
    VIEW360 -. indicateurs client croisés .-> RPT
    RPT --> PBI
```

L'objectif cible est de relier progressivement Perfect Vision et la Solution Numérique par le **numéro de téléphone normalisé**. Cette clé permet de rapprocher un client Perfect Vision avec ses activités numériques : transactions, compte ouvert, DAT, crédit digital, activité G2 de contrôle et indicateurs statistiques.

Le rapprochement par téléphone ne transforme pas G2 en source financière. G2 reste une preuve de contrôle et d'identité ; les montants de la Solution Numérique restent calculés depuis les fichiers numériques principaux.

## Responsabilités

| Sujet | Perfect Vision | Perfect Power BI | Solution Numérique |
|---|---|---|---|
| Données métier microfinance | Source opérationnelle historique | Consommées via reporting | Hors périmètre principal |
| Reporting décisionnel | Fournit les règles et données | Produit les KPI et visuels | Peut fournir une lecture digitale séparée |
| Transactions numériques | Peut servir au rapprochement selon disponibilité | Non source principale | Source principale via Transactions |
| G2 M-Pesa | Contrôle éventuel | Généralement non pilotant | Contrôle secondaire et enrichissement d'identité |
| Pont client | Fournit l'identité client et le téléphone de référence | Peut exploiter la vue client croisée | Utilise `msisdn1` / téléphone normalisé pour relier l'activité numérique au client Perfect Vision |
| Devises | Séparées | Séparées | Séparées |

## Règle de non-confusion

Un même libellé de KPI ne signifie pas forcément le même calcul. Par exemple, un indicateur de crédit peut exister dans Perfect Vision, dans Power BI et dans la Solution Numérique, mais la source, le grain et les champs disponibles peuvent différer.
