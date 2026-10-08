"""Create a two-bone skinned form, normalized weights, and one action."""

from math import radians
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))

from meshkit import MeshDraft, add_profile_loft, create_mesh_object, start_empty_scene, write_glb
from rigkit import JointSpec, bind_weights, create_armature, weight_report


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, default=ROOT / "build" / "skinned-chain-animation.glb")
args = parser.parse_args(argv)

start_empty_scene()
draft = MeshDraft("SkinnedForm")
sections = []
for z, radius in ((0.0, 0.42), (0.6, 0.40), (1.2, 0.34), (1.8, 0.27), (2.4, 0.16)):
    sections.append(((-radius, -radius, z), (radius, -radius, z), (radius, radius, z), (-radius, radius, z)))
add_profile_loft(draft, sections)
mesh = create_mesh_object(draft)

armature = create_armature(
    "DemonstrationRig",
    (
        JointSpec("Root", (0.0, 0.0, 0.0), (0.0, 0.0, 1.2)),
        JointSpec("Tip", (0.0, 0.0, 1.2), (0.0, 0.0, 2.4), parent="Root"),
    ),
)
weights = []
for vertex in mesh.data.vertices:
    blend = min(1.0, max(0.0, (vertex.co.z - 0.8) / 0.8))
    weights.append({"Root": 1.0 - blend, "Tip": blend})
bind_weights(mesh, armature, weights)
report = weight_report(mesh)
if any(report.values()):
    raise RuntimeError(f"weight audit failed: {report}")

tip = armature.pose.bones["Tip"]
tip.rotation_mode = "XYZ"
for frame, angle in ((1, 0.0), (16, radians(28.0)), (31, 0.0)):
    tip.rotation_euler.y = angle
    tip.keyframe_insert("rotation_euler", frame=frame)
armature.animation_data.action.name = "BendLoop"
for curve in armature.animation_data.action.fcurves:
    for point in curve.keyframe_points:
        point.interpolation = "BEZIER"

scene = __import__("bpy").context.scene
scene.frame_start, scene.frame_end, scene.render.fps = 1, 31, 30
write_glb([armature], args.out)
print(f"weight report: {report}")
print(f"wrote {args.out.resolve()}")
