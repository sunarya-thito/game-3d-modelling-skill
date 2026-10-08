"""Import a shipping GLB into a clean scene and write a compact JSON manifest."""

from pathlib import Path
import argparse
import json
import sys

import bpy
from mathutils import Vector


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--report", type=Path, required=True)
args = parser.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
meshes = [
    obj for obj in bpy.context.scene.objects
    if obj.type == "MESH" and all(collection.name != "glTF_not_exported" for collection in obj.users_collection)
]
points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
if not points:
    raise RuntimeError("imported GLB contains no mesh bounds")
low = [min(point[axis] for point in points) for axis in range(3)]
high = [max(point[axis] for point in points) for axis in range(3)]
triangles = 0
for obj in meshes:
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
actions = sorted(action.name for action in bpy.data.actions)
armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
report = {
    "input": args.input.name,
    "blender": bpy.app.version_string,
    "meshes": sorted(obj.name for obj in meshes),
    "triangles": triangles,
    "bounds": {"min": low, "max": high, "size": [high[i] - low[i] for i in range(3)]},
    "materials": sorted(material.name for material in bpy.data.materials),
    "actions": actions,
    "armatures": {
        obj.name: sorted(bone.name for bone in obj.data.bones) for obj in armatures
    },
    "objects": sorted(
        obj.name for obj in bpy.context.scene.objects
        if all(collection.name != "glTF_not_exported" for collection in obj.users_collection)
    ),
}
args.report.parent.mkdir(parents=True, exist_ok=True)
args.report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(report, indent=2, sort_keys=True))
