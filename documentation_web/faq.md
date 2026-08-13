# FAQ

Cette page regroupe les questions récurrentes par domaine afin d'aider les utilisateurs à retrouver rapidement l'analyse ou l'explication attendue.

<section class="bb-section">
  <h2>Choisir une catégorie</h2>
  <p>
    Sélectionnez le domaine concerné pour accéder directement aux questions et réponses.
  </p>
  <div class="bb-card-grid">
    <article class="bb-card">
      <span class="bb-card__tag">Base métier</span>
      <h3>Perfect Vision</h3>
      <p>
        Questions liées aux cycles de contrôle, requêtes SQL, indicateurs et analyses issues de Perfect Vision.
      </p>
      <a href="#perfect-vision">Voir les questions Perfect Vision →</a>
    </article>
    <article class="bb-card">
      <span class="bb-card__tag">Décisionnel</span>
      <h3>Perfect Power BI</h3>
      <p>
        Questions liées à BB_VISION_REPORTING, aux KPI, au modèle Power BI et aux analyses décisionnelles.
      </p>
      <a href="#perfect-power-bi">Voir les questions Power BI →</a>
    </article>
    <article class="bb-card">
      <span class="bb-card__tag">Digital</span>
      <h3>Solution Numérique</h3>
      <p>
        Questions liées aux fichiers numériques, clients, épargnes, crédits, DAT, G2 M-Pesa et extraits clients.
      </p>
      <a href="#solution-numerique">Voir les questions Solution Numérique →</a>
    </article>
  </div>
</section>

## Perfect Vision

### Quelle différence y a-t-il entre Perfect Vision et Solution Numérique 

Perfect Vision est la source métier historique de la microfinance : crédits, épargne classique, portefeuille, risques, qualité de données et indicateurs de contrôle interne.

La Solution Numérique exploite les exports du portail digital pour analyser les transactions, clients, comptes ouverts, comptes bloqués, crédits digitaux, rapprochements G2 M-Pesa et extraits clients numériques.

### Où trouver les analyses Perfect Vision dans l'interface 

Les analyses Perfect Vision se trouvent dans le parcours principal de contrôle interne, selon le cycle sélectionné dans la barre latérale : crédit, épargne ou autre cycle disponible.

Les onglets importants sont notamment :

| Besoin | Onglet à consulter |
|---|---|
| Vue globale du cycle | `Synthèse` |
| Contrôles métier et anomalies | `Contrôles` |
| Surveillance opérationnelle | `Surveillance` |
| Portefeuille et encours | `Portefeuille` |
| Risques | `Risques` |
| Qualité des données | `Qualité` |
| Export des analyses | `Export` |

### À quoi servent les requêtes Perfect Vision du fichier `requetes.sql` 

Le fichier `data/vision/requetes.sql` recense les indicateurs, requêtes de contrôle et analyses à automatiser progressivement. Les requêtes avec un niveau d'importance élevé, notamment 9 ou 10, servent de base pour les tableaux de bord, les contrôles prioritaires et les rapports destinés à la direction.

## Perfect Power BI

### Pourquoi Power BI utilise-t-il `BB_VISION_REPORTING` 

La couche `BB_VISION_REPORTING` transforme les données métier en tables plus adaptées au reporting : faits, dimensions, indicateurs et périodes d'analyse. Elle évite de connecter Power BI directement à toute la complexité de `BB_VISION_PRO`.

### Quel est l'objectif du projet Perfect Power BI 

L'objectif est de produire des indicateurs fiables, visuels et directement exploitables par les décideurs à partir des données Perfect Vision. Power BI doit permettre de suivre l'évolution des crédits, de l'épargne, des remboursements, des risques, de la qualité de données et des performances opérationnelles.

### Pourquoi certains KPI existent dans Power BI mais pas dans Solution Numérique 

Les sources et le grain d'analyse ne sont pas les mêmes. Power BI peut s'appuyer sur la base Perfect Vision et sur une couche reporting structurée. La Solution Numérique dépend des colonnes présentes dans les exports du portail digital, comme `Transactions`, `Savings Account`, `Loans Account`, `Customers` et les rapports G2 M-Pesa facultatifs.

## Solution Numérique

### Quels fichiers sont les plus importants pour la Solution Numérique 

Les fichiers principaux sont :

| Priorité | Fichier | Importance |
|---|---|---|
| 1 | `Transactions` | Source principale des mouvements, dépôts, retraits, remboursements, crédits décaissés et activité dans le temps |
| 2 | `Savings Account` | Source des comptes ouverts, comptes bloqués, DAT, soldes d'épargne et échéances |
| 3 | `Loans Account` | Source des crédits accordés, encours, impayés, échéances et portefeuille crédit |
| 4 | `Customers` | Source du référentiel client et des dates de création |
| 5 | Rapports `G2 M-Pesa` | Source facultative d'enrichissement du nom client et de contrôle des écritures |
| 6 | `Clients_Perfect` | Source facultative pour les croisements Perfect / Solution Numérique |

### Où trouver le cockpit client 

Dans le module `Solution Numérique`, ouvrir l'onglet `Clients`.

Le cockpit Clients est organisé en cinq volets :

| Besoin | Volet à consulter |
|---|---|
| KPI, référentiel et qualité des données | `Vue d'ensemble` |
| Clients actifs, inactifs, acquisition et activation | `Activité et activation` |
| Nouveaux numéros clients et produits créés sur la période | `Nouveaux numéros clients et produits` |
| Vue Client 360, produits détenus et tranches d'encours | `Client 360 et segmentation` |
| DAT sans crédit actif et listes commerciales prudentes | `Opportunités` |

Le bloc `Export du cockpit Clients` se trouve après les volets d'analyse. Il permet de préparer l'Excel complet du cockpit Clients uniquement si l'utilisateur en a besoin.

### Pourquoi faut-il cliquer sur `Actualiser les clients` 

Les fichiers de la Solution Numérique peuvent être lourds. Pour éviter qu'un changement de date, de fréquence ou de seuil relance immédiatement tous les calculs, les paramètres sont regroupés dans un formulaire. L'analyse démarre seulement après le clic sur `Actualiser les clients`.

Ce principe est aussi utilisé dans les onglets analytiques lourds comme `Épargnes`, `Crédits`, `Statistiques` et `Projections`.

### Pourquoi l'Excel n'apparaît-il pas directement 

La consultation en ligne est prioritaire. Les KPI, tableaux, alertes et listes sont affichés dans Streamlit pour permettre une lecture rapide. L'Excel est un support secondaire de retraitement ou de partage.

Pour limiter les risques de lenteur ou de crash sur Streamlit Cloud, les gros classeurs Excel sont préparés seulement après clic sur `Préparer`, puis le bouton `Télécharger` apparaît quand le fichier est construit.

### Où trouver les clients qui épargnent le plus 

Dans l'interface Streamlit, ouvrir le module `Solution Numérique`, puis l'onglet `Épargnes`.

Les emplacements utiles sont :

| Besoin | Sous-onglet | Liste ou tableau |
|---|---|---|
| Clients qui épargnent le plus | `Concentration et opportunités` | Classement des gros déposants |
| Concentration de l'épargne par client | `Concentration et opportunités` | Top clients par devise et tranches d'encours |
| Analyse des clients et comptes | `Portefeuille et produits` | Détail client, compte et solde |

Ces analyses doivent toujours être lues devise par devise. Les montants CDF et USD ne doivent pas être additionnés.

### Peut-on analyser les meilleurs clients par tranche d'argent 

Oui. Le classement `rang_client` donne les meilleurs clients un par un, tandis que `tranche_encours` regroupe les clients par niveau d'argent. Dans `Solution Numérique`, cette lecture est disponible dans :

- `Épargnes > Concentration et opportunités` pour les comptes ouverts et DAT ;
- `Clients > Client 360 et segmentation` pour les familles compte ouvert, DAT et crédit ;
- `Crédits > Risques et concentration` pour les expositions crédit.

Les tranches sont calculées séparément par devise. Elles ne remplacent pas le top clients ; elles le complètent.

### Où trouver les épargnes ou DAT sans crédit actif 

Dans le module `Solution Numérique`, ouvrir l'onglet `Épargnes`, puis le sous-onglet `Concentration et opportunités`.

Les listes utiles sont :

| Besoin | Liste à consulter |
|---|---|
| Clients avec DAT sans crédit actif | `dat_sans_credit_actif` |
| Clients avec forte épargne sans crédit | `forte_epargne_sans_credit` |

Ces listes sont des signaux commerciaux prudents. Elles ne constituent pas une éligibilité automatique au crédit.

### Où trouver les échéances DAT et les comptes bloqués proches du terme 

Dans le module `Solution Numérique`, ouvrir l'onglet `Épargnes`, puis :

| Besoin | Sous-onglet |
|---|---|
| DAT en cours | `DAT et échéances` |
| Comptes bloqués échus ou bientôt à terme | `DAT et échéances` |
| Préparation des remboursements DAT | `DAT et échéances` |

Le taux annuel DAT est paramétrable. Par défaut, la règle Bisou Bisou utilisée pour l'estimation est 11 % par an.

### Où trouver les crédits en arriéré 

Dans le module `Solution Numérique`, ouvrir l'onglet `Crédits`, puis le sous-onglet `Opportunités et qualité`.

La liste principale à consulter est :

| Besoin | Liste à consulter |
|---|---|
| Crédits échus avec encours | `prets_echus_avec_encours` |

Cette analyse utilise principalement `Loans Account`, notamment les informations d'encours, de statut et d'échéance.

### Où trouver les crédits en PAR 30 jours 

Dans le module `Solution Numérique`, ouvrir l'onglet `Crédits`, puis le sous-onglet `Opportunités et qualité`.

La liste à consulter est :

| Besoin | Liste à consulter |
|---|---|
| Crédits en PAR 30 jours | `prets_par_simplifie_30j` |

Le PAR affiché est un suivi opérationnel simplifié lorsqu'un plan d'amortissement détaillé n'est pas disponible.

### Où trouver les crédits en défaut ou avec pénalités 

Dans le module `Solution Numérique`, ouvrir l'onglet `Crédits`, puis le sous-onglet `Opportunités et qualité`.

Les listes utiles sont :

| Besoin | Liste à consulter |
|---|---|
| Crédits en défaut | `prets_defaulted` |
| Crédits avec pénalités | `prets_avec_penalites` |

### Pourquoi G2 M-Pesa n'est-il pas un troisième canal financier 

G2 M-Pesa est un rapport de contrôle. Il aide à vérifier les écritures, enrichir le nom du client et rapprocher certaines références. Il ne doit pas piloter les montants, les soldes, les DAT, les remboursements ou les crédits.

La source financière principale reste la Solution Numérique.

### Pourquoi CDF et USD ne sont-ils pas totalisés ensemble 

CDF et USD sont deux devises différentes. Sans taux officiel de conversion et sans règle comptable validée, les additionner produirait un chiffre trompeur.

Les analyses financières de la Solution Numérique doivent donc rester séparées par devise.
