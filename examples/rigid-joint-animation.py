"""Create a rigid articulated prop with an exported animation clip."""

from math import radians
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))

from meshkit import MeshDraft, add_profile_loft, create_mesh_object, start_empty_scene, write_glb
from rigkit import JointSpec, create_rigid_hierarchy, keep_world_parent


def box(name, low, high):
    x0, y0, z0 = low
    x1, y1, z1 = high
    draft = MeshDraft(name)
    add_profile_loft(
        draft,
        (
            ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)),
            ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)),
        ),
    )
    return create_mesh_object(draft)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, default=ROOT / "build" / "rigid-joint-animation.glb")
args = parser.parse_args(argv)

start_empty_scene()
joints = create_rigid_hierarchy(
    (
        JointSpec("PropRoot", (0.0, 0.0, 0.0)),
        JointSpec("LidPivot", (-0.9, 0.0, 1.2), parent="PropRoot"),
    )
)
body = box("Housing", (-1.0, -0.6, 0.0), (1.0, 0.6, 1.2))
lid = box("Lid", (-0.9, -0.58, 1.2), (0.9, 0.58, 1.32))
keep_world_parent(body, joints["PropRoot"])
keep_world_parent(lid, joints["LidPivot"])

pivot = joints["LidPivot"]
pivot.rotation_mode = "XYZ"
for frame, angle in ((1, 0.0), (18, radians(-70.0)), (35, 0.0)):
    pivot.rotation_euler.y = angle
    pivot.keyframe_insert("rotation_euler", frame=frame)
pivot.animation_data.action.name = "OpenAndClose"
for curve in pivot.animation_data.action.fcurves:
    for point in curve.keyframe_points:
        point.interpolation = "BEZIER"

scene = __import__("bpy").context.scene
scene.frame_start, scene.frame_end, scene.render.fps = 1, 35, 30
write_glb([joints["PropRoot"]], args.out)
print(f"wrote {args.out.resolve()}")
