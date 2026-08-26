# Plan global — Distant reading des fictions interactives

> Document de référence mis à jour le 25.08.2026. La représentation du pré-graphe et la
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
- l'analyse structurelle par BoP ;
- l'analyse des histoires complètes produites par les trajectoires.

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

Le profil contient uniquement les trois orientations comportementales `risk`,
`morality` et `action`. Les disciplines, les conditions persistantes, les combats et
l'évasion sont réglés une fois pour toute l'expérience. Plusieurs profils peuvent donc
être compilés sans modifier ni réannoter le pré-graphe et sans changer de schéma de
profil.

### 3.4 Usage de Bag-of-Paths

La première étude se place à la borne **Random Walk** :

- seule $W^{(p)}$ est utilisée ;
- aucune matrice de coûts $C$ n'est construite à ce stade ;
- la borne Shortest Path n'est pas étudiée ;
- l'objectif est d'obtenir un flux moyen représentant un grand nombre d'aventures.

Avec les deux issues `Death` et `Win`, les probabilités d'absorption donnent
directement les probabilités de défaite et de victoire du profil.

Le catalogue et le noyau des indices BoP ont été fixés après la validation des matrices
$W$ ; ils sont décrits dans la phase 4 de la feuille de route.

## 4. Mécaniques retenues

### 4.1 Choix

Les annotations `risk`, `morality` et `action` servent à définir les affinités
du profil. Les poids sont normalisés localement. Une marche uniforme fournit le profil
de référence.

### 4.2 Hasard

Les intervalles de la table de hasard donnent des probabilités constantes. Les séquences
de tirages sont aplaties en une distribution finale.

### 4.3 Disciplines et compétences

La disponibilité de toute discipline est fixée à $0{,}5$ pour cette itération. Elle
représente une approximation marginale commune à tous les profils, et non un joueur
possédant une configuration particulière. Les configurations réelles de disciplines ne
sont pas comparées dans la présentation.

### 4.4 Combats et évasions

Une unique probabilité de victoire `combat_win_probability` et une unique probabilité de
prendre la fuite `escape_probability` sont fixées pour toute l'expérience. Elles ne
dépendent ni du profil ni du combat. Pour un combat avec fuite simple, si $v$ désigne la
première et $f$ la seconde :

$$
P(\text{fuite})=f,\qquad
P(\text{victoire})=(1-f)v,\qquad
P(\text{mort})=(1-f)(1-v).
$$

Toutes les issues catégorielles sont ramenées aux trois rôles génériques `survive`,
`escape` et `death`. Si plusieurs arêtes partagent un rôle, sa masse est répartie à parts
égales entre elles. Les précisions comme une victoire rapide, une perte d'Endurance ou un
combat encore en cours restent dans les notes, sans règle propre au livre.

Cette simplification est volontaire : elle sacrifie une partie de la mécanique locale
pour que le même compilateur puisse traiter d'autres livres sans connaître leurs
paragraphes particuliers.

Les rounds, l'Endurance et les tables de combat ne sont pas simulés pendant la compilation
du graphe. Ils sont toutefois utilisés hors pipeline générique par une calibration
reproductible : `scripts/3.2_calibrate_combat.py` simule la création de personnages, les
combats et l'attrition sur les routes neutres, puis les regroupe en une seule valeur.
Pour LW01, cette opération donne $P(\text{perte})=0{,}167$ et fixe donc
`combat_win_probability` à 0,833. La méthode, les hypothèses et les limites sont décrites
avec les autres paramètres fixes dans `docs/fixed_probabilities.md`.

Les probabilités propres à chaque combat $v(i)$ restent exclues de l'expérience : elles
ne sont conservées que dans le rapport de calibration et ne changent pas les poids du
compilateur.

### 4.5 État persistant

L'Endurance, l'inventaire, la monnaie, les repas et l'équipement ne sont pas suivis. Leurs
occurrences restent des métadonnées. Lorsqu'une condition simple peut être isolée —
possession d'un objet, montant minimal de Gold Crowns ou seuil d'Endurance — elle est
conservée par une règle symbolique sans reconstituer l'état du personnage.

Toutes les conditions persistantes simples utilisent la même probabilité fixe
`has_condition`, quelle que soit leur nature ou leur valeur. Les détails conservés par
`condition_available(type, value)` restent utiles à la traçabilité, mais le compilateur
résout chaque appel avec ce même scalaire. La route complémentaire reçoit
`1 - has_condition`. Les conditions composées ou ambiguës restent soumises à
supervision.

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

1. générer les 27 profils obtenus par le produit des trois niveaux de `risk`, des trois
   niveaux de `morality` et des trois niveaux de `action` ;
2. définir séparément les hypothèses fixes de l'expérience : `kai_availability`,
   `combat_win_probability`, `escape_probability`, `has_condition` et l'intensité des
   affinités de choix ;
3. lancer `3.1_compile_w.py` pour compiler et contrôler une matrice $W^{(p)}$ par
   profil selon un unique schéma.

Les 27 matrices sont calculées et contrôlées. La présentation de 20 minutes montrera
seulement un profil neutre, quelques archétypes lisibles et des effets agrégés par axe.

Le générateur des 27 profils, le compilateur et le validateur indépendant sont
implémentés. La configuration fixe est documentée, les 27 matrices LW01 sont valides et
leurs probabilités d'absorption et durées attendues sont synthétisées dans
`docs/phase3_results.md`. La phase 3 est terminée pour LW01.

### Phase 4 — Indices et analyses BoP — terminée pour LW01

À la borne Random Walk retenue pour cette itération, les indices sont calculés à partir
de la matrice transitoire $Q^{(p)}$ et de la matrice fondamentale :

$$
N^{(p)}=(I-Q^{(p)})^{-1}.
$$

$N^{(p)}_{si}$ donne le nombre attendu de visites du nœud $i$ depuis le paragraphe
initial $s$. Les probabilités de visite, flux, absorptions et entropies dérivés de cette
matrice décrivent les chemins effectivement probables pour chaque profil. Les décisions
ci-dessous limitent le nombre d'indicateurs principaux tout en conservant un catalogue
pour les extensions futures.

#### Indices locaux potentiels

| Indice | Ce qu'il mesure | Intérêt pour la fiction interactive | Décision pour cette itération |
| :--- | :--- | :--- | :--- |
| **Probabilité de visite** | Probabilité qu'une lecture atteigne le nœud. | Distingue les scènes centrales des contenus rares. | **Oui — principal** |
| **Nombre attendu de visites** | Flux total passant par le nœud, répétitions et cycles compris. | Mesure son poids effectif dans l'expérience de lecture. | **Oui — support** |
| **Flux d'arête** | Nombre attendu de passages par chaque transition. | Identifie les routes réellement empruntées et prépare la sélection des trajectoires. | **Oui — support** |
| **Contribution à la mortalité** | Probabilité totale qu'une lecture meure en quittant ce nœud vers `Death`. | Localise les principaux points de danger du livre. | **Oui — principal** |
| **Potentiel de victoire** | Probabilité d'atteindre `Win` en partant du nœud. | Situe les régions favorables ou dangereuses et sert au calcul de l'impact des choix. | **Oui — support** |
| **Impact d'un choix** | Dispersion des potentiels de victoire de ses options. | Distingue les décisions décisives des choix sans conséquence sur l'issue. | **Oui — principal** |
| **Divergence des branches** | Différence entre les distributions de futurs accessibles après chaque option. | Détecte les faux choix, les reconvergences et les bifurcations narratives durables. | **Non — reporté à l'article** |
| **Entropie locale** | Incertitude de la distribution sortante du nœud. | Mesure la liberté immédiate offerte au lecteur. | **Oui — support** |
| **Sensibilité locale au profil** | Variation de la probabilité de visite entre profils. | Montre où les styles de jeu produisent des expériences différentes. | **Oui — principal** |
| **Co-présence des nœuds** | Covariance ou corrélation entre les scènes visitées. | Permet d'identifier des régions narratives parcourues ensemble. | **Non — reporté à l'article** |

#### Indices globaux potentiels

| Indice | Ce qu'il mesure | Intérêt pour la fiction interactive | Décision pour cette itération |
| :--- | :--- | :--- | :--- |
| **Probabilité de victoire et de mort** | Probabilités d'absorption depuis le paragraphe initial. | Mesure la difficulté globale pour chaque profil. | **Oui — principal, déjà calculé** |
| **Durée attendue** | Nombre moyen de transitions avant `Win` ou `Death`. | Donne la longueur effective d'une lecture. | **Oui — support, déjà calculé** |
| **Entropie totale des trajectoires** | Somme des entropies locales pondérées par les visites attendues. | Mesure la quantité globale de liberté rencontrée pendant une lecture. | **Oui — principal** |
| **Entropie par transition** | Entropie totale divisée par la durée attendue. | Compare la variété des décisions sans la confondre avec la longueur des parcours. | **Oui — support** |
| **Couverture attendue** | Fraction moyenne des paragraphes distincts atteints en une lecture. | Mesure la quantité de contenu découverte à chaque partie. | **Oui — principal** |
| **Chevauchement entre deux lectures** | Contenu attendu en commun entre deux parcours indépendants. | Son complément fournit un indice interprétable de rejouabilité. | **Oui — principal** |
| **Concentration du flux** | Concentration des visites sur une petite partie du graphe. | Mesure la force d'une colonne vertébrale narrative commune. | **Non — redondant pour la présentation** |
| **Divergence entre profils** | Divergence entre les distributions normalisées de visites ou de flux. | Mesure la réactivité du livre au type de joueur. | **Oui — principal** |
| **Agentivité globale** | Impact moyen des choix, pondéré par leur probabilité de visite. | Résume la capacité effective du lecteur à influencer l'issue. | **Oui — support** |
| **Rapport survie–liberté** | Position de chaque profil selon sa victoire et son entropie de trajectoire. | Montre si survivre exige de sacrifier de la liberté de parcours. | **Oui — visualisation dérivée** |

#### Conditions de calcul et niveaux de comparaison

Tous les indices retenus sont calculés séparément pour les **27 profils**. Ce calcul
exhaustif est conservé dans les sorties scientifiques, même si seule une sélection est
montrée dans la présentation. Il évite de choisir les profils après observation des
résultats et permet de réutiliser les données pour l'article.

Deux références différentes sont conservées :

- le profil `neutral_neutral_neutral`, qui représente un comportement défini par le
  schéma expérimental ;
- la moyenne équilibrée des 27 profils, qui représente une population artificielle où
  chaque combinaison reçoit le même poids.

Cette moyenne ne constitue ni un profil observé ni une estimation d'un joueur moyen
réel. Chaque indice est d'abord calculé sur chaque $W^{(p)}$, puis moyenné. Les matrices
$W^{(p)}$ ne sont jamais moyennées avant le calcul : une telle matrice représenterait un
lecteur hybride changeant implicitement de comportement au cours de l'histoire et ne
correspondrait pas au schéma de profil retenu.

Les comparaisons suivantes seront produites :

| Comparaison | Définition | Usage |
| :--- | :--- | :--- |
| **Profil neutre** | Tous les indices pour `neutral_neutral_neutral`. | Référence principale. |
| **Moyenne équilibrée** | Moyenne arithmétique de chaque indice sur les 27 profils. | Niveau global du plan factoriel, non moyenne empirique de joueurs. |
| **Effets marginaux des axes** | Pour chaque niveau d'un axe, moyenne sur les neuf combinaisons des deux autres axes. | Isoler les effets moyens du risque, de la moralité et de l'action. |
| **Contraste contrôlé du risque** | `cautious_neutral_neutral`, `neutral_neutral_neutral` et `reckless_neutral_neutral`. | Montrer une différence lisible où un seul axe varie. |
| **Extrêmes observés** | Minimum et maximum obtenus parmi les 27 profils pour un indice. | Illustrer l'étendue, avec mention explicite de leur sélection après calcul. |
| **Conditionnement sur l'issue** | Visites et flux calculés sans condition, puis conditionnellement à `Win` ou `Death`. | Comparer les chemins caractéristiques de la réussite et de l'échec et préparer la phase 5. |
| **Sensibilité des paramètres fixes** | Recalcul limité avec les hypothèses alternatives documentées. | Contrôle de robustesse en annexe, non nouvelle famille de profils. |

Pour un indice $I$, l'effet marginal du niveau `cautious` est par exemple :

$$
I_{\mathrm{cautious}}
=\frac{1}{9}\sum_{m\in\mathrm{morality}}\sum_{a\in\mathrm{action}}
I_{\mathrm{cautious},m,a}.
$$

Les 27 profils constituent le plan expérimental complet et non un échantillon aléatoire.
Les résultats seront donc décrits par leurs moyennes, écarts, étendues et divergences,
sans intervalle de confiance ou test de significativité artificiel. Une incertitude de
Monte-Carlo ne sera pas introduite dans l'itération actuelle : les trajectoires de la
phase 5 seront sélectionnées exactement par leur probabilité maximale conditionnelle.

#### Sélection pour la présentation

La présentation de 20 minutes ne montrera pas un tableau de 27 profils. Elle utilisera :

1. une figure globale contenant les 27 profils, placés selon la probabilité de victoire
   et l'entropie des trajectoires, mais n'étiquetant que le profil neutre et les extrêmes ;
2. une synthèse des effets marginaux des trois axes ;
3. une comparaison locale détaillée des trois profils contrôlés
   `cautious_neutral_neutral`, `neutral_neutral_neutral` et
   `reckless_neutral_neutral` ;
4. si l'espace le permet, une opposition entre flux conditionnés à la victoire et à la
   mort pour préparer le passage vers les histoires complètes de la phase 5.

Les profils donnant le minimum et le maximum d'un indice sont visibles dans la figure
globale, mais ne servent pas seuls à interpréter l'effet d'un axe puisqu'ils peuvent
différer simultanément sur les trois dimensions. Les tableaux exhaustifs, la sensibilité
et les comparaisons supplémentaires restent disponibles en annexe.

Le noyau destiné à la présentation comprend donc cinq familles : difficulté, liberté,
rejouabilité, réactivité au profil et importance locale des nœuds. Les indices de support
seront calculés lorsqu'ils sont nécessaires aux formules ou à leur interprétation, sans
recevoir chacun une figure. La divergence complète des branches et la covariance de
présence sont reportées à l'article.

Les centralités classiques comme PageRank, le degré brut et les centralités de plus
court chemin ne sont pas retenues : elles ignorent les probabilités de lecture ou sont
déformées par les nœuds absorbants. La phase 4 privilégie les mesures fondées sur les
flux de chemins produits par $W^{(p)}$.

Le calcul canonique est implémenté par `scripts/4.1_compute_bop_indices.py`. Il produit
les tables par profil, nœud, arête et paire de profils dans
`data/processed/bop/<BOOK_ID>/`. Le contrôle indépendant
`scripts/tests/test_4_1_compute_bop_indices.py` reconstruit les matrices fondamentales et
vérifie les identités d'absorption, de flux, de durée, d'entropie, de couverture et de
divergence. Les formules exactes et les schémas de sortie sont documentés dans
`phase4_indices.md`. `scripts/4.2_summarize_bop_indices.py` extrait ensuite, sans
recalculer les indices, la référence neutre, la moyenne équilibrée, les effets marginaux,
le contraste contrôlé du risque, les valeurs locales prêtes à projeter sur le graphe et
six classements de paragraphes. Son validateur reproduit indépendamment toutes les
agrégations. `scripts/4.3_build_bop_presentation.py` transforme enfin ces synthèses en
trois diapositives principales et un tableau optionnel, tous disponibles en PNG 16:9 et
SVG éditable. La sélection, les messages et les précautions d'interprétation sont fixés
dans `phase4_presentation.md`. La phase 4 est terminée pour LW01.

#### Visualisation longitudinale du graphe

Une même représentation du graphe servira de fil visuel entre les phases 3 et 4. Pour
LW01, elle réutilise les centres des 350 nœuds numérotés du diagramme longitudinal de
Project Aon. Les identifiants `001`–`350` correspondent exactement aux paragraphes
canoniques `1`–`350`. Seules les coordonnées sont importées : les nœuds, arêtes, types et
poids affichés restent ceux du pipeline courant.

Les coordonnées sont extraites une seule fois et conservées dans
`project_aon_layout.csv`, accompagnées d'un manifeste donnant l'URL, l'empreinte SHA-256
et la transformation appliquée. Tous les profils et tous les indices utilisent exactement
ce même layout : une différence visuelle représente ainsi une différence de valeur, et
non un déplacement arbitraire des nœuds. Un layout algorithmique fondé sur le pré-graphe
reste disponible comme solution de repli pour les livres sans diagramme externe.

Les figures produites retiennent finalement :

- une vue **topologique** de la phase 3 ;
- un panneau où taille et couleur représentent la **probabilité de visite** neutre ;
- un panneau des principales **contributions à la mortalité** neutre ;
- un panneau de la **sensibilité au profil**, mesurée par l'étendue des probabilités de
  visite entre les 27 profils.

Ces trois indices locaux partagent une même diapositive afin de montrer que la colonne
vertébrale, les points de danger et les régions sensibles ne coïncident pas. Une carte
séparée de l'impact des choix et les contrastes par paires restent disponibles dans les
données, mais sont écartés de la présentation pour conserver un message concis.

Deux rendus sont produits à partir des mêmes coordonnées : un SVG longitudinal complet,
zoomable et portant les numéros des paragraphes, et une version simplifiée au format de
la présentation, où seuls les nœuds importants sont étiquetés. Les arêtes parallèles
peuvent être agrégées visuellement par couple source–cible, même si elles restent séparées
dans les données scientifiques.

Dans le modèle, toutes les morts rejoignent l'unique absorbant `Death`. Les afficher sous
forme de longues arêtes vers un même point rendrait la figure illisible. La projection de
présentation colore donc les paragraphes de mort et les transitions mortelles localement,
tout en indiquant dans la légende qu'ils correspondent au même absorbant. Le fichier de
calcul et les indices restent, eux, fondés sur le graphe canonique inchangé.

La vue structurelle utilise une couleur et une forme stables pour les principaux types de
nœuds : cercle blanc pour un paragraphe ordinaire, losange orange pour un combat, croix
rouge sombre pour une fin mortelle, étoile verte pour la victoire et cercle bleu sombre
pour le départ. Une petite croix rouge distincte signale une transition possible vers
`Death` sans transformer sa source en fin mortelle. Lorsque la couleur représente un
indice BoP, les formes conservent ces catégories.

`scripts/utils/extract_project_aon_layout.py` télécharge ou lit le SVG/SVGZ, contrôle la
correspondance avec les paragraphes canoniques et écrit les références. Le script
`4.0_visualize_graph.py` utilise ce layout par défaut, puis produit le SVG longitudinal et
la vue 16:9 du profil demandé. Tous les textes de la figure sont en anglais et son titre
est limité à `<BOOK_ID> - graph`. Les rendus 4.3 peuvent être régénérés sans refaire
l'extraction du layout ni les calculs BoP.

### Phase 5 — Analyse des trajectoires complètes avec un LLM

La position épistémologique est détaillée dans `docs/llm_digital_humanities.md` et la
spécification opérationnelle validée dans `docs/phase5_protocol.md`.

Cette phase passe de la structure probabiliste du livre aux histoires effectivement
produites par ses parcours. Elle devra :

1. sélectionner un nombre limité de trajectoires complètes issues des matrices
   $W^{(p)}$ ;
2. reconstruire pour chacune le texte narratif dans l'ordre de lecture, avec son profil,
   son issue et ses métadonnées structurelles conservés séparément ;
3. faire lire l'histoire complète par un LLM avec une sortie JSON contrainte ;
4. comparer les histoires entre elles et relier les résultats qualitatifs aux indices
   BoP de la phase 4.

Le corpus comprend 14 trajectoires : sept profils contrôlés — neutre et les deux extrêmes
de chacun des trois axes — croisés avec `Win` et `Death`. Chaque cellule est représentée
par le médoïde empirique de 2 000 trajectoires conditionnées par l'issue, tirées par
transformation de Doob. La distance fixée est la distance LCS normalisée entre suites de
paragraphes. Le chemin retenu est observé dans l'échantillon et minimise sa distance
moyenne aux autres tirages ; aucune sélection n'intervient après lecture du texte. Les
embeddings sont exclus : ils ajouteraient un second instrument sémantique sans être
nécessaires à ce plan contrôlé.

L'étape 5.0 est terminée pour LW01 : les tirages et les 14 médoïdes ont été calculés et
validés indépendamment. Les premiers résultats et les limites liées à l'échantillonnage
sont consignés dans `docs/phase5_results.md`.

#### Méthodes potentielles

| Méthode | Usage possible | Limite | Orientation actuelle |
| :--- | :--- | :--- | :--- |
| **Distances structurelles** | Comparer les suites de paragraphes, leur longueur, leur issue et leur chevauchement. | Ne mesure pas la similarité du contenu narratif. | **Oui — comparaison indépendante** |
| **Embeddings des histoires** | Regrouper un grand nombre de trajectoires par proximité sémantique. | Ajoute un modèle et une mesure difficile à interpréter ; inutile pour le petit pilote. | **Non — abandonné pour cette recherche** |
| **Évaluation LLM structurée** | Inférer les trois axes du profil et contrôler continuité causale et cohérence du profil sur les histoires complètes. | Sensible au modèle et au prompt. | **Oui — méthode principale** |
| **Comparaisons LLM par paires** | Comparer les médoïdes des extrêmes de chaque axe à issue identique. | Sensible à l'ordre A/B. | **Oui — 6 paires, évaluées dans les deux ordres** |
| **Extraction d'événements, entités et lieux** | Vérifier la continuité des personnages, objets, lieux et événements le long du parcours. | Demande une nouvelle annotation et une métrique de séquence. | **Non — extension future** |
| **Évaluation humaine** | Vérifier la validité d'un petit échantillon de jugements du LLM. | Coûteuse et difficile à étendre. | **Oui — contrôle requis sur 14 histoires et 6 paires** |

La grille individuelle contient uniquement le profil perçu sur `risk`, `morality` et
`action`, la `causal_continuity` et la `profile_coherence`. Les deux derniers champs sont
des résultats complémentaires et ne seront montrés que s'ils sont stables. Les champs
d'adéquation choix–conséquence, d'équité de l'issue et de qualité littéraire sont exclus.

Qwen3.6-27B recevra les histoires complètes et leurs choix, mais aucun profil, poids,
annotation sémantique ni indice BoP. Les justifications devront citer des choix ou
paragraphes vérifiables. Les quatorze histoires et les six paires seront annotées
humainement ; les comparaisons seront inversées pour détecter le biais de position.

Les résultats principaux seront la manifestation des trois axes sur ces chemins centraux,
la récupération des contrastes, la fuite entre axes et la confrontation descriptive
entre différence structurelle et `narrative_distinctness`. Ils seront rapportés comme des
effectifs sur des trajectoires sélectionnées, non comme une estimation de la distribution
de toutes les histoires. La présentation restera limitée à une seule diapositive.

### Phase 6 — Généralisation

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

## 8. Questions restant à traiter dans la phase 5

Le corpus, les grilles, Qwen3.6-27B et les contrôles sont fixés, et les médoïdes sont
calculés. Il reste à reconstruire les histoires, implémenter l'échange avec le
cluster, puis vérifier empiriquement la longueur des contextes, la stabilité des sorties
et l'utilité des deux champs complémentaires avant de choisir le contenu de la diapositive.

## 9. Documentation active

- `gamebook_global_plan.md` : objectifs, décisions et phases ;
- `graph_model.md` : pré-graphe, annotation et compilation de $W$ ;
- `phase4_indices.md` : formules, tables canoniques et validation des indices BoP ;
- `phase4_presentation.md` : sélection finale, figures et messages pour la présentation ;
- `phase5_protocol.md` : corpus, grilles, modèle, validation et sorties de la phase 5 ;
- `phase5_implementation_plan.md` : scripts locaux, paquet cluster et artefacts attendus ;
- `phase5_results.md` : résultats de la sélection des médoïdes et limites d'interprétation ;
- `llm_digital_humanities.md` : rôle, limites, audit et sources pour l'usage local des LLM ;
- `future_improvements.md` : limites connues et extensions reportées du pipeline ;
- `progress_log.md` : journal chronologique ;
- `notes.md` : questions de travail ;
- `archives/` : documents et décisions remplacés.
