# Data Schema: Gamebook Graph Extraction

> Reference for all data files produced by phase 1 (extraction).
> See `docs/gamebook_global_plan.md` for the overall pipeline and
> `docs/gamebook_mechanics.md` for the modeling choices.
> The legacy edges schema (pre-LLM extraction) is archived in
> `docs/archives/legacy_edges_schema.md`.

## 1. Pipeline and File Naming Convention

```
data/raw/LWXX/sections/sect*.htm          (Project Aon HTML, one file per paragraph)
        │
        │  scripts/1_parse_for_edge_extraction.py
        ▼
data/processed/nodes_edges/LWXX/LWXX_for_edges_extraction.json   (paragraphs with <choice> tags)
        │
        │  cluster: cluster_scripts/extract.py (vLLM + structured outputs)
        ▼
data/processed/nodes_edges/LWXX/LWXX_e_edges.csv                 (enhanced edges table, §3)

data/raw/LWXX/sections/sect*.htm
        │
        │  scripts/2_parse_nodes.py (to be refactored from the node part of
        ▼  the legacy scripts/2_parse_simple_gamebook.py)
data/processed/nodes_edges/LWXX/LWXX_nodes.csv                   (nodes table, §2)
```

File naming: `[SeriesCode][BookNumber]_[DataType].[ext]`

* `SeriesCode`: e.g., `LW` for Lone Wolf, `FF` for Fighting Fantasy.
* `BookNumber`: two digits, e.g., `01`, `02`.
* `DataType`: `nodes`, `e_edges`, `for_edges_extraction`, `calibration*` (see §4).

### Intermediate JSON (`LWXX_for_edges_extraction.json`)

A list of paragraph objects. Choice texts are kept inline, wrapped in `<choice>` tags,
so the LLM sees each choice in its narrative context:

```json
[
  {
    "id": "1",
    "text": "Narrative text of the paragraph... <choice>If you wish to..., turn to 85.</choice> <choice>...</choice>"
  }
]
```

---

## 2. Nodes Table (`LWXX_nodes.csv`)

Models the static properties of each paragraph. It strictly captures what is written on
the page, handling multiple entities via JSON-like strings to avoid column bloat.

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

## 3. Enhanced Edges Table (`LWXX_e_edges.csv`)

The reference edges table, produced by the LLM extraction on the cluster
(`cluster_scripts/extract.py` + `system_prompt_final.txt`, structured outputs enforced by
`cluster_scripts/schemas.py`). One row per outgoing transition.

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

The semantic axes feed the player profiles defined in
`docs/gamebook_global_plan.md` §7.

---

## 4. Calibration Files (`data/for_edge_extraction/`)

Used to calibrate the LLM extraction prompt against a manually annotated gold standard
(see the calibration history in `results/curnagl_results/`).

| File | Content |
| :--- | :--- |
| `LWXX_calibration.json` | Manually selected subset of paragraphs, same format as the intermediate JSON (§1). |
| `LWXX_calibration_edges_gold.csv` | Manually annotated gold edges for this subset, same schema as `LWXX_e_edges.csv` (§3). |

Evaluation: `scripts/utils/eval_diff.py` compares a cluster output against the gold and
writes an error report (`rapport_erreurs_*.csv`, one row per divergence with a
`gravite` level).

Quality control of a full extraction: `scripts/utils/qc_extraction.py` checks the final
edges table against the tagged corpus and the nodes table (completeness vs `<choice>`
tags, ID validity, absorbing states, schema-rule coherence, label distributions,
reachability) and prints a summary report.
