# KPI, DAX et validation

## Documentation centralisée

Les anciennes notes Power BI ont été centralisées dans cette documentation web :

- [Catalogue KPI](catalogue_kpi.md)
- [Résultats de validation](resultats_validation.md)
- [Data gaps](data_gaps.md)
- [État de migration](etat_migration.md)
- [Prochaines étapes](prochaines_etapes.md)

## Exemples de familles de mesures

| Famille | Exemples |
|---|---|
| Crédit | prêts actifs, encours, décaissements, top encours |
| Risque | PAR 30, PAR 60, PAR 90, provisions |
| Épargne | soldes, mobilisation, comptes |
| Clients | clients actifs, nouveaux clients, rétention |
| Conformité | alertes, dossiers incomplets, contrôles |

## Validation

Chaque KPI publié doit préciser :

- mesure DAX ;
- table TMDL ;
- table ou vue reporting ;
- requête SQL ou règle métier d'origine ;
- devise ;
- période ;
- résultat de rapprochement avec SQL.

!!! warning "Attention"
    Un KPI affiché dans Power BI ne doit pas être considéré comme certifié tant que son rapprochement avec la source SQL n'est pas documenté.
