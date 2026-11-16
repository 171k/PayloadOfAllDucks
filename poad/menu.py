"""Interactive, keyboard-only menu.

Uses numbered selections (robust everywhere, no special terminal support needed)
with sensible defaults and input validation. In a non-interactive shell it prints
the banner and usage hint instead of blocking for input. Ctrl+C exits cleanly.
"""

from __future__ import annotations

import sys
from typing import Any

from poad import config
from poad.core import exporter
from poad.modules import get_module, iter_modules
from poad.ui import Console, banner


class _Back(Exception):
    """Raised to return to the previous menu."""


class _Quit(Exception):
    """Raised to exit the program."""


def _raw_input(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError as exc:
        raise _Quit() from exc
    except KeyboardInterrupt:
        print()
        raise _Quit()


def _ask(prompt: str, *, default: str | None = None) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    value = _raw_input(f"{prompt}{suffix}: ").strip()
    if value.lower() in ("b", "back"):
        raise _Back()
    if value == "" and default is not None:
        return str(default)
    return value


def _ask_int(prompt: str, *, default: int) -> int:
    while True:
        raw = _ask(prompt, default=str(default))
        try:
            return int(raw)
        except ValueError:
            print("  Please enter a whole number.")


def _ask_choice(prompt: str, choices: list[str], *, default: str | None = None) -> str:
    print(prompt)
    for i, choice in enumerate(choices, start=1):
        marker = " (default)" if choice == default else ""
        print(f"  [{i}] {choice}{marker}")
    while True:
        raw = _ask("Select", default=default)
        if raw in choices:
            return raw
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1]
        print("  Invalid choice.")


def _ask_multichoice(prompt: str, choices: list[str], *, default: list[str]) -> list[str]:
    print(prompt + " (comma-separated numbers, blank = all)")
    for i, choice in enumerate(choices, start=1):
        print(f"  [{i}] {choice}")
    raw = _ask("Select", default="all")
    if raw in ("", "all"):
        return list(default)
    picked: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= len(choices):
            picked.append(choices[int(part) - 1])
        elif part in choices:
            picked.append(part)
    return picked or list(default)


def _ask_flag(prompt: str, *, default: bool = False) -> bool:
    d = "y" if default else "n"
    raw = _ask(f"{prompt} (y/n)", default=d).lower()
    return raw in ("y", "yes", "true", "1")


def _collect_options(module, console: Console) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for opt in module.options():
        if not opt.applies(ctx):
            continue
        prompt = opt.prompt or opt.help
        # Show a short hint (what the field is for, and an example) so prompts
        # like "Marker" or "Target file" are self-explanatory.
        hint = opt.help
        if opt.example:
            hint = f"{hint} (e.g. {opt.example})" if hint else f"e.g. {opt.example}"
        if hint and opt.prompt and opt.prompt != opt.help:
            print(f"  {hint}")
        if opt.type == "flag":
            ctx[opt.name] = _ask_flag(prompt, default=bool(opt.default))
        elif opt.type == "int":
            ctx[opt.name] = _ask_int(prompt, default=int(opt.default or 0))
        elif opt.type == "choice":
            choices = list(opt.choices) or _dynamic_choices(module, opt)
            ctx[opt.name] = _ask_choice(prompt, choices, default=opt.default)
        elif opt.type == "multichoice":
            default = list(opt.default or opt.choices)
            ctx[opt.name] = _ask_multichoice(prompt, list(opt.choices), default=default)
        else:
            value = _ask(prompt, default=opt.default)
            if opt.required and value == "":
                print("  This field is required.")
                return _collect_options(module, console)
            ctx[opt.name] = value
    return ctx


def _dynamic_choices(module, opt) -> list[str]:
    if module.key == "ssti" and opt.name == "engine":
        from poad.cli import load_library
        lib, _ = load_library()
        return module.engines(lib)
    return []


def _run_category(module, console: Console) -> None:
    from poad.cli import _build_and_generate, _print_summary

    console.rule(module.title)
    ctx = _collect_options(module, console)

    encoding = _ask_choice(
        "Encoding", ["all", "raw", "url", "double", "html"], default="all"
    )
    settings = config.load_settings()

    lib, _ = __import__("poad.cli", fromlist=["load_library"]).load_library()
    try:
        build, result = _build_and_generate(
            module, ctx, lib, encoding=encoding,
            max_payloads=settings["max_payloads"], sort=False,
        )
    except Exception as exc:  # noqa: BLE001 - surface any build error cleanly
        console.error(str(exc))
        return

    total = result.stats["final_payloads"]
    console.print("")
    console.print(f"Generated {total} payload(s). Preview:")
    for rec in result.records[:15]:
        print("  " + rec.value)
    if total > 15:
        console.print(f"  ... ({total - 15} more)")

    if total == 0:
        return
    if not _ask_flag("Write to file?", default=True):
        return
    output = _ask("Output file", default="payloadlist.txt")
    fmt = _ask_choice("Format", ["txt", "json", "csv", "md"], default="txt")
    try:
        exporter.write_output(result, output, fmt=fmt, overwrite=False,
                              title=f"POAD {module.title}", meta=dict(build.info))
    except exporter.ExportError:
        if _ask_flag(f"{output} exists. Overwrite?", default=False):
            exporter.write_output(result, output, fmt=fmt, overwrite=True,
                                  title=f"POAD {module.title}", meta=dict(build.info))
        else:
            console.warn("Not written.")
            return
    _print_summary(console, module, build, result, output=output, fmt=fmt)


def _browse_library(console: Console) -> None:
    from poad.cli import load_library
    lib, _ = load_library()
    console.rule("Payload Library")
    for cat in lib.categories():
        console.print(f"{cat}: {len(lib.by_category(cat))} templates")
    _ask("Press Enter to return", default="")


def _presets_menu(console: Console) -> None:
    from poad import presets
    console.rule("Presets")
    names = presets.list_presets()
    if not names:
        console.print("No presets saved. Use generate --save-preset NAME to create one.")
        _ask("Press Enter to return", default="")
        return
    for i, name in enumerate(names, start=1):
        console.print(f"  [{i}] {name}")
    raw = _ask("Run which preset? (number, or blank to return)", default="")
    if raw == "":
        return
    if raw.isdigit() and 1 <= int(raw) <= len(names):
        name = names[int(raw) - 1]
        from poad.cli import _build_and_generate, _print_summary
        from poad.cli import load_library
        preset = presets.load_preset(name)
        module = get_module(preset.category)
        if module is None:
            console.error("Preset references an unknown category.")
            return
        lib, _ = load_library()
        build, result = _build_and_generate(
            module, dict(preset.options), lib, encoding=preset.encoding,
            max_payloads=preset.max_payloads or config.load_settings()["max_payloads"],
            sort=False,
        )
        output = _ask("Output file", default="payloadlist.txt")
        try:
            exporter.write_output(result, output, fmt=preset.fmt, overwrite=True,
                                  title=f"POAD {module.title}", meta=dict(build.info))
            _print_summary(console, module, build, result, output=output, fmt=preset.fmt)
        except exporter.ExportError as exc:
            console.error(str(exc))


def _settings_menu(console: Console) -> None:
    console.rule("Settings")
    settings = config.load_settings()
    for key, value in settings.items():
        console.print(f"  {key} = {value}")
    console.print("")
    console.print("Editable: burp_mode, default_format, max_payloads, use_rich, unicode_banner")
    key = _ask("Setting to change (blank to return)", default="")
    if key == "" or key not in settings:
        return
    value = _ask(f"New value for {key}", default=str(settings[key]))
    # Coerce to the existing type.
    current = settings[key]
    if isinstance(current, bool):
        settings[key] = value.lower() in ("y", "yes", "true", "1")
    elif isinstance(current, int):
        try:
            settings[key] = int(value)
        except ValueError:
            console.error("Not a number.")
            return
    else:
        settings[key] = value
    config.save_settings(settings)
    console.success("Saved.")


def run_interactive(console: Console | None = None) -> int:
    console = console or Console()
    settings = config.load_settings()

    if not sys.stdin.isatty():
        print(banner(unicode=settings.get("unicode_banner", True)))
        print()
        print("Non-interactive shell detected. Use subcommands, e.g.:")
        print("  poad list")
        print("  poad generate lfi --file /flag/flag.txt --os linux --depth 8")
        print("  poad --help")
        return 0

    try:
        while True:
            print()
            print(banner(unicode=settings.get("unicode_banner", True)))
            print()
            print("[1] Payload list      - generate wordlists for Burp Intruder")
            print("[2] Exploit script    - build a request harness for a payload list")
            print("[3] RCE               - reverse shells, web shells, image polyglots")
            print()
            print("[4] Browse Payload Library")
            print("[5] Presets")
            print("[6] Settings")
            print("[0] Exit")
            print()
            try:
                choice = _ask("Select", default="")
            except _Back:
                continue
            if choice in ("0", "q", "quit", "exit"):
                raise _Quit()
            if not choice.isdigit():
                continue
            n = int(choice)
            try:
                if n == 1:
                    _payload_list_menu(console)
                elif n == 2:
                    _exploit_script_menu(console)
                elif n == 3:
                    _rce_menu(console)
                elif n == 4:
                    _browse_library(console)
                elif n == 5:
                    _presets_menu(console)
                elif n == 6:
                    _settings_menu(console)
            except _Back:
                continue
    except _Quit:
        print("\nGoodbye. 🦆" if settings.get("unicode_banner", True) else "\nGoodbye.")
        return 0


def _payload_list_menu(console: Console) -> None:
    """The former top menu: pick a vulnerability category to generate a wordlist."""
    modules = list(iter_modules())
    while True:
        print()
        console.rule("Payload list")
        for i, mod in enumerate(modules, start=1):
            print(f"[{i}] {mod.title}")
        print(f"[{len(modules)+1}] Custom Payload Templates (import/validate)")
        print("[0] Back")
        print()
        choice = _ask("Select category", default="")
        if choice in ("0", "", "b", "back"):
            return
        if not choice.isdigit():
            continue
        n = int(choice)
        try:
            if 1 <= n <= len(modules):
                _run_category(modules[n - 1], console)
            elif n == len(modules) + 1:
                _custom_templates_menu(console)
        except _Back:
            continue


def _custom_templates_menu(console: Console) -> None:
    from poad.cli import _write_user_pack
    from poad.core import template_engine
    from poad.importers import plaintext

    console.rule("Custom Templates")
    print("[1] Validate a template pack file")
    print("[2] Import a plaintext wordlist")
    choice = _ask("Select", default="")
    if choice == "1":
        path = _ask("Pack file path", default="")
        if not path:
            return
        try:
            pack = template_engine.load_pack_file(path)
            console.success(f"Valid pack '{pack.name}': {len(pack.templates)} templates.")
        except template_engine.TemplateError as exc:
            console.error(str(exc))
    elif choice == "2":
        path = _ask("Wordlist file path", default="")
        category = _ask("Category", default="lfi")
        if not path:
            return
        try:
            pack, stats = plaintext.import_wordlist(path, category)
            out = _write_user_pack(pack, category, __import__("pathlib").Path(path).stem)
            console.success(f"Imported {stats.imported} payloads -> {out}")
        except OSError as exc:
            console.error(str(exc))


# --------------------------------------------------------------------------
# Mode 2: Exploit script
# --------------------------------------------------------------------------

def _write_file(path: str, data, console: Console, *, binary: bool = False) -> bool:
    from pathlib import Path
    p = Path(path)
    if p.exists() and not _ask_flag(f"{path} exists. Overwrite?", default=False):
        console.warn("Not written.")
        return False
    if binary:
        p.write_bytes(data)
    else:
        p.write_text(data, encoding="utf-8", newline="\n")
    console.success(f"Wrote {p}")
    return True


def _exploit_script_menu(console: Console) -> None:
    from poad import exploit
    console.rule("Exploit script")
    print("Builds a standalone Python harness that sends a payload list at one")
    print("authorised target. POAD does not send the requests; you run the script.")
    print()
    print("  Put the marker FUZZ where each payload should go.")
    url = _ask("Target URL with FUZZ", default="http://TARGET/?page=FUZZ")
    wordlist = _ask("Payload wordlist path", default="payloadlist.txt")
    match = _ask("Match string to flag hits (blank = none)", default="")
    method = _ask_choice("HTTP method", ["GET", "POST"], default="GET")
    data = ""
    if method == "POST":
        data = _ask("POST body (include FUZZ)", default="")
    src = exploit.build_exploit_script(
        url=url, wordlist=wordlist, match=match, method=method, data=data
    )
    out = _ask("Output script file", default="exploit.py")
    if _write_file(out, src, console):
        print()
        print("Run it (authorised targets only):")
        print(f"  python3 {out}")
        print(f"  python3 {out} -u '{url}' -w {wordlist}"
              + (f" --match '{match}'" if match else ""))


# --------------------------------------------------------------------------
# Mode 3: RCE
# --------------------------------------------------------------------------

def _rce_menu(console: Console) -> None:
    console.rule("RCE")
    print("[1] Reverse shell one-liners")
    print("[2] Web shell (php / jsp / aspx)")
    print("[3] PHP-in-image polyglot (upload-filter bypass)")
    print("[0] Back")
    print()
    choice = _ask("Select method", default="")
    if choice == "1":
        _rce_revshell(console)
    elif choice == "2":
        _rce_webshell(console)
    elif choice == "3":
        _rce_polyglot(console)


def _rce_revshell(console: Console) -> None:
    from poad import rce
    console.rule("Reverse shell one-liners")
    os_name = _ask_choice("Target OS", ["linux", "windows"], default="linux")
    print("  LHOST = your listener IP. On Pwnbox/HTB:  ip -4 addr show tun0")
    lhost = _ask("LHOST", default="")
    lport = _ask("LPORT", default="4444")
    try:
        shells = rce.reverse_shells(lhost, lport, os_name)
    except Exception as exc:  # noqa: BLE001
        console.error(str(exc))
        return
    print()
    for i, s in enumerate(shells, 1):
        print(f"[{i}] {s.name} ({s.shell})")
        print("    " + s.payload)
    print()
    if _ask_flag("Write all one-liners to a file?", default=True):
        out = _ask("Output file", default="revshells.txt")
        _write_file(out, "\n".join(s.payload for s in shells) + "\n", console)
    print()
    print("Catch it from Pwnbox (start this BEFORE triggering the shell):")
    for line in rce.listener_commands(lport):
        print("  " + line)


def _rce_webshell(console: Console) -> None:
    from poad import rce
    console.rule("Web shell")
    lang = _ask_choice("Language", list(rce.WEBSHELL_LANGS), default="php")
    param = _ask("Command parameter name", default="cmd")
    try:
        fn, content = rce.webshell(lang, param=param)
    except Exception as exc:  # noqa: BLE001
        console.error(str(exc))
        return
    out = _ask("Output file", default=fn)
    if _write_file(out, content, console):
        print()
        print("Use it (authorised targets only):")
        for line in rce.webshell_commands("http://TARGET/uploads", param):
            print("  " + line)


def _rce_polyglot(console: Console) -> None:
    from poad import rce
    console.rule("PHP-in-image polyglot")
    img = _ask_choice("Image type", list(rce.POLYGLOT_IMAGES), default="png")
    param = _ask("Command parameter name", default="cmd")
    try:
        fn, content = rce.polyglot(img, param=param)
    except Exception as exc:  # noqa: BLE001
        console.error(str(exc))
        return
    out = _ask("Output file", default=fn)
    if _write_file(out, content, console, binary=True):
        print()
        print("A valid image that also contains PHP. It executes only if the server")
        print("treats it as PHP. Common triggers:")
        for line in rce.polyglot_commands(img, param):
            print("  " + line)
