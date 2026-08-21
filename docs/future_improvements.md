# Améliorations et extensions futures

> **Statut au 20.08.2026 : chantier reporté.** Ce document conserve les limites
> identifiées et les évolutions souhaitables. Il ne modifie ni le schéma courant de la
> phase 1, ni la recette nécessaire pour terminer le pré-graphe de LW01.

## 1. Objectif

Le pipeline actuel suffit pour poursuivre l'étude de LW01, mais une partie de
l'interprétation linguistique est effectuée tardivement par
`scripts/2.1_prepare_pregraph.py`. Cette approche repose sur des expressions régulières
anglaises et risque d'augmenter fortement la supervision lors du passage à LW02 ou à un
autre corpus.

L'évolution proposée repose sur une frontière plus nette :

- la **phase 1** décrit sous forme structurée ce que dit le texte ;
- la **phase 2.1** traduit cette description en règles du pré-graphe ;
- la **phase 3** combine un profil comportemental de schéma unique et une configuration
  expérimentale fixe pour attribuer des valeurs aux règles symboliques.

Le LLM ne doit donc produire ni probabilités finales, ni `weight_expression`, ni matrice
$W$. Ces opérations restent déterministes et auditables.

## 2. Limites à conserver en mémoire

### 2.1 Type de transition trop exclusif

Le champ actuel `transition_type` impose une seule catégorie parmi `forced`,
`explicit_choice`, `stochastic`, `conditional` et `complex`. Or plusieurs dimensions
peuvent coexister.

Par exemple, « If you have 10 Gold Crowns and wish to pay him » exprime à la fois :

- une condition de disponibilité : posséder au moins 10 Gold Crowns ;
- une décision du joueur : accepter ou refuser de payer.

Le schéma actuel classe cette transition comme `conditional` et interdit alors de lui
attribuer les axes sémantiques réservés aux `explicit_choice`. La conversion automatique
peut ainsi confondre disponibilité et décision.

### 2.2 Nouvelle interprétation linguistique en phase 2.1

La phase 2.1 redéduit actuellement depuis `realisation_value` :

- le nom d'une discipline Kai ;
- la possession ou l'absence d'un objet ;
- un montant minimal de Gold Crowns ;
- un seuil d'Endurance ;
- la polarité positive ou négative d'une condition ;
- les valeurs couvertes par une branche de la Random Number Table ;
- certains enchaînements de tirages et cas de combat à partir de mots présents dans les
  `warnings`.

Ces faits appartiennent à l'extraction sémantique. La phase 2.1 devrait les recevoir sous
forme structurée et se limiter à leur compilation.

### 2.3 `warnings` utilisé comme interface implicite

Un avertissement libre doit expliquer une ambiguïté à un humain. Il ne devrait pas être
interprété par le code comme une instruction. Les dépendances entre tirages, les morts
implicites et les mécaniques inhabituelles doivent disposer de champs dédiés et de codes
fermés.

### 2.4 Combats insuffisamment caractérisés

La présence d'un ennemi permet de reconnaître un combat, mais ne distingue pas toujours :

- la continuation après victoire ;
- une fuite avant ou pendant le combat ;
- un choix effectué après la victoire ;
- une issue dépendant du nombre de rounds ou des dégâts subis ;
- un modificateur de combat lié à un objet ou à une discipline.

Ces rôles doivent être extraits avant que la phase 2.1 choisisse une formule ou demande
une supervision.

## 3. Processus cible

### Étape A — Parsing déterministe du corpus

Le parseur HTML conserve les paragraphes, les balises `<choice>`, les cibles explicites,
les marqueurs de fin, les blocs de combat et les références de provenance. Il ne demande
pas au LLM de retrouver une information déjà encodée dans le HTML.

### Étape B — Extraction sémantique structurée par le petit LLM

Le LLM reçoit le paragraphe complet avec ses choix balisés. Pour chaque transition, il
sépare les dimensions suivantes :

- agentivité ;
- conditions de disponibilité ;
- rôle dans un tirage aléatoire ;
- rôle et temporalité dans un combat ;
- effet éventuel sur l'état ;
- issue implicite ;
- axes sémantiques si une décision du joueur existe.

Une sortie structurée contrainte par un schéma remplace autant que possible le texte
libre. `edge_text` et les formulations originales restent conservés pour audit.

### Étape C — Contrôle de la phase 1

Le contrôle vérifie au minimum :

- une représentation pour chaque balise `<choice>` ;
- des identifiants valides ;
- la conformité au schéma et aux énumérations ;
- la cohérence entre agentivité et annotations sémantiques ;
- la cohérence des groupes de conditions et de tirages ;
- la présence d'un motif de revue pour toute ambiguïté déclarée.

### Étape D — Compilation déterministe par la phase 2.1

À partir des champs structurés, la phase 2.1 :

- groupe les transitions par source ;
- calcule les probabilités exactes des tirages simples ;
- construit `kai_available(...)`, `condition_available(...)`, `combat_win(...)` et les
  parts de choix ;
- ajoute les issues implicites vers `Death` ou `Win` ;
- dirige les compositions non prises en charge vers la supervision ;
- garantit la traçabilité jusqu'aux lignes de phase 1.

## 4. Fichiers de sortie proposés pour la phase 1

Les noms ci-dessous sont indicatifs. Toute migration devra introduire une version de
schéma explicite et conserver les sorties actuelles le temps de comparer les deux
pipelines.

### 4.1 `<BOOK_ID>_nodes.csv`

| Champ | Contenu attendu |
| :--- | :--- |
| `node_id` | Identifiant stable du paragraphe. |
| `text_content` | Texte narratif du paragraphe, hors balises de choix si cette convention est conservée. |
| `outcome` | `none`, `death` ou `win`. Ne pas utiliser `potential_death` comme issue finale. |
| `enemies_json` | Liste structurée `{name, combat_skill, endurance}` extraite des blocs de combat. |
| `node_effects_json` | Effets certains du paragraphe : Endurance, objets, monnaie, repas ou équipement. |
| `special_mechanics_json` | Mécaniques qui ne correspondent pas aux catégories ordinaires. |
| `image_refs` | Références des illustrations liées au paragraphe. |
| `source_ref` | Fichier HTML ou autre provenance primaire. |
| `warnings` | Ambiguïtés résiduelles destinées à la revue humaine. |

`node_effects_json` peut contenir une liste d'objets de la forme :

```json
[
  {
    "kind": "endurance_change",
    "operator": "add",
    "value": -2,
    "timing": "on_entry"
  }
]
```

La collecte de ces effets ne signifie pas que L3 sera simulé. Elle préserve seulement
l'information pour une extension future ou une analyse de sensibilité.

### 4.2 `<BOOK_ID>_e_edges.csv`

| Champ | Contenu attendu |
| :--- | :--- |
| `source_id`, `target_id` | Paragraphes source et cible explicite. |
| `edge_text` | Texte brut complet de la balise `<choice>`. |
| `agency` | `forced` ou `player_choice`, indépendamment des conditions. |
| `timing` | `ordinary`, `precombat`, `during_combat` ou `postcombat`. |
| `outcome_role` | `continuation`, `combat_win`, `combat_escape`, `death`, `win` ou `other`. |
| `conditions_json` | Liste structurée des conditions qui rendent la transition disponible. |
| `condition_logic` | `all`, `any` ou vide s'il n'existe aucune condition. |
| `random_event_id` | Identifiant local du tirage auquel appartient la branche. |
| `random_stage` | Ordre du tirage dans une séquence, à partir de 1. |
| `random_values_json` | Valeurs exactes de la RNT conduisant à cette branche, par exemple `[0,1,2,3,4]`. |
| `depends_on_event_id` | Événement antérieur qui doit avoir eu lieu ou échoué. |
| `state_effects_json` | Effets propres à la transition : perte d'Endurance, paiement, objet consommé, etc. |
| `implicit_outcome` | `death`, `win` ou vide lorsqu'une issue non ciblée est décrite dans la balise. |
| `semantic_risk` | `cautious`, `neutral` ou `reckless` si `agency=player_choice`. |
| `semantic_morality` | `selfish`, `neutral` ou `noble` si `agency=player_choice`. |
| `semantic_action` | `physical`, `neutral` ou `tactical` si `agency=player_choice`. |
| `needs_review` | Booléen signalant une extraction que le LLM ne peut résoudre proprement. |
| `review_reason_code` | Code fermé expliquant la revue. |
| `warnings` | Explication libre facultative, jamais interprétée automatiquement. |
| `source_ref` | Provenance du paragraphe et version du corpus. |

Une condition élémentaire dans `conditions_json` suit la forme :

```json
{
  "kind": "kai_discipline | item | currency | endurance | combat_outcome | other",
  "operator": "has | not_has | eq | neq | gte | gt | lte | lt | win | lose",
  "value": "valeur textuelle ou numérique",
  "raw_text": "fragment exact qui exprime la condition"
}
```

Exemple pour une transition conditionnelle qui reste un choix :

```json
{
  "source_id": "12",
  "target_id": "262",
  "agency": "player_choice",
  "timing": "ordinary",
  "outcome_role": "continuation",
  "conditions_json": [
    {
      "kind": "currency",
      "operator": "gte",
      "value": 10,
      "raw_text": "If you have 10 Gold Crowns"
    }
  ],
  "condition_logic": "all"
}
```

### 4.3 `<BOOK_ID>_extraction_manifest.json`

La provenance de l'extraction ne doit pas être répétée dans chaque ligne. Un manifeste
par exécution contient :

| Champ | Contenu attendu |
| :--- | :--- |
| `schema_version` | Version du schéma structuré. |
| `book_id` | Identifiant du corpus. |
| `source_corpus` | Chemin ou URI de la source. |
| `source_hash` | Empreinte du corpus effectivement traité. |
| `model_id` | Modèle et révision utilisés. |
| `prompt_ref`, `prompt_hash` | Prompt versionné et son empreinte. |
| `decoding_parameters` | Température, graine et paramètres utiles à la reproductibilité. |
| `started_at`, `completed_at` | Horodatage de l'exécution. |
| `node_count`, `edge_count`, `review_count` | Volumes produits. |
| `calibration_ref` | Version du gold standard ou du rapport d'évaluation associé. |

### 4.4 `<BOOK_ID>_extraction_review.csv`

Cette file concerne les ambiguïtés de l'extraction LLM. Elle reste distincte de la file
de supervision de phase 2, qui concerne l'encodage dans le pré-graphe.

| Champ | Contenu attendu |
| :--- | :--- |
| `source_id`, `target_id` | Transition concernée. |
| `reason_code` | Cause normalisée de la revue. |
| `edge_text` | Texte à relire. |
| `structured_payload_json` | Proposition structurée du LLM. |
| `status` | `pending`, `accepted`, `corrected` ou `rejected`. |
| `resolution_note` | Justification humaine. |

## 5. Répartition des responsabilités

| Tâche | Parsing | Petit LLM | Phase 2.1 |
| :--- | :---: | :---: | :---: |
| Repérer les balises et cibles explicites | Oui | Non | Non |
| Conserver le texte et la provenance | Oui | Non | Non |
| Identifier agentivité, conditions et rôles mécaniques | Non | Oui | Non |
| Signaler une ambiguïté linguistique | Non | Oui | Non |
| Calculer une probabilité depuis les valeurs RNT | Non | Non | Oui |
| Choisir une formule symbolique du pré-graphe | Non | Non | Oui |
| Ajouter `Death`/`Win` et les arêtes générées | Non | Non | Oui |
| Déterminer les paramètres propres à un profil | Non | Non | Phase 3 |

## 6. Priorités si le chantier est rouvert

### Priorité 1 — Corriger la perte d'information

1. Séparer `agency` des conditions.
2. Remplacer la condition textuelle unique par `conditions_json` et
   `condition_logic`.
3. Autoriser les axes sémantiques sur tout `player_choice`, même conditionnel.
4. Cesser d'utiliser le contenu libre de `warnings` dans la logique de production.

### Priorité 2 — Réduire la supervision récurrente

1. Identifier victoire, fuite et choix post-combat.
2. Structurer les tirages successifs et leurs dépendances.
3. Signaler les morts implicites et les effets portés par une transition.

### Priorité 3 — Préparer la généralisation

1. Versionner le schéma et le manifeste d'extraction.
2. Tester le même contrat sur LW01 et LW02.
3. Séparer les catégories générales des vocabulaires propres à *Lone Wolf*.
4. Évaluer ensuite un corpus extérieur à la série.

## 7. Migration et validation

Cette évolution ne doit pas remplacer directement le pipeline validé. La migration
proposée est :

1. figer les sorties et résultats actuels de LW01 ;
2. créer un schéma `v2` parallèle ;
3. enrichir le gold standard avec les nouveaux champs ;
4. recalibrer le prompt du petit LLM ;
5. exécuter les deux schémas sur LW01 ;
6. comparer couverture, erreurs sémantiques et volume de supervision ;
7. tester le schéma `v2` sur LW02 ;
8. migrer 2.1 seulement après validation des contrôles de non-régression.

Les critères minimaux d'acceptation sont :

- toutes les balises `<choice>` sont couvertes exactement une fois ;
- chaque choix conditionnel conserve à la fois son agentivité et sa disponibilité ;
- les plages RNT simples sont reconstruites sans interpréter du texte libre en phase 2 ;
- les warnings ne pilotent aucune conversion automatique ;
- toutes les lignes automatiques gardent une provenance ;
- la file de supervision est expliquée par des codes stables ;
- la sortie LW01 reste topologiquement compatible avec le pré-graphe validé.

## 8. Axes d'analyse reportés après l'itération de présentation

La phase 3 actuelle ne fait varier que `risk`, `morality` et `action`. Les dimensions
suivantes sont volontairement fixées afin de garder 27 profils homogènes et une méthode
présentable en 20 minutes :

- disponibilité réelle des disciplines Kai et comparaison des configurations de cinq
  disciplines parmi dix ;
- effet d'une discipline particulière sur la réussite, les flux et les trajectoires ;
- variation de la capacité de combat propre au joueur et utilisation dans le graphe de
  probabilités $v(i)$ propres à chaque ennemi ; la table officielle est désormais
  utilisée uniquement pour calibrer le scalaire global de LW01 ;
- propension individuelle à prendre la fuite et survie jusqu'au round où elle devient
  possible ;
- disponibilité propre à chaque objet, seuil de monnaie ou seuil d'Endurance ;
- dépendance de ces conditions au chemin déjà parcouru ;
- interactions entre les trois axes comportementaux et les compétences ou ressources ;
- analyses de sensibilité de `kai_availability`, `combat_win_probability`,
  `escape_probability` et `has_condition` ;
- comparaison entre une probabilité globale et des probabilités estimées par paragraphe
  ou par mécanique ;
- suivi exact des dégâts hors combat, de l'inventaire acquis, des soins et des rounds
  obligatoires avant une fuite dans la calibration ;
- expansion L3 de l'état `(paragraphe, Endurance, inventaire, monnaie, équipement)` ;
- robustesse des résultats sur LW02, d'autres volumes et d'autres séries.

Ces extensions ne devront pas modifier le schéma du profil comportemental. Elles seront
portées par des configurations expérimentales séparées ou, pour L3, par un autre niveau
de modèle.

## 9. Décisions encore ouvertes pour le pipeline étendu

Avant une refonte de l'extraction ou du modèle, il faudra encore décider :

1. si une ligne de phase 1 représente toujours une balise `<choice>` ou une issue logique
   élémentaire ;
2. quels effets d'état conserver comme métadonnées sans introduire une simulation L3 ;
3. quelles catégories sont propres à *Lone Wolf* et lesquelles appartiennent au modèle
   général des fictions interactives ;
4. si une future étude doit remplacer le partage égal entre plusieurs continuations
   `survive` par des parts déduites des règles détaillées du combat.

## 10. Éléments à ne pas déléguer au LLM

Même dans le processus étendu, le petit LLM ne doit pas :

- inventer une cible absente du texte ;
- calculer ou normaliser les poids du pré-graphe ;
- choisir une probabilité de victoire ou de fuite ;
- produire directement une expression exécutable ;
- décider des paramètres d'un profil ;
- simuler l'inventaire ou l'Endurance au fil d'un parcours ;
- corriger silencieusement une structure ambiguë.

## 11. Quand rouvrir ce chantier

Cette refonte devient prioritaire si au moins une des situations suivantes apparaît :

- la file de supervision de LW02 est dominée par des formulations récurrentes que le LLM
  pourrait structurer ;
- des choix conditionnels importants perdent leur agentivité ;
- les expressions régulières de 2.1 doivent être étendues livre par livre ;
- les warnings libres deviennent nécessaires au fonctionnement du pipeline ;
- un corpus non anglophone ou extérieur à *Lone Wolf* doit être traité.

D'ici là, le pipeline actuel reste la référence opérationnelle pour terminer LW01.

## 12. Observations à compléter lors des prochains corpus

Les extensions doivent être motivées par des cas observés plutôt que par une liste
théorique toujours plus large. Après chaque nouvelle extraction, consigner ici ou dans
un rapport lié :

| Date | Corpus et schéma | Arêtes extraites | Sources automatiques | Sources supervisées | Motifs récurrents | Décision prise |
| :--- | :--- | ---: | ---: | ---: | :--- | :--- |
| À compléter | LW02 |  |  |  |  |  |

Cette mesure permettra de distinguer une formulation isolée, qui peut rester supervisée,
d'une mécanique récurrente qui justifie une évolution du schéma ou du convertisseur.
