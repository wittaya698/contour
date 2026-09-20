"""Fixture build: plinth + pillar + sphere, all touching, base on the floor."""
from lib import kit

stone = kit.material("stone", "#8A8F98")
accent = kit.material("accent", "#D9822B")

kit.add("plinth", kit.box_bm((120, 100, 40)), at_mm=(0, 0, 20), mat=stone)
kit.add("pillar", kit.box_bm((40, 40, 100)), at_mm=(0, 0, 90), mat=stone)
kit.add("cap", kit.sphere_bm(30, segments=32, rings=24), at_mm=(0, 0, 170), mat=accent,
        smooth=True)
