# Phase 5 — Protocole d'annotation des trajectoires complètes

> **Statut au 26.08.2026 : protocole validé, implémentation à faire.** Cette phase reste
> une preuve de concept courte. Elle privilégie quelques annotations bornées, vérifiables
> et directement reliées aux profils et aux résultats BoP de la phase 4. Chaque cellule
> profil–issue est représentée par sa trajectoire conditionnelle la plus probable (MAP),
> calculée exactement et non tirée au hasard.

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

Les sorties du LLM sont des annotations conditionnées par un modèle et un codebook. Elles
doivent être vérifiées contre des annotations humaines et ne constituent pas des mesures
objectives au sens fort.

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

Pour chaque profil, une trajectoire conditionnelle la plus probable est calculée vers
`Win` et une autre vers `Death` :

$$
7\ \text{profils} \times 2\ \text{issues}
= 14\ \text{trajectoires MAP}.
$$

Le corpus ne vise donc ni à estimer la variabilité interne d'une cellule, ni à représenter
toute la masse des chemins possibles. Il répond à une question plus étroite et
reproductible : quelle histoire complète est individuellement la plus probable pour ce
profil, sachant que l'issue fixée est atteinte ?

### 2.3 Calcul exact de la trajectoire conditionnelle MAP

Pour une trajectoire étiquetée $\pi=(e_1,\ldots,e_m)$ conduisant du départ à l'issue $o$,
où $w(e)$ est le `compiled_weight` de l'arête, le modèle attribue le poids :

$$
P(\pi)=\prod_{k=1}^{m}w(e_k).
$$

Le conditionnement sur l'issue ne change pas le chemin maximisant cette quantité :

$$
P(\pi\mid o)=\frac{P(\pi)}{P(o)},
$$

car $P(o)$ est constant pour tous les chemins comparés. La même conclusion découle de la
transformation de Doob : ses facteurs $h_o(j)/h_o(i)$ se télescopent le long d'une
trajectoire terminée en $o$.

Le produit est transformé en somme en donnant à chaque arête de probabilité strictement
positive le coût :

$$
c(e)=-\log w(e).
$$

La trajectoire MAP est alors un plus court chemin dans le multigraphe pondéré. Les arêtes
de poids nul sont exclues. Comme $0<w(e)\leq1$, les coûts sont non négatifs et un
algorithme de Dijkstra suffit. Le calcul part de `compiled_edges.csv`, plutôt que de la
matrice dense qui agrège les arêtes de mêmes extrémités : les arêtes parallèles conservent
ainsi leur identité et leur choix narratif. Les règles suivantes sont fixées avant toute
annotation :

- le même algorithme et la même règle de départage déterministe sont employés dans les
  quatorze cellules ;
- aucune trajectoire n'est remplacée selon son intérêt narratif ou après lecture du texte ;
- le produit des poids $P(\pi)$, son logarithme, la probabilité de l'issue $P(o)$ et la
  part conditionnelle $P(\pi\mid o)=P(\pi)/P(o)$ sont consignés ;
- toute égalité entre plusieurs chemins optimaux est signalée et résolue par un ordre
  canonique des identifiants d'arêtes ;
- tout cycle atteignable de coût nul est une erreur bloquante, car il rendrait la
  trajectoire modale ambiguë ;
- chaque trajectoire doit atteindre l'issue demandée et être reproductible depuis la
  matrice $W$ archivée.

Cette sélection produit un **mode**, et non une médiane ou un médoïde. Le chemin le plus
probable peut être court ou isolé alors qu'une famille de chemins voisins concentre une
masse totale supérieure. Cette limite est explicitement conservée dans l'interprétation ;
les médoïdes et l'étude de la dispersion sont reportés à une extension ultérieure.

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

Les profils extrêmes sont comparés à issue identique, en utilisant leurs trajectoires MAP :

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

Quatre histoires humaines de calibration servent à corriger le codebook et les consignes,
mais ne sont pas insérées comme longues démonstrations dans le prompt. Le prompt final est
figé avant l'analyse du reste du corpus.

## 8. Validation humaine et stabilité de l'instrument

Les 14 trajectoires MAP sont annotées humainement avant de consulter Qwen :

- quatre histoires servent à la calibration ;
- dix histoires restent un petit ensemble de validation ;

Les six comparaisons, trois axes par deux issues, sont également annotées humainement. Les
preuves citées peuvent ainsi être contrôlées sur la totalité du corpus retenu.

Le run primaire couvre les 14 histoires. Une variante prédéfinie du prompt, qui conserve
exactement les mêmes définitions et ne change que leur ordre de présentation, est appliquée
aux 14 histoires pour estimer la sensibilité à la formulation. Les six paires sont
toutes évaluées dans les deux ordres.

Les résultats sont rapportés en effectifs bruts lorsque les sous-ensembles sont petits. La
confiance déclarée par le modèle n'est pas utilisée comme mesure de fiabilité.

## 9. Indicateurs retenus

### 9.1 Résultats principaux

1. **Manifestation sur les trajectoires modales** : effectif des 14 trajectoires MAP dont
   le profil perçu correspond au niveau générateur, séparément pour `risk`, `morality` et
   `action`, avec les `unclear` rapportés à part. Ce résultat décrit les chemins modaux
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

- accord exact Qwen–humain sur les dix histoires de validation ;
- accord sur les six comparaisons humaines ;
- taux de `unclear` et `insufficient_evidence` ;
- validité et pertinence des références citées ;
- stabilité entre les deux formulations sur les 14 histoires ;
- stabilité après inversion A/B ;
- taux de sorties JSON valides et non tronquées.

## 10. Sorties attendues

Les noms restent indicatifs jusqu'à l'implémentation :

| Fichier | Contenu |
| :--- | :--- |
| `trajectories.jsonl` | Textes complets, choix, issues, profils cachés au modèle, probabilités MAP et empreintes. |
| `map_selection_report.json` | Algorithme, coûts, probabilités brutes et conditionnelles des chemins, égalités et règle de départage. |
| `trajectory_annotations.jsonl` | Sorties individuelles brutes et normalisées de Qwen. |
| `pairwise_annotations.jsonl` | Comparaisons A/B et B/A. |
| `human_annotations.jsonl` | Calibration et validation humaines, séparées des sorties du modèle. |
| `pair_structural_metrics.csv` | Chevauchements, distances séquentielles et divergences BoP. |
| `phase5_summary.csv` | Indicateurs principaux, complémentaires et contrôles. |
| `phase5_manifest.json` | Modèle, révision, prompt, paramètres, matériel, durées et empreintes. |

## 11. Présentation

La phase 5 doit tenir sur une seule diapositive :

1. le plan `7 profils × 2 issues = 14 trajectoires conditionnelles MAP` ;
2. la manifestation modale et la récupération des trois axes ;
3. une confrontation courte entre distance structurelle et différence narrative ;
4. une ligne donnant l'accord humain et la stabilité.

`causal_continuity` et `profile_coherence` sont calculés mais ne seront montrés que si leur
résultat est à la fois stable et utile. Aucun exemple n'est choisi après coup sans que sa
règle de sélection soit explicitée.

Phrase proposée :

> We asked a local 27B model to infer player profiles from complete stories, without
> access to edge annotations or BoP results. This tests whether probabilistic structural
> differences become perceptible narrative differences.
