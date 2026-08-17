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
| `docs/gamebook_global_plan.md` | **Current reference plan**: research question, generic model, decisions and roadmap. |
| `docs/graph_model.md` | Adopted L0–L3 graph model, mechanics scope and compilation process. |
| `docs/progress_log.md` | Append-only progress journal and current project status. |
| `docs/infict-llm_abstract.tex` | Accepted COMHUM2026 extended abstract. |
| `docs/cluster_help/` | HPC (Curnagl) workflow notes. |
| `docs/archives/` | Superseded plans, schemas and notes, preserved for history. |

## Repository layout

```
docs/            current plan, progress journal, abstract and archived documentation
scripts/         local pipeline: 1_parse_for_edge_extraction.py, 2_parse_nodes.py
scripts/utils/   cross-cutting tools (eval_diff.py: gold vs LLM comparison)
cluster_scripts/ LLM edge extraction on the cluster (vLLM + structured outputs)
data/raw/        Project Aon HTML sections
data/processed/  extracted nodes/edges tables
data/for_edge_extraction/  manual calibration set (paragraphs + gold edges)
results/         cluster outputs and calibration history
*/archives/      inactive material kept for history
```

## Pipeline status (August 2026)

1. **Extraction** (phase 1, done): prompt calibrated on Qwen3.6-27B (3 soft divergences
   vs the gold standard), full book extracted (556 edges, `LW01_e_edges.csv`) and
   quality-checked (complete vs `<choice>` tags, fully reachable graph, zero schema
   violations).
2. **Graph modeling** (phase 2, specified, to implement): generic L0–L2 graph,
   adaptation tables, probabilistic baseline and player policies. Detailed Lone Wolf
   state mechanics are optional extensions rather than part of the core model.
3. **BoP and analyses** (later phases): select justified structural indices, sample
   representative paths and develop the LLM critic protocol.

## Setup

Python project managed with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python scripts/1_parse_for_edge_extraction.py
uv run python scripts/2_parse_nodes.py
```
