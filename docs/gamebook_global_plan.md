# Plan global — Distant reading des fictions interactives

> Document de référence à partir du 13.08.2026. Les documents antérieurs sont conservés
> dans [`docs/archives/`](archives/). L'avancement est consigné dans
> [`progress_log.md`](progress_log.md). La représentation retenue est spécifiée dans
> [`graph_model.md`](graph_model.md).

## 1. Question de recherche

**Comment étudier les fictions interactives par des méthodes de distant reading, en
combinant l'analyse structurelle — notamment le formalisme Bag-of-Paths (BoP) — et
l'analyse sémantique par les LLM ?**

Le cadre doit relier trois échelles : les transitions locales, l'organisation globale du
graphe et les histoires produites par ses chemins.

## 2. Objectif et périmètre

L'objectif est une méthode applicable à plusieurs formes de récits à embranchements.
*Lone Wolf 01* (LW01) est le premier cas d'étude, pas le modèle universel.

Deux livrables sont visés :

1. une présentation COMHUM2026 démontrant le cadre sur LW01 ;
2. un article approfondissant la méthode et sa validation sur d'autres corpus.

La simulation détaillée des ressources persistantes est retirée du socle. Les combats et
autres mécaniques sont représentés par leurs conséquences, exactes ou paramétrées, sans
simuler leurs règles internes. Ce choix réduit les hypothèses propres à *Lone Wolf* et
rend la méthode transférable.

## 3. Principes de modélisation

### 3.1 Niveaux indépendants

| Niveau | Information représentée | Rôle |
| :--- | :--- | :--- |
| L0 — Topologie | Unités narratives, transitions, débuts et fins | Socle obligatoire pour toute fiction à embranchements. |
| L1 — Agentivité | Choix du joueur, transitions automatiques, conditions d'accès | Distingue ce que décide le joueur de ce que le système impose. |
| L2 — Incertitude | Résultats probabilistes, exacts ou paramétrés | Représente le hasard sans imposer une mécanique particulière. |
| L3 — État | Variables persistantes : santé, objets, compétences, relations, etc. | Extension optionnelle lorsque l'analyse l'exige. |

Le cœur du projet porte sur L0–L2. L3 reste une extension non implémentée pour la
présentation. Le périmètre de chaque mécanique est justifié dans
[`graph_model.md`](graph_model.md#4-traitement-des-mécaniques-de-lone-wolf).

### 3.2 Graphe minimal

La représentation par défaut est un **multigraphe dirigé** :

- un nœud représente une unité narrative ou une fin ;
- une arête représente une transition possible ;
- plusieurs arêtes entre deux nœuds restent possibles si elles correspondent à des
  actions différentes.

Le modèle canonique sépare les nœuds, les actions et leurs conséquences. Une arête peut
porter le contrôle de l'action, sa disponibilité, ses annotations et sa probabilité.

Une transition déterministe reste une arête directe. Un **nœud virtuel de résolution**
n'est ajouté que lorsqu'une même action peut produire plusieurs conséquences. Ce choix
évite un graphe biparti systématique tout en séparant, lorsque nécessaire, la décision du
joueur du résultat de cette décision.

```text
cas simple :     unité A ── action ──▶ unité B

cas composé :    unité A ── action ──▶ [résolution]
                                      ├── p ──▶ unité B
                                      └── 1-p ▶ fin C
```

Les nœuds virtuels sont générés au moment du calcul ; ils ne sont pas annotés manuellement
dans les données sources et n'ajoutent ni contenu ni coût narratif.

### 3.3 Disponibilité, décision et conséquence

Dans un scénario de calcul explicite, le modèle distingue trois opérations :

1. déterminer les actions disponibles dans le scénario étudié ;
2. choisir une action selon une politique de joueur ;
3. résoudre ses conséquences éventuelles.

Pour une action `a` au nœud `i`, la transition vers `j` peut ainsi se décomposer en :

```text
P(j | i) = P(a choisie | i, actions disponibles)
           × P(j | i, a choisie)
```

Cette factorisation empêche de confondre la préférence du joueur avec la réussite d'une
action. Une condition est résolue par le scénario, pas transformée en probabilité. Une
probabilité mécanique inconnue reste un paramètre soumis à une analyse de sensibilité ;
elle n'est pas fixée arbitrairement à 0,5.

### 3.4 Caractéristiques sémantiques et playstyles

Le principe général est qu'une action peut recevoir des caractéristiques sémantiques,
dont une politique de joueur peut favoriser certaines valeurs.

Les axes `risk`, `morality` et `action` déjà extraits pour LW01 sont conservés tels quels.
Ils constituent une application au corpus, pas une ontologie universelle. Un autre corpus
peut employer d'autres axes ou ne pas utiliser de playstyles. Cette souplesse évite de
faire dépendre le moteur de catégories propres à une œuvre.

### 3.5 Rôle de Bag-of-Paths

Le graphe compilé fournira à BoP une matrice de transition de référence `P_ref`, les
caractéristiques nécessaires à une matrice de coûts et une distinction entre nœuds
narratifs, virtuels et terminaux. Il faudra encore distinguer :

- une politique locale décrivant les décisions d'un joueur ;
- une pondération globale des chemins par leur coût dans BoP.

Ces deux formulations ne seront ni confondues ni supposées équivalentes sans démonstration.
Les coûts techniques des nœuds virtuels seront nuls. Les indices BoP seront choisis dans
une étape dédiée ; le présent plan ne les présuppose pas.

## 4. Conservation de la phase 1

La phase d'extraction existante reste inchangée : HTML, JSON intermédiaire, tables de
nœuds et d'arêtes, annotations LLM, jeu gold, prompts, résultats de calibration et contrôle
qualité demeurent les sources de référence.

Le nouveau modèle sera construit par une **couche d'adaptation** au-dessus des tables
existantes. Elle traduira les catégories actuelles (`forced`, `explicit_choice`,
`stochastic`, `conditional`) vers les objets `nodes`, `actions` et `outcomes`, sans
réécrire l'extraction validée. Les conditions, combats, avertissements et fins implicites
seront revus avec une provenance explicite.

## 5. Étapes de travail

### Phase 1 — Extraction LW01 — terminée

- Corpus de 350 sections et table de 556 arêtes.
- Annotation structurelle et sémantique par LLM, calibrée sur un jeu gold.
- Contrôle de complétude, de schéma et d'atteignabilité.
- Scripts, données et résultats conservés sans modification.

### Phase 2 — Adaptation et compilation

1. appliquer la spécification de [`graph_model.md`](graph_model.md) ;
2. construire et relire la table d'adaptation LW01 ;
3. produire les tables canoniques `nodes`, `actions`, `outcomes` ;
4. compiler une baseline et des scénarios de sensibilité ;
5. exporter le graphe, `P_ref`, l'interface de coûts et les contrôles.

La couche d'adaptation est la première implémentation : elle garde les hypothèses visibles
et testables sans modifier la phase 1.

### Phase 3 — Modèle probabiliste et playstyles

1. analyser et valider la baseline sans préférence sémantique ;
2. définir les politiques locales fondées sur les annotations existantes ;
3. vérifier normalisation, absorption, cycles et sensibilité aux paramètres ;
4. comparer les comportements produits par les profils.

La baseline permet de séparer l'effet du graphe de celui des hypothèses comportementales.

### Phase 4 — BoP et indices

1. préciser la question à laquelle BoP doit répondre ;
2. comparer la formulation BoP à la chaîne probabiliste locale ;
3. retenir un petit ensemble d'indices interprétables ;
4. vérifier les formules sur des graphes artificiels avant LW01.

Le choix des indices vient après le modèle afin d'éviter d'adapter artificiellement les
données à des mesures prédéfinies.

### Phase 5 — Histoires et analyse LLM

1. sélectionner ou échantillonner des chemins représentatifs ;
2. reconstruire leur texte avec une provenance complète ;
3. analyser leur cohérence et leurs propriétés narratives avec un protocole LLM calibré ;
4. confronter les résultats sémantiques aux résultats structurels.

### Phase 6 — Validation de la généralisabilité

Appliquer au moins L0–L1 à un second corpus de nature différente. Une validation limitée
mais réelle est préférable à une généralisabilité seulement déclarée.

## 6. Critères de qualité

- **Simplicité** : aucune structure complexe sans cas concret qui la nécessite.
- **Généralisabilité** : le cœur ne contient aucune règle propre à *Lone Wolf*.
- **Traçabilité** : données sources, conversions, hypothèses et paramètres restent séparés.
- **Reproductibilité** : configuration, graines, sorties et contrôles sont versionnés.
- **Testabilité** : chaque niveau est validé isolément sur des exemples minimaux.
- **Interprétabilité** : chaque probabilité et chaque indice répond à une question explicite.

## 7. Questions ouvertes immédiates

1. Quel rôle précis attribuer à BoP par rapport à la chaîne de Markov locale ?
2. Quels indices BoP répondent directement à la question de recherche ?
3. Quelles valeurs et quels scénarios retenir pour les probabilités inconnues de LW01 ?
4. Quel second corpus permettra de tester L0–L1 à faible coût ?

Ces questions doivent être tranchées et justifiées avant le développement correspondant.

## 8. Documentation du projet

- `gamebook_global_plan.md` : objectifs, modèle retenu et feuille de route actuelle ;
- `graph_model.md` : spécification L0–L3, périmètre mécanique et compilation du graphe ;
- `progress_log.md` : journal chronologique append-only ;
- futurs documents méthodologiques : indices BoP et protocole d'analyse LLM ;
- `archives/` : documents remplacés, conservés pour l'historique.

Le plan décrit l'état courant de la méthode ; le journal conserve l'évolution qui y a
conduit.
