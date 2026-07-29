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
