# Formations

Cette rubrique transforme la documentation en support de formation. L'objectif est d'aider un nouvel utilisateur, un analyste, un contrôleur ou un responsable métier à comprendre progressivement les outils Data de la Microfinance Bisou Bisou S.A.

Les formations doivent rester simples, sincères et pratiques : on part du besoin métier, on explique les sources, puis on montre comment lire les indicateurs sans mélanger les systèmes ni les devises.

La partie pédagogique ne remplace pas la partie technique. Le site doit garder deux niveaux de lecture :

- **lecture métier** : comprendre les indicateurs, les fichiers, les onglets et les décisions possibles ;
- **lecture informaticien** : comprendre les scripts, les contrats de données, les fonctions, les tests, les limites techniques et les règles de maintenance.

## Parcours disponibles

<div class="bb-link-grid">
  <a class="bb-link-card" href="solution_numerique.html">
    <span>Formation Solution Numérique</span>
    Comprendre les fichiers numériques, les transactions, les DAT, les crédits, les extraits clients et le lien avec Perfect Vision par téléphone.
  </a>
  <a class="bb-link-card" href="perfect_vision.html">
    <span>Formation Perfect Vision</span>
    Comprendre les cycles, les contrôles internes, les requêtes SQL prioritaires et les indicateurs métier.
  </a>
  <a class="bb-link-card" href="perfect_power_bi.html">
    <span>Formation Perfect Power BI</span>
    Comprendre le reporting décisionnel, les KPI, le modèle de données et les bonnes pratiques de lecture.
  </a>
  <a class="bb-link-card" href="exercices.html">
    <span>Cas pratiques et exercices</span>
    S'entraîner avec des questions de contrôle, des scénarios et des lectures de tableaux.
  </a>
  <a class="bb-link-card" href="glossaire_pedagogique.html">
    <span>Glossaire pédagogique</span>
    Retrouver les mots importants expliqués simplement pour les utilisateurs métiers.
  </a>
  <a class="bb-link-card" href="technique_informaticiens.html">
    <span>Technique pour informaticiens</span>
    Conserver la lecture code, architecture, contrats, tests et maintenance pour les équipes informatiques.
  </a>
</div>

## Méthode pédagogique

Chaque module suit la même logique :

| Étape | Question à résoudre |
|---|---|
| 1. Comprendre | De quoi parle-t-on |
| 2. Identifier les sources | Quel fichier ou quelle base alimente l'analyse |
| 3. Lire le résultat | Quel chiffre faut-il regarder |
| 4. Contrôler | Qu'est-ce qui peut être faux ou incomplet |
| 5. Décider | Quelle action métier peut être préparée |

## Règles de formation à répéter

- Ne jamais additionner CDF et USD sans conversion officielle.
- Distinguer une source financière d'une source de contrôle.
- Expliquer le grain d'analyse : client, compte, transaction, crédit, échéance ou période.
- Rappeler que G2 M-Pesa enrichit et contrôle, mais ne pilote pas les montants.
- Relier progressivement Perfect Vision et la Solution Numérique par le numéro de téléphone normalisé.

## Règles pour la partie technique

- Ne jamais supprimer les noms techniques utiles aux informaticiens : fichiers, fonctions, tables, colonnes, scripts et chemins de code.
- Toujours distinguer le nom affiché à l'utilisateur du nom technique utilisé par le code.
- Documenter les tests associés aux règles importantes.
- Garder les limites techniques visibles : performance, cache, format de fichier, colonnes manquantes, données partielles.
- Lorsqu'une page est destinée aux informaticiens, écrire clairement les fichiers concernés et le rôle de chaque composant.
