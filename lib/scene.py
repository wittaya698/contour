"""Scene lifecycle, data API only: start empty, gather the build into one
collection, load a saved build back in."""
import bpy


def reset():
    """Empty the file. --factory-startup leaves a cube, light, camera and collection."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.curves, bpy.data.images, bpy.data.collections):
        for block in list(coll):
            coll.remove(block)
    for c in list(bpy.context.scene.collection.children):
        bpy.context.scene.collection.children.unlink(c)


def organize(variant):
    """Put every object in one collection named after the variant. work/scene.blend
    links that collection, so its name is part of the contract (README)."""
    coll = bpy.data.collections.new(variant)
    for o in list(bpy.data.objects):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    bpy.context.scene.collection.children.link(coll)
    bpy.context.view_layer.update()
    return coll


def save_collection(coll, path):
    """Write just the variant's collection (plus what it depends on) to a .blend."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    bpy.data.libraries.write(str(path), {coll})


def load_collections(path):
    """Copy a saved build into the current (empty) scene; returns the collections."""
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.collections = list(src.collections)
    for c in dst.collections:
        bpy.context.scene.collection.children.link(c)
    bpy.context.view_layer.update()
    return dst.collections
