# Phase 5 — Sélection pour la présentation

La phase 5 occupera **trois ou quatre diapositives** au total. Les figures sont en anglais,
au format 16:9. Les deux diapositives de résultats sont produites ; les une ou deux
diapositives de procédure et de calibration seront construites plus tard.

## Ordre prévu

### 1–2. Procédure et calibration — à produire

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

La figure montre l'adéquation exacte entre niveau générateur et profil perçu sur les 14
médoïdes : `risk` 9/14, `morality` 6/14 et `action` 2/14. Elle montre aussi les deux
résultats complémentaires suffisamment lisibles : 14/14 histoires `continuous` et 9/14
profils perçus `coherent`.

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

La figure conserve les six paires, leur axe et issue contrôlés, leur distance
structurelle, les deux jugements de différence narrative et le résultat sur l'axe
contrôlé. Les trois chiffres supérieurs résument :

- 5/6 contrastes contrôlés retrouvés de manière stable ;
- 18/24 labels stables après inversion canonique B/A ;
- 9/9 axes non contrôlés mais stables également perçus comme différents, trois autres
  étant sensibles à l'ordre.

Message à dire en une phrase :

> Relative profile contrasts are visible in five of the six designed pairs, but the
> off-axis shifts show that risk, morality and action do not remain narratively
> independent.

Temps conseillé : **55–70 secondes**.

## Interprétation à préserver

Les résultats absolus et pairwise répondent à deux questions différentes. La première
slide demande si chaque niveau générateur est reconnaissable isolément. La seconde demande
si deux extrêmes conçus pour différer sur un axe produisent une différence globale
perceptible. Il n'est donc pas contradictoire d'obtenir seulement 2/14 correspondances
exactes sur `action`, mais de récupérer le contraste contrôlé de cinq paires sur six.

La fuite entre axes est un résultat substantiel : le contrôle probabiliste d'un seul axe
ne crée pas nécessairement un personnage qui ne diffère que sur cet axe. Elle peut aussi
refléter des associations narratives du livre — aider implique souvent de prendre un
risque et d'agir physiquement. Elle ne doit pas être présentée comme une erreur certaine
de la phase 1 ou du LLM.

## Génération et validation

```bash
uv run python scripts/5.5_build_phase5_presentation.py --book LW01
uv run python scripts/tests/test_5_5_build_phase5_presentation.py --book LW01
```

Les fichiers sont écrits dans `results/phase5/LW01/presentation/`. Les PNG mesurent
exactement 1920 × 1080 pixels et les SVG conservent du texte éditable. Le manifeste fixe
le plan des quatre positions, marque les slides de procédure comme encore à produire et
archive les empreintes de toutes les sources et sorties.

Le validateur contrôle les dimensions, les titres anglais, les six chiffres affichés, les
diagnostics individuels, les six comparaisons et toutes les empreintes. Les deux slides ont
également été inspectées visuellement après leur génération.
