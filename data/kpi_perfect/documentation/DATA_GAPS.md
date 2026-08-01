# Données manquantes ou non encore matérialisées

Ce document distingue une absence réelle de source d'une simple migration restant à réaliser.

| Donnée ou capacité | KPI bloqués ou partiels | Source / structure attendue | Grain attendu | Situation |
|---|---|---|---|---|
| Décaissements matérialisés | demandes, approbations, décaissements, montant décaissé | Q99 et tables de demandes/prêts | mois × agence × produit × devise × type client | Matérialisé par `rpt.f_credit_decaissements`; rapprochement source/reporting OK ; contrôle visuel Power BI restant |
| Échéances et remboursements séparés | échéances futures, capital payé, intérêts payés, taux de remboursement, taux de recouvrement | Q100, Q145, Q146 et remboursements | mois d'échéance × agence × produit × devise ; remboursement × prêt × date | Échéances futures matérialisées par `rpt.f_credit_echeances_futures`; remboursements détaillés encore à concevoir |
| Historique quotidien du PAR | évolution PAR fidèle à chaque date passée | snapshot crédit quotidien ou mensuel | prêt × date de situation × devise | Q109 matérialise la tendance disponible pour le reporting ; un historique quotidien complet reste à gouverner si demandé |
| Épargne et mouvements | dépôts, retraits, collecte nette, croissance ; les soldes et ratios crédits/dépôts sont matérialisés | Q103, Q110, Q113 et opérations | compte × date de situation ; opération × date | Q103 matérialisée dans `rpt.f_epargne_soldes`; mouvements détaillés Q110/Q113 encore à concevoir |
| DAT détaillé | actifs, échus, 7/30 jours, renouvelés, intérêts | Q144 et tables DAT | DAT × client × devise × date | Source disponible, fait dédié non créé |
| Taux de change daté et gouverné | équivalents CDF, consolidation institutionnelle multi-devises | table de taux validée | date × devise source × devise cible | Non validé ; aucune conversion automatique autorisée |
| Charges, produits comptables, fonds propres et actifs | résultat net, coefficient d'exploitation, liquidité prudentielle | balance générale / écritures comptables validées | compte comptable × date × devise × agence | Source métier non confirmée ; ne pas inventer |
| Sécurité utilisateurs | RLS agence et gestionnaire | table de sécurité dans `BB_VISION_REPORTING` | utilisateur × rôle × agence/gestionnaire | Structure à préparer ; utilisateurs non fournis |
| Validation visuelle Power BI | statut final des KPI migrés | actualisation Power BI Desktop puis relevé des cartes | mesure × période × devise | À exécuter après ouverture du PBIP, surtout depuis la bascule complète vers `BB_VISION_REPORTING` |
