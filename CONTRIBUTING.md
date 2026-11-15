# Contributing to PayloadOfAllDucks

Thanks for your interest! POAD is a focused, offline payload **generator** for
authorised security testing and CTFs. Contributions that keep it lightweight,
deterministic, and honest are very welcome.

## Scope

In scope: new payload templates/packs, new or improved vulnerability modules,
encoding transforms, importers, UX, tests, docs.

Out of scope (by design): network scanning/attacking, exploitation automation,
reverse shells / destructive payloads in the default library, AI integrations,
telemetry, web dashboards, or anything that contacts a target.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,rich]"
pytest
```

## Guidelines

- **Python 3.10+**, standard-library-first. New runtime dependencies need a
  strong justification; `rich` is optional and must never be required.
- **Determinism**: identical inputs + version + library must yield identical
  output. Avoid unordered sets in output paths; de-dupe preserving first-seen
  order.
- **Templates are data, not code.** Never introduce `eval`/`exec`/shell execution
  of template or imported content. Use `<<POAD_NAME>>` placeholders.
- **Encoding correctness**: add byte-exact tests for any new transform. Never
  URL-decode-then-re-encode user input. Preserve braces, `+`, backslashes, quotes.
- **Honesty**: don't fabricate payload counts or claim filter bypasses. If a
  technique can't be a single Burp Sniper string, say so in the module output.
- **Type hints** where they help; keep abstractions minimal.

## Adding a template pack

1. Create JSON under `poad/templates/<category>/` (see existing packs).
2. Each template needs a stable `id`, `name`, `category`, and `template`. Declare
   every `<<POAD_X>>` placeholder in `required`.
3. Run `poad templates validate <file>` and add/extend tests.

## Adding a module

1. Subclass `BaseModule` in `poad/modules/`, declare `options()` and `build()`.
2. Register it and add it to `poad/modules/__init__.py`.
3. Set compatible transforms per unit; raw-only where encoding would corrupt
   syntax (SSTI, XXE).
4. Add tests covering context filtering, validation, and determinism.

## Tests & PRs

- Run `pytest` (all tests must pass) and `poad doctor` before opening a PR.
- Keep commits focused; describe behaviour changes in `CHANGELOG.md`.
- By contributing you agree your work is released under the project's MIT License.
