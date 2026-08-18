# Modélisation du graphe et compilation de $W$

> **Décision méthodologique du 18.08.2026.** Ce document remplace le formalisme
> « action–conséquence » encore présent dans la version du 17.08.2026. Le graphe est
> désormais pondéré directement par une matrice de marche aléatoire $W$. La phase
> actuelle n'utilise ni `action_id`, ni décomposition $\pi\times q$, ni matrice de coûts
> $C$.

## 1. Objectif

Construire, à partir des données de phase 1, un graphe probabiliste qui :

- conserve les paragraphes et leurs transitions directes ;
- représente un grand nombre d'aventures par un flux moyen ;
- permet de modifier les probabilités selon un profil ou un scénario ;
- reste simple, contrôlable et applicable à d'autres fictions interactives ;
- conserve la provenance de chaque nœud, transition et correction.

LW01 sert à développer et tester la méthode. Ses règles ne doivent pas devenir celles du
moteur général.

## 2. Niveaux L0–L3

| Niveau | Information | Statut |
| :--- | :--- | :--- |
| **L0 — Topologie** | Unités narratives, transitions, entrées et fins. | Socle obligatoire. |
| **L1 — Agentivité** | Choix du joueur, passages automatiques, conditions et caractéristiques sémantiques. | Inclus. |
| **L2 — Incertitude** | Probabilités exactes, moyennes ou paramétrées. | Inclus. |
| **L3 — État persistant** | Santé, inventaire, monnaie, équipement, relations et autres variables mémorisées. | Non implémenté. |

L0–L2 décrivent les chemins et leurs probabilités sans reproduire tout le système de jeu.
L3 demanderait des états `(nœud narratif, état du personnage)`, augmenterait fortement
la taille du graphe et rendrait le moteur dépendant de l'œuvre.

Une compétence choisie au début du livre constitue bien une propriété persistante, mais
elle sera traitée par plusieurs matrices $W$, pas par une expansion des nœuds.

## 3. Objets du modèle

### 3.1 Nœuds

Le graphe contient seulement :

- les **nœuds narratifs** provenant du corpus ;
- les **fins narratives** déjà présentes dans le corpus ;
- les **terminaux synthétiques** nécessaires aux issues sans paragraphe cible, par
  exemple `Death_implicit`.

Aucun nœud intermédiaire n'est créé pour représenter un choix, un tirage, un combat ou
une résolution. Un chemin reste une succession de passages effectivement lus, suivie
éventuellement d'un terminal synthétique.

### 3.2 Arêtes directes

Chaque arête représente directement une transition possible de $i$ vers $j$. Une
table d'arêtes peut conserver plusieurs lignes entre les mêmes nœuds afin de préserver
la provenance ou des mécanismes différents.

Il n'existe aucun objet formel « action » dans le modèle :

- pas d'`action_id` ;
- pas de table séparée de décisions ou de conséquences ;
- pas de décomposition entre une politique locale et une résolution mécanique ;
- pas de nœud technique pour relier ces éléments.

Les paramètres de profil, de hasard ou de combat servent uniquement à calculer le poids
final de chaque arête.

### 3.3 Schéma minimal de `model_nodes`

| Champ | Rôle |
| :--- | :--- |
| `node_id` | Identifiant stable du nœud. |
| `node_kind` | `narrative`, `death`, `win` ou `synthetic_terminal`. |
| `absorbing` | Booléen indiquant une fin de marche. |
| `source_ref` | Ligne de phase 1 ou justification du terminal synthétique. |

Le texte narratif et les métadonnées détaillées restent dans la table `nodes` de phase 1
et ne sont pas dupliqués inutilement.

### 3.4 Schéma minimal de `model_edges`

| Champ | Rôle |
| :--- | :--- |
| `edge_id` | Identifiant stable de la ligne. |
| `source_id`, `target_id` | Origine et destination narratives ou terminales. |
| `transition_kind` | `forced`, `profile_choice`, `random`, `kai`, `combat`, `escape`, `manual` ou autre catégorie documentée. |
| `weight_rule` | Règle utilisée pour obtenir le poids final. |
| `weight_value` | Constante éventuelle. |
| `weight_expression` | Expression paramétrée éventuelle. |
| `condition_kind`, `condition_value` | Condition détectée si elle doit être conservée. |
| `semantic_risk`, `semantic_morality`, `semantic_action` | Annotations de phase 1 utilisées pour les profils. |
| `review_status` | `auto`, `auto_assumption`, `reviewed` ou `blocked`. |
| `source_ref` | Provenance précise dans `edges`, `nodes`, le texte ou la supervision. |

`semantic_action` conserve ici le nom d'une colonne existante. Il s'agit d'un axe
sémantique (`physical`, `neutral`, `tactical`), pas d'une entité du graphe.

## 4. Matrice de marche $W$

Pour un profil $p$ et un scénario mécanique $s$, chaque arête
$e:i\rightarrow j$ reçoit un poids final :

$$
w_e^{(p,s)}\geq 0.
$$

Les arêtes parallèles sont agrégées seulement lors de la construction de la matrice :

$$
W_{ij}^{(p,s)}=\sum_{e:i\rightarrow j}w_e^{(p,s)}.
$$

Pour chaque nœud non terminal :

$$
\sum_j W_{ij}^{(p,s)}=1.
$$

Les terminaux ont une boucle de probabilité 1 dans la chaîne complète. Pour le calcul de
la matrice fondamentale, on extrait la sous-matrice $Q$ des nœuds transitoires :

$$
N=(I-Q)^{-1}.
$$

Pour une distribution initiale $\mu$, le nombre moyen de visites est :

$$
v^\top=\mu^\top N.
$$

Le flux moyen sur une arête est alors :

$$
F_e=v_{\operatorname{source}(e)}w_e.
$$

Il compte les traversées attendues, y compris les passages répétés dans les cycles. Ce
n'est pas la probabilité que l'arête soit visitée au moins une fois.

## 5. Règles directes de pondération

### 5.1 Transition forcée

Une transition forcée non combattante reçoit :

$$
w_e=1.
$$

Les pertes d'Endurance, d'objets ou d'équipement associées restent des métadonnées si
elles n'altèrent pas la destination dans le modèle L0–L2.

### 5.2 Choix explicite

Pour chaque profil $p$, une fonction d'affinité positive $r_p(e)$ est calculée à partir
des annotations sémantiques. Entre les transitions de choix disponibles au même nœud :

$$
w_e^{(p)}=\frac{r_p(e)}{\sum_{e'}r_p(e')}.
$$

La marche de référence utilise $r_p(e)=1$, donc une distribution uniforme. La formule
exacte des profils devra être fixée dans un fichier de configuration et non codée en dur
pour LW01.

### 5.3 Tirage aléatoire

La table RNT de LW01 est uniforme sur $\{0,\ldots,9\}$. Une transition correspondant à
un ensemble de $m$ résultats reçoit :

$$
w_e=\frac{m}{10}.
$$

Une séquence de tirages est aplatie en multipliant les probabilités successives, sans
créer de nœud intermédiaire.

### 5.4 Discipline moyenne

Si le personnage choisit $k$ disciplines parmi $n$, la disponibilité moyenne d'une
discipline précise est :

$$
r=\frac{k}{n}.
$$

Sous l'hypothèse que la transition spéciale est prise dès que la discipline est
possédée :

$$
w_{\text{discipline}}=r.
$$

La masse $1-r$ est distribuée entre les autres transitions selon leurs affinités de
profil. Dans LW01, $k=5$, $n=10$, donc $r=0.5$.

Ce traitement est une approximation sans mémoire : deux occurrences successives de la
même discipline sont marginalisées indépendamment.

### 5.5 Configurations exactes de disciplines

Une seconde compilation énumère les $\binom{10}{5}=252$ configurations de LW01. Pour
chaque configuration :

- une transition exigeant une discipline possédée est disponible ;
- sous l'hypothèse retenue, elle est prise automatiquement lorsqu'elle est l'unique
  transition spéciale disponible ;
- sinon elle est indisponible et les autres poids sont renormalisés.

Les flux sont calculés séparément pour chaque $W$, puis moyennés. Il ne faut pas
remplacer cette moyenne par le flux de la matrice moyenne :

$$
N\!\left(\mathbb{E}[W]\right)\neq\mathbb{E}[N(W)].
$$

Les nœuds proposant plusieurs disciplines exigent une règle de départage supervisée.

### 5.6 Combat simple

Si $d_s(i)$ est la probabilité de défaite retenue pour le combat du nœud $i$ dans le scénario $s$ :

$$
w_{i\rightarrow\text{suite}}=1-d_s(i),
\qquad
w_{i\rightarrow\text{Death\_implicit}}=d_s(i).
$$

Les caractéristiques détaillées de l'ennemi ne sont pas utilisées dans le premier
modèle. Elles restent disponibles pour construire ultérieurement des valeurs de
$d_s(i)$ plus fines.

### 5.7 Combat suivi d'un tirage ou d'un choix

Si la victoire est suivie d'un RNT de probabilités $r_j$ :

$$
w_{i\rightarrow j}=(1-d_s(i))r_j,
\qquad
w_{i\rightarrow\text{Death\_implicit}}=d_s(i).
$$

Si elle est suivie de plusieurs choix dont les parts normalisées sont 
$c_j^{(p)}$ :

$$
w_{i\rightarrow j}=(1-d_s(i))c_j^{(p)},
\qquad
w_{i\rightarrow\text{Death\_implicit}}=d_s(i).
$$

Ces formules portent directement sur les arêtes finales. Elles ne créent aucune couche
intermédiaire.

### 5.8 Combat et évasion

Si $b_p(i)$ est la propension du profil à poursuivre le combat plutôt qu'à s'évader :

$$
w_{i\rightarrow\text{victoire}}=b_p(i)(1-d_s(i)),
$$

$$
w_{i\rightarrow\text{Death\_implicit}}=b_p(i)d_s(i),
$$

$$
w_{i\rightarrow\text{évasion}}=1-b_p(i).
$$

Un risque propre à l'évasion peut être ajouté directement à ces poids. Les détails des
rounds et des dommages restent exclus.

## 6. Mécaniques incluses et exclues

| Mécanique | Décision | Justification |
| :--- | :--- | :--- |
| Topologie et fins | **Incluse — L0** | Socle commun à toute fiction à embranchements. |
| Choix explicites | **Inclus — L1** | Les poids de $W$ varient selon le profil. |
| Hasard | **Inclus — L2** | Les probabilités textuelles sont directement convertibles. |
| Combat | **Inclus abstraitement — L2** | Seules les transitions finales et leurs probabilités sont nécessaires au flux. |
| Évasion | **Incluse abstraitement — L1/L2** | Destination directe et risque éventuel paramétré. |
| Disciplines et compétences initiales | **Incluses par scénarios — L1/L2** | Comparaison d'une moyenne directe et de configurations cohérentes. |
| Endurance, dégâts et soins | **Exclus — L3** | Nécessiteraient de mémoriser la santé le long du parcours. |
| Objets, inventaire et équipement | **Exclus — L3** | Dépendances persistantes et combinatoires, spécifiques au système. |
| Monnaie | **Exclue — L3** | Même problème de persistance que l'inventaire. |
| Repas et survie | **Exclus — L3** | Combinent ressource, discipline et Endurance. |
| Modificateurs de combat | **Absorbés dans les paramètres** | Une simulation exacte serait spécifique à LW. |
| Énigmes et liens cachés | **Ajoutés seulement si vérifiables** | Aucune cible ne doit être inventée ; toute insertion est supervisée. |

Le modèle conserve dans ses métadonnées les mécaniques exclues afin que leur absence ne
soit jamais confondue avec une absence dans l'œuvre.

## 7. Audit des données LW01

La phase 1 contient 350 nœuds et 556 arêtes. Les 556 balises `<choice>` ont toutes une
arête, tous les identifiants sont valides et les 350 nœuds sont atteignables depuis le
§1. Les comptes ci-dessous peuvent se recouvrir lorsqu'un paragraphe combine plusieurs
mécanismes.

| Mécanisme | Données observées | Traitement automatique |
| :--- | :--- | :--- |
| Terminaux écrits | 16 morts et 1 victoire | Création de nœuds absorbants. |
| Transitions forcées non combattantes | 140 arêtes, dont 117 sans warning et 23 avec une mécanique L3 ou particulière | Poids 1 ; mécanique exclue conservée comme métadonnée. |
| Choix explicites non combattants | 283 arêtes | Calcul d'une affinité de profil puis normalisation directe au nœud. |
| RNT simple | 39 arêtes dans 18 paragraphes | Extraction des intervalles sur 0–9 et calcul exact des poids. |
| Disciplines Kai | 41 arêtes dans 32 paragraphes | Extraction du nom ; compilation moyenne ou par configuration. Trente paragraphes sont standards. |
| Combats simples | 18 paragraphes sur 29 | Ajout de la mort implicite et application du paramètre de défaite ; composition avec le RNT au §17. |
| Objets ou monnaie | 7 arêtes dans 4 paragraphes | Type détecté automatiquement ; disponibilité fixée par scénario. |
| Seuil d'Endurance | 2 arêtes au §203 | Type détecté ; poids non déductible sans paramètre supervisé. |

### 7.1 Limites des colonnes de nœuds

La topologie est fiable, mais certaines colonnes mécaniques ne sont pas exhaustives :

- `enemies` contient 29 paragraphes et 39 ennemis structurés ;
- `health_modifier` ne contient que 7 valeurs non nulles alors que le texte décrit
  davantage de pertes et de soins ;
- `special_mechanic` est vide ;
- `items_granted` est vide.

Le compilateur peut donc utiliser `enemies` pour reconnaître les combats, mais il ne doit
pas déduire l'absence d'une mécanique L3 à partir des autres colonnes vides.

### 7.2 Cas exigeant une supervision

La file initiale contient 18 paragraphes distincts :

| Cas | Paragraphes | Annotation nécessaire |
| :--- | :--- | :--- |
| Tirages successifs | §21 | Distribution aplatie : §189 = 0,60 ; §312 = 0,04 ; mort = 0,36. |
| Objet, monnaie ou condition multiple | §9, 12, 23, 173 | Règle restrictive et permissive ; au §23, articulation avec Mind Over Matter. |
| Plusieurs disciplines | §334 | Règle de départage si Sixth Sense et Camouflage sont toutes deux possédées. |
| Seuil d'Endurance | §203 | Paramètre pour les deux branches, ou exclusion documentée. |
| Choix après victoire | §112, 208, 229 | Annotations sémantiques des transitions qui ne les possèdent pas. |
| Combat et évasion | §43, 169, 180, 191, 220 | Formule directe et paramètre de propension à continuer le combat. |
| Durée du combat et évasion | §231, 339 | Poids des issues avant/après quatre rounds, évasion et mort. |
| Victoire avec ou sans dégâts | §227 | Poids de la victoire sans perte, avec perte et de la mort. |

Les 53 warnings présents sur 48 paragraphes ne doivent pas tous devenir des corrections
manuelles. Le code les classe d'abord en `ignored_endurance`, `ignored_inventory`,
`combat_detected`, `review_required` ou `unclassified_warning`. Seules les deux dernières
catégories bloquent la compilation.

## 8. Données dérivées attendues

La phase 1 reste inchangée. La phase 2 produit :

```text
data/processed/graph/LW01/model_nodes.csv
data/processed/graph/LW01/model_edges.csv
data/processed/graph/LW01/review_queue.csv
data/processed/graph/LW01/matrices/<scenario>/W.*
data/processed/graph/LW01/matrices/<scenario>/manifest.json
```

Les annotations humaines sont conservées séparément, par exemple dans :

```text
data/for_graph_model/LW01_supervision.csv
```

Un fichier dérivé peut toujours être régénéré à partir de la phase 1, de la supervision
et de la configuration du scénario.

## 9. Plan d'implémentation — recette

### Étape 1 — Écrire les schémas et les tests minimaux

1. Créer un module décrivant strictement les colonnes de `model_nodes`, `model_edges` et
   de la supervision.
2. Interdire explicitement `action_id`, les nœuds intermédiaires et les poids sans règle
   ni provenance.
3. Écrire de petits jeux de test contenant : une transition forcée, un choix à deux
   branches, un RNT, une discipline, un combat et deux arêtes parallèles.
4. Tester dès cette étape l'agrégation $W_{ij}=\sum_e w_e$.

**Sortie attendue :** contrats de données stables et tests unitaires rouges tant que le
compilateur n'existe pas.

### Étape 2 — Écrire le script d'audit de la phase 1

1. Charger `LW01_nodes.csv` et `LW01_e_edges.csv` sans les modifier.
2. Réutiliser les contrôles de `scripts/utils/qc_extraction.py`.
3. Vérifier les 350 nœuds, 556 arêtes, identifiants, fins et atteignabilité.
4. Attribuer un `edge_id` stable de la forme
   `LW01:<source>:<target>:<ordinal>`.
5. Produire un rapport machine lisible ; arrêter le programme si la topologie diffère du
   corpus balisé.

**Sortie attendue :** un audit reproductible et la liste stable des arêtes sources.

### Étape 3 — Transformer les transitions forcées et les fins

1. Copier les 350 nœuds narratifs dans `model_nodes`.
2. Marquer les 16 morts et la victoire comme absorbantes.
3. Ajouter `Death_implicit` comme terminal synthétique commun aux morts sans paragraphe
   cible, qu'elles proviennent d'un combat ou d'un autre mécanisme.
4. Pour chaque arête `forced` dont le nœud source n'a pas d'ennemi, écrire une ligne
   `weight_rule=constant`, `weight_value=1`.
5. Classer les warnings liés à l'Endurance, aux objets ou à l'équipement comme mécaniques
   exclues, sans modifier le poids.

**Sortie attendue :** les 140 transitions forcées non combattantes compilables.

### Étape 4 — Transformer les choix explicites ordinaires

1. Sélectionner les 283 arêtes `explicit_choice` dont le nœud source n'est pas un combat.
2. Copier leurs trois annotations sémantiques.
3. Attribuer `weight_rule=profile_normalized`.
4. Écrire d'abord une configuration uniforme donnant la même affinité à toutes les
   transitions concernées.
5. Tester que la somme des poids vaut 1 à chaque nœud ne contenant que des choix
   ordinaires.

**Sortie attendue :** une marche uniforme fonctionnelle avant toute définition fine des
profils.

### Étape 5 — Écrire le parseur des tirages RNT

1. Reconnaître les formes `0–4`, `5–9`, `below 5`, `5 or above`, `4 or lower`, etc.
2. Convertir chaque condition en ensemble d'entiers de 0 à 9.
3. Vérifier, par paragraphe, l'absence de chevauchement et la couverture complète des dix
   valeurs.
4. Écrire `weight_rule=constant` avec la probabilité calculée pour les 39 arêtes simples.
5. Envoyer automatiquement le §21 dans la file de supervision au lieu d'essayer de
   deviner sa séquence.

**Sortie attendue :** 18 paragraphes RNT compilés automatiquement et un cas bloqué bien
identifié.

### Étape 6 — Écrire les deux traitements des disciplines

1. Détecter `Kai Discipline` et extraire le nom canonique de la discipline.
2. Relier les formulations négatives comme `If not` à la discipline citée dans la même
   source.
3. Pour le modèle moyen, écrire une règle `kai_mean` utilisant $5/10$ et distribuant le
   reste entre les autres transitions.
4. Pour le modèle exact, générer les 252 configurations et écrire une règle `kai_build`
   activée selon chaque configuration.
5. Envoyer les §23 et 334 dans la supervision.
6. Tester sur deux occurrences successives d'une même discipline que le modèle moyen et
   la moyenne exacte produisent bien des résultats différents.

**Sortie attendue :** 30 paragraphes Kai standards compilables dans les deux variantes.

### Étape 7 — Écrire le transformateur des combats simples

1. Identifier un combat uniquement par `enemies` non vide, jamais par
   `potential_death` seul.
2. Pour les 17 combats avec une unique transition de victoire, remplacer le poids 1 par
   `1-d_s(i)` et ajouter une arête vers `Death_implicit` de poids `d_s(i)`.
3. Pour le §17, multiplier les trois poids RNT par `1-d_s(17)` et ajouter la mort de poids
   `d_s(17)`.
4. Conserver les statistiques et modificateurs de combat comme métadonnées sans les
   interpréter.
5. Envoyer les 11 autres paragraphes de combat dans la supervision.

**Sortie attendue :** 18 combats compilés automatiquement et 11 cas spéciaux bloqués.

### Étape 8 — Classer les autres conditions

1. Détecter les objets et la monnaie aux §9, 12, 23 et 173.
2. Préparer deux configurations : `restrictive`, où la transition conditionnelle est
   indisponible, et `permissive`, où elle est disponible.
3. Détecter le seuil d'Endurance du §203 et lui attribuer un paramètre explicite plutôt
   qu'une valeur inventée.
4. Marquer toutes les autres mécaniques L3 comme `ignored_metadata`.
5. Bloquer toute condition non classée.

**Sortie attendue :** aucune condition silencieusement interprétée.

### Étape 9 — Rédiger manuellement la table de supervision

Pour chacun des 18 paragraphes listés en §7.2 :

1. recopier `source_id`, `target_id` et la citation pertinente ;
2. indiquer la catégorie corrigée ;
3. écrire la règle ou l'expression directe du poids ;
4. compléter les annotations sémantiques manquantes, notamment après victoire ;
5. indiquer la justification et l'auteur de la validation ;
6. marquer la ligne `reviewed` seulement après une seconde lecture du paragraphe.

Le §21 reçoit les constantes $0{,}60$, $0{,}04$ et $0{,}36$. Les autres cas reçoivent
des expressions paramétrées plutôt que des nombres arbitraires.

**Sortie attendue :** `LW01_supervision.csv`, court, lisible et versionné.

### Étape 10 — Fusionner règles automatiques et supervision

1. Construire `model_edges` depuis les règles automatiques.
2. Appliquer la supervision comme surcharge explicite, sans modifier les CSV de phase 1.
3. Refuser une surcharge sans provenance ou visant une arête inconnue.
4. Refuser toute ligne encore marquée `blocked`, `review_required` ou
   `unclassified_warning`.
5. Produire un rapport donnant, pour chaque arête, sa règle finale et son origine.

**Sortie attendue :** `model_nodes.csv` et `model_edges.csv` complets, mais encore
paramétrés.

### Étape 11 — Écrire les configurations de scénarios

Créer des fichiers de configuration séparés pour :

1. la marche uniforme ;
2. chaque profil sémantique ;
3. le traitement Kai moyen ;
4. chacune des 252 configurations Kai ;
5. les valeurs basse, centrale et haute de défaite au combat ;
6. les variantes restrictive et permissive des objets ;
7. les paramètres des combats spéciaux et du §203.

Le compilateur doit échouer si une valeur nécessaire manque. Les valeurs numériques de
combat devront être justifiées avant d'être inscrites dans ces fichiers.

**Sortie attendue :** des scénarios explicites, comparables et reproductibles.

### Étape 12 — Compiler les poids et la matrice $W$

Pour chaque scénario :

1. évaluer directement `weight_value` ou `weight_expression` sur chaque arête ;
2. normaliser les transitions de choix lorsque la règle le demande ;
3. vérifier que tous les poids sont finis et positifs ou nuls ;
4. agréger les arêtes parallèles dans $W_{ij}$ ;
5. ajouter les boucles absorbantes dans la matrice complète ;
6. extraire $Q$, la sous-matrice transitoire ;
7. enregistrer $W$, la liste ordonnée des nœuds et le manifeste du scénario.

**Sortie attendue :** une matrice $W$ traçable pour chaque scénario.

### Étape 13 — Valider chaque matrice

1. Vérifier $W_{ij}\geq0$.
2. Vérifier une somme de ligne égale à 1 à la tolérance numérique près.
3. Vérifier que seuls les terminaux ont une boucle absorbante.
4. Vérifier que toute masse peut atteindre un terminal depuis le §1.
5. Vérifier $\rho(Q)<1$, puis calculer $(I-Q)^{-1}$.
6. Comparer les visites et flux analytiques à une simulation Monte-Carlo sur les petits
   graphes de test, puis sur LW01.
7. Vérifier que toute arête de phase 1 est soit modélisée, soit explicitement exclue.

**Sortie attendue :** un rapport de validation bloquant en cas d'erreur.

### Étape 14 — Comparer les deux modèles Kai

1. Calculer le flux issu de la matrice moyenne Kai.
2. Calculer séparément les flux des 252 configurations.
3. Moyenner ces 252 flux.
4. Mesurer les différences par nœud, par arête et par probabilité d'absorption.
5. Décider, sur cette base, si l'approximation moyenne est suffisante pour l'analyse
   principale.

**Sortie attendue :** une décision empirique documentée, et non une préférence de
principe.

### Étape 15 — Geler la phase de modélisation

1. Versionner schémas, supervision, configurations, tests et rapports.
2. Documenter les paramètres retenus et les mécaniques exclues.
3. Produire une matrice de référence et les scénarios de sensibilité validés.
4. Ne commencer le choix des indices BoP qu'après réussite de tous les contrôles.

## 10. Critères de fin de la phase

La modélisation du graphe est terminée lorsque :

- chaque transition possède une règle directe de poids et une provenance ;
- aucune structure « action–conséquence » ne subsiste dans les données dérivées ;
- les 18 cas supervisés sont validés ;
- les matrices $W$ sont normalisées et absorbantes ;
- le calcul de $(I-Q)^{-1}$ est stable ;
- les flux analytiques concordent avec les simulations ;
- la comparaison des deux traitements Kai est produite ;
- les mécaniques exclues sont recensées dans le manifeste.

Les indices BoP et l'étude des trajectoires commencent seulement après ce jalon.
