# Plan global — Distant reading des fictions interactives

> Document de référence mis à jour le 19.08.2026. La représentation du pré-graphe et la
> compilation de $W$ sont définies dans [`graph_model.md`](graph_model.md). Le suivi
> chronologique se trouve dans [`progress_log.md`](progress_log.md).

## 1. Question de recherche

**Comment étudier les fictions interactives par des méthodes de distant reading, en
particulier avec les LLM et les outils Bag-of-Paths (BoP) ?**

Le projet relie trois échelles :

1. les transitions locales entre unités narratives ;
2. les flux et l'organisation globale du récit ;
3. les histoires produites par les trajectoires.

## 2. Objectif

La méthode doit être applicable au plus grand nombre possible de fictions interactives.
*Lone Wolf 01* (LW01) est le premier cas d'étude, pas le modèle universel.

Deux livrables sont visés :

1. une présentation de 20 minutes démontrant le cadre sur LW01 ;
2. un article approfondissant la méthode et sa validation sur d'autres corpus.

Le projet représente les effets narratifs des mécaniques sans simuler leurs règles
internes. Il sépare :

- l'extraction des paragraphes et transitions ;
- la construction d'un pré-graphe indépendant des profils ;
- la compilation d'une matrice $W^{(p)}$ pour chaque profil de joueur ;
- l'analyse BoP et l'étude des trajectoires.

## 3. Périmètre de modélisation

### 3.1 Niveaux L0–L3

| Niveau | Information | Décision |
| :--- | :--- | :--- |
| **L0 — Topologie** | Unités narratives, transitions, entrée et issues. | Inclus. |
| **L1 — Agentivité** | Choix, passages automatiques, conditions et annotations. | Inclus. |
| **L2 — Incertitude** | Hasard et règles probabilistes dépendant du profil. | Inclus. |
| **L3 — État persistant** | Santé, inventaire, monnaie, équipement et relations. | Non simulé. |

L0–L2 permettent d'étudier les flux sans transformer le projet en simulateur de jeu.
L3 nécessiterait des états `(paragraphe, état du personnage)`, produirait une forte
expansion du graphe et limiterait sa généralisabilité.

### 3.2 Pré-graphe direct

La phase 2 produit un multigraphe dirigé contenant :

- les paragraphes narratifs ;
- les paragraphes de fin, traités comme pré-terminaux ;
- un unique nœud terminal `Death` ;
- un unique nœud terminal `Win` ;
- des arêtes directes avec une règle de pondération constante ou symbolique.

Les 16 paragraphes de mort sont reliés à `Death` et le paragraphe de victoire à
`Win`. Les morts implicites, notamment après un combat perdu, pointent directement
vers `Death`. Seuls `Death` et `Win` sont absorbants.

Aucun nœud intermédiaire ne représente un choix, un tirage, un combat ou sa résolution.
Il n'existe ni `action_id`, ni couche « action–conséquence ».

### 3.3 Compilation de $W$

Le pré-graphe ne contient pas nécessairement les poids numériques finaux. Pour un profil
$p$, le compilateur évalue les règles et produit :

$$
(\mathcal G^\ast,p)\longmapsto W^{(p)}.
$$

Les arêtes parallèles sont agrégées :

$$
W_{ij}^{(p)}=\sum_{e:i\rightarrow j}w_e^{(p)}.
$$

Le profil contient les affinités de choix, les disciplines, les hypothèses de ressources,
les propensions d'évasion et les probabilités de victoire au combat. Plusieurs profils
peuvent donc être compilés sans modifier ni réannoter le pré-graphe.

### 3.4 Usage de Bag-of-Paths

La première étude se place à la borne **Random Walk** :

- seule $W^{(p)}$ est utilisée ;
- aucune matrice de coûts $C$ n'est construite à ce stade ;
- la borne Shortest Path n'est pas étudiée ;
- l'objectif est d'obtenir un flux moyen représentant un grand nombre d'aventures.

Avec les deux issues `Death` et `Win`, les probabilités d'absorption donnent
directement les probabilités de défaite et de victoire du profil.

Le choix des indices BoP est reporté jusqu'à la validation des matrices $W$.

## 4. Mécaniques retenues

### 4.1 Choix

Les annotations `risk`, `morality` et `action` servent à définir les affinités
du profil. Les poids sont normalisés localement. Une marche uniforme fournit le profil
de référence.

### 4.2 Hasard

Les intervalles de la table de hasard donnent des probabilités constantes. Les séquences
de tirages sont aplaties en une distribution finale.

### 4.3 Disciplines et compétences

Deux familles de profils seront comparées :

1. un profil moyen où une discipline précise a une disponibilité de $5/10$ ;
2. les $\binom{10}{5}=252$ configurations cohérentes de cinq disciplines.

Les matrices sont compilées séparément, puis les flux des configurations peuvent être
moyennés.

### 4.4 Combats et évasions

La chance de victoire $v_p(i)$ au combat $i$ reste libre et dépend du profil. Le
pré-graphe contient seulement les règles symboliques de victoire, mort, évasion ou autre
issue. Le compilateur refuse un profil auquel il manque une valeur nécessaire.

Les rounds, l'Endurance et les tables de combat ne sont pas simulés. Les caractéristiques
des ennemis restent disponibles et pourront plus tard servir à calculer $v_p(i)$.

### 4.5 État persistant

L'Endurance, l'inventaire, la monnaie, les repas et l'équipement ne sont pas suivis. Leurs
occurrences restent des métadonnées. Lorsqu'une condition simple peut être isolée —
possession d'un objet, montant minimal de Gold Crowns ou seuil d'Endurance — elle est
conservée par une règle symbolique sans reconstituer l'état du personnage.

Quand une transition dépend d'une ressource, le profil porte l'hypothèse retenue via
`condition_available(type, value)`, par exemple restrictive ou permissive. Cela permet
des analyses de sensibilité sans étendre les nœuds par l'état complet du personnage. Les
conditions composées ou ambiguës restent soumises à supervision.

## 5. Conservation de la phase 1

La phase 1 reste immuable : HTML, JSON balisé, tables de nœuds et d'arêtes, annotations
LLM, gold standard, prompts et contrôles demeurent les sources.

La phase 2 crée une couche dérivée :

- `pregraph_nodes.csv` ;
- `pregraph_edges.csv` ;
- un tableau de supervision limité aux exceptions ;
- un rapport de conversion.

Aucune correction n'est appliquée aux fichiers de phase 1.

### 5.1 Chaîne commune aux livres *Lone Wolf*

Tous les scripts numérotés utilisent `--book <BOOK_ID>` et la même convention :

```text
data/raw/<BOOK_ID>/sections/
data/processed/nodes_edges/<BOOK_ID>/<BOOK_ID>_nodes.csv
data/processed/nodes_edges/<BOOK_ID>/<BOOK_ID>_e_edges.csv
data/processed/pregraph/<BOOK_ID>/
data/for_graph_model/<BOOK_ID>_supervision.csv
```

La chaîne de production ne contient ni identifiants de paragraphes ni volumes attendus
propres à LW01. Les attentes connues pour un corpus sont isolées dans `scripts/tests/`.
La généralisation à d'autres familles de fictions pourra ensuite adapter les parseurs de
phase 1 sans modifier le principe du pré-graphe.

## 6. Feuille de route

Les scripts du pipeline suivent la convention `<phase>.<ordre>_<action>.py`. Leur nom
indique ainsi directement leur place dans cette feuille de route.

### Phase 1 — Extraction LW01 — terminée

- 350 sections et 556 arêtes ;
- annotation structurelle et sémantique calibrée ;
- complétude, identifiants et atteignabilité contrôlés.
- scripts : `1.1_parse_for_edge_extraction.py --book <BOOK_ID>` et
  `1.2_parse_node.py --book <BOOK_ID>`.

### Phase 2 — Construire le pré-graphe — terminée pour LW01

La préparation produit 558 arêtes automatiques. Les 14 paragraphes particuliers ont été
annotés en 44 arêtes supervisées, puis la finalisation a produit 352 nœuds et 602 arêtes
de pré-graphe sans transition de phase 1 non classée.

La recette réutilisable pour un autre livre reste :

1. lancer `2.1_prepare_pregraph.py --book <BOOK_ID>`, qui traite les cas ordinaires,
   dont les conditions persistantes simples, produit la file d'exceptions et crée le
   tableau d'annotation vide ;
2. remplir le tableau pour les paragraphes particuliers du livre ;
3. lancer `2.2_finalize_pregraph.py --book <BOOK_ID>`, qui finalise et contrôle le
   pré-graphe.

La recette est donnée dans
[`graph_model.md`](graph_model.md#9-recette-courte-de-la-phase-2).

### Phase 3 — Compiler $W$ pour les profils

1. définir les profils dans un fichier de paramètres ;
2. laisser chaque profil fixer notamment ses affinités, ses disciplines et ses chances de
   victoire au combat ;
3. lancer `3.1_compile_w.py` pour compiler et contrôler une matrice $W^{(p)}$ par
   profil.

### Phase 4 — Analyses BoP et trajectoires — différée

Choisir les indices BoP, calculer les flux et probabilités d'absorption, puis sélectionner
et analyser les trajectoires. Les formules et interprétations seront fixées seulement
après validation de $W$.

### Phase 5 — Généralisation

Appliquer au moins L0–L1 à un second corpus différent afin de distinguer les règles
générales des adaptations propres à LW01.

## 7. Critères de qualité

- **Simplicité** : deux scripts courts pour produire le pré-graphe.
- **Séparation** : aucune hypothèse de profil figée dans le pré-graphe.
- **Généralisabilité** : aucune règle propre à LW dans le moteur central.
- **Traçabilité** : extraction, supervision, pré-graphe, profils et matrices séparés.
- **Supervision explicite** : tout paragraphe non reconnu bloque la finalisation.
- **Interprétabilité** : chaque poids de $W$ dérive d'une règle du pré-graphe et d'un
  profil identifié.

## 8. Questions reportées

Les questions suivantes ne bloquent pas la construction du pré-graphe :

1. quels indices BoP retenir ;
2. comment les interpréter narrativement ;
3. comment sélectionner et analyser les trajectoires ;
4. comment articuler les indices et l'analyse LLM des histoires.

## 9. Documentation active

- `gamebook_global_plan.md` : objectifs, décisions et phases ;
- `graph_model.md` : pré-graphe, annotation et compilation de $W$ ;
- `future_improvements.md` : limites connues et extensions reportées du pipeline ;
- `progress_log.md` : journal chronologique ;
- `notes.md` : questions de travail ;
- `archives/` : documents et décisions remplacés.
