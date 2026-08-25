# Phase 4 — Sélection pour la présentation

La présentation dure 20 minutes et doit aussi couvrir la méthodologie, la construction
des graphes et l'analyse future des trajectoires. La phase 4 ne doit donc pas devenir un
catalogue d'indices. La sélection finale tient en **trois diapositives**, avec un tableau
optionnel de secours. Toutes les figures sont en anglais et au format 16:9.

## Ordre recommandé

### 1. Profils, survie et liberté narrative

Fichier : `01_profile_landscape.png` ou sa version SVG.

La figure place les 27 profils selon leur probabilité de victoire et leur entropie de
trajectoire. La couleur représente le risque et la forme l'axe d'action ; seuls le profil
neutre et les deux extrêmes de victoire sont nommés.

Message à dire en une phrase :

> Player profiles substantially change both survival and the paths encountered; in this
> design, greater survival is associated with greater trajectory entropy rather than a
> survival–freedom trade-off.

La corrélation descriptive vaut $r=0{,}826$. Elle résume les 27 profils configurés : ce
n'est ni une estimation d'une population de joueurs, ni un test de significativité, ni
un effet causal. Le profil neutre gagne 11,98 % des lectures ; l'étendue complète va de
5,44 % à 25,83 %.

Temps conseillé : **40–50 secondes**.

### 2. Effets marginaux des trois axes

Fichier : `02_axis_effects.png` ou sa version SVG.

La figure montre les différences avec le niveau neutre du même axe pour quatre mesures
complémentaires : victoire, entropie, couverture et rejouabilité. Chaque valeur moyenne
sur les neuf combinaisons des deux autres axes.

Message à dire en une phrase :

> Risk is the dominant behavioural axis: cautious choices raise win probability by 9.23
> percentage points, whereas reckless choices lower it by 5.24 points and strongly
> reduce trajectory entropy.

Les axes de moralité et d'action ont des effets plus petits, mais non nuls. Les valeurs
de probabilité sont affichées en points de pourcentage ; l'entropie reste en nats.

Temps conseillé : **50–60 secondes**.

### 3. Trois lectures locales du même graphe

Fichier : `03_local_index_maps.png` ou sa version SVG.

Les trois panneaux utilisent exactement le même layout Project Aon. La taille et la
couleur des nœuds représentent successivement :

1. la probabilité de visite du profil neutre ;
2. la contribution à la mortalité du profil neutre ;
3. l'étendue de la probabilité de visite entre les 27 profils.

Les formes conservent les catégories structurelles : cercle ordinaire, losange de
combat, croix de mort, étoile de victoire et départ cerclé. Les arêtes grises sont
pondérées par leur flux attendu neutre.

Message à dire en une phrase :

> The narrative backbone, the main death bottlenecks and the regions most sensitive to
> player type are not the same parts of the graph.

Hors paragraphe initial, les nœuds les plus visités sont 141, 157, 264 et 97. Les trois
principales contributions à la mortalité sont 306, 327 et 154 ; les plus grandes
sensibilités au profil se trouvent en 200, 6 et 255. Ces numéros servent à guider la
lecture du graphe, pas à remplacer une interprétation du texte des paragraphes.

Temps conseillé : **50–70 secondes**.

### Tableau optionnel

Fichier : `04_key_numbers.png`, sa version SVG ou `04_key_numbers.csv`.

Le tableau conserve seulement cinq mesures : victoire, durée, entropie, couverture et
rejouabilité. Il distingue le profil neutre, la moyenne équilibrée et l'étendue observée.
Il peut servir de diapositive de secours, d'annexe ou de résumé écrit, mais il n'est pas
nécessaire si les trois figures précédentes sont commentées.

## Ce qui n'est volontairement pas montré

- les 15 indices globaux dans un même tableau ;
- les noms des 27 profils dans la figure globale ;
- les 351 divergences par paires de profils ;
- les flux conditionnés détaillés à `Win` et `Death` ;
- une carte séparée de l'impact des choix ;
- des intervalles de confiance ou tests statistiques artificiels.

Ces informations restent disponibles dans les sorties 4.1 et 4.2. Les flux conditionnés
seront plus utiles pour sélectionner les trajectoires de la phase 5. L'impact des choix
reste disponible dans `node_rankings.csv`, mais une quatrième carte locale alourdirait la
présentation sans ajouter un message aussi distinct que les trois cartes retenues.

## Génération et validation

```bash
uv run python scripts/4.3_build_bop_presentation.py --book LW01
uv run python scripts/tests/test_4_3_build_bop_presentation.py --book LW01
```

Les fichiers sont écrits dans `results/phase4/LW01/presentation/`. Les PNG mesurent
exactement 1920 × 1080 pixels ; les SVG conservent du texte éditable. Le manifeste
`presentation_manifest.json` donne l'ordre recommandé, les sources, les messages, les
dimensions ainsi que la taille et l'empreinte SHA-256 de chaque artefact.

Le validateur contrôle les dimensions, les titres anglais, le tableau arrondi depuis les
données sources, la corrélation descriptive, les nœuds mis en avant et toutes les
empreintes. Il garantit la reproductibilité technique, tandis que la lisibilité des
quatre supports a également été contrôlée visuellement après génération. Une seconde
génération complète produit les mêmes empreintes pour les neuf artefacts.
