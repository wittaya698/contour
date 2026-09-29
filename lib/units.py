"""The arithmetic and validation under `lib/kit.py`, kept out of Blender.

`kit` is what every space's `build.py` calls and it needs `bpy`, so nothing
pure can test it. What it does that is only numbers lives here instead, where a
test can reach it: millimetres to metres, a size that must be three lengths,
and a hex colour to the linear values Blender stores (issue 26).

Authors write millimetres; Blender stores metres.
"""
import re

MM = 0.001
_HEX = re.compile(r"#?([0-9a-fA-F]{6})")


def mm(*v):
    """mm(50) -> 0.05 ; mm(1, 2, 3) -> (0.001, 0.002, 0.003)"""
    return v[0] * MM if len(v) == 1 else tuple(x * MM for x in v)


def size(size_mm):
    """Three positive lengths in millimetres -> three in metres. Refused here,
    in words about the size, rather than inside bmesh in words about vectors."""
    size_mm = tuple(size_mm)
    if len(size_mm) != 3:
        raise ValueError(f"a size is three lengths in mm, not {size_mm}")
    if any(not v > 0 for v in size_mm):
        raise ValueError(f"every length of a size must be positive: {size_mm}")
    return mm(*size_mm)


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear(hex_colour):
    """'#8A8F98' -> its linear (r, g, b), what `diffuse_color` and the
    Principled base colour take."""
    got = _HEX.fullmatch(hex_colour)
    if not got:
        raise ValueError(f"a colour is six hex digits, like '#8A8F98', not {hex_colour!r}")
    h = got.group(1)
    return tuple(_srgb_to_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
