"""./contour api <symbol>... : the real signature from the installed Blender.

Blender 5.2.1 postdates the assistant's knowledge cutoff, so a recalled signature
is a guess. One line per symbol, ~15 tokens, is the cost of not guessing.
"""
import importlib
import inspect

MAX = 700  # chars per symbol; a lookup that needs more should be read in full


def resolve(sym):
    """Dotted path -> (parent, name, obj). Imports the longest module prefix."""
    parts = sym.split(".")
    obj, i = None, len(parts)
    while i > 0:
        try:
            obj = importlib.import_module(".".join(parts[:i]))
            break
        except Exception:
            i -= 1
    if obj is None:
        raise LookupError(f"no importable module in {sym!r}")
    parent = None
    for p in parts[i:]:
        parent = obj
        try:
            obj = getattr(obj, p)
        except AttributeError:
            rna = getattr(parent, "bl_rna", None)
            if rna is not None and (p in rna.properties or p in rna.functions):
                obj = None  # described through bl_rna below
                return parent, p, None
            raise LookupError(f"{sym!r}: no attribute {p!r}")
    return parent, parts[-1], obj


def enum_items(prop):
    try:
        return [i.identifier for i in prop.enum_items]
    except Exception:
        return []


def describe_prop(name, p):
    is_arr = bool(getattr(p, "array_length", 0))  # only numeric props have it
    kind = p.type + ("[]" if is_arr else "")
    bits = [f"{name}: {kind}"]
    if p.type == "ENUM":
        items = enum_items(p)
        bits.append("{" + "|".join(items[:24]) + ("|…" if len(items) > 24 else "") + "}")
    if p.type == "POINTER" and p.fixed_type:
        bits.append(f"-> {p.fixed_type.identifier}")
    if p.type == "COLLECTION" and p.fixed_type:
        bits.append(f"of {p.fixed_type.identifier}")
    if getattr(p, "is_readonly", False):
        bits.append("readonly")
    if p.type in ("INT", "FLOAT", "BOOLEAN", "STRING") and not is_arr:
        bits.append(f"default={p.default!r}")
    elif p.type == "ENUM" and getattr(p, "default", None):
        bits.append(f"default={p.default!r}")
    return " ".join(bits)


def describe_func(name, f):
    args = []
    for p in f.parameters:
        s = p.identifier
        if p.type == "ENUM":
            s += "{" + "|".join(enum_items(p)[:12]) + "}"
        else:
            s += f":{p.type.lower()}"
        args.append(s)
    return f"{name}({', '.join(args)})"


def describe_op(op, want=()):
    rna = op.get_rna_type()
    props = []
    for p in rna.properties:
        if p.identifier == "rna_type":
            continue
        if want and not any(w in p.identifier for w in want):
            continue
        s = p.identifier
        if p.type == "ENUM":
            items = enum_items(p)
            s += "{" + "|".join(items[:10]) + ("|…" if len(items) > 10 else "") + "}"
        else:
            if p.type in ("INT", "FLOAT", "BOOLEAN", "STRING") and not getattr(p, "array_length", 0):
                s += f"={p.default!r}"
        props.append(s)
    return f"{op.idname_py() if hasattr(op, 'idname_py') else '?'}({', '.join(props)})"


def describe(sym):
    """`sym~a,b` narrows an operator's parameters to those containing a or b."""
    sym, _, flt = sym.partition("~")
    want = tuple(w for w in flt.split(",") if w)
    parent, name, obj = resolve(sym)
    rna = getattr(parent, "bl_rna", None)
    if obj is None and rna is not None:
        if name in rna.functions:
            return describe_func(sym, rna.functions[name])
        return describe_prop(sym, rna.properties[name])
    if hasattr(obj, "get_rna_type") and callable(getattr(obj, "get_rna_type")):
        return describe_op(obj, want)
    if hasattr(obj, "bl_rna") and inspect.isclass(obj):
        props = [d for d in obj.bl_rna.properties if d.identifier != "rna_type"]
        fns = list(obj.bl_rna.functions.keys())
        return (f"{sym} (class) props[{len(props)}]: "
                + ", ".join(p.identifier for p in props)
                + (f" | funcs: {', '.join(fns)}" if fns else ""))
    if callable(obj):
        sig = None
        try:
            sig = str(inspect.signature(obj))
        except (TypeError, ValueError):
            pass
        if sig and sig != "(*args, **kwargs)":
            return f"{sym}{sig}"
        # C-implemented callables (bmesh.ops.*) hide the real signature behind
        # *args/**kwargs; it is in the docstring's leading paragraph instead.
        head = (obj.__doc__ or "").strip().split("\n\n")[0]
        head = " ".join(head.split())
        return f"{sym}: {head}" if head else f"{sym}{sig or ''} (no doc)"
    if inspect.ismodule(obj):
        names = [n for n in dir(obj) if not n.startswith("_")]
        return f"{sym} (module): {', '.join(names)}"
    return f"{sym} = {obj!r}"


def run(args):
    lines, ok = [], True
    for sym in args:
        try:
            s = describe(sym)
        except Exception as e:
            s, ok = f"FAIL {sym}: {type(e).__name__}: {e}", False
        lines.append(s if len(s) <= MAX else s[:MAX] + "…")
    return {"ok": ok, "lines": lines}
