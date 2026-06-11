# Examples

## 1

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
    "realisation_value": "If you wish to use your Kai Discipline of Sixth Sense", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 4
  },
  {
    "source_id": "1",
    "target_id": "85",
    "edge_text": "If you wish to take the right path into the wood, turn to 85.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 4
  },
  {
    "source_id": "1",
    "target_id": "275",
    "edge_text": "If you wish to follow the left track, turn to 275.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 4
  }
]
```

## 2


```json
{
    "id": 2,
    "text": "As you dash through the thickening trees, the shouts of the Giaks begin to fade behind you. You have nearly outdistanced them completely, when you crash headlong into a tangle of low branches. Pick a number from the Random Number Table. <choice>If you have picked a number 0–4, turn to 343.</choice> <choice>If you have picked a number 5–9, turn to 276.</choice>"
}
```

```json
[
  {
    "source_id": "2",
    "target_id": "343",
    "edge_text": "If you have picked a number 0–4, turn to 343.",
    "transition_type": "stochastic",
    "realisation_value": "If you have picked a number 0–4",
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  },
  {
    "source_id": "2",
    "target_id": "276",
    "edge_text": "If you have picked a number 5–9, turn to 276.",
    "transition_type": "stochastic",
    "realisation_value": "If you have picked a number 5–9",
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  }
]
```

## 12

```json
{
    "id": 12,
    "text": "The bodyguard looks at you with great suspicion and then slams the door shut. You can hear the sound of voices inside the caravan. Suddenly the door swings open and the face of a wealthy merchant appears. He demands 10 Gold Crowns as payment for the ride. <choice>If you have 10 Gold Crowns and wish to pay him, turn to 262.</choice> <choice>If you do not have enough Gold Crowns or do not wish to pay him, turn to 247.</choice>"
}
```

```json
[
  {
    "source_id": "12",
    "target_id": "262",
    "edge_text": "If you have 10 Gold Crowns and wish to pay him, turn to 262.",
    "transition_type": "conditional",
    "realisation_value": "If you have 10 Gold Crowns and wish to pay him", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "12",
    "target_id": "247",
    "edge_text": "If you do not have enough Gold Crowns or do not wish to pay him, turn to 247.",
    "transition_type": "conditional",
    "realisation_value": "If you do not have enough Gold Crowns or do not wish to pay him", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  }
]
```

## 21

```json
{
    "id": 21,
    "text": "You have ridden about two miles into the tangle of trees when the ground becomes very marshy. Pick a number from the Random Number Table. <choice>If it is below 5, your horse has suddenly plunged into thick mud up to its belly. If the number is 5 or above, you manage to steer clear of the morass and may now turn to 189.</choice> <choice>If you are stuck, pick another number from the Random Number Table. If this time the number is 7 or less, the mud engulfs you up to your armpits. Your horse gives one last despairing scream as its muzzle disappears into the bubbling mud. If you scored above 7, you drag yourself onto firm ground and turn to 189.</choice> <choice>If not, then this is your last chance! If you pick any number except a 9, the foul-smelling bog sucks you under and claims another victim. Your life and your mission end here. But if you have picked a 9, turn to 312.</choice>"
}
```

```json
[
  {
    "source_id": "21",
    "target_id": "189",
    "edge_text": "If it is below 5, your horse has suddenly plunged into thick mud up to its belly. If the number is 5 or above, you manage to steer clear of the morass and may now turn to 189.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "21",
    "target_id": "189",
    "edge_text": "If you are stuck, pick another number from the Random Number Table. If this time the number is 7 or less, the mud engulfs you up to your armpits. Your horse gives one last despairing scream as its muzzle disappears into the bubbling mud. If you scored above 7, you drag yourself onto firm ground and turn to 189.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "21",
    "target_id": "312",
    "edge_text": "If not, then this is your last chance! If you pick any number except a 9, the foul-smelling bog sucks you under and claims another victim. Your life and your mission end here. But if you have picked a 9, turn to 312.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  }
]
```

## 23

```json
{
    "id": 23,
    "text": "The corridor soon widens into a large hall. At the far end, a stone staircase leads up to a huge door. Two black candles on either side of the stone steps dimly illuminate the chamber. You notice that no wax has melted, and as you get nearer you can feel that they give off no heat. Ancient engravings cover the stone surfaces of the walls. Anxious to leave this evil tomb, you examine the door for a latch. An ornate pin appears to lock the door, but there is also a keyhole in the lockplate. <choice>If you have a Golden Key and wish to use it, turn to 326.</choice> <choice>If you have the Kai Discipline of Mind Over Matter, turn to 151.</choice> <choice>If you wish to remove the pin, turn to 337.</choice>"
  }
```

```json
[
  {
    "source_id": "23",
    "target_id": "326",
    "edge_text": "If you have a Golden Key and wish to use it, turn to 326.",
    "transition_type": "conditional",
    "realisation_value": "If you have a Golden Key and wish to use it", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 2
  },
  {
    "source_id": "23",
    "target_id": "151",
    "edge_text": "If you have the Kai Discipline of Mind Over Matter, turn to 151.",
    "transition_type": "conditional",
    "realisation_value": "If you have the Kai Discipline of Mind Over Matter", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 2
  },
  {
    "source_id": "23",
    "target_id": "337",
    "edge_text": "If you wish to remove the pin, turn to 337.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "reckless",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 2
  }
]
```

## 27

```json
{
    "id": 27,
    "text": "You walk along this path for over an hour, carefully watching the sky above you in case the Kraan attack again. Up ahead, a large tree has fallen across the path. As you approach, you can hear voices coming from the other side of the massive trunk. <choice>If you choose to attack, turn to 250.</choice> <choice>If you choose to listen to what the voices say, turn to 52.</choice>"
}
```

```json
[
  {
    "source_id": "27",
    "target_id": "250",
    "edge_text": "If you choose to attack, turn to 250.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "reckless",
    "semantic_morality": "neutral",
    "semantic_action": "physical",
    "parsing_confidence": 4
  },
  {
    "source_id": "27",
    "target_id": "52",
    "edge_text": "If you choose to listen to what the voices say, turn to 52.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "cautious",
    "semantic_morality": "neutral",
    "semantic_action": "tactical",
    "parsing_confidence": 4
  }
]
```

## 97

```json
{
    "id": 97,
    "text": "Ahead of you, you can see a fierce battle raging across a stone bridge. The clash of steel and the cries of men and beasts echo through the forest. In the midst of the fighting, you see Prince Pelathar, the King’s son. He is in combat with a large grey Gourgaz who is wielding a black axe above his scaly head. Suddenly, the Prince falls wounded—a black arrow in his side. <choice>If you wish to defend the fallen Prince, turn to 255.</choice> <choice>If you wish to run into the forest, turn to 306.</choice>"
}
```

```json
[
  {
    "source_id": "97",
    "target_id": "255",
    "edge_text": "If you wish to defend the fallen Prince, turn to 255.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "reckless",
    "semantic_morality": "noble",
    "semantic_action": "physical",
    "parsing_confidence": 4
  },
  {
    "source_id": "97",
    "target_id": "306",
    "edge_text": "If you wish to run into the forest, turn to 306.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "cautious",
    "semantic_morality": "selfish",
    "semantic_action": "neutral",
    "parsing_confidence": 4
  }
]
```

## 104

```json
{
    "id": 104,
    "text": "The walls are dank and slimy. The stale air chokes you and cobwebs brush across your face. You can feel panic grip your stomach, as the tunnel gets darker and darker. You reach a junction where the tunnel meets a corridor leading from north to south. <choice>If you wish to turn north, go to 26.</choice> <choice>If you wish to go south, turn to 100.</choice>"
},
```

```json
[
  {
    "source_id": "104",
    "target_id": "26",
    "edge_text": "If you wish to turn north, go to 26.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 5
  },
  {
    "source_id": "104",
    "target_id": "100",
    "edge_text": "If you wish to go south, turn to 100.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 5
  }
]
```

## 125

```json
{
    "id": 125,
    "text": "The path opens out into a large clearing. You notice strange claw prints in the earth. Kraan have landed here. By the number of prints and by the size of the area disturbed, you judge that at least five of the foul creatures landed here in the last twelve hours. You see two exits on the far side of the clearing. One leads west, the other south. <choice>If you have the Kai Discipline of Tracking, turn to 301.</choice> <choice>If you wish to take the south path, turn to 27.</choice> <choice>If you wish to take the west path, turn to 214.</choice>"
}
```

```json
[
  {
    "source_id": "125",
    "target_id": "301",
    "edge_text": "If you have the Kai Discipline of Tracking, turn to 301.",
    "transition_type": "conditional",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "125",
    "target_id": "301",
    "edge_text": "If you wish to take the south path, turn to 27.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 3
  },
  {
    "source_id": "125",
    "target_id": "214",
    "edge_text": "If you wish to take the west path, turn to 214.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 3
  }
]
```

## 131

```json
{
    "id": 131,
    "text": "You have covered about a quarter of a mile when you hear shouting and a noise like thunderclaps ahead. Edging nearer, you soon make out a clearing that you recognize to be the site of the ruins of Raumas, an ancient forest temple. A war party of Giaks, some twenty-five to thirty strong, are attacking the ruins from all sides. Many more of the Giaks are dead or dying among the broken pillars of marble, but still they assault whatever is hidden inside. Suddenly, a bolt of blue lightning rips through the front rank of Giaks sending the armour-clad creatures tumbling in all directions. A Giak, taller than the others and dressed from head to foot in black chainmail, curses at his troops as he whips them forward with a barbed flail. With weapon ready, you move to the edge of the clearing, under cover of the thick foliage, and try to catch a glimpse of the defenders. To your amazement, the ruins are being defended by a young man no older than yourself. You recognize his sky-blue robes, embroidered with stars. He is a young theurgist of the Magicians’ Guild of Toran: an apprentice in magic. Five Giaks charge forward, their spears raised to stab the apprentice as he hurriedly retreats deeper into the ruins. You see him turn and raise his left hand just before a bolt of blue flame shoots from his fingertips into the snarling Giak soldiers. Close to where you are hidden, you see a Giak scuttle past and climb one of the pillars of the temple. He has a long curved dagger in his mouth and he is about to jump on the young wizard standing below. <choice>If you wish to shout a warning to the wizard, turn to 241.</choice> <choice>If you wish to run forward and attack the Giak when he jumps, turn to 55.</choice> <choice>If you wish to pick up a chunk of temple marble and throw it at the Giak’s head, turn to 302.</choice> <choice>Or if you would rather turn and leave the battle area and run back into the woods, turn to 101.</choice>"
}
```

```json
[
  {
    "source_id": "131",
    "target_id": "241",
    "edge_text": "If you wish to shout a warning to the wizard, turn to 241.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "tactical",
    "parsing_confidence": 3
  },
  {
    "source_id": "131",
    "target_id": "55",
    "edge_text": "If you wish to run forward and attack the Giak when he jumps, turn to 55.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "reckless",
    "semantic_morality": "noble",
    "semantic_action": "physical",
    "parsing_confidence": 3
  },
  {
    "source_id": "131",
    "target_id": "302",
    "edge_text": "If you wish to pick up a chunk of temple marble and throw it at the Giak’s head, turn to 302.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "neutral",
    "semantic_morality": "noble",
    "semantic_action": "physical",
    "parsing_confidence": 3
  },
  {
    "source_id": "131",
    "target_id": "101",
    "edge_text": "Or if you would rather turn and leave the battle area and run back into the woods, turn to 101.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "cautious",
    "semantic_morality": "selfish",
    "semantic_action": "neutral",
    "parsing_confidence": 3
  }
]
```

## 153


```json
{
    "id": 153,
    "text": "Before you are the tall grey-white walls and glimmering spires of Holmgard, the city’s banners fluttering from the battlements in the fresh morning breeze. Stretching out towards the west, the River Eledil traces its course from the mountains of the Durncrag Range to the Holmgulf. But below the mountain peaks you can see a vast black army marching relentlessly on towards the capital. To your right you can see the highway heading off over the rolling plain towards Holmgard. At a gallop you could make the outer fieldworks of the city’s defences in less than an hour, but you would be in the open for most of the time and vulnerable to attack by Kraan. Directly ahead of you, a wide river drifts sluggishly towards the Eledil. If you abandoned your horse, you could swim towards the outer defences under cover of the river banks. Or there is a final alternative. To your left lies the Graveyard of the Ancients. These tombs and crumbling monuments to a forgotten age would conceal your approach but it is a forbidden area. Many are the unnamed horrors that lie there in restless sleep, waiting to consume the unwary trespasser. <choice>If you will try your luck by the highway, turn to 202.</choice> <choice>If you feel that you stand a better chance of reaching the capital via the river then turn to 135.</choice> <choice>Or if you are brave enough to risk the unknown perils of the Graveyard of the Ancients, turn to 329.</choice>"
}
```


```json
[
  {
    "source_id": "153",
    "target_id": "202",
    "edge_text": "If you will try your luck by the highway, turn to 202.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 3
  },
  {
    "source_id": "153",
    "target_id": "135",
    "edge_text": "If you feel that you stand a better chance of reaching the capital via the river then turn to 135.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "physical",
    "parsing_confidence": 3
  },
  {
    "source_id": "153",
    "target_id": "329",
    "edge_text": "Or if you are brave enough to risk the unknown perils of the Graveyard of the Ancients, turn to 329.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "reckless",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 3
  }
]
```

## 203


```json
{
    "id": 203,
    "text": "You suddenly feel a searing pain shoot through your chest as something explodes against you in a shower of red sparks. You lose 10 ENDURANCE points. Through the smoke, the Sage is preparing to throw more explosives at you. <choice>If you have 10 or more ENDURANCE points left, turn to 80.</choice> <choice>If you now have less than 10 ENDURANCE points, turn to 344.</choice>"
}
```

```json
[
  {
    "source_id": "203",
    "target_id": "80",
    "edge_text": "If you have 10 or more ENDURANCE points left, turn to 80.",
    "transition_type": "conditional",
    "realisation_value": "If you have 10 or more ENDURANCE points left", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  },
  {
    "source_id": "203",
    "target_id": "344",
    "edge_text": "If you now have less than 10 ENDURANCE points, turn to 344.",
    "transition_type": "conditional",
    "realisation_value": "If you now have less than 10 ENDURANCE points", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  }
]
```

## 220

```json
{
    "id": 220,
    "text": "The bodyguard unsheathes a scimitar and lunges for your head. Bodyguard: COMBAT SKILL 11   ENDURANCE 20 <choice>If you win, turn to 24.</choice> <choice>If you wish to evade combat at any time during the fight, you can jump from the speeding caravan by turning to 234.</choice>"
  }
```

```json
[
  {
    "source_id": "220",
    "target_id": "24",
    "edge_text": "If you win, turn to 24.",
    "transition_type": "conditional",
    "realisation_value": "If you win", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 4
  },
  {
    "source_id": "220",
    "target_id": "234",
    "edge_text": "If you wish to evade combat at any time during the fight, you can jump from the speeding caravan by turning to 234.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "reckless",
    "semantic_morality": "neutral",
    "semantic_action": "physical",
    "parsing_confidence": 4
  }
]
```

## 227

```json
{
    "id": 227,
    "text": "You are now up to your waist in slimy water. The air is thick with small insects that sting your face and clog your nose. Something wraps itself around your leg. It is a Marshviper and you must fight it. Marshviper: COMBAT SKILL 16   ENDURANCE 6 <choice>If you lose any ENDURANCE points in the combat, turn to 271.</choice> <choice>If you kill it without losing any ENDURANCE points, turn to 348.</choice>"
}
```

```json
[
  {
    "source_id": "227",
    "target_id": "271",
    "edge_text": "If you lose any ENDURANCE points in the combat, turn to 271.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "227",
    "target_id": "348",
    "edge_text": "If you kill it without losing any ENDURANCE points, turn to 348.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  }
]
```

## 276 

```json
{
    "id": 276,
    "text": "Reaching for your weapon you manage to hack your way through the tangle of wood and twisted branches to the clearer forest beyond. Your cloak is torn in several places and your right leg is badly bruised above the knee. <choice>Lose 1 ENDURANCE point and turn to 213.</choice>"
}
```

```json
[
  {
    "source_id": "276",
    "target_id": "213",
    "edge_text": "Lose 1 ENDURANCE point and turn to 213.",
    "transition_type": "forced",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  }
]
```

## 294

```json
{
    "id": 294,
    "text": "Staying underwater for as long as you can, you finally surface to see the Giaks far behind you. You have lost your Weapon(s) and Backpack but at least you are still alive. You wade out of the muddy water and continue your journey under cover of the trees that line the right-hand bank. Pick a number from the Random Number Table. <choice>If the number you pick is 0–2, turn to 230.</choice> <choice>If the number is 3–6, turn to 190.</choice> <choice>If the number is 7–9, turn to 321.</choice>"
}
```

```json
[
  {
    "source_id": "294",
    "target_id": "230",
    "edge_text": "If the number you pick is 0–2, turn to 230.",
    "transition_type": "stochastic",
    "realisation_value": "If the number you pick is 0–2", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  },
  {
    "source_id": "294",
    "target_id": "190",
    "edge_text": "If the number is 3–6, turn to 190.",
    "transition_type": "stochastic",
    "realisation_value": "If the number is 3–6", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  },
  {
    "source_id": "294",
    "target_id": "321",
    "edge_text": "If the number is 7–9, turn to 321.",
    "transition_type": "stochastic",
    "realisation_value": "If the number is 7–9", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  }
]
```


## 303

```json
{
    "id": 303,
    "text": "The forest here is sparse and hilly. It does not give much cover from an attack from the air. You move as quickly as you can from tree to tree, to avoid the Kraan but you can hear the sound of Doomwolves close behind. <choice>If you have the Kai Discipline of Camouflage, turn to 237.</choice> <choice>If you do not, turn to 72.</choice>"
}
```

```json
[
  {
    "source_id": "303",
    "target_id": "237",
    "edge_text": "If you have the Kai Discipline of Camouflage, turn to 237.",
    "transition_type": "conditional",
    "realisation_value": "If you have the Kai Discipline of Camouflage", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  },
  {
    "source_id": "303",
    "target_id": "72",
    "edge_text": "If you do not, turn to 72.",
    "transition_type": "conditional",
    "realisation_value": "If you do not", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  }
]
```


## 333

```json
{
    "id": 333,
    "text": "You have cut your way through the thick undergrowth for nearly half an hour when you hear the beat of wings high above the trees. Looking up you can just make out the shape of a Kraan approaching from the north. It is one of the monsters that attacked the monastery and on its back are two grey-skinned creatures armed with long spears. These are Mountain Giaks—evil servants of the Darklords, full of hatred and malice. Many centuries ago, their ancestors were used by the Darklords to build the infernal city of Helgedad, which lies in the volcanic wastelands beyond the Durncrag range of mountains. The construction of the city was long and torturous and only the strongest of the Giaks survived the heat and poisonous atmosphere of Helgedad. Hidden by the trees, you freeze, keeping absolutely still as the Kraan passes overhead and disappears towards the south. When you are sure that it has gone, you move off once again into the forest. <choice>\nTurn to 131.</choice>"
  }
```

```json
[
  {
    "source_id": "333",
    "target_id": "131",
    "edge_text": "Turn to 131.",
    "transition_type": "forced",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 5
  }
]
```

## 334

```json
{
    "id": 334,
    "text": "As the stream vanishes up into the rocky hillside, you can see on the track above four soldiers and their officer. They wear the uniform of the King’s army. <choice>If you wish to use the Kai Discipline of Sixth Sense, turn to 48.</choice> <choice>If you wish to use the Kai Discipline of Camouflage and wait for them to pass, turn to 73.</choice> <choice>If you wish to approach them, turn to 162.</choice>"
}
```


```json
[
  {
    "source_id": "334",
    "target_id": "48",
    "edge_text": "If you wish to use the Kai Discipline of Sixth Sense, turn to 48.",
    "transition_type": "conditional",
    "realisation_value": "If you wish to use the Kai Discipline of Sixth Sense", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 2
  },
  {
    "source_id": "334",
    "target_id": "73",
    "edge_text": "If you wish to use the Kai Discipline of Camouflage and wait for them to pass, turn to 73.",
    "transition_type": "conditional",
    "realisation_value": "If you wish to use the Kai Discipline of Camouflage and wait for them to pass", 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 2
  },
  {
    "source_id": "334",
    "target_id": "162",
    "edge_text": "If you wish to approach them, turn to 162.",
    "transition_type": "explicit_choice",
    "realisation_value": null, 
    "semantic_risk": "neutral",
    "semantic_morality": "neutral",
    "semantic_action": "neutral",
    "parsing_confidence": 2
  }
]
```

## 339

```json
{
    "id": 339,
    "text": "You quickly sidestep just as a long dagger shatters the glass top of the counter. A swarthy youth is attacking you and you must fight him. Robber: COMBAT SKILL 13   ENDURANCE 20 <choice>If you kill him within 4 rounds of Combat, turn to 94.</choice> <choice>If you are still fighting after 4 rounds of Combat, turn to 203.</choice> <choice>You may evade combat by escaping through the front door at any stage of the fight, by turning to 7.</choice>"
}
```

```json
[
  {
    "source_id": "339",
    "target_id": "94",
    "edge_text": "If you kill him within 4 rounds of Combat, turn to 94.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "339",
    "target_id": "203",
    "edge_text": "If you are still fighting after 4 rounds of Combat, turn to 203.",
    "transition_type": "complex",
    "realisation_value": null, 
    "semantic_risk": null,
    "semantic_morality": null,
    "semantic_action": null,
    "parsing_confidence": 3
  },
  {
    "source_id": "339",
    "target_id": "7",
    "edge_text": "You may evade combat by escaping through the front door at any stage of the fight, by turning to 7.",
    "transition_type": "explicit_choice",
    "realisation_value": null,
    "semantic_risk": "cautious",
    "semantic_morality": "neutral",
    "semantic_action": "physical",
    "parsing_confidence": 3
  }
]
```