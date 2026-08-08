<section class="bb-hero">
  <div class="bb-hero__label">Microfinance Bisou Bisou S.A</div>
  <h1>Documentation Web des solutions Data</h1>
  <p>
    Un point d'entrée unique pour comprendre Perfect Vision, Perfect Power BI
    et la Solution Numérique : sources, règles métier, KPI, contrôles, exports,
    limites et responsabilités.
  </p>
  <div class="bb-hero__actions">
    <a href="perfect_vision/index.html" class="bb-button">Perfect Vision</a>
    <a href="perfect_power_bi/index.html" class="bb-button bb-button--light">Perfect Power BI</a>
    <a href="solution_numerique/index.html" class="bb-button bb-button--green">Solution Numérique</a>
  </div>
</section>

<section class="bb-section">
  <h2>Trois domaines, un seul site</h2>
  <div class="bb-card-grid">
    <article class="bb-card">
      <span class="bb-card__tag">Base métier</span>
      <h3>Perfect Vision</h3>
      <p>
        Documentation du socle SQL, des cycles de contrôle, des requêtes
        prioritaires et du tableau de bord Streamlit.
      </p>
      <a href="perfect_vision/index.html">Ouvrir la documentation →</a>
    </article>
    <article class="bb-card">
      <span class="bb-card__tag">Décisionnel</span>
      <h3>Perfect Power BI</h3>
      <p>
        Documentation de BB_VISION_REPORTING, du modèle en étoile, des pages
        Power BI, des mesures DAX et des validations.
      </p>
      <a href="perfect_power_bi/index.html">Ouvrir la documentation →</a>
    </article>
    <article class="bb-card">
      <span class="bb-card__tag">Digital</span>
      <h3>Solution Numérique</h3>
      <p>
        Documentation des imports, extraits clients, DAT, crédits, statistiques,
        projections, balances et rapprochements G2.
      </p>
      <a href="solution_numerique/index.html">Ouvrir la documentation →</a>
    </article>
  </div>
</section>

<section class="bb-section bb-section--soft">
  <h2>Architecture simplifiée</h2>

```mermaid
flowchart LR
    PV[Perfect Vision<br/>BB_VISION_PRO]
    RPT[BB_VISION_REPORTING]
    PBI[Perfect Power BI]
    SN[Solution Numérique]
    T[Transactions]
    S[Savings Account]
    L[Loans Account]
    C[Customers]
    G2[G2 M-Pesa]

    PV --> RPT --> PBI
    T --> SN
    S --> SN
    L --> SN
    C --> SN
    G2 -. Contrôle et identité .-> SN
```
</section>

<section class="bb-section">
  <h2>Règles de lecture essentielles</h2>
  <div class="bb-rule-list">
    <div><strong>Devises séparées</strong><br>CDF et USD ne sont jamais additionnés sans conversion officielle documentée.</div>
    <div><strong>G2 non pilotant</strong><br>G2 enrichit l'identité et contrôle les écritures, sans piloter les montants.</div>
    <div><strong>Traçabilité</strong><br>Chaque KPI doit pouvoir être relié à sa source, son grain, sa période et sa devise.</div>
    <div><strong>Confidentialité</strong><br>Aucune donnée client réelle ne doit être publiée dans la documentation web.</div>
  </div>
</section>

<section class="bb-section">
  <h2>Sources documentaires utilisées</h2>
  <table>
    <thead>
      <tr>
        <th>Source</th>
        <th>Utilisation</th>
      </tr>
    </thead>
    <tbody>
      <tr><td><code>skills/perfect-vision</code></td><td>Règles Perfect Vision et cycles de contrôle</td></tr>
      <tr><td><code>skills/perfect-power-bi</code></td><td>Architecture Power BI, DAX, validation et déploiement</td></tr>
      <tr><td><code>skills/solution-mpesa</code></td><td>Règles Solution Numérique, contrats, exports et KPI</td></tr>
      <tr><td><code>data/modelisation/requetes.sql</code></td><td>Catalogue SQL des requêtes métier</td></tr>
      <tr><td><code>data/kpi_perfect</code></td><td>PBIP, TMDL, reporting SQL et documentation KPI</td></tr>
      <tr><td><code>credit_app/services/mpesa_analysis.py</code></td><td>Calculs métier de la Solution Numérique</td></tr>
    </tbody>
  </table>
</section>
