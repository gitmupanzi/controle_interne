---
name: solution-mpesa
description: Importer, normaliser, contrôler et rapprocher les fichiers Excel M-PESA de Turbo, G2 et Perfect; construire les sous-onglets Pilotage financier Turbo, Comptabilité Turbo, G2/DAT, Extrait client, Crédits et Perfect_client, produire la balance auxiliaire client, mesurer les flux, remboursements, nouveaux crédits, encours, PAR, épargne, DAT, concentration et risques, détecter les anomalies et produire les exports Excel ciblés, Word et PDF sans mélanger les devises. Utiliser pour toute question ou modification liée à Solution M-PESA, Bisou Bisou Digital, Portal/Turbo, G2, Perfect, Phone_Prefixe, Receipt No/ref_no, DAT, épargne, crédit, comptabilité, balance, fidélisation, rapprochement client ou rapport M-PESA du projet Streamlit.
---

# Solution M-PESA

Réutiliser les contrats et fonctions métier existants. Préserver la traçabilité des sources, le grain des opérations et la séparation stricte des devises.

## Procédure de travail

1. Identifier les fichiers disponibles, la période, le sens des flux et le livrable demandé.
2. Lire [references/data-contracts.md](references/data-contracts.md) pour sélectionner les colonnes, clés, classifications et règles de dégradation.
3. Exécuter `scripts/inspect_mpesa_contracts.py` avant de modifier un import ou un alias.
4. Normaliser avec les fonctions `prepare_*` de `credit_app/services/mpesa_analysis.py`; ne pas reproduire cette logique dans Streamlit.
5. Valider les colonnes obligatoires et afficher les colonnes manquantes ainsi que les colonnes réellement disponibles.
6. Construire les rapprochements et classifications dans le service, puis limiter l'interface au filtrage et au rendu.
7. Conserver les indicateurs de correspondance, motifs d'écart, lignes non rapprochées et sources facultatives absentes.
8. Calculer chaque solde, total et taux par devise. Ne jamais sommer CDF et USD.
9. Tester les cas nominal, source absente, format G2 alternatif, doublon, référence inconnue, contrôle en écart et solde d'ouverture manquant.

Tous les téléversements de Solution M-PESA peuvent recevoir plusieurs fichiers. Conserver leur provenance, supprimer les chevauchements avec la clé métier propre à chaque source et ne jamais additionner plusieurs instantanés du même compte, crédit ou client.

Dans tous les libellés destinés aux utilisateurs, ajouter `[Turbo]`, `[G2]` ou `[Turbo + G2]` selon la source effective. Réserver `Solution M-PESA` au nom global du module; ne jamais utiliser `M-PESA` seul comme source d'un indicateur. Exception : le Word officiel de l'Extrait client ne contient aucun suffixe `[Turbo]`, car il constitue un relevé client et non un écran de traçabilité technique.

## Décision de refactoring des téléversements

État : refactoring Streamlit implémenté. Le parcours principal affiche quatre sources Turbo et deux compléments facultatifs.

- Réduire le parcours principal Turbo à quatre téléversements : `Transactions`, `Savings Account`, `Loans Account` et `Customers`.
- Traiter `Savings Account` comme l'unique téléversement principal pour l'épargne courante et les DAT. En déduire deux jeux internes : tous les `NORMAL SAVINGS` et tous les `FIXED SAVINGS`, soldes positifs ou nuls.
- Ne plus exiger deux téléversements distincts pour `Customers with Current Savings Account` et `Customers with Fixed Savings Account`. Ce sont des vues filtrées à solde positif de `Savings Account`, pas des sources exhaustives.
- Ne pas afficher deux widgets séparés pour les vues résumées. Le téléversement multiple unique `Savings Account` accepte soit la source complète recommandée, soit les deux fichiers `Customers with Current Savings Account` et `Customers with Fixed Savings Account` chargés ensemble en mode de compatibilité.
- Si la source complète et les vues résumées sont chargées ensemble, donner la priorité à la source complète et ignorer les lignes résumées afin d'éviter les doublons. Si seules les synthèses sont présentes, signaler que les comptes à solde nul et l'historique exhaustif sont indisponibles.
- Conserver un seul téléversement multiple G2 facultatif pour réunir les entrées 1441 et les sorties 15558, puis un téléversement `Clients_Perfect` facultatif.
- Interface en production : quatre emplacements Turbo principaux, plus G2 et Perfect comme compléments facultatifs. L'emplacement `Savings Account` porte aussi le repli compatible Current + Fixed sans créer de nouveaux widgets. Ne pas dupliquer une donnée déjà démontrable depuis la source complète.
- Maintenir les tests de parité sur les comptes, soldes, devises, statuts et dates. Tous les sous-onglets doivent fonctionner avec les quatre sources Turbo principales, sans fichiers résumés.

Cas réel de référence du 17 juillet 2026 : `Savings Account` contient 77 084 comptes courants, dont 862 à solde positif, et 3 707 DAT, dont 1 214 à solde positif. Le résumé Current Savings correspond exactement aux 862 comptes courants positifs; le résumé Fixed Savings correspond exactement aux 1 214 DAT positifs.

## Invariants G2/DAT

- Autoriser G2/DAT sans fichier G2 lorsque Transactions M-PESA_Turbo est disponible. Dans ce mode, construire une ligne analytique par `ref_no` pour les dépôts/DAT/remboursements et par `reference_id + created_at` pour `Retrait Vers M-Pesa`; utiliser `created_at` comme date d'analyse et tracer `source_analytique = Turbo seul`.
- En mode Turbo seul, ne jamais inventer `Opposite Party`, nom, statut, solde, `Initiation Time` ou `Completion Time` G2. Marquer les contrôles indépendants G2/Turbo et le rapprochement comme `Non applicable - Turbo seul`. Si G2 est chargé, le conserver comme source de son propre relevé de contrôle et ne pas ajouter les opérations proxy Turbo; Portal Turbo reste la source financière principale de la solution.
- Conserver une ligne analytique canonique par `Receipt No.`; signaler tout reçu dupliqué et ne pas le compter deux fois.
- Accepter plusieurs relevés G2 simultanément, notamment les fichiers d'entrées et de sorties; conserver le fichier source avant de les unifier.
- Compter les transactions terminees par date, jour de semaine et heure de `Completion Time`, sur des grilles completes de lundi a dimanche et de 00h a 23h; conserver la separation par devise et par sens et afficher les periodes sans activite a zero.
- Rapprocher d'abord `Receipt No.` avec `ref_no` du Portal/Turbo. Agréger les écritures techniques du même `ref_no` sans additionner les miroirs comptables comme plusieurs opérations G2.
- Pour une sortie `BisouBisouB2C` sans `ref_no`, autoriser le repli uniquement vers `Retrait Vers M-Pesa` avec téléphone, devise et montant identiques et un écart maximal de 120 minutes. Identifier l'opération Turbo par `reference_id + created_at`; ne jamais utiliser `reference_id` seul, car il peut désigner un compte réutilisé.
- Classifier les entrées rapprochées avec `account_type` et `description` du Portal : `FIXED SAVINGS`/`Depot Bloque` = `DAT`, `NORMAL SAVINGS`/`Epargne depot` = `Depot normal`, compte prêt/principal/portefeuille = `Remboursement prets`.
- Utiliser les règles G2 comme repli lorsque le Portal ne contient pas la référence; classifier les sorties B2C, demandes de crédit et opérations internes selon `Details`, `Reason Type`, `Paid In` et `Withdrawn`.
- Comparer la création avec `Initiation Time` G2 contre `created_at` Turbo; utiliser `Completion Time` seulement comme repli de création, puis comme date de finalisation et source du délai de traitement. Une différence absolue supérieure à 60 minutes est une anomalie de date, même si les deux horodatages sont le même jour. Tolérer un passage de date jusqu'à 60 minutes en conservant les deux dates dans `Observation`. Un délai G2 négatif est une anomalie.
- Contrôler séparément téléphone, devise, montant et date. Distinguer `Rapproche exact`, `Rapproche avec ecart`, `Non rapproche` et `Non applicable - operation interne`. Une `Super Transaction` non rapprochée ne constitue pas, à elle seule, une anomalie client.
- Dès qu'un export fournit des statuts, retenir uniquement les statuts G2 explicitement terminés dans les synthèses financières, le rapprochement DAT, Perfect_client et le Word; conserver les autres lignes dans la répartition des statuts, le détail Excel et les anomalies. Un ancien export sans aucun statut reste compatible.
- Utiliser `G2_CLASSIFIED_TRANSACTION_COLUMNS` comme ordre du noyau métier du tableau `Transactions` et du Word : `date`, `receipt_no`, `currency_code`, `details_rapport`, `opposite_party`, `duree`, `compte_cree`, `montant`, `montant_entree`, `montant_sortie`, `balance_numeric`. L'écran peut ajouter le fichier source et le statut comme colonnes de contrôle.
- Appliquer les bornes inclusives de date et d'heure de `Completion Time`, puis le filtre de sens, avant les synthèses, contrôles et exports; une sélection vide du multisélecteur de sens signifie tous les flux.

## Règles client et sources facultatives

Turbo constitue la source opérationnelle principale de la Solution M_PESA. G2 enrichit l’identité du client et fournit une preuve de rapprochement des écritures, sans intervenir dans le calcul des montants, des soldes, des DAT ou des remboursements.

- Considérer Portal Turbo comme la source financière principale de l'Extrait client. Transactions fournit les mouvements et remboursements; `Savings Account` fournit les DAT en cours.
- Construire la recherche, l'extrait, la synthèse et les exports depuis Turbo même si G2 est absent; afficher alors explicitement `Turbo seul` et réduire le contrôle G2 sans bloquer le client.
- Utiliser G2 uniquement comme source facultative de vérification et de complément du nom : enrichir Turbo par téléphone normalisé et, quand disponible, par `Receipt No = ref_no`. Ne jamais remplacer les montants, dates, soldes ou mouvements Turbo de l'extrait par G2; une divergence reste un résultat de contrôle.
- Construire la colonne `Description` de l'extrait officiel depuis les valeurs brutes `description` de Transactions M-PESA_Turbo, agrégées au grain de l'opération. Ajouter éventuellement téléphone et nom G2 après le libellé Turbo; ne jamais substituer `Details` ou `Reason Type` G2 à la description Turbo.
- Présenter les flux de l'extrait du point de vue de Bisou Bisou : le débit du compte `MPESA ACCOUNT` Turbo devient une entrée et le crédit devient une sortie. Affecter le compte `1441` aux entrées et `15558` aux sorties dans le Word et l'aperçu.
- Remplacer `Compte :` par `Devise :` dans les critères de l'en-tête Word. Conserver la colonne `Compte` dans le tableau transactionnel pour montrer 1441 ou 15558 ligne par ligne.
- Proposer les exports Word `CDF`, `USD` et `ALL`. Dans `ALL`, afficher la devise sur chaque ligne et calculer ouvertures, entrées, sorties et clôtures séparément par devise; ne jamais produire de total CDF + USD.
- Sélectionner par défaut les dépôts, les retraits `Retrait Vers M-Pesa`, les décaissements de crédit et les remboursements de crédit dans l'Extrait client. Regrouper un retrait au grain `customer_id + devise + created_at + reference_id` lorsque `ref_no` est absent, afin de ne pas compter deux fois les lignes miroir `MPESA ACCOUNT` et `NORMAL SAVINGS`.
- Limiter le tableau de vérification G2 au seul `customer_id` sélectionné, y compris lorsque le fichier DAT est absent.
- Résoudre vers `customer_id` après rapprochement; utiliser MSISDN ou référence uniquement selon les règles documentées.
- Rechercher `compte_cree` dans `Clients_Turbo`, puis l'épargne courante, puis le DAT.
- Agréger Perfect par `Phone_Prefixe` avant la jointure et conserver le nombre d'identités associées au numéro.
- Construire l'intersection G2–Turbo–Perfect au grain d'un téléphone normalisé, avec `present_dans_turbo`, `present_dans_g2`, `present_dans_perfect`, `present_dans_les_3_systemes` et le dataset `clients_trois_systemes`.
- Dans les libellés utilisateur, distinguer `Clients_Turbo`, `Clients_Perfect` et les clients transactionnels déduits de Turbo/G2; ne jamais appeler ces derniers `Clients_Turbo` sans preuve dans le fichier correspondant.
- Produire trois populations inclusives : `clients_perfect_dans_mpesa` pour Perfect∩G2, `clients_perfect_dans_turbo` pour Perfect∩Turbo et `clients_perfect_dans_turbo_et_mpesa` pour Perfect∩Turbo∩G2.
- Réduire proprement le rapport lorsqu'une source facultative manque; ne jamais provoquer un `KeyError` en indexant une source absente.
- Présenter un cumul relatif, et non un solde réel, si le solde d'ouverture M-PESA n'est pas fourni.
- Dans l'Extrait client, construire `dat_en_cours_client` depuis les `FIXED SAVINGS` à solde strictement positif de `Savings Account`, au grain `savings_id`, filtrés par client et devise. Ne pas appliquer la période transactionnelle à cette position courante.
- Dater la situation depuis `updated_at` ou `date_locked` de `Savings Account`; à défaut, utiliser la dernière transaction Turbo du client, puis les dates du DAT. Ne jamais utiliser une date G2 pour la situation DAT.
- Calculer l'intérêt simple estimé au taux DAT paramétré, 11 % par défaut, entre `date_approved` et `maturity_date`. Qualifier chaque DAT `En cours`, `Échéance proche`, `Échéance aujourd'hui` ou `Échu à rembourser`. Ne jamais présenter l'estimation comme une écriture comptable.
- Construire `remboursements_turbo_synthese_client` et `remboursements_turbo_detail_client` uniquement depuis les événements de remboursement de Transactions M-PESA_Turbo. Exclure les décaissements, la dette créée et les positions de crédit de la restitution Extrait client.
- Ne jamais modifier les fichiers Excel sources pendant l'analyse.
- Traiter l'export détaillé `Savings Account` comme source maître lorsqu'il est fourni. Déduire `NORMAL SAVINGS` de `Open Savings` / `Current account` et `FIXED SAVINGS` des produits `Fixed Account`; conserver les DAT à solde nul comme historique.
- Utiliser l'export `Customers with Current Savings Account` comme vue des comptes courants à solde positif; il ne représente pas les comptes courants à solde nul. Sans source maître, l'accepter seulement avec le résumé Fixed dans le téléversement unique et afficher le mode partiel.
- Utiliser l'export `Customers with Fixed Savings Account` comme vue des DAT à solde positif. Sans source maître, l'accepter avec le résumé Current et alimenter les analyses DAT disponibles en signalant l'absence des DAT à solde nul; avec la source maître, ne pas le recompter.
- Accepter les relevés G2 commençant directement par `Receipt No.` et les exports organisation bruts contenant cinq lignes descriptives. Promouvoir automatiquement la vraie ligne d'en-tête séparément pour chaque fichier 1441/15558.

## Invariants Pilotage financier Turbo

- Pour Transactions Turbo, conserver la sémantique comptable : `dr` = sortie du compte M-PESA et `cr` = entrée. Ne jamais appliquer les règles G2 `Paid In`/`Withdrawn` aux fichiers Turbo.
- Dédupliquer les transactions Turbo par `id`, les crédits par `loan_id`, les clients par identifiant ou téléphone/date, les comptes d'épargne et DAT par leur clé de compte; conserver la version la plus récente et la liste des fichiers sources.
- Construire chaque événement métier par `ref_no`; quand il manque, regrouper `customer_id + devise + created_at`. Ne jamais compter les écritures miroir comme plusieurs opérations.
- Utiliser une période inclusive `date début - date fin` et proposer la dernière journée opérationnelle complète. Permettre les évolutions par jour, semaine ou mois.
- Calculer exclusivement depuis Transactions M-PESA_Turbo les dépôts, retraits, remboursements observés, décaissements de nouveaux crédits, flux nets, activité d'épargne, concentration des transactions, transactions importantes, activité inhabituelle et fractionnement potentiel.
- Utiliser Loans Account_Turbo pour l'encours, les positions de crédit et le PAR 1/7/30 simplifié depuis `due_date`. Laisser le PAR vide si l'encours ou l'échéance nécessaire manque; ne jamais prétendre disposer d'un plan d'amortissement détaillé.
- Rapprocher globalement les décaissements Turbo des comptes de crédit créés dans la période, par devise. Présenter l'écart comme un contrôle global et non comme une affectation ligne à ligne.
- Adapter les contrôles Perfect Vision prioritaires réellement démontrables : remboursements, évolution dépôts/crédits, nouveaux crédits, concentration crédit/transactions, PAR par tranche, dépôts fréquents, tranches de dépôts, comptes inactifs, DAT sans crédit actif et crédit avec épargne disponible. Signaler les analyses non reproductibles faute de plan d'amortissement, provision, garantie ou plan comptable complet.
- Conserver G2 hors de tous ces calculs. Il peut enrichir un nom et prouver un rapprochement ailleurs dans la solution, mais ne modifie aucun montant, solde, DAT, encours, remboursement, seuil ou alerte du cockpit.
- Calculer toutes les analyses du cockpit une fois au premier chargement et les conserver en cache. Mettre en cache séparément le journal d'événements Turbo et le rapprochement crédit-épargne; une modification de période doit réutiliser la consolidation initiale. Ne jamais basculer vers un calcul limité au seul onglet interne sélectionné.
- Traiter les alertes comme des signaux de revue et non comme des preuves de fraude ou d'erreur.
- Produire l'échéancier DAT par tranche et devise.
- Dans le sous-onglet DAT, lister en priorité les comptes à solde positif déjà échus et ceux arrivant à terme dans un horizon réglable, fixé à 30 jours par défaut. Conserver `savings_id`, client, téléphone, produit, statut, approbation, échéance, jours restants, capital, intérêt estimé et capital plus intérêt.
- Utiliser 11 % comme taux d'intérêt annuel DAT Bisou Bisou par défaut dans la barre latérale. Autoriser sa modification et calculer l'intérêt simple estimé par `capital × taux annuel × durée contractuelle en jours / 365`, de `date_approved` à `maturity_date`.
- Présenter le capital, l'intérêt et le remboursement estimé séparément par devise. Qualifier ces montants d'estimations de préparation et non d'écritures comptables officielles.

## Invariants crédit et épargne

- Conserver `Loans Account` comme source obligatoire des prêts, encours, remboursements, intérêts, frais, échéances et statuts. `Savings Account` seul ne permet jamais de reconstruire un crédit.
- Rapprocher d'abord `Loans.savings_account_id` avec `Savings Account.id` ou `Savings Account.savings_id` lorsqu'il est renseigné et unique. Sinon, déduire le compte courant uniquement lorsque `customer_id + currency_code` identifie exactement un `NORMAL SAVINGS`.
- Conserver dans le contrôle les identifiants directs introuvables, les absences de compte courant, les correspondances multiples et les écarts de client, devise ou téléphone. Qualifier la liaison de `directe` ou `déduite`; ne jamais présenter une liaison déduite comme contractuelle.
- Construire la vue consolidée au grain `customer_id x devise`. Compter l'épargne courante et les DAT une seule fois par client et devise, même si le client possède plusieurs prêts.
- Juxtaposer montant du crédit, remboursements, encours, épargne courante et DAT positifs. Ne jamais compenser comptablement l'épargne avec le crédit, assimiler l'épargne à une garantie ou additionner CDF et USD.
- Cas réel du 17 juillet 2026 : `savings_account_id` est vide sur les 2 213 crédits. Le repli client x devise rapproche 2 212 crédits; un crédit USD sans compte courant correspondant reste à revoir.

## Invariants Comptabilité Turbo

- Utiliser exclusivement Transactions M-PESA_Turbo pour les écritures, les débits, les crédits, les soldes observés et les journaux comptables. G2 sert seulement à compléter le nom du client et à mesurer le rapprochement `Receipt No = ref_no`; ses montants ne remplacent jamais Turbo.
- Construire la balance auxiliaire client sur les comptes produits `NORMAL SAVINGS`, `FIXED SAVINGS` et `PRINCIPLE`, au grain `customer_id x devise x famille de position`. Résoudre une référence absente uniquement lorsqu'un seul compte connu du même type existe pour le client; sinon conserver `Reference compte ambigue ou absente`.
- Présenter tous les autres types de compte dans la balance des mouvements et le journal Turbo. Ne pas additionner les sous-registres techniques d'un crédit comme s'ils formaient une écriture unique : Turbo peut décrire plusieurs couches comptables de la même opération.
- Regrouper les opérations d'abord par `ref_no`; lorsque la référence manque, utiliser `customer_id + devise + created_at`. Conserver le journal brut, le journal regroupé, le contrôle de symétrie débit/crédit et le contrôle d'amplitude `abs(bal_after - bal_before) = abs(dr) + abs(cr)`.
- Qualifier chaque ouverture, clôture et position comme `observée`. Sans plan comptable complet ni soldes d'ouverture officiels, ne jamais appeler cette restitution `balance générale certifiée`, bilan ou compte de résultat officiel.
- Présenter séparément les intérêts, pénalités, parts Bisou et parts Voda observées. Ne pas les additionner automatiquement, car ces lignes peuvent constituer plusieurs ventilations d'un même produit financier.
- Afficher les positions des instantanés Current Savings, Fixed Savings et Loans à part de la balance journalière : leur date d'extraction peut être postérieure à la période comptable filtrée.
- Calculer et exporter toutes les synthèses par devise. Ne jamais compenser ou totaliser CDF et USD.
- Pour contrôler une évolution de la comptabilité Turbo, relire le cas de référence clôturé du 16 juillet 2026 dans [references/data-contracts.md](references/data-contracts.md). Comparer le grain, les contrôles et les montants par devise; ne pas transformer ces valeurs historiques en seuils métier permanents.

## Architecture Streamlit des sous-onglets

- Construire tous les sous-onglets avec `st.tabs` au premier chargement de Solution M-PESA afin qu'ils soient immédiatement disponibles après l'importation.
- Isoler chaque fonction de rendu avec `st.fragment`. Après le chargement initial, une interaction locale doit recalculer uniquement le sous-onglet concerné.
- Garder les téléversements et la préparation partagée en dehors des fragments : toute modification des fichiers sources déclenche volontairement une reconstruction complète des sous-onglets.
- Mettre en cache avec `st.cache_data` la lecture, la normalisation et les calculs déterministes lourds. Laisser les widgets et le rendu Streamlit hors du cache.
- Ne pas faire hacher les grands DataFrames préparés à chaque interaction. Utiliser une empreinte compacte du contenu des fichiers comme clé de préparation, puis ajouter la période, le client ou le filtre aux clés des rapports dérivés. Borner `max_entries` pour éviter une croissance mémoire sans limite.
- Pour G2/Turbo, agréger uniquement les `ref_no` réellement présents dans G2 et les retraits B2C candidats situés dans la fenêtre utile. Le filtrage de performance ne doit jamais élargir ni réduire la tolérance métier de 60 minutes.
- Conserver le contexte client dans `Extrait client`. Alimenter DAT, G2/DAT, crédits et diagnostics depuis les données globales préparées afin qu'un fragment ne dépende pas de l'état local d'un autre sous-onglet.
- Exiger Streamlit 1.59 ou une version ultérieure compatible avec les fragments écrivant dans les conteneurs `st.tabs` créés à l'extérieur du fragment.

## Norme visuelle commune des onglets

- Appliquer cette norme à tous les niveaux de navigation de Solution M-PESA : sous-onglets principaux, sous-sous-onglets de `Pilotage financier Turbo`, `Perfect_client`, `G2 / DAT` et tout futur bloc `st.tabs`.
- Conserver une barre d'onglets sobre et professionnelle, avec des espacements réguliers entre les libellés.
- Afficher l'onglet actif en bleu, avec des coins arrondis et un soulignement rouge.
- Appliquer un survol discret et rendre la navigation au clavier clairement visible avec `:focus-visible`.
- Permettre le défilement horizontal des onglets sur les petits écrans, sans retour à la ligne.
- Encapsuler chaque barre `st.tabs` dans un `st.container(key=...)` doté d'une clé CSS unique. Ne jamais créer directement un sous-sous-onglet avec `st.tabs` hors d'un conteneur ciblé.
- Appeler `inject_professional_tabs_css(container_key=...)`, puis `format_professional_tab_labels(...)`, afin de réutiliser la norme commune de `credit_app/ui.py`. Ne pas dupliquer ce CSS dans `solution_mpesa.py`.
- Choisir des clés stables et propres au contexte, par exemple `mpesa_solution_tabs`, `mpesa_turbo_financial_inner_tabs`, `mpesa_perfect_client_cohort_tabs` et `mpesa_g2_temporal_detail_tabs`, afin d'éviter les collisions et les débordements de style entre niveaux.
- Préserver le mode de calcul défini dans la section précédente : l'habillage visuel ne doit jamais transformer les onglets en calcul conditionnel limité au seul onglet sélectionné.

## Exports

- Générer uniquement les feuilles Excel demandées par le contexte; ne jamais ajouter automatiquement toutes les feuilles vides du module.
- Pour G2/DAT, conserver la synthèse, les comptages, le détail, les analyses temporelles et la fidélisation. Nommer les feuilles de contrôle `Statuts_G2`, `Anomalies_G2`, `G2_DAT` en mode G2 et `Statuts_Turbo`, `Anomalies_Turbo`, `Turbo_DAT` en mode Turbo seul.
- Garder le Word modifiable et ajouter en annexe le tableau unique `Transactions`, dans le même ordre que l'écran et en orientation paysage.
- Transmettre `rapport_journalier_pivot` au Word même lorsqu'il est exclu de l'Excel compact; reconstruire la synthèse par devise depuis le détail si le pivot manque.
- Répéter les en-têtes Word sur plusieurs pages et conserver toutes les lignes `Completed` du périmètre filtré; garder les autres statuts dans l'Excel de contrôle.
- Calculer la ligne `Activite` de la synthèse exécutive Word directement depuis le détail `Completed` filtré par date, heure et sens; ne jamais la reprendre du dernier mois de fidélisation.
- Vérifier qu'un export client reprend les filtres de l'extrait sans perdre les feuilles contextuelles du client.
- Pour le Word client, vérifier les trois sorties CDF, USD et ALL, les comptes 1441/15558, l'en-tête `Devise` et les synthèses multidevises séparées.
- Proposer le PDF client en CDF, USD et ALL avec le même périmètre filtré et les mêmes règles de séparation des devises que le Word. Générer le PDF nativement avec ReportLab afin de fonctionner sur Streamlit en ligne sans navigateur système.
- Dans les Word et PDF client, placer `DAT en cours` avant `Détail des transactions`, avec la date de situation Turbo, le `savings_id`, la durée, la souscription, l'échéance, les jours restants, la devise, le capital bloqué, le taux, l'intérêt estimé, capital + intérêt estimé et la situation. Ne plus afficher `Intérêts des DAT échus`.
- Dans les Word et PDF client, placer `Remboursements observés` avant `Détail des transactions`, avec la date, la référence Turbo, la devise, le montant payé, le principal remboursé, les intérêts, les pénalités et le mode observé. Ne pas afficher les décaissements ni une section crédit.
- Dans l'Excel client, utiliser `DAT_En_Cours` et `Remboursements_Turbo`; ne pas exporter `Interets_DAT_Echus`, `Credit_Client_Turbo`, `Positions_Turbo` ou `Credits`.
- Intégrer le logo officiel `skills/logo Bisou Bisou.PNG` dans les exports Word et PDF de l'Extrait client; conserver un libellé texte de repli si l'image est absente ou illisible.
- Nommer le Word Turbo seul `extrait_compte_<customer_id>_<telephone>_<devise>_<debut>_<fin>.docx`. Si G2 est chargé, insérer le nom G2 entre l'identifiant et le téléphone. Conserver les espaces du nom, supprimer uniquement les caractères interdits des noms de fichiers et ne jamais utiliser G2 pour recalculer les montants.
- Dans le Word client, retirer tous les suffixes `[Turbo]`. Si le solde d'ouverture n'est pas renseigné, conserver l'intitulé `Cumul net` mais ne plus imprimer l'ancien avertissement relatif au solde d'ouverture.
- Dans le Word client, ne pas inclure les tableaux `Synthese du comportement observe`, `Positions observees et rapprochement des soldes` et `Jalons du parcours financier`. Conserver obligatoirement `Detail des transactions`. Le pied de page porte `Solution Bisou Bisou Digital`.
- Dans le titre du Word client, omettre entièrement le segment du nom lorsque celui-ci est vide, `Non disponible` ou `Nom non disponible`; produire alors `Extrait de compte - <telephone> - <devise>` sans séparateur vide.
- Exporter les trois populations `Clients_Perfect` dans `Clients_Perfect_G2`, `Clients_Perfect_Turbo` et `Clients_Perfect_Turbo_G2`.
- Dans l'export `Pilotage financier Turbo`, n'inclure que les synthèses et listes d'action Turbo demandées : flux, remboursements, nouveaux crédits, encours/PAR, épargne, DAT, concentrations, alertes, contrôles et définitions. Ne produire aucune feuille de montant G2.
- Generer l'Excel du cockpit uniquement sur demande et limiter ses feuilles aux syntheses et listes d'action utiles.
- Pour `Comptabilité Turbo`, exporter uniquement les feuilles demandées parmi `Compta_Synthese_Turbo`, `Balance_Clients_Turbo`, `Positions_Clients_Turbo`, `Balance_Comptes_Turbo`, `Journal_Operations_Turbo`, `Journal_Ecritures_Turbo`, `Controles_Operations_Turbo`, `Controles_Soldes_Turbo`, `Flux_MPESA_Turbo`, `Produits_Financiers_Turbo`, `Positions_Portefeuille_Turbo` et `Controle_G2_Turbo`.

## Architecture à respecter

- Contrats : `credit_app/data_schema.py`
- Calculs, rapprochements et exports : `credit_app/services/mpesa_analysis.py`
- Interface : `credit_app/tabs/solution_mpesa.py`
- Tests : `tests/test_mpesa_analysis.py`

Placer les règles déterministes dans le service, le rendu dans l'onglet Streamlit et chaque nouveau cas métier dans les tests.

## Validation

Exécuter au minimum avec l'environnement Python du projet :

```powershell
& $PYTHON skills/solution-mpesa/scripts/inspect_mpesa_contracts.py
& $PYTHON -m pytest tests/test_mpesa_analysis.py -q
```

Pour un changement G2/DAT, Word ou PDF, tester aussi un fichier réel sans l'écrire dans le dépôt et vérifier le nombre de reçus, l'ordre des colonnes, les devises, les totaux, le logo et les anomalies. Vérifier également que chaque Excel contient seulement les feuilles prévues. Pour `Perfect_client`, vérifier les trois populations inclusives et leurs trois feuilles Excel avec un export 122 réel.

Pour un changement `Comptabilité Turbo`, tester la journée de référence du 16 juillet 2026 lorsqu'elle est disponible, vérifier les 12 feuilles comptables, le rapprochement G2 direct, la séparation CDF/USD et la concordance entre synthèse, balances, journaux et contrôles. Une opération non symétrique ou une variation de solde à revoir est un signal de contrôle; ne jamais la qualifier automatiquement d'erreur comptable.

Pour un changement `Pilotage financier Turbo`, tester également le 16 juillet 2026 : attendre 135 événements consolidés, 48 CDF et 87 USD; vérifier 284 910 CDF et 194,54 USD de remboursements observés, 122 200 CDF et 99 USD de nouveaux crédits décaissés, la séparation stricte des devises et l'absence totale des montants G2. Mesurer la consolidation et le rapprochement crédit-épargne sur les fichiers réels afin de prévenir toute régression de performance.
