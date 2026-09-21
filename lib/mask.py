"""The identity mask: a picture whose pixels are part numbers (ADR 0018).

`contour render` emits one of these beside the sheet, laid out tile for tile the
same way, so a pixel on the sheet and a pixel on the mask are the same pixel.
Index 0 is background. Every other index names a part through `parts.json`.

It is an 8-bit greyscale PNG written here rather than by Blender, because the
value has to *be* the index: pushed through Workbench's colour management and
back it would only approximate one. Written and read in the standard library,
every scanline filter 0, which keeps both halves of this file short and keeps
the mask openable by anything that reads a PNG.
"""
import json
import struct
import zlib
from pathlib import Path

SIG = b"\x89PNG\r\n\x1a\n"


def _chunk(kind, payload):
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))


def write(path, rows):
    """Write one index per pixel. `rows` is height sequences of width ints —
    lists or a numpy array, which is why the length is taken from the bytes
    rather than from the row: a numpy row has no truth value."""
    scanlines = [bytes(bytearray(row)) for row in rows]
    h = len(scanlines)
    w = len(scanlines[0]) if h else 0
    raw = b"".join(b"\x00" + line for line in scanlines)
    Path(path).write_bytes(
        SIG
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 6))
        + _chunk(b"IEND", b""))


def read(path):
    """`(width, height, data)` — one byte per pixel, row-major."""
    blob = Path(path).read_bytes()
    if not blob.startswith(SIG):
        raise ValueError(f"{path}: not a PNG")
    w = h = None
    pieces, i = [], len(SIG)
    while i < len(blob):
        n, kind = struct.unpack(">I", blob[i:i + 4])[0], blob[i + 4:i + 8]
        payload = blob[i + 8:i + 8 + n]
        if kind == b"IHDR":
            w, h, depth, colour = struct.unpack(">IIBB", payload[:10])
            if (depth, colour) != (8, 0):
                raise ValueError(f"{path}: not an 8-bit greyscale mask")
        elif kind == b"IDAT":
            pieces.append(payload)
        i += n + 12
    raw = zlib.decompress(b"".join(pieces))
    stride = w + 1
    return w, h, b"".join(raw[r * stride + 1:(r + 1) * stride] for r in range(h))


def part_at(mask_path, parts_path, x, y):
    """The part owning this pixel, or None for background — and None, never a
    guess, when there is no mask: a space rendered before the mask existed
    still takes marks, they just do not know what they are on."""
    mask_path, parts_path = Path(mask_path), Path(parts_path)
    if not (mask_path.exists() and parts_path.exists()):
        return None
    w, h, data = read(mask_path)
    if not (0 <= x < w and 0 <= y < h):
        return None
    index = data[y * w + x]
    if not index:
        return None
    return json.loads(parts_path.read_text()).get(str(index))
