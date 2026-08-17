# Modélisation en graphe retenue

> **Décision méthodologique du 17.08.2026.** Ce document fixe la représentation utilisée
> après la phase 1. Il remplace la [première spécification](archives/graph_model_2026-08-13.md),
> devenue trop complexe, et complète le [plan global](gamebook_global_plan.md).

## 1. Objectif

Construire un graphe probabiliste qui :

- représente directement les parcours entre unités narratives ;
- distingue décisions du joueur, conditions et conséquences mécaniques ;
- reste applicable aux récits sans système de jeu élaboré ;
- fournit probabilités et coûts nécessaires à Bag-of-Paths (BoP) ;
- conserve la provenance des données de phase 1.

LW01 est le premier cas d'étude, pas le modèle universel.

## 2. Les niveaux L0–L3

| Niveau | Information | Statut |
| :--- | :--- | :--- |
| **L0 — Topologie** | Unités narratives, transitions, entrées et fins. | Socle obligatoire. |
| **L1 — Agentivité** | Actions du joueur, transitions automatiques, conditions de disponibilité et caractéristiques sémantiques. | Inclus dans le modèle central. |
| **L2 — Incertitude** | Conséquences déterministes, probabilités exactes ou paramètres inconnus. | Inclus dans le modèle central. |
| **L3 — État persistant** | Santé, inventaire, compétences acquises, monnaie, relations et autres variables mémorisées. | Extension non implémentée. |

L0–L2 suffisent pour comparer la structure, les choix et les distributions de chemins.
L3 demanderait des états `(unité narrative, état du joueur)`, ferait croître le graphe et
introduirait des règles propres à chaque œuvre. Il est donc exclu du périmètre actuel.

## 3. Graphe retenu

### 3.1 Nœuds

Le graphe contient seulement :

- les **nœuds narratifs** issus du corpus ;
- des **terminaux synthétiques** lorsque le texte implique une issue sans paragraphe
  cible, par exemple `Death` ou `Failure`.

Aucun nœud intermédiaire n'est créé pour un tirage, un combat ou une autre résolution.
Un chemin du graphe reste ainsi une suite de passages effectivement lus, suivie
éventuellement d'une issue synthétique.

### 3.2 Multiarêtes

Le graphe est un **multigraphe dirigé**. Chaque arête représente une conséquence possible
d'une action ou d'une transition automatique.

Champs minimaux de la table `model_edges` :

| Champ | Rôle |
| :--- | :--- |
| `edge_id` | Identifiant stable de la conséquence. |
| `action_id` | Regroupe les conséquences produites par une même action. |
| `source_id`, `target_id` | Origine et destination narratives ou terminales. |
| `control` | `player` ou `system`. |
| `availability` | Condition résolue par le scénario, ou `always`. |
| `probability_kind` | `deterministic`, `exact` ou `parameter`. |
| `probability_value` | Probabilité exacte si elle est connue. |
| `probability_parameter` | Nom du paramètre si elle est inconnue. |
| caractéristiques sémantiques | Axes disponibles pour l'action. |
| `source_refs` | Provenance dans les données et le texte. |

Les caractéristiques et le coût d'une action sont répétés sur ses différentes
conséquences. `action_id` permet de les reconnaître comme une seule décision.

### 3.3 Exemples

Transition déterministe :

```text
10 ── action=route, q=1 ──▶ 20
```

Tirage automatique :

```text
10 ── action=roll, q=0,5 ──▶ 20
10 ── action=roll, q=0,5 ──▶ 30
```

Combat abstrait :

```text
10 ── action=fight, q ─────▶ 20
10 ── action=fight, 1-q ───▶ Death
```

Combat avec évasion :

```text
10 ── action=fight, q ─────▶ 20
10 ── action=fight, 1-q ───▶ Death
10 ── action=escape, 1 ─────▶ 30
```

Ces représentations séparent les actions grâce à `action_id`, sans ajouter de nœud
technique.

## 4. Disponibilité, décision et conséquence

Pour un scénario `s`, soit `A_s(i)` l'ensemble des actions disponibles au nœud `i`.
La politique locale `π_s(a | i)` distribue la probabilité entre ces actions :

```text
Σ π_s(a | i) = 1  pour a dans A_s(i)
```

Pour une action `a`, les arêtes qui partagent son `action_id` décrivent ses conséquences :

```text
Σ q_s(e | a) = 1
P_ref(e) = π_s(a | i) × q_s(e | a)
```

La baseline distribue uniformément la masse entre les actions du joueur disponibles.
Une transition automatique unique reçoit une masse de 1.

Une condition n'est pas transformée en probabilité : le scénario rend l'action
disponible ou indisponible. Une probabilité mécanique inconnue devient un paramètre
explicite et fait l'objet d'une analyse de sensibilité.

## 5. Justification de la simplification

Le corpus LW01 contient 556 paragraphes de choix. Aucun ne contient plusieurs liens de
section dans un même paragraphe de choix. Les 19 paragraphes stochastiques ne mélangent
pas choix libre et tirage : le livre sépare déjà l'essentiel des décisions et des
résolutions.

Les [règles de combat de Project Aon](https://www.projectaon.org/en/ReadersHandbook/KaiCombat)
et leur [exemple appliqué à LW01](https://www.projectaon.org/en/ReadersHandbook/ExampleCombat)
confirment que le combat est un sous-processus mécanique. Le modèle en conserve les
issues narratives sans transformer ses rounds en nœuds du récit.

Même lorsqu'une action possède plusieurs conséquences, la multiplication
`π_s(a | i) × q_s(e | a)` donne directement le poids de chaque arête. Un nœud
intermédiaire n'ajouterait aucune information, mais compliquerait la longueur des chemins,
les probabilités de visite et leur interprétation narrative.

Les terminaux synthétiques restent nécessaires pour fermer une distribution lorsqu'une
issue, notamment une mort mécanique, n'a pas de paragraphe cible.

## 6. Traitement des mécaniques de *Lone Wolf*

| Mécanique | Décision | Représentation et justification |
| :--- | :--- | :--- |
| Topologie et fins | **Modélisées — L0** | Les paragraphes et liens sont le socle commun. Les fins écrites restent distinctes ; une issue implicite peut viser un terminal synthétique. |
| Table de hasard (RNT) | **Modélisée — L2** | Les plages 0–9 produisent des multiarêtes de probabilités exactes regroupées par `action_id`. Une séquence purement mécanique est réduite à sa distribution finale. |
| Combat | **Modélisé abstraitement — L2** | Victoire, défaite et autres sorties deviennent des arêtes directes d'une même action. La probabilité est paramétrée. Les rounds, Combat Skill et tables de combat ne sont pas simulés, car ils exigeraient L3 et sont spécifiques à LW. |
| Évasion | **Modélisée abstraitement — L1/L2** | L'évasion est une action distincte. Sa destination est directe ; son éventuel risque devient une distribution paramétrée. Le détail des rounds et dégâts est exclu. |
| Endurance, dégâts et soins | **Non modélisés — L3** | Ils demanderaient une expansion d'état et influenceraient les transitions futures. Les issues fatales restent toutefois représentées. |
| Disciplines et compétences | **Disponibilité — L1** | Une compétence active ou désactive une action dans un scénario. Elle n'est pas remplacée par une probabilité moyenne indépendante. |
| Objets de quête, clés et verrous | **Condition conservée — L1/L3** | L'action conditionnelle est identifiée. Sans inventaire persistant, des scénarios permissifs et restrictifs donnent des bornes ; une cohérence exacte demanderait L3. |
| Inventaire et capacité du sac | **Non modélisés — L3** | Leur espace d'états est combinatoire et très propre au système de jeu. |
| Monnaie | **Non modélisée — L3** | Accumulation et dépenses sont des variables persistantes comparables à l'inventaire. |
| Repas et survie | **Non modélisés — L3** | Ils combinent ressource, compétence et endurance. Leur présence peut rester une métadonnée. |
| Modificateurs d'équipement | **Non modélisés — L3** | Leur effet éventuel est absorbé par les paramètres des conséquences. Une simulation exacte serait spécifique à l'œuvre. |
| Énigmes et liens cachés | **Modélisés si la cible est vérifiable — L0/L1** | Le lien est ajouté avec une provenance manuelle. Sa résolution peut être une disponibilité de scénario ; aucune cible n'est inventée. |

Le modèle retient donc les propriétés transférables — topologie, agentivité, conditions et
incertitude — sans devenir un simulateur des règles de *Lone Wolf*.

## 7. Compatibilité avec Bag-of-Paths

Pour chaque scénario, le compilateur produit une matrice de référence `P_ref` et les
caractéristiques permettant de construire une matrice de coûts `C`.

Pour des arêtes parallèles entre `i` et `j` :

```text
W_ij = Σ_{e:i→j} P_ref(e) × exp(-θ C(e))
```

Toutes les conséquences d'une même action partagent le même coût d'action. Les
transitions automatiques ne reçoivent pas une préférence de joueur. Un éventuel coût de
longueur compte un passage narratif, ce qui est direct puisque le graphe ne contient pas
de nœuds de résolution.

Les choix exacts de `C`, de `θ` et des indices BoP restent à définir. Avant le calcul, il
faudra vérifier la normalisation, l'absorption et le rayon spectral de la partie
transitoire de `W`.

## 8. Compilation depuis la phase 1

La phase 1 reste immuable. Une couche d'adaptation produit deux tables :

- `model_nodes`, dérivée des nœuds narratifs et complétée par les terminaux synthétiques ;
- `model_edges`, dérivée des arêtes et complétée par les conséquences implicites.

### Étape 1 — Charger et valider

Charger `LW01_nodes.csv`, `LW01_e_edges.csv`, le JSON balisé et, pour les audits ciblés,
les HTML. Exécuter le contrôle qualité existant et attribuer un `edge_id` stable sans
modifier les données sources.

### Étape 2 — Appliquer les conversions sûres

| Type de phase 1 | Conversion initiale |
| :--- | :--- |
| `forced` | Arête système déterministe. |
| `explicit_choice` | Action joueur déterministe, annotations conservées. |
| `stochastic` | Arêtes d'une même action système, probabilités à calculer. |
| `conditional` | Revue : disponibilité d'action ou conséquence mécanique. |
| `complex` | Revue obligatoire ; cette catégorie est absente de LW01. |

### Étape 3 — Construire la table d'adaptation

Une table versionnée, séparée de la phase 1, fournit seulement les informations manquantes
ou corrigées :

- `action_id` ;
- rôle joueur/système ;
- disponibilité ;
- probabilité exacte ou paramètre ;
- conséquence terminale implicite ;
- provenance et justification.

La revue porte en priorité sur les arêtes `conditional`, les warnings, les combats et les
liens cachés. Une décision manuelle doit toujours citer le texte source.

### Étape 4 — Produire `model_nodes` et `model_edges`

Le convertisseur fusionne les règles sûres et la table d'adaptation. Il échoue si une
condition nécessaire n'est pas classée, si une probabilité n'a ni valeur ni paramètre, ou
si une décision manuelle n'a pas de provenance.

### Étape 5 — Compiler un scénario

La configuration fixe disponibilités, paramètres et politique. Le compilateur :

1. retire les actions indisponibles ;
2. normalise la politique entre les `action_id` restants ;
3. normalise les conséquences de chaque action ;
4. calcule `P_ref(e) = π_s(a | i) × q_s(e | a)` ;
5. agrège les multiarêtes pour les matrices ;
6. exporte graphe, matrices et manifeste du scénario.

### Étape 6 — Valider

Les contrôles minimaux sont :

- provenance de chaque nœud et arête ;
- somme de 1 entre actions disponibles puis entre conséquences d'une action ;
- aucune condition ou probabilité silencieusement irrésolue ;
- terminaux sans sortie pour BoP ;
- atteignabilité et absorption depuis chaque entrée ;
- rayon spectral compatible avec la matrice fondamentale ;
- résultats connus sur de petits multigraphes artificiels.

## 9. Produits attendus de la phase 2

1. le schéma de `model_nodes` et `model_edges` ;
2. une table d'adaptation LW01 relue ;
3. une baseline et des scénarios de sensibilité ;
4. un multigraphe compilé avec sa provenance ;
5. `P_ref`, l'interface de coûts et les tests de validation ;
6. un rapport des mécaniques volontairement non représentées.

Ce socle doit être validé avant l'implémentation des indices BoP.
