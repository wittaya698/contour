"""Read a .glb without Blender: the round-trip's independent measurement (ADR 0006).

Inspecting the Blender scene proves nothing about what landed in the file, and
re-importing through Blender's own importer would share any exporter/importer
symmetry bug. This reads the container directly and measures in glTF space
(Y-up, right-handed, metres). Pure stdlib, so it is testable outside Blender.
"""
import copy
import json
import re
import struct

_COMP = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


_JSON, _BIN = 0x4E4F534A, 0x004E4942


def load(path):
    """-> (document, buffer). Refuses a file that is not exactly one glTF 2.0
    container: cut short, longer than it says, chunks out of order or
    misaligned. A half-read file would be measured, confidently, as whatever
    half arrived."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 12:
        raise ValueError(f"truncated: {len(data)} bytes is not even a header")
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError(f"not a glTF 2.0 binary: {magic!r} v{version}")
    if length > len(data):
        raise ValueError(f"truncated: the header says {length} bytes and there are {len(data)}")
    if length < len(data):
        raise ValueError(f"the header's length is {length} and the file is {len(data)} bytes")
    doc, blob, off = None, None, 12
    while off < length:
        if off + 8 > length:
            raise ValueError(f"truncated: a chunk header at byte {off} is cut short")
        clen, ctype = struct.unpack_from("<II", data, off)
        if off + 8 + clen > length:
            raise ValueError(f"truncated: a chunk at byte {off} runs {off + 8 + clen - length} "
                             f"bytes past the end")
        if clen % 4:
            raise ValueError(f"a chunk at byte {off} is {clen} bytes, not padded to 4")
        chunk = data[off + 8: off + 8 + clen]
        if off == 12 and ctype != _JSON:
            raise ValueError(f"the first chunk must be JSON, not {ctype:#010x}")
        if ctype == _JSON:
            if doc is not None:
                raise ValueError("a second JSON chunk")
            doc = json.loads(chunk)
        elif ctype == _BIN:
            if blob is not None:
                raise ValueError("a second BIN chunk")
            blob = chunk
        off += 8 + clen                     # a chunk of any other kind is skipped
    if doc is None:
        raise ValueError("no JSON chunk")
    return doc, blob or b""


def accessor(doc, blob, idx):
    a = doc["accessors"][idx]
    if "bufferView" not in a or "sparse" in a:
        raise ValueError("sparse or bufferView-less accessors are not supported")
    bv = doc["bufferViews"][a["bufferView"]]
    fmt, n = _COMP[a["componentType"]], _NCOMP[a["type"]]
    size = struct.calcsize("<" + fmt)
    stride = bv.get("byteStride") or size * n
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return [struct.unpack_from("<" + fmt * n, blob, base + i * stride) for i in range(a["count"])]


def _mul(a, b):
    """Column-major 4x4 product a @ b."""
    return [sum(a[k * 4 + r] * b[c * 4 + k] for k in range(4)) for c in range(4) for r in range(4)]


def _local(n):
    if "matrix" in n:
        return list(n["matrix"])
    t, (x, y, z, w), s = (n.get("translation", [0, 0, 0]), n.get("rotation", [0, 0, 0, 1]),
                          n.get("scale", [1, 1, 1]))
    cols = [(1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)),
            (2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)),
            (2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y))]
    m = []
    for c in range(3):
        m += [cols[c][r] * s[c] for r in range(3)] + [0.0]
    return m + [t[0], t[1], t[2], 1.0]


def _xf(m, p):
    return tuple(m[0 + i] * p[0] + m[4 + i] * p[1] + m[8 + i] * p[2] + m[12 + i] for i in range(3))


def _det3(m):
    a, b, c = m[0:3], m[4:7], m[8:11]
    return (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0]))


def measure(path):
    """-> dict(lo, hi, meshes={node name: signed volume m^3}, det_min, tris, materials,
    joints, clips={animation name: seconds}).

    A rig is counted, not posed: how many joints the skins name, and how long
    each animation runs — its latest sample time. The file holds seconds and no
    frame rate; the round-trip reads them at the build's (issue 54)."""
    doc, blob = load(path)
    lo, hi = [1e30] * 3, [-1e30] * 3
    meshes, dets, tris, mats = {}, [], 0, set()

    def visit(i, parent):
        nonlocal tris
        n = doc["nodes"][i]
        m = _mul(parent, _local(n))
        dets.append(_det3(m))
        if "mesh" in n:
            vol = 0.0
            for prim in doc["meshes"][n["mesh"]]["primitives"]:
                if prim.get("mode", 4) != 4:
                    raise ValueError("only triangle primitives are supported")
                pos = [_xf(m, p) for p in accessor(doc, blob, prim["attributes"]["POSITION"])]
                for p in pos:
                    for k in range(3):
                        lo[k], hi[k] = min(lo[k], p[k]), max(hi[k], p[k])
                idx = ([i[0] for i in accessor(doc, blob, prim["indices"])]
                       if "indices" in prim else list(range(len(pos))))
                for j in range(0, len(idx) - 2, 3):
                    p0, p1, p2 = pos[idx[j]], pos[idx[j + 1]], pos[idx[j + 2]]
                    vol += (p0[0] * (p1[1] * p2[2] - p1[2] * p2[1])
                            - p0[1] * (p1[0] * p2[2] - p1[2] * p2[0])
                            + p0[2] * (p1[0] * p2[1] - p1[1] * p2[0])) / 6.0
                    tris += 1
                if "material" in prim:
                    mats.add(doc["materials"][prim["material"]].get("name", ""))
            meshes[n.get("name", f"node{i}")] = vol
        for c in n.get("children", []):
            visit(c, m)

    ident = [1.0 if r == c else 0.0 for c in range(4) for r in range(4)]
    for root in doc["scenes"][doc.get("scene", 0)]["nodes"]:
        visit(root, ident)
    joints = {j for skin in doc.get("skins", []) for j in skin["joints"]}
    clips = {a.get("name", f"animation{i}"):
             max((t[0] for s in a["samplers"] for t in accessor(doc, blob, s["input"])),
                 default=0.0)
             for i, a in enumerate(doc.get("animations", []))}
    return {"lo": lo, "hi": hi, "meshes": meshes, "det_min": min(dets) if dets else 1.0,
            "tris": tris, "materials": mats, "joints": len(joints), "clips": clips}


def base_name(node_name):
    """'leg.001' -> 'leg': Blender numbers duplicates, and the spec counts them."""
    return re.sub(r"\.\d{3}$", "", node_name)


def wrapped(doc, **trs):
    """A copy of `doc` with every scene root parented under one new node carrying
    `trs` (translation / rotation / scale). Lets a test corrupt a real export."""
    d = copy.deepcopy(doc)
    sc = d["scenes"][d.get("scene", 0)]
    d["nodes"].append({"name": "_wrap", "children": list(sc["nodes"]), **trs})
    sc["nodes"] = [len(d["nodes"]) - 1]
    return d


def write(path, doc, blob):
    """Pack doc + blob back into a .glb (JSON chunk space-padded, BIN zero-padded)."""
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    blob = blob + b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(js) + (8 + len(blob) if blob else 0)
    out = struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js
    if blob:
        out += struct.pack("<II", len(blob), 0x004E4942) + blob
    with open(path, "wb") as f:
        f.write(out)
