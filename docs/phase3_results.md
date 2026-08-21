# Phase 3 terminée — Résultats de compilation

## 1. Expérience compilée

Les 27 combinaisons de `risk`, `morality` et `action` ont été compilées avec la même
configuration fixe documentée dans `fixed_probabilities.md`. Chaque profil produit une
matrice $W^{(p)}$ de 352 nœuds et 602 arêtes.

Le compilateur ne modifie que les poids des choix annotés. Les disciplines Kai, le
combat, la fuite et les conditions persistantes restent identiques entre les profils.

## 2. Validation

Le validateur global contrôle pour chacune des 27 matrices :

- la conservation exacte des 602 arêtes du pré-graphe ;
- les distributions sortantes et leur agrégation dans $W$ ;
- les deux seuls absorbants `Death` et `Win` ;
- l'absorption éventuelle depuis chaque état transitoire ;
- des probabilités d'absorption finies et comprises dans $[0,1]$.

Les 27 matrices passent ces contrôles. L'erreur maximale de somme de ligne est
$1{,}11\times10^{-15}$.

## 3. Résultats par profil

Le profil entièrement neutre donne :

$$
P(Win)=0{,}119811,qquad
P(Death)=0{,}880189,
$$

avec 27,21 transitions attendues avant absorption.

Les extrêmes observés sont :

| Profil | $P(Win)$ | Transitions attendues |
| :--- | ---: | ---: |
| `cautious_selfish_physical` | **25,835 %** | 32,16 |
| `neutral_neutral_neutral` | 11,981 % | 27,21 |
| `reckless_selfish_tactical` | **5,440 %** | 24,72 |

L'étendue entre les extrêmes atteint 20,40 points de pourcentage. Le profil le plus
favorable gagne environ 4,75 fois plus souvent que le moins favorable : les coefficients
d'affinité actuels produisent donc un contraste global suffisant pour l'analyse.

## 4. Effets moyens des axes

Chaque ligne moyenne neuf profils, en faisant varier les deux autres axes :

| Axe | Niveau | $P(Win)$ moyen | Transitions attendues |
| :--- | :--- | ---: | ---: |
| Risque | cautious | 21,197 % | 30,30 |
| Risque | neutral | 11,968 % | 27,36 |
| Risque | reckless | 6,732 % | 25,75 |
| Moralité | selfish | 12,355 % | 26,77 |
| Moralité | neutral | 13,431 % | 27,89 |
| Moralité | noble | 14,111 % | 28,75 |
| Action | physical | 15,409 % | 29,04 |
| Action | neutral | 13,473 % | 27,71 |
| Action | tactical | 11,016 % | 26,66 |

Dans LW01, l'axe du risque est nettement dominant. Les parcours prudents survivent plus
souvent et durent davantage. L'effet moyen de la moralité est plus faible ; l'action
physique est ici associée à une meilleure réussite que l'action tactique. Ces résultats
décrivent le graphe annoté et ses pondérations : ils ne constituent pas une propriété
générale de ces comportements.

### Biais de la simplification des combats

Un contrôle exploratoire remplaçant la probabilité de victoire globale de 0,833 par les
taux estimés pour chaque paragraphe donne 11,60 % de victoire au profil neutre, contre
11,98 % dans le modèle courant. Le biais neutre paraît donc faible, mais le taux unique
tend surtout à rapprocher les profils de la moyenne : il pénalise les parcours évitant
les combats difficiles et favorise ceux qui les rencontrent. Ces valeurs restent des
probabilités internes au modèle L2, et non des probabilités exactes de terminer le livre.

**Phrase pour la présentation :** « Notre modèle surestime légèrement la probabilité de
victoire du profil neutre, de 11,60 % à 11,98 %, mais il comprime surtout les écarts :
notre contrôle suggère une sous-estimation d'environ 3,9 points pour le meilleur parcours
prudent et une surestimation pouvant atteindre 4,4 points pour un parcours téméraire. »

## 5. Intensité des choix

Les affinités `matching / neutral / opposed = 2 / 1 / 0.5` restent des préférences
souples. Entre deux options identiques sur les autres axes, une option correspondante et
une option opposée reçoivent respectivement 80 % et 20 % de la masse. Les profils ne
suivent donc pas mécaniquement une seule route, mais l'accumulation de ces préférences
produit déjà des résultats fortement contrastés. Les affinités sont conservées pour
l'itération actuelle.

## 6. Artefacts

- `data/processed/graph/LW01/<profile>/W.csv` : matrice de transition ;
- `data/processed/graph/LW01/<profile>/compiled_edges.csv` : arêtes pondérées ;
- `profile_summary.csv` : résultats et écarts au profil neutre pour les 27 profils ;
- `axis_summary.csv` : moyennes par niveau de chaque axe ;
- `profile_summary.json` : résumé compact et profils extrêmes.

Ces fichiers terminent la compilation de la phase 3. Ils constituent les entrées de la
phase 4 consacrée aux indices BoP ; les trajectoires complètes seront sélectionnées et
analysées par LLM dans la phase 5.
