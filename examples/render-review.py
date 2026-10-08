"""Render deterministic multi-view evidence from a re-imported GLB."""

from pathlib import Path
import argparse
import sys

import bpy
from mathutils import Vector


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--input", type=Path, required=True)
parser.add_argument("--out-dir", type=Path, required=True)
parser.add_argument("--size", type=int, default=512)
args = parser.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(args.input.resolve()))
meshes = [
    obj for obj in bpy.context.scene.objects
    if obj.type == "MESH" and all(collection.name != "glTF_not_exported" for collection in obj.users_collection)
]
points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
if not points:
    raise RuntimeError("imported GLB contains no renderable meshes")
low = Vector(tuple(min(point[axis] for point in points) for axis in range(3)))
high = Vector(tuple(max(point[axis] for point in points) for axis in range(3)))
centre = (low + high) * 0.5
radius = max((high - low).length * 0.5, 0.1)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.studio_light = "paint.sl"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.cavity_type = "WORLD"
scene.display.shading.color_type = "MATERIAL"
scene.render.resolution_x = scene.render.resolution_y = args.size
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.world = bpy.data.worlds.new("ReviewWorld")
scene.world.color = (0.055, 0.055, 0.055)

camera_data = bpy.data.cameras.new("ReviewCamera")
camera = bpy.data.objects.new("ReviewCamera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = radius * 2.5
camera.data.clip_start = max(0.001, radius * 0.01)
camera.data.clip_end = radius * 20.0

views = {
    "three-quarter": (1.0, -1.0, 0.75),
    "front": (0.0, -1.0, 0.0),
    "back": (0.0, 1.0, 0.0),
    "left": (-1.0, 0.0, 0.0),
    "right": (1.0, 0.0, 0.0),
    "top": (0.001, 0.0, 1.0),
}
args.out_dir.mkdir(parents=True, exist_ok=True)
for name, direction in views.items():
    outward = Vector(direction).normalized()
    camera.location = centre + outward * radius * 4.0
    camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str((args.out_dir / f"{name}.png").resolve())
    bpy.ops.render.render(write_still=True)

scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.0, 0.0, 0.0)
scene.display.shading.show_shadows = False
scene.display.shading.show_cavity = False
scene.world.color = (1.0, 1.0, 1.0)
scene.render.resolution_x = scene.render.resolution_y = 64
outward = Vector(views["three-quarter"]).normalized()
camera.location = centre + outward * radius * 4.0
camera.rotation_euler = (centre - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = str((args.out_dir / "silhouette-64.png").resolve())
bpy.ops.render.render(write_still=True)

print(f"wrote {len(views)} review views and one silhouette to {args.out_dir.resolve()}")
