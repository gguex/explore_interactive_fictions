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
| `docs/fixed_probabilities.md` | Calibration and assumptions for the fixed phase-3 parameters. |
| `docs/phase3_results.md` | Validation and comparative results for all 27 profiles. |
| `docs/phase4_indices.md` | Canonical phase-4 BoP metrics, output tables and independent validation. |
| `docs/phase4_presentation.md` | Final three-slide phase-4 selection, speaking points and generated artifacts. |
| `docs/phase5_protocol.md` | Validated complete-trajectory sampling, annotation grids, robustness checks and outputs. |
| `docs/phase5_implementation_plan.md` | Proposed local/cluster script split and files exchanged for phase 5. |
| `docs/llm_digital_humanities.md` | Critical and reproducible use of local LLMs in digital humanities; phase-5 protocol and sources. |
| `docs/future_improvements.md` | Deferred improvements: extraction schema, portability, mechanics and trajectory analysis. |
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
3. **Profile compilation** (phase 3, done for LW01): all 27 matrices contain 352 nodes
   and 602 edges and pass the independent structural and absorption checks. The fixed
   combat probability is calibrated at `0.833`; the neutral profile reaches `Win` with
   probability `0.119811`, and the complete design ranges from `0.054397` to `0.258347`.
4. **BoP indices** (done for LW01): the selected local and global structural indices are
   calculated and independently validated for all 27 profiles. A concise three-slide
   presentation package and an optional key-number table are generated reproducibly.
5. **LLM trajectory analysis**: the protocol is fixed; sample 42 controlled complete
   paths and apply a structured, human-checked Qwen3.6-27B annotation to their stories.
6. **Generalization**: apply the reusable pipeline to another book or corpus.

## Setup

Python project managed with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python scripts/1.1_parse_for_edge_extraction.py --book LW01
uv run python scripts/1.2_parse_node.py --book LW01
uv run python scripts/3.0_generate_profiles.py
uv run python scripts/3.1_compile_w.py --book LW01 \
  --profile neutral_neutral_neutral
uv run python scripts/tests/test_3_1_compile_w.py --book LW01 \
  --all-profiles
uv run python scripts/3.2_calibrate_combat.py --book LW01
uv run python scripts/tests/test_3_2_calibrate_combat.py --book LW01
uv run python scripts/3.3_summarize_profiles.py --book LW01
uv run python scripts/tests/test_3_3_summarize_profiles.py --book LW01
uv run python scripts/utils/extract_project_aon_layout.py --book LW01
uv run python scripts/tests/test_extract_project_aon_layout.py --book LW01
uv run python scripts/4.0_visualize_graph.py --book LW01 \
  --profile neutral_neutral_neutral
uv run python scripts/tests/test_4_0_visualize_graph.py --book LW01 \
  --profile neutral_neutral_neutral
uv run python scripts/4.1_compute_bop_indices.py --book LW01
uv run python scripts/tests/test_4_1_compute_bop_indices.py --book LW01
uv run python scripts/4.2_summarize_bop_indices.py --book LW01
uv run python scripts/tests/test_4_2_summarize_bop_indices.py --book LW01
uv run python scripts/4.3_build_bop_presentation.py --book LW01
uv run python scripts/tests/test_4_3_build_bop_presentation.py --book LW01
```

The same commands accept another Lone Wolf identifier, such as `--book LW02`, provided
its HTML sections follow the repository path convention described in the global plan.
