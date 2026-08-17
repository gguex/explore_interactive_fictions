# Modélisation en graphe retenue

> **Décision méthodologique du 13.08.2026.** Ce document fixe la représentation utilisée
> après la phase 1. Il complète le [plan global](gamebook_global_plan.md) et remplace, pour
> la suite du projet, la stratégie spécifique à *Lone Wolf* décrite dans
> [l'ancienne note sur les mécaniques](archives/gamebook_mechanics_2026-07-14.md).

## 1. Objectif

Construire, à partir d'une fiction interactive, un graphe probabiliste qui :

- distingue les décisions du joueur des conséquences imposées par le système ;
- reste simple pour les récits sans mécanique complexe ;
- peut représenter le hasard sans simuler toutes les règles d'une œuvre ;
- fournit une matrice de référence et des coûts utilisables par Bag-of-Paths (BoP) ;
- conserve la provenance de chaque transformation depuis les données extraites.

LW01 sert de cas d'étude. Aucune règle propre à *Lone Wolf* ne doit être nécessaire au
moteur générique.

## 2. Les quatre niveaux

Les niveaux sont cumulatifs mais indépendants : un corpus peut s'arrêter au niveau dont
il a besoin.

### L0 — Topologie narrative

L0 décrit ce qui peut succéder à quoi :

- nœuds narratifs ;
- transitions dirigées ;
- nœuds initiaux ;
- fins et catégories de fins, lorsqu'elles existent.

L0 est obligatoire. Il ne suppose ni joueur probabiliste, ni hasard, ni état interne.

### L1 — Agentivité et disponibilité

L1 distingue :

- les **actions du joueur** ;
- les **transitions automatiques** du système ;
- les conditions qui rendent une action disponible.

Une condition n'est pas une probabilité. Elle est résolue par un scénario explicite :
par exemple, un personnage possède ou non une compétence. Plusieurs scénarios peuvent
être comparés lorsque l'information est inconnue.

L1 peut aussi porter des caractéristiques sémantiques sur les actions. Pour LW01, les
axes déjà extraits (`risk`, `morality`, `action`) sont conservés, sans être imposés aux
autres corpus.

### L2 — Incertitude et conséquences

L2 décrit les conséquences d'une action ou d'une transition automatique :

- une conséquence unique de probabilité 1 ;
- plusieurs conséquences de probabilités exactes ;
- plusieurs conséquences dépendant de paramètres déclarés.

Une probabilité inconnue n'est jamais remplacée implicitement par 0,5. Elle devient un
paramètre, étudié sur plusieurs valeurs ou scénarios.

### L3 — État persistant

L3 représente les variables mémorisées au cours d'une partie : santé, inventaire,
compétences, monnaie, relations, drapeaux narratifs, etc. Une représentation exacte
demanderait des états du type `(nœud narratif, état du joueur)`.

L3 est une extension, pas le socle du projet. Elle peut faire croître le graphe de manière
combinatoire et impose des règles propres à chaque œuvre. Elle n'est donc pas implémentée
pour la présentation COMHUM2026.

## 3. Objets du modèle

### 3.1 Représentation canonique

Avant compilation, le modèle contient trois tables logiques :

| Objet | Rôle | Champs minimaux |
| :--- | :--- | :--- |
| Nœud | Unité narrative ou fin | identifiant, type, catégorie terminale, provenance |
| Action | Ce que choisit le joueur ou déclenche le système | source, contrôle, disponibilité, caractéristiques, provenance |
| Conséquence | Résultat d'une action | action, cible, probabilité exacte ou paramètre, provenance |

Une action possède au moins une conséquence. Cette représentation sépare la probabilité
de **choisir** une action de la probabilité d'en obtenir un **résultat**.

### 3.2 Graphe compilé

Le graphe de calcul est un multigraphe dirigé. Le cas simple reste direct :

```text
unité A ── action déterministe ──▶ unité B
```

Un nœud virtuel de résolution est créé seulement si une même action possède plusieurs
conséquences :

```text
unité A ── action ──▶ [résolution de l'action]
                       ├── q ──▶ unité B
                       └── 1-q ▶ fin C
```

Les nœuds virtuels sont générés automatiquement. Ils ne contiennent aucun texte narratif
et n'ajoutent aucun coût narratif. Cette construction évite un graphe biparti généralisé
tout en empêchant de confondre choix et réussite.

Les actions parallèles entre deux mêmes nœuds restent distinctes dans le multigraphe.
Lors du passage à une matrice, leurs poids sont additionnés ; la représentation par
arêtes conserve leur identité et leurs annotations.

### 3.3 Politique et probabilités

Dans un scénario `s`, soit `A_s(i)` l'ensemble des actions disponibles au nœud `i`.
Une politique locale `π_s(a | i)` distribue la masse entre ces actions :

```text
Σ π_s(a | i) = 1  pour a dans A_s(i)
```

La baseline est uniforme entre les actions du joueur disponibles. Une transition
automatique unique reçoit une masse de 1. Les playstyles modifieront ensuite cette
politique à partir des caractéristiques sémantiques.

Pour chaque action `a`, les conséquences ont une distribution `q_s(j | i, a)` :

```text
Σ q_s(j | i, a) = 1
P_s(j | i) = Σ π_s(a | i) × q_s(j | i, a)
```

Le scénario regroupe toutes les hypothèses : actions disponibles, paramètres de réussite
et politique. Il rend les choix de modélisation reproductibles et comparables.

## 4. Traitement des mécaniques de *Lone Wolf*

Toutes les mécaniques recensées dans l'ancienne note sont prises en compte ci-dessous.
« Non modélisé » signifie que l'information peut être conservée comme métadonnée, mais
qu'elle ne modifie pas le graphe probabiliste du socle L0–L2.

| Mécanique | Décision | Représentation et justification |
| :--- | :--- | :--- |
| Topologie et fins | **Modélisées — L0** | Les paragraphes, liens et fins constituent le phénomène commun aux fictions à embranchements. Les fins explicites restent des nœuds terminaux distincts. Une fin mécanique implicite peut cibler un nœud terminal virtuel catégorisé. |
| Table de hasard (RNT) | **Modélisée — L2** | Les plages 0–9 donnent des probabilités exactes. Une séquence de tirages purement mécanique peut être réduite à sa distribution finale ou compilée avec des résolutions virtuelles. Ce mécanisme se généralise à tout dé ou tirage aléatoire. |
| Combat | **Modélisé abstraitement — L2** | Un combat devient une action ou une transition automatique avec des conséquences telles que victoire, défaite ou autre sortie. La probabilité de victoire est un paramètre si elle n'est pas directement calculable. Les rounds, le ratio de Combat Skill et la table de combat ne sont pas simulés : ils sont spécifiques à LW et exigeraient L3. |
| Évasion d'un combat | **Modélisée abstraitement — L1/L2** | L'évasion est une action du joueur menant à une sortie, éventuellement avec une probabilité de succès paramétrée. Le nombre de rounds requis et les dégâts subis avant la fuite ne sont pas simulés, car ils dépendent de l'état de combat. |
| Endurance, dégâts et soins | **Non modélisés — L3** | Ils nécessiteraient une expansion `(nœud, endurance)` et influencent plusieurs transitions futures. Leur coût et leur spécificité dépassent le besoin du modèle général. Les morts explicitement écrites et les issues fatales abstraites restent représentées. |
| Disciplines et compétences | **Modélisées comme disponibilité — L1** | Une compétence active ou désactive une action dans un scénario. Elle n'est pas remplacée par une probabilité moyenne indépendante. Ce modèle se généralise aux capacités, statistiques et drapeaux choisis avant la partie. |
| Objets de quête, clés et verrous | **Condition conservée, dépendance exacte non modélisée — L1/L3** | Le lien conditionnel est identifié. Sans inventaire persistant, on compare des scénarios permissifs/restrictifs ou on exclut le lien de certains calculs. Garantir qu'un objet a réellement été acquis demanderait L3. Cette limite doit être signalée dans les résultats. |
| Inventaire et capacité du sac | **Non modélisés — L3** | Les objets possédés, emplacements et abandons produiraient un espace d'états combinatoire et très dépendant du système de jeu. |
| Monnaie | **Non modélisée — L3** | Accumulation et dépenses sont des variables persistantes comparables à l'inventaire. Les modéliser n'apporterait rien au socle généralisable. |
| Repas et survie | **Non modélisés — L3** | Les repas combinent ressource, compétence et endurance. Leur effet est conservé comme métadonnée, mais ne modifie pas le graphe du socle. |
| Modificateurs d'équipement | **Non modélisés — L3** | Leur effet sur les statistiques et les combats est absorbé par les paramètres de résultat des scénarios. Une simulation exacte serait spécifique à l'œuvre. |
| Énigmes et liens cachés | **Modélisés topologiquement si la cible est identifiable — L0/L1** | Un lien implicite vérifiable est ajouté par une annotation complémentaire avec provenance manuelle. Sa résolution peut être traitée comme une disponibilité de scénario. Aucune cible ne doit être inventée lorsque le texte ne permet pas de la déterminer. |

Cette sélection conserve trois propriétés communes à de nombreux corpus : choix,
conditions et incertitude. Elle écarte la simulation des ressources persistantes, qui est
coûteuse, difficile à extraire et rarement comparable entre œuvres.

## 5. Compatibilité avec Bag-of-Paths

Pour chaque scénario, le compilateur produit :

- une indexation stable des nœuds ;
- une matrice de transition de référence `P_ref` ;
- les caractéristiques d'arêtes permettant de construire une matrice de coûts `C` ;
- la liste des nœuds initiaux, terminaux, narratifs et virtuels.

Pour une température `θ`, la matrice BoP pourra prendre la forme :

```text
W = P_ref ⊙ exp(-θ C)
```

Les choix précis de `C` et des indices BoP ne sont pas fixés ici. La séparation suivante
est toutefois obligatoire :

- le coût d'un playstyle porte sur l'arête correspondant à l'action du joueur ;
- une conséquence mécanique et un nœud virtuel ont un coût sémantique nul ;
- un coût de longueur compte une transition narrative, pas le nombre d'arêtes techniques ;
- les transitions automatiques ne reçoivent pas artificiellement une préférence de joueur.

Le multigraphe reste la source de vérité. Pour des arêtes parallèles, la matrice agrège les
poids `P_ref(e) × exp(-θ C(e))` entre la même paire de nœuds.

Les indices portant sur le récit seront calculés sur les nœuds narratifs ou reprojetés
sur eux. Les nœuds virtuels ne doivent pas être comptés comme des scènes, des choix
supplémentaires ou de la longueur narrative.

Avant tout calcul, il faudra vérifier la normalisation, l'absorption et le rayon spectral
de la partie transitoire de `W`. Les nœuds terminaux pourront être exportés sans arête
sortante pour BoP et avec une boucle de probabilité 1 pour les outils de chaînes de Markov.

## 6. Compilation depuis la phase 1

La phase 1 reste immuable. La compilation ajoute une couche distincte et traçable.

### Étape 1 — Charger et valider

Entrées :

- `LW01_nodes.csv` ;
- `LW01_e_edges.csv` ;
- le JSON balisé et les textes HTML pour les audits ciblés.

Le contrôle qualité existant est exécuté avant chaque compilation. Un identifiant stable,
dérivé du contenu et de son occurrence, est attribué à chaque arête source sans modifier
son CSV.

### Étape 2 — Appliquer les conversions sûres

| Type de phase 1 | Conversion provisoire |
| :--- | :--- |
| `forced` | Action système, conséquence déterministe. |
| `explicit_choice` | Action joueur, conséquence déterministe, annotations conservées. |
| `stochastic` | Conséquences d'une même résolution aléatoire, à grouper et probabiliser. |
| `conditional` | Cas à classifier : condition de disponibilité ou conséquence mécanique. |
| `complex` | Revue manuelle obligatoire ; cette catégorie est absente de LW01. |

Ces règles sont provisoires parce qu'un combat forcé peut avoir été extrait comme
`forced`, et « si vous gagnez » comme `conditional`. Le type actuel ne suffit donc pas à
compiler tous les cas sans audit.

### Étape 3 — Construire une table d'adaptation

Une table versionnée, séparée des données de phase 1, décrit uniquement les exceptions et
informations nécessaires au modèle :

- regroupement en `action_id` ;
- rôle joueur/système ;
- type et référence de disponibilité ;
- regroupement des conséquences ;
- probabilité exacte ou nom du paramètre ;
- fin implicite éventuelle ;
- provenance et justification.

La revue porte en priorité sur les arêtes `conditional`, les avertissements, les nœuds de
combat et les éventuels liens cachés. Une décision manuelle est autorisée, mais jamais
sans référence au texte source.

### Étape 4 — Produire les tables canoniques

Le convertisseur fusionne les règles sûres et la table d'adaptation pour produire des
tables `nodes`, `actions` et `outcomes`. Il doit refuser de continuer si une condition ou
une probabilité nécessaire reste silencieusement indéterminée.

### Étape 5 — Résoudre un scénario

Un fichier de configuration fixe :

- les disponibilités statiques, notamment les compétences ;
- le traitement des conditions dépendant d'un état non modélisé ;
- les paramètres de combat, d'évasion ou de résolution d'énigme ;
- la politique de décision, uniforme pour la baseline puis liée aux playstyles.

Plusieurs configurations constituent une analyse de sensibilité, pas plusieurs versions
des données.

### Étape 6 — Compiler le graphe et les matrices

Le compilateur :

1. retire les actions indisponibles ;
2. normalise la politique entre les actions restantes ;
3. crée les seuls nœuds virtuels nécessaires ;
4. affecte les probabilités de conséquence ;
5. exporte le multigraphe, `P_ref`, les caractéristiques de coûts et un manifeste complet.

### Étape 7 — Valider

Les contrôles minimaux sont :

- une provenance de phase 1 ou d'adaptation pour chaque objet ;
- une somme de 1 pour chaque politique et chaque distribution de conséquences ;
- aucune condition ni probabilité non résolue dans un scénario compilé ;
- des nœuds terminaux sans sortie dans la représentation BoP ;
- atteignabilité et absorption depuis chaque entrée ;
- rayon spectral compatible avec la matrice fondamentale ;
- coût nul et absence de contenu pour les nœuds virtuels ;
- résultats connus sur de petits graphes artificiels.

## 7. Produits attendus de la phase 2

1. une table d'adaptation LW01 relue ;
2. les tables canoniques `nodes`, `actions`, `outcomes` ;
3. au moins une configuration baseline et des scénarios de sensibilité ;
4. un graphe compilé avec sa provenance ;
5. `P_ref`, l'interface de coûts et les tests de validation ;
6. un rapport des mécaniques volontairement non représentées.

Ce socle doit être terminé avant de sélectionner les indices BoP.
