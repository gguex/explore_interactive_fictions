# Plan global — Distant reading des fictions interactives

> Document de référence mis à jour le 18.08.2026. La représentation du graphe et sa
> recette d'implémentation sont définies dans [`graph_model.md`](graph_model.md). Le suivi
> chronologique se trouve dans [`progress_log.md`](progress_log.md).

## 1. Question de recherche

**Comment étudier les fictions interactives par des méthodes de distant reading, en
particulier avec les LLM et les outils Bag-of-Paths (BoP) ?**

Le projet relie trois échelles :

1. les transitions locales entre unités narratives ;
2. les flux et l'organisation globale du récit ;
3. les histoires produites par les trajectoires.

## 2. Objectif et principe général

La méthode doit être applicable au plus grand nombre possible de fictions interactives.
*Lone Wolf 01* (LW01) est le premier cas d'étude, pas le modèle universel.

Deux livrables restent visés :

1. une présentation de 20 minutes démontrant le cadre sur LW01 ;
2. un article approfondissant la méthode et sa validation sur d'autres corpus.

Le projet représente les effets narratifs des mécaniques sans simuler leurs règles
internes. Le modèle central repose donc sur :

- les unités narratives ;
- leurs transitions ;
- des probabilités directement portées par ces transitions ;
- des matrices de marche aléatoire \(W\) décrivant différents profils et scénarios.

Les états persistants propres à un système de jeu restent hors du modèle central.

## 3. Périmètre de modélisation

### 3.1 Niveaux L0–L3

| Niveau | Information | Décision |
| :--- | :--- | :--- |
| **L0 — Topologie** | Unités narratives, transitions, entrées et fins. | Socle obligatoire. |
| **L1 — Agentivité** | Choix du joueur, passages automatiques, conditions et caractéristiques sémantiques. | Inclus. |
| **L2 — Incertitude** | Probabilités exactes, moyennes ou paramétrées. | Inclus. |
| **L3 — État persistant** | Santé, inventaire, monnaie, équipement, relations et autres variables mémorisées. | Non implémenté. |

L0–L2 permettent d'étudier des flux de lecture sans transformer le projet en simulateur
de jeu. L3 nécessiterait des états du type `(paragraphe, état du personnage)`, produirait
une forte expansion du graphe et limiterait la généralisabilité.

### 3.2 Graphe direct

Le graphe est un multigraphe dirigé contenant uniquement :

- les nœuds narratifs du corpus ;
- les fins narratives ;
- quelques terminaux synthétiques pour les issues sans paragraphe cible, notamment les
  morts implicites de combat.

Aucun nœud intermédiaire n'est créé pour un choix, un tirage, un combat ou sa résolution.
Chaque arête représente directement une transition possible entre deux nœuds.

### 3.3 Pondération directe par \(W\)

Pour un profil et un scénario donnés, chaque arête \(e:i\rightarrow j\) reçoit directement
un poids final \(w_e\). Les arêtes parallèles sont ensuite agrégées :

\[
W_{ij}=\sum_{e:i\rightarrow j}w_e.
\]

Il n'existe pas d'objet formel « action », pas d'`action_id` et pas de décomposition
séparée entre décision et conséquence. Les choix du joueur, le hasard, les disciplines
et les combats sont tous résolus dans les poids finaux des arêtes.

### 3.4 Usage de Bag-of-Paths

La première étude se place à la borne **Random Walk** du formalisme BoP :

- seule la matrice de marche \(W\) est utilisée ;
- aucune matrice de coûts \(C\) n'est construite à ce stade ;
- la borne Shortest Path n'est pas étudiée ;
- l'objectif est d'obtenir un flux moyen représentant un grand nombre d'aventures.

Pour la sous-matrice transitoire \(Q\), la matrice fondamentale est :

\[
N=(I-Q)^{-1}.
\]

Le choix des indices BoP est volontairement reporté jusqu'à ce que les matrices \(W\)
soient implémentées et validées.

## 4. Mécaniques retenues

### 4.1 Choix explicites et profils

Les annotations `risk`, `morality` et `action` déjà extraites pour LW01 servent à faire
varier directement les poids des arêtes de choix. Pour chaque nœud, ces poids sont
normalisés afin que la somme des transitions sortantes soit égale à 1.

Ces axes sont propres au cas d'étude. Un autre corpus peut utiliser d'autres annotations
ou une marche uniforme.

### 4.2 Hasard

Les intervalles de la table de hasard donnent directement les poids des arêtes. Les
séquences de plusieurs tirages sont aplaties en une distribution finale entre nœuds
narratifs et terminaux.

### 4.3 Disciplines et compétences

Deux traitements seront comparés :

1. **modèle moyen direct** : si cinq disciplines sont choisies parmi dix, une transition
   exigeant une discipline précise reçoit une disponibilité moyenne de \(5/10\) ;
2. **moyenne exacte des configurations** : une matrice \(W\) est compilée pour chacune
   des \(\binom{10}{5}=252\) configurations, puis les flux obtenus sont moyennés.

Cette comparaison mesurera l'erreur produite par l'approximation moyenne sans mémoire.

### 4.4 Combats et évasions

Les combats sont réduits à leurs transitions finales : victoire, mort et, si nécessaire,
évasion ou autre issue particulière. Les probabilités sont directement inscrites dans
\(W\) et peuvent varier selon le scénario de combat.

Les rounds, points d'Endurance et tables de combat ne sont pas simulés. Les scores des
ennemis restent disponibles comme métadonnées et permettront une extension ultérieure.

### 4.5 Mécaniques persistantes

L'Endurance, l'inventaire, la monnaie, les repas et l'équipement ne sont pas suivis dans
le modèle central. Leurs occurrences sont conservées comme métadonnées ou avertissements.

Les transitions exigeant un objet ou de l'argent sont conservées dans la topologie mais
résolues par des scénarios explicites : restrictif par défaut, permissif en sensibilité.
Cette convention évite de simuler un inventaire tout en documentant les chemins écartés.

## 5. Conservation de la phase 1

La phase 1 reste immuable : HTML, JSON balisé, tables de nœuds et d'arêtes, annotations
LLM, gold standard, prompts et contrôles demeurent les sources de référence.

Une couche dérivée produira :

- `model_nodes` : nœuds narratifs et terminaux synthétiques ;
- `model_edges` : arêtes directes avec règle de pondération et provenance ;
- une petite table de supervision contenant uniquement les exceptions ;
- une matrice \(W\) pour chaque profil et scénario retenu.

Aucune correction ne sera appliquée silencieusement aux données de phase 1.

## 6. Feuille de route

### Phase 1 — Extraction LW01 — terminée

- 350 sections et 556 arêtes ;
- annotation structurelle et sémantique calibrée sur un jeu gold ;
- complétude, validité des identifiants et atteignabilité contrôlées.

### Phase 2 — Construire le graphe et \(W\) — prochaine phase

1. lancer un script qui traite tous les cas ordinaires et produit une file d'exceptions ;
2. annoter les 18 paragraphes particuliers et renseigner un petit fichier de scénarios ;
3. lancer un second script qui fusionne les résultats, compile les scénarios de \(W\) et
   effectue quatre contrôles simples.

La recette exacte est donnée dans
[`graph_model.md`](graph_model.md#9-recette-courte).

### Phase 3 — Indices BoP — différée

Définir les indices seulement après validation de \(W\). Cette phase précisera les
questions interprétatives, les formules et les tests sur graphes artificiels.

### Phase 4 — Étude des trajectoires — différée

Définir ensuite la sélection des trajectoires et leur analyse sémantique par LLM ou par
d'autres méthodes.

### Phase 5 — Généralisation

Appliquer au moins L0–L1 à un second corpus différent afin de distinguer les règles
générales des adaptations propres à LW01.

## 7. Critères de qualité

- **Simplicité** : aucune structure intermédiaire sans nécessité empirique.
- **Généralisabilité** : aucune règle *Lone Wolf* dans le moteur central.
- **Traçabilité** : données sources, adaptations, scénarios et sorties séparés.
- **Reproductibilité** : scripts, supervision et paramètres versionnés.
- **Supervision explicite** : tout cas non reconnu bloque la compilation.
- **Interprétabilité** : chaque poids de \(W\) possède une règle et une provenance.

## 8. Questions reportées

Les questions suivantes ne doivent pas bloquer l'implémentation du graphe :

1. quels indices BoP retenir ;
2. comment les interpréter narrativement ;
3. comment sélectionner et analyser des trajectoires ;
4. comment articuler les indices et l'analyse LLM des histoires.

## 9. Documentation active

- `gamebook_global_plan.md` : objectifs, décisions et phases ;
- `graph_model.md` : spécification de \(W\), inventaire des cas et recette courte ;
- `progress_log.md` : journal chronologique ;
- `notes.md` : questions de travail non encore intégrées ;
- `archives/` : documents et décisions remplacés.
