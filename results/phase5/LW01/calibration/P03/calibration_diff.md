# Phase 5 pilot — Human/Qwen calibration comparison

> Descriptive prompt calibration only. This is neither accuracy nor an
> out-of-sample validation, and disagreements are not automatically errors.

## Summary

| Status | Count |
| :--- | ---: |
| `match` | 32 |
| `disagreement` | 10 |
| `human_abstention` | 2 |
| `model_abstention` | 0 |

## Evidence-rule check

- Human violations: 0
- Qwen violations: 0


## All compared fields

| Task | ID | Field | Human | Qwen | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| individual | `T0001` | `perceived_profile.risk.label` | `cautious` | `neutral` | `disagreement` |
| individual | `T0001` | `perceived_profile.risk.support` | `mixed` | `mixed` | `match` |
| individual | `T0001` | `perceived_profile.morality.label` | `unclear` | `neutral` | `human_abstention` |
| individual | `T0001` | `perceived_profile.morality.support` | `insufficient` | `mixed` | `human_abstention` |
| individual | `T0001` | `perceived_profile.action.label` | `tactical` | `tactical` | `match` |
| individual | `T0001` | `perceived_profile.action.support` | `mixed` | `clear` | `disagreement` |
| individual | `T0001` | `causal_continuity.label` | `continuous` | `continuous` | `match` |
| individual | `T0001` | `profile_coherence.label` | `mixed` | `mixed` | `match` |
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
| individual | `T0009` | `profile_coherence.label` | `mixed` | `mixed` | `match` |
| individual | `T0014` | `perceived_profile.risk.label` | `cautious` | `neutral` | `disagreement` |
| individual | `T0014` | `perceived_profile.risk.support` | `mixed` | `mixed` | `match` |
| individual | `T0014` | `perceived_profile.morality.label` | `selfish` | `selfish` | `match` |
| individual | `T0014` | `perceived_profile.morality.support` | `mixed` | `clear` | `disagreement` |
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
| pairwise | `C006` | `perceived_profile_shift.risk` | `A_more_cautious` | `A_more_reckless` | `disagreement` |
| pairwise | `C006` | `perceived_profile_shift.morality` | `A_more_selfish` | `A_more_selfish` | `match` |
| pairwise | `C006` | `perceived_profile_shift.action` | `A_more_physical` | `A_more_physical` | `match` |

## Fields requiring textual review

### T0001 — perceived_profile.risk.label

- Human: `cautious` — evidence `{"counterevidence":["S018-C02","S029-C03"],"supporting":["S020-C01","S026-C01","S035-C02"]}`
- Qwen: `neutral` — evidence `{"counterevidence":["S025-C01","S029-C03"],"supporting":["S026-C01","S036-C02","S015-C02"]}`
- Human justification: Avoidable danger is repeatedly sidestepped through cover, waiting, evasion, and bypassing nearby conflict. This cautious tendency is substantial but not uniform, because the trajectory also chooses a direct charge through Doomwolves and prepares to fight suspicious soldiers.
- Qwen justification: The player exhibits a mix of caution and recklessness. S026-C01 shows caution by hiding from Doomwolves, and S036-C02 shows caution by waiting for a madman to disappear. However, S025-C01 involves taking a risky open route to the capital, and S029-C03 involves initiating combat with soldiers, which is a voluntary engagement with danger.

### T0001 — perceived_profile.morality.label

- Human: `unclear` — evidence `{"counterevidence":["S010-C02"],"supporting":["S011-C01"]}`
- Qwen: `neutral` — evidence `{"counterevidence":["S010-C02","S034-C02"],"supporting":["S006-C01","S011-C01","S009-C01"]}`
- Human justification: The clearest moral evidence is confined to the wagon episode: the player first runs for personal cover, then returns to defend the children. The reversal leaves too little repeated evidence elsewhere to support a stable moral orientation.
- Qwen justification: The player shows noble intent by approaching refugees (S006-C01) and defending children (S011-C01). However, this is contradicted by initially fleeing from the children in danger (S010-C02) and prioritizing personal speed/safety by avoiding the King's Guard (S015-C02) and declining assistance from a court official (S034-C02), suggesting a self-reliant or self-preservationist streak.

### T0001 — perceived_profile.morality.support

- Human: `insufficient` — evidence `{"counterevidence":["S010-C02"],"supporting":["S011-C01"]}`
- Qwen: `mixed` — evidence `{"counterevidence":["S010-C02","S034-C02"],"supporting":["S006-C01","S011-C01","S009-C01"]}`
- Human justification: The clearest moral evidence is confined to the wagon episode: the player first runs for personal cover, then returns to defend the children. The reversal leaves too little repeated evidence elsewhere to support a stable moral orientation.
- Qwen justification: The player shows noble intent by approaching refugees (S006-C01) and defending children (S011-C01). However, this is contradicted by initially fleeing from the children in danger (S010-C02) and prioritizing personal speed/safety by avoiding the King's Guard (S015-C02) and declining assistance from a court official (S034-C02), suggesting a self-reliant or self-preservationist streak.

### T0001 — perceived_profile.action.support

- Human: `mixed` — evidence `{"counterevidence":["S018-C02","S029-C03"],"supporting":["S020-C01","S026-C01","S035-C02"]}`
- Qwen: `clear` — evidence `{"counterevidence":["S029-C03","S018-C02"],"supporting":["S015-C02","S026-C01","S035-C02"]}`
- Human justification: The trajectory often favors cover, waiting, avoidance, and disengagement rather than direct confrontation. Several direct-risk choices recur, however, so the tactical orientation is noticeable without being fully consistent.
- Qwen justification: The player repeatedly chooses observation, concealment, or strategic avoidance over direct confrontation. S015-C02 avoids the Guard to stay hidden. S026-C01 hides from Doomwolves. S035-C02 evades a fight with a madman. S036-C02 waits for safety. Even when combat occurs (S029-C03), it is a reaction to a threat, but the overall pattern favors tactical positioning and evasion.

### T0004 — perceived_profile.morality.support

- Human: `clear` — evidence `{"counterevidence":[],"supporting":["S004-C04","S027-C02"]}`
- Qwen: `mixed` — evidence `{"counterevidence":["S010-C01"],"supporting":["S004-C04","S025-C03","S027-C02"]}`
- Human justification: When another person's danger is explicit, the trajectory twice prioritizes personal survival or the mission: it abandons the threatened wizard and later runs rather than defend the fallen Prince. No comparably clear prosocial player choice offsets these decisions.
- Qwen justification: The player consistently prioritizes their own safety and mission completion over the welfare of others. They explicitly abandon a wizard in danger (S004-C04), ignore a potential victim behind a boulder (S025-C03), and flee from a wounded Prince (S027-C02). While they investigate a crime scene (S010-C01), this is done for information rather than aid, and the overwhelming pattern is one of non-intervention and self-preservation.

### T0009 — perceived_profile.risk.label

- Human: `reckless` — evidence `{"counterevidence":["S013-C02","S019-C01"],"supporting":["S009-C01","S017-C02","S025-C02"]}`
- Qwen: `neutral` — evidence `{"counterevidence":["S024-C01","S025-C02"],"supporting":["S002-C01","S019-C01","S017-C02"]}`
- Human justification: The player repeatedly accepts avoidable danger by helping under aerial attack, fighting the Giaks, charging through Doomwolves, remaining exposed on the highway, and later choosing another fight. Tactical retreats also recur, so the risk orientation is strong but not uniform.
- Qwen justification: The player exhibits a mix of caution and recklessness. S002-C01 (heading south to avoid known danger) and S019-C01 (veering off to cover) show caution. Conversely, S017-C02 (charging through Doomwolves) and S024-C01 (running on the open highway) show voluntary engagement with high danger. Neither pole dominates exclusively.

### T0009 — perceived_profile.action.support

- Human: `mixed` — evidence `{"counterevidence":["S013-C02","S019-C01"],"supporting":["S010-C01","S017-C02","S035-C01"]}`
- Qwen: `clear` — evidence `{"counterevidence":["S006-C02","S014-C02"],"supporting":["S010-C01","S017-C02","S035-C01"]}`
- Human justification: Several voluntary choices favor direct force or confrontation, including fighting the Giaks, charging through attackers, and fighting the madman. The player also uses cover and bypasses some conflicts, so physical action does not dominate every situation.
- Qwen justification: The player repeatedly chooses direct confrontation and force. S010-C01 (fight Giaks), S017-C02 (charge through enemies), S025-C02 (draw weapon and run), and S035-C01 (fight madman) all demonstrate a preference for physical engagement over tactical avoidance or stealth.

### T0014 — perceived_profile.risk.label

- Human: `cautious` — evidence `{"counterevidence":["S022-C01","S028-C01"],"supporting":["S016-C02","S017-C02","S025-C02"]}`
- Qwen: `neutral` — evidence `{"counterevidence":["S013-C01","S025-C02"],"supporting":["S002-C02","S008-C02","S022-C01"]}`
- Human justification: The player commonly stays under cover, leaves compromised routes, avoids uncertain contacts, and presses on rather than investigate optional sites. This pattern is opposed by entering an explicitly dangerous tunnel and deliberately approaching the sound of battle.
- Qwen justification: The player exhibits a mix of cautious avoidance and voluntary engagement with danger. S002-C02 (cutting through heavy foliage to avoid known patrols) and S008-C02 (changing direction to escape ambush) demonstrate caution. Conversely, S022-C01 (entering a dark, unknown tunnel) and S013-C01 (investigating a hut with fresh Giak tracks) show a willingness to engage with potential threats. These competing behaviors prevent a clear classification as either consistently cautious or reckless.

### T0014 — perceived_profile.morality.support

- Human: `mixed` — evidence `{"counterevidence":["S004-C01"],"supporting":["S027-C02","S029-C02"]}`
- Qwen: `clear` — evidence `{"counterevidence":["S004-C01"],"supporting":["S027-C02","S029-C02","S017-C02"]}`
- Human justification: The trajectory later abandons a wounded King's soldier and then runs from the fallen Prince, both clear choices of self-preservation over helping others. Earlier, however, it warns the endangered wizard, providing direct noble counterevidence.
- Qwen justification: The player repeatedly prioritizes personal safety and mission efficiency over the welfare of others. S027-C02 explicitly chooses to leave a wounded soldier behind. S029-C02 chooses to flee from a battle where the Prince is wounded, abandoning him to his fate. While S004-C01 involves helping a wizard, the subsequent choices to ignore or abandon others in distress (S027-C02, S029-C02) establish a dominant pattern of self-preservation at the expense of others.

### T0014 — profile_coherence.label

- Human: `mixed` — evidence `{"counterevidence":["S004-C01","S022-C01"],"supporting":["S016-C02","S025-C02","S027-C02"]}`
- Qwen: `coherent` — evidence `{"counterevidence":["S022-C01"],"supporting":["S004-C01","S027-C02","S029-C02"]}`
- Human justification: The risk and action choices are broadly cautious and tactical, but the moral profile shifts from aiding the wizard to abandoning two explicitly endangered allies.
- Qwen justification: The decisions form a stable profile of a self-preserving, tactical operator. The player avoids direct conflict (S004-C01, S008-C02, S025-C02) and prioritizes their own safety over helping others (S027-C02, S029-C02). The few instances of risk-taking (S022-C01, S013-C01) are consistent with a tactical approach to gathering information or finding shortcuts, rather than a desire for combat. The profile is internally consistent.

### C003 — narrative_distinctness.label

- Human: `high` — evidence `{"story_a":["S014-C02","S015-C02","S021-C01","S030-C02","S040-C02"],"story_b":["S009-C01","S010-C01","S017-C02","S025-C02","S035-C01"]}`
- Qwen: `medium` — evidence `{"story_a":["S014-C02","S015-C02","S021-C01","S030-C02","S040-C02"],"story_b":["S009-C01","S010-C01","S017-C02","S025-C02","S035-C01"]}`
- Human justification: Although the stories share several locations and later city material, they present clearly different ways of moving through the adventure. Story A repeatedly withdraws from danger and from opportunities to help, then relies on concealment and indirect routes. Story B repeatedly enters dangerous situations, helps the children, fights directly, and presses ahead through exposed threats.
- Qwen justification: Both trajectories share the same origin, destination, and final outcome, following a similar geographic path from the monastery to Holmgard. However, the manner of travel differs significantly in the middle section. Story A involves a stealthy approach via the river and hiding behind a log, avoiding direct confrontation with most threats. Story B involves a high-speed chase on horseback, a direct charge through Doomwolves, and a fight against bandits on the highway. These differences create a perceptible global difference in the experience of the journey (stealth vs. action), though the shared narrative basis keeps the label at medium.

### C006 — perceived_profile_shift.risk

- Human: `A_more_cautious` — evidence `{"story_a":["S004-C04","S013-C03","S020-C02","S025-C02","S026-C02"],"story_b":["S004-C01","S013-C01","S016-C02","S022-C01","S028-C01"]}`
- Qwen: `A_more_reckless` — evidence `{"story_a":["S004-C04","S013-C03","S019-C02","S025-C02","S029-C02"],"story_b":["S004-C01","S013-C01","S022-C01","S027-C02","S029-C02"]}`
- Human justification: A shows more repeated danger avoidance, notably leaving the wizard's battle, taking cover when the Kraan approach, leaving the wounded soldier, and initially continuing away from the battle. B takes several comparatively riskier options, including warning the wizard, investigating huts despite fresh Giak tracks, entering the unknown tunnel, and following the sound of battle. Morally, both later leave endangered characters, but B's warning to the wizard contrasts with A's explicit withdrawal, making A more selfish overall. For action, A's direct pre-emptive attack on the suspicious stranger gives it a more physical orientation relative to B's warning, route changes, and avoidance choices.
- Qwen justification: Risk: Story A exhibits more reckless behavior by choosing to attack a powerful undead Vordak directly (S013-C03) and initially attempting to climb an exposed hillside under threat of aerial attack (S019-C02), whereas Story B avoids the Vordak by calling out cautiously (S013-C01) and chooses to enter a tunnel for cover (S022-C01). Story A also leaves a valuable gem behind to run (S015-C02), prioritizing speed over gain, while B's choices are generally more cautious regarding engagement. Morality: Story A is more selfish, choosing to leave a wounded soldier without aid (S025-C02) and fleeing from a battle where the Prince is wounded (S029-C02). Story B also leaves the soldier (S027-C02) and flees the Prince (S029-C02), but earlier chose to help a wizard in danger (S004-C01), whereas Story A fled the wizard entirely (S004-C04). This makes A consistently more self-preserving at the expense of others. Action: Story A is more physical, opting to draw a weapon and attack the stranger (S013-C03) rather than observe or communicate. Story B opts for communication (S013-C01) and investigation (S013-C01 in B's context of tracking), showing a more tactical or observational approach compared to A's direct confrontation.
