# Architecture et connectivité

## Configuration locale connue

État vérifié le 29 juillet 2026 ; le recontrôler avant chaque décision :

- instance locale : `CDBBIMFL065` ;
- base de test : `BB_VISION_PRO_TEST` ;
- moteur : SQL Server 2022 Standard ;
- Always On : non activé lors du contrôle ;
- SQL Server Agent : arrêté lors du contrôle ;
- Power BI Desktop : installé.

Cette configuration convient au développement et aux tests, pas à une conclusion sur la production.

## Architecture cible

```text
BB_VISION_PRO production
        |
        | extraction incrémentale en lecture seule
        v
BB_VISION_REPORTING
        |
        | passerelle locale standard
        v
Modèle sémantique Power BI en Import
        |
        v
Rapports et applications Power BI
```

Placer `BB_VISION_REPORTING` sur une instance ou une VM séparée lorsque la charge et la disponibilité le justifient. Ne pas considérer une seconde base sur le même serveur comme une isolation de ressources complète.

## Choix de la copie de données

| Méthode | Fraîcheur | Avantage | Limite | Usage |
|---|---:|---|---|---|
| ETL incrémental | 15 min à 24 h | Modèle maîtrisé et optimisé | Développement et supervision | Choix recommandé |
| Sauvegarde/restauration | Journalier | Simple pour démarrer | Copie complète et données moins fraîches | Prototype ou secours |
| Réplication transactionnelle | Secondes à minutes | Quasi-temps réel | Administration, schéma source, licence du Subscriber | Besoin opérationnel démontré |
| Log shipping en standby | Minutes à heures | Technologie SQL Server classique | Lecture interrompue pendant certaines restaurations | Reporting périodique tolérant les coupures |
| Basic Availability Group | Haute disponibilité | Basculement | Pas de lecture sur le secondaire en édition Standard | Ne pas choisir pour le reporting |

Ne pas activer CDC, réplication ou objets dans la base du progiciel sans validation de l'éditeur.

## Choix du mode Power BI

### Import

Choisir Import par défaut :

- meilleure interactivité ;
- fonctionnalités Power BI plus complètes ;
- faible charge lors de la consultation ;
- fonctionnement adapté au rafraîchissement planifié et incrémental.

### DirectQuery

Choisir DirectQuery seulement si :

- la fraîcheur attendue est inférieure à l'intervalle de rafraîchissement possible ;
- la source est un data mart, une réplique lisible ou une couche agrégée ;
- chaque requête répond à une latence interactive ;
- les index, le query folding, la concurrence et la passerelle ont été testés.

Ne pas utiliser DirectQuery contre les requêtes longues de `requetes.sql` ou directement contre les tables de production.

### Modèle composite

Envisager après stabilisation :

- dimensions et agrégats en Import ;
- détail récent en DirectQuery ;
- tables Dual uniquement avec un modèle et des tests maîtrisés.

## Paramètres de connexion du prototype

Dans Power BI Desktop :

- Serveur : `CDBBIMFL065`
- Base : `BB_VISION_PRO_TEST`
- Mode : `Importer`
- Authentification : Windows
- Instruction SQL : vide lors du premier branchement

Sélectionner ensuite les tables de reporting préparées. Définir les relations dans le modèle et ne pas faire confiance aveuglément à la détection automatique.

## Connexion au data mart reporting validée

Lorsque `BB_VISION_REPORTING` est alimentée, les tables déjà matérialisées doivent être consommées depuis cette base plutôt que recalculées dans Power Query.

Configuration validée localement :

- Serveur : `CDBBIMFL065`
- Base source opérationnelle de test : `BB_VISION_PRO_TEST`
- Base reporting : `BB_VISION_REPORTING`
- Mode Power BI : `Importer`
- Authentification : Windows

Dans le PBIP IMF BB, conserver deux paramètres de base :

- `pBaseDonnees = "BB_VISION_PRO_TEST"` pour les tables non encore migrées vers le data mart ;
- `pBaseReporting = "BB_VISION_REPORTING"` pour les faits matérialisés.

Tables validées :

- `F_Conformite` lit `BB_VISION_REPORTING.rpt.f_conformite` ;
- `F_Clients` lit `BB_VISION_REPORTING.rpt.f_clients` ;
- `F_Credit_PAR_Detail` lit `BB_VISION_REPORTING.rpt.f_credit_par_detail` ;
- `F_Credit_Portefeuille` lit `BB_VISION_REPORTING.rpt.f_credit_portefeuille`.

Power Query recommandé :

```powerquery
Source = Sql.Database(pServeur, pBaseReporting, [CreateNavigationProperties=false]),
TableSource = Source{[Schema="rpt", Item="f_conformite"]}[Data],
FiltrePeriode = Table.SelectRows(TableSource, each [date_debut] = pDateDebut and [date_fin] = pDateFin)
```

Éviter pour ces tables matérialisées :

- `Value.NativeQuery` avec `SET NOCOUNT ON` ;
- les blocs `DECLARE @date_debut ...` dans Power Query ;
- les filtres de date construits par concaténation de chaînes.

Ces formes peuvent échouer dans Power BI avec des erreurs OLE DB/ODBC de syntaxe ou de conversion de date.

## Passerelle et identités

- Installer une passerelle locale en mode standard sur une machine toujours allumée.
- Employer exactement les mêmes noms de serveur et de base dans Power BI Desktop et dans la source de la passerelle.
- Utiliser un compte de service en lecture seule et non un compte personnel.
- Autoriser uniquement les auteurs et administrateurs nécessaires sur la source de passerelle.
- Prévoir la supervision des erreurs, certificats, mots de passe et versions de passerelle.

## Ordonnancement

1. Charger les tables de reporting.
2. Exécuter les contrôles de qualité et de rapprochement.
3. Marquer le lot comme prêt.
4. Rafraîchir le modèle Power BI.
5. Contrôler la fraîcheur et notifier les échecs.

Ne pas rafraîchir Power BI pendant qu'une table de faits est partiellement alimentée.
