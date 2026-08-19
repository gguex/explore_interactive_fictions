# Pré-graphe et compilation de $W$

> **Décision méthodologique du 19.08.2026.** La phase 2 produit un pré-graphe
> indépendant des profils. La matrice de marche $W^{(p)}$ est compilée seulement en
> phase 3 pour un profil $p$. LW01 possède exactement deux nœuds terminaux : `Death`
> et `Win`.

## 1. Objectif

Transformer les données extraites en phase 1 en un pré-graphe qui :

- conserve les paragraphes et leurs transitions directes ;
- décrit les mécanismes sans fixer prématurément leurs probabilités ;
- peut être compilé plusieurs fois pour différents profils de joueur ;
- reste simple et applicable à d'autres fictions interactives ;
- sépare clairement extraction, supervision et hypothèses de pondération.

LW01 sert de cas d'étude. Ses règles particulières ne doivent pas devenir celles du
moteur général.

## 2. Niveaux L0–L3

| Niveau | Information | Statut |
| :--- | :--- | :--- |
| **L0 — Topologie** | Unités narratives, transitions, entrée et issues. | Inclus. |
| **L1 — Agentivité** | Choix, passages imposés, conditions et annotations sémantiques. | Inclus. |
| **L2 — Incertitude** | Hasard et règles de pondération dépendant du profil. | Inclus sous forme symbolique dans le pré-graphe. |
| **L3 — État persistant** | Santé, inventaire, monnaie, équipement et autres variables mémorisées. | Non simulé. |

Le pré-graphe couvre L0–L2 sans reproduire tout le système de jeu. L3 demanderait des
états de la forme `(paragraphe, état du personnage)`, ce qui alourdirait fortement le
modèle et le rendrait dépendant de l'œuvre.

## 3. Le pré-graphe

Le résultat de la phase 2 est :

$$
\mathcal G^\ast=(V,E,\tau,\rho),
$$

où $V$ contient les nœuds, $E$ les transitions possibles, $\tau$ leur type et $\rho$
leur règle de pondération. Certaines règles sont constantes ; d'autres ne deviennent
numériques qu'après fourniture d'un profil.

### 3.1 Nœuds narratifs, pré-terminaux et terminaux

Le pré-graphe de LW01 contient :

- les 350 paragraphes du corpus ;
- parmi eux, 16 paragraphes pré-terminaux de mort et un paragraphe pré-terminal de
  victoire ;
- un unique nœud terminal `Death` ;
- un unique nœud terminal `Win`.

Un **pré-terminal** est un paragraphe de fin effectivement lu. Il est conservé comme
nœud narratif, puis relié par une arête de poids 1 à `Death` ou `Win`. Une mort
implicite sans paragraphe cible, par exemple après un combat perdu, pointe directement
vers `Death`.

Seuls `Death` et `Win` sont absorbants. Ils portent une boucle de poids 1 dans
$W$ ; le compilateur peut ajouter ces boucles à partir de la colonne `absorbing`, sans
les stocker dans le pré-graphe. Les deux issues ne sont pas incluses dans les statistiques
narratives. L'arête entre un pré-terminal et son issue peut également être ignorée lors
du calcul d'une longueur narrative.

`Death` et `Win` sont les deux **nœuds d'issue** communs ; aucun autre terminal
technique n'est ajouté. Dans un autre corpus, le même principe peut être étendu à
d'autres classes d'issues.

### 3.2 Arêtes directes

Chaque arête relie directement deux paragraphes, ou un paragraphe à `Death` ou
`Win`. Aucun nœud intermédiaire ne représente un choix, un tirage, un combat ou sa
résolution.

Plusieurs arêtes entre les mêmes nœuds peuvent être conservées dans le pré-graphe. Elles
sont additionnées seulement lors de la compilation :

$$
W_{ij}^{(p)}=\sum_{e:i\rightarrow j}w_e^{(p)}.
$$

Il n'existe ni `action_id`, ni couche « action–conséquence », ni décomposition
$\pi\times q$.

### 3.3 Table `pregraph_nodes`

| Champ | Rôle |
| :--- | :--- |
| `node_id` | Identifiant du paragraphe, ou `Death`/`Win`. |
| `node_kind` | `narrative`, `preterminal` ou `terminal`. |
| `outcome` | Vide, `death` ou `win`. |
| `absorbing` | Vrai uniquement pour `Death` et `Win`. |
| `source_ref` | Référence au paragraphe de phase 1 ou à la règle d'issue. |

Le texte et les métadonnées détaillées restent dans `LW01_nodes.csv`.

### 3.4 Table `pregraph_edges`

| Champ | Rôle |
| :--- | :--- |
| `edge_id` | Identifiant attribué automatiquement. |
| `source_id`, `target_id` | Extrémités de la transition. |
| `transition_kind` | `forced`, `profile_choice`, `random`, `kai`, `combat`, `escape`, `outcome` ou `manual`. |
| `weight_rule` | `constant`, `profile_choice` ou `formula`. |
| `weight_value` | Valeur d'une probabilité exacte, si elle existe déjà. |
| `weight_expression` | Règle symbolique évaluée avec le profil. |
| `condition_kind`, `condition_value` | Condition conservée si nécessaire. |
| `semantic_risk`, `semantic_morality`, `semantic_action` | Annotations utilisées pour les choix de profil. |
| `origin` | `auto` ou `supervised`. |
| `source_ref` | Provenance dans la phase 1 ou la supervision. |
| `note` | Justification éventuelle, notamment pour une règle supervisée. |

Une arête constante remplit `weight_value`. Une règle dépendant du profil remplit
`weight_expression`. Le pré-graphe ne contient donc pas encore une distribution
numérique complète.

## 4. Compilation pour un profil

Un profil $p$ rassemble les paramètres nécessaires pour transformer les règles du
pré-graphe en probabilités :

- les affinités sémantiques qui orientent les choix ;
- les disciplines ou compétences disponibles ;
- la probabilité de victoire à chaque combat ;
- la propension à combattre ou à s'évader ;
- les hypothèses de disponibilité des ressources exclues de L3.

La compilation est une fonction :

$$
(\mathcal G^\ast,p)\longmapsto W^{(p)}.
$$

Pour chaque nœud non terminal :

$$
\sum_j W_{ij}^{(p)}=1.
$$

Les deux terminaux vérifient :

$$
W_{\mathrm{Death},\mathrm{Death}}^{(p)}=1,
\qquad
W_{\mathrm{Win},\mathrm{Win}}^{(p)}=1.
$$

La sous-matrice $Q^{(p)}$ contient les nœuds transitoires et :

$$
N^{(p)}=(I-Q^{(p)})^{-1}.
$$

Avec $R^{(p)}$ contenant les transitions vers `Death` et `Win`, les
probabilités d'absorption sont :

$$
B^{(p)}=N^{(p)}R^{(p)}.
$$

Les deux colonnes de $B^{(p)}$ donnent directement les probabilités de défaite et de
victoire.

## 5. Règles de pondération du pré-graphe

### 5.1 Transition imposée et pré-terminal

Une transition imposée reçoit :

$$
w_e=1.
$$

Il en va de même pour les arêtes des paragraphes pré-terminaux vers `Death` ou
`Win`.

### 5.2 Choix du joueur

Pour une affinité positive $r_p(e)$ déterminée par le profil :

$$
w_e^{(p)}=\frac{r_p(e)}{\sum_{e'}r_p(e')}.
$$

Le profil de référence utilise $r_p(e)=1$ et produit une distribution uniforme.

### 5.3 Tirage aléatoire

Pour une table uniforme de dix valeurs, une branche couvrant $m$ résultats reçoit :

$$
w_e=\frac{m}{10}.
$$

Une suite de tirages est aplatie en une distribution finale sans créer de nœud de
résolution.

### 5.4 Disciplines

Deux profils ou familles de profils seront comparés :

1. un profil moyen donnant à une discipline précise la disponibilité $5/10$ ;
2. les 252 profils correspondant aux configurations cohérentes de cinq disciplines parmi
   dix.

Les règles restent inscrites symboliquement dans le pré-graphe. Les matrices sont
compilées séparément, puis les flux des 252 configurations peuvent être moyennés.

### 5.5 Combat

La chance de victoire n'est pas fixée dans le pré-graphe. Pour un profil $p$, on note :

$$
v_p(i)=P(\text{victoire au combat du nœud }i\mid p).
$$

Pour un combat simple :

$$
w_{i\rightarrow\text{suite}}^{(p)}=v_p(i),
\qquad
w_{i\rightarrow\mathrm{Death}}^{(p)}=1-v_p(i).
$$

Le profil peut fournir directement $v_p(i)$ ou le calculer à partir de caractéristiques
du personnage et de l'ennemi. Le pré-graphe ne choisit aucune valeur par défaut.

Si la victoire est suivie d'un RNT de probabilités $r_j$ :

$$
w_{i\rightarrow j}^{(p)}=v_p(i)r_j,
\qquad
w_{i\rightarrow\mathrm{Death}}^{(p)}=1-v_p(i).
$$

Si elle est suivie de choix dont les parts sont $c_j^{(p)}$ :

$$
w_{i\rightarrow j}^{(p)}=v_p(i)c_j^{(p)},
\qquad
w_{i\rightarrow\mathrm{Death}}^{(p)}=1-v_p(i).
$$

### 5.6 Combat et évasion

Si $b_p(i)$ est la propension du profil à poursuivre le combat :

$$
w_{i\rightarrow\text{victoire}}^{(p)}=b_p(i)v_p(i),
$$

$$
w_{i\rightarrow\mathrm{Death}}^{(p)}=b_p(i)(1-v_p(i)),
$$

$$
w_{i\rightarrow\text{évasion}}^{(p)}=1-b_p(i).
$$

Un risque propre à l'évasion peut être ajouté dans la règle supervisée. Les rounds,
l'Endurance et les tables de combat ne sont pas simulés dans le pré-graphe.

## 6. Mécaniques incluses et exclues

| Mécanique | Décision | Justification |
| :--- | :--- | :--- |
| Topologie et issues | **Incluse — L0** | Socle commun aux fictions à embranchements. |
| Choix explicites | **Inclus — L1** | Les poids varient selon le profil. |
| Hasard | **Inclus — L2** | Les probabilités textuelles sont convertibles. |
| Combat | **Inclus abstraitement — L2** | La chance de victoire reste un paramètre du profil. |
| Évasion | **Incluse abstraitement — L1/L2** | Destination et propension sont paramétrées. |
| Disciplines et compétences | **Incluses dans les profils — L1/L2** | Comparaison du profil moyen et des configurations cohérentes. |
| Endurance, dégâts et soins | **Exclus — L3** | Exigeraient de mémoriser la santé. |
| Objets, inventaire et monnaie | **Exclus — L3** | Dépendances persistantes et combinatoires. |
| Repas et équipement | **Exclus — L3** | Mécaniques trop spécifiques au système. |
| Modificateurs de combat | **Paramètres possibles du profil** | Ils peuvent servir plus tard à calculer $v_p(i)$. |
| Énigmes et liens cachés | **Ajoutés seulement si vérifiables** | Aucune cible n'est inventée. |

Les occurrences des mécaniques exclues restent disponibles comme métadonnées.

## 7. Cas de figure à traiter

Le code raisonne par paragraphe source. Une source est soit entièrement automatique, soit
entièrement supervisée ; aucune transformation partielle n'est conservée.

### 7.1 Tableau pour la présentation

| Cas de figure | Traitement dans le pré-graphe |
| :--- | :--- |
| Fin narrative | Pré-terminal relié par poids 1 à `Death` ou `Win`. |
| Transition imposée | Règle constante de poids 1. |
| Choix du joueur | Règle de normalisation selon les affinités du profil. |
| Tirage aléatoire | Probabilité exacte déduite des résultats possibles. |
| Compétence ou condition | Règle de disponibilité dépendant du profil. |
| Combat | Règles symboliques $v_p(i)$ et $1-v_p(i)$. |
| Paragraphe mixte | Composition symbolique si elle est simple ; sinon supervision. |
| État persistant non simulé | Hypothèse portée par le profil ou supervision. |

### 7.2 Inventaire de LW01

| Cas dans LW01 | Traitement automatique | Supervision |
| :--- | :--- | :--- |
| 16 morts et 1 victoire écrites | Pré-terminaux reliés à `Death`/`Win`. | Aucune. |
| 140 transitions forcées hors combat | `constant=1`. | Warning incompris seulement. |
| 283 arêtes de choix hors combat | `profile_choice` et copie des axes sémantiques. | Si le paragraphe mixte n'est pas reconnu. |
| RNT simple : 39 arêtes dans 18 paragraphes | Probabilités exactes sur 0–9. | Aucune. |
| RNT successifs | Détection du cas composé. | §21. |
| Plusieurs arêtes vers la même cible | Conservation puis agrégation dans $W$. | §21 est déjà supervisé. |
| Discipline Kai standard : 30 paragraphes | Règle symbolique de disponibilité. | Aucune. |
| Plusieurs conditions ou disciplines | Détection puis blocage de la source entière. | §23 et 334. |
| Objet ou monnaie | Détection de la condition. | §9, 12, 23 et 173. |
| Seuil d'Endurance | Détection sans probabilité inventée. | §203. |
| Combat simple : 17 paragraphes | `combat_win(source)` et `1-combat_win(source)`. | Aucune. |
| Combat suivi d'un RNT | Composition automatique. | Aucune : §17. |
| Combat suivi de choix | Composition après annotation sémantique. | §112, 208 et 229. |
| Combat avec évasion | Règles de victoire, mort et évasion. | §43, 169, 180, 191 et 220. |
| Combat dépendant de sa durée | Issues avant/après quatre rounds. | §231 et 339. |
| Combat avec/sans perte d'Endurance | Deux issues de victoire et mort. | §227. |
| Cas inconnu | Blocage de la source entière. | Aucun autre cas connu. |

La file connue contient 18 paragraphes : §9, 12, 21, 23, 43, 112, 169, 173, 180, 191,
203, 208, 220, 227, 229, 231, 334 et 339.

La colonne `enemies`, non `potential_death`, identifie les combats. Les colonnes
`health_modifier`, `special_mechanic` et `items_granted` ne sont pas assez
exhaustives pour prouver l'absence d'une mécanique.

## 8. Phase 2 — fichiers produits

La phase 1 reste inchangée. La phase 2 utilise :

```text
# Brouillon automatique
data/processed/pregraph/LW01/auto_edges.csv
data/processed/pregraph/LW01/review_queue.csv

# Tableau créé vide puis annoté
data/for_graph_model/LW01_supervision.csv

# Résultat de la phase 2
data/processed/pregraph/LW01/pregraph_nodes.csv
data/processed/pregraph/LW01/pregraph_edges.csv
data/processed/pregraph/LW01/conversion_report.csv
```

### 8.1 Tableau d'annotation

L'étape A crée `LW01_supervision.csv` avec son en-tête et aucune ligne. Ce fichier
n'est jamais écrasé s'il contient déjà des annotations.

```text
source_id,target_id,transition_kind,weight_rule,weight_value,weight_expression,condition_kind,condition_value,semantic_risk,semantic_morality,semantic_action,note
```

| Colonne à remplir | Contenu attendu |
| :--- | :--- |
| `source_id` | Paragraphe supervisé. |
| `target_id` | Paragraphe cible, `Death` ou `Win`. |
| `transition_kind` | Type final de la transition. |
| `weight_rule` | `constant`, `profile_choice` ou `formula`. |
| `weight_value` | Nombre si la probabilité est exacte. |
| `weight_expression` | Formule symbolique si elle dépend du profil. |
| `condition_kind`, `condition_value` | Condition éventuelle. |
| `semantic_risk`, `semantic_morality`, `semantic_action` | Annotations éventuelles d'un choix. |
| `note` | Justification concise de l'annotation. |

Les règles de remplissage sont déterministes :

- `constant` exige `weight_value` et laisse `weight_expression` vide ;
- `profile_choice` laisse les deux champs de poids vides et exige les trois annotations
  sémantiques ;
- `formula` exige `weight_expression` et laisse `weight_value` vide ;
- `condition_kind` et `condition_value` sont soit remplis ensemble, soit laissés vides.

Une ligne représente une transition finale. Toutes les transitions sortantes d'un
paragraphe supervisé doivent être décrites, y compris la transition vers `Death`.
L'annotateur peut supprimer, fusionner ou ajouter des transitions par rapport à la phase
1. Les `edge_id` et `origin=supervised` sont ajoutés automatiquement lors de la
finalisation.

Exemples :

| source | cible | type | règle | valeur ou expression |
| :--- | :--- | :--- | :--- | :--- |
| 21 | 189 | `random` | `constant` | `0.60` |
| 21 | 312 | `random` | `constant` | `0.04` |
| 21 | `Death` | `random` | `constant` | `0.36` |
| 43 | 195 | `combat` | `formula` | `fight_43 * combat_win(43)` |
| 43 | 106 | `escape` | `formula` | `1 - fight_43` |
| 43 | `Death` | `combat` | `formula` | `fight_43 * (1 - combat_win(43))` |

Les constantes décrivent un hasard objectif. Les expressions comme
`combat_win(43)` ou `fight_43` restent libres et seront fournies par chaque
profil en phase 3.

## 9. Recette courte de la phase 2

### A — Préparer automatiquement

Écrire puis lancer :

```bash
uv run python scripts/3_prepare_pregraph.py
```

Le script :

1. charge les tables de phase 1 et groupe les arêtes par source ;
2. ajoute les nœuds `Death` et `Win`, puis relie les 17 pré-terminaux ;
3. transforme les cas entièrement reconnus dans `auto_edges.csv` ;
4. écrit les sources non reconnues dans `review_queue.csv`, avec leur texte, leurs
   arêtes et la raison du blocage ;
5. crée `LW01_supervision.csv` vide avec les colonnes du §8.1.

Le script doit retrouver les 18 paragraphes connus. Toute combinaison nouvelle rejoint
la file au lieu d'être interprétée silencieusement.

### B — Annoter les exceptions

1. Ouvrir `review_queue.csv` et relire le texte de chaque source.
2. Ajouter dans `LW01_supervision.csv` une ligne par transition finale.
3. Décrire toute la distribution sortante de chaque source, pas seulement la transition
   corrigée.
4. Utiliser une constante seulement si elle est déductible du texte.
5. Utiliser `profile_choice` ou une formule symbolique pour toute probabilité
   dépendant du profil.
6. Ajouter une note courte justifiant la décision.

Le fichier est terminé lorsque les 18 sources de `review_queue.csv` y sont toutes
représentées et qu'aucune règle requise n'est vide.

### C — Finaliser le pré-graphe

Écrire puis lancer :

```bash
uv run python scripts/4_finalize_pregraph.py
```

Le script :

1. concatène les sources automatiques et les sources entièrement supervisées ;
2. attribue les identifiants et la provenance ;
3. produit `pregraph_nodes.csv`, `pregraph_edges.csv` et
   `conversion_report.csv` ;
4. vérifie que les 556 arêtes de phase 1 sont classées ou remplacées par une source
   supervisée, que toutes les cibles existent et que chaque arête possède une règle.

Il ne construit aucune matrice $W$.

## 10. Phase 3 — compiler $W$ pour plusieurs profils

Les profils sont définis dans un fichier séparé, par exemple :

```text
data/for_graph_model/LW01_profiles.json
```

Chaque profil fournit les affinités de choix, les disciplines, les probabilités
`combat_win(source_id)`, les propensions d'évasion et les hypothèses de ressources.
Une probabilité de combat manquante provoque une erreur : le compilateur n'invente pas
de valeur.

Le script :

```bash
uv run python scripts/5_compile_w.py \
  --pregraph data/processed/pregraph/LW01 \
  --profiles data/for_graph_model/LW01_profiles.json
```

itère sur tous les profils et produit :

```text
data/processed/graph/LW01/<profile>/compiled_edges.csv
data/processed/graph/LW01/<profile>/W.csv
```

Pour chaque profil, il vérifie que les poids sont finis et positifs ou nuls, que chaque
ligne non terminale somme à 1 et que `Death`/`Win` sont les deux seuls nœuds
absorbants.

## 11. Critères de fin

La phase 2 est terminée lorsque :

- `pregraph_nodes.csv` contient les 350 paragraphes, `Death` et `Win` ;
- les 17 pré-terminaux sont reliés à leur issue ;
- les 18 paragraphes particuliers sont entièrement annotés ;
- toutes les transitions possèdent une règle constante ou symbolique ;
- le pré-graphe peut être régénéré depuis la phase 1 et la supervision.

La phase 3 est terminée lorsqu'au moins un profil de référence et les profils de
comparaison produisent des matrices $W$ valides. Les indices BoP et l'étude des
trajectoires commencent ensuite.
