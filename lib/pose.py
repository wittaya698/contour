"""A bone's turn, in the spec's words and in Blender's (ADR 0023, issue 52).

The spec writes a key pose as `[x, y, z]` degrees about the model's X, Y and
Z, in the parent's frame, from rest, applied X then Y then Z. A bone keys its
turn about its own axes, and `kit.rig()` stands every bone up +Z with no roll,
so a bone's X is the model's X, its Y the model's Z and its Z the model's -Y.
This module is the one place that knows it: `kit` keys through `turn` and the
gather reads back through `read`, so the two cannot disagree.

Keyed in the order `XZY` because, for a bone standing up, that is the model's
`XYZ` written on the bone's axes: each of the spec's three angles lands on one
channel of its own, and the frames between keys move each the way it reads.
"""
import math

from mathutils import Euler

ORDER = "XZY"


def _frame(bone):
    """The bone's rest axes, in the model's: the turn from one to the other."""
    return bone.matrix_local.to_3x3()


def turn(pose_bone, degrees):
    """Set `pose_bone` turned by `degrees` about the model's axes, from rest."""
    b = _frame(pose_bone.bone)
    model = Euler([math.radians(d) for d in degrees], "XYZ").to_matrix()
    pose_bone.rotation_mode = ORDER
    pose_bone.rotation_euler = (b.inverted() @ model @ b).to_euler(ORDER)


def read(pose_bone):
    """How far `pose_bone` stands turned from rest in its parent's frame, as
    the spec writes it: degrees about the model's X, Y and Z.

    Read off the evaluated pose, not off the keys, so what is checked is where
    the bone went.
    """
    bone, parent = pose_bone.bone, pose_bone.parent
    rest, posed = bone.matrix_local, pose_bone.matrix
    if parent:
        rest = parent.bone.matrix_local.inverted() @ rest
        posed = parent.matrix.inverted() @ posed
    local = (rest.inverted() @ posed).to_3x3()
    b = _frame(bone)
    return tuple(math.degrees(a) for a in (b @ local @ b.inverted()).to_euler("XYZ"))
