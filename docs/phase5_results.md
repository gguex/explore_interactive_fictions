# Phase 5 — Premiers résultats de sélection des trajectoires

> **Statut au 26.08.2026 : étape 5.0 terminée pour LW01.** Les histoires ne sont pas
> encore reconstruites ni annotées. Le corpus canonique contient maintenant des
> **médoïdes empiriques conditionnels**, et non des trajectoires MAP.

## 1. Méthode et corpus produit

`scripts/5.0_select_medoid_trajectories.py` traite les sept profils contrôlés et les deux
issues. Dans chaque cellule profil–issue, il :

1. calcule les probabilités d'atteindre l'issue depuis chaque nœud ;
2. échantillonne 2 000 trajectoires complètes avec la transformation de Doob ;
3. mesure la distance séquentielle
   $d(A,B)=1-2\,LCS(A,B)/(|A|+|B|)$ entre suites de paragraphes ;
4. retient une trajectoire réellement observée qui minimise la distance moyenne pondérée
   à l'échantillon.

La graine de chaque cellule découle de la graine de base 42 et de sa position dans le plan
expérimental. Les chemins uniques et leurs effectifs sont archivés, de sorte que la
sélection puisse être auditée sans relancer le premier script. Les sorties sont :

- `data/processed/phase5/LW01/medoid_trajectories.jsonl` ;
- `data/processed/phase5/LW01/conditional_path_counts.jsonl` ;
- `data/processed/phase5/LW01/medoid_selection_report.json`.

Le validateur indépendant reconstruit chaque matrice depuis les multiarêtes, recalcule les
probabilités d'absorption, régénère les tirages depuis les graines et recalcule les 14
médoïdes.

## 2. Résultats

| Profil | Issue | Transitions | Chemins uniques / 2 000 | Distance moyenne | $P(\pi\mid o)$ |
| :--- | :--- | ---: | ---: | ---: | ---: |
| `neutral_neutral_neutral` | Win | 41 | 2 000 | 0,5382 | $2,24\times10^{-8}$ |
| `neutral_neutral_neutral` | Death | 31 | 1 676 | 0,6832 | $2,09\times10^{-7}$ |
| `cautious_neutral_neutral` | Win | 39 | 1 998 | 0,4095 | $9,76\times10^{-6}$ |
| `cautious_neutral_neutral` | Death | 28 | 1 674 | 0,6326 | $2,36\times10^{-6}$ |
| `reckless_neutral_neutral` | Win | 49 | 1 999 | 0,4776 | $2,65\times10^{-7}$ |
| `reckless_neutral_neutral` | Death | 19 | 1 499 | 0,6707 | $5,08\times10^{-4}$ |
| `neutral_selfish_neutral` | Win | 46 | 2 000 | 0,4886 | $4,89\times10^{-9}$ |
| `neutral_selfish_neutral` | Death | 29 | 1 665 | 0,6637 | $1,23\times10^{-5}$ |
| `neutral_noble_neutral` | Win | 42 | 2 000 | 0,5728 | $1,17\times10^{-7}$ |
| `neutral_noble_neutral` | Death | 32 | 1 674 | 0,6742 | $4,74\times10^{-7}$ |
| `neutral_neutral_physical` | Win | 47 | 2 000 | 0,5064 | $3,96\times10^{-9}$ |
| `neutral_neutral_physical` | Death | 30 | 1 745 | 0,6698 | $5,11\times10^{-7}$ |
| `neutral_neutral_tactical` | Win | 46 | 2 000 | 0,4964 | $9,40\times10^{-8}$ |
| `neutral_neutral_tactical` | Death | 30 | 1 584 | 0,6729 | $9,61\times10^{-6}$ |

## 3. Interprétation

- Les 14 médoïdes sont distincts. Les victoires comptent 39 à 49 transitions et les morts
  19 à 32 : les trajectoires de mort sont désormais utilisables comme histoires complètes
  et comme comparaisons entre profils.
- Les échantillons de victoire sont extrêmement dispersés : 13 997 chemins uniques sur
  14 000 tirages. Les morts totalisent 11 517 chemins uniques sur 14 000 tirages.
- Chaque médoïde sélectionné apparaît une seule fois. Il représente donc une **position
  centrale sous la distance choisie**, pas un chemin fréquent ou une majorité de joueurs.
- Le MAP est conservé uniquement dans le rapport comme diagnostic. Aucun MAP ne coïncide
  avec le médoïde ; ses morts ne comptent que trois transitions, contre 19 à 32 pour les
  médoïdes. Cela confirme son biais pratique en faveur des chemins courts dans ce corpus.

Un contrôle préliminaire avec une seconde graine sur le profil neutre avait donné des
médoïdes exacts différents, mais appartenant à des familles proches : similarité LCS de
0,759 pour `Win` et 0,831 pour `Death`. La sélection doit donc être appelée **médoïde
empirique**. Elle est reproductible avec la graine fixée, mais elle ne constitue ni le
médoïde exact de toute la distribution ni une mesure de sa dispersion.

## 4. Corpus narratif produit par 5.1

Les 14 histoires ont maintenant été reconstruites sous identifiants opaques, avec le texte
de chaque paragraphe, les options disponibles, l'action suivie et le type de transition.
Elles comptent 19 à 49 étapes et 2 005 à 5 854 mots. Les six paires extrême–extrême sont
matérialisées dans les deux ordres et leurs distances structurelles sont archivées.

Les conclusions du LLM porteront explicitement sur ces histoires représentatives
sélectionnées, pas sur toutes les trajectoires possibles. Les profils et issues restent
dans les métadonnées privées et ne figurent pas dans les corpus publics.
