# Phase 5 — Prompt iteration log

> This table documents prompt calibration, not model accuracy. Each new row must use the
> same seven calibration tasks unless the protocol change is explicitly recorded.

| Trial | Run and instrument | Calibration result | Errors or problems observed | Improvement proposed for the next prompt | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `P01` | `LW01_phase5_pilot_v2`; baseline prompts `v1`; Qwen revision `6a9e13bd…`; 4 individual trajectories + 3 A/B pairs | 7/7 valid outputs, 0 quarantined; 31 matches, 11 disagreements and 2 human abstentions over 44 fields; these figures are not accuracy | 14 inadmissible profile-evidence citations: 8 Kai, 3 forced, 1 random and 2 combat references. Qwen is also more affirmative than the human on support and `profile_coherence`. Main label differences: `T0009/risk`, `C003/narrative_distinctness`, `C006/risk shift`. | Add an explicit `eligible_profile_choice_refs` list derived only from transitions labelled `Player choice` or `Player choice: escape from combat`. Require all profile and coherence evidence to come from it. State that mechanical transitions may inform causal continuity, but never profile labels, support or coherence. Retain the blocking post-generation check. | Revise generically and rerun exactly the same seven tasks before freezing the prompt. |
| `P02` | `LW01_phase5_pilot_p02`; allow-list/conservative prompts `v2`; same pinned Qwen revision, parameters, output schemas and seven tasks; input envelope `v1.1` | 5/7 valid, 2 quarantined. On the five valid outputs: 26 concordances and 6 désaccords sur 32 champs, sans abstention humaine ; ce n'est pas une accuracy. Les mêmes cas donnaient 25/7 avec P01. | `T0001` et `C003_AB` citent la même résolution de combat inadmissible, `S030-C01`. Le contrôle bloque donc correctement deux sorties, mais la consigne seule n'assure pas l'obéissance. Les désaccords `clear`/`coherent` passent de quatre à trois sur les cinq cas communs ; le risque de `C006` reste un désaccord interprétatif. | Distinguer génériquement les décisions du joueur des transitions automatiques dans l'histoire rendue elle-même : réserver `[CHOSEN ACTION]` et les références `Cxx` aux choix admissibles, et présenter les autres comme des transitions résolues non choisies. Conserver la liste exhaustive et le contrôle bloquant. | Ne pas geler. Préparer P03 avec les mêmes sept tâches et le même environnement, en ne changeant que ce rendu générique et sa validation. |
| `P03` — frozen | `LW01_phase5_pilot_p03`; mêmes prompts `v2`, révision Qwen, paramètres, schémas de sortie et sept tâches ; rendu des entrées `resolved_transition_render_v1`, enveloppe `v1.2` | 7/7 valides, aucune quarantaine ; 32 concordances, 10 désaccords, 2 abstentions humaines et aucune abstention modèle sur 44 champs ; ce n'est pas une accuracy. Sur les cinq cas valides de P02, 29 champs sur 32 restent inchangés. | Aucune preuve inadmissible. Les différences restantes concernent des seuils ou lectures concurrentes de choix admissibles : trois labels individuels de risque, quatre jugements de support/cohérence, la distinctivité de `C003` et la direction du risque de `C006`. Les justifications sont toutes traçables au texte admissible. | Aucun nouveau changement : poursuivre la calibration risquerait d'ajuster l'instrument aux quatre histoires humaines. Geler les prompts `v2`, le rendu `resolved_transition_render_v1`, l'enveloppe `v1.2`, les schémas de sortie et les validateurs bloquants. | Critères préenregistrés atteints. Construire le paquet final de 26 tâches sans autre modification de calibration. |

## Rules for subsequent rows

1. Change only rules that apply generically to any book; never mention a trajectory,
   paragraph or character from LW01 in the prompt.
2. Keep the model, revision, decoding parameters, schemas and seven calibration inputs
   fixed unless the changed element is explicitly identified in the row.
3. Report JSON validity, quarantine, field concordances/abstentions and objective evidence
   violations separately.
4. Do not call the field comparison accuracy or validation.
5. Freeze the prompt only after the remaining problems have been read in the stories and
   the stopping decision has been recorded before the final run.

The failed `pilot_v1` bundle is excluded from this table because inference never began:
vLLM rejected the unsupported JSON Schema keyword `uniqueItems`. It remains documented as
a technical compatibility incident in `docs/progress_log.md`.
