| Column Name | Data Type | Description / Modalities |
| :--- | :--- | :--- |
| `source_id` | String | The originating `node_id`. |
| `target_id` | String | The destination `node_id`. |
| `edge_text` | String | The exact raw text of the choice presented to the player (between `<choice>` tags). |
| `transition_type` | Category | Defines the nature of the link:<br> - `forced`: Automatic progression with no alternatives.<br> - `explicit_choice`: Standard player decision.<br> - `stochastic`: Based on a random roll.<br> - `conditional`: Based on a specific requirement (item, skill, stat, combat outcome).<br> - `complex`: Combats or unusual choices (e.g., risk of death). |
| `realisation_value` | String / Null | The exact raw text triggering the outcome. **Requires** `transition_type` to be `stochastic` or `conditional`. Otherwise, `null`. |
| `semantic_risk` | Category / Null | Axis of risk. Evaluated as `cautious`, `neutral`, or `reckless` via contrastive evaluation. **Requires** `transition_type` to be `explicit_choice`. Otherwise, `null`. |
| `semantic_morality` | Category / Null | Axis of morality. Evaluated as `selfish`, `neutral`, or `noble` via contrastive evaluation. **Requires** `transition_type` to be `explicit_choice`. Otherwise, `null`. |
| `semantic_action` | Category / Null | Axis of approach. Evaluated as `physical`, `neutral`, or `tactical` via contrastive evaluation. **Requires** `transition_type` to be `explicit_choice`. Otherwise, `null`. |
| `warnings` | String / Null | Annotator comments. Used ONLY if the text is ambiguous, broken, or highly unusual. Otherwise, `null`. |


On a les `transition_type` suivants : 

- Forced : Probabilité fixée (facile)
- Stochastic : Probabilité fixée (facile)
- Explicit_choice : Probabilité qui dépend du "profil" du joueur, il faut un peu plus réfléchir à l'encodage.
- Conditional - object : Ignoré
- Conditional - Kai : Ici, il faut un peu réfléchir. Choix moyen ou inclus dans le "profil" du joueur. Je penche pour le choix moyen car il va être difficile de choisir des archétypes avec un style de jeu + de disciplines Kai.
- Combat : Petite chance de mourir ici, peut-être dépendante du profil du joueur. Mais si on ne fait pas les disciplines Kai, on va faire une probabilité fixe ici. 

QUESTIONS À RESOUDRE : 

1. Comment faire pour garder, dans l'encodage du graphe, la possibilité d'ajuster les probabilités de transition des edges "explicit_choice" en fonction du profil du joueur ?
2. Doit-on opter pour des probabilités "KAI" et probabilité "Combat" qui dépendent d'un type de joueur un faire des transitions moyennes ? 
3. (Touche aux autres questions) Dans le modèle BoP, à quoi correpsondent les deux bornes SP et RW ? Doit-on utiliser le modèle BoP qu'avec la borne RW ? (totalement possible car chaîne absorbante et $(I - W)^(-1)$ converge)
4. Quels sont les noeuds qui ne sont pas modélisés par les décisions prises ci-dessus ?
5. Quelle doit-être la procédure pour passer de la table des edges à une table permettant de créer le graphe ? Comment trier et anoter les cas particuliers afin d'automatiser complétement la suite du processus.  