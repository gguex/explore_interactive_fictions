# Plan global — Distant reading des fictions interactives

> Document de référence mis à jour le 17.08.2026. La modélisation retenue est définie
> dans [`graph_model.md`](graph_model.md), l'avancement dans
> [`progress_log.md`](progress_log.md), et les documents remplacés dans
> [`archives/`](archives/).

## 1. Question de recherche

**Comment étudier les fictions interactives par des méthodes de distant reading, en
combinant l'analyse structurelle — notamment Bag-of-Paths (BoP) — et l'analyse
sémantique par les LLM ?**

Le cadre relie trois échelles : transitions locales, organisation du graphe et histoires
produites par les chemins.

## 2. Objectif et périmètre

La méthode doit s'appliquer à plusieurs formes de récits à embranchements. *Lone Wolf 01*
(LW01) est le premier cas d'étude, pas le modèle universel.

Deux livrables sont visés :

1. une présentation COMHUM2026 démontrant le cadre sur LW01 ;
2. un article approfondissant la méthode et sa validation sur d'autres corpus.

Le projet représente les effets narratifs des mécaniques sans simuler leurs règles
internes. Les ressources persistantes, trop spécifiques et coûteuses, restent des
extensions facultatives.

## 3. Décisions de modélisation

### 3.1 Niveaux L0–L3

| Niveau | Information | Décision |
| :--- | :--- | :--- |
| L0 — Topologie | Unités narratives, liens, entrées et fins. | Socle obligatoire. |
| L1 — Agentivité | Actions, transitions automatiques, disponibilités et caractéristiques sémantiques. | Inclus. |
| L2 — Incertitude | Conséquences déterministes, probabilités exactes ou paramètres. | Inclus. |
| L3 — État persistant | Santé, inventaire, monnaie, relations et autres variables mémorisées. | Non implémenté. |

L0–L2 suffisent pour comparer structures, politiques de choix et distributions de
chemins. L3 ferait croître le graphe et imposerait les règles particulières de chaque
œuvre ; il est donc hors du périmètre actuel.

### 3.2 Multigraphe direct

Le graphe contient :

- les nœuds narratifs du corpus ;
- quelques terminaux synthétiques pour les issues sans paragraphe cible ;
- des multiarêtes directes entre ces nœuds.

Aucun nœud intermédiaire n'est créé pour les tirages, combats ou résolutions. Plusieurs
conséquences d'une même action partagent un `action_id` :

```text
10 ── action=fight, q ─────▶ 20
10 ── action=fight, 1-q ───▶ Death
10 ── action=escape, 1 ─────▶ 30
```

Ce choix conserve des chemins composés uniquement de passages réellement lus, simplifie
les indices narratifs et suffit pour le calcul matriciel.

### 3.3 Politique et conséquences

Un scénario détermine d'abord les actions disponibles. Une politique `π_s(a | i)` choisit
entre elles, puis `q_s(e | a)` distribue les conséquences de l'action :

```text
P_ref(e) = π_s(a | i) × q_s(e | a)
```

Une condition n'est pas une probabilité : elle active ou désactive une action. Une
probabilité inconnue reste un paramètre explicite soumis à une analyse de sensibilité.

### 3.4 Mécaniques

- Topologie, fins, choix, conditions et hasard sont modélisés dans L0–L2.
- Les combats et évasions sont réduits à leurs conséquences directes, exactes ou
  paramétrées.
- Les compétences déterminent la disponibilité dans un scénario.
- Les dépendances exactes à l'endurance, aux objets, à l'inventaire, à la monnaie, aux
  repas et à l'équipement relèvent de L3 et ne sont pas simulées.
- Les liens cachés ne sont ajoutés que si leur cible est vérifiable et documentée.

Ces décisions sont détaillées et justifiées dans
[`graph_model.md`](graph_model.md#6-traitement-des-mécaniques-de-lone-wolf).

### 3.5 Sémantique et playstyles

Les axes `risk`, `morality` et `action` déjà extraits pour LW01 sont conservés. Ils sont
propres au cas d'étude et ne constituent pas une ontologie universelle. Un autre corpus
peut employer d'autres axes ou aucun playstyle.

### 3.6 Interface Bag-of-Paths

Pour chaque scénario, le compilateur fournit `P_ref` et les caractéristiques nécessaires
à une matrice de coûts `C`. Pour les multiarêtes entre `i` et `j` :

```text
W_ij = Σ_{e:i→j} P_ref(e) × exp(-θ C(e))
```

Les conséquences d'une même action partagent son coût. Le rôle exact de `θ`, la relation
entre politique locale et pondération globale, et les indices BoP seront définis dans une
étape dédiée.

## 4. Conservation de la phase 1

La phase 1 reste immuable : HTML, JSON balisé, tables de nœuds et d'arêtes, annotations
LLM, gold, prompts, résultats et contrôles demeurent les sources de référence.

Une couche d'adaptation séparée convertira ces données en :

- `model_nodes` : nœuds narratifs et terminaux synthétiques ;
- `model_edges` : multiarêtes probabilistes regroupées par `action_id`.

Les conditions, warnings, combats et fins implicites seront revus avec une provenance
explicite, sans corriger silencieusement les données extraites.

## 5. Étapes de travail

### Phase 1 — Extraction LW01 — terminée

- 350 sections et 556 arêtes.
- Annotation structurelle et sémantique calibrée sur un jeu gold.
- Complétude, schéma et atteignabilité contrôlés.

### Phase 2 — Adaptation et compilation

1. fixer le schéma de `model_nodes` et `model_edges` ;
2. générer puis relire la table d'adaptation LW01 ;
3. traiter probabilités RNT, conditions, combats et issues implicites ;
4. produire une baseline et des scénarios de sensibilité ;
5. exporter le multigraphe, `P_ref`, l'interface de coûts et les validations.

### Phase 3 — Modèle probabiliste et playstyles

1. analyser la baseline uniforme ;
2. définir les politiques locales fondées sur les annotations existantes ;
3. vérifier normalisation, absorption, cycles et sensibilité ;
4. comparer les comportements produits par les profils.

### Phase 4 — BoP et indices

1. préciser les questions auxquelles BoP doit répondre ;
2. distinguer les résultats de chaîne de Markov des résultats proprement BoP ;
3. retenir un petit ensemble d'indices interprétables ;
4. valider les formules sur des graphes artificiels avant LW01.

### Phase 5 — Histoires et analyse LLM

1. sélectionner ou échantillonner des chemins représentatifs ;
2. reconstruire leur texte avec sa provenance ;
3. développer un protocole de critique LLM calibré ;
4. confronter résultats structurels et sémantiques.

### Phase 6 — Validation de la généralisabilité

Appliquer au moins L0–L1 à un second corpus de nature différente. Une validation limitée
mais réelle est préférable à une généralisabilité seulement déclarée.

## 6. Critères de qualité

- **Simplicité** : aucune structure sans nécessité empirique.
- **Généralisabilité** : aucune règle *Lone Wolf* dans le moteur central.
- **Traçabilité** : sources, adaptations, scénarios et résultats séparés.
- **Reproductibilité** : configurations, paramètres, graines et sorties versionnés.
- **Testabilité** : chaque niveau validé sur des exemples minimaux.
- **Interprétabilité** : chaque probabilité et indice répond à une question explicite.

## 7. Questions ouvertes

1. Quel rôle précis attribuer à BoP par rapport à la politique locale ?
2. Quels indices BoP répondent directement à la question de recherche ?
3. Quels scénarios retenir pour les paramètres inconnus de LW01 ?
4. Quel second corpus permettra de tester L0–L1 à faible coût ?

## 8. Documentation active

- `gamebook_global_plan.md` : objectifs, décisions et feuille de route ;
- `graph_model.md` : spécification du multigraphe et compilation ;
- `progress_log.md` : journal chronologique append-only ;
- `archives/` : documents et décisions remplacés.
