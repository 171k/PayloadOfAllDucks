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

    modules = list(iter_modules())
    try:
        while True:
            print()
            print(banner(unicode=settings.get("unicode_banner", True)))
            print()
            for i, mod in enumerate(modules, start=1):
                print(f"[{i}] {mod.title}")
            print(f"[{len(modules)+1}] Custom Payload Templates (import/validate)")
            print()
            print(f"[{len(modules)+2}] Browse Payload Library")
            print(f"[{len(modules)+3}] Presets")
            print(f"[{len(modules)+4}] Settings")
            print("[0] Exit")
            print()
            try:
                choice = _ask("Select category", default="")
            except _Back:
                continue
            if choice in ("0", "q", "quit", "exit"):
                raise _Quit()
            if not choice.isdigit():
                continue
            n = int(choice)
            try:
                if 1 <= n <= len(modules):
                    _run_category(modules[n - 1], console)
                elif n == len(modules) + 1:
                    _custom_templates_menu(console)
                elif n == len(modules) + 2:
                    _browse_library(console)
                elif n == len(modules) + 3:
                    _presets_menu(console)
                elif n == len(modules) + 4:
                    _settings_menu(console)
            except _Back:
                continue
    except _Quit:
        print("\nGoodbye. 🦆" if settings.get("unicode_banner", True) else "\nGoodbye.")
        return 0


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
