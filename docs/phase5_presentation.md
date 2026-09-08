# Phase 5 — Sélection pour la présentation

La phase 5 occupe **quatre diapositives** au total : procédure, calibration et deux
diapositives de résultats. Les figures analytiques sont générées en anglais puis composées
dans les slides LaTeX ; elles ne contiennent plus de cartes de chiffres clés.

## Ordre prévu

### 1–2. Procédure et calibration — composées en LaTeX

Cette partie devra rester courte et expliquer :

- la sélection des `7 profils × 2 issues = 14` médoïdes conditionnels ;
- la reconstruction et l'annotation aveugle des histoires complètes ;
- le modèle local Qwen3.6-27B, le codebook lisible et les sorties JSON contraintes ;
- la calibration humaine sur quatre trajectoires et trois paires ;
- les itérations P01–P03, puis le gel du prompt avant le run complet.

Elle devra rappeler que les 32 concordances sur 44 champs de P03 sont une concordance de
calibration, et non une accuracy ou une validation hors échantillon.

### 3. Résultats des trajectoires individuelles — produit

Fichier : `01_individual_trajectories.png` ou sa version SVG.

La figure contient uniquement le graphique d'adéquation exacte entre niveau générateur et
profil perçu sur les 14 médoïdes : `risk` 9/14, `morality` 6/14 et `action` 2/14. Les
résultats complémentaires — 14/14 histoires `continuous`, 9/14 profils perçus `coherent`
et le diagnostic détaillé de l'axe d'action — sont composés directement en LaTeX.

Le diagnostic de l'axe d'action est affiché pour ne pas laisser le score 2/14 sans
explication : 0/10 niveaux neutres, 0/2 physiques et 2/2 tactiques sont retrouvés
exactement. Le résultat indique une forte asymétrie de la manifestation narrative, pas
une défaillance JSON ni une accuracy faible du modèle.

Message à dire en une phrase :

> Complete trajectories preserve causal continuity, but the intended player profile is
> unevenly perceptible: risk is recovered more often than morality, while action is
> strongly biased toward a tactical reading.

Temps conseillé : **45–60 secondes**.

### 4. Résultats des comparaisons de trajectoires — produit

Fichier : `02_trajectory_comparisons.png` ou sa version SVG.

La figure est centrée sur la question de recherche : les profils opposés sont-ils
perceptibles dans les histoires complètes ? Chaque ligne montre le contraste attendu,
l'issue (`Win` ou `Death`), la différence entre les deux chemins, puis ce que devient A
par rapport à B sur les trois axes. L'axe expérimentalement manipulé est en gras. La
dernière colonne donne la différence narrative globale. Les identifiants de paires et les
deux sorties directionnelles détaillées ne sont pas affichés.

Une cellule rouge signale que les ordres A/B et B/A ne concordent pas. La valeur affichée
les résume : deux directions opposées s'annulent en `even`, tandis que `even` associé à
une direction conserve cette direction. Pour `narrative distinctness`, la moyenne entre
`medium` et `high` est affichée `Medium-high`. Cette agrégation est une aide de lecture et
ne transforme pas les catégories ordinales en mesures continues.

Le résultat principal est que **5/6 contrastes contrôlés sont retrouvés de manière stable**.
Les contrastes de risque et de moralité sont retrouvés pour les deux issues ; sur l'axe
contrôlé, seul `action / Win` devient `even` après agrégation des deux ordres. Les cellules
hors axe rendent également visibles les covariations narratives entre profils.

Les six paires sont au moins moyennement distinctes. Quatre niveaux de
`narrative distinctness` sont stables ; `morality / Death` et `action / Win` oscillent
entre `medium` et `high` et sont donc affichés `Medium-high` en rouge.

La colonne `Path difference (LCS)` vaut `1 - similarité LCS normalisée`. Elle mesure la
différence séquentielle entre les deux médoïdes sélectionnés et ne constitue pas elle-même
un indice BoP. L'appui BoP est donné séparément par la divergence de Jensen--Shannon des
flux d'arêtes : risque `0.163`, action `0.052`, moralité `0.037`. Le risque est donc à la
fois le contraste structurel le plus fort et un contraste constamment perceptible dans
les histoires.

Trois lectures concises du tableau sont défendables :

- le risque est retrouvé pour `Win` et `Death` et possède aussi la plus forte divergence
  BoP ;
- la moralité reste retrouvée dans la paire `Death` malgré une faible distance LCS
  (`0.21`), ce qui montre que la perception du profil ne se réduit pas au nombre de
  paragraphes différents ;
- l'action est retrouvée pour `Death`, mais la paire `Win` est sensible à l'ordre et doit
  être présentée comme le seul résultat non robuste.

Ces six paires sont des contrastes conçus, et non un échantillon aléatoire : les résultats
sont descriptifs et ne permettent pas d'estimer un taux général de récupération.

Message à dire en une phrase :

> The intended relative profile is recovered in five of six controlled comparisons;
> risk is both the strongest BoP contrast and consistently perceptible in complete
> stories.

Temps conseillé : **55–70 secondes**.

## Interprétation à préserver

Les résultats absolus et pairwise répondent à deux questions différentes. La première
slide demande si chaque niveau générateur est reconnaissable isolément. La seconde demande
si deux extrêmes conçus pour différer sur un axe produisent une différence globale
perceptible. Il n'est donc pas contradictoire d'obtenir seulement 2/14 correspondances
exactes sur `action`, mais de récupérer le contraste contrôlé de cinq paires sur six.

L'inversion reste un contrôle de robustesse, pas un résultat principal : elle est encodée
par la couleur des cellules plutôt que résumée dans une colonne ou un score autonome.

## Génération et validation

```bash
uv run python scripts/5.5_build_phase5_presentation.py --book LW01
uv run python scripts/tests/test_5_5_build_phase5_presentation.py --book LW01
```

Les fichiers sont écrits dans `results/phase5/LW01/presentation/`. Les PNG mesurent
exactement 1920 × 1080 pixels et les SVG conservent du texte éditable. Le manifeste fixe
le plan des quatre positions, signale que les slides sont composées séparément en LaTeX et
archive les empreintes de toutes les sources et sorties.

Le validateur contrôle les dimensions, les titres anglais, les quatre chiffres clés, les
diagnostics individuels, les six comparaisons et toutes les empreintes. Les deux slides ont
également été inspectées visuellement après leur génération.
