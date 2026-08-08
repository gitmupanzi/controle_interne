# Modèle sémantique et pages Power BI

## Tables TMDL observées

| Table | Type | Rôle |
|---|---|---|
| `D_Date` | Dimension | Analyse temporelle |
| `D_Devise` | Dimension | Séparation CDF/USD |
| `D_Agence` | Dimension | Lecture par agence |
| `F_Clients` | Fait | Indicateurs clients |
| `F_Epargne_Soldes` | Fait | Soldes d'épargne |
| `F_Conformite` | Fait | Contrôles conformité |
| `F_Credit_Portefeuille` | Fait | Encours crédit |
| `F_Credit_PAR_Detail` | Fait | Risque et PAR |
| `F_Credit_Decaissements` | Fait | Flux de crédit |
| `_Mesures` | Mesures | 118 mesures DAX observées |

## Pages observées dans le PBIP

| Page | Audience principale | Lecture attendue |
|---|---|---|
| Paramétrage | Data / BI | Paramètres et filtres globaux |
| Direction | Direction | Synthèse exécutive |
| Clients | Métiers / Direction | Base clients et tendances |
| Crédit | Crédit / Risque | Portefeuille et production |
| Risque crédit | Risque / Contrôle interne | PAR, provisions et alertes |
| Prévisions crédit | Direction / Crédit | Tendances et projections |
| Épargne | Opérations | Mobilisation et soldes |
| Conformité | Conformité / Contrôle interne | Alertes et qualité |
| Surveillance | Contrôle interne | Points d'attention transversaux |

## Devises

Les mesures de montants sont séparées par devise. Les mesures observées incluent notamment `Encours CDF`, `Encours USD`, `PAR 30 CDF`, `PAR 30 USD`, `Provision CDF`.
