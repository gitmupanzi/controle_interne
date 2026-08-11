# Perfect Vision — Requêtes prioritaires 9 et 10

Cette page expose les requêtes les plus importantes du catalogue `data/modelisation/requetes.sql`. Elle ne remplace pas le SQL : elle aide le lecteur métier, l’auditeur ou l’informaticien à comprendre rapidement quelle requête utiliser et pourquoi.

## Principe de lecture

- **Importance 10** : contrôle critique, reporting réglementaire, risque financier direct ou action opérationnelle prioritaire.
- **Importance 9** : contrôle important à suivre régulièrement, utile pour la qualité des données, la supervision ou la préparation du tableau de bord.
- Les montants doivent toujours rester séparés par devise. Une requête qui sort USD et CDF ne doit pas être lue comme un total monétaire unique.
- Une alerte ou une ligne retournée par une requête est un signal de revue. Elle ne prouve pas automatiquement une fraude ou une erreur ; il faut relire la pièce source et le contexte métier.

## Synthèse par cycle

| Cycle | Nombre de requêtes prioritaires | Lecture simple |
|---|---:|---|
| Opérations dépôt/retrait | 20 | Sécuriser la saisie, la validation, les annulations, les volumes et les comportements transactionnels. |
| Comptable et financier | 12 | Contrôler l’équilibre débit/crédit, le lien opération-comptabilité et les écritures journalières. |
| Épargne | 19 | Surveiller les comptes, les produits, les mouvements, les DAT, les dépôts fréquents et les soldes à risque. |
| CRM clients | 9 | Améliorer le référentiel client, le téléphone, les doublons, les comptes et la qualité KYC. |
| Money Provider | 5 | Contrôler les opérations mobiles/API et leur comptabilisation. |
| Crédit | 33 | Suivre demandes, octrois, encours, impayés, remboursements, garanties, échéances et opportunités liées à l’épargne. |
| Caisse et guichet | 4 | Suivre les arrêtés de caisse et la discipline de clôture journalière. |
| Trésorerie | 1 | Suivre les flux de trésorerie utiles au pilotage. |
| Ressources humaines | 1 | Produire un socle RH exploitable dans le tableau de bord. |
| Sécurité SI | 1 | Suivre les utilisateurs, profils et risques d’accès. |
| Sauvegarde et continuité | 1 | Donner un indicateur technique de continuité à compléter par les preuves externes. |
| Likelemba | 1 | Alimenter les analyses de tontine et groupes. |
| Conformité | 9 | Alimenter et justifier le reporting LBC-FT, les alertes, déclarations, profils de risque et sanctions. |
| Clients | 1 | Produire le socle client par devise pour les indicateurs transversaux. |
| **Total** | **117** | Requêtes de niveau 9 ou 10 extraites du catalogue. |

## Comment choisir une requête

| Besoin terrain | Famille à regarder en premier | Exemple de requête |
|---|---|---|
| Vérifier les opérations non validées, annulées ou doublonnées | Opérations dépôt/retrait | Q03 à Q11, Q23, Q36 à Q45 |
| Contrôler l’équilibre comptable | Comptable et financier | Q14, Q15, Q21, Q139, Q140 |
| Trouver les clients qui épargnent beaucoup ou régulièrement | Épargne | Q57, Q92, Q93, Q113 |
| Identifier les DAT sans crédit actif | Crédit / Épargne | Q144 |
| Suivre les crédits en retard, impayés ou à échéance | Crédit | Q91, Q96, Q100, Q143, Q145, Q146 |
| Préparer le reporting LBC-FT | Conformité | Q149, Q150, Q151, Q152, Q153, Q154, Q155, Q156, Q158 |
| Produire le socle Power BI Clients | Clients | Q157 |

## Catalogue prioritaire détaillé

### Opérations dépôt/retrait

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 3 | 9 | `03_cycle_operations_depot_retrait_operations_creees_mais_non_validees` | Lister les operations actives dont la validation est absente ou incomplete. | met en evidence les operations a regulariser ou a expliquer. | Hebdomadaire |
| 4 | 9 | `04_cycle_operations_depot_retrait_operations_saisies_apres_la_date_d_operation` | Detecter les operations enregistrees apres leur date effective. | un delai important peut signaler une saisie tardive ou un rattrapage manuel. | Hebdomadaire |
| 5 | 10 | `05_cycle_operations_depot_retrait_operations_validees_avant_la_saisie_ou_avant_la_date_d_operation` | Identifier les incoherences chronologiques entre operation, saisie et validation. | ces cas doivent etre verifies car ils peuvent reveler un probleme de workflow ou de donnees. | Hebdomadaire |
| 6 | 9 | `06_cycle_operations_depot_retrait_operations_sans_utilisateur_point_de_service_ou_type_operation` | Reperer les operations avec des champs de rattachement essentiels manquants. | ces absences limitent la tracabilite operationnelle et le reporting par agence/utilisateur. | Hebdomadaire |
| 7 | 9 | `07_cycle_operations_depot_retrait_doublons_de_numero_de_transaction_dans_operations` | Detecter les numeros de transaction utilises plusieurs fois dans le back-office. | chaque doublon doit etre rapproche du metier pour distinguer cas normal, reprise ou anomalie. | Hebdomadaire |
| 8 | 9 | `08_cycle_operations_depot_retrait_doublons_de_numero_de_recu_dans_operations` | Detecter les recus partages par plusieurs operations. | utile pour verifier l'unicite documentaire et les risques de double comptabilisation. | Hebdomadaire |
| 9 | 9 | `09_cycle_operations_depot_retrait_doublons_metier_potentiels_meme_date_utilisateur_type_reference_et_description` | Identifier les operations tres similaires pouvant correspondre a une double saisie. | le resultat doit etre examine operation par operation avec les justificatifs. | Hebdomadaire |
| 10 | 9 | `10_cycle_operations_depot_retrait_operations_annulees_sans_operation_annulee_referencee` | Lister les operations marquees annulees sans lien vers l'operation d'origine. | absence de reference = tracabilite d'annulation incomplete. | Hebdomadaire |
| 11 | 9 | `11_cycle_operations_depot_retrait_operations_referencees_comme_annulees_mais_introuvables` | Verifier que les references d'annulation pointent vers une operation existante. | les lignes retournees indiquent des liens rompus ou des donnees manquantes. | Hebdomadaire |
| 23 | 9 | `23_cycle_operations_depot_retrait_operations_saisies_et_validees_par_le_meme_utilisateur` | Detecter les cas d'auto-validation. | utile pour verifier la separation des taches et les habilitations. | Hebdomadaire |
| 36 | 9 | `36_cycle_operations_depot_retrait_liste_de_tous_les_depots_et_retraits_back_office_et_api_mobile` | Obtenir le detail unifie des depots/retraits toutes sources. | base de travail pour extraction Excel, controle LBC-FT et investigations transactionnelles. | Hebdomadaire |
| 38 | 9 | `38_cycle_operations_depot_retrait_synthese_excel_lbc_ft_depots_retraits_et_mobile_banking` | Produire une table directement exploitable pour certaines lignes du reporting BCC/LBC-FT. | renseigne section, ligne Excel, rubrique, devise, nombre, volume et commentaire. | Mensuel |
| 39 | 10 | `39_cycle_operations_depot_retrait_fractionnement_potentiel_plusieurs_mouvements_sous_seuil_mais_cumul_au_dessus_du_seuil` | Detecter les clients avec plusieurs operations sous seuil dont le cumul depasse le seuil journalier. | cas typique de surveillance LBC-FT sur contournement possible des seuils. | Hebdomadaire |
| 40 | 9 | `40_cycle_operations_depot_retrait_operations_inhabituelles_par_client_volume_periode_vs_moyenne_des_3_mois_precedents` | Comparer le volume de la periode avec l'historique recent du client. | les multiples eleves ou l'absence d'historique doivent etre investigues. | Hebdomadaire |
| 41 | 10 | `41_cycle_operations_depot_retrait_clients_avec_forte_activite_mais_donnees_kyc_incompletes_ou_atypiques` | Croiser volume transactionnel et qualite des donnees adherent. | priorise les dossiers KYC incomplets ayant une activite significative. | Hebdomadaire |
| 42 | 9 | `42_cycle_operations_depot_retrait_depots_et_retraits_agreges_par_client` | Calculer nombres et volumes de depots/retraits par adherent. | base pour profilage client et suivi commercial/risque. | Mensuel |
| 43 | 9 | `43_cycle_operations_depot_retrait_top_clients_par_volume_de_mouvements` | Afficher les 50 clients les plus actifs en montant sur la periode. | utile pour selectionner les dossiers a examiner en priorite. | Hebdomadaire |
| 44 | 9 | `44_cycle_operations_depot_retrait_analyse_detaillee_des_operations_annulees` | Lister les annulations avec utilisateur, validateur et references operationnelles. | facilite la revue des annulations et de leur justification. | Hebdomadaire |
| 45 | 9 | `45_cycle_operations_depot_retrait_utilisateurs_a_risque_volumes_annulations_saisies_tardives_et_auto_validation` | Identifier les utilisateurs dont l'activite presente des signaux de supervision. | combine volume, annulations, saisies tardives et separation des taches. | Hebdomadaire |
| 126 | 9 | `126_cycle_operations_depot_retrait_streamlit` | Produire un fichier transactionnel depots/retraits directement exploitable dans le cycle operations_depot_retrait. | une ligne represente une operation client back-office ou API mobile, avec client, compte, utilisateur, validation et equilibre comptable. | A chaque televersement du cycle operations depot/retrait |

### Comptable et financier

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 12 | 9 | `12_cycle_comptable_et_financier_hdpm_sans_operation_back_office_correspondante` | Detecter les ecritures comptables HDPM rattachees a une operation inexistante. | ces cas doivent etre expliques car ils cassent le lien operation-comptabilite. | Hebdomadaire |
| 13 | 9 | `13_cycle_comptable_et_financier_operations_back_office_sans_ecriture_hdpm` | Identifier les operations actives sans impact comptable retrouve dans HDPM. | utile pour verifier l'exhaustivite de la comptabilisation. | Hebdomadaire |
| 14 | 10 | `14_cycle_comptable_et_financier_equilibre_debit_credit_par_operation_dans_hdpm` | Controler que les ecritures back-office sont equilibrees entre debit et credit. | un ecart non nul signale une anomalie comptable potentielle. | Hebdomadaire |
| 15 | 10 | `15_cycle_comptable_et_financier_equilibre_debit_credit_par_operation_dans_hdpm_api` | Controler l'equilibre debit/credit des ecritures issues de l'API mobile. | chaque operation mobile devrait generalement avoir une paire debit/credit equilibree. | Hebdomadaire |
| 16 | 9 | `16_cycle_comptable_et_financier_lignes_hdpm_avec_montant_nul_negatif_ou_sens_absent` | Reperer les ecritures comptables dont les montants ou le sens sont invalides/incomplets. | ces lignes sont prioritaires pour controle de qualite des donnees comptables. | Hebdomadaire |
| 17 | 9 | `17_cycle_comptable_et_financier_ecritures_comptables_avec_date_valeur_differente_de_la_date_operation` | Lister les ecritures dont la date valeur differe de la date d'operation. | un ecart important peut etre normal mais doit etre justifie selon la procedure. | Hebdomadaire |
| 18 | 9 | `18_cycle_comptable_et_financier_mouvements_hdpm_sans_compte_ou_avec_compte_inexistant` | Verifier le rattachement de chaque ecriture a un compte existant. | les lignes retournees indiquent un probleme de referentiel compte. | Hebdomadaire |
| 20 | 9 | `20_cycle_comptable_et_financier_rapprochement_operations_vs_operations_api_par_num_transaction` | Comparer les operations back-office et API sur les references communes. | signale les absences ou differences de date, recu, point de service ou type operation. | Hebdomadaire |
| 21 | 10 | `21_cycle_comptable_et_financier_rapprochement_des_totaux_hdpm_vs_hdpm_api_par_reference_operation` | Comparer les volumes et montants comptables entre HDPM et HDPM_API. | met en evidence les operations presentes dans une source mais pas l'autre ou avec ecarts. | Hebdomadaire |
| 129 | 9 | `129_cycle_comptable_et_financier_streamlit` | Produire un journal comptable detaille pour les analyses du cycle comptable. | une ligne represente une ecriture HDPM/HDPM_API avec debit, credit, journal, compte et point de service. | A chaque televersement du cycle comptable et financier |
| 139 | 10 | `139_cycle_comptable_et_financier_annulations_non_symetriques_dans_les_mouvements_comptables` | Verifier qu'une operation d'annulation inverse exactement les mouvements comptables de l'operation initiale. | compare les lignes de la CTE locale mouvements_comptables pour l'operation annulee et l'operation d'annulation, par compte et devise. | Hebdomadaire |
| 140 | 10 | `140_cycle_comptable_et_financier_equilibre_comptable_journalier_par_devise_et_journal` | Verifier chaque jour que le total debit egale le total credit par devise et journal. | complete les controles par operation en donnant une vue de cloture quotidienne adaptee a une institution avec une seule agence. | Quotidien a la cloture, avec synthese mensuelle |

### Épargne

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 19 | 9 | `19_cycle_epargne_mouvements_sur_comptes_clotures_inactifs_selon_etat` | Detecter les mouvements passes sur des comptes dont l'etat n'est pas actif/ouvert. | ces mouvements doivent etre justifies ou corriges selon le statut du compte. | Hebdomadaire |
| 49 | 9 | `49_cycle_epargne_produits_d_epargne_inactifs_encore_utilises_par_des_comptes` | Identifier les comptes encore rattaches a des produits d'epargne inactifs. | ces comptes doivent etre verifies pour confirmer si le produit devait encore etre exploite ou etre cloture/migre. | Hebdomadaire |
| 50 | 9 | `50_cycle_epargne_produits_d_epargne_non_valides_encore_utilises_par_des_comptes` | Reperer les comptes rattaches a des produits non valides. | utile pour la regularisation des parametres produits et le nettoyage du portefeuille epargne. | Hebdomadaire |
| 51 | 9 | `51_cycle_epargne_produits_sans_depot_retrait_autorise_mais_avec_mouvements_sur_les_comptes` | Controler la coherence entre les regles produit et les mouvements observes. | dans cette lecture, un mouvement crediteur sur un compte client est assimile a un depot et un mouvement debiteur a un retrait. | Hebdomadaire |
| 52 | 9 | `52_cycle_epargne_incoherences_entre_devise_du_produit_du_compte_et_du_mouvement` | Detecter les differences de devise susceptibles de fausser les traitements epargne. | une incoherence doit etre analysee selon la regle metier du produit, du compte et du mouvement comptable. | Hebdomadaire |
| 53 | 9 | `53_cycle_epargne_comptes_rattaches_a_un_produit_epargne_inexistant_ou_invalide` | Lister les comptes sans produit reference ou lies a un produit non exploitable. | ces cas perturbent la supervision du portefeuille et doivent etre regularises en priorite. | Hebdomadaire |
| 54 | 9 | `54_cycle_epargne_mouvements_hdpm_view_sans_compte_avec_compte_inexistant_ou_sans_operation_rattachee` | Controler les references minimales des mouvements. | cette requete unifie directement HDPM et HDPM_API dans une CTE locale. | Hebdomadaire |
| 55 | 10 | `55_cycle_epargne_mouvements_avec_montant_nul_negatif_ou_superieur_au_seuil_de_revue` | Isoler les montants qui meritent une verification prioritaire. | le seuil eleve s'appuie sur l'equivalent CDF de 10 000 USD calcule avec @taux_usd_cdf. | Hebdomadaire |
| 56 | 9 | `56_cycle_epargne_depots_et_retraits_par_client_compte_agence_devise_et_produit` | Produire une lecture consolidee de l'activite epargne sur la periode. | les credits sur compte client sont lus comme depots et les debits comme retraits/sorties. | Hebdomadaire |
| 57 | 10 | `57_cycle_epargne_analyse_des_gros_mouvements_par_periode` | Suivre les mouvements superieurs au seuil de revue par mois, agence et devise. | utile pour la supervision LBC-FT, le pilotage des pics d'activite et la revue des operations sensibles. | Hebdomadaire |
| 92 | 10 | `92_cycle_epargne_clients_avec_depots_frequents_par_semaine_sur_la_periode` | Identifier les clients qui effectuent des depots 3 a 5 fois par semaine ou plus. | une operation de depot est comptee une seule fois par client et par operation. Les lignes non rattachees a COMPTES_ADHERENT sont exclues pour eviter les contreparties caisse/banque. | Hebdomadaire |
| 93 | 10 | `93_cycle_epargne_clients_avec_depots_par_tranche_usd_cdf_sur_la_periode` | Reperer les clients qui effectuent des depots dans les tranches de montant sensibles definies pour USD et CDF. | USD est classe en 10-24.99, 25-49.99, 50-99.99, 100 et plus. CDF est classe en 125000-199999 et 200000 et plus. Les depots inferieurs aux seuils ne sortent pas. | Hebdomadaire |
| 103 | 10 | `103_cycle_epargne_dashboard_epargne_solde_et_comptes_par_mois_produit_et_agence` | Alimenter les courbes de solde epargne, nombre de comptes et solde moyen par produit/agence. | calcule le solde comptable a chaque fin de mois avec la CTE locale mouvements_comptables. Les comptes clotures avant la date de situation mensuelle sont exclus. | Mensuel |
| 110 | 9 | `110_cycle_epargne_comptes_epargne_inactifs_ou_dormants_avec_solde_a_la_date_de_fin` | Identifier les comptes epargne sans mouvement recent afin d'anticiper les actions commerciales, le suivi des comptes dormants et le risque de reclamation. | calcule le dernier mouvement et le solde a @date_fin avec la CTE locale mouvements_comptables. Le seuil retenu ici est 12 mois sans mouvement; il peut etre ajuste dans DATEADD. | Hebdomadaire pour surveillance, mensuel pour reporting epargne |
| 113 | 9 | `113_cycle_epargne_activite_epargne_par_client_produit_et_agence_sur_la_periode` | Mesurer les depots, retraits, activite nette et nombre de mouvements epargne pour alimenter les decisions commerciales. | exploite la CTE locale mouvements_comptables sur les comptes epargne et separe les credits comptables des debits comptables. | Hebdomadaire |
| 124 | 9 | `124_cycle_epargne_streamlit` | Produire un fichier compte/mouvement pour alimenter les analyses du cycle epargne dans Streamlit. | une ligne represente un compte epargne et, s'il existe, un mouvement de la periode; les comptes sans mouvement restent visibles avec date_operation nulle. | A chaque televersement du cycle epargne |
| 137 | 10 | `137_cycle_epargne_depots_et_retraits_epargne_avec_sens_comptable_incoherent` | Verifier que les depots creditent le compte client et que les retraits le debitent dans les mouvements comptables. | rapproche OPERATIONS_EPG avec la CTE locale mouvements_comptables sur le compte client. En microfinance, une mauvaise orientation debit/credit fausse directement le solde du membre. | Hebdomadaire |
| 138 | 10 | `138_cycle_epargne_comptes_epargne_avec_solde_negatif_apres_mouvement_debit` | Detecter les retraits ou debits qui font passer un compte epargne client en solde negatif. | reconstruit le solde avant periode puis applique les mouvements de la CTE locale mouvements_comptables dans l'ordre chronologique. Sauf autorisation de decouvert, un solde negatif est un risque client et caisse. | Hebdomadaire |
| 141 | 10 | `141_cycle_epargne_mouvements_sur_comptes_clotures_bloques_ou_inactifs` | Identifier les mouvements passes sur des comptes clients qui ne devraient plus recevoir d'operations courantes. | renforce le controle des comptes clotures/inactifs en ajoutant client, produit, sens, montant et motif de risque pour faciliter la regularisation. | Hebdomadaire |

### CRM clients

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 24 | 9 | `24_cycle_crm_clients_adherents_inscrits_en_doublon_par_code` | Verifier l'unicite du code adherent. | les doublons peuvent perturber le KYC, les comptes et les reportings clients. | Hebdomadaire |
| 25 | 9 | `25_cycle_crm_clients_adherents_sans_informations_essentielles` | Reperer les fiches adherents incompletes sur les champs de base. | sert au nettoyage KYC et a l'amelioration de la qualite du referentiel client. | Hebdomadaire |
| 26 | 9 | `26_cycle_crm_clients_adherents_non_valides_ou_droit_d_adhesion_non_paye` | Identifier les adherents non valides ou dont le droit d'adhesion n'est pas paye. | a rapprocher avec les ouvertures de comptes et l'activite transactionnelle. | Hebdomadaire |
| 28 | 9 | `28_cycle_crm_clients_adherents_sans_compte_adherent_ou_avec_compte_adherent_introuvable` | Verifier l'existence et l'appartenance du compte principal indique dans ADHERENTS. | un compte existant mais rattache a un autre adherent dans COMPTES_ADHERENT est aussi une anomalie. | Hebdomadaire |
| 90 | 9 | `90_cycle_crm_clients_liste_des_clients_avec_leurs_comptes_et_devises` | Obtenir le portefeuille client-compte avec les informations de devise et d'agence. | une ligne correspond a un compte rattache a un client. Renseigner @id_devise_reporting pour limiter a une devise. | Hebdomadaire si extraction terrain, sinon mensuel |
| 121 | 9 | `121_cycle_crm_clients_departs_et_retours_clients_avec_exposition_epargne_credit` | Mesurer l'impact des departs clients sur les soldes epargne et les credits actifs afin de prioriser les actions de retention ou de recouvrement. | combine DEPARTS_ADHERENT avec les soldes epargne de la CTE locale mouvements_comptables et les encours credit actifs a @date_fin. | Mensuel, avec revue hebdomadaire des cas sensibles |
| 122 | 10 | `122_cycle_crm_clients_controle_qualite_des_numeros_de_telephone_clients` | Identifier les telephones vides, non normalises, incomplets ou correspondant au numero staff. | extrait uniquement les chiffres du telephone client, normalise au format RDC 243XXXXXXXXX, puis classe chaque numero selon son statut. | Mensuel, et avant campagne KYC/conformite |
| 125 | 9 | `125_cycle_crm_clients_streamlit` | Produire un fichier client complet pour les analyses CRM, KYC, segmentation et qualite de donnees. | une ligne represente un client Perfect, enrichi par la derniere activite epargne/credit visible avant @date_fin. | A chaque televersement du cycle CRM clients |
| 148 | 10 | `148_cycle_crm_clients_liste_unique_des_clients_avec_telephone_et_nombre_de_comptes` | Restituer exactement une ligne par client avec ses coordonnees et le nombre de comptes qui lui sont rattaches. | la CTE locale base_clients est dedupliquee par id_client avant la jointure. Les comptes sont comptes distinctement dans COMPTES_ADHERENT. | Hebdomadaire |

### Money Provider

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 31 | 9 | `31_cycle_money_provider_operations_api_sans_ecritures_hdpm_api_rattachees` | Verifier que chaque operation API active a des ecritures comptables API. | absence d'ecriture = anomalie d'integration ou de comptabilisation potentielle. | Hebdomadaire |
| 32 | 10 | `32_cycle_money_provider_operations_api_mobiles_sans_paire_debit_credit_equilibree_dans_hdpm_api` | Controler que les operations mobiles ont une paire debit/credit coherente. | signale les mobiles incomplets, desequilibres ou mal rattaches. | Hebdomadaire |
| 33 | 9 | `33_cycle_money_provider_operations_api_annulees_et_leurs_ecritures_hdpm_api` | Documenter les operations API annulees avec leur impact comptable. | facilite la revue des annulations mobile banking. | Hebdomadaire |
| 119 | 9 | `119_cycle_money_provider_operations_money_provider_et_commissions_sur_la_periode` | Suivre les depots, retraits, transferts et commissions Money Provider afin de piloter le canal mobile et ses revenus. | consolide OPERATIONS_MOB_WS et MOB_OPERATIONS; les comptes client sont rattaches a la CTE locale base_epargnes quand ID_COMPTE_EPG est disponible. | Mensuel |
| 134 | 9 | `134_cycle_money_provider_streamlit` | Produire un fichier transactionnel Money Provider pour les analyses du cycle money_provider. | une ligne represente une operation mobile issue de OPERATIONS_MOB_WS ou MOB_OPERATIONS, enrichie avec agent, client et compte lorsque disponibles. | A chaque televersement du cycle Money Provider |

### Crédit

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 68 | 9 | `68_cycle_credit_anomalies_a_prioriser_pour_audit` | Produire une synthese courte des principaux signaux d'alerte. | ce tableau sert de point d'entree pour prioriser les revues d'audit et de supervision. | Hebdomadaire |
| 69 | 10 | `69_cycle_credit_prets_decaisses_sans_validation_prealable_exploitable` | Verifier qu'un pret a bien fait l'objet d'une validation exploitable avant deboursement. | signale les prets sans validation, sans validation favorable ou avec validation enregistree apres deboursement. | Hebdomadaire |
| 71 | 10 | `71_cycle_credit_caution_financiere_insuffisante_par_rapport_au_dossier` | Rapprocher la caution constatee, le taux attendu et le minimum parametre. | signale les prets dont la caution financiere reste absente ou insuffisante. | Hebdomadaire |
| 72 | 10 | `72_cycle_credit_garanties_sans_garant_identifiable_ou_sans_piece_exploitable` | Reperer les garanties rattachees a un dossier mais sans garant correctement documente. | permet de cibler les dossiers dont la garantie existe sur le papier mais reste fragile juridiquement. | Hebdomadaire |
| 73 | 10 | `73_cycle_credit_dossiers_avec_analyse_obligatoire_absente_ou_inachevee` | Verifier l'existence des analyses de revenu et de projet quand la tranche les exige. | tres utile pour les controles d'octroi et la revue de la qualite documentaire. | Hebdomadaire |
| 85 | 10 | `85_cycle_credit_clients_qui_terminent_leur_credit_par_mois_ou_sur_la_periode` | Suivre la fidÃ©lisation et les clÃ´tures effectives de prÃªts sur une pÃ©riode donnÃ©e. | un prÃªt terminÃ© est ici un prÃªt avec DATE_SOLDE renseignÃ©e. Le rÃ©sultat aide Ã suivre les clients qui bouclent un cycle et peuvent revenir dans le pipeline, avec une lecture mensuelle, par devise et par agence. | Mensuel, avant les actions de renouvellement |
| 91 | 10 | `91_cycle_credit_credits_en_cours_ou_termines_avec_echeances_impayees_sur_la_periode` | Lister les prets dont au moins une echeance attendue sur la periode n'est pas totalement remboursee. | compare TABAMOR (attendu) avec REMBOURS_CRD (remboursements rattaches a l'echeance, valides jusqu'a @date_fin). Le statut distingue les prets encore en cours et ceux deja soldes dans le SIG. | Hebdomadaire |
| 94 | 10 | `94_cycle_credit_decalage_transfert_d_echeance_et_reechelonnement_de_credit` | Lister les demandes de reechelonnement sur la periode et comparer la date validee avec PRETS.DATE_REECH. | dr.DATE_VALIDATION represente la validation de la demande; PRETS.DATE_REECH represente la date appliquee sur le pret; un ecart signale un decalage a justifier. | Hebdomadaire |
| 95 | 10 | `95_cycle_credit_credits_en_cours_ou_termines_avec_echeances_sans_impayees_sur_la_periode` | Lister les prets dont les echeances attendues sur la periode sont totalement remboursees. | compare TABAMOR (attendu) avec REMBOURS_CRD (remboursements rattaches a l'echeance, valides jusqu'a @date_fin). Le pret est retenu seulement si chaque echeance de la periode est totalement couverte. | Mensuel |
| 96 | 10 | `96_cycle_credit_dashboard_par_details_credit_a_la_date_de_fin` | Produire le dataset detaille des prets actifs pour les pages PAR, provision et top encours du dashboard. | calcule l'encours depuis OPERATIONS_CRD, le retard depuis TABAMOR/REMBOURS_CRD et la provision depuis PROVISIONS_CRD a @date_fin. Les colonnes PAR ventilent l'encours selon l'anciennete du retard. | Mensuel, avec revue hebdomadaire si le PAR se degrade |
| 97 | 10 | `97_cycle_credit_dashboard_synthese_par_et_provision_par_produit_et_agence` | Alimenter les cartes et graphes PAR1, PAR30, PAR90, provision et encours par produit/agence. | reprend la logique de la requete 96 puis agrege les encours et les tranches de retard. Les taux PAR sont calcules sur l'encours actif a @date_fin. | Mensuel, a la cloture du portefeuille credit |
| 98 | 10 | `98_cycle_credit_dashboard_top_encours_credits_par_client` | Identifier les plus fortes expositions individuelles pour les visuels Top encours et concentration du portefeuille. | l'encours vient des mouvements OPERATIONS_CRD valides jusqu'a @date_fin; le resultat garde les prets actifs et les classe par encours decroissant. | Mensuel, avec revue hebdomadaire des grands risques |
| 99 | 10 | `99_cycle_credit_dashboard_decaissements_mensuels_par_agence_et_produit` | Suivre le volume et le nombre de prÃªts decaisses par mois, agence, produit et type de client. | utilise PRETS.DATE_DECAISSEMENT si disponible, sinon PRETS.DATE_EFFET. Le montant vient du pret/cycle selon la CTE locale base_credits. | Mensuel |
| 100 | 10 | `100_cycle_credit_dashboard_echeances_futures_des_prets_en_cours` | Produire le calendrier des maturites et remboursements attendus dans les douze mois suivant @date_fin. | les Ã©chÃ©ances viennent de TABAMOR pour les prÃªts actifs a @date_fin. Le montant attendu additionne capital, interet, commission et epargne planifies. | Hebdomadaire pour relance, mensuel pour previsions |
| 101 | 10 | `101_cycle_credit_dashboard_retention_et_renouvellement_mensuel` | Mesurer la retention globale et la retention a 90 jours des clients dont un prÃªt arrive a solde. | un client est retenu s'il obtient un nouveau prÃªt apres DATE_SOLDE; la retention90Days limite ce nouveau prÃªt aux 90 jours suivant le solde. | Mensuel |
| 102 | 10 | `102_cycle_credit_dashboard_vintage_par_par_cohorte_de_decaissement` | Suivre la qualite des cohortes de prÃªts decaisses et leur exposition PAR a @date_fin. | la cohorte correspond au mois de dÃ©caissement. Le rÃ©sultat donne l'age de la cohorte en mois, l'encours restant et les montants PAR30/PAR90 observÃ©s a @date_fin. | Mensuel |
| 104 | 10 | `104_cycle_credit_dashboard_par_par_tranche_de_montant_initial_du_credit` | Alimenter les visuels PAR par intervalle de montant initial et comparer le risque selon la taille du credit. | classe les prÃªts actifs a @date_fin par tranches de montant initial puis calcule PAR1, PAR30 et PAR90 sur l'encours. | Mensuel |
| 105 | 10 | `105_cycle_credit_dashboard_concentration_top_10_pourcent_des_encours` | Mesurer la concentration du portefeuille sur les plus gros encours par agence, produit et devise. | classe les prÃªts actifs par encours decroissant dans chaque groupe agence/produit/devise et isole le premier decile pour calculer sa part dans l'encours. | Mensuel |
| 106 | 10 | `106_cycle_credit_dashboard_couverture_credit_par_epargne_et_garanties` | Rapprocher l'encours et les arrieres credit avec l'epargne, les cautions et les garanties disponibles. | l'epargne client provient des soldes de la CTE locale mouvements_comptables a @date_fin; les cautions et garanties sont rattachees au pret ou a la demande de credit. | Mensuel, ou avant comite credit important |
| 107 | 10 | `107_cycle_credit_dashboard_provision_trois_derniers_mois_par_client_agence_produit` | Reproduire les visuels de provision par client, branche, produit et tranche de montant sur les trois derniers mois. | calcule le solde de provision par prÃªt a chaque fin de mois, sur les trois fins de mois jusqu'a @date_fin. | Mensuel, a la cloture du portefeuille credit |
| 108 | 10 | `108_cycle_credit_dashboard_duree_et_echeances_restantes_des_prets_actifs` | Alimenter les graphes sur la duree moyenne, le nombre total d'echeances et les echeances restantes. | le total d'echeances vient de TABAMOR; les echeances restantes sont celles dont DATE_ECHEANCE est posterieure a @date_fin pour les prÃªts actifs. | Mensuel |
| 109 | 10 | `109_cycle_credit_dashboard_tendance_mensuelle_par_et_encours` | Produire l'historique mensuel des encours, PAR1, PAR30 et PAR90 pour les courbes du dashboard. | reconstruit les situations mensuelles entre @date_debut et @date_fin avec les mouvements credit valides et les echeances attendues/remboursees a chaque fin de mois. | Mensuel |
| 114 | 9 | `114_cycle_credit_pipeline_credit_et_delais_instruction_decision_decaissement` | Suivre les demandes de credit, les montants sollicites/accordes et les delais de traitement pour ameliorer la productivite et reduire les ruptures de parcours client. | rapproche DEMANDES_CREDIT, DOSSIERS_CREDIT et PRETS; les delais sont calcules entre reception, decision et decaissement. | a la demande |
| 115 | 9 | `115_cycle_credit_credits_decaisses_avec_faible_activite_epargne_avant_octroi` | Controler si les clients decaisses avaient une activite epargne minimale avant l'octroi, utile pour l'analyse de comportement et de capacite d'epargne. | compte les mouvements epargne des 6 mois precedant le decaissement; les dossiers avec moins de 3 mouvements sont signales. | Hebdomadaire |
| 116 | 10 | `116_cycle_credit_couverture_caution_et_garanties_par_rapport_au_credit_accorde` | Comparer la caution financiere, l'epargne obligatoire et les garanties avec le montant du credit pour detecter les dossiers insuffisamment couverts. | rapproche les champs de DOSSIERS_CREDIT, les CAUTIONS et les GARANTIES; le statut signale les ecarts par rapport au taux ou montant attendu. | Hebdomadaire |
| 123 | 9 | `123_cycle_credit_streamlit` | Produire un fichier large par pret/dossier pour alimenter les analyses du cycle credit dans Streamlit. | une ligne represente le dernier cycle connu du pret, enrichi avec client, produit, agence, encours estime, echeances dues et statut de remboursement. | A chaque televersement du cycle credit |
| 136 | 10 | `136_cycle_credit_remboursements_credit_encaisses_mais_non_imputes_correctement_au_pret` | Identifier les remboursements credit visibles dans OPERATIONS_CRD mais absents, incomplets ou incoherents dans la ventilation REMBOURS_CRD. | en microfinance, ce controle protege le client et le portefeuille credit. Un remboursement encaisse mais mal impute peut laisser le client en retard, fausser le PAR et provoquer un suivi de recouvrement injustifie. | Hebdomadaire |
| 142 | 10 | `142_cycle_credit_credits_decaisses_sans_mouvement_comptable_coherent` | Verifier que chaque decaissement de credit dispose d'une ecriture comptable coherente sur le compte credit et d'une contrepartie. | un decaissement augmente l'encours du pret dans OPERATIONS_CRD. Le controle rapproche le mouvement credit avec la CTE locale mouvements_comptables. | Hebdomadaire |
| 143 | 10 | `143_cycle_credit_remboursements_credit_recus_apres_echeance_a_suivre_pour_par` | Lister les remboursements effectues apres la date d'echeance afin de controler la discipline de remboursement et l'impact PAR. | rapproche REMBOURS_CRD, TABAMOR et OPERATIONS_CRD. Un paiement tardif peut etre regularise comptablement, mais il reste important pour le suivi risque et l'analyse du comportement client. | Hebdomadaire |
| 144 | 10 | `144_cycle_credit_clients_avec_dat_sans_credits_en_cours` | Identifier les clients disposant d'un depot a terme actif ou non cloture a la date de situation, mais sans credit en cours avec encours positif. | le DAT provient de DOSSIERS_DAT et CYCLES_DAT, avec solde calcule depuis OPERATIONS_DAT a @date_fin; les credits en cours utilisent la CTE locale base_credits. | Hebdomadaire pour opportunites terrain, mensuel pour pilotage |
| 145 | 10 | `145_cycle_credit_liste_detaillee_des_prets_avec_impayes` | Restituer une ligne par pret ayant au moins une echeance echue et non totalement remboursee a @date_fin. | l'impaye correspond au reste planifie dans TABAMOR apres deduction des remboursements valides. Le solde du compte de remboursement vient de la CTE locale mouvements_comptables. | Hebdomadaire pour recouvrement, et a chaque date de situation |
| 146 | 10 | `146_cycle_credit_liste_detaillee_des_clients_avec_echeances_sur_la_periode` | Restituer une ligne par client, pret et echeance comprise entre @date_debut et @date_fin. | le solde est le reste a payer de l'echeance a @date_fin. Le total de l'echeance comprend capital, interet, commission et epargne planifies. | Hebdomadaire pour relance, mensuel pour previsions |
| 147 | 10 | `147_cycle_credit_comptes_ordinaires_et_disponibilites_clients` | Rapprocher les prets cibles avec les comptes courants ou d'epargne ordinaires du client, en conservant la devise propre a chaque compte. | une ligne represente un pret et un compte ordinaire (type DAV). Le solde comptable est calcule dans la devise du compte a @date_fin. Le montant disponible est une estimation positive du solde comptable; la colonne convertie applique @taux_usd_cdf vers la devise du credit sans effectuer de compensation comptable. | Hebdomadaire pour recouvrement et compensation a analyser |

### Caisse et guichet

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 117 | 10 | `117_cycle_caisse_et_guichet_arretes_de_caisse_et_ecarts_de_billetage_sur_la_periode` | Suivre les controles quotidiens de caisse, les soldes declares et les ecarts entre solde d'arrete et billetage. | compare ARRETES_CAISSE.SOLDE avec le total NBRE_PIECE * PIECE de ARRETES_CAISSE_DET. | Quotidien, avec synthese hebdomadaire ou mensuelle |
| 118 | 9 | `118_cycle_caisse_et_guichet_mouvements_de_caisse_par_caisse_agence_devise_et_type_operation` | Suivre les entrees, sorties, transferts et volumes de caisse pour piloter la liquidite par agence. | unifie directement les operations de caisse back-office et API dans une CTE locale, puis agrege par mois/caisse/type operation. | Mensuel |
| 127 | 9 | `127_cycle_caisse_et_guichet_streamlit` | Produire un fichier operationnel de caisse pour les analyses du cycle caisse. | une ligne represente un mouvement de caisse avec caisse, agence, caissier, encaisse de fin de jour et ecart de billetage lorsqu'il existe. | A chaque televersement du cycle caisse et guichet |
| 135 | 10 | `135_cycle_caisse_et_guichet_caisses_sans_arrete_quotidien_sur_la_periode` | Verifier que chaque caisse agence/devise dispose d'un arrete journalier sur la periode, en priorisant les caisses qui ont eu des mouvements. | construit le calendrier entre @date_debut et @date_fin, croise avec les caisses agence, puis signale les jours sans ARRETES_CAISSE. Les mouvements de la CTE locale operations_caisse_unifiees donnent la criticite du manquement. | Quotidien en caisse, avec synthese hebdomadaire |

### Trésorerie

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 128 | 9 | `128_cycle_tresorerie_et_banque_streamlit` | Produire un fichier de mouvements de tresorerie/banque exploitable dans Streamlit. | s'appuie sur la CTE locale mouvements_comptables et les comptes dont le numero ou le libelle evoque banque, tresorerie ou caisse; ajuster le filtre selon le plan comptable local. | A chaque televersement du cycle tresorerie et banque |

### Ressources humaines

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 130 | 9 | `130_cycle_ressources_humaines_et_administration_streamlit` | Produire un fichier RH de base pour suivre effectifs, entrees, departs et rattachements. | une ligne represente un employe; le salaire reste nul si la paie n'est pas rattachee de facon fiable dans Perfect Vision. | A chaque televersement du cycle ressources humaines |

### Sécurité SI

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 131 | 9 | `131_cycle_securite_systeme_information_streamlit` | Produire un fichier utilisateurs/profils pour les analyses de securite SI. | une ligne represente un utilisateur et son profil/domaine lorsqu'il est renseigne; verifier les comptes actifs, expires, verrouilles ou sans profil. | A chaque televersement du cycle securite SI |

### Sauvegarde et continuité

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 132 | 9 | `132_cycle_sauvegarde_et_continuite_activite_streamlit` | Produire un fichier proxy de continuite a partir des executions batch connues dans Perfect Vision. | Perfect Vision ne contient pas toujours les journaux de sauvegarde; ce SELECT exploite BATCH_JOB_EXECUTION comme indicateur technique a completer par les preuves de sauvegarde externes. | A chaque televersement du cycle sauvegarde et continuite |

### Likelemba

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 133 | 9 | `133_cycle_likelemba_streamlit` | Produire un fichier consolide Likelemba/Tontine et credits Likelemba pour analyses de groupe, discipline de cycle et activite de collecte. | combine les credits dont le produit evoque Likelemba avec les cycles tontine; les colonnes non applicables sont laissees nulles. | A chaque televersement du cycle Likelemba |

### Conformité

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 149 | 10 | `149_cycle_conformite_reporting_lbc_ft` | Alimenter les rubriques automatisees du reporting BCC LBC-FT a partir des tables sources reelles. | une ligne par rubrique Excel et par devise lorsque la rubrique est monetaire. | Mensuel et a chaque reporting LBC-FT Parametres obligatoires : - @date_debut et @date_fin : periode inclusive du reporting ; - @id_devise_reporting : 1 devise precise, ou NULL pour toutes les devises disponibles ; - @taux_usd_cdf : taux retenu pour deriver automatiquement les equivalents CDF des seuils 5k/10k USD. |
| 150 | 10 | `150_cycle_conformite_alertes_lbc_ft_detaillees` | Fournir la piste d audit des alertes generees, traitees et en attente sur la periode. | une ligne par alerte LAB avec client, operation, montant, devise, profil et etat. | Hebdomadaire, voire quotidien si alertes sensibles |
| 151 | 10 | `151_cycle_conformite_declarations_soupcon_centif` | Inventorier les declarations reglementaires sans additionner les deux formulaires. | une ligne par declaration, avec source explicite pour controler les doubles saisies. | Hebdomadaire pour suivi conformite, mensuel pour reporting |
| 152 | 10 | `152_cycle_conformite_clients_profils_risque` | Fournir la population actuelle des clients profiles par le module LAB. | une ligne par affectation client/profil ; aucune date de reclassement n existe dans cette table. | Hebdomadaire pour surveillance renforcee, mensuel pour comite conformite |
| 153 | 10 | `153_cycle_conformite_referentiel_listes_sanctions` | Controler la presence et l identifiabilite des personnes inscrites dans les blacklists. | une ligne par entree de liste ; ce resultat ne prouve ni screening, ni gel, ni refus. | Mensuel, et apres toute mise a jour de liste de sanctions |
| 154 | 10 | `154_cycle_conformite_comptes_dormants_reactives` | Justifier la ligne 149 du reporting avec la piste d audit compte/operation. | une ligne par reactivation, avec dates de cloture/reouverture, compte, montant et devise. | Hebdomadaire pour reactivations, mensuel pour reporting LBC-FT |
| 155 | 10 | `155_cycle_conformite_qualite_donnees_lbc_ft` | Mesurer les lacunes qui peuvent fausser le reporting ou empecher le traitement des alertes. | une ligne par controle, avec volume d anomalies, severite et action recommandee. | Mensuel, avant validation du reporting LBC-FT |
| 156 | 10 | `156_cycle_conformite_lbc_ft_socle_unique_analyses_38_39_48_57_149_155` | Produire un seul fichier a televerser dans l'application pour couvrir la synthese des flux, le fractionnement, les trous de couverture, les gros mouvements, le reporting, les alertes, declarations, profils de risque, sanctions, comptes reactives et controles qualite LBC-FT. | une ligne par element de controle, avec analyse_source pour distinguer les blocs 38, 39, 48, 57 et 149 a 155. | Mensuel et a chaque televersement du cycle conformite |
| 158 | 10 | `158_cycle_conformite_detail_credits_reporting_lbc_ft` | Fournir la liste complete des credits qui alimentent les lignes 15 a 24 du canevas REPORTING_FIN_MENSUEL DES IMF ACTUALISE JUIN 2026.xlsx. | une ligne par credit et par rubrique du canevas. Le meme credit peut apparaitre plusieurs fois s'il satisfait plusieurs classifications. La ligne 15 reprend tous les credits avec encours positif a @date_fin. | Mensuel et a chaque reporting LBC-FT |

### Clients

| N° | Importance | Export | Ce que la requête permet de voir | Lecture simple | Périodicité |
|---:|---:|---|---|---|---|
| 157 | 10 | `157_cycle_clients_socle_indicateurs_par_client_et_devise` | Alimenter une feuille Power BI Clients avec une ligne par client et par devise utile. | - client actif = adherent Perfect valide, non parti a @date_fin et avec au moins un compte ouvert; - compte dormant = compte ouvert sans mouvement depuis au moins 24 mois, selon la logique de la requete 110; - credit a rembourser = echeance TABAMOR comprise entre @date_debut et @date_fin; - interet de credit = interet que le client doit payer sur les echeances de la periode; - interet epargne credite = interet effectivement credite au client sur epargne ou DAT pendant la periode; - DAT a echeance = cycle DAT dont DATE_FIN est comprise dans la periode. La requete est autonome et ne depend d aucune vue ni d une autre requete du catalogue. Renseigner @id_devise_reporting avec 1 ou 2 pour filtrer une devise; laisser NULL pour toutes les devises. | Mensuel et a chaque actualisation du tableau de bord clients |

## Garde-fous avant utilisation

- Relire la requête complète dans `data/modelisation/requetes.sql` avant exécution en production.
- Vérifier les paramètres `@date_debut`, `@date_fin`, `@id_devise_reporting`, `@taux_usd_cdf` et `@convertir_affichage_cdf` lorsque la requête les utilise.
- Ne pas modifier la base de production : les requêtes du catalogue doivent rester en lecture, avec CTE, `SELECT` et tables temporaires locales `#...` si nécessaire.
- Pour les requêtes lourdes, filtrer le plus tôt possible par date, devise, type d’opération ou population cible.
- Ne jamais additionner des montants CDF et USD. Les nombres de clients ou d’opérations peuvent être consolidés, mais pas les montants.

## Référence technique

Pour lire une requête complète depuis le terminal :

```powershell
& C:\Users\Benjamin-mupanzi\AppData\Local\anaconda3\python.exe skills\perfect-vision\scripts\inspect_vision_sql.py --number 144
```

Pour chercher par thème :

```powershell
& C:\Users\Benjamin-mupanzi\AppData\Local\anaconda3\python.exe skills\perfect-vision\scripts\inspect_vision_sql.py --query "DAT sans credit"
```
