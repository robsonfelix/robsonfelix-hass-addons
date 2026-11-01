#!/usr/bin/env python3
"""Checa consistencia entre options, schema e as traducoes de um add-on.

Existe por causa de um caso real: o PR #47 adicionou tres opcoes traduzidas so
para ingles, e o fr.yaml estava sem quatro chaves de remote control desde a
1.2.65. Nada no repositorio pegava isso -- a opcao simplesmente aparecia sem
nome na interface do Home Assistant, no idioma do usuario.

    python3 .github/scripts/check-addon-options.py claudecode
"""
import sys
from pathlib import Path

import yaml

falhou = False


def erro(msg):
    global falhou
    falhou = True
    print(f"::error::{msg}")


for addon in sys.argv[1:]:
    base = Path(addon)
    cfg = yaml.safe_load((base / "config.yaml").read_text(encoding="utf-8"))
    options = set(cfg.get("options") or {})
    schema = set(cfg.get("schema") or {})

    # toda opcao precisa de schema, e vice-versa
    for k in sorted(options - schema):
        erro(f"{addon}: '{k}' esta em options mas nao em schema")
    for k in sorted(schema - options):
        # opcional no schema (sufixo ?) pode nao ter default
        tipo = str((cfg.get("schema") or {}).get(k, ""))
        if not tipo.endswith("?"):
            erro(f"{addon}: '{k}' esta em schema mas nao tem default em options")

    traducoes = sorted((base / "translations").glob("*.yaml"))
    if not traducoes:
        erro(f"{addon}: nenhuma traducao encontrada")
    for t in traducoes:
        dados = yaml.safe_load(t.read_text(encoding="utf-8")) or {}
        chaves = set((dados.get("configuration") or {}))
        faltando = sorted(schema - chaves)
        sobrando = sorted(chaves - schema)
        for k in faltando:
            erro(f"{addon}/{t.name}: falta traducao para '{k}'")
        for k in sobrando:
            erro(f"{addon}/{t.name}: '{k}' traduzida mas nao existe no schema")
        if not faltando and not sobrando:
            print(f"  {addon}/{t.name}: {len(chaves)}/{len(schema)} opcoes OK")

    # a versao do config precisa ter entrada no changelog
    versao = str(cfg.get("version", ""))
    ch = (base / "CHANGELOG.md")
    if ch.exists() and f"[{versao}]" not in ch.read_text(encoding="utf-8"):
        erro(f"{addon}: versao {versao} nao tem entrada em CHANGELOG.md")

sys.exit(1 if falhou else 0)
