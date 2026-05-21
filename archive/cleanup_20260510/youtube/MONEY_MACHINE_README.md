# Local Money Machine (8 Streams)

Production-oriented local pipeline for generating synchronized content artifacts using Ollama.

## Quick Start

1. Ensure Python is installed.
2. Ensure Ollama is running and your model is pulled.
3. Use config:
   - `pipeline_config.json` (editable)
   - `pipeline_config.example.json` (template)
4. Run commands:

```powershell
.\money-machine.cmd doctor --config pipeline_config.json
.\money-machine.cmd plan --config pipeline_config.json
.\money-machine.cmd run --config pipeline_config.json
.\money-machine.cmd run --config pipeline_config.json --streams S1,S3,S5
.\money-machine.cmd resume --config pipeline_config.json --run-id <run_id>
.\money-machine.cmd retry --config pipeline_config.json --run-id <run_id>
.\money-machine.cmd status --config pipeline_config.json --run-id <run_id>
```

## Artifacts

- Output root: `runs/<run_id>/`
- Per stream:
  - `outputs/` generated files (`.md`, `.txt`, `.html` based on config)
  - `progress.json` checkpoint state
  - `manifest.jsonl` generation log
- Run-level:
  - `run_summary.json`
  - `failures.json`

## Stream Modules

- `S1` YouTube Long-form
- `S2` YouTube Shorts
- `S3` TikTok/Reels Scripts
- `S4` SEO Blog Articles
- `S5` Email Newsletter Sequence
- `S6` Affiliate Offer Assets
- `S7` Digital Product Assets
- `S8` Repurposing/Distribution Pack

## Notes

- Model policy is fixed to local-first Ollama for v1.
- Existing one-off S1 scripts remain untouched for compatibility.
- Text output is normalized to ASCII-safe format by default.
- Prompts are file-based in `prompts/` and can be edited per stream:
  - `S1.prompt.txt` ... `S8.prompt.txt`
- Local starter topics are included in `data/topics_seed.json`.
