"""The references, as the canvas may see them: read, and only read (ADR 0018).

`refs/` holds the user's intent in pictures, and rule 1 says nothing may ever
change one. So this module has no way to: it can name the images and hand back
their bytes, and there is deliberately no function here that writes, renames or
deletes. A mark *about* a reference lives in the space's marks file like every
other mark, and the reference itself is never touched.
"""
from pathlib import Path

KINDS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".webp": "image/webp"}


def listing(refs):
    """The images the canvas can show, by name, in a stable order.

    Flat: a reference is a picture the user dropped in, and a tab strip is no
    place for a nested path. Anything that is not an image is not offered.
    """
    refs = Path(refs) if refs else None
    if not refs or not refs.is_dir():
        return []
    return sorted(p.name for p in refs.iterdir()
                  if p.is_file() and p.suffix.lower() in KINDS)


def blob(refs, name):
    """`(bytes, content type)` for one reference, or None when there is no such
    image to hand back.

    The name is taken as a bare filename and nothing else: a reference is
    addressed by what it is called, never by a path, so there is no traversal to
    reason about rather than a traversal defended against.
    """
    refs = Path(refs) if refs else None
    if not refs or name not in listing(refs):
        return None
    return (refs / name).read_bytes(), KINDS[Path(name).suffix.lower()]
