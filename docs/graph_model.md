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

## 7. Cas de figure à traiter

La phase 1 contient 350 nœuds et 556 arêtes. Sa topologie est déjà contrôlée. Le code de
conversion raisonne **par paragraphe source**, car un même paragraphe peut combiner un
combat, un choix et une condition. Il applique la première règle compatible avec la
combinaison complète ; s'il ne reconnaît pas cette combinaison, il envoie le paragraphe
entier en supervision et n'en conserve aucune transition partielle dans le brouillon
automatique.

### 7.1 Tableau synthétique pour la présentation

Ce tableau est conçu pour tenir sur une slide et expliquer le passage des données de
phase 1 au graphe.

| Cas de figure | Traitement |
| :--- | :--- |
| Fin narrative | Nœud absorbant. |
| Transition imposée | Arête de poids 1. |
| Choix du joueur | Affinités du profil, puis normalisation des arêtes sortantes. |
| Tirage aléatoire | Conversion des résultats possibles en probabilités. |
| Compétence ou autre condition | Disponibilité moyenne ou scénario explicite. |
| Combat | Victoire $1-d$, défaite $d$ vers `Death_implicit`. |
| Paragraphe mixte | Composition directe des probabilités si la règle est simple ; sinon supervision. |
| État persistant non modélisé | Métadonnée conservée ; hypothèse signalée ou supervision si la destination en dépend. |

### 7.2 Inventaire détaillé de LW01

| Cas dans LW01 | Traitement par le code | Cas supervisés |
| :--- | :--- | :--- |
| 16 morts et 1 victoire écrites | Marquer les nœuds absorbants. | Aucun. |
| 140 transitions forcées hors combat | Poids 1 ; ignorer les effets L3 sans effet sur la destination. | Warning incompris seulement. |
| 283 arêtes de choix hors combat | Copier les axes sémantiques et normaliser selon le profil. | Choix appartenant à un paragraphe mixte non reconnu. |
| RNT simple : 39 arêtes dans 18 paragraphes | Parser les intervalles sur 0–9 et calculer la probabilité. | Aucun. |
| RNT successifs | Ne pas deviner la composition. | §21 : §189 = 0,60 ; §312 = 0,04 ; mort = 0,36. |
| Plusieurs arêtes vers la même cible | Conserver les arêtes séparées, puis additionner leurs poids dans \(W_{ij}\). | §21 est déjà supervisé à cause de ses tirages successifs. |
| Discipline Kai standard : 30 paragraphes | Modèle moyen $5/10$ ou disponibilité selon la configuration Kai. | Aucun. |
| Plusieurs conditions ou disciplines | Détecter la catégorie, puis envoyer le paragraphe entier à la file. | §23 et 334. |
| Objet ou monnaie | Détecter la condition ; utiliser les variantes restrictive et permissive. | §9, 12, 23 et 173. |
| Seuil d'Endurance | Détecter sans inventer sa probabilité. | §203. |
| Combat simple : 17 paragraphes | Succès $1-d_s(i)$ ; mort implicite $d_s(i)$. | Aucun. |
| Combat suivi d'un RNT | Multiplier les probabilités du RNT par $1-d_s(i)$ ; ajouter la mort. | Aucun : §17 est automatique. |
| Combat suivi de choix après victoire | Détecter le combat, puis annoter les choix et composer les poids. | §112, 208 et 229. |
| Combat avec évasion | Décrire directement combat, mort et évasion. | §43, 169, 180, 191 et 220. |
| Combat dépendant de sa durée | Décrire les issues avant/après quatre rounds et l'évasion. | §231 et 339. |
| Combat avec/sans perte d'Endurance | Décrire les deux victoires et la mort. | §227. |
| Cas inconnu ou incohérent | Ne produire aucun poids ; ajouter le paragraphe à la file. | Aucun cas connu supplémentaire. |

Les comptes se recouvrent pour les paragraphes mixtes. La file connue contient donc 18
paragraphes distincts : §9, 12, 21, 23, 43, 112, 169, 173, 180, 191, 203, 208, 220,
227, 229, 231, 334 et 339.

La colonne `enemies`, non `potential_death`, identifie les combats. Les colonnes
`health_modifier`, `special_mechanic` et `items_granted` ne sont pas assez exhaustives
pour prouver l'absence d'une mécanique. Un warning clairement lié à une mécanique L3
exclue est simplement conservé ; tout warning incompris part en supervision.

## 8. Fichiers produits

Les données de phase 1 restent inchangées. Le processus utilise seulement :

```text
# Brouillon automatique
data/processed/graph/LW01/auto_edges.csv
data/processed/graph/LW01/review_queue.csv

# Annotation humaine
data/for_graph_model/LW01_supervision.csv
data/for_graph_model/LW01_scenarios.json

# Résultat final
data/processed/graph/LW01/model_nodes.csv
data/processed/graph/LW01/model_edges.csv
data/processed/graph/LW01/W_<scenario>.csv
data/processed/graph/LW01/conversion_report.csv
```

`LW01_supervision.csv` reste volontairement simple : `source_id`, `target_id`,
`transition_kind`, règle ou expression du poids, trois annotations sémantiques et une
note de justification. Pour un paragraphe supervisé, ses lignes décrivent **toutes** les
transitions sortantes finales, y compris une mort implicite éventuelle. Cela évite une
fusion partielle difficile à contrôler.

`LW01_scenarios.json` rassemble dans un seul petit fichier les affinités de profil, les
probabilités de défaite, le traitement Kai et les variantes restrictive/permissive des
ressources. Les 252 configurations Kai sont générées par le code, pas écrites à la main.

## 9. Recette courte

### A — Lancer la conversion automatique

Écrire puis lancer un seul script :

```bash
uv run python scripts/3_prepare_graph.py
```

Le script :

1. charge `LW01_nodes.csv` et `LW01_e_edges.csv` et réutilise le contrôle qualité
   existant ;
2. groupe les arêtes par paragraphe source ;
3. applique les traitements du tableau §7.2 avec quelques fonctions simples
   (`forced`, `choice`, `rnt`, `kai`, `combat`, `mixed`) ;
4. écrit les transitions reconnues dans `auto_edges.csv` ;
5. écrit les paragraphes non entièrement reconnus dans `review_queue.csv`, avec leur
   texte, leurs arêtes actuelles, le cas détecté et la raison du blocage.

Le script doit retrouver les 18 paragraphes connus, mais la règle générale reste : toute
combinaison inconnue rejoint automatiquement la file. Une source est donc soit entièrement
automatique, soit entièrement supervisée. Il ne faut ni architecture de validation
séparée, ni batterie de tests avant de travailler sur les données réelles.

### B — Annoter les exceptions

1. Ouvrir `review_queue.csv` et les textes des paragraphes indiqués.
2. Remplir `LW01_supervision.csv` avec une ligne par transition finale.
3. Renseigner dans `LW01_scenarios.json` les quelques paramètres nécessaires aux
   matrices demandées.
4. Pour chaque paragraphe, vérifier que les lignes manuelles décrivent toute sa
   distribution sortante, et ajouter une courte justification.
5. Versionner ces deux petits fichiers : ils constituent la trace des décisions.

Les probabilités déjà déductibles sont écrites comme constantes, par exemple celles du
§21. Les choix dépendant d'un profil, d'un combat ou d'un état non simulé reçoivent une
expression paramétrée, pas une valeur arbitraire.

### C — Compiler le graphe et vérifier le résultat

Écrire puis lancer :

```bash
uv run python scripts/4_compile_graph.py
```

Ce second script :

1. concatène `auto_edges.csv` et les paragraphes entièrement décrits dans
   `LW01_supervision.csv` ;
2. évalue les poids pour le scénario demandé, agrège les arêtes parallèles et construit
   $W$ ;
3. produit `model_nodes.csv`, `model_edges.csv`, $W$ et un rapport donnant le nombre de
   cas automatiques et supervisés.

Quatre contrôles intégrés suffisent pour cette étude :

- chaque arête de phase 1 est classée ou rattachée à un paragraphe supervisé ;
- aucune entrée de la file de supervision ne reste sans annotation ;
- les cibles existent et les poids sont finis et positifs ou nuls ;
- chaque ligne non terminale de $W$ somme à 1 et chaque terminal possède sa boucle 1.

On n'ajoute un petit test ciblé que si un parseur délicat le justifie, par exemple pour
les intervalles RNT. Une infrastructure générale de schémas, de tests et de rapports de
validation n'est pas un objectif de ce projet.

## 10. Critères de fin de la phase

La phase est terminée lorsque :

- les deux scripts reproduisent le graphe depuis la phase 1 et la supervision ;
- les 556 arêtes sources sont toutes prises en compte et chaque arête synthétique est
  identifiable ;
- les 18 paragraphes particuliers sont explicitement annotés ;
- les contrôles simples de $W$ passent ;
- `conversion_report.csv` fournit directement les nombres utiles à la slide.

La comparaison des deux traitements Kai peut alors être faite avec les mêmes scripts.
Les indices BoP et l'étude des trajectoires commencent après ce jalon.
