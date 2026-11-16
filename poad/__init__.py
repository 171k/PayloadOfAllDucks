"""PayloadOfAllDucks (POAD) - context-aware offline payload wordlist generator.

POAD generates customised security-testing wordlists (e.g. for Burp Suite
Intruder) from user-selected vulnerability categories and context. It is an
entirely offline, deterministic generator: it never contacts or attacks a
target, requires no AI, and performs no network access during generation.

The user is responsible for only testing generated payloads against systems
they are authorised to test.
"""

__version__ = "0.2.1"
__app_name__ = "PayloadOfAllDucks"
__cli_name__ = "poad"

# Placeholder token namespace used inside payload templates. These are chosen so
# they never collide with literal payload characters (braces, slashes, quotes).
PLACEHOLDER_PREFIX = "<<POAD_"
PLACEHOLDER_SUFFIX = ">>"

__all__ = [
    "__version__",
    "__app_name__",
    "__cli_name__",
    "PLACEHOLDER_PREFIX",
    "PLACEHOLDER_SUFFIX",
]
