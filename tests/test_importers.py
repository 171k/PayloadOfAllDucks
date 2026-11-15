"""Importer tests."""

from __future__ import annotations

from poad.importers import payloadsallthethings as patt
from poad.importers import plaintext


def test_plaintext_import_dedup_and_skip(tmp_path):
    wl = tmp_path / "wl.txt"
    wl.write_text("a\n\nb\n# comment\na\nc\n", encoding="utf-8")
    pack, stats = plaintext.import_wordlist(wl, "lfi")
    values = [t.template for t in pack.templates]
    assert values == ["a", "b", "c"]
    assert stats.imported == 3
    assert stats.duplicates == 1
    assert stats.skipped_blank == 1


def test_plaintext_import_is_data_not_code(tmp_path):
    # A line that looks like code is stored verbatim as a template, never executed.
    wl = tmp_path / "wl.txt"
    wl.write_text("__import__('os').system('echo pwned')\n", encoding="utf-8")
    pack, _ = plaintext.import_wordlist(wl, "lfi")
    assert pack.templates[0].template == "__import__('os').system('echo pwned')"
    assert pack.templates[0].source.startswith("imported")


def test_patt_categorisation(tmp_path):
    base = tmp_path / "PayloadsAllTheThings"
    (base / "Directory Traversal" / "Intruder").mkdir(parents=True)
    (base / "Directory Traversal" / "Intruder" / "deep.txt").write_text(
        "../../etc/passwd\n..%2fetc%2fpasswd\n", encoding="utf-8"
    )
    (base / "SQL Injection").mkdir(parents=True)
    (base / "SQL Injection" / "payloads.txt").write_text("' OR 1=1-- -\n", encoding="utf-8")
    (base / "Unknown Thing").mkdir(parents=True)
    (base / "Unknown Thing" / "x.txt").write_text("whatever\n", encoding="utf-8")

    packs, stats = patt.import_patt(base)
    assert "lfi" in packs
    assert "sqli" in packs
    assert stats.files_skipped_uncategorised == 1
    assert packs["lfi"].license == "MIT"
    assert "PayloadsAllTheThings" in packs["lfi"].attribution


def test_patt_imported_pack_validates(tmp_path):
    from poad.core import template_engine
    base = tmp_path / "patt"
    (base / "XSS Injection").mkdir(parents=True)
    (base / "XSS Injection" / "x.txt").write_text("<script>alert(1)</script>\n", encoding="utf-8")
    packs, _ = patt.import_patt(base)
    data = template_engine.pack_to_dict(packs["xss"])
    # Round-trips through strict validation without error.
    template_engine.pack_from_dict(data)
