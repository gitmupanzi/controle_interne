# Perfect Vision — Cycle client

Le cycle client décrit comment Perfect Vision identifie une personne ou une organisation, la rattache à ses comptes, puis permet de contrôler la qualité des informations utilisées par les opérations, l'épargne, le crédit et la conformité.

## Objectif métier

Un client fiable doit pouvoir être retrouvé par son identité, son numéro manuel, son code client, son téléphone et ses comptes. Ce cycle sert donc à répondre à trois questions simples :

- le client existe-t-il une seule fois ?
- ses informations essentielles sont-elles exploitables ?
- ses comptes sont-ils correctement rattachés ?

## Modèle relationnel simplifié

```mermaid
erDiagram
    ADHERENTS {
        string ID PK "identifiant_adherent"
        string CODE UK "code_client"
        string NUM_MANUEL UK "numero_manuel"
        string ID_CATEGORIE_ADHERENT FK "categorie_adherent"
        string ID_COMPTE_ADHERENT FK "compte_adherent_principal"
    }
    INDIVIDUS {
        string ID PK "identifiant_individu"
        string ID_PERSONNE FK "identifiant_personne"
    }
    GROUPES {
        string ID PK "identifiant_groupe"
        string ID_ADRESSE FK "adresse_groupe"
        string NOM "nom_groupe"
    }
    PERSONNES {
        string ID PK "identifiant_personne"
        string ID_ADRESSE FK "adresse_principale"
        string ID_ADRESSE_CONTACT FK "adresse_contact"
        string NOM "nom"
        string PRENOMS "prenoms"
    }
    ADRESSES {
        string ID PK "identifiant_adresse"
        string TELEPHONE "telephone"
    }
    COMPTES_ADHERENT {
        string id PK "identifiant_compte_adherent"
        string ID_ADHERENT FK "identifiant_adherent"
    }
    COMPTES {
        string ID PK "identifiant_compte"
        string ID_DEVISE FK "devise"
        string ID_COMPTE_GENERAL FK "compte_general"
    }
    LAB_ADHERENT_PROFIL_RISQUES {
        string ID PK "identifiant_profil_adherent"
        string ID_ADHERENT FK "identifiant_adherent"
        string ID_PROFIL_RISQUE FK "profil_risque"
        string ID_RISQUE_DE_PROFIL FK "niveau_risque"
    }
    LAB_PROFILS_DE_RISQUE {
        string ID PK "identifiant_profil_risque"
        string CODE UK "code_profil_risque"
    }
    ADHERENTS ||--o| INDIVIDUS : "client personne physique"
    ADHERENTS ||--o| GROUPES : "client personne morale/groupe"
    INDIVIDUS ||--|| PERSONNES : "identité"
    GROUPES ||--o| ADRESSES : "coordonnées"
    PERSONNES ||--o| ADRESSES : "coordonnées"
    ADHERENTS ||--o{ COMPTES_ADHERENT : "possède"
    COMPTES_ADHERENT ||--|| COMPTES : "compte"
    ADHERENTS ||--o{ LAB_ADHERENT_PROFIL_RISQUES : "profil risque"
    LAB_ADHERENT_PROFIL_RISQUES }o--|| LAB_PROFILS_DE_RISQUE : "niveau"
```

Les attributs indiqués comme `PK` sont les clés primaires ou clés logiques principales. Les attributs `FK` sont les clés secondaires utilisées pour joindre les tables. Par exemple, `ADHERENTS.ID` alimente `COMPTES_ADHERENT.ID_ADHERENT`, puis `COMPTES_ADHERENT.id` permet de retrouver le compte correspondant dans `COMPTES.ID`.

## Tables et vues principales

| Objet SQL | Rôle dans le cycle |
|---|---|
| `ADHERENTS` | Table centrale des clients/adhérents. |
| `INDIVIDUS` | Extension pour les personnes physiques. |
| `GROUPES` | Extension pour les personnes morales ou groupes. |
| `PERSONNES` | Nom, prénoms, sexe, civilité et identité de base. |
| `ADRESSES` | Téléphone, adresse, ville, e-mail. |
| `COMPTES_ADHERENT` | Table de rattachement entre client et compte. |
| `COMPTES` | Comptes rattachés aux clients. |
| `extra_clients_view` | Vue métier qui rassemble identité, téléphone, agence, zone, profession et catégorie client. |

## Lecture relationnelle

| Relation métier | Lecture base de données | Commentaire |
|---|---|---|
| Un adhérent peut être une personne physique. | `ADHERENTS` 1 → 0/1 `INDIVIDUS` | Utilisé lorsque `ID_CATEGORIE_ADHERENT = 'IND'`. |
| Un adhérent peut être une personne morale ou un groupe. | `ADHERENTS` 1 → 0/1 `GROUPES` | Utilisé pour les groupes et organisations. |
| Un adhérent peut avoir un ou plusieurs comptes adhérents. | `ADHERENTS` 1 → n `COMPTES_ADHERENT` | C'est la relation centrale du cycle client. |
| Un compte adhérent pointe vers un compte. | `COMPTES_ADHERENT` n → 1 `COMPTES` | Permet de retrouver la devise, le produit et les mouvements. |
| Un client peut avoir un profil de risque. | `ADHERENTS` 1 → 0/n `LAB_ADHERENT_PROFIL_RISQUES` | Utile pour la conformité et la surveillance. |

En phrase simple :

```text
Un adhérent peut avoir un ou plusieurs comptes_adherent.
Chaque comptes_adherent rattache l'adhérent à un compte.
Le compte devient ensuite le point d'entrée vers les mouvements, l'épargne, le crédit ou la conformité.
```

## Vues, méthodes et procédures utiles

| Objet | Type | Usage |
|---|---|---|
| `extra_clients_view` | Vue | Vue de référence pour restituer le client sans refaire toutes les jointures d'identité. |
| `sp_perf_extra_clients` | Procédure stockée | Extraction client Perfect Vision. |
| `sp_perf_extra_clients_frais_inscription` | Procédure stockée | Suivi des frais d'inscription clients. |
| `sp_perf_extra_clients_tontine` | Procédure stockée | Extraction des clients liés à la tontine, lorsque ce périmètre est utilisé. |

## Requêtes utiles

Les requêtes ci-dessous sont classées en privilégiant d'abord l'aide à la décision, puis les contrôles de qualité de données.

| Priorité | N° | Export | Ce que la requête apporte | Commentaire |
|---:|---:|---|---|---|
| 1 | 157 | `157_cycle_clients_socle_indicateurs_par_client_et_devise` | Socle client décisionnel par devise : activité, exposition épargne/crédit, échéances et indicateurs utiles au tableau de bord. | À privilégier pour Power BI ou un cockpit Direction, car il donne une lecture 360 sans mélanger USD et CDF. |
| 2 | 090 | `90_cycle_crm_clients_liste_des_clients_avec_leurs_comptes_et_devises` | Liste client + comptes + devises. | Utile pour retrouver les comptes rattachés à un client et contrôler la couverture des devises. |
| 3 | 148 | `148_cycle_crm_clients_liste_unique_des_clients_avec_telephone_et_nombre_de_comptes` | Liste unique client/téléphone/nombre de comptes. | Très pratique pour les équipes terrain : le téléphone devient une clé de contact et de rapprochement. |
| 4 | 121 | `121_cycle_crm_clients_departs_et_retours_clients_avec_exposition_epargne_credit` | Départs/retours avec exposition épargne/crédit. | Aide à voir l'impact commercial et financier des clients partis ou revenus. |
| 5 | 122 | `122_cycle_crm_clients_controle_qualite_des_numeros_de_telephone_clients` | Qualité des numéros de téléphone. | Indispensable avant relance, rapprochement Solution Numérique ou connexion à d'autres sources. |
| 6 | 024 | `24_cycle_crm_clients_adherents_inscrits_en_doublon_par_code` | Clients en doublon par code. | Contrôle de qualité pour éviter une lecture fausse du nombre de clients. |
| 7 | 025 | `25_cycle_crm_clients_adherents_sans_informations_essentielles` | Clients sans informations essentielles. | À utiliser pour compléter les dossiers KYC et améliorer la fiabilité des analyses. |
| 8 | 026 | `26_cycle_crm_clients_adherents_non_valides_ou_droit_d_adhesion_non_paye` | Clients non validés ou droit d'adhésion non payé. | Permet d'isoler les clients dont le statut administratif doit être revu. |
| 9 | 028 | `28_cycle_crm_clients_adherents_sans_compte_adherent_ou_avec_compte_adherent_introuvable` | Clients sans compte ou avec rattachement incohérent. | Contrôle structurel : un client sans compte rattaché peut perturber les analyses épargne/crédit. |

## Requêtes recommandées pour le cockpit Clients

Le cockpit Clients doit aider à connaître la base client, la qualité des informations, l'activité réelle et les points de relance possibles. La priorité est de garder des feuilles exploitables par la Direction et les équipes opérationnelles : nom client, numéro de téléphone, agence, devise, statut, activité, solde ou exposition lorsque c'est utile.

| Priorité | Requête | Export | Utilité pour le cockpit | Commentaire |
|---:|---:|---|---|---|
| 1 | `148` | `148_cycle_crm_clients_liste_unique_des_clients_avec_telephone_et_nombre_de_comptes` | Liste unique des clients avec téléphone et nombre de comptes. | Requête essentielle pour appeler, retrouver ou rapprocher rapidement un client. |
| 2 | `125` | `125_cycle_crm_clients_streamlit` | Source large du cycle client : KYC, segmentation, rattachements et informations CRM. | Sert de base complète lorsque l'équipe veut analyser la qualité et la structure du référentiel client. |
| 3 | `157` | `157_cycle_clients_socle_indicateurs_par_client_et_devise` | Socle décisionnel par client et par devise : comptes, épargne, crédits, DAT, échéances et intérêts. | Donne une vue client 360 sans mélanger les devises ; utile pour les tableaux de bord Direction. |
| 4 | `090` | `90_cycle_crm_clients_liste_des_clients_avec_leurs_comptes_et_devises` | Portefeuille client-compte avec devise et agence. | Permet de vérifier si les comptes sont correctement rattachés aux clients. |
| 5 | `122` | `122_cycle_crm_clients_controle_qualite_des_numeros_de_telephone_clients` | Contrôle qualité des numéros de téléphone. | Important pour la Solution Numérique, car le téléphone est la clé de rapprochement la plus pratique. |
| 6 | `042` | `42_cycle_operations_depot_retrait_depots_et_retraits_agreges_par_client` | Dépôts et retraits agrégés par client. | Mesure l'activité réelle du client et aide à distinguer les clients actifs des clients simplement enregistrés. |
| 7 | `043` | `43_cycle_operations_depot_retrait_top_clients_par_volume_de_mouvements` | Top clients par volume de mouvements sur la période. | Aide à identifier les clients les plus importants ou les plus sensibles en volume. |
| 8 | `041` | `41_cycle_operations_depot_retrait_clients_avec_forte_activite_mais_donnees_kyc_incompletes_ou_atypiques` | Clients actifs mais avec KYC incomplet ou atypique. | Prioritaire pour éviter qu'une forte activité financière repose sur un dossier client insuffisant. |
| 9 | `121` | `121_cycle_crm_clients_departs_et_retours_clients_avec_exposition_epargne_credit` | Départs et retours clients avec exposition épargne/crédit. | Utile pour suivre le risque et les actions de rétention lorsqu'un client quitte ou revient. |
| 10 | `159` | `159_cycle_conformite_clients_depots_retraits_superieurs_equivalent_10k_usd` | Clients avec dépôts ou retraits supérieurs ou égaux à l'équivalent 10 000 USD. | Sert à repérer les clients à examiner dans le cadre conformité et LBC-FT. |
| 11 | `160` | `160_cycle_conformite_detail_depots_retraits_superieurs_equivalent_10k_usd` | Détail opération par opération des mouvements sensibles. | Fournit la preuve détaillée derrière la synthèse des mouvements sensibles. |

Feuilles cockpit conseillées : `Clients_Socle`, `Clients_Uniques_Telephone`, `Clients_Comptes_Devises`, `Clients_Actifs_Mouvements`, `Clients_KYC_A_Verifier`, `Clients_Top_Volumes`, `Clients_Depots_Retraits_10K`.

## Points de contrôle

- Un client sans téléphone fiable devient difficile à rapprocher avec la Solution Numérique.
- Le numéro de téléphone est une clé de rapprochement, mais il doit être normalisé avant comparaison.
- Les doublons client peuvent fausser les indicateurs de portefeuille, d'épargne et de crédit.
- Les comptes sans rattachement client exploitable doivent être isolés avant toute analyse financière.
