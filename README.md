# Refining the Computational Analysis of Interactive Fiction: A Hybrid Framework using Bag-of-Paths Formalism and LLMs

Project repository for the COMHUM 2026 conference submission (accepted extended abstract:
`docs/infict-llm_abstract.tex`), to be followed by an article.

The project extracts the narrative graph of gamebooks (nodes = paragraphs, edges =
choices) from the first book of the *Lone Wolf* series ([Project Aon](https://www.projectaon.org)),
enriches the edges with LLM-extracted features (transition types, semantic axes), and
analyzes the resulting structure with the Bag-of-Paths formalism combined with LLM-based
narrative analysis.

## Documentation

| Document | Content |
| :--- | :--- |
| `docs/gamebook_global_plan.md` | **The reference plan**: research phases, scope decisions, index catalogue, player profiles. |
| `docs/gamebook_data_schema.md` | Data pipeline and schemas (nodes, enhanced edges, calibration files). |
| `docs/gamebook_mechanics.md` | Lone Wolf game mechanics and graph modeling strategy. |
| `docs/cleaning_plan.md` | Repo cleanup plan (July 2026) and its progress. |
| `docs/cluster_help/` | HPC (Curnagl) workflow notes. |
| `docs/archives/` | Superseded notes, kept for reference. |

## Repository layout

```
docs/            reference notes (see above)
scripts/         local pipeline: 1_parse_for_edge_extraction.py, 2_parse_nodes.py
scripts/utils/   cross-cutting tools (eval_diff.py: gold vs LLM comparison)
cluster_scripts/ LLM edge extraction on the cluster (vLLM + structured outputs)
data/raw/        Project Aon HTML sections
data/processed/  extracted nodes/edges tables
data/for_edge_extraction/  manual calibration set (paragraphs + gold edges)
results/         cluster outputs and calibration history
*/archives/      inactive material kept for history
```

## Pipeline status (July 2026)

1. **Extraction** (phase 1, done): prompt calibrated on Qwen3.6-27B (4 soft divergences
   vs the gold standard), full book extracted (556 edges, `LW01_e_edges.csv`) and
   quality-checked (complete vs `<choice>` tags, fully reachable graph, zero schema
   violations).
2. **Modeling** (phase 2, to do): weighted graph with (Node, EP) state expansion,
   player profiles, Bag-of-Paths.
3. **Indices & analyses** (phase 3, to do): structural indices, path sampling,
   LLM critic.

## Setup

Python project managed with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python scripts/1_parse_for_edge_extraction.py
uv run python scripts/2_parse_nodes.py
```
