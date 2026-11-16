"""Command-line interface for POAD.

Supports both an interactive menu (no arguments) and fully scriptable
subcommands. Non-interactive mode never blocks for input: missing required
options produce a helpful error and a non-zero exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from poad import __app_name__, __version__, config
from poad.core import exporter, generator, template_engine
from poad.core.template_engine import TemplateError
from poad.modules import base as modbase
from poad.modules import get_module, iter_modules
from poad.ui import Console


# --------------------------------------------------------------------------
# Library loading
# --------------------------------------------------------------------------

def load_library():
    return template_engine.load_library(config.user_templates_dir())


def _lib():
    """Return just the template library (ignoring load warnings)."""
    lib, _ = load_library()
    return lib


# --------------------------------------------------------------------------
# Shared generation helper
# --------------------------------------------------------------------------

def _build_and_generate(module, ctx, library, *, encoding, max_payloads, sort):
    build = module.build(ctx, library)
    enc = modbase.resolve_encoding(encoding)
    result = generator.generate(
        build.units, encodings=enc, max_payloads=max_payloads, sort=sort
    )
    return build, result


def _print_summary(console: Console, module, build, result, *, output: str | None,
                   fmt: str) -> None:
    unicode_ok = config.load_settings().get("unicode_banner", True)
    duck = " 🦆" if unicode_ok and _unicode_ok() else ""
    console.print("")
    console.print(f"{__app_name__}{duck}", style="bold")
    console.print("")
    for key, value in build.info.items():
        console.print(f"{key}: {value}")
    console.print("")
    stats = result.stats
    console.print(f"Templates loaded: {stats['templates_loaded']}")
    console.print(f"Variants generated: {stats['variants_generated']}")
    console.print(f"Duplicates removed: {stats['duplicates_removed']}")
    if stats.get("skipped_invalid"):
        console.print(f"Skipped (invalid for TXT): {stats['skipped_invalid']}")
    console.print(f"Final payloads: {stats['final_payloads']}")
    console.print("")
    if output is not None:
        console.print(f"Output: {output}")
        fmt_label = "Burp Intruder Simple List" if fmt == "txt" else fmt.upper()
        console.print(f"Format: {fmt_label}")
        console.print("")
    for warn in result.warnings:
        console.warn(warn)
    for note in build.notes:
        console.print(f"note: {note}")
    if result.stats["final_payloads"] == 0:
        console.warn("No payloads generated for this selection.")
    else:
        console.success("Completed successfully.")


def _unicode_ok() -> bool:
    from poad.ui import supports_unicode
    return supports_unicode()


# --------------------------------------------------------------------------
# generate / preview
# --------------------------------------------------------------------------

def _add_module_arguments(parser: argparse.ArgumentParser, module) -> None:
    for opt in module.options():
        flag = "--" + opt.name.replace("_", "-")
        help_text = opt.help
        if opt.example:
            help_text = f"{help_text} (e.g. {opt.example})"
        # Escape literal '%' so argparse's help formatting (help % params) is safe.
        kwargs: dict[str, Any] = {"dest": opt.name, "help": help_text.replace("%", "%%")}
        if opt.type == "flag":
            kwargs["action"] = "store_true"
            kwargs["default"] = False
        elif opt.type == "int":
            kwargs["type"] = int
            if opt.default is not None:
                kwargs["default"] = opt.default
        elif opt.type == "choice":
            if opt.choices:
                kwargs["choices"] = list(opt.choices)
            if opt.default is not None and not opt.required:
                kwargs["default"] = opt.default
        else:  # str or multichoice
            if opt.default is not None and opt.type != "multichoice":
                kwargs["default"] = opt.default
        if opt.required:
            kwargs["required"] = True
        parser.add_argument(flag, **kwargs)


def _ctx_from_namespace(module, ns) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    for opt in module.options():
        if hasattr(ns, opt.name):
            ctx[opt.name] = getattr(ns, opt.name)
    return ctx


def cmd_generate(argv: list[str], *, preview: bool, console: Console) -> int:
    category = next((tok for tok in argv if not tok.startswith("-")), None)
    if category is None:
        console.error("generate requires a CATEGORY (try: poad list)")
        return 2
    module = get_module(category)
    if module is None:
        console.error(f"Unknown category: {category}")
        _print_category_hint(console)
        return 2

    prog = f"poad {'preview' if preview else 'generate'} {module.key}"
    parser = argparse.ArgumentParser(prog=prog, description=module.summary)
    parser.add_argument("category", help="vulnerability category")
    settings = config.load_settings()
    if not preview:
        parser.add_argument("-o", "--output", default="payloadlist.txt",
                            help="output file (default: payloadlist.txt)")
        parser.add_argument("-f", "--format", default="txt",
                            choices=["txt", "json", "csv", "md", "markdown"],
                            help="export format (default: txt)")
        parser.add_argument("--force", action="store_true",
                            help="overwrite an existing output file")
        parser.add_argument("--save-preset", metavar="NAME",
                            help="save these settings as a reusable preset")
    else:
        parser.add_argument("--limit", type=int, default=40,
                            help="max payloads to show (default: 40)")
    parser.add_argument("-e", "--encoding", default="all",
                        help="encoding selection: all|raw|url|double|html or "
                             "comma-separated transform names (default: all)")
    parser.add_argument("--max-payloads", type=int,
                        default=settings.get("max_payloads", 50000),
                        help="hard cap on generated payloads")
    parser.add_argument("--sort", action="store_true",
                        help="sort output alphabetically (default: relevance order)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="suppress the summary (still writes the file)")
    _add_module_arguments(parser, module)

    try:
        ns = parser.parse_args(argv)
    except SystemExit as exc:  # argparse printed help/error; surface the code
        return int(exc.code or 0)
    ctx = _ctx_from_namespace(module, ns)

    try:
        build, result = _build_and_generate(
            module, ctx, _lib(),
            encoding=ns.encoding, max_payloads=ns.max_payloads, sort=ns.sort,
        )
    except modbase.ModuleError as exc:
        console.error(str(exc))
        return 2
    except TemplateError as exc:
        console.error(f"template error: {exc}")
        return 2

    if preview:
        limit = max(0, ns.limit)
        shown = result.records[:limit]
        for rec in shown:
            print(rec.value)
        if not ns.quiet:
            total = result.stats["final_payloads"]
            console.print("")
            console.print(
                f"[preview] showing {len(shown)} of {total} payloads "
                f"(templates: {result.stats['templates_loaded']}, "
                f"duplicates removed: {result.stats['duplicates_removed']})"
            )
            for note in build.notes:
                console.print(f"note: {note}")
        return 0

    meta = dict(build.info)
    try:
        exporter.write_output(
            result, ns.output, fmt=ns.format, overwrite=ns.force,
            title=f"POAD {module.title}", meta=meta,
        )
    except exporter.ExportError as exc:
        console.error(str(exc))
        return 1

    if not ns.quiet:
        _print_summary(console, module, build, result, output=ns.output, fmt=ns.format)

    if ns.save_preset:
        _save_preset_from_ctx(console, module, ctx, ns)

    return 0


def _save_preset_from_ctx(console: Console, module, ctx, ns) -> None:
    from poad import presets
    # Drop None/default-empty values to keep presets tidy.
    clean = {k: v for k, v in ctx.items() if v not in (None, "", False)}
    preset = presets.Preset(
        name=ns.save_preset,
        category=module.key,
        options=clean,
        encoding=ns.encoding,
        fmt=ns.format,
        max_payloads=ns.max_payloads,
    )
    try:
        path = presets.save_preset(preset)
        console.success(f"Saved preset '{ns.save_preset}' -> {path}")
    except presets.PresetError as exc:
        console.error(str(exc))


# --------------------------------------------------------------------------
# list
# --------------------------------------------------------------------------

def _print_category_hint(console: Console) -> None:
    console.print("Available categories:")
    for mod in iter_modules():
        console.print(f"  {mod.key:<8} {mod.title}")


def cmd_list(args, console: Console) -> int:
    if args.category:
        module = get_module(args.category)
        if module is None:
            console.error(f"Unknown category: {args.category}")
            _print_category_hint(console)
            return 2
        console.print(f"{module.key}: {module.title}")
        console.print(module.summary)
        console.print("")
        if module.key == "ssti":
            engines = module.engines(_lib())
            console.print("Engines: " + ", ".join(engines))
            console.print("")
        console.print("Options:")
        for opt in module.options():
            req = " (required)" if opt.required else ""
            choices = f" [{', '.join(opt.choices)}]" if opt.choices else ""
            default = f" (default: {opt.default})" if opt.default not in (None, "", False) else ""
            console.print(f"  --{opt.name.replace('_','-'):<16} {opt.help}{choices}{default}{req}")
        return 0

    console.print("Vulnerability categories:")
    for i, mod in enumerate(iter_modules(), start=1):
        console.print(f"  [{i}] {mod.key:<8} {mod.title} - {mod.summary}")
    return 0


# --------------------------------------------------------------------------
# templates
# --------------------------------------------------------------------------

def cmd_templates(args, console: Console) -> int:
    if args.templates_cmd == "list":
        lib = _lib()
        cat_filter = getattr(args, "category", None)
        templates = lib.by_category(cat_filter) if cat_filter else lib.all()
        for tpl in sorted(templates, key=lambda t: (t.category, t.id)):
            console.print(f"{tpl.id:<34} {tpl.category:<18} {tpl.name}")
        console.print("")
        console.print(f"{len(templates)} template(s).")
        return 0
    if args.templates_cmd == "show":
        lib = _lib()
        tpl = lib.get(args.template_id)
        if tpl is None:
            console.error(f"Template not found: {args.template_id}")
            return 2
        console.print(json.dumps(template_engine.template_to_dict(tpl), indent=2,
                                 ensure_ascii=False))
        console.print("")
        console.print(f"Required variables: {', '.join(tpl.required) or '(none)'}")
        console.print(f"Placeholders in template: {', '.join(sorted(tpl.tokens())) or '(none)'}")
        return 0
    if args.templates_cmd == "validate":
        try:
            pack = template_engine.load_pack_file(args.file)
        except TemplateError as exc:
            console.error(f"Invalid template pack: {exc}")
            return 1
        console.success(
            f"Valid pack '{pack.name}' ({pack.category}): {len(pack.templates)} template(s)."
        )
        return 0
    console.error("Unknown templates subcommand")
    return 2


# --------------------------------------------------------------------------
# presets
# --------------------------------------------------------------------------

def cmd_presets(args, console: Console) -> int:
    from poad import presets
    if args.presets_cmd == "list":
        names = presets.list_presets()
        if not names:
            console.print("No presets saved.")
            return 0
        for name in names:
            try:
                p = presets.load_preset(name)
                console.print(f"  {name:<20} category={p.category} encoding={p.encoding}")
            except presets.PresetError:
                console.print(f"  {name:<20} (corrupted)")
        return 0
    if args.presets_cmd == "run":
        try:
            preset = presets.load_preset(args.name)
        except presets.PresetError as exc:
            console.error(str(exc))
            return 2
        module = get_module(preset.category)
        if module is None:
            console.error(f"Preset references unknown category: {preset.category}")
            return 2
        output = args.output or "payloadlist.txt"
        try:
            build, result = _build_and_generate(
                module, dict(preset.options), _lib(),
                encoding=preset.encoding,
                max_payloads=preset.max_payloads or config.load_settings()["max_payloads"],
                sort=False,
            )
            exporter.write_output(result, output, fmt=preset.fmt,
                                  overwrite=args.force, title=f"POAD {module.title}",
                                  meta=dict(build.info))
        except (modbase.ModuleError, TemplateError, exporter.ExportError) as exc:
            console.error(str(exc))
            return 1
        _print_summary(console, module, build, result, output=output, fmt=preset.fmt)
        return 0
    if args.presets_cmd == "delete":
        if presets.delete_preset(args.name):
            console.success(f"Deleted preset '{args.name}'.")
            return 0
        console.error(f"Preset not found: {args.name}")
        return 2
    if args.presets_cmd == "save":
        console.error("Save a preset via: poad generate <category> ... --save-preset NAME")
        return 2
    console.error("Unknown presets subcommand")
    return 2


# --------------------------------------------------------------------------
# import
# --------------------------------------------------------------------------

def cmd_import(args, console: Console) -> int:
    from poad.importers import payloadsallthethings, plaintext

    if args.import_cmd == "wordlist":
        module = get_module(args.category)
        if module is None and args.category not in {m.key for m in iter_modules()}:
            console.error(f"Unknown category: {args.category}")
            return 2
        try:
            pack, stats = plaintext.import_wordlist(args.file, args.category)
        except OSError as exc:
            console.error(f"Cannot read wordlist: {exc}")
            return 1
        out = _write_user_pack(pack, args.category, args.name or Path(args.file).stem)
        console.success(
            f"Imported {stats.imported} payload(s) into category '{args.category}'."
        )
        console.print(
            f"  blanks skipped: {stats.skipped_blank}, "
            f"invalid skipped: {stats.skipped_invalid}, duplicates: {stats.duplicates}"
        )
        console.print(f"  saved: {out}")
        return 0

    if args.import_cmd == "patt":
        try:
            packs, stats = payloadsallthethings.import_patt(args.directory)
        except (NotADirectoryError, OSError) as exc:
            console.error(str(exc))
            return 1
        for category, pack in packs.items():
            _write_user_pack(pack, category, "payloadsallthethings")
        console.success("PayloadsAllTheThings import complete.")
        console.print(f"  files scanned: {stats.files_scanned}")
        console.print(f"  files imported: {stats.files_imported}")
        console.print(f"  uncategorised files skipped: {stats.files_skipped_uncategorised}")
        console.print(f"  payloads imported: {stats.payloads_imported}")
        console.print(f"  payloads skipped: {stats.payloads_skipped}")
        console.print(f"  duplicates removed: {stats.duplicates}")
        for cat, count in sorted(stats.per_category.items()):
            console.print(f"    {cat}: {count}")
        console.print(
            "  attribution: PayloadsAllTheThings (MIT) - "
            "https://github.com/swisskyrepo/PayloadsAllTheThings"
        )
        return 0

    console.error("Unknown import subcommand")
    return 2


def _write_user_pack(pack, category: str, name: str) -> Path:
    config.ensure_dirs()
    target_dir = config.user_templates_dir() / category
    target_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in name if c.isalnum() or c in "._-") or "pack"
    out = target_dir / f"{safe}.json"
    out.write_text(
        json.dumps(template_engine.pack_to_dict(pack), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out


# --------------------------------------------------------------------------
# doctor / version
# --------------------------------------------------------------------------

def cmd_doctor(args, console: Console) -> int:
    ok = True
    console.rule("POAD doctor")
    console.print(f"Version: {__version__}")
    console.print(f"Python: {sys.version.split()[0]}")
    console.print(f"Config dir: {config.config_dir()}")
    try:
        lib, warnings = load_library()
        console.success(f"Template library loaded: {len(lib)} templates.")
        for cat in lib.categories():
            console.print(f"  {cat}: {len(lib.by_category(cat))}")
        for w in warnings:
            console.warn(w)
    except TemplateError as exc:
        console.error(f"Template library failed to load: {exc}")
        ok = False

    # Smoke-test each module with a minimal valid context.
    smoke = {
        "lfi": {"file": "/etc/passwd", "os": "linux", "depth": 2},
        "ssti": {"engine": "jinja2", "mode": "detection"},
        "sqli": {"dbms": "mysql", "context": "string", "mode": "detection"},
        "xss": {"context": "html"},
        "cmdi": {"os": "linux"},
        "ssrf": {"host": "127.0.0.1"},
        "xxe": {"mode": "detection"},
    }
    lib2, _ = load_library()
    for mod in iter_modules():
        ctx = smoke.get(mod.key, {})
        try:
            build = mod.build(ctx, lib2)
            res = generator.generate(build.units, encodings="all", max_payloads=1000)
            console.print(f"  module {mod.key:<6} OK ({res.stats['final_payloads']} payloads)")
        except Exception as exc:  # pragma: no cover - doctor reports, never raises
            console.error(f"  module {mod.key} FAILED: {exc}")
            ok = False

    console.print("")
    if ok:
        console.success("All checks passed.")
        return 0
    console.error("Some checks failed.")
    return 1


def cmd_version(args, console: Console) -> int:
    console.print(f"{__app_name__} (poad) {__version__}")
    console.print(f"Python {sys.version.split()[0]} on {sys.platform}")
    console.print("Offline payload wordlist generator - no network, no AI.")
    return 0


# --------------------------------------------------------------------------
# argument parser (non-dynamic subcommands)
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="poad",
        description="PayloadOfAllDucks - context-aware offline payload wordlist generator.",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="list vulnerability categories")
    p_list.add_argument("category", nargs="?", help="show options for one category")

    p_tpl = sub.add_parser("templates", help="inspect the template library")
    tpl_sub = p_tpl.add_subparsers(dest="templates_cmd", required=True)
    t_list = tpl_sub.add_parser("list", help="list templates")
    t_list.add_argument("category", nargs="?", help="filter by category")
    t_show = tpl_sub.add_parser("show", help="show one template")
    t_show.add_argument("template_id")
    t_val = tpl_sub.add_parser("validate", help="validate a template pack file")
    t_val.add_argument("file")

    p_pre = sub.add_parser("presets", help="manage saved presets")
    pre_sub = p_pre.add_subparsers(dest="presets_cmd", required=True)
    pre_sub.add_parser("list", help="list presets")
    pr_run = pre_sub.add_parser("run", help="regenerate from a preset")
    pr_run.add_argument("name")
    pr_run.add_argument("-o", "--output", help="output file (default: payloadlist.txt)")
    pr_run.add_argument("--force", action="store_true", help="overwrite existing output")
    pr_save = pre_sub.add_parser("save", help="(use generate --save-preset)")
    pr_save.add_argument("name")
    pr_del = pre_sub.add_parser("delete", help="delete a preset")
    pr_del.add_argument("name")

    p_imp = sub.add_parser("import", help="import external wordlists/packs")
    imp_sub = p_imp.add_subparsers(dest="import_cmd", required=True)
    i_wl = imp_sub.add_parser("wordlist", help="import a plaintext wordlist")
    i_wl.add_argument("file")
    i_wl.add_argument("--category", required=True, help="target category")
    i_wl.add_argument("--name", help="pack name (default: file stem)")
    i_patt = imp_sub.add_parser("patt", help="import a local PayloadsAllTheThings checkout")
    i_patt.add_argument("directory")

    sub.add_parser("doctor", help="check installation and library integrity")
    sub.add_parser("version", help="print version information")
    return parser


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    settings = config.load_settings()
    console = Console(use_rich=settings.get("use_rich", True))

    if not argv:
        from poad.menu import run_interactive
        return run_interactive(console)

    cmd = argv[0]

    # Dynamic subcommands (module-specific options) are parsed separately.
    if cmd in ("generate", "gen"):
        return cmd_generate(argv[1:], preview=False, console=console)
    if cmd == "preview":
        return cmd_generate(argv[1:], preview=True, console=console)

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse already printed a message
        return int(exc.code or 0)

    if getattr(args, "version", False) or args.command == "version":
        return cmd_version(args, console)
    if args.command == "list":
        return cmd_list(args, console)
    if args.command == "templates":
        return cmd_templates(args, console)
    if args.command == "presets":
        return cmd_presets(args, console)
    if args.command == "import":
        return cmd_import(args, console)
    if args.command == "doctor":
        return cmd_doctor(args, console)

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
