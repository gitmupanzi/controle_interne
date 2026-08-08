# Perfect Power BI

Perfect Power BI est la couche décisionnelle destinée au reporting, aux KPI et aux tableaux de bord.

Elle dépend fonctionnellement de Perfect Vision :

```mermaid
flowchart LR
    PV[Perfect Vision<br/>BB_VISION_PRO]
    RPT[BB_VISION_REPORTING]
    PBI[Power BI<br/>PBIP / TMDL / DAX]
    PV --> RPT --> PBI
```

## Sources documentaires

- `skills/perfect-power-bi/SKILL.md`
- `skills/perfect-power-bi/references/architecture-and-connectivity.md`
- `skills/perfect-power-bi/references/semantic-model-and-pages.md`
- `skills/perfect-power-bi/references/validation-and-deployment.md`
- `data/kpi_perfect/reporting_sql`
- `data/kpi_perfect/power-bi`
- `documentation_web/perfect_power_bi/catalogue_kpi.md`
- `documentation_web/perfect_power_bi/data_gaps.md`
- `documentation_web/perfect_power_bi/resultats_validation.md`
- `documentation_web/perfect_power_bi/etat_migration.md`
- `documentation_web/perfect_power_bi/prochaines_etapes.md`

## Objectif

Mettre à disposition une lecture décisionnelle fiable, rapprochable avec Perfect Vision et exploitable par la Direction, le contrôle interne et les métiers.

## Parcourir Perfect Power BI

<div class="bb-link-grid">
  <a class="bb-link-card" href="architecture_reporting.html">
    <span>Architecture reporting</span>
    Chaîne Perfect Vision, BB_VISION_REPORTING, faits, dimensions et scripts SQL.
  </a>
  <a class="bb-link-card" href="modele_pages.html">
    <span>Modèle et pages</span>
    Tables TMDL, pages PBIP, dimensions, faits et audiences.
  </a>
  <a class="bb-link-card" href="kpi_dax_validation.html">
    <span>KPI, DAX et validation</span>
    Mesures, traçabilité, rapprochements et contrôles.
  </a>
  <a class="bb-link-card" href="catalogue_kpi.html">
    <span>Catalogue KPI</span>
    KPI matérialisés, sources, mesures DAX, grains et validations.
  </a>
  <a class="bb-link-card" href="data_gaps.html">
    <span>Data gaps</span>
    Données manquantes ou capacités non encore matérialisées.
  </a>
  <a class="bb-link-card" href="resultats_validation.html">
    <span>Résultats de validation</span>
    Lots contrôlés, rapprochements SQL et validation des faits.
  </a>
  <a class="bb-link-card" href="etat_migration.html">
    <span>État de migration</span>
    Suivi de la bascule vers BB_VISION_REPORTING.
  </a>
  <a class="bb-link-card" href="prochaines_etapes.html">
    <span>Prochaines étapes</span>
    Feuille de route opérationnelle Power BI.
  </a>
  <a class="bb-link-card" href="exploitation_limites.html">
    <span>Exploitation</span>
    Rafraîchissement, sécurité, publication, RLS et limites.
  </a>
</div>
