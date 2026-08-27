# Phase 5 — Protocole d'annotation des trajectoires complètes

> **Statut au 27.08.2026 : protocole validé, étapes 5.0 et 5.1 implémentées.** Cette phase reste
> une preuve de concept courte. Elle privilégie quelques annotations bornées, vérifiables
> et directement reliées aux profils et aux résultats BoP de la phase 4. Chaque cellule
> profil–issue est représentée par un médoïde empirique de 2 000 trajectoires
> conditionnées par l'issue.

Le découpage des futurs scripts, le paquet envoyé au cluster et les fichiers attendus au
retour sont décrits dans `docs/phase5_implementation_plan.md`.

## 1. Question de recherche et périmètre

La phase 5 demande :

> Les profils probabilistes produisent-ils, à l'échelle d'histoires complètes, des
> comportements narrativement perceptibles et différenciés ?

L'unité d'analyse est toujours une **trajectoire complète**, du paragraphe initial à
`Win` ou `Death`. Le LLM ne réannote ni l'importance des paragraphes, ni les arêtes, ni les
indices déjà calculés par le formalisme Bag-of-Paths.

Cette itération exclut :

- les embeddings ;
- l'adéquation subjective entre choix et conséquences ;
- l'équité perçue de la victoire ou de la mort ;
- les scores généraux de qualité littéraire, de tension ou de richesse ;
- toute prétention à mesurer une réception réelle par les lecteurs.

Les sorties du LLM sont des annotations conditionnées par un modèle et un codebook. Un
petit ensemble humain sert à calibrer l'instrument, mais il n'existe pas de jeu humain de
validation dans cette preuve de concept. Les résultats ne constituent donc ni une mesure
objective au sens fort, ni une performance de généralisation démontrée.

## 2. Corpus de trajectoires

### 2.1 Profils contrôlés

Sept profils isolent les trois axes sans faire varier les deux autres :

| Contraste | Profils |
| :--- | :--- |
| Référence | `neutral_neutral_neutral` |
| Risque | `cautious_neutral_neutral`, `reckless_neutral_neutral` |
| Moralité | `neutral_selfish_neutral`, `neutral_noble_neutral` |
| Action | `neutral_neutral_physical`, `neutral_neutral_tactical` |

### 2.2 Issues et trajectoires retenues

Pour chaque profil, un médoïde empirique est sélectionné vers `Win` et un autre vers
`Death` :

$$
7\ \text{profils} \times 2\ \text{issues}
= 14\ \text{médoïdes empiriques}.
$$

Le corpus ne vise pas à estimer toute la variabilité interne d'une cellule. Il répond à
une question plus étroite : parmi un grand échantillon conditionné par l'issue, quelle
histoire réelle occupe la position la plus centrale sous une distance séquentielle fixée ?

### 2.3 Échantillonnage conditionnel

Pour une issue $o$, on calcule d'abord le potentiel :

$$
h_o(i)=P(\text{atteindre }o\mid X_0=i).
$$

La transformation de Doob donne alors, pour chaque arête étiquetée $e:i\to j$ :

$$
P_o(e\mid i)=\frac{w(e)h_o(j)}{h_o(i)}.
$$

Cette chaîne permet de tirer directement des trajectoires complètes sachant qu'elles se
terminent en $o$, sans rejeter les trajectoires de l'autre issue. Les multiarêtes restent
distinctes par `edge_id`. Dans chaque cellule, `5.0` produit exactement 2 000 tirages avec
une graine dérivée de la graine de base 42, de l'indice du profil et de l'issue.

### 2.4 Distance et médoïde empirique

Une trajectoire est représentée par sa suite ordonnée de nœuds, départ et issue compris.
Pour deux trajectoires $A$ et $B$, la distance fixée est :

$$
d(A,B)=1-\frac{2\,LCS(A,B)}{|A|+|B|},
$$

où $LCS$ est la plus longue sous-séquence commune. Cette mesure conserve l'ordre des
paragraphes, tolère des détours de longueurs différentes, vaut zéro pour deux suites
identiques et reste interprétable sans modèle sémantique supplémentaire.

Parmi les trajectoires distinctes observées, le médoïde empirique est :

$$
\hat\pi^* = \arg\min_{\pi\in S}
\frac{1}{N}\sum_{\rho\in S} n(\rho)d(\pi,\rho),
$$

où $n(\rho)$ est l'effectif du chemin $\rho$ dans les $N=2\,000$ tirages. Le chemin retenu
est donc une trajectoire possible et effectivement observée, contrairement à une suite
« moyenne » artificielle. Les règles suivantes sont fixées avant l'annotation :

- le nombre de tirages, la distance, les graines et la règle de départage sont identiques
  dans les quatorze cellules ;
- aucune trajectoire n'est remplacée selon son intérêt narratif ou après lecture du texte ;
- tous les chemins uniques et leurs effectifs sont archivés ;
- toute égalité de l'objectif est signalée et résolue par l'ordre lexicographique de la
  suite complète des `edge_id` ;
- la probabilité brute et conditionnelle du chemin retenu est consignée comme information,
  mais ne détermine pas la sélection ;
- le validateur régénère l'échantillon depuis la graine et recalcule le médoïde ;
- le MAP est calculé uniquement comme diagnostic de concentration et n'est jamais envoyé
  au LLM comme trajectoire à annoter.

Il s'agit d'un **médoïde empirique** : une autre graine peut sélectionner un chemin exact
différent, et le chemin central n'est ni le plus fréquent, ni la « trajectoire moyenne »,
ni le médoïde exact d'une distribution infinie. Un contrôle préliminaire à deux graines
sur le profil neutre a toutefois retrouvé des familles proches (similarité LCS 0,759 pour
`Win` et 0,831 pour `Death`). Cette limite est déclarée plutôt que présentée comme une
analyse de robustesse complète.

## 3. Reconstruction des histoires

Le document transmis au modèle contient toute la trajectoire dans l'ordre. Chaque étape
comprend :

```text
[PARAGRAPH 97]
Full narrative text...

[AVAILABLE CHOICES]
A. Defend the fallen Prince.
B. Run into the forest.

[CHOSEN ACTION]
A. Defend the fallen Prince.

[TRANSITION KIND]
Player choice
```

Les transitions sans décision sont marquées `Forced transition` ou
`Random or mechanical resolution`. Les options non choisies sont montrées uniquement pour
donner le contexte de la décision ; leurs conséquences narratives ne sont pas ajoutées.

Le modèle ne reçoit jamais :

- `profile_id` ni les niveaux générateurs des trois axes ;
- `semantic_risk`, `semantic_morality` ou `semantic_action` ;
- les poids, probabilités ou règles symboliques ;
- les indices et classements BoP ;
- les annotations humaines.

Ces métadonnées sont conservées dans un fichier séparé, puis réunies aux sorties seulement
après l'inférence.

## 4. Annotation individuelle

### 4.1 Profil narratif perçu

Le modèle infère les trois axes à partir de l'ensemble des décisions observées :

| Axe | Valeurs |
| :--- | :--- |
| `risk` | `cautious`, `neutral`, `reckless`, `unclear` |
| `morality` | `selfish`, `neutral`, `noble`, `unclear` |
| `action` | `physical`, `neutral`, `tactical`, `unclear` |

Pour chaque axe, il rend :

- un `label` ;
- un degré d'étayage `clear`, `mixed` ou `insufficient` ;
- une justification courte ;
- au plus trois choix probants ;
- au plus deux choix constituant une contre-preuve.

Les définitions du codebook sont :

- **cautious** : évitement répété des dangers évitables, recherche d'information ou de
  protection ;
- **reckless** : engagement répété dans des dangers évitables malgré les risques ;
- **selfish** : priorité répétée à la sécurité ou au gain personnel au détriment d'autrui ;
- **noble** : aide, protection ou sacrifice volontaire en faveur d'autrui ;
- **physical** : recours dominant à l'affrontement, à la force ou à l'action directe ;
- **tactical** : recours dominant à l'observation, à la préparation, à la diversion ou à
  l'évitement stratégique ;
- **neutral** : aucune orientation dominante n'est étayée ;
- **unclear** : la trajectoire ne contient pas assez de décisions pertinentes pour
  conclure.

Une action imposée, un combat obligatoire ou une résolution aléatoire ne constitue pas
une preuve du profil du joueur.

### 4.2 Continuité causale

`causal_continuity` recherche uniquement des ruptures globales appuyées sur le texte : un
événement suppose une cause absente, un état contredit explicitement un état antérieur, ou
le passage entre deux épisodes devient incompréhensible malgré la lecture de toute la
trajectoire.

| Valeur | Définition |
| :--- | :--- |
| `continuous` | Aucun problème causal vérifiable n'est trouvé. |
| `minor_gap` | Une liaison reste implicite ou ambiguë, sans rendre l'histoire globalement incompréhensible. |
| `broken` | Au moins une rupture ou contradiction étayée affecte l'enchaînement global. |
| `unclear` | Le texte fourni ne permet pas de trancher. |

Une ellipse, une transition rapide ou une coïncidence ne suffit pas à déclarer une rupture.
Tout `minor_gap` ou `broken` doit citer les deux paragraphes au minimum qui établissent le
problème. `continuous` signifie « aucun problème trouvé selon ce protocole », et non
« cohérence objectivement démontrée ».

### 4.3 Cohérence du profil

`profile_coherence` mesure la stabilité interne du comportement perçu sans révéler le
profil générateur :

| Valeur | Définition |
| :--- | :--- |
| `coherent` | Les décisions dessinent un profil global stable ; les exceptions sont rares ou expliquées par le contexte. |
| `mixed` | Des orientations concurrentes sont bien étayées, mais un profil reste partiellement lisible. |
| `incoherent` | Les décisions se contredisent de façon répétée et empêchent de dégager un profil stable. |
| `insufficient_evidence` | Trop peu de décisions permettent d'évaluer la stabilité. |

Ce champ ne mesure pas l'accord avec le profil générateur. Cet accord est calculé ensuite,
par le script d'analyse, entre `perceived_profile` et les métadonnées cachées au modèle.

### 4.4 Schéma individuel

```json
{
  "trajectory_id": "...",
  "perceived_profile": {
    "risk": {
      "label": "cautious|neutral|reckless|unclear",
      "support": "clear|mixed|insufficient",
      "justification": "...",
      "supporting_choice_refs": ["..."],
      "counterevidence_choice_refs": ["..."]
    },
    "morality": {
      "label": "selfish|neutral|noble|unclear",
      "support": "clear|mixed|insufficient",
      "justification": "...",
      "supporting_choice_refs": ["..."],
      "counterevidence_choice_refs": ["..."]
    },
    "action": {
      "label": "physical|neutral|tactical|unclear",
      "support": "clear|mixed|insufficient",
      "justification": "...",
      "supporting_choice_refs": ["..."],
      "counterevidence_choice_refs": ["..."]
    }
  },
  "causal_continuity": {
    "label": "continuous|minor_gap|broken|unclear",
    "justification": "...",
    "evidence_paragraph_ids": ["..."]
  },
  "profile_coherence": {
    "label": "coherent|mixed|incoherent|insufficient_evidence",
    "justification": "...",
    "supporting_choice_refs": ["..."],
    "counterevidence_choice_refs": ["..."]
  }
}
```

## 5. Comparaisons par paires

Les profils extrêmes sont comparés à issue identique, en utilisant leurs médoïdes :

| Axe | Paire |
| :--- | :--- |
| Risque | `cautious_neutral_neutral` / `reckless_neutral_neutral` |
| Moralité | `neutral_selfish_neutral` / `neutral_noble_neutral` |
| Action | `neutral_neutral_physical` / `neutral_neutral_tactical` |

Le plan contient donc :

$$
3\ \text{axes} \times 2\ \text{issues}
=6\ \text{paires}.
$$

Le modèle reçoit les deux histoires complètes, identifiées seulement comme A et B. Il ne
compte pas les paragraphes communs et ne reçoit aucune distance structurelle.

```json
{
  "comparison_id": "...",
  "narrative_distinctness": {
    "label": "low|medium|high|unclear",
    "justification": "..."
  },
  "perceived_profile_shift": {
    "risk": "A_more_cautious|similar|A_more_reckless|unclear",
    "morality": "A_more_selfish|similar|A_more_noble|unclear",
    "action": "A_more_physical|similar|A_more_tactical|unclear"
  },
  "profile_shift_justification": "...",
  "evidence_story_a": ["..."],
  "evidence_story_b": ["..."]
}
```

`narrative_distinctness` est ancré ainsi :

- `low` : même impression globale de parcours et de protagoniste ;
- `medium` : différence globale perceptible sur un fond narratif fortement partagé ;
- `high` : impression claire de deux manières différentes de vivre l'aventure ;
- `unclear` : preuves insuffisantes.

Chaque paire est réévaluée dans l'ordre B/A. Un résultat qui ne s'inverse pas correctement
est marqué `order_sensitive` et n'est pas utilisé comme comparaison stable.

### 5.1 Règles d'annotation pairwise

L'annotation porte sur l'**impression globale produite par les deux histoires complètes**.
Elle ne cherche pas à refaire les distances structurelles de la phase 4. L'annotateur :

1. lit A puis B entièrement avant de remplir la ligne ;
2. ignore les profils générateurs, l'axe contrôlé, les poids BoP et les annotations
   individuelles déjà produites ;
3. évalue `narrative_distinctness` à partir du parcours, des situations rencontrées et de
   la manière d'agir du protagoniste, sans compter manuellement les paragraphes communs ;
4. renseigne les trois directions de `perceived_profile_shift`, même lorsqu'un seul axe
   a été volontairement contrasté ;
5. utilise `similar` lorsque les histoires fournissent assez de preuves mais ne montrent
   pas de direction stable, et `unclear` lorsque les preuves sont insuffisantes ou non
   comparables ;
6. fonde les axes uniquement sur les décisions `Player choice` ou
   `Player choice: escape from combat`, jamais sur un combat imposé, un tirage ou l'issue ;
7. résume le contraste des trois axes dans `profile_shift_justification`, puis cite au
   plus cinq références par histoire dans `evidence_story_a` et
   `evidence_story_b`. Une référence de choix (`S012-C02`) étaye un déplacement de profil ;
   une référence d'étape (`S012`) peut étayer une différence narrative globale.

Les directions autorisées sont :

| Axe | Valeurs autorisées |
| :--- | :--- |
| `risk` | `A_more_cautious`, `similar`, `A_more_reckless`, `unclear` |
| `morality` | `A_more_selfish`, `similar`, `A_more_noble`, `unclear` |
| `action` | `A_more_physical`, `similar`, `A_more_tactical`, `unclear` |

Les preuves doivent concerner les histoires dans l'ordre indiqué par le canevas humain.
L'inversion B/A est un contrôle automatisé appliqué à Qwen ; l'humain n'annote qu'un seul
ordre par paire.

## 6. Mesures structurelles indépendantes

Pour les mêmes six paires, un script calcule sans LLM :

- les longueurs des trajectoires ;
- le nombre et la proportion de paragraphes communs ;
- le Jaccard des ensembles de paragraphes ;
- le nombre et la proportion d'arêtes communes ;
- la plus longue sous-séquence commune normalisée ;
- la distance d'édition normalisée ;
- la divergence BoP entre les profils générateurs.

Ces valeurs sont jointes aux annotations après l'inférence. Avec six paires, leur relation
avec `narrative_distinctness` reste descriptive et ne soutient pas un test inférentiel.

## 7. Modèle, prompt et inférence

### 7.1 Modèle fixé

Le modèle primaire est **`Qwen/Qwen3.6-27B`**, exécuté localement sur le cluster en BF16
avec vLLM et une sortie JSON contrainte. Le point de départ est :

- `temperature = 0` ;
- `seed = 42` ;
- thinking désactivé ;
- fenêtre effective de 32k tokens ;
- lots de petite taille ;
- aucune troncature.

La longueur réelle de chaque entrée et de la trajectoire la plus longue doit être mesurée.
Une histoire ou une paire dépassant la fenêtre configurée est signalée, jamais raccourcie.

### 7.2 Prompt sans exemple de trajectoire complète

Le prompt contient le codebook, le schéma JSON, les règles de preuve et quelques
contre-exemples courts. Il ne contient pas une trajectoire complète déjà annotée.

Exemples de règles :

```text
Fighting because combat is forced is not evidence of a physical profile.
A single action must not determine the global profile when the rest of the
trajectory points in another direction.
An abrupt transition is not a causal break unless the two cited passages
contain an unsupported dependency or an explicit contradiction.
Use unclear or insufficient_evidence when the trajectory does not support a label.
```

Quatre histoires humaines et trois paires de calibration servent à corriger le codebook et
les consignes, mais ne sont pas insérées comme longues démonstrations dans le prompt. Le
prompt final est figé avant l'analyse du corpus complet.

## 8. Calibration humaine et stabilité de l'instrument

Cette preuve de concept ne comporte pas de jeu humain de validation séparé. Avant de
consulter Qwen, l'annotation humaine est limitée à `T0001`, `T0004`, `T0009` et
`T0014`. Ces cellules sont choisies avant lecture afin de couvrir le neutre, un pôle de
chacun des trois axes et les deux issues. La correspondance exacte avec les profils et les
issues reste dans les métadonnées privées pendant l'annotation. Les dix autres
trajectoires sont analysées par Qwen mais ne sont pas présentées comme des données de
validation humaine.

L'annotation humaine pairwise est limitée à une paire par axe :

| Comparaison | Histoires dans le canevas |
| :--- | :--- |
| `C002` | A = `T0004`, B = `T0006` |
| `C003` | A = `T0007`, B = `T0009` |
| `C006` | A = `T0012`, B = `T0014` |

Ce plan exige donc quatre annotations individuelles, trois annotations pairwise et la
lecture de sept histoires distinctes. La sélection couvre exactement un contraste de
chaque axe, à issue identique, et réutilise une histoire individuellement annotée dans
chaque paire. L'axe et l'issue associés à chaque identifiant ne figurent ni dans le guide
ni dans l'annexe aveugle utilisés pendant l'annotation.

L'absence de validation séparée est acceptable ici parce que l'objectif est une
démonstration méthodologique exploratoire et non l'estimation d'une performance
prédictive. Elle est compensée partiellement, mais non annulée, par un codebook générique,
un prompt entièrement lisible et archivé, l'absence de règles propres aux personnages ou
paragraphes de LW01, et le gel du prompt avant le run complet. La lisibilité rend le
surajustement auditable ; elle ne démontre pas la transférabilité à LW02. Les concordances
sur le petit ensemble humain sont donc rapportées comme **concordances de calibration**,
jamais comme accuracy ou validation hors échantillon.

Le run individuel couvre une seule fois les 14 histoires avec le prompt figé. Les six
paires sont toutes évaluées dans les deux ordres afin de contrôler le biais de position,
qui concerne directement la tâche comparative.

Les résultats sont rapportés en effectifs bruts lorsque les sous-ensembles sont petits. La
confiance déclarée par le modèle n'est pas utilisée comme mesure de fiabilité.

## 9. Indicateurs retenus

### 9.1 Résultats principaux

1. **Manifestation sur les trajectoires centrales** : effectif des 14 médoïdes dont
   le profil perçu correspond au niveau générateur, séparément pour `risk`, `morality` et
   `action`, avec les `unclear` rapportés à part. Ce résultat décrit les chemins centraux
   retenus ; ce n'est ni une accuracy du modèle ni une estimation de toutes les
   trajectoires possibles.
2. **Récupération du contraste** : effectif des six paires où la direction attendue de
   l'axe contrôlé est retrouvée.
3. **Fuite entre axes** : fréquence à laquelle les deux axes maintenus constants sont
   néanmoins perçus comme différents dans une paire contrôlée.
4. **Structure et impression narrative** : confrontation descriptive entre les distances
   structurelles et `narrative_distinctness`.

### 9.2 Résultats complémentaires

- distribution de `causal_continuity` ;
- distribution de `profile_coherence` et relation descriptive avec la manifestation du
  profil ;
- différences entre `Win` et `Death`, sans interprétation causale.

### 9.3 Contrôles de qualité

- concordance descriptive Qwen–humain sur les quatre histoires de calibration ;
- concordance descriptive sur les trois comparaisons pairwise de calibration ;
- taux de `unclear` et `insufficient_evidence` ;
- validité et pertinence des références citées ;
- stabilité après inversion A/B ;
- taux de sorties JSON valides et non tronquées.

La transférabilité à un autre livre n'est pas un contrôle réalisé dans cette itération ;
elle devra faire l'objet d'une réplication ultérieure avec le prompt figé.

## 10. Sorties attendues

Les noms de 5.0 et 5.1 sont désormais fixés ; les suivants restent indicatifs :

| Fichier | Contenu |
| :--- | :--- |
| `medoid_trajectories.jsonl` | Séquences des 14 médoïdes, profils, issues, objectif, probabilités, graines et empreintes produites par 5.0. |
| `conditional_path_counts.jsonl` | Chemins conditionnels uniques, effectifs et probabilités permettant d'auditer les médoïdes. |
| `trajectories.jsonl` | Textes complets et choix reconstruits par 5.1, avec les données privées séparées avant l'inférence. |
| `trajectory_private_metadata.jsonl` | Correspondance locale entre identifiants opaques, profils, issues et chemins ; jamais transmise au modèle. |
| `trajectory_pairs.jsonl` | Six comparaisons extrême–extrême matérialisées dans les ordres A/B et B/A. |
| `pair_private_metadata.jsonl` | Axe, issue et profils générateurs des six paires, conservés localement. |
| `medoid_selection_report.json` | Conditionnement, tirages, distance, règles de sélection, empreintes et MAP diagnostiques. |
| `trajectory_corpus_report.json` | Sources, empreintes, tailles du corpus, sélection de calibration humaine et estimation des longueurs. |
| `trajectory_annotations.jsonl` | Sorties individuelles brutes et normalisées de Qwen. |
| `pairwise_annotations.jsonl` | Comparaisons A/B et B/A. |
| `human_trajectory_annotations.jsonl` | Quatre annotations humaines individuelles de calibration, séparées des sorties du modèle. |
| `human_pairwise_annotations.jsonl` | Trois annotations humaines pairwise de calibration, séparées des sorties du modèle. |
| `pair_structural_metrics.csv` | Chevauchements, distances séquentielles et divergences BoP. |
| `phase5_summary.csv` | Indicateurs principaux, complémentaires et contrôles. |
| `phase5_manifest.json` | Modèle, révision, prompt, paramètres, matériel, durées et empreintes. |

## 11. Présentation

La phase 5 doit tenir sur une seule diapositive :

1. le plan `7 profils × 2 issues = 14 médoïdes conditionnels` ;
2. la manifestation des profils sur ces histoires centrales et la récupération des axes ;
3. une confrontation courte entre distance structurelle et différence narrative ;
4. une ligne donnant la concordance de calibration et la stabilité A/B–B/A.

`causal_continuity` et `profile_coherence` sont calculés mais ne seront montrés que si leur
résultat est à la fois stable et utile. Aucun exemple n'est choisi après coup sans que sa
règle de sélection soit explicitée.

Phrase proposée :

> We asked a local 27B model to infer player profiles from complete stories, without
> access to edge annotations or BoP results. This tests whether probabilistic structural
> differences become perceptible narrative differences.
