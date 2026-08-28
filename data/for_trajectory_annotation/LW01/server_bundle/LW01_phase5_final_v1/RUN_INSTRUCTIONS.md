# Phase 5 cluster bundle

This directory is self-contained. It requires Python 3.12, a compatible recent vLLM
installation, access to the configured Qwen model and one CUDA GPU with sufficient memory.

Validate the transferred bundle without loading vLLM:

```bash
python run_phase5.py --bundle-dir . --output-dir outputs/run --validate-only
```

Run the bundle:

```bash
python run_phase5.py --bundle-dir . --output-dir outputs/run
```

Resume after an interrupted job:

```bash
python run_phase5.py --bundle-dir . --output-dir outputs/run --resume
```

Replace `outputs/run` consistently with a stable run-specific name if desired. Transfer
the complete output directory back to the local project. Do not edit JSONL files on the
cluster. Invalid or truncated model outputs are preserved in `quarantine.jsonl`.
