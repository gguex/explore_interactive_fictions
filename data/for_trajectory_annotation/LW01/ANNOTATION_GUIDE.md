# Guide d'annotation humaine — Phase 5, LW01

## Fichiers à utiliser

- Lire les histoires dans `TRAJECTORIES_FOR_ANNOTATION.md`, l'annexe mise en page pour
  la calibration humaine. Le fichier JSONL complet utilisé par Qwen reste disponible dans
  `../../processed/phase5/LW01/trajectories.jsonl`.
- Reporter les annotations dans `human_trajectory_annotations.jsonl`.
- Reporter les comparaisons dans `human_pairwise_annotations.jsonl`.
- Ne pas ouvrir `trajectory_private_metadata.jsonl` avant d'avoir terminé : il contient
  les profils générateurs et les issues cachées.

Le premier canevas contient exactement les quatre trajectoires à annoter individuellement :
`T0001`, `T0004`, `T0009` et `T0014`. Le second contient exactement les trois
comparaisons à annoter :

| Comparaison | Histoire A | Histoire B |
| :--- | :--- | :--- |
| `C002` | `T0004` | `T0006` |
| `C003` | `T0007` | `T0009` |
| `C006` | `T0012` | `T0014` |

Les axes contrôlés, profils générateurs et issues ne sont volontairement pas indiqués ici.
N'essayez pas de les retrouver dans d'autres fichiers avant la fin de l'annotation. Il
n'existe pas de jeu humain de validation dans cette itération : ces quatre histoires et
trois paires servent à calibrer le prompt lisible avant son gel.

`example_T0001_annotation_nonhuman.json` montre un remplissage possible fondé uniquement
sur le texte. Il s'agit d'un exemple produit par un assistant, **pas d'une annotation
humaine de référence** : il ne doit pas être copié automatiquement dans le fichier
canonique ni utilisé pour évaluer Qwen.

## Procédure

1. Lire l'histoire entière avant d'attribuer un label.
2. Évaluer le comportement global, pas une action isolée.
3. Utiliser seulement les décisions marquées `Player choice` ou
   `Player choice: escape from combat` comme preuves du profil.
4. Ne pas utiliser comme preuves les combats imposés, résultats aléatoires, transitions
   forcées, disponibilités Kai ou conditions d'inventaire.
5. Citer les références exactes des choix, par exemple `S012-C02`.
6. Une fois la ligne terminée, renseigner `annotator_id` et remplacer
   `"status":"pending"` par `"status":"complete"`.
7. Conserver une ligne JSON valide par trajectoire et ne pas modifier `trajectory_id` ou
   `annotation_role`.

## Profil perçu

Pour chacun des trois axes, remplir `label`, `support`, `justification`, les preuves et les
contre-preuves.

| Axe | Labels autorisés | Définition des pôles |
| :--- | :--- | :--- |
| `risk` | `cautious`, `neutral`, `reckless`, `unclear` | Évitement répété des dangers / engagement répété dans des dangers évitables. |
| `morality` | `selfish`, `neutral`, `noble`, `unclear` | Priorité au gain ou à la sécurité personnelle / aide, protection ou sacrifice pour autrui. |
| `action` | `physical`, `neutral`, `tactical`, `unclear` | Force et affrontement direct / observation, préparation, diversion ou évitement stratégique. |

`support` accepte :

- `clear` : plusieurs décisions convergentes et peu de contre-preuves ;
- `mixed` : preuves réelles mais orientation concurrencée ou irrégulière ;
- `insufficient` : trop peu de décisions pertinentes.

Utiliser `neutral` lorsqu'il existe assez de décisions, mais aucune orientation dominante.
Utiliser `unclear` lorsque les preuves ne permettent pas de choisir un label. Citer au
maximum trois `supporting_choice_refs` et deux `counterevidence_choice_refs` par axe.

## Continuité causale

Labels autorisés pour `causal_continuity` :

- `continuous` : aucune rupture vérifiable trouvée ;
- `minor_gap` : liaison implicite ou ambiguë, sans rupture globale ;
- `broken` : dépendance sans cause ou contradiction explicite affectant l'enchaînement ;
- `unclear` : le texte ne permet pas de trancher.

Une ellipse ou une transition rapide ne suffit pas. Pour `minor_gap` ou `broken`, citer au
moins les deux `evidence_paragraph_ids` concernés. Pour `continuous`, la liste peut rester
vide.

## Cohérence interne du profil

Labels autorisés pour `profile_coherence` :

- `coherent` : comportement global stable, avec peu d'exceptions contextuelles ;
- `mixed` : orientations concurrentes mais profil encore partiellement lisible ;
- `incoherent` : contradictions répétées empêchant un profil stable ;
- `insufficient_evidence` : trop peu de décisions pertinentes.

Ce champ mesure la cohérence interne de l'histoire lue, pas l'accord avec le profil caché.
La justification doit rester courte et les références doivent appartenir à la trajectoire.

## Règles d'interprétation

- Ne pas deviner le profil générateur.
- Ne pas juger la qualité littéraire, la tension, l'équité de l'issue ou l'adéquation entre
  choix et conséquences.
- Ne pas traiter l'issue finale comme une preuve du comportement du joueur.
- Préférer `unclear` ou `insufficient_evidence` à une inférence non étayée.

## Annotation des comparaisons pairwise

### Procédure

1. Lire entièrement l'histoire A, puis l'histoire B, avant de remplir la comparaison.
2. Former une impression globale des deux parcours. Ne pas compter les paragraphes
   communs : les distances structurelles sont calculées séparément.
3. Évaluer `narrative_distinctness`, puis les trois axes de
   `perceived_profile_shift`, et les expliquer brièvement dans
   `profile_shift_justification`. Ne pas chercher quel axe était intentionnellement
   contrôlé.
4. Pour les axes, utiliser uniquement les décisions marquées `Player choice` ou
   `Player choice: escape from combat` comme preuves.
5. Ne pas utiliser les combats imposés, transitions forcées, mécanismes aléatoires,
   conditions Kai, inventaire ou issue finale comme preuves d'un profil.
6. Citer au plus cinq références pertinentes par histoire dans `evidence_story_a` et
   `evidence_story_b`.
7. Renseigner `annotator_id`, passer `status` à `complete` et conserver les identifiants et
   l'ordre A/B du canevas.

L'humain annote un seul ordre. L'inversion B/A sera réalisée séparément avec Qwen pour
détecter un éventuel biais de position.

### Différence narrative globale

`narrative_distinctness.label` accepte :

- `low` : même impression globale de parcours et de protagoniste ;
- `medium` : différence perceptible, mais sur un fond narratif largement partagé ;
- `high` : impression claire de deux manières différentes de vivre l'aventure ;
- `unclear` : le texte ne permet pas de comparer de façon suffisamment étayée.

La justification porte sur l'impression produite par les histoires entières, pas sur leur
qualité littéraire. Une différence de longueur ou d'issue ne suffit pas à elle seule. Pour
ce champ, une référence d'étape telle que `S012` est autorisée.

### Déplacement du profil perçu

Remplir les trois champs, même si deux histoires paraissent similaires sur certains axes :

| Champ | Labels autorisés |
| :--- | :--- |
| `risk` | `A_more_cautious`, `similar`, `A_more_reckless`, `unclear` |
| `morality` | `A_more_selfish`, `similar`, `A_more_noble`, `unclear` |
| `action` | `A_more_physical`, `similar`, `A_more_tactical`, `unclear` |

- `similar` signifie qu'il existe assez de décisions comparables, sans direction globale
  stable entre A et B ;
- `unclear` signifie que les preuves sont insuffisantes ou trop peu comparables ;
- `A_more_*` est toujours interprété relativement à B, jamais comme une propriété absolue
  de A.

Pour ces champs, citer de préférence des choix précis tels que `S012-C02`. Les références
de A vont uniquement dans `evidence_story_a`, celles de B dans `evidence_story_b`. La
justification de `narrative_distinctness` concerne la différence globale ;
`profile_shift_justification` explique brièvement comment les références citées soutiennent
les déplacements de profil retenus.

### Exemple abstrait

Si A évite plusieurs dangers optionnels tandis que B les affronte régulièrement, `risk`
peut valoir `A_more_cautious`. Si les deux histoires contiennent trop peu de décisions
morales comparables, `morality` vaut `unclear`, et non `similar`.
