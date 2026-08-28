# Phase 5 — Prompt iteration log

> This table documents prompt calibration, not model accuracy. Each new row must use the
> same seven calibration tasks unless the protocol change is explicitly recorded.

| Trial | Run and instrument | Calibration result | Errors or problems observed | Improvement proposed for the next prompt | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `P01` | `LW01_phase5_pilot_v2`; baseline prompts `v1`; Qwen revision `6a9e13bd…`; 4 individual trajectories + 3 A/B pairs | 7/7 valid outputs, 0 quarantined; 31 matches, 11 disagreements and 2 human abstentions over 44 fields; these figures are not accuracy | 14 inadmissible profile-evidence citations: 8 Kai, 3 forced, 1 random and 2 combat references. Qwen is also more affirmative than the human on support and `profile_coherence`. Main label differences: `T0009/risk`, `C003/narrative_distinctness`, `C006/risk shift`. | Add an explicit `eligible_profile_choice_refs` list derived only from transitions labelled `Player choice` or `Player choice: escape from combat`. Require all profile and coherence evidence to come from it. State that mechanical transitions may inform causal continuity, but never profile labels, support or coherence. Retain the blocking post-generation check. | Revise generically and rerun exactly the same seven tasks before freezing the prompt. |
| `P02` | `LW01_phase5_pilot_p02`; allow-list/conservative prompts `v2`; same pinned Qwen revision, parameters, output schemas and seven tasks; input envelope `v1.1` | 5/7 valid, 2 quarantined. On the five valid outputs: 26 matches and 6 disagreements over 32 fields, with no human abstentions; this is not accuracy. The same cases produced 25 matches and 7 disagreements in P01. | `T0001` and `C003_AB` cite the same inadmissible combat-resolution reference, `S030-C01`. The validator therefore correctly blocks two outputs, but the instruction alone does not ensure compliance. `clear`/`coherent` disagreements fall from four to three across the five common cases; the `C006` risk direction remains an interpretive disagreement. | Generically distinguish player decisions from automatic transitions in the rendered story itself: reserve `[CHOSEN ACTION]` and `Cxx` references for eligible choices, and present all other transitions as resolved non-player transitions. Retain the exhaustive allow-list and blocking validator. | Do not freeze. Prepare P03 with the same seven tasks and environment, changing only this generic rendering and its validation. |
| `P03` — frozen | `LW01_phase5_pilot_p03`; same prompts `v2`, Qwen revision, parameters, output schemas and seven tasks; input rendering `resolved_transition_render_v1`, envelope `v1.2` | 7/7 valid, 0 quarantined; 32 matches, 10 disagreements, 2 human abstentions and 0 model abstentions over 44 fields; this is not accuracy. Across the five valid P02 cases, 29 of 32 fields remain unchanged. | No inadmissible evidence. The remaining differences concern thresholds or competing readings of eligible choices: three individual risk labels, four support/coherence judgments, `C003` narrative distinctness and the `C006` risk direction. Every justification is traceable to eligible text. | Make no further change: continuing calibration would risk fitting the instrument to the four human-annotated stories. Freeze prompts `v2`, rendering `resolved_transition_render_v1`, envelope `v1.2`, the output schemas and blocking validators. | Pre-registered criteria met. Build the final 26-task bundle without further calibration changes. |

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
