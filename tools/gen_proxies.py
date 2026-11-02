"""Generate per-vehicle highlight proxies for the empty_vehicle_highlight mod.

For every vehicle def in /entity/-vehicle (wrecks under /x/ and *_x / *_xx skipped):
  * proxy model    entity/evh/<faction>/.../<model>.mdl - copy of the vehicle's mdl whose
                    ply/vol/anm references point back into /entity/-vehicle, with the
                    geometry of moving parts removed (turrets, guns, trails, doors...:
                    revolute bones and bones moved by pose animations such as close /
                    open / aim). Those parts can sit in another pose on the real vehicle
                    and showed up as a doubled image; the static rest of the proxy covers
                    the vehicle exactly. Materials resolve next to the .mdl, so the
                    vanilla .mtl files are copied alongside (texture paths kept valid).
  * proxy entity   entity/evh/<faction>/.../evh_<name>.def - uses the proxy model, all
                    volumes "able clear", stuff extender -> outlined with key C
  * item           set/stuff/evh/evh_<name>  - hover text key desc/stuff/evh_<name>
  * localization   desc/stuff/evh_<name> = vehicle name (copied from desc/entity/<name>)
  * script block   {"<name> obstacle_ignore_height" {on "evh_proxy" {spawn "evh_<name>" ...}}}
  * debug.inc      vanilla set/interaction_entity/debug.inc + our two includes

Compatibility rules (see README):
  * nothing under /entity/-vehicle/ or /set/stuff/special/: the in-game library
    scans those folders and crashes / lists our proxies.
  * do not override entity.set (big mods replace it); hook into the tiny debug.inc,
    which every entity.set keeps including.
  * script block keys never equal a bare vanilla entity name.

Reads the game paks only; writes into mod/empty_vehicle_highlight/.
Game folder: env GOH_DIR, else the default below.
"""
import os
import posixpath
import re
import shutil
import struct
import zipfile
from pathlib import Path

GAME = Path(os.environ.get("GOH_DIR", r"D:\SteamLibrary\steamapps\common\Call to Arms - Gates of Hell"))
MOD = Path(__file__).resolve().parent.parent / "mod" / "empty_vehicle_highlight"
INCLUDES = ['empty_vehicle_highlight.inc', 'empty_vehicle_highlight_proxies.inc']
VPAK = "-vehicle"                      # paths inside -vehicle.pak start with this
PROXY_ROOT = "evh"                     # proxies live in /entity/evh/<path below -vehicle/>
ITEM_DIR = "evh"                       # items live in /set/stuff/evh/
HOOK_FILE = "set/interaction_entity/debug.inc"
KEY_SUFFIX = "obstacle_ignore_height"  # prop from /properties/vehicle.ext
PROXY_LIFE = 3.3                       # must stay > refresh period in the .inc (3 s)
# Note: an invisible proxy is not possible - the key-C outline is only drawn where the
# proxy itself is drawn (tested: alpha 0 / alpha test / additive all lose the outline).

# bones that rotate but keep the silhouette (wheels, tracks...) or carry the whole model
KEEP_BONE = re.compile(r"(?i)wheel|track|roller|steer|suspension|sprocket|idler|basis|pivot"
                       r"|axle|achse|^body$")
# animations that do not leave a part in another resting pose
TRANSIENT_SEQ = re.compile(r"(?i)^(start|stop|fire\w*|hit|recoil|shell_eject|repair|drift"
                           r"|engine\w*|board|wipers|headlight|reload\w*|move|wheels|water)$")
MIN_VISIBLE = 0.10   # keep at least this share of the geometry, else hide less


FILE_REF = re.compile(r'"([^"/\\]+\.(?:ply|vol|anm))"', re.I)
SEQUENCE = re.compile(r'(?i)\{\s*sequence\s+"([^"]+)"')
TEX_KEYS = re.compile(r'(\{\s*(?:diffuse1?|bump|specular|mask|lightmap|envmap|height)\s+")'
                      r'([^"$/][^"]*)"', re.I)

# outputs of older versions that must not be shipped any more
LEGACY = ["resource/set/interaction_entity/entity.set", f"resource/entity/{VPAK}",
          "resource/texture/common/evh"]

vz = zipfile.ZipFile(GAME / "resource/entity/-vehicle.pak")
files = {n.lower(): n for n in vz.namelist()}


def read(path):
    n = files.get(path.lower())
    return vz.read(n).decode("utf-8", "replace") if n else None


def strip_comments(s):
    return re.sub(r";[^\n]*", "", s)


def mask(s):
    """same length as s, with string contents and ; comments blanked (for brace matching)"""
    out, i, n = list(s), 0, len(s)
    while i < n:
        c = s[i]
        if c == '"':
            j = s.find('"', i + 1)
            nl = s.find("\n", i + 1)
            if j < 0 or 0 <= nl < j:     # unterminated string ends at the line end
                j = nl if nl >= 0 else n
            for k in range(i + 1, j):
                out[k] = " "
            i = j + 1
        elif c == ";":
            j = s.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def moving_bones(path):
    """bone names whose position/rotation changes during an .anm (frame 0 = reference);
    all animated bones if the file layout is not understood"""
    n = files.get(path.lower())
    if not n:
        return set()
    b = vz.read(n)
    try:
        j = b.find(b"BMAP")
        cnt = int.from_bytes(b[j + 4:j + 8], "little")
        k, names = j + 8, []
        for _ in range(cnt):
            ln = int.from_bytes(b[k:k + 4], "little")
            names.append(b[k + 4:k + 4 + ln].decode("latin1").lower())
            k += 4 + ln
        first, moving, frame = {}, set(), 0
        while b[k:k + 4] == b"FRM2":
            recs = b[k + 6]
            k += 7
            for _ in range(recs):
                bone, flags = b[k], b[k + 1]
                k += 3
                if flags & ~0x0B:
                    return set(names)
                v = {}
                for bit, key in ((1, "p"), (2, "r")):
                    if flags & bit:
                        v[key] = struct.unpack("<3f", b[k:k + 12])
                        k += 12
                if frame == 0:
                    first[bone] = v
                    continue
                f0 = first.get(bone, {})
                for key, tol in (("p", 0.3), ("r", 0.01)):
                    if key in v and (key not in f0 or
                                     max(abs(a - c) for a, c in zip(v[key], f0[key])) > tol):
                        moving.add(names[bone])
            frame += 1
        return moving if k == len(b) else set(names)
    except (IndexError, struct.error):
        return set()


def bone_spans(text, masked):
    """(start, end, name, kind) for every {bone ...} block"""
    out = []
    for m in re.finditer(r"(?i)\{\s*bone\b\s*(\w*)\s*\"", masked):
        s = m.start()
        name = re.search(r'"([^"\n]+)', text[s:s + 200]).group(1).lower()
        out.append((s, block_end(masked, s), name, m.group(1).lower()))
    return out


def geometry_blocks(masked):
    """(start, end) of outermost {LODView} / {VolumeView} blocks"""
    out = []
    for m in re.finditer(r"(?i)\{\s*(LODView|VolumeView)\b", masked):
        s = m.start()
        if out and s < out[-1][1]:
            continue
        out.append((s, block_end(masked, s)))
    return out


def ply_size(text, start, end, mdl_dir):
    total = 0
    for f in re.findall(r'"([^"]+\.ply)"', text[start:end], re.I):
        n = files.get(posixpath.join(mdl_dir, f).lower())
        total += vz.getinfo(n).file_size if n else 0
    return total


def hidden_spans(text, mdl_dir):
    """geometry blocks to drop from the proxy, and the hidden top-level bone names"""
    masked = mask(text)
    posed = set()
    for m in re.finditer(r"(?i)\{\s*sequence\b", masked):
        blk = text[m.start():block_end(masked, m.start())]
        seq = re.search(r'"([^"\n]+)', blk).group(1)
        if TRANSIENT_SEQ.match(seq):
            continue
        f = re.search(r'(?i)\{\s*file\s+"([^"]+)"', blk)
        posed |= moving_bones(posixpath.join(mdl_dir, f.group(1) if f else f"{seq}.anm"))
    bones = [b for b in bone_spans(text, masked) if not KEEP_BONE.search(b[2])]
    geo = geometry_blocks(masked)
    total = sum(ply_size(text, s, e, mdl_dir) for s, e in geo) or 1

    def pick(hide):
        tops = [b for b in hide if not any(o[0] < b[0] < o[1] for o in hide)]
        drop = [g for g in geo if any(t[0] <= g[0] < t[1] for t in tops)]
        shown = 1 - sum(ply_size(text, s, e, mdl_dir) for s, e in drop) / total
        return drop, sorted({t[2] for t in tops}), shown

    # 1) rotating parts + parts left in another pose; 2) posed parts only; 3) nothing
    for hide in ([b for b in bones if b[3] == "revolute" or b[2] in posed],
                 [b for b in bones if b[2] in posed]):
        drop, names, shown = pick(hide)
        if shown >= MIN_VISIBLE:
            return drop, names
    return [], []


def ply_materials(path):
    """material file names embedded in a .ply (length-prefixed strings ending in .mtl)"""
    n = files.get(path.lower())
    if not n:
        return set()
    b = vz.read(n)
    out, i = set(), 0
    while (i := b.find(b".mtl", i)) >= 0:
        end = i + 4
        for start in range(end - 1, max(0, end - 120), -1):
            if b[start - 1] == end - start:
                out.add(b[start:end].decode("latin1"))
                break
        i = end
    return out


def block_end(s, start):
    """index just past the brace block that opens at s[start] == '{'"""
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(s)


def explicit_sequence_files(text, mdl_dir):
    """{sequence "x" ...} without {file} loads x.anm next to the .mdl; make that explicit
    so it keeps loading from the vanilla folder after the mdl is moved."""
    out, pos = [], 0
    for m in SEQUENCE.finditer(text):
        if m.start() < pos:
            continue
        end = block_end(text, m.start())
        body = text[m.end():end]
        anm = f"{m.group(1)}.anm"
        out.append(text[pos:m.end()])
        if not re.search(r"(?i)\{\s*file\s", strip_comments(body)) and \
                posixpath.join(mdl_dir, anm).lower() in files:
            out.append(f' {{file "{anm}"}}')
        out.append(body)
        pos = end
    out.append(text[pos:])
    return "".join(out)


def write_proxy_model(mdl, proxy_dir):
    """Copy mdl into proxy_dir without the geometry of moving parts, file refs pointing
    back to the vanilla folder, plus the vanilla materials. Returns (file name, hidden
    bone names) or (None, None)."""
    text = read(mdl)
    if text is None:
        return None, None
    mdl_dir = posixpath.dirname(mdl)
    back = posixpath.relpath(mdl_dir, proxy_dir)
    drop, hidden = hidden_spans(text, mdl_dir)
    for s, e in sorted(drop, reverse=True):
        text = text[:s] + text[e:]
    plys = set()

    def repl(m):
        f = m.group(1)
        if f.lower().endswith(".ply"):
            plys.add(posixpath.join(mdl_dir, f))
        return f'"{back}/{f}"'

    out = FILE_REF.sub(repl, explicit_sequence_files(text, mdl_dir))
    if not plys:
        return None, None
    mats = set()
    for p in plys:
        mats |= ply_materials(p)
    dest = MOD / "resource" / "entity" / Path(proxy_dir)
    dest.mkdir(parents=True, exist_ok=True)
    name = posixpath.basename(mdl)
    header = (";// empty_vehicle_highlight proxy model (generated from vanilla)\n"
              f";// moving parts without geometry: {' '.join(hidden) or '-'}\n")
    (dest / name).write_text(header + out, encoding="utf-8")
    # all vanilla materials of the folder (texmod variants included)
    prefix = mdl_dir.lower() + "/"
    for low_name, real in files.items():
        if not (low_name.startswith(prefix) and low_name.endswith(".mtl")
                and "/" not in low_name[len(prefix):]):
            continue
        src = vz.read(real).decode("utf-8", "replace")

        def absolute(t):
            # texture next to the vanilla mtl -> absolute VFS path; others unchanged
            local = posixpath.join(mdl_dir, t.group(2)).lower()
            if any(local + ext in files for ext in (".dds", ".tex")):
                return f'{t.group(1)}/entity/{mdl_dir}/{t.group(2)}"'
            return t.group(0)

        (dest / posixpath.basename(real)).write_text(TEX_KEYS.sub(absolute, src),
                                                    encoding="utf-8")
    missing = [m for m in mats if posixpath.join(mdl_dir, m).lower() not in files]
    if missing:
        print(f"  note {mdl}: plys use materials not in its folder: {missing}")
    return name, hidden


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


def write_hook():
    """Copy the vanilla debug.inc from the installed game and append our includes,
    so a game update only needs a re-run of this script."""
    raw = zipfile.ZipFile(GAME / "resource/gamelogic.pak").read(HOOK_FILE)
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    if b"(include" in raw:
        raise SystemExit(f"unexpected {HOOK_FILE} layout: already has includes")
    add = nl + b";// mod empty_vehicle_highlight: hooked here instead of entity.set for compatibility" + nl
    add += b"".join(b'(include "' + i.encode() + b'")' + nl for i in INCLUDES)
    out = raw.rstrip() + nl + add
    p = MOD / "resource" / HOOK_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(out)


def main():
    for rel in LEGACY:
        p = MOD / rel
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
    for p in (MOD / "resource/texture/common", MOD / "resource/texture"):
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    old_items = MOD / "resource/set/stuff/special"
    for p in old_items.glob("evh_*"):
        p.unlink()
    if old_items.is_dir() and not any(old_items.iterdir()):
        old_items.rmdir()

    write_hook()
    names = load_names()
    defs = sorted(n for n in vz.namelist()
                  if n.endswith(".def") and not re.search(r"/x/|_xx?\.def$", n))

    out_entity = MOD / "resource" / "entity" / PROXY_ROOT
    out_items = MOD / "resource" / "set" / "stuff" / ITEM_DIR
    # remove previous generation
    shutil.rmtree(out_entity, ignore_errors=True)
    shutil.rmtree(out_items, ignore_errors=True)
    out_items.mkdir(parents=True, exist_ok=True)

    blocks, pot, po, skipped, fallback = [], [], [], [], []
    models = {}
    for d in defs:
        name = posixpath.splitext(posixpath.basename(d))[0]
        mdl, texmod = find_model(d)
        if not mdl:
            skipped.append(name)
            continue
        mdl_text = strip_comments(read(mdl) or "")
        vols = sorted(set(re.findall(r'(?i)\{\s*volume\s+"([^"]+)"', mdl_text)))
        proxy = f"evh_{name}"
        # proxy sits at /entity/evh/<faction>/..., model stays at /entity/-vehicle/<faction>/...
        mdl_dir = posixpath.dirname(mdl)
        proxy_dir = posixpath.join(PROXY_ROOT, posixpath.relpath(mdl_dir, VPAK))
        if mdl not in models:
            models[mdl] = write_proxy_model(mdl, proxy_dir)
        own, _ = models[mdl]
        if own:
            mdl_ref = own
        else:
            # could not build a reduced copy: full vanilla model
            fallback.append(name)
            mdl_ref = posixpath.relpath(mdl, proxy_dir)
        lines = ["{game_entity",
                 f"\t;// empty_vehicle_highlight proxy for {name} (generated)",
                 f'\t{{Extension "{mdl_ref}"}}']
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
        dest = MOD / "resource" / "entity" / Path(proxy_dir) / f"{proxy}.def"
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

        blocks.append(f'{{"{name} {KEY_SUFFIX}"\n\t{{on "evh_proxy"\n'
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
    hid = [h for m, h in models.values() if m]
    print(f"proxy models {len(hid)}  with moving parts removed {sum(1 for h in hid if h)}  "
          f"full-model fallback proxies {len(fallback)} {fallback[:15]}")
    print(f"no chinese name (falls back to english/def name): {len(no_name)}")


if __name__ == "__main__":
    main()
