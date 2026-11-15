"""Exporters for generated payloads.

The default TXT export is deliberately minimal: UTF-8, exactly one payload per
line, LF line endings, no banner/comments/numbering, no duplicates, no trailing
whitespace added by the generator. It is directly loadable as a Burp Intruder
"Simple list".
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from poad.core.generator import GenerationResult
from poad.core.validation import is_valid_line


class ExportError(Exception):
    pass


def render_txt(result: GenerationResult) -> str:
    """Return the TXT body (LF-terminated lines, no trailing blank line issues)."""
    lines = []
    for rec in result.records:
        if not is_valid_line(rec.value):  # pragma: no cover - already filtered
            raise ExportError(f"Refusing to export malformed line: {rec.value!r}")
        lines.append(rec.value)
    # One payload per line; final newline after the last payload is conventional
    # for wordlists and does NOT create an empty trailing payload in Burp.
    return "\n".join(lines) + ("\n" if lines else "")


def render_json(result: GenerationResult, *, meta: dict | None = None) -> str:
    payload = {
        "meta": meta or {},
        "stats": result.stats,
        "payloads": [
            {
                "value": r.value,
                "family": r.family,
                "template_id": r.template_id,
                "transform": r.transform,
                "note": r.note,
            }
            for r in result.records
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_csv(result: GenerationResult) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["value", "family", "template_id", "transform", "note"])
    for r in result.records:
        writer.writerow([r.value, r.family, r.template_id, r.transform, r.note or ""])
    return buf.getvalue()


def render_markdown(result: GenerationResult, *, title: str = "POAD payloads", meta: dict | None = None) -> str:
    out = [f"# {title}", ""]
    if meta:
        for key, value in meta.items():
            out.append(f"- **{key}**: {value}")
        out.append("")
    out.append("## Statistics")
    out.append("")
    for key, value in result.stats.items():
        out.append(f"- {key}: {value}")
    out.append("")
    out.append("## Payloads")
    out.append("")
    out.append("```text")
    for r in result.records:
        out.append(r.value)
    out.append("```")
    out.append("")
    return "\n".join(out)


RENDERERS = {
    "txt": render_txt,
    "json": render_json,
    "csv": render_csv,
    "md": render_markdown,
    "markdown": render_markdown,
}


def render(result: GenerationResult, fmt: str, *, title: str = "POAD payloads", meta: dict | None = None) -> str:
    fmt = fmt.lower()
    if fmt == "txt":
        return render_txt(result)
    if fmt == "json":
        return render_json(result, meta=meta)
    if fmt == "csv":
        return render_csv(result)
    if fmt in ("md", "markdown"):
        return render_markdown(result, title=title, meta=meta)
    raise ExportError(f"Unknown export format: {fmt!r}")


def write_output(
    result: GenerationResult,
    path: str | Path,
    *,
    fmt: str = "txt",
    overwrite: bool = False,
    title: str = "POAD payloads",
    meta: dict | None = None,
) -> Path:
    """Render and write ``result`` to ``path``. Refuses to overwrite by default."""
    out_path = Path(path)
    if out_path.exists() and not overwrite:
        raise ExportError(
            f"Output file already exists: {out_path}. "
            "Use --force/overwrite to replace it."
        )
    body = render(result, fmt, title=title, meta=meta)
    # newline="" keeps our LF line endings intact on Windows (no CRLF rewrite).
    out_path.write_text(body, encoding="utf-8", newline="")
    return out_path
