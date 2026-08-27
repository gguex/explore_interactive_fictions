# Phase 5 pilot — Human/Qwen calibration comparison

> Descriptive prompt calibration only. This is neither accuracy nor an
> out-of-sample validation, and disagreements are not automatically errors.

## Summary

| Status | Count |
| :--- | ---: |
| `match` | 31 |
| `disagreement` | 11 |
| `human_abstention` | 2 |
| `model_abstention` | 0 |

## Evidence-rule check

- Human violations: 0
- Qwen violations: 14

| ID | Location | Reference | Excluded transition type |
| :--- | :--- | :--- | :--- |
| `T0001` | `perceived_profile.risk.supporting_choice_refs` | `S001-C01` | Kai availability or mechanical route |
| `T0001` | `perceived_profile.morality.counterevidence_choice_refs` | `S030-C01` | Combat resolution |
| `T0001` | `perceived_profile.action.supporting_choice_refs` | `S001-C01` | Kai availability or mechanical route |
| `T0001` | `perceived_profile.action.supporting_choice_refs` | `S016-C01` | Kai availability or mechanical route |
| `T0001` | `profile_coherence.supporting_choice_refs` | `S001-C01` | Kai availability or mechanical route |
| `T0001` | `profile_coherence.supporting_choice_refs` | `S016-C01` | Kai availability or mechanical route |
| `T0004` | `perceived_profile.action.supporting_choice_refs` | `S001-C01` | Kai availability or mechanical route |
| `T0004` | `profile_coherence.supporting_choice_refs` | `S001-C01` | Kai availability or mechanical route |
| `T0009` | `perceived_profile.risk.supporting_choice_refs` | `S003-C01` | Forced transition |
| `T0009` | `perceived_profile.risk.supporting_choice_refs` | `S038-C02` | Random or mechanical resolution |
| `T0009` | `perceived_profile.risk.counterevidence_choice_refs` | `S005-C01` | Forced transition |
| `T0009` | `perceived_profile.action.counterevidence_choice_refs` | `S003-C01` | Forced transition |
| `T0014` | `perceived_profile.action.supporting_choice_refs` | `S001-C01` | Kai availability or mechanical route |
| `C003` | `evidence_story_b` | `S030-C01` | Combat resolution |

## All compared fields

| Task | ID | Field | Human | Qwen | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| individual | `T0001` | `perceived_profile.risk.label` | `cautious` | `cautious` | `match` |
| individual | `T0001` | `perceived_profile.risk.support` | `mixed` | `clear` | `disagreement` |
| individual | `T0001` | `perceived_profile.morality.label` | `unclear` | `noble` | `human_abstention` |
| individual | `T0001` | `perceived_profile.morality.support` | `insufficient` | `mixed` | `human_abstention` |
| individual | `T0001` | `perceived_profile.action.label` | `tactical` | `tactical` | `match` |
| individual | `T0001` | `perceived_profile.action.support` | `mixed` | `clear` | `disagreement` |
| individual | `T0001` | `causal_continuity.label` | `continuous` | `continuous` | `match` |
| individual | `T0001` | `profile_coherence.label` | `mixed` | `coherent` | `disagreement` |
| individual | `T0004` | `perceived_profile.risk.label` | `cautious` | `cautious` | `match` |
| individual | `T0004` | `perceived_profile.risk.support` | `clear` | `clear` | `match` |
| individual | `T0004` | `perceived_profile.morality.label` | `selfish` | `selfish` | `match` |
| individual | `T0004` | `perceived_profile.morality.support` | `clear` | `mixed` | `disagreement` |
| individual | `T0004` | `perceived_profile.action.label` | `tactical` | `tactical` | `match` |
| individual | `T0004` | `perceived_profile.action.support` | `clear` | `clear` | `match` |
| individual | `T0004` | `causal_continuity.label` | `continuous` | `continuous` | `match` |
| individual | `T0004` | `profile_coherence.label` | `coherent` | `coherent` | `match` |
| individual | `T0009` | `perceived_profile.risk.label` | `reckless` | `neutral` | `disagreement` |
| individual | `T0009` | `perceived_profile.risk.support` | `mixed` | `mixed` | `match` |
| individual | `T0009` | `perceived_profile.morality.label` | `noble` | `noble` | `match` |
| individual | `T0009` | `perceived_profile.morality.support` | `clear` | `clear` | `match` |
| individual | `T0009` | `perceived_profile.action.label` | `physical` | `physical` | `match` |
| individual | `T0009` | `perceived_profile.action.support` | `mixed` | `clear` | `disagreement` |
| individual | `T0009` | `causal_continuity.label` | `continuous` | `continuous` | `match` |
| individual | `T0009` | `profile_coherence.label` | `mixed` | `coherent` | `disagreement` |
| individual | `T0014` | `perceived_profile.risk.label` | `cautious` | `cautious` | `match` |
| individual | `T0014` | `perceived_profile.risk.support` | `mixed` | `clear` | `disagreement` |
| individual | `T0014` | `perceived_profile.morality.label` | `selfish` | `selfish` | `match` |
| individual | `T0014` | `perceived_profile.morality.support` | `mixed` | `mixed` | `match` |
| individual | `T0014` | `perceived_profile.action.label` | `tactical` | `tactical` | `match` |
| individual | `T0014` | `perceived_profile.action.support` | `clear` | `clear` | `match` |
| individual | `T0014` | `causal_continuity.label` | `continuous` | `continuous` | `match` |
| individual | `T0014` | `profile_coherence.label` | `mixed` | `coherent` | `disagreement` |
| pairwise | `C002` | `narrative_distinctness.label` | `high` | `high` | `match` |
| pairwise | `C002` | `perceived_profile_shift.risk` | `A_more_cautious` | `A_more_cautious` | `match` |
| pairwise | `C002` | `perceived_profile_shift.morality` | `A_more_selfish` | `A_more_selfish` | `match` |
| pairwise | `C002` | `perceived_profile_shift.action` | `A_more_tactical` | `A_more_tactical` | `match` |
| pairwise | `C003` | `narrative_distinctness.label` | `high` | `medium` | `disagreement` |
| pairwise | `C003` | `perceived_profile_shift.risk` | `A_more_cautious` | `A_more_cautious` | `match` |
| pairwise | `C003` | `perceived_profile_shift.morality` | `A_more_selfish` | `A_more_selfish` | `match` |
| pairwise | `C003` | `perceived_profile_shift.action` | `A_more_tactical` | `A_more_tactical` | `match` |
| pairwise | `C006` | `narrative_distinctness.label` | `medium` | `medium` | `match` |
| pairwise | `C006` | `perceived_profile_shift.risk` | `A_more_cautious` | `similar` | `disagreement` |
| pairwise | `C006` | `perceived_profile_shift.morality` | `A_more_selfish` | `A_more_selfish` | `match` |
| pairwise | `C006` | `perceived_profile_shift.action` | `A_more_physical` | `A_more_physical` | `match` |

## Fields requiring textual review

### T0001 — perceived_profile.risk.support

- Human: `mixed` — evidence `{"counterevidence":["S018-C02","S029-C03"],"supporting":["S020-C01","S026-C01","S035-C02"]}`
- Qwen: `clear` — evidence `{"counterevidence":["S018-C02","S029-C03"],"supporting":["S001-C01","S026-C01","S035-C02"]}`
- Human justification: Avoidable danger is repeatedly sidestepped through cover, waiting, evasion, and bypassing nearby conflict. This cautious tendency is substantial but not uniform, because the trajectory also chooses a direct charge through Doomwolves and prepares to fight suspicious soldiers.
- Qwen justification: The player repeatedly chooses paths that minimize exposure to danger or utilize skills to avoid conflict. Evidence includes using Sixth Sense to avoid tracked paths (S001-C01), hiding from a Kraan (S003-C01), choosing the safer path after tracking reveals a bear (S005-C01), hiding from Doomwolves (S026-C01), and evading a fight with a madman (S035-C02). Counterevidence exists in the decision to charge Doomwolves (S018-C02) and fight bandits (S029-C03), but these are often reactive or forced by circumstance, whereas the avoidance patterns are consistent proactive choices.

### T0001 — perceived_profile.morality.label

- Human: `unclear` — evidence `{"counterevidence":["S010-C02"],"supporting":["S011-C01"]}`
- Qwen: `noble` — evidence `{"counterevidence":["S010-C02","S030-C01"],"supporting":["S006-C01","S011-C01"]}`
- Human justification: The clearest moral evidence is confined to the wagon episode: the player first runs for personal cover, then returns to defend the children. The reversal leaves too little repeated evidence elsewhere to support a stable moral orientation.
- Qwen justification: The player shows a tendency to help others, such as approaching refugees to reassure them (S006-C01) and returning to defend children after initially fleeing (S011-C01). However, this is contradicted by the initial choice to flee from the children in danger (S010-C02) and the decision to kill three bandits rather than surrender or evade (S030-C01), which prioritizes self-preservation and resource gain (looting bodies) over mercy or non-violence. The profile is mixed because the noble acts are significant but not exclusive.

### T0001 — perceived_profile.morality.support

- Human: `insufficient` — evidence `{"counterevidence":["S010-C02"],"supporting":["S011-C01"]}`
- Qwen: `mixed` — evidence `{"counterevidence":["S010-C02","S030-C01"],"supporting":["S006-C01","S011-C01"]}`
- Human justification: The clearest moral evidence is confined to the wagon episode: the player first runs for personal cover, then returns to defend the children. The reversal leaves too little repeated evidence elsewhere to support a stable moral orientation.
- Qwen justification: The player shows a tendency to help others, such as approaching refugees to reassure them (S006-C01) and returning to defend children after initially fleeing (S011-C01). However, this is contradicted by the initial choice to flee from the children in danger (S010-C02) and the decision to kill three bandits rather than surrender or evade (S030-C01), which prioritizes self-preservation and resource gain (looting bodies) over mercy or non-violence. The profile is mixed because the noble acts are significant but not exclusive.

### T0001 — perceived_profile.action.support

- Human: `mixed` — evidence `{"counterevidence":["S018-C02","S029-C03"],"supporting":["S020-C01","S026-C01","S035-C02"]}`
- Qwen: `clear` — evidence `{"counterevidence":["S029-C03","S018-C02"],"supporting":["S001-C01","S016-C01","S026-C01"]}`
- Human justification: The trajectory often favors cover, waiting, avoidance, and disengagement rather than direct confrontation. Several direct-risk choices recur, however, so the tactical orientation is noticeable without being fully consistent.
- Qwen justification: The player consistently prefers observation, concealment, and strategic movement over direct confrontation. Key evidence includes using Sixth Sense (S001-C01), Tracking (S004-C01), Camouflage (S016-C01), hiding from enemies (S003-C01, S026-C01), and evading fights (S035-C02). Even when combat occurs, it is often a result of being forced into it or a calculated risk (charging to break through), but the dominant pattern is tactical avoidance and preparation.

### T0001 — profile_coherence.label

- Human: `mixed` — evidence `{"counterevidence":["S018-C02","S029-C03"],"supporting":["S020-C01","S026-C01","S035-C02"]}`
- Qwen: `coherent` — evidence `{"counterevidence":["S010-C02","S029-C03"],"supporting":["S001-C01","S016-C01","S011-C01"]}`
- Human justification: A cautious, tactical tendency is readable across many choices, but direct confrontation recurs and the wagon sequence reverses the moral direction immediately.
- Qwen justification: The decisions form a stable profile of a cautious, tactical player who is generally noble but pragmatic. The few instances of direct action (fighting bandits, charging wolves) do not contradict the overall pattern of seeking safety and using skills to avoid danger; rather, they represent necessary actions when avoidance is no longer viable or when the player chooses to take a calculated risk. The moral ambiguity (fleeing then returning) is a common narrative arc for a hero, maintaining coherence.

### T0004 — perceived_profile.morality.support

- Human: `clear` — evidence `{"counterevidence":[],"supporting":["S004-C04","S027-C02"]}`
- Qwen: `mixed` — evidence `{"counterevidence":["S010-C01"],"supporting":["S004-C04","S027-C02"]}`
- Human justification: When another person's danger is explicit, the trajectory twice prioritizes personal survival or the mission: it abandons the threatened wizard and later runs rather than defend the fallen Prince. No comparably clear prosocial player choice offsets these decisions.
- Qwen justification: The player explicitly prioritizes their mission and personal survival over helping others in distress. They abandon a wizard under attack (S004-C04) and flee a wounded Prince (S027-C02). However, they also investigate a potentially dangerous hut area after detecting tracks (S010-C01), which could imply a desire to understand the situation or help, though the outcome was merely looting. The repeated abandonment of allies suggests a selfish orientation, but the lack of active malice keeps it from being purely malicious.

### T0009 — perceived_profile.risk.label

- Human: `reckless` — evidence `{"counterevidence":["S013-C02","S019-C01"],"supporting":["S009-C01","S017-C02","S025-C02"]}`
- Qwen: `neutral` — evidence `{"counterevidence":["S019-C01","S005-C01"],"supporting":["S003-C01","S017-C02","S038-C02"]}`
- Human justification: The player repeatedly accepts avoidable danger by helping under aerial attack, fighting the Giaks, charging through Doomwolves, remaining exposed on the highway, and later choosing another fight. Tactical retreats also recur, so the risk orientation is strong but not uniform.
- Qwen justification: The player exhibits a mix of caution and recklessness. Cautious behaviors include hiding from the Kraan (S003), avoiding the bear path (S005), and veering off the highway to escape a diving Kraan (S019). Reckless behaviors include charging head-on into Doomwolves (S017-S018) and attempting a dangerous roof jump (S038). Neither pole dominates exclusively.

### T0009 — perceived_profile.action.support

- Human: `mixed` — evidence `{"counterevidence":["S013-C02","S019-C01"],"supporting":["S010-C01","S017-C02","S035-C01"]}`
- Qwen: `clear` — evidence `{"counterevidence":["S003-C01","S019-C01"],"supporting":["S010-C01","S017-C02","S035-C01"]}`
- Human justification: Several voluntary choices favor direct force or confrontation, including fighting the Giaks, charging through attackers, and fighting the madman. The player also uses cover and bypasses some conflicts, so physical action does not dominate every situation.
- Qwen justification: The player consistently chooses direct confrontation and physical force. They fight Giaks (S010), charge Doomwolves (S017), fight bandits (S030), and fight a madman (S035). Even when tactical options like hiding or evading are available (e.g., S025, S035), the player often opts for the physical engagement or the most direct physical route (roof jumping).

### T0009 — profile_coherence.label

- Human: `mixed` — evidence `{"counterevidence":["S013-C02","S019-C01"],"supporting":["S010-C01","S017-C02","S035-C01"]}`
- Qwen: `coherent` — evidence `{"counterevidence":["S006-C02","S019-C01"],"supporting":["S009-C01","S010-C01","S017-C02"]}`
- Human justification: A risk-accepting and physically direct profile is visible, especially around combat, but repeated evasive choices and route avoidance create a meaningful competing tactical tendency.
- Qwen justification: The decisions form a stable profile of a brave, duty-bound warrior who prefers direct action. The mix of risk-taking (charging enemies) and caution (hiding from superior air threats) is consistent with a skilled combatant assessing immediate threats. The moral choices align with the 'noble' archetype of the Kai warrior.

### T0014 — perceived_profile.risk.support

- Human: `mixed` — evidence `{"counterevidence":["S022-C01","S028-C01"],"supporting":["S016-C02","S017-C02","S025-C02"]}`
- Qwen: `clear` — evidence `{"counterevidence":["S022-C01"],"supporting":["S002-C02","S017-C02","S025-C02"]}`
- Human justification: The player commonly stays under cover, leaves compromised routes, avoids uncertain contacts, and presses on rather than investigate optional sites. This pattern is opposed by entering an explicitly dangerous tunnel and deliberately approaching the sound of battle.
- Qwen justification: The player repeatedly chooses paths that minimize exposure to danger or allow for evasion. Evidence includes cutting through foliage to avoid known enemy tracks (S002-C02), freezing and hiding when a monster passes overhead (S003), avoiding the source of wood smoke (S017-C02), and choosing to travel under cover of trees rather than joining a visible refugee column (S025-C02). The decision to enter a dark tunnel (S022-C01) is a minor counterpoint, but the overall pattern favors stealth and avoidance over confrontation or exposure.

### T0014 — profile_coherence.label

- Human: `mixed` — evidence `{"counterevidence":["S004-C01","S022-C01"],"supporting":["S016-C02","S025-C02","S027-C02"]}`
- Qwen: `coherent` — evidence `{"counterevidence":["S004-C01"],"supporting":["S027-C02","S029-C02","S025-C02"]}`
- Human justification: The risk and action choices are broadly cautious and tactical, but the moral profile shifts from aiding the wizard to abandoning two explicitly endangered allies.
- Qwen justification: The decisions form a stable profile of a cautious, self-preserving character who relies on stealth and avoidance. The initial help to the wizard is an exception, but the subsequent abandonment of the soldier and the Prince aligns with a 'selfish' or 'survivalist' orientation that prioritizes the mission and self over others. The tactical approach is consistent throughout.

### C003 — narrative_distinctness.label

- Human: `high` — evidence `{"story_a":["S014-C02","S015-C02","S021-C01","S030-C02","S040-C02"],"story_b":["S009-C01","S010-C01","S017-C02","S025-C02","S035-C01"]}`
- Qwen: `medium` — evidence `{"story_a":["S014-C02","S015-C02","S027-C02","S029-C01","S030-C02"],"story_b":["S009-C01","S010-C01","S017-C02","S025-C02","S030-C01"]}`
- Human justification: Although the stories share several locations and later city material, they present clearly different ways of moving through the adventure. Story A repeatedly withdraws from danger and from opportunities to help, then relies on concealment and indirect routes. Story B repeatedly enters dangerous situations, helps the children, fights directly, and presses ahead through exposed threats.
- Qwen justification: Both trajectories follow the same general route from the monastery to Holmgard and share the same ending. However, the manner of travel differs significantly. Story A involves a more cautious, stealth-oriented approach, utilizing the river and hiding from threats (S027-C02, S029-C01, S030-C02). Story B involves a more direct, high-risk approach, charging through enemies on horseback (S017-C02) and fighting bandits on the highway (S025-C02, S030-C01). The experience in A is one of evasion and survival, while B is one of confrontation and speed.

### C006 — perceived_profile_shift.risk

- Human: `A_more_cautious` — evidence `{"story_a":["S004-C04","S013-C03","S020-C02","S025-C02","S026-C02"],"story_b":["S004-C01","S013-C01","S016-C02","S022-C01","S028-C01"]}`
- Qwen: `similar` — evidence `{"story_a":["S004-C04","S013-C03","S025-C02"],"story_b":["S004-C01","S020-C02","S027-C02"]}`
- Human justification: A shows more repeated danger avoidance, notably leaving the wizard's battle, taking cover when the Kraan approach, leaving the wounded soldier, and initially continuing away from the battle. B takes several comparatively riskier options, including warning the wizard, investigating huts despite fresh Giak tracks, entering the unknown tunnel, and following the sound of battle. Morally, both later leave endangered characters, but B's warning to the wizard contrasts with A's explicit withdrawal, making A more selfish overall. For action, A's direct pre-emptive attack on the suspicious stranger gives it a more physical orientation relative to B's warning, route changes, and avoidance choices.
- Qwen justification: Risk: Both protagonists engage in combat when forced (Vordak/Burrowcrawler in A, Burrowcrawler in B) and flee from overwhelming odds (Giaks in both). Story A attacks a stranger (Vordak) while Story B avoids a treehouse; these balance out. Morality: Story A explicitly chooses to leave a wounded wizard to die (S004-C04) and later leaves a wounded soldier (S025-C02). Story B chooses to help the wizard (S004-C01) but also leaves the wounded soldier (S027-C02). The initial choice to save a life in B versus abandoning it in A makes A more selfish. Action: Story A chooses to draw a weapon and attack a stranger (S013-C03), a direct physical confrontation. Story B chooses to avoid a potential threat (the treehouse) and take a different path (S020-C02), showing more caution/tactical avoidance. Thus, A is more physical.
