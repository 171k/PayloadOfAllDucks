# POAD examples

A tiny, **deliberately vulnerable**, **local-only** lab for practising with the
wordlists POAD generates. Standard library only (no Flask/deps).

> ⚠️ For education and authorised practice on your own machine only. The lab binds
> to `127.0.0.1`, intentionally reads any file path you give it, and must never be
> exposed or run in production.

## 1. Start the lab

```bash
python3 examples/vuln_lab.py
# [lab] Deliberately vulnerable LFI lab on http://127.0.0.1:8099
```

It exposes `GET /?page=<path>` and naively reads `<path>` relative to the
`examples/` directory, a classic path-traversal/LFI sink.

Baseline (works, intended file):

```bash
curl "http://127.0.0.1:8099/?page=secret_flag.txt"
# POAD{this_is_a_demo_flag_for_the_local_lab}
```

## 2. Generate a wordlist with POAD

```bash
poad generate lfi --file secret_flag.txt --os linux --depth 4 -e all -o payloadlist.txt
```

Or target a system file to practise traversal out of the webroot:

```bash
poad generate lfi --file /etc/hostname --os linux --depth 6 -o payloadlist.txt
```

## 3. Try the payloads

Load `payloadlist.txt` into **Burp Intruder** (Sniper, Simple list) against the
`page` parameter, or loop with curl for a quick local check:

```bash
while IFS= read -r p; do
  printf '%s -> ' "$p"
  curl -s "http://127.0.0.1:8099/?page=$p" | head -c 60
  echo
done < payloadlist.txt
```

Because this lab decodes once and reads relative to `examples/`, the plain and
single-URL-encoded traversal variants are the ones that resolve here; other
encodings in the list are there for targets that decode differently. That is the
whole point. POAD gives you the spread of variants so you can see which the
target's parser accepts.

## 4. Burp encoding reminder

For the pre-encoded entries (`..%2f`, `..%252f`), disable Burp's
"URL-encode these characters" (uncheck `%`) so Burp does not turn `%2f` into
`%252f`. See the main README's *Encoding & Burp Intruder setup* section.
