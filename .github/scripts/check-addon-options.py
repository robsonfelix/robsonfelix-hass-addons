#!/usr/bin/env python3
"""Check that an add-on's options, schema and translations agree.

This exists because of a real case: PR #47 added three options translated for
English only, and fr.yaml had been missing four remote-control keys since
1.2.65. Nothing in the repository caught it -- the option simply rendered
without a name in the Home Assistant UI, in the user's language.

    python3 .github/scripts/check-addon-options.py claudecode
"""
import sys
from pathlib import Path

import yaml

failed = False


def error(msg):
    global failed
    failed = True
    print(f"::error::{msg}")


for addon in sys.argv[1:]:
    base = Path(addon)
    cfg = yaml.safe_load((base / "config.yaml").read_text(encoding="utf-8"))
    options = set(cfg.get("options") or {})
    schema = set(cfg.get("schema") or {})

    # every option needs a schema entry, and vice versa
    for k in sorted(options - schema):
        error(f"{addon}: '{k}' is in options but not in schema")
    for k in sorted(schema - options):
        # optional in the schema (? suffix) may have no default
        tipo = str((cfg.get("schema") or {}).get(k, ""))
        if not tipo.endswith("?"):
            error(f"{addon}: '{k}' is in schema but has no default in options")

    traducoes = sorted((base / "translations").glob("*.yaml"))
    if not traducoes:
        error(f"{addon}: no translations found")
    for t in traducoes:
        dados = yaml.safe_load(t.read_text(encoding="utf-8")) or {}
        chaves = set((dados.get("configuration") or {}))
        faltando = sorted(schema - chaves)
        sobrando = sorted(chaves - schema)
        for k in faltando:
            error(f"{addon}/{t.name}: missing translation for '{k}'")
        for k in sobrando:
            error(f"{addon}/{t.name}: '{k}' translated but absent from schema")
        if not faltando and not sobrando:
            print(f"  {addon}/{t.name}: {len(chaves)}/{len(schema)} options OK")

    # the config version needs a changelog entry
    versao = str(cfg.get("version", ""))
    ch = (base / "CHANGELOG.md")
    if ch.exists() and f"[{versao}]" not in ch.read_text(encoding="utf-8"):
        error(f"{addon}: version {versao} has no CHANGELOG.md entry")

sys.exit(1 if failed else 0)
