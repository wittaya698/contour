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
Seen again 2026-09-20: `view_transform` lists only `NONE` yet `'Standard'` assigns,
and the glTF operator's `export_format` lists `{}` yet `'GLB'` works.
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

## `./contour api` reading guide — VERIFIED 2026-09-20

- `bmesh.ops.*` are C callables whose `inspect.signature` is just `(*args, **kwargs)`;
  the real signature and the return dict are in the docstring, which `api` prints.
- Operators: `./contour api 'bpy.ops.export_scene.gltf~yup,apply'` narrows an
  operator to the parameters containing those substrings (the full list is ~100).
- Enum values shown may be incomplete (see the trap above).

## bmesh.ops signatures, second batch — VERIFIED 2026-09-20

```python
create_uvsphere(bm, u_segments=0, v_segments=0, radius=0.0, matrix=Matrix(), calc_uvs=False) -> dict(verts=[])
create_cone(bm, cap_ends=False, cap_tris=False, segments=0, radius1=0.0, radius2=0.0,
            depth=0.0, matrix=Matrix(), calc_uvs=False) -> dict(verts=[])
find_doubles(bm, verts=[], keep_verts=[], use_connected=False, dist=0.0) -> dict(targetmap={})
reverse_faces(bm, faces=[], flip_multires=False)
translate(bm, vec=Vector(), space=Matrix(), verts=[], use_shapekey=False)
scale(bm, vec=Vector(), space=Matrix(), verts=[], use_shapekey=False)
```

Measured behaviour: `create_cube(size=1.0)` is a unit cube (scale it to size it);
`create_uvsphere(radius=r)` is a true radius. A UV sphere of `u` segments and `v`
rings has `u*(v-2)` quads and `2u` pole triangles, so `quads_min_pct: 90` needs
`v >= 20` rings. bmesh element sequences need `ensure_lookup_table()` before indexing.

## Mesh checks — VERIFIED 2026-09-20 (moved up from UNVERIFIED)

Each is exercised by `verify.py` and provoked by a `lib/mutants.py` mutant:

```python
not e.is_manifold                 # non-manifold / boundary / wire edge
not v.link_edges                  # loose vertex
not e.link_faces                  # loose edge
len(f.verts) > 4                  # n-gon
bmesh.ops.find_doubles(...)["targetmap"]
# outward normals: bm.copy(); recalc_face_normals on the copy; count faces whose
# normal.dot(recomputed) < 0
```

## Evaluated mesh, no operators — VERIFIED 2026-09-20

```python
dg = bpy.context.evaluated_depsgraph_get()
me = obj.evaluated_get(dg).to_mesh()    # includes modifiers; call to_mesh_clear() after
bm = bmesh.new(); bm.from_mesh(me)
```

## Saving and loading a build with the data API — VERIFIED 2026-09-20

```python
bpy.data.libraries.write(str(path), {collection})        # only that collection + deps
with bpy.data.libraries.load(str(path), link=False) as (src, dst):
    dst.collections = list(src.collections)              # then link to scene.collection.children
```

Emptying the factory scene without `wm.read_factory_settings`: remove every object,
then every datablock in meshes / materials / lights / cameras / curves / images /
collections, then unlink the scene's child collections (`lib/scene.py`).

## Materials — VERIFIED 2026-09-20

`Material.use_nodes` defaults to **False** in 5.2.1. Setting it True creates a node
tree with a node named `"Principled BSDF"`; set `inputs["Base Color"]` and
`inputs["Roughness"]` there. `diffuse_color` drives Workbench renders and Principled
drives glTF export. Names and slot counts survive export and re-import.

## Rendering — VERIFIED 2026-09-20

- **Workbench final render does not draw wire-display objects** (`display_type='WIRE'`,
  edge-only meshes). A grid or ruler built that way is simply absent. `lib/cmd_render.py`
  projects world points with `world_to_camera_view(scene, cam_obj, co)` and paints
  them onto the pixels instead, only where the render is still background.
- `render.render(write_still=True)` works under `ctx_override.call`.
- `scene.render.dither_intensity = 0` cut a 1024 sheet from 591 KB to 93 KB.
- `scene.view_settings.view_transform = 'Standard'` keeps material colours flat.
- numpy is present in Blender's Python. Image compositing:
  `img.pixels.foreach_get(buf)` / `img.pixels.foreach_set(buf)` with a float32
  `H*W*4` array whose row 0 is the bottom; `img.filepath_raw`, `img.file_format`,
  `img.save()`.
- The top view sets `rotation_euler = (0, 0, 0)` explicitly (straight down, +Y up the
  frame, confirmed in the sheet). A track-to aim straight down was NOT tried.

## glTF export / import — VERIFIED 2026-09-20

```python
export_scene.gltf(filepath=..., export_format='GLB', use_selection=False, use_visible=False,
                  export_yup=True, export_apply=True, export_materials='EXPORT',
                  export_cameras=False, export_lights=False)
import_scene.gltf(filepath=...)
```

Axis mapping: Blender X, Z, Y become glTF X, Y, Z, so width is glTF X, height Y, depth Z.
Verified by measuring the file itself (`lib/glb.py`) on an asymmetric fixture. Only the
extents were checked; the sign of the Y-to-Z flip (front facing +Z) was not. An importer re-triangulates and splits
vertices, so re-imported topology is not comparable, but triangle count is.

## Applying transforms without operators

`Mesh.transform(matrix, shape_keys=False)` exists (confirmed by `api`). Used by
`lib/kit.bake_transform`, which has **not yet been run**: UNVERIFIED until a build uses it.

---

# UNVERIFIED — confirm before use

## Modifiers via the data API (not operators)

```python
m = obj.modifiers.new(name="Bevel", type='BEVEL')
m.width = 0.002
```

The modifier `type` enum on this build is long and includes many
`GREASE_PENCIL_*` entries; confirm the exact identifier with `./contour api`
before assuming `'BEVEL'`, `'SUBSURF'` or `'MIRROR'`.

## UV unwrapping

Almost certainly operator-only (`bpy.ops.uv.*`), which means whitelist plus
`lib.ctx_override`. Not yet attempted headlessly — context requirements for UV
operators under `--background` are the main open risk in this pipeline. `verify.py`
FAILS a spec that requires UV overlap checking rather than skipping it.
