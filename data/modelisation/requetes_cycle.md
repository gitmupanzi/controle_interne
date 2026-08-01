# Requetes importantes par cycle

Source : `data/vision/requetes.sql`

Ce fichier sert de guide rapide pour choisir les extractions utiles aux agents de credit, d'epargne et de conformite.

## Regles communes

- Toujours parametrer `@date_debut`, `@date_fin` et `@id_devise_reporting`.
- Si `@id_devise_reporting = NULL`, garder les montants separes par devise.
- Utiliser le numero de requete et le nom `Export` exact pour retrouver rapidement l'extraction dans le catalogue.
- Donner la priorite aux requetes utiles a l'action : relance, regularisation, surveillance et justification.

## Cycle credit

### Hebdomadaire

Suivi terrain, recouvrement et anomalies urgentes.

| Requete | Export | Usage |
|---:|---|---|
| 091 | `91_cycle_credit_credits_en_cours_ou_termines_avec_echeances_impayees_sur_la_periode` | Voir les credits avec echeances de la periode non totalement remboursees. |
| 100 | `100_cycle_credit_dashboard_echeances_futures_des_prets_en_cours` | Preparer les relances avant les echeances a venir. |
| 136 | `136_cycle_credit_remboursements_credit_encaisses_mais_non_imputes_correctement_au_pret` | Verifier les remboursements encaisses mais mal imputes, car ils peuvent fausser le PAR. |
| 143 | `143_cycle_credit_remboursements_credit_recus_apres_echeance_a_suivre_pour_par` | Identifier les paiements tardifs et la discipline de remboursement. |
| 145 | `145_cycle_credit_liste_detaillee_des_prets_avec_impayes` | Obtenir la liste directe des prets en arriere a la date de situation. |
| 146 | `146_cycle_credit_liste_detaillee_des_clients_avec_echeances_sur_la_periode` | Connaitre les clients qui doivent rembourser sur la periode. |
| 147 | `147_cycle_credit_comptes_ordinaires_et_disponibilites_clients` | Verifier si le client en impaye/echeance dispose d'un solde recuperable sur compte ordinaire. |
| 142 | `142_cycle_credit_credits_decaisses_sans_mouvement_comptable_coherent` | Controler les decaissements sans ecriture comptable coherente. |

### Mensuel

Pilotage portefeuille, PAR, provision et qualite credit.

| Requete | Export | Usage |
|---:|---|---|
| 096 | `96_cycle_credit_dashboard_par_details_credit_a_la_date_de_fin` | Suivre le portefeuille a risque detaille a la date de fin. |
| 097 | `97_cycle_credit_dashboard_synthese_par_et_provision_par_produit_et_agence` | Produire la synthese PAR/provision par produit et agence. |
| 098 | `98_cycle_credit_dashboard_top_encours_credits_par_client` | Suivre la concentration des plus gros encours. |
| 106 | `106_cycle_credit_dashboard_couverture_credit_par_epargne_et_garanties` | Mesurer la couverture des credits par epargne et garanties. |
| 107 | `107_cycle_credit_dashboard_provision_trois_derniers_mois_par_client_agence_produit` | Suivre les provisions sur trois mois. |
| 114 | `114_cycle_credit_pipeline_credit_et_delais_instruction_decision_decaissement` | Mesurer les delais entre demande, instruction, decision et decaissement. |
| 115 | `115_cycle_credit_credits_decaisses_avec_faible_activite_epargne_avant_octroi` | Identifier les credits octroyes a des clients peu actifs en epargne. |
| 116 | `116_cycle_credit_couverture_caution_et_garanties_par_rapport_au_credit_accorde` | Verifier caution, epargne obligatoire et garanties par rapport au credit accorde. |
| 059 | `59_cycle_credit_demandes_de_credit_sans_pret_accorde` | Suivre le pipeline des demandes non transformees en pret. |
| 060 | `60_cycle_credit_prets_incomplets_sans_dossier_sans_compte_credit_sans_compte_epargne_ou_sans_cycle` | Detecter les prets incomplets. |
| 061 | `61_cycle_credit_cycles_de_pret_avec_echeance_depassee_et_non_cloturee` | Reperer les cycles ouverts apres leur date de fin d'echeance. |
| 068 | `68_cycle_credit_anomalies_a_prioriser_pour_audit` | Obtenir une synthese des anomalies credit a prioriser. |
| 069 | `69_cycle_credit_prets_decaisses_sans_validation_prealable_exploitable` | Verifier les decaissements sans validation prealable. |
| 070 | `70_cycle_credit_couverture_de_garantie_insuffisante_par_rapport_a_la_tranche` | Detecter les garanties insuffisantes selon la tranche. |
| 071 | `71_cycle_credit_caution_financiere_insuffisante_par_rapport_au_dossier` | Detecter les cautions financieres insuffisantes. |
| 072 | `72_cycle_credit_garanties_sans_garant_identifiable_ou_sans_piece_exploitable` | Reperer les garanties sans garant ou pieces exploitables. |
| 073 | `73_cycle_credit_dossiers_avec_analyse_obligatoire_absente_ou_inachevee` | Reperer les dossiers sans analyse obligatoire finalisee. |
| 077 | `77_cycle_credit_mainlevee_ou_retrait_de_garantie_avant_solde_du_pret` | Controler les retraits ou mainlevees de garantie avant solde. |
| 078 | `78_cycle_credit_demandes_de_reechelonnement_sans_validation_exploitable` | Revoir les reechelonnements sans validation exploitable. |
| 079 | `79_cycle_credit_prets_marques_reechelonnes_sans_demande_formelle` | Identifier les prets marques reechelonnes sans demande formelle. |
| 080 | `80_cycle_credit_prets_en_contentieux_avec_incoherences_de_transfert_ou_de_montant` | Revoir les credits en contentieux avec incoherences. |
| 083 | `83_cycle_credit_cycles_de_pret_sans_echeancier_tabamor_exploitable` | Identifier les prets sans echeancier exploitable. |
| 084 | `84_cycle_credit_taux_d_impaye_du_portefeuille_par_tranche_de_montant_et_par_devise` | Calculer le taux d'impaye par tranche et devise. |
| 085 | `85_cycle_credit_clients_qui_terminent_leur_credit_par_mois_ou_sur_la_periode` | Identifier les clients dont le credit arrive a terme. |

## Cycle epargne

### Hebdomadaire

Comptes, mouvements et disponibilites.

| Requete | Export | Usage |
|---:|---|---|
| 055 | `55_cycle_epargne_mouvements_avec_montant_nul_negatif_ou_superieur_au_seuil_de_revue` | Revoir les mouvements epargne prioritaires. |
| 056 | `56_cycle_epargne_depots_et_retraits_par_client_compte_agence_devise_et_produit` | Obtenir le detail depots/retraits par client, compte, devise et produit. |
| 057 | `57_cycle_epargne_analyse_des_gros_mouvements_par_periode` | Investiguer les gros mouvements. |
| 110 | `110_cycle_epargne_comptes_epargne_inactifs_ou_dormants_avec_solde_a_la_date_de_fin` | Suivre les comptes inactifs ou dormants avec solde. |
| 137 | `137_cycle_epargne_depots_et_retraits_epargne_avec_sens_comptable_incoherent` | Detecter les depots/retraits dont le sens comptable parait incoherent. |
| 138 | `138_cycle_epargne_comptes_epargne_avec_solde_negatif_apres_mouvement_debit` | Reperer les comptes devenus negatifs apres un debit. |
| 141 | `141_cycle_epargne_mouvements_sur_comptes_clotures_bloques_ou_inactifs` | Identifier les mouvements sur comptes clotures, bloques ou inactifs. |
| 144 | `144_cycle_credit_clients_avec_dat_sans_credits_en_cours` | Reperer les clients avec DAT sans credit en cours. |

### Mensuel

Pilotage produit, qualite compte et activite.

| Requete | Export | Usage |
|---:|---|---|
| 049 | `49_cycle_epargne_produits_d_epargne_inactifs_encore_utilises_par_des_comptes` | Identifier les produits inactifs encore utilises. |
| 050 | `50_cycle_epargne_produits_d_epargne_non_valides_encore_utilises_par_des_comptes` | Identifier les produits non valides encore rattaches a des comptes. |
| 051 | `51_cycle_epargne_produits_sans_depot_retrait_autorise_mais_avec_mouvements_sur_les_comptes` | Detecter les mouvements sur produits qui ne devraient pas accepter depot/retrait. |
| 052 | `52_cycle_epargne_incoherences_entre_devise_du_produit_du_compte_et_du_mouvement` | Detecter les incoherences de devise entre produit, compte et mouvement. |
| 053 | `53_cycle_epargne_comptes_rattaches_a_un_produit_epargne_inexistant_ou_invalide` | Reperer les comptes rattaches a un produit inexistant ou invalide. |
| 058 | `58_cycle_epargne_analyse_des_mouvements_par_point_de_service` | Suivre l'activite epargne par point de service. |
| 113 | `113_cycle_epargne_activite_epargne_par_client_produit_et_agence_sur_la_periode` | Analyser l'activite epargne mensuelle par client, produit et agence. |
| 090 | `90_cycle_crm_clients_liste_des_clients_avec_leurs_comptes_et_devises` | Verifier le referentiel clients, comptes et devises. |

## Cycle conformite

### Hebdomadaire

Surveillance LBC-FT et alertes.

| Requete | Export | Usage |
|---:|---|---|
| 039 | `39_cycle_operations_depot_retrait_fractionnement_potentiel_plusieurs_mouvements_sous_seuil_mais_cumul_au_dessus_du_seuil` | Detecter le fractionnement potentiel sous seuil. |
| 040 | `40_cycle_operations_depot_retrait_operations_inhabituelles_par_client_volume_periode_vs_moyenne_des_3_mois_precedents` | Identifier les operations inhabituelles par rapport a l'historique du client. |
| 041 | `41_cycle_operations_depot_retrait_clients_avec_forte_activite_mais_donnees_kyc_incompletes_ou_atypiques` | Reperer les clients actifs avec KYC incomplet ou atypique. |
| 043 | `43_cycle_operations_depot_retrait_top_clients_par_volume_de_mouvements` | Identifier les clients les plus actifs a surveiller. |
| 044 | `44_cycle_operations_depot_retrait_analyse_detaillee_des_operations_annulees` | Revoir les annulations. |
| 045 | `45_cycle_operations_depot_retrait_utilisateurs_a_risque_volumes_annulations_saisies_tardives_et_auto_validation` | Identifier les utilisateurs avec signaux de supervision. |
| 057 | `57_cycle_epargne_analyse_des_gros_mouvements_par_periode` | Revoir les gros mouvements par periode. |
| 150 | `150_cycle_conformite_alertes_lbc_ft_detaillees` | Traiter les alertes LBC-FT detaillees. |
| 151 | `151_cycle_conformite_declarations_soupcon_centif` | Suivre les declarations de soupcon et CENTIF. |
| 152 | `152_cycle_conformite_clients_profils_risque` | Suivre les clients classes a risque ou en surveillance renforcee. |
| 154 | `154_cycle_conformite_comptes_dormants_reactives` | Justifier les reactivations de comptes dormants. |

### Mensuel

Reporting, justification et qualite LBC-FT.

| Requete | Export | Usage |
|---:|---|---|
| 038 | `38_cycle_operations_depot_retrait_synthese_excel_lbc_ft_depots_retraits_et_mobile_banking` | Produire la synthese depots, retraits et mobile banking pour reporting. |
| 042 | `42_cycle_operations_depot_retrait_depots_et_retraits_agreges_par_client` | Analyser les depots/retraits agreges par client. |
| 048 | `48_cycle_conformite_lbc_ft_rubriques_lbc_ft_non_couvertes_automatiquement_et_pistes_de_mapping` | Identifier les trous de couverture du reporting LBC-FT. |
| 122 | `122_cycle_crm_clients_controle_qualite_des_numeros_de_telephone_clients` | Controler la qualite des numeros de telephone clients. |
| 148 | `148_cycle_crm_clients_liste_unique_des_clients_avec_telephone_et_nombre_de_comptes` | Utiliser une base client unique avec telephone et nombre de comptes. |
| 149 | `149_cycle_conformite_reporting_lbc_ft` | Produire le reporting LBC-FT parametre par periode. |
| 153 | `153_cycle_conformite_referentiel_listes_sanctions` | Revoir le referentiel sanctions et la qualite d'identification. |
| 155 | `155_cycle_conformite_qualite_donnees_lbc_ft` | Mesurer la qualite des donnees du dispositif LBC-FT. |
| 156 | `156_cycle_conformite_lbc_ft_socle_unique_analyses_38_39_48_57_149_155` | Televerser un seul fichier dans l'application pour couvrir le cycle conformite. |

## Requetes transversales

Ces requetes sont utiles aux trois equipes.

| Requete | Export | Usage |
|---:|---|---|
| 121 | `121_cycle_crm_clients_departs_et_retours_clients_avec_exposition_epargne_credit` | Suivre les clients partis/retours avec exposition epargne et credit. |
| 157 | `157_cycle_clients_socle_indicateurs_par_client_et_devise` | Alimenter le socle clients par devise pour tableau de bord. |

## Packs rapides

| Pack | Requetes |
|---|---|
| Hebdomadaire credit | `091`, `100`, `136`, `143`, `145`, `146`, `147`, `142` |
| Mensuel credit | `096`, `097`, `098`, `106`, `107`, `114`, `115`, `116`, `059`, `060`, `061`, `068`, `069`, `070`, `071`, `072`, `073`, `077`, `078`, `079`, `080`, `083`, `084`, `085` |
| Hebdomadaire epargne | `055`, `056`, `057`, `110`, `137`, `138`, `141`, `144` |
| Mensuel epargne | `049`, `050`, `051`, `052`, `053`, `058`, `113`, `090` |
| Hebdomadaire conformite | `039`, `040`, `041`, `043`, `044`, `045`, `057`, `150`, `151`, `152`, `154` |
| Mensuel conformite | `038`, `042`, `048`, `122`, `148`, `149`, `153`, `155`, `156` |
