# Solution Numérique

La Solution Numérique analyse les données digitales issues du portail opérationnel : transactions, clients, épargne, DAT, crédits, rapprochements G2, statistiques et projections.

Le nom historique M-PESA reste utilisé pour certaines sources, mais l'onglet cible est **Solution Numérique**.

## Sources principales

| Priorité | Fichier | Importance | Pourquoi |
|---|---|---|---|
| 1 | Transactions | Indispensable | Source principale des mouvements, dépôts, retraits, remboursements, crédits décaissés, activité dans le temps |
| 2 | Savings Account | Indispensable | Source des comptes ouverts, DAT, soldes d'épargne, statuts, échéances |
| 3 | Loans Account | Très important | Source des crédits accordés, encours, impayés et portefeuille crédit |
| 4 | Customers | Important | Source des clients connus et créations de clients |
| 5 | Transactions G2 | Facultatif utile | Enrichit le nom du client et contrôle les écritures |
| 6 | Clients Perfect | Facultatif analytique | Croisement Perfect / Solution Numérique / G2 |

## Règle source

Turbo / Solution Numérique constitue la source opérationnelle principale. G2 enrichit l'identité du client et fournit une preuve de rapprochement des écritures, sans intervenir dans le calcul des montants, des soldes, des DAT ou des remboursements.

## Parcourir la Solution Numérique

<div class="bb-link-grid">
  <a class="bb-link-card" href="sources_contrats.html">
    <span>Sources et contrats</span>
    Transactions, Savings Account, Loans Account, Customers, G2 et colonnes attendues.
  </a>
  <a class="bb-link-card" href="modele_relationnel.html">
    <span>Modèle relationnel</span>
    Lecture des fichiers Excel comme des tables : clés, relations, cardinalités et pont Perfect Vision.
  </a>
  <a class="bb-link-card" href="circuits_information.html">
    <span>Circuit d'information</span>
    Comment les lignes sont générées lors d'une transaction, d'une épargne, d'un DAT ou d'un crédit.
  </a>
  <a class="bb-link-card" href="extraits_clients.html">
    <span>Extraits clients</span>
    Relevé bancaire, détail des transactions, DAT, remboursements et exports.
  </a>
  <a class="bb-link-card" href="finance_balances.html">
    <span>Finance et balances</span>
    Balance observée, journaux, suivi dépôts/retraits et exports.
  </a>
  <a class="bb-link-card" href="clients_epargnes_credits.html">
    <span>Clients, épargnes, crédits</span>
    Cockpits, comptes ouverts, comptes bloqués, portefeuille crédit et remboursements.
  </a>
  <a class="bb-link-card" href="g2_dat_rapprochements.html">
    <span>G2 et DAT</span>
    Rôle de G2, rapprochements, échéances DAT et contrôles.
  </a>
  <a class="bb-link-card" href="statistiques_projections.html">
    <span>Statistiques et projections</span>
    Blocs d'analyse, comparaisons, tendances et prévisions.
  </a>
  <a class="bb-link-card" href="tests_limites.html">
    <span>Tests et limites</span>
    Tests automatisés, jeux de test métier et limites des données.
  </a>
</div>
