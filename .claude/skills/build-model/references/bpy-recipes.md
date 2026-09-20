# bpy / bmesh recipes — Blender 5.2.1 LTS

Patterns that have actually been run against **this** install. Blender 5.2.1 was
built 2026-08-25, after the assistant's knowledge cutoff, so recalled API
details are guesses (ADR 0008).

Every entry carries a status:

- **VERIFIED** — executed successfully against this install on the date shown.
- **UNVERIFIED** — plausible but not yet run here. **Confirm with
  `./contour api <symbol>` before using.** Never present one as fact.

When you make an UNVERIFIED pattern work, change its status and date it. When
one fails, replace it with what actually worked — a wrong recipe is worse than
no recipe, because it reads as authoritative.

---

## Environment facts — VERIFIED 2026-09-20

```
Blender 5.2.1 LTS   (build 2026-08-25)
bundled Python      3.13.13        # NOT the system 3.14.7 — do not assume parity
binary              /Applications/Blender.app/Contents/MacOS/Blender
```

## Trap: enum introspection under-reports — VERIFIED 2026-09-20

```python
[i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
# -> ['BLENDER_EEVEE']     <-- WRONG, incomplete

scene.render.engine = 'BLENDER_WORKBENCH'   # works
scene.render.engine = 'CYCLES'              # works
```

Render engines are registered dynamically, so the static enum lists only one.
**Assignment is the real test, not the enum.** Expect this for other
dynamically-populated enums — if `./contour api` shows a suspiciously short
enum list, try the assignment before believing it.

## bmesh.ops signatures — VERIFIED 2026-09-20

Probed from this install; argument names are exact.

```python
bmesh.ops.create_cube(bm, size=0.0, matrix=Matrix(), calc_uvs=False)
bmesh.ops.inset_region(bm, faces=[], faces_exclude=[], use_boundary=False,
                       use_even_offset=False, use_interpolate=False,
                       use_relative_offset=False, ...)
bmesh.ops.bevel(bm, geom=[], offset=0.0, offset_type='OFFSET',
                profile_type='SUPERELLIPSE', segments=0, profile=0.0,
                affect='VERTICES', ...)
bmesh.ops.solidify(bm, geom=[], thickness=0.0)
bmesh.ops.recalc_face_normals(bm, faces=[])
bmesh.ops.remove_doubles(bm, verts=[], use_connected=False, dist=0.0)
bmesh.ops.subdivide_edges(bm, edges=[], smooth=0.0, smooth_falloff='SMOOTH',
                          fractal=0.0, along_normal=0.0, cuts=0, seed=0, ...)
```

Note `bevel(affect='VERTICES')` — the default affects **vertices**, not edges.
Pass `affect='EDGES'` for the usual edge bevel.

## Mesh.from_pydata — VERIFIED 2026-09-20

```python
Mesh.from_pydata(self, vertices, edges, faces, shade_flat=True)
```

`shade_flat=True` is the default in 5.2 — pass `shade_flat=False` for smooth
shading rather than reaching for a `shade_smooth` operator (which is banned by
ADR 0004 anyway).

## Camera types — VERIFIED 2026-09-20

```python
['PERSP', 'ORTHO', 'PANO', 'CUSTOM']
cam_data.type = 'ORTHO'
cam_data.ortho_scale = 6      # world units across the frame
```

## Workbench headless rendering — VERIFIED 2026-09-20

Workbench **does** render under `--background` on this machine (macOS/Metal).
Shading options confirmed present:

```python
sc.render.engine = 'BLENDER_WORKBENCH'
d = sc.display.shading
d.light = 'STUDIO'          # options: STUDIO | MATCAP | FLAT
d.show_cavity = True        # reads form/topology without lighting
d.show_object_outline = True
```

### Measured cost — VERIFIED 2026-09-20

```
first render in a process : 0.45s   (GPU context init; up to ~1.5s with shading opts)
each render after that    : 0.02s
whole invocation, 4 views : ~1.7s wall, including Blender startup
```

**Therefore: render all four sheet views inside ONE Blender process.** Four
separate invocations pay startup four times (~6s) for no benefit.

EEVEE measured at 1.42s for the same trivial scene — on simple geometry it is
**not** meaningfully slower than Workbench. Workbench is chosen for needing no
lights or materials and producing no denoising artifacts, not for speed.

## glTF export operator — VERIFIED present 2026-09-20

`bpy.ops.export_scene.gltf` and `bpy.ops.import_scene.gltf` both exist.
Confirmed parameters include:

```python
filepath, export_format, use_selection, export_yup, export_apply
```

`export_yup=True` is the Blender-Z-up → glTF-Y-up conversion, and `export_apply`
applies modifiers. Both matter for the round-trip check (ADR 0006).

These are `bpy.ops` calls with no data-API equivalent, so they belong in
`lib/ops_whitelist.py`.

---

# UNVERIFIED — confirm before use

## Manifold / loose-geometry checks

```python
non_manifold = [e for e in bm.edges if not e.is_manifold]
loose_verts  = [v for v in bm.verts if not v.link_edges]
loose_edges  = [e for e in bm.edges if not e.link_faces]
ngons        = [f for f in bm.faces if len(f.verts) > 4]
```

Attribute names are long-standing but have not been run here yet.

## Modifiers via the data API (not operators)

```python
m = obj.modifiers.new(name="Bevel", type='BEVEL')
m.width = 0.002
```

The modifier `type` enum on this build is long and includes many
`GREASE_PENCIL_*` entries; confirm the exact identifier with `./contour api`
before assuming `'BEVEL'`, `'SUBSURF'` or `'MIRROR'`.

## Applying transforms without operators

Needed for the `scale_applied` / `rotation_applied` spec checks. The data-API
route is to bake `obj.matrix_world` into mesh vertices and reset the matrix —
not yet written or run here. If only an operator route exists, it goes on the
whitelist with a note.

## UV unwrapping

Almost certainly operator-only (`bpy.ops.uv.*`), which means whitelist plus
`lib.ctx_override`. Not yet attempted headlessly — context requirements for UV
operators under `--background` are the main open risk in this pipeline.
