# [ARCHIVED] Legacy Edges Table Schema (`LWXX_edges.csv`)

> **Status: superseded (July 2026).** This was the original edges schema, produced by
> rule-based parsing in `scripts/2_parse_simple_gamebook.py`. It has been replaced by the
> LLM-extracted enhanced edges table (`LWXX_e_edges.csv`) documented in
> `docs/gamebook_data_schema.md` §3. Kept for reference because
> `data/processed/nodes_edges/LW01/LW01_edges.csv` was produced with this schema.

This table models the transitions connecting the nodes. It explicitly separates
text-based conditions from stochastic triggers.

| Column Name | Data Type | Description / Modalities |
| :--- | :--- | :--- |
| `source_id` | String | The originating `node_id`. |
| `target_id` | String | The destination `node_id`. |
| `edge_text` | Text | The exact raw text of the choice presented to the player. |
| `transition_type` | Category | Defines the nature of the link:<br> - `explicit_choice`: Standard player decision.<br> - `forced`: Automatic progression ("Turn to...").<br> - `stochastic`: Based on a random roll (Dice or RNT).<br> - `conditional`: Blocked by a specific requirement or combat outcome. |
| `stochastic_trigger` | String | The exact raw text or range triggering this edge (e.g., `0-4`, `even_number`). Leave empty if not stochastic. |
| `condition_type` | Category | The generalized type of lock on this edge:<br> - `none`: Freely accessible.<br> - `skill`: Requires a specific discipline/spell.<br> - `stat_check`: Based on a numeric threshold (Health, Luck, etc.).<br> - `combat_victory`: Requires defeating the enemies in this node.<br> - `combat_evasion`: Represents fleeing from the combat in this node.<br> - `item`: **[FUTURE-PROOFING]** Requires a specific object. |
| `condition_value` | String | The specific requirement (e.g., `Sixth Sense`, `<10`). Leave empty for combat outcomes. |
