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
| `docs/graph_model.md` | Adopted direct multigraph model, mechanics scope and compilation process. |
| `docs/future_improvements.md` | Deferred improvements: structured phase-1 schema, portability and migration path. |
| `docs/progress_log.md` | Append-only progress journal and current project status. |
| `docs/infict-llm_abstract.tex` | Accepted COMHUM2026 extended abstract. |
| `docs/cluster_help/` | HPC (Curnagl) workflow notes. |
| `docs/archives/` | Superseded plans, schemas and notes, preserved for history. |

## Repository layout

```
docs/            current plan, progress journal, abstract and archived documentation
scripts/         numbered extraction and pregraph pipeline
scripts/tests/   lightweight, corpus-specific pipeline checks
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
2. **Pregraph construction** (phase 2, done for LW01): 352 nodes and 602 direct
   multiedges with constant or symbolic weighting rules. The 17 narrative preterminals
   lead to exactly two absorbing outcome nodes, `Death` and `Win`; all 556 phase-1 edges
   are classified or replaced by one of the 14 fully supervised sources.
3. **Profile compilation** (phase 3, planned): compile one `W` per player profile, with
   profile-dependent choice affinities, disciplines, and combat victory probabilities.
4. **BoP and analyses** (later phases): select justified structural indices, sample
   representative paths and develop the LLM critic protocol.

## Setup

Python project managed with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python scripts/1.1_parse_for_edge_extraction.py --book LW01
uv run python scripts/1.2_parse_node.py --book LW01
```

The same commands accept another Lone Wolf identifier, such as `--book LW02`, provided
its HTML sections follow the repository path convention described in the global plan.
