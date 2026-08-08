# FAQ

## Quelle différence entre Perfect Vision et Solution Numérique ?

Perfect Vision est la source métier microfinance historique. La Solution Numérique exploite les exports du portail digital pour analyser les transactions, clients, épargne, DAT, crédits et rapprochements G2.

## Pourquoi Power BI utilise BB_VISION_REPORTING ?

La couche `BB_VISION_REPORTING` transforme les données métier en tables de faits et dimensions adaptées au reporting. Elle protège le modèle Power BI contre la complexité directe de `BB_VISION_PRO`.

## Pourquoi G2 n'est-il pas un troisième canal financier ?

G2 est un rapport de contrôle M-Pesa. Il aide à vérifier et enrichir, mais les montants de la Solution Numérique viennent des exports opérationnels principaux.

## Pourquoi CDF et USD ne sont-ils pas totalisés ?

Parce qu'il s'agit de deux devises différentes. Sans taux officiel de conversion, les additionner produirait un chiffre trompeur.

## Pourquoi certains KPI existent dans Power BI mais pas dans Solution Numérique ?

Les sources et le grain diffèrent. Power BI peut utiliser la couche reporting Perfect Vision, tandis que la Solution Numérique dépend des colonnes disponibles dans les exports numériques.
