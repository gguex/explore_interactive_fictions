# Presentation draft

> **Format visé :** 20 minutes, environ 17 diapositives et 18–19 minutes de contenu
> préparé. Les titres et figures seront en anglais ; les notes ci-dessous restent en
> français. La présentation suit les six étapes de la recherche, mais chaque section doit
> faire avancer une même question plutôt que décrire successivement des scripts.

## Question directrice

> **How can we build a profile-dependent probabilistic model of a gamebook, and do its
> structural differences become perceptible in complete stories?**

Fil narratif général :

```text
gamebook text
    → semantically annotated choices
    → profile-dependent probabilistic graph
    → structural BoP measurements
    → perceived differences between complete stories
```

## 1. Introduction — 4 slides, environ 4 minutes

### Slide 1 — Titre et question de recherche

**Titre possible :** *From gamebook graphs to narrative experience*

- Présenter en une phrase les fictions interactives et les livres-jeux.
- Annoncer immédiatement la question : différents profils de joueurs produisent-ils des
  structures et des histoires perceptiblement différentes ?
- Ne pas commencer par le détail du pipeline.

**Message oral :** un même livre matériel contient de nombreuses histoires possibles,
mais toutes ne sont ni également probables ni également accessibles à tous les types de
joueurs.

**Temps maximal :** 30–45 secondes.

### Slide 2 — Le graphe et son angle mort

**Titre possible :** *A graph captures choices—but loses their meaning*

- Expliquer la représentation habituelle : paragraphes = nœuds, renvois = arêtes.
- Montrer ce que le graphe permet déjà d'étudier : accessibilité, embranchements,
  centralité, fins.
- Exposer sa limite : deux arêtes restent structurellement identiques même si l'une
  consiste à secourir quelqu'un et l'autre à fuir.
- Introduire la solution générale : réintégrer le contenu textuel par une annotation
  sémantique contrôlée.

**Visuel suggéré :** un court paragraphe avec deux choix à gauche, le même embranchement
non annoté à droite.

**Temps maximal :** 60 secondes.

### Slide 3 — Corpus et frontière du modèle

**Titre possible :** *Lone Wolf 1 as a controlled case study*

- Présenter brièvement *Flight from the Dark* : 350 paragraphes narratifs, choix,
  disciplines Kai, combats, objets, argent, endurance et hasard.
- Distinguer clairement trois niveaux :
  - **modélisé sémantiquement :** `risk`, `morality`, `action` ;
  - **simplifié par une probabilité fixe :** victoire en combat, fuite, disciplines Kai et
    `has_condition` ;
  - **non simulé dynamiquement dans cette itération :** inventaire détaillé, évolution de
    l'endurance et difficulté variable des combats.
- Mentionner la probabilité de victoire fixe `0.833` comme hypothèse calibrée et non comme
  règle générale des livres-jeux.

**Précaution :** présenter ces choix comme la frontière explicite du modèle, pas comme une
reconstitution exhaustive du système de jeu.

**Temps maximal :** 60–75 secondes.

### Slide 4 — Question resserrée, LLM local et pipeline

**Titre possible :** *An auditable pipeline from text to trajectories*

- Montrer les cinq phases appliquées à LW01 : annotation, prégraphe, compilation des
  profils, indices BoP, analyse des trajectoires complètes.
- Expliquer pourquoi utiliser des modèles locaux :
  - souveraineté et absence de dépendance à une API commerciale ;
  - version exacte des poids et paramètres archivée ;
  - coût reproductible ;
  - compatibilité avec une démarche critique en Humanités numériques.
- Ne pas dire qu'un modèle local est intrinsèquement transparent. L'auditabilité vient du
  prompt lisible, des sorties contraintes, des preuves textuelles, de la supervision et de
  la calibration humaine.

**Message oral :** le LLM est utilisé comme instrument d'annotation documenté, jamais
comme lecteur omniscient ni comme arbitre final de la qualité littéraire.

**Temps maximal :** 75 secondes.

## 2. Annotation des paragraphes — 2 slides, environ 2 minutes 30

### Slide 5 — Du texte aux choix sémantiquement annotés

**Titre possible :** *Recovering the semantics of local choices*

- Montrer les prétraitements : texte XML, paragraphes, choix et destinations.
- Présenter un exemple réel avec les trois axes :
  - `risk`: cautious / neutral / reckless ;
  - `morality`: selfish / neutral / noble ;
  - `action`: physical / neutral / tactical.
- Montrer les autres champs structurés nécessaires : type de transition, combat, fuite,
  condition, avertissement et justification.
- Préciser que le LLM n'attribue pas directement les probabilités finales et ne construit
  pas seul le graphe.

**Visuel suggéré :** un paragraphe court, ses choix et l'objet JSON correspondant, plutôt
qu'un schéma technique complet.

**Temps maximal :** 75 secondes.

### Slide 6 — Affinement du prompt et contrôle de l'extraction

**Titre possible :** *Prompt refinement remains inspectable*

- Résumer l'annotation en deux temps : petit modèle local, puis supervision explicite des
  cas non couverts ou ambigus.
- Expliquer que le prompt est lisible et reste générique : aucune règle ne doit apprendre
  un paragraphe particulier pour améliorer artificiellement le résultat.
- Donner les résultats objectifs de l'extraction : 556 arêtes attendues et extraites,
  couverture complète des balises `<choice>`, graphe atteignable et aucune violation du
  schéma final.
- Ne pas présenter la concordance sur le petit échantillon humain comme une accuracy hors
  échantillon.

**Message oral :** l'automatisation accélère le passage du texte à la donnée, mais les cas
non interprétables restent visibles au lieu d'être silencieusement forcés.

**Temps maximal :** 75 secondes.

## 3. Prégraphe et pondération selon un profil — 2 slides, environ 2 minutes

### Slide 7 — Des annotations au graphe probabiliste

**Titre possible :** *One symbolic pregraph, many player profiles*

- Expliquer la séparation entre :
  1. le prégraphe symbolique indépendant du profil ;
  2. le profil numérique ;
  3. la matrice compilée \(W(\text{profile})\).
- Montrer un seul choix contrasté, par exemple cautious / reckless, et la manière dont les
  poids sont normalisés entre les arêtes disponibles.
- Donner l'équation intuitive d'une trajectoire :

\[
P(\pi \mid \text{profile}) = \prod_{(i,j)\in\pi} W_{ij}(\text{profile}).
\]

- Mentionner que les mécanismes fixes restent des paramètres génériques et documentés,
  pas des constantes cachées propres à LW01.

**Temps maximal :** 75 secondes.

### Slide 8 — Le graphe compilé

**Titre possible :** *LW01 — graph*

- Afficher le graphe longitudinal avec le profil neutre.
- Expliquer brièvement les couleurs des nœuds : départ, combat, mort, victoire et nœuds
  ordinaires.
- Donner uniquement les dimensions utiles : 352 nœuds et 602 multiarêtes, deux états
  absorbants `Win` et `Death`.
- Utiliser cette slide comme transition visuelle vers l'analyse BoP.

**Visuel existant :** `results/phase4/LW01/graph_neutral_neutral_neutral_slide.png`.

**Temps maximal :** 40–50 secondes.

## 4. Le formalisme Bag-of-Paths — 4 slides, environ 4 minutes 30

### Slide 9 — Intuition et indices retenus

**Titre possible :** *Bag-of-Paths aggregates all possible trajectories*

- Présenter BoP comme une distribution sur les marches possibles du graphe, biaisée par
  les poids de \(W\), plutôt que comme la recherche d'un chemin unique.
- Expliquer les trois questions retenues :
  - quels passages sont importants ?
  - où se concentre la mortalité ?
  - quelles parties et propriétés changent selon le profil ?
- Distinguer en une phrase les indices locaux et globaux.
- Éviter le catalogue complet des indices et les développements mathématiques détaillés.

**Temps maximal :** 75 secondes.

### Slide 10 — Profils, survie et liberté narrative

**Visuel existant :**
`results/phase4/LW01/presentation/01_profile_landscape.png`.

**Message oral :**

> Player profiles substantially change both survival and the paths encountered; in this
> design, greater survival is associated with greater trajectory entropy rather than a
> survival–freedom trade-off.

Rappeler qu'il s'agit des 27 profils configurés et non d'une population observée.

**Temps maximal :** 50–60 secondes.

### Slide 11 — Effets marginaux des trois axes

**Visuel existant :** `results/phase4/LW01/presentation/02_axis_effects.png`.

**Message oral :** `risk` est l'axe structurel dominant ; `morality` et `action` ont des
effets plus faibles mais non nuls sur la survie, l'entropie, la couverture et la
rejouabilité.

**Temps maximal :** 50–60 secondes.

### Slide 12 — Localisation dans le graphe

**Visuel existant :** `results/phase4/LW01/presentation/03_local_index_maps.png`.

**Message oral :** le cœur narratif, les principaux goulets de mortalité et les zones les
plus sensibles au profil ne correspondent pas aux mêmes parties du graphe.

Ne commenter que quelques nœuds exemplaires ; ne pas lire les trois classements complets.

**Temps maximal :** 60–75 secondes.

## 5. Analyse de trajectoires complètes — 4 slides, environ 4 minutes 30

### Slide 13 — Pourquoi et comment sélectionner les trajectoires

**Titre possible :** *From structural differences to complete stories*

- Faire la transition : BoP montre que la distribution des chemins change, mais pas
  encore si les histoires complètes produisent une impression différente.
- Présenter le plan `7 profils × 2 issues = 14` trajectoires centrales.
- Pour chaque cellule, tirer 2 000 trajectoires conditionnées par `Win` ou `Death` avec la
  transformation de Doob.
- Sélectionner le médoïde empirique par distance LCS normalisée entre suites de
  paragraphes.
- Expliquer que le médoïde est une trajectoire observée et centrale, sans biais mécanique
  en faveur des chemins courts comme le MAP.

**Visuel suggéré :** un entonnoir `2 000 paths → distance matrix → one medoid`, puis la
grille `7 × 2`.

**Temps maximal :** 75 secondes.

### Slide 14 — Annotation aveugle et calibration P01–P03

**Titre possible :** *Treating the local LLM as a calibrated instrument*

- Montrer ce que Qwen3.6-27B reçoit : uniquement les histoires complètes, les choix
  admissibles et des identifiants opaques.
- Montrer ce qu'il ne reçoit pas : profils générateurs, issue comme métadonnée, poids,
  annotations de phase 1 ou indices BoP.
- Résumer la calibration humaine : quatre trajectoires et trois paires.
- Montrer l'itération :
  - P01 : 14 preuves mécaniques inadmissibles ;
  - P02 : règle renforcée, mais deux sorties mises en quarantaine ;
  - P03 : séparation explicite choix / transition résolue, sept sorties valides et zéro
    preuve inadmissible ;
  - gel du prompt avant le run final de 26 tâches.
- Présenter les 32 concordances sur 44 champs comme une concordance de calibration, jamais
  comme une accuracy ou une validation hors échantillon.

**Temps maximal :** 75 secondes.

### Slide 15 — Résultats individuels

**Visuel existant :**
`results/phase5/LW01/presentation/01_individual_trajectories.png`.

**Message oral :**

> Complete trajectories preserve causal continuity, but the intended player profile is
> unevenly perceptible: risk is recovered more often than morality, while action is
> strongly biased toward a tactical reading.

Bien distinguer l'adéquation absolue au niveau générateur d'une mesure de performance du
LLM.

**Temps maximal :** 50–60 secondes.

### Slide 16 — Comparaisons de trajectoires

**Visuel existant :**
`results/phase5/LW01/presentation/02_trajectory_comparisons.png`.

**Message oral :**

> Relative profile contrasts are visible in five of the six designed pairs, but the
> off-axis shifts show that risk, morality and action do not remain narratively
> independent.

Expliquer que résultats individuels et pairwise répondent à deux questions différentes :
reconnaître un profil absolu dans une histoire, puis percevoir une différence relative
entre deux histoires.

**Temps maximal :** 60–70 secondes.

## 6. Conclusions — 1 slide, environ 1 minute 30

### Slide 17 — Conclusions, limites et prolongements

**Titre possible :** *A reproducible bridge between choices, structure and stories*

**Trois conclusions :**

1. les profils modifient substantiellement la structure probabiliste du livre ;
2. ces différences deviennent généralement perceptibles dans les histoires complètes ;
3. les axes `risk`, `morality` et `action` ne restent pas narrativement orthogonaux.

**Trois limites :**

1. un seul livre étudié ;
2. probabilités mécaniques et état du personnage simplifiés ;
3. calibration humaine réduite, sans jeu de validation séparé.

**Prolongement principal :** appliquer à LW02 le même pipeline et le prompt gelé afin de
tester la transférabilité plutôt que de recalibrer sur un nouveau livre.

**Phrase finale proposée :**

> The contribution is not an LLM that “understands” literature, but an auditable pipeline
> connecting local choices, probabilistic structure and complete narrative experience.

**Temps maximal :** 75–90 secondes.

## Budget temporel récapitulatif

| Partie | Slides | Temps visé |
| :--- | :---: | ---: |
| Introduction | 1–4 | 4:00 |
| Annotation des paragraphes | 5–6 | 2:30 |
| Prégraphe et profils | 7–8 | 2:00 |
| Bag-of-Paths | 9–12 | 4:30 |
| Trajectoires complètes | 13–16 | 4:30 |
| Conclusion | 17 | 1:30 |
| **Total préparé** | **17** | **19:00** |

La minute restante sert aux transitions, aux variations de débit et à une éventuelle
question brève. Si une coupe devient nécessaire, fusionner les slides 3 et 4 ou réduire
la théorie BoP de la slide 9 ; ne pas supprimer les deux slides de résultats de phase 5.
