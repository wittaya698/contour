"""Fixture build: plinth + pillar + sphere, base on the floor.

The pillar reaches 5 mm into the plinth and 5 mm into the cap, so each joint
has a seam: a ring where the surfaces cross, not a face where they meet. Each
origin sits on the centre of the seam with its parent (ADR 0023).
"""
from lib import kit

stone = kit.material("stone", "#8A8F98")
accent = kit.material("accent", "#D9822B")

kit.add("plinth", kit.box_bm((120, 100, 40)), at_mm=(0, 0, 20), mat=stone,
        pivot_mm=(0, 0, 40))
kit.add("pillar", kit.box_bm((40, 40, 110)), at_mm=(0, 0, 90), mat=stone,
        pivot_mm=(0, 0, 145))
kit.add("cap", kit.sphere_bm(30, segments=32, rings=24), at_mm=(0, 0, 170), mat=accent,
        smooth=True)

kit.rig()
