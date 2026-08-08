# Matrice des systèmes

| Sujet | Perfect Vision | Perfect Power BI | Solution Numérique |
|---|---|---|---|
| Source principale | `BB_VISION_PRO` | `BB_VISION_REPORTING` | Exports Solution Numérique |
| Crédit | Tables crédit, échéances, remboursements | Faits crédit et mesures DAX | `Loans Account` + transactions observées |
| Épargne | Produits et comptes Perfect Vision | `F_Epargne_Soldes` | `Savings Account` |
| Clients | `ADHERENTS`, vues clients | `F_Clients`, dimensions | `Customers`, transactions, G2 facultatif |
| Comptabilité | `HDPM`, `HDPM_API` | Agrégations reporting | Balance observée depuis transactions |
| M-Pesa / G2 | Rapprochement possible selon données | Hors source principale | Contrôle et enrichissement |
| Devise | CDF/USD séparées | CDF/USD séparées | CDF/USD séparées |
| Usage | Contrôle métier | Décisionnel | Pilotage numérique et rapprochements |
