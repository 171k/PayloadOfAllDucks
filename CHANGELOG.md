# Changelog

All notable changes to PayloadOfAllDucks are documented here. This project
follows [Semantic Versioning](https://semver.org/) and the format of
[Keep a Changelog](https://keepachangelog.com/).

## [0.2.0] - 2026-11-16

Adds offensive artifact generation for authorised testing / CTFs. POAD still
never executes anything or contacts a target; it writes files and prints the
commands you run yourself.

### Added
- **Three top-level modes** in the interactive menu: Payload list, Exploit
  script, and RCE.
- **RCE module** (`poad rce ...`, opt-in, separate from the shell-free payload
  library):
  - `revshell` - reverse shell one-liners (bash, nc, python, perl, php, ruby,
    socat, PowerShell, nc.exe) with your LHOST/LPORT, plus the `nc -lvnp`
    catcher and Pwnbox `tun0` guidance.
  - `webshell` - readable PHP / JSP / ASPX command web shells.
  - `polyglot` - PHP-in-image (PNG/GIF) files that pass `getimagesize()` for
    upload-filter bypass, with trigger guidance.
- **Exploit script generator** (`poad exploit ...`) - emits a self-contained,
  stdlib-only Python request harness that fuzzes a `FUZZ` marker against one
  authorised target and ranks responses. POAD does not send the requests.
- New braille-duck banner (ASCII box fallback retained).
- Input hints/examples in interactive prompts and `--help` (e.g. the marker).

### Notes
- The base payload-generator library remains shell-free; reverse/web shells live
  only in the opt-in RCE mode.

## [0.1.0] - 2026-11-16

Initial release.

### Added
- Installable Python package (`pip install .`) with `poad` entry point and
  `python3 -m poad` support; Python 3.10+.
- Data-driven template engine with `<<POAD_NAME>>` placeholders (literal
  substitution, no `eval`/code execution) and strict pack validation.
- Deterministic transformation engine (separator/double/mixed-case/overlong URL
  encodings, full percent-encoding, HTML entities) with byte-exact tests.
- Generation pipeline: substitute → expand → transform → validate lines →
  de-duplicate → cap → deterministic order → export.
- Clean TXT exporter (Burp Intruder Simple list) plus JSON/CSV/Markdown exports.
- Vulnerability modules:
  - **LFI / Path Traversal** (Linux/Windows, depth & family control, encodings,
    prefix/suffix, null-byte, cross-platform).
  - **SSTI** (12 engines; detection/identification/context/file-read; expected
    results; honest unsupported-technique reporting).
  - **SQL Injection** (MySQL/PostgreSQL/SQLite/MSSQL/generic; context-aware;
    non-destructive).
  - **XSS** (HTML/attribute/JS/URL/SVG contexts; proof marker).
  - **Command Injection** (Linux/Windows shells; harmless default command).
  - **SSRF** (URL-parser/encoding variants from a user-supplied host; no default
    targets).
  - **XXE** (whole-document detection/file-read probes).
- Interactive, keyboard-only menu with ASCII/Unicode banner, defaults,
  validation, preview, graceful Ctrl+C, and non-interactive fallback.
- Saved presets (config-only JSON, schema-versioned, corruption-safe).
- Importers: plaintext wordlists and a local PayloadsAllTheThings checkout
  (data-only, attribution preserved, uncategorisable entries skipped).
- `poad doctor` installation/library self-check.
- Test suite (105 tests): transformations, LFI, SSTI, other modules, templates,
  export, CLI, importers, presets, custom packs, and security properties.
- README, LICENSE (MIT), CONTRIBUTING, and a local deliberately-vulnerable demo
  lab under `examples/`.

### Security
- Imported templates and wordlists are treated as data and never executed.
- No network access or telemetry during generation.
- Preset/import paths reject directory traversal; generation is hard-capped.
