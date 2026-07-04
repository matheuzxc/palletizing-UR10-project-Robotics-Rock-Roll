#!/usr/bin/env python
"""
Sincroniza os programas Python (macros) da estacao aberta no RoboDK com
arquivos .py na sua IDE, nos dois sentidos.

    pull   RoboDK -> IDE   (extrai cada macro Python para programs/<nome>.py)
    push   IDE -> RoboDK   (reimporta cada programs/<nome>.py de volta na estacao)
    status                 (lista os macros da estacao e o estado dos arquivos)

Uso (com o Python embutido do RoboDK, que ja tem o pacote robodk):

    "C:/RoboDK/Python-Embedded/python.exe" sync_robodk.py pull
    "C:/RoboDK/Python-Embedded/python.exe" sync_robodk.py push --save
    "C:/RoboDK/Python-Embedded/python.exe" sync_robodk.py status

O RoboDK precisa estar aberto com a estacao desejada em foco.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRAMS_DIR = os.path.join(HERE, "programs")
MANIFEST = os.path.join(HERE, "programs", "_manifest.json")

# --- garante que o pacote robodk seja encontrado (fallback p/ instalacao embutida) ---
try:
    from robolink import Robolink, ITEM_TYPE_PROGRAM_PYTHON
except ImportError:
    _emb = r"C:/RoboDK/Python-Embedded/Lib/site-packages"
    if os.path.isdir(_emb):
        sys.path.insert(0, _emb)
    from robolink import Robolink, ITEM_TYPE_PROGRAM_PYTHON


def decode_code(raw):
    """O comando 'Code' devolve o fonte com <br> no lugar de \\n. So isso e escapado."""
    return raw.replace("\r", "").replace("<br>", "\n")


def safe_filename(name):
    """Converte o nome do macro em um nome de arquivo valido."""
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def connect():
    rdk = Robolink()
    st = rdk.ActiveStation()
    if not st.Valid():
        print("ERRO: nenhuma estacao aberta no RoboDK.")
        sys.exit(1)
    print("Estacao ativa:", st.Name())
    return rdk


def python_macros(rdk):
    """Todos os itens do tipo Programa que sao macros Python (possuem codigo)."""
    result = []
    for it in rdk.ItemList():
        if it.Type() != ITEM_TYPE_PROGRAM_PYTHON:
            continue
        raw = it.setParam("Code")
        result.append((it, raw))
    return result


def load_manifest():
    if os.path.isfile(MANIFEST):
        with open(MANIFEST, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(data):
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cmd_pull(args):
    rdk = connect()
    os.makedirs(PROGRAMS_DIR, exist_ok=True)
    manifest = {}
    count = 0
    for it, raw in python_macros(rdk):
        name = it.Name()
        fname = safe_filename(name) + ".py"
        code = decode_code(raw)
        with open(os.path.join(PROGRAMS_DIR, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(code)
        manifest[fname] = name
        count += 1
        print("  pull <-", name, "->", os.path.join("programs", fname))
    save_manifest(manifest)
    print("OK: %d macro(s) extraido(s) para %s" % (count, PROGRAMS_DIR))


def cmd_push(args):
    rdk = connect()
    manifest = load_manifest()
    if not os.path.isdir(PROGRAMS_DIR):
        print("ERRO: pasta programs/ nao existe. Rode 'pull' primeiro.")
        sys.exit(1)

    existing = {it.Name(): it for it, _ in python_macros(rdk)}
    count = 0
    for fname in sorted(os.listdir(PROGRAMS_DIR)):
        if not fname.endswith(".py"):
            continue
        target_name = manifest.get(fname, fname[:-3])
        # remove o macro antigo de mesmo nome (as chamadas por nome continuam validas)
        if target_name in existing:
            existing[target_name].Delete()
        newit = rdk.AddFile(os.path.join(PROGRAMS_DIR, fname))
        if not newit.Valid():
            print("  FALHA ao importar", fname)
            continue
        if newit.Name() != target_name:
            newit.setName(target_name)
        count += 1
        print("  push ->", target_name)

    print("OK: %d macro(s) enviado(s) para a estacao." % count)
    if args.save:
        path = rdk.getParam("PATH_OPENSTATION")
        st = rdk.ActiveStation()
        # PATH_OPENSTATION as vezes e so a pasta; monta o caminho do .rdk
        if path and os.path.isdir(path):
            path = os.path.join(path, st.Name() + ".rdk")
        rdk.Save(path)
        print("Estacao salva em:", path)


def cmd_status(args):
    rdk = connect()
    manifest = load_manifest()
    macros = python_macros(rdk)
    print("\nMacros Python na estacao (%d):" % len(macros))
    for it, _ in macros:
        fname = safe_filename(it.Name()) + ".py"
        ondisk = os.path.isfile(os.path.join(PROGRAMS_DIR, fname))
        print("  [%s] %s" % ("arquivo OK" if ondisk else "sem arquivo", it.Name()))
    if os.path.isdir(PROGRAMS_DIR):
        names = {safe_filename(it.Name()) + ".py" for it, _ in macros}
        for fname in sorted(os.listdir(PROGRAMS_DIR)):
            if fname.endswith(".py") and fname not in names:
                print("  [so na IDE] programs/%s" % fname)


def main():
    p = argparse.ArgumentParser(description="Sincroniza macros Python entre RoboDK e a IDE.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pull", help="RoboDK -> IDE")
    pp = sub.add_parser("push", help="IDE -> RoboDK")
    pp.add_argument("--save", action="store_true", help="salva a estacao .rdk apos enviar")
    sub.add_parser("status", help="mostra o estado da sincronizacao")
    args = p.parse_args()

    {"pull": cmd_pull, "push": cmd_push, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    main()
