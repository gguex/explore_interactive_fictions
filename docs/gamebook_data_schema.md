# Data Schema: Gamebook Graph Extraction

## 1. File Naming Convention

To ensure consistency across multiple books and processing stages, files must follow this strict naming convention:
`[SeriesCode][BookNumber]_[DataType].csv`

* `SeriesCode`: E.g., `LW` for Lone Wolf, `FF` for Fighting Fantasy.
* `BookNumber`: Two digits, e.g., `01`, `02`.
* `DataType`: `nodes` (for paragraphs) or `edges` (for transitions).

**Examples:**
* `LW01_nodes.csv` (Flight from the Dark - Paragraphs)
* `LW01_edges.csv` (Flight from the Dark - Links)

---

## 2. Nodes Table (`LWXX_nodes.csv`)

This table models the static properties of each paragraph. It strictly captures what is written on the page, handling multiple entities via JSON-like strings to avoid column bloat.

| Column Name | Data Type | Description / Modalities |
| :--- | :--- | :--- |
| `node_id` | String | Unique identifier (e.g., "1", "112", "350"). |
| `text_content` | Text | The raw text of the paragraph, stripped of HTML tags. |
| `absorbing_status` | Category | Defines if the node ends the game:<br> - `none`: Normal narrative node.<br> - `win`: Successful end of the book.<br> - `death`: Instant narrative death.<br> - `potential_death`: Nodes where combat or mechanics *could* be lethal. |
| `enemies` | String (JSON) | List of dictionaries for all enemies present. E.g., `[{"name": "Giak 1", "cs": 13, "ep": 10}]`. Leave empty if no combat. |
| `health_modifier` | Integer | Fixed health changes occurring immediately at this node. Negative for damage/traps (e.g., `-2`), positive for healing (e.g., `+3`). Defaults to `0`. |
| `special_mechanic` | String | Highly specific, rule-breaking events (e.g., `meal_required`, `lose_backpack`). |
| `image_refs` | String | **[FUTURE-PROOFING]** Comma-separated list of image filenames found in the node (e.g., `small9.png`, `ill2.png`). |
| `items_granted` | String | **[FUTURE-PROOFING]** Comma-separated list of items found here. |

---

## 3. Edges Table (`LWXX_edges.csv`)

This table models the transitions connecting the nodes. It explicitly separates text-based conditions from stochastic triggers. 

| Column Name | Data Type | Description / Modalities |
| :--- | :--- | :--- |
| `source_id` | String | The originating `node_id`. |
| `target_id` | String | The destination `node_id`. |
| `edge_text` | Text | The exact raw text of the choice presented to the player. |
| `transition_type` | Category | Defines the nature of the link:<br> - `explicit_choice`: Standard player decision.<br> - `forced`: Automatic progression ("Turn to...").<br> - `stochastic`: Based on a random roll (Dice or RNT).<br> - `conditional`: Blocked by a specific requirement or combat outcome. |
| `stochastic_trigger` | String | The exact raw text or range triggering this edge (e.g., `0-4`, `even_number`). Leave empty if not stochastic. |
| `condition_type` | Category | The generalized type of lock on this edge:<br> - `none`: Freely accessible.<br> - `skill`: Requires a specific discipline/spell.<br> - `stat_check`: Based on a numeric threshold (Health, Luck, etc.).<br> - `combat_victory`: Requires defeating the enemies in this node.<br> - `combat_evasion`: Represents fleeing from the combat in this node.<br> - `item`: **[FUTURE-PROOFING]** Requires a specific object. |
| `condition_value` | String | The specific requirement (e.g., `Sixth Sense`, `<10`). Leave empty for combat outcomes. |