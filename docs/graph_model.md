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
| **L2 — Incertitude** | Hasard et règles de pondération évaluées à la compilation. | Inclus sous forme symbolique dans le pré-graphe. |
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
numériques qu'après fourniture d'un profil et des hypothèses fixes de l'expérience.

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
| `transition_kind` | `forced`, `profile_choice`, `random`, `kai`, `state_condition`, `combat`, `escape`, `outcome` ou `manual`. |
| `weight_rule` | `constant`, `profile_choice` ou `formula`. |
| `weight_value` | Valeur d'une probabilité exacte, si elle existe déjà. |
| `weight_expression` | Règle symbolique évaluée avec le profil et la configuration fixe. |
| `condition_kind`, `condition_value` | Condition conservée si nécessaire. |
| `semantic_risk`, `semantic_morality`, `semantic_action` | Annotations utilisées pour les choix de profil. |
| `origin` | `auto` ou `supervised`. |
| `source_ref` | Provenance dans la phase 1 ou la supervision. |
| `note` | Justification éventuelle, notamment pour une règle supervisée. |

Une arête constante remplit `weight_value`. Une règle évaluée à la compilation remplit
`weight_expression`, qu'elle dépende du profil ou d'une hypothèse fixe. Le pré-graphe ne
contient donc pas encore une distribution numérique complète.

## 4. Compilation pour un profil

La phase 3 utilise une seule définition de profil. Un profil $p$ contient exactement :

- `profile_id` ;
- `risk` : `cautious`, `neutral` ou `reckless` ;
- `morality` : `selfish`, `neutral` ou `noble` ;
- `action` : `physical`, `neutral` ou `tactical`.

Le produit cartésien donne $3^3=27$ profils. Il n'existe pas de profil alternatif pour
les disciplines, le combat, la fuite ou les ressources.

Ces mécanismes sont placés dans une configuration fixe de l'expérience, commune aux 27
profils :

- `kai_availability` : disponibilité marginale de toute discipline, fixée à $0{,}5$ ;
- `combat_win_probability` : probabilité unique de gagner un combat ;
- `escape_probability` : probabilité unique de prendre une fuite lorsqu'elle est
  proposée ;
- `has_condition` : probabilité unique de satisfaire toute condition persistante
  simple, objet, monnaie ou Endurance ;
- les coefficients globaux qui transforment la correspondance entre un profil et les
  annotations sémantiques en affinité positive.

Les valeurs numériques encore à choisir sont des hypothèses de l'expérience, pas des
dimensions de profil. L'interface recommandée matérialise cette séparation :

```python
compiler = WCompiler(pre_graph, fixed_settings)
W = compiler.generate_W(profile)
```

Pour une arête $e$, chaque axe reçoit le coefficient `matching`, `neutral` ou `opposed`.
L'affinité $r_p(e)$ est le produit des trois coefficients. Si le profil ou l'arête est
neutre sur un axe, le coefficient `neutral` est utilisé. Les valeurs provisoires sont
respectivement 2, 1 et 0,5 ; le profil entièrement neutre donne donc $r_p(e)=1$ pour
toutes les arêtes de choix.

Pour une configuration fixe $s$, la compilation est une fonction :

$$
(\mathcal G^\ast,s,p)\longmapsto W^{(p;s)}.
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
Dans les expressions du pré-graphe, `choice_share(i, j)` désigne cette part normalisée
pour l'arête $i\rightarrow j$ parmi les choix encore disponibles.

### 5.3 Tirage aléatoire

Pour une table uniforme de dix valeurs, une branche couvrant $m$ résultats reçoit :

$$
w_e=\frac{m}{10}.
$$

Une suite de tirages est aplatie en une distribution finale sans créer de nœud de
résolution.

### 5.4 Disciplines

La notation `kai_available("Discipline")` vaut toujours le paramètre fixe
`kai_availability`, égal à $0{,}5$ dans cette itération. Lorsqu'une route Kai standard
est disponible, elle est prise ; la masse restante est répartie entre les autres choix
avec `choice_share`. Dans un groupe où la route Kai reste elle-même un choix,
`kai_availability` devient son facteur de disponibilité dans
`available_choice_share`.

Cette valeur est une approximation marginale de population. Elle ne décrit ni la liste
des disciplines d'un joueur réel ni un comportement aléatoire en cours de partie.
Le convertisseur détecte le nom écrit après « Discipline of » sans maintenir une liste
fermée : les disciplines Kai, Magnakai et Grand Master des autres livres utilisent donc
la même règle.

### 5.5 Conditions d'état persistant

Le pré-graphe ne reconstruit ni l'inventaire, ni la monnaie, ni l'Endurance au fil du
parcours. Il peut néanmoins conserver une condition simple sous la forme :

```text
condition_available("type", "valeur")
```

Le convertisseur reconnaît actuellement la possession d'un objet, un nombre minimal de
Gold Crowns et un seuil minimal d'Endurance. La route conditionnelle reçoit cette
expression ; sa route complémentaire reçoit `1 - condition_available(...)`. Les types
produits sont `has_item`, `gold_crowns_at_least` et `endurance_at_least`, avec une
variante suffixée par `_absent` sur l'arête complémentaire.

Cette notation ne prétend pas calculer la condition depuis les paragraphes précédents.
Lors de la compilation, tout appel à `condition_available(type, value)` reçoit le même
paramètre fixe `has_condition`, indépendamment de `type` et de `value`. Ces deux arguments
restent dans le pré-graphe uniquement pour la provenance et de futures extensions. Une
condition simple positive vaut donc `has_condition` et sa complémentaire vaut
`1 - has_condition`. Une condition composée, ambiguë, sans alternative identifiable ou
mêlée à une autre mécanique reste entièrement soumise à supervision.

Lorsqu'un paragraphe supervisé propose plusieurs choix dont certains seulement sont
conditionnels, l'agentivité est conservée avec :

$$
\operatorname{available\_choice\_share}(i,j,a_j)
=\frac{a_j r_p(i,j)}{\sum_k a_k r_p(i,k)},
$$

où $a_j$ vaut `condition_available(...)`, `kai_available(...)` ou 1 pour une option
toujours disponible. Cette règle est utilisée aux §23 et 334 : posséder un objet ou une
discipline ouvre une option sans obliger le joueur à la prendre.

### 5.6 Combat

La chance de victoire n'est pas fixée dans le pré-graphe. La phase 3 utilise cependant
une seule valeur $v=$ `combat_win_probability`, commune à tous les combats et profils.

Pour un combat simple :

$$
w_{i\rightarrow\text{suite}}=v,
\qquad
w_{i\rightarrow\mathrm{Death}}=1-v.
$$

Si la victoire est suivie d'un RNT de probabilités $r_j$ :

$$
w_{i\rightarrow j}=vr_j,
\qquad
w_{i\rightarrow\mathrm{Death}}=1-v.
$$

Si elle est suivie de choix dont les parts sont $c_j^{(p)}$ :

$$
w_{i\rightarrow j}^{(p)}=vc_j^{(p)},
\qquad
w_{i\rightarrow\mathrm{Death}}^{(p)}=1-v.
$$

Dans le fichier de supervision, ces parts sont notées
`postcombat_choice_share(i, j)`. Elles sont normalisées uniquement entre les choix
accessibles après la victoire.

### 5.7 Combat avec évasion ou issues particulières

Une fuite proposée après un ou plusieurs rounds dépend réellement de la décision du
joueur et de sa survie jusqu'à cette occasion. Comme les rounds ne sont pas simulés,
cette itération l'approxime par un paramètre global $f=$ `escape_probability`. Pour un
combat avec fuite simple :

$$
P(\mathrm{escape})=f,\qquad
P(\mathrm{win})=(1-f)v,\qquad
P(\mathrm{death})=(1-f)(1-v).
$$

Le pré-graphe conserve ces issues sous la forme d'une distribution catégorielle :

$$
\sum_o \operatorname{combat\_outcome}(i,o)=1.
$$

Un cas particulier peut employer des issues plus précises, par exemple
`win_with_endurance_loss`, `win_without_endurance_loss`, `win_within_4_rounds` ou
`continue_after_4_rounds`. Les répartitions supplémentaires nécessaires sont des
exceptions fixes de la configuration du livre. Elles doivent être normalisées, mais ne
créent aucune dimension de profil.

Une blessure non fatale pendant la fuite est conservée dans `note`, mais ne crée pas un
état supplémentaire. L'Endurance et les tables de combat ne sont pas simulées dans le
pré-graphe.

## 6. Mécaniques incluses et exclues

| Mécanique | Décision | Justification |
| :--- | :--- | :--- |
| Topologie et issues | **Incluse — L0** | Socle commun aux fictions à embranchements. |
| Choix explicites | **Inclus — L1** | Les poids varient selon le profil. |
| Hasard | **Inclus — L2** | Les probabilités textuelles sont convertibles. |
| Combat | **Inclus abstraitement — L2** | Une probabilité de victoire fixe est commune à tous les combats et profils. |
| Évasion | **Incluse abstraitement — L1/L2** | Une probabilité de fuite fixe est commune à tous les profils. |
| Disciplines et compétences | **Incluses comme hypothèse fixe — L1/L2** | Toute discipline a une disponibilité marginale de 0,5. |
| Endurance, dégâts et soins | **État exclu — L3** | Aucun suivi dynamique ; tout seuil simple utilise `has_condition`. |
| Objets, inventaire et monnaie | **État exclu — L3** | Aucun inventaire dynamique ; toute condition simple utilise `has_condition`. |
| Repas et équipement | **Exclus — L3** | Mécaniques trop spécifiques au système. |
| Modificateurs de combat | **Extension reportée** | Ils pourront plus tard alimenter une configuration de combat plus détaillée. |
| Énigmes et liens cachés | **Ajoutés seulement si vérifiables** | Aucune cible n'est inventée. |

Les occurrences des mécaniques exclues restent disponibles comme métadonnées ou comme
conditions symboliques lorsqu'une disponibilité simple peut être isolée sans simuler L3.

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
| Compétence ou condition | Règle de disponibilité évaluée avec une hypothèse fixe. |
| Combat | Règles symboliques évaluées avec la probabilité de victoire fixe. |
| Paragraphe mixte | Composition symbolique si elle est simple ; sinon supervision. |
| État persistant non simulé | Hypothèse fixe `has_condition` ou supervision. |

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
| Objet ou monnaie | Condition simple et complément convertis symboliquement. | §9, 12 et 173 automatiques ; condition composée au §23. |
| Seuil d'Endurance | Condition simple et complément convertis symboliquement. | §203 automatique. |
| Combat simple : 17 paragraphes | `combat_win(source)` et `1-combat_win(source)`. | Aucune. |
| Combat suivi d'un RNT | Composition automatique. | Aucune : §17. |
| Combat suivi de choix | Composition après annotation sémantique. | §112, 208 et 229. |
| Combat avec évasion | Règles de victoire, mort et évasion. | §43, 169, 180, 191 et 220. |
| Combat dépendant de sa durée | Issues avant/après quatre rounds. | §231 et 339. |
| Combat avec/sans perte d'Endurance | Deux issues de victoire et mort. | §227. |
| Cas inconnu | Blocage de la source entière. | Aucun autre cas connu. |

La file connue contient 14 paragraphes : §21, 23, 43, 112, 169, 180, 191, 208, 220,
227, 229, 231, 334 et 339. Les §9, 12, 173 et 203, présents dans la file initiale, sont
désormais convertis automatiquement.

La colonne `enemies`, non `potential_death`, identifie les combats. Les colonnes
`health_modifier`, `special_mechanic` et `items_granted` ne sont pas assez
exhaustives pour prouver l'absence d'une mécanique.

## 8. Phase 2 — fichiers produits

La phase 1 reste inchangée. La phase 2 utilise :

```text
# Brouillon automatique
data/processed/pregraph/<BOOK_ID>/auto_edges.csv
data/processed/pregraph/<BOOK_ID>/review_queue.csv

# Tableau créé vide puis annoté
data/for_graph_model/<BOOK_ID>_supervision.csv

# Résultat de la phase 2
data/processed/pregraph/<BOOK_ID>/pregraph_nodes.csv
data/processed/pregraph/<BOOK_ID>/pregraph_edges.csv
data/processed/pregraph/<BOOK_ID>/conversion_report.csv
```

### 8.1 Tableau d'annotation

L'étape A crée `<BOOK_ID>_supervision.csv` avec son en-tête et aucune ligne. Ce
fichier n'est jamais écrasé s'il existe déjà.

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
| `weight_expression` | Formule symbolique évaluée pendant la compilation. |
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
| 43 | 195 | `combat` | `formula` | `combat_outcome(43, "win")` |
| 43 | 106 | `escape` | `formula` | `combat_outcome(43, "escape")` |
| 43 | `Death` | `combat` | `formula` | `combat_outcome(43, "death")` |

Les constantes décrivent un hasard objectif. Les expressions comme
`combat_win(112)`, `postcombat_choice_share(112, 33)` ou
`combat_outcome(43, "escape")` restent symboliques jusqu'à la phase 3. Le compilateur
les résout à partir du profil comportemental pour les parts de choix et des hypothèses
fixes pour les combats.

### 8.2 Règles appliquées à la supervision de LW01

Le fichier `LW01_supervision.csv` applique les conventions suivantes :

1. **Tirages successifs (§21).** Les chemins du petit arbre de tirages sont aplatis. Les
   probabilités finales sont 0,60 vers le §189, 0,04 vers le §312 et 0,36 vers `Death`.
2. **Choix soumis à plusieurs disponibilités (§23 et 334).** Chaque option reçoit
   `available_choice_share(source, target, disponibilité)`. Une clé ou une discipline
   rend le choix disponible mais ne le rend pas obligatoire. Les axes sémantiques sont
   annotés manuellement pour toutes les options.
3. **Choix après victoire (§112, 208 et 229).** Chaque destination reçoit
   `combat_win(source) * postcombat_choice_share(source, target)` ; `Death` reçoit
   `1 - combat_win(source)`.
4. **Combat avec fuite (§43, 169, 180, 191 et 220).** Les trois issues `win`, `escape`
   et `death` sont représentées par `combat_outcome(source, issue)`. Cette distribution
   est résolue avec les probabilités globales de victoire et de fuite.
5. **Issues de combat particulières (§227, 231 et 339).** La même distribution
   catégorielle distingue la victoire avec ou sans perte d'Endurance, la victoire avant
   quatre rounds, la continuation après quatre rounds, la fuite et la mort selon le
   texte du paragraphe.
6. **État persistant.** Les blessures et autres effets non fatals sont signalés dans les
   notes mais ne provoquent aucune expansion L3.

Pour toute source fondée sur `combat_outcome`, les expressions sortantes doivent former
une distribution normalisée. Pour toute source utilisant `available_choice_share` ou
`postcombat_choice_share`, les parts sont normalisées sur le groupe de choix effectivement
disponible.

## 9. Recette courte de la phase 2

### A — Préparer automatiquement

Écrire puis lancer :

```bash
uv run python scripts/2.1_prepare_pregraph.py --book LW01
```

Le script :

1. charge les tables de phase 1 et groupe les arêtes par source ;
2. ajoute les nœuds `Death` et `Win`, puis relie les 17 pré-terminaux ;
3. transforme les cas entièrement reconnus dans `auto_edges.csv` ;
4. écrit les sources non reconnues dans `review_queue.csv`, avec leur texte, leurs
   arêtes et la raison du blocage ;
5. crée `<BOOK_ID>_supervision.csv` vide avec les colonnes du §8.1.

Le script de production ne connaît aucune liste d'exceptions. Toute combinaison non
reconnue rejoint la file au lieu d'être interprétée silencieusement. Après son exécution,
un contrôle léger peut être lancé :

```bash
uv run python scripts/tests/test_2_1_prepare_pregraph.py --book LW01
```

Il vérifie la couverture des arêtes, les règles élémentaires, les fins explicites et,
pour LW01 seulement, la liste des 14 paragraphes déjà auditée ainsi que la conversion
symbolique des conditions aux §9, 12, 173 et 203.

### B — Annoter les exceptions

1. Ouvrir `review_queue.csv` et relire le texte de chaque source.
2. Ajouter dans `<BOOK_ID>_supervision.csv` une ligne par transition finale.
3. Décrire toute la distribution sortante de chaque source, pas seulement la transition
   corrigée.
4. Utiliser une constante seulement si elle est déductible du texte.
5. Utiliser `profile_choice` ou une formule symbolique pour toute probabilité qui doit
   être résolue pendant la compilation.
6. Ajouter une note courte justifiant la décision.

Le fichier est terminé lorsque les 14 sources de `review_queue.csv` y sont toutes
représentées et qu'aucune règle requise n'est vide.

### C — Finaliser le pré-graphe

Écrire puis lancer :

```bash
uv run python scripts/2.2_finalize_pregraph.py --book LW01
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

Les profils et les hypothèses fixes sont définis dans deux fichiers séparés :

```text
data/for_graph_model/behavioral_profiles.json
data/for_graph_model/LW01_compilation_settings.json
```

Chaque profil suit le même schéma à quatre champs : `profile_id`, `risk`, `morality` et
`action`. Les 27 combinaisons sont générées exhaustivement. Un fichier séparé contient
les paramètres fixes `kai_availability`, `combat_win_probability`,
`escape_probability`, `has_condition`, les coefficients d'affinité et, si nécessaire,
les distributions particulières propres au livre. Le compilateur en déduit les
`available_choice_share` et `postcombat_choice_share`. Un paramètre nécessaire manquant
provoque une erreur : le compilateur n'invente pas de valeur.

Le contrat minimal des deux fichiers est :

| Fichier des profils | Valeur autorisée |
| :--- | :--- |
| `profile_id` | Identifiant unique. |
| `risk` | `cautious`, `neutral` ou `reckless`. |
| `morality` | `selfish`, `neutral` ou `noble`. |
| `action` | `physical`, `neutral` ou `tactical`. |

| Configuration fixe | Rôle |
| :--- | :--- |
| `kai_availability` | Nombre dans $[0,1]$, égal à 0,5 pour cette itération. |
| `combat_win_probability` | Nombre dans $[0,1]$, identique pour tous les combats. |
| `escape_probability` | Nombre dans $[0,1]$, identique pour toutes les fuites. |
| `has_condition` | Nombre dans $[0,1]$, utilisé pour tout `condition_available(type, value)`. |
| `choice_affinities` | Coefficients positifs communs qui distinguent accord, neutralité et opposition sur les axes. |
| `special_combat_outcomes` | Exceptions normalisées propres au livre, seulement si les issues ne se ramènent pas à `win`, `escape` et `death`. |

Le script :

```bash
uv run python scripts/3.0_generate_profiles.py
uv run python scripts/3.1_compile_w.py \
  --book LW01 \
  --profiles data/for_graph_model/behavioral_profiles.json \
  --settings data/for_graph_model/LW01_compilation_settings.json
```

itère sur tous les profils et produit :

```text
data/processed/graph/LW01/<profile>/compiled_edges.csv
data/processed/graph/LW01/<profile>/W.csv
```

Pour chaque profil, il vérifie que les poids sont finis et positifs ou nuls, que chaque
ligne non terminale somme à 1 et que `Death`/`Win` sont les deux seuls nœuds
absorbants.

L'option répétable `--profile <PROFILE_ID>` limite la compilation à un ou plusieurs
profils. Le contrôle indépendant s'exécute ensuite, par exemple pour la référence
neutre :

```bash
uv run python scripts/tests/test_3_1_compile_w.py \
  --book LW01 \
  --profile neutral_neutral_neutral
```

Le validateur compare les arêtes compilées au pré-graphe, recalcule leur agrégation dans
$W$, vérifie les distributions locales et les deux états absorbants, puis résout les
probabilités d'absorption. Il échoue si une partie de la masse ne rejoint pas `Death` ou
`Win`.

La configuration LW01 actuelle est une configuration technique initiale : les quatre
probabilités globales valent 0,5. Pour les §227, 231 et 339, les issues supplémentaires
sont données par des distributions fixes normalisées. Ces valeurs permettent de tester
le pipeline ; elles devront être justifiées ou présentées explicitement comme hypothèses
avant l'analyse scientifique.

## 11. Critères de fin

La phase 2 est terminée lorsque :

- `pregraph_nodes.csv` contient les 350 paragraphes, `Death` et `Win` ;
- les 17 pré-terminaux sont reliés à leur issue ;
- les 14 paragraphes de la file de supervision sont entièrement annotés ;
- toutes les transitions possèdent une règle constante ou symbolique ;
- le pré-graphe peut être régénéré depuis la phase 1 et la supervision.

La phase 3 est terminée lorsque les 27 profils produisent des matrices $W$ valides avec
la même configuration fixe. Les indices BoP et l'étude des trajectoires commencent
ensuite. Tous les profils sont calculés, mais seuls quelques archétypes et les effets
agrégés par axe sont destinés à la présentation.
