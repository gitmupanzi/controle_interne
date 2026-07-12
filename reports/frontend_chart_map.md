# Carte des graphiques du tableau de bord

Cette carte fixe les choix de visualisation appliqués à l'interface Streamlit. Elle sert de référence pour garder les vues cohérentes lors des prochaines évolutions.

| Besoin utilisateur | Vue retenue | Encodage principal | Règle de lisibilité |
|---|---|---|---|
| Suivre une évolution | Courbe | Temps en abscisse, valeur en ordonnée, devise ou série en couleur | Légende horizontale uniquement à partir de deux séries |
| Comparer des catégories courtes | Barres verticales | Catégorie puis volume ou montant | Rotation légère des libellés, une couleur par défaut |
| Lire des motifs ou champs longs | Barres horizontales | Valeur en abscisse, libellé en ordonnée | Tri croissant pour faire ressortir le maximum en haut |
| Comprendre une composition simple | Anneau | Part par statut ou catégorie | Étiquettes directes jusqu'à cinq parts, légende au-delà |
| Examiner une distribution | Histogramme | Classe de valeur puis fréquence | Grille légère et unités visibles dans l'axe |
| Comparer les flux M-PESA | Courbes ou barres groupées | Jour, montant, sens, puis devise en facette | CDF et USD restent séparés ; aucun total monétaire mixte |

## Palette et interactions

- Bleu `#1553A1` : série principale et information neutre.
- Orange `#D97B16` : attention ou seconde série.
- Vert `#2D7D46` : état favorable.
- Violet et ocre : séries additionnelles, utilisées avec parcimonie.
- La barre d'outils apparaît au survol, le zoom à la molette est désactivé et chaque graphique reste exportable en PNG.

## Contrôles qualité

- Les graphiques multi-séries conservent leur légende ; les graphiques à série unique la masquent.
- Les libellés longs utilisent une orientation horizontale et des marges automatiques.
- Les vues sans données affichent un état vide explicite.
- Les valeurs CDF et USD ne sont jamais additionnées entre elles.
