# Changelog Perfect Vision

## 13 août 2026

### Modifié

- Ajout d'une lecture métier des requêtes crédit prioritaires : qualité du portefeuille, politiques d'octroi, stabilisation du PAR et suivi des KPI.
- Optimisation de la requête `162_cycle_credit_encours_credit_detaille_a_date` avec des tables temporaires locales indexées dans `tempdb`, sans création de table permanente.
- Ajout de la requête `163_cycle_epargne_encours_epargne_detaille_a_date` pour produire l'encours épargne hebdomadaire à une date de situation, avec des colonnes lisibles par les utilisateurs.
- Renforcement de la requête `144_cycle_credit_clients_avec_dat_sans_credits_en_cours` : la détection d'un DAT utilisé comme garantie vérifie désormais le chemin `GARANTIES -> OPERATIONS_DAT` et le chemin `CAUTIONS_FINANCIERE_COMPTE -> DOSSIERS_DAT`.
- Réorganisation des sections `Requêtes utiles` par cycle : les requêtes d'aide à la décision sont placées avant les contrôles techniques, avec une colonne `Commentaire`.

### Tests

- Test sur `BB_VISION_PROD` au 10/08/2026 : `GARANTIES` ne contient aucune ligne et les cautions financières observées pointent vers des comptes ordinaires/DAV; dans ce contexte, `DAT utilisé comme garantie = Non` est cohérent.
- Profilage court sur `BB_VISION_PROD` : Q162 s'exécute correctement après optimisation.
- Profilage court sur `BB_VISION_PROD` au 10/08/2026 : Q163 s'exécute correctement avec tables temporaires locales.

## 08 août 2026

### Ajouté

- Création de la documentation web Perfect Vision.
- Documentation initiale des sources, du schéma SQL, des requêtes prioritaires et du tableau de bord Streamlit.

### Limites

- Le dictionnaire exhaustif des 800+ tables n'est pas encore détaillé table par table.
