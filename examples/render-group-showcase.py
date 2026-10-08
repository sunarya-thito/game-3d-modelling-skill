"""Compose four supplied GLBs in a new studio scene and render a still/loop.

This script contains no bundled model paths. Pass assets explicitly after ``--``.
It is intended for rights-cleared showcase material, not as an asset generator.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import math
import sys

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--cow", type=Path, required=True)
    parser.add_argument("--goat", type=Path, required=True)
    parser.add_argument("--chicken", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--still-size", type=int, default=1600)
    parser.add_argument("--animation-size", type=int, default=768)
    parser.add_argument("--frames", type=int, default=24)
    parser.add_argument("--still-only", action="store_true")
    return parser.parse_args(argv)


def import_group(label: str, path: Path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    created = [obj for obj in bpy.data.objects if obj not in before]
    created = [
        obj for obj in created
        if all(collection.name != "glTF_not_exported" for collection in obj.users_collection)
    ]
    if not created:
        raise RuntimeError(f"{path}: import created no usable objects")
    for obj in created:
        obj.name = f"{label}_{obj.name}"
    roots = [obj for obj in created if obj.parent is None]
    group = bpy.data.objects.new(f"{label}_Group", None)
    bpy.context.scene.collection.objects.link(group)
    for root in roots:
        world = root.matrix_world.copy()
        root.parent = group
        root.matrix_world = world
    armatures = [obj for obj in created if obj.type == "ARMATURE"]
    return group, armatures


def studio_material(name, rgba, roughness=0.8, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    return material


def add_cyclorama():
    x0, x1 = -30.0, 30.0
    floor_y = 2.0
    radius = 4.0
    profile = [(-20.0, -0.04)]
    for step in range(17):
        angle = math.pi * 0.5 * step / 16.0
        profile.append(
            (
                floor_y + radius * math.sin(angle),
                -0.04 + radius * (1.0 - math.cos(angle)),
            )
        )
    profile.append((floor_y + radius, 20.0))
    vertices = [(x, y, z) for y, z in profile for x in (x0, x1)]
    faces = []
    for index in range(len(profile) - 1):
        a = index * 2
        faces.append((a, a + 1, a + 3, a + 2))
    mesh = bpy.data.meshes.new("StudioSweep")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("StudioSweep", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(studio_material("StudioBackdrop", (0.09, 0.14, 0.17, 1.0)))
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def add_area(name, location, energy, size, colour):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = colour
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0.0, 0.0, 1.2)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def set_bone_loop(armature, bone_name, axis, samples):
    bone = armature.pose.bones.get(bone_name)
    if bone is None:
        return False
    bone.rotation_mode = "XYZ"
    base = bone.rotation_euler.copy()
    for frame, degrees in samples:
        bone.rotation_euler = base.copy()
        bone.rotation_euler[axis] += math.radians(degrees)
        bone.keyframe_insert("rotation_euler", index=axis, frame=frame)
    return True


def set_bone_location_loop(armature, bone_name, axis, samples):
    bone = armature.pose.bones.get(bone_name)
    if bone is None:
        return False
    base = bone.location.copy()
    for frame, offset in samples:
        bone.location = base.copy()
        bone.location[axis] += offset
        bone.keyframe_insert("location", index=axis, frame=frame)
    return True


def cycle_samples(end_frame, fn, steps=8):
    """Sample one seamless cycle; the duplicate endpoint is not rendered."""

    return tuple(
        (1.0 + end_frame * step / steps, fn(step / steps))
        for step in range(steps + 1)
    )


def stride(end_frame, phase, forward, backward):
    def value(t):
        wave = math.sin(math.tau * (t + phase))
        return wave * (forward if wave >= 0.0 else backward)

    return cycle_samples(end_frame, value)


def wave(end_frame, phase, amplitude, frequency=1.0, offset=0.0):
    return cycle_samples(
        end_frame,
        lambda t: offset + amplitude * math.sin(math.tau * (t * frequency + phase)),
    )


def polish_action(armature, label):
    if not armature.animation_data or not armature.animation_data.action:
        return
    action = armature.animation_data.action
    action.name = f"{label}_Walk"
    for curve in action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


def animate_animals(armatures, end_frame):
    for label, rigs in armatures.items():
        if not rigs:
            continue
        rig = rigs[0]
        if label == "Cow":
            # A deliberate four-beat walk. Each hoof advances in turn instead
            # of the diagonal pairs moving as a trot.
            for bone, phase in (("LegBL", 0.00), ("LegFL", 0.25), ("LegBR", 0.50), ("LegFR", 0.75)):
                set_bone_loop(rig, bone, 0, stride(end_frame, phase, 15.0, 10.0))
            set_bone_location_loop(rig, "Body", 2, wave(end_frame, 0.00, 0.025, frequency=2.0, offset=0.018))
            set_bone_loop(rig, "Body", 1, wave(end_frame, 0.00, 1.8))
            set_bone_loop(rig, "Body", 0, wave(end_frame, 0.25, 1.2, frequency=2.0))
            set_bone_loop(rig, "Neck", 0, wave(end_frame, 0.12, 3.4, frequency=2.0))
            set_bone_loop(rig, "Head", 0, wave(end_frame, 0.62, 2.4, frequency=2.0))
            set_bone_loop(rig, "Tail", 1, wave(end_frame, 0.10, 10.0))
            set_bone_loop(rig, "Tail2", 1, wave(end_frame, 0.22, 13.0))
            set_bone_loop(rig, "Tail3", 1, wave(end_frame, 0.34, 16.0))
        elif label == "Goat":
            # A lighter four-beat walk with more lift and a small alert head
            # counter-motion, sequenced opposite the cow's measured stride.
            for bone, phase in (("LegBR", 0.00), ("LegFR", 0.25), ("LegBL", 0.50), ("LegFL", 0.75)):
                set_bone_loop(rig, bone, 0, stride(end_frame, phase, 19.0, 12.0))
            set_bone_location_loop(rig, "Body", 2, wave(end_frame, 0.00, 0.045, frequency=2.0, offset=0.025))
            set_bone_loop(rig, "Body", 0, wave(end_frame, 0.25, 2.5, frequency=2.0))
            set_bone_loop(rig, "Body", 1, wave(end_frame, 0.00, 1.6))
            set_bone_loop(rig, "Neck", 0, wave(end_frame, 0.12, 4.8, frequency=2.0))
            set_bone_loop(rig, "Head", 0, wave(end_frame, 0.62, 3.8, frequency=2.0))
            set_bone_loop(rig, "EarL", 2, wave(end_frame, 0.18, 4.0, frequency=2.0))
            set_bone_loop(rig, "EarR", 2, wave(end_frame, 0.68, 4.0, frequency=2.0))
            set_bone_loop(rig, "Beard", 0, wave(end_frame, 0.30, 5.0, frequency=2.0))
            set_bone_loop(rig, "Tail", 1, wave(end_frame, 0.05, 8.0))
            set_bone_loop(rig, "Tail2", 1, wave(end_frame, 0.20, 11.0))
            set_bone_loop(rig, "Tail3", 1, wave(end_frame, 0.35, 13.0))
        elif label == "Chicken":
            # Alternating biped steps, with the body carried over the planted
            # side and the head counter-rotated to keep its gaze readable.
            set_bone_loop(rig, "LegL", 0, stride(end_frame, 0.00, 24.0, 15.0))
            set_bone_loop(rig, "LegR", 0, stride(end_frame, 0.50, 24.0, 15.0))
            set_bone_location_loop(rig, "Body", 2, wave(end_frame, 0.00, 0.040, frequency=2.0, offset=0.022))
            set_bone_loop(rig, "Body", 1, wave(end_frame, 0.00, 3.2))
            set_bone_loop(rig, "Body", 0, wave(end_frame, 0.25, 2.2, frequency=2.0))
            set_bone_loop(rig, "Neck", 0, wave(end_frame, 0.10, 6.0, frequency=2.0))
            set_bone_loop(rig, "Head", 0, wave(end_frame, 0.60, 5.0, frequency=2.0))
            set_bone_loop(rig, "WingL", 1, wave(end_frame, 0.00, 3.8))
            set_bone_loop(rig, "WingR", 1, wave(end_frame, 0.50, 3.8))
            set_bone_loop(rig, "Tail", 1, wave(end_frame, 0.50, 5.0))
            set_bone_loop(rig, "Tail2", 1, wave(end_frame, 0.62, 6.5))
            set_bone_loop(rig, "Tail3", 1, wave(end_frame, 0.74, 8.0))
            set_bone_loop(rig, "Comb", 0, wave(end_frame, 0.22, 2.0, frequency=2.0))
            set_bone_loop(rig, "Wattle", 0, wave(end_frame, 0.35, 3.0, frequency=2.0))
        polish_action(rig, label)


def configure_scene(args):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.resolution_percentage = 100
    scene.render.fps = args.frames
    scene.frame_start = 1
    scene.frame_end = args.frames
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.18
    world = bpy.data.worlds.new("StudioWorld")
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.055, 0.075, 0.10, 1.0)
    background.inputs["Strength"].default_value = 0.55
    scene.world = world
    add_area("FrontSoftbox", (0.0, -8.5, 6.5), 850.0, 7.0, (1.0, 0.94, 0.86))
    add_area("Key", (5.5, -4.5, 7.5), 1150.0, 5.5, (1.0, 0.82, 0.66))
    add_area("Fill", (-5.5, -4.0, 4.8), 1250.0, 6.0, (0.62, 0.78, 1.0))
    add_area("Rim", (0.5, 4.5, 7.5), 1200.0, 4.0, (0.76, 0.88, 1.0))
    camera_data = bpy.data.cameras.new("ShowcaseCamera")
    camera = bpy.data.objects.new("ShowcaseCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (7.6, -10.5, 5.8)
    target = Vector((0.0, -0.15, 1.45))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 56.0
    scene.camera = camera
    return scene


def main():
    args = parse_args()
    for path in (args.environment, args.cow, args.goat, args.chicken):
        if not path.is_file():
            raise FileNotFoundError(path)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    environment, _ = import_group("Environment", args.environment)
    cow, cow_rigs = import_group("Cow", args.cow)
    goat, goat_rigs = import_group("Goat", args.goat)
    chicken, chicken_rigs = import_group("Chicken", args.chicken)

    environment.location = (0.0, 0.65, 0.0)
    cow.location = (-1.45, -1.75, 0.0)
    cow.rotation_euler.z = math.radians(-8.0)
    goat.location = (0.55, -1.92, 0.0)
    goat.rotation_euler.z = math.radians(8.0)
    chicken.location = (1.9, -1.45, 0.0)
    chicken.rotation_euler.z = math.radians(15.0)

    add_cyclorama()
    scene = configure_scene(args)
    scene.render.resolution_x = scene.render.resolution_y = args.still_size
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str((args.out_dir / "group-showcase.png").resolve())
    # Render the hero before creating any walk keys. It is therefore the clean
    # imported rest pose, independent of the loop's strongest deformation.
    scene.frame_set(1)
    bpy.ops.render.render(write_still=True)

    if args.still_only:
        bpy.ops.wm.save_as_mainfile(filepath=str((args.out_dir / "group-showcase.blend").resolve()))
        print(f"wrote showcase still to {args.out_dir.resolve()}")
        return

    animate_animals({"Cow": cow_rigs, "Goat": goat_rigs, "Chicken": chicken_rigs}, args.frames)
    scene.render.resolution_x = scene.render.resolution_y = args.animation_size
    scene.render.filepath = str((args.out_dir / "frames" / "frame-").resolve())
    (args.out_dir / "frames").mkdir(parents=True, exist_ok=True)
    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str((args.out_dir / "group-showcase.blend").resolve()))
    bpy.ops.render.render(animation=True)
    print(f"wrote showcase still and {args.frames} animation frames to {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()
