"""Generate per-vehicle highlight proxies for the empty_vehicle_highlight mod.

For every vehicle def in /entity/-vehicle (wrecks under /x/ and *_x / *_xx skipped):
  * proxy entity   <mdl folder>/evh_<name>.def   - same model as the vehicle, all
                    volumes "able clear", stuff extender -> lights up with key C
  * item           set/stuff/special/evh_<name>  - hover text key desc/stuff/evh_<name>
  * localization   desc/stuff/evh_<name> = vehicle name (copied from desc/entity/<name>)
  * script block   {"<name>" {on "evh_proxy" {spawn "evh_<name>" ...}}}
  * entity.set     vanilla set/interaction_entity/entity.set + our two includes

Reads the game paks only; writes into mod/empty_vehicle_highlight/.
Game folder: env GOH_DIR, else the default below.
"""
import os
import posixpath
import re
import shutil
import zipfile
from pathlib import Path

GAME = Path(os.environ.get("GOH_DIR", r"F:\SteamLibrary\steamapps\common\Call to Arms - Gates of Hell"))
MOD = Path(__file__).resolve().parent.parent / "mod" / "empty_vehicle_highlight"
INCLUDES = ['empty_vehicle_highlight.inc', 'empty_vehicle_highlight_proxies.inc']
VPAK = "-vehicle"                      # paths inside -vehicle.pak start with this
PROXY_LIFE = 3.3                       # must stay > refresh period in the .inc (3 s)

vz = zipfile.ZipFile(GAME / "resource/entity/-vehicle.pak")
files = {n.lower(): n for n in vz.namelist()}


def read(path):
    n = files.get(path.lower())
    return vz.read(n).decode("utf-8", "replace") if n else None


def strip_comments(s):
    return re.sub(r";[^\n]*", "", s)


def resolve(cur_dir, ref):
    if ref.startswith("/"):
        # absolute VFS path; only /entity/-vehicle/... can be read from this pak
        if not ref.lower().startswith("/entity/"):
            return None
        return ref[len("/entity/"):]
    return posixpath.normpath(posixpath.join(cur_dir, ref))


def find_model(path, seen=None):
    """depth-first: (mdl_path, texmod) following local includes / extensions"""
    seen = seen if seen is not None else set()
    if path.lower() in seen:
        return None, None
    seen.add(path.lower())
    s = read(path)
    if s is None:
        return None, None
    s = strip_comments(s)
    d = posixpath.dirname(path)
    texmod = None
    m = re.search(r'(?i)\{\s*texmod\s+"([^"]+)"', s)
    if m:
        texmod = m.group(1)
    for m in re.finditer(r'(?i)\{\s*extension\s+"([^"]+)"|\(\s*include\s+"([^"]+)"', s):
        ref = m.group(1) or m.group(2)
        p = resolve(d, ref)
        if not p:
            continue
        if p.lower().endswith(".mdl"):
            if p.lower() in files:
                return files[p.lower()], texmod
            continue
        if p.lower().endswith((".inc", ".ext", ".def")):
            mdl, tm = find_model(p, seen)
            if mdl:
                return mdl, texmod or tm
    return None, texmod


def load_names():
    out = {}
    for lang in ("default", "ch"):
        z = zipfile.ZipFile(GAME / "localizations" / f"{lang}.pak")
        names = {}
        for n in z.namelist():
            if not n.endswith((".po", ".pot")):
                continue
            t = z.read(n).decode("utf-8", "replace")
            for m in re.finditer(r'msgctxt "desc/entity/([^"]+)"\s*\nmsgid "((?:[^"\\]|\\.)*)"\s*\nmsgstr "((?:[^"\\]|\\.)*)"', t):
                key, mid, mstr = m.groups()
                names.setdefault(key.lower(), mstr or mid)
        out[lang] = names
    return out


def po_header(lang):
    return ('msgid ""\nmsgstr ""\n'
            '"Project-Id-Version: empty_vehicle_highlight\\n"\n'
            '"MIME-Version: 1.0\\n"\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            '"Content-Transfer-Encoding: 8bit\\n"\n'
            f'"Language: {lang}\\n"\n\n')


def write_entity_set():
    """Copy the vanilla entity.set from the installed game and append our includes,
    so a game update only needs a re-run of this script."""
    raw = zipfile.ZipFile(GAME / "resource/gamelogic.pak").read("set/interaction_entity/entity.set")
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    body = raw.rstrip()
    if not body.endswith(b"}"):
        raise SystemExit("unexpected entity.set layout: no closing brace")
    add = nl + b"\t;// mod empty_vehicle_highlight (keep last so its handlers chain after vanilla ones)" + nl
    add += b"".join(b'\t(include "' + i.encode() + b'")' + nl for i in INCLUDES)
    out = body[:-1].rstrip() + nl + add + b"}" + nl
    p = MOD / "resource/set/interaction_entity/entity.set"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(out)


def main():
    write_entity_set()
    names = load_names()
    defs = sorted(n for n in vz.namelist()
                  if n.endswith(".def") and not re.search(r"/x/|_xx?\.def$", n))

    out_entity = MOD / "resource" / "entity"
    out_items = MOD / "resource" / "set" / "stuff" / "special"
    # remove previous generation
    for p in (out_entity / VPAK,):
        shutil.rmtree(p, ignore_errors=True)
    for p in out_items.glob("evh_*"):
        p.unlink()
    out_items.mkdir(parents=True, exist_ok=True)

    blocks, pot, po, skipped = [], [], [], []
    for d in defs:
        name = posixpath.splitext(posixpath.basename(d))[0]
        mdl, texmod = find_model(d)
        if not mdl:
            skipped.append(name)
            continue
        mdl_text = strip_comments(read(mdl) or "")
        vols = sorted(set(re.findall(r'(?i)\{\s*volume\s+"([^"]+)"', mdl_text)))
        proxy = f"evh_{name}"
        lines = ["{game_entity",
                 f"\t;// empty_vehicle_highlight proxy for {name} (generated)",
                 f'\t{{Extension "{posixpath.basename(mdl)}"}}']
        if texmod:
            lines.append(f'\t{{texmod "{texmod}"}}')
        lines += ["\t{extender \"stuff\"",
                  f'\t\t{{item "{proxy}"}}',
                  "\t}",
                  '\t{props "steel" "nocover"}',
                  '\t{obstacleID "stuff"}']
        for v in vols:
            lines.append(f'\t{{volume "{v}" {{able clear}}}}')
        lines += ['\t{lodclass "vehicle"}', "\t{NoGroupMesh 1}", "\t{NoVisibilityPatch}",
                  "\t{NoCastShadows}", "}", ""]
        dest = out_entity / Path(posixpath.dirname(mdl)) / f"{proxy}.def"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("\n".join(lines), encoding="utf-8")

        (out_items / proxy).write_text(
            "{item\n"
            f'\t;// empty_vehicle_highlight proxy item for {name} (generated)\n'
            f'\t{{entity "{proxy}"}}\n'
            "\t{inventory\n\t\t{size 4 1}\n\t\t{weight 100}\n\t\t{block 5}\n\t\t{fsm \"stuff\"}\n\t}\n"
            "\t{mass 20}\n}\n", encoding="utf-8")

        en = names["default"].get(name.lower(), name)
        zh = names["ch"].get(name.lower(), en)
        pot.append(f'msgctxt "desc/stuff/{proxy}"\nmsgid "{en}"\nmsgstr ""\n')
        po.append(f'msgctxt "desc/stuff/{proxy}"\nmsgid "{en}"\nmsgstr "{zh}"\n')

        blocks.append(f'{{"{name}"\n\t{{on "evh_proxy"\n'
                      f'\t\t{{spawn "{proxy}" "basis" x {{delay {PROXY_LIFE} {{delete}}}}}}\n\t}}\n}}')

    inc = MOD / "resource/set/interaction_entity/empty_vehicle_highlight_proxies.inc"
    inc.write_text(";SDL\n;// generated by tools/gen_proxies.py - do not edit by hand\n"
                   + "\n".join(blocks) + "\n", encoding="utf-8")
    for lang, body, ext in (("default", pot, "pot"), ("ch", po, "po")):
        p = MOD / "localizations" / lang / "interface" / "text" / "desc" / f"evh_names.{ext}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(po_header("en" if lang == "default" else "zh_CN") + "\n".join(body), encoding="utf-8")

    no_name = [b for b in defs if posixpath.splitext(posixpath.basename(b))[0].lower() not in names["ch"]]
    print(f"defs {len(defs)}  proxies {len(blocks)}  skipped(no mdl) {len(skipped)} {skipped[:15]}")
    print(f"no chinese name (falls back to english/def name): {len(no_name)}")


if __name__ == "__main__":
    main()
