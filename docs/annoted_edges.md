# Examples

```json
{
    "id": 1,
    "text": "You must make haste for you sense it is not safe to linger by the smoking remains of the ruined monastery. The black-winged beasts could return at any moment. You must set out for the Sommlending capital of Holmgard and tell the King the terrible news of the massacre: that the whole élite of Kai warriors, save yourself, have been slaughtered. Without the Kai Lords to lead her armies, Sommerlund will be at the mercy of their ancient enemy, the Darklords. Fighting back tears, you bid farewell to your dead kinsmen. Silently, you promise that their deaths will be avenged. You turn away from the ruins and carefully descend the steep track. At the foot of the hill, the path splits into two directions, both leading into a large wood. <choice>If you wish to use your Kai Discipline of Sixth Sense, turn to 141.</choice> <choice>If you wish to take the right path into the wood, turn to 85.</choice> <choice>If you wish to follow the left track, turn to 275.</choice>"
  }
```

```json
[
  {
    "source_id": "1",
    "target_id": "141",
    "edge_text": "If you wish to use your Kai Discipline of Sixth Sense, turn to 141.",
    "transition_type": "conditional",
    "stochastic_value": null,
    "condition_value": "If you wish to use your Kai Discipline of Sixth Sense", 
    "semantic_risk_level": null,
    "semantic_moral_stance": null,
    "semantic_cognitive_approach": null,
    "parsing_confidence": 4,
  },
  {
    "source_id": "1",
    "target_id": "85",
    "edge_text": "If you wish to take the right path into the wood, turn to 85.",
    "transition_type": "explicit_choice",
    "stochastic_value": null,
    "condition_value": null, 
    "semantic_risk_level": 3,
    "semantic_moral_stance": 3,
    "semantic_cognitive_approach": 3,
    "parsing_confidence": 4,
  },
  {
    "source_id": "1",
    "target_id": "275",
    "edge_text": "If you wish to follow the left track, turn to 275.",
    "transition_type": "explicit_choice",
    "stochastic_value": null,
    "condition_value": null, 
    "semantic_risk_level": 3,
    "semantic_moral_stance": 3,
    "semantic_cognitive_approach": 3,
    "parsing_confidence": 4,
  },
]
```
