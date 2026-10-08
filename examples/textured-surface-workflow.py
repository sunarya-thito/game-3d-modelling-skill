"""Build layered painted samples, export textured GLB, re-import and render.

blender --background --factory-startup --python-exit-code 1 \
  --python examples/textured-surface-workflow.py -- --out-dir build/textured-surface
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))
from meshkit import MeshDraft, add_profile_loft, create_mesh_object, inspect_topology, start_empty_scene, write_glb
from surfacekit import (triangle_atlas, paint_atlas, principled_textured, uv_report,
                       require_uv_metrics, glb_surface_report, imported_surface_report)


def smoothstep(low, high, value):
    t = max(0.0, min(1.0, (value - low) / (high - low)))
    return t * t * (3 - 2 * t)


def build_samples():
    """Three chamfered, profiled paint samples, not a finished hero asset."""
    objects, descriptions = [], []
    for index, (x, height) in enumerate(((-0.86, 1.12), (0.0, 1.48), (0.86, 1.27))):
        width, depth = 0.65, 0.34
        outline = [(-0.42, -0.5), (0.42, -0.5), (0.5, -0.32), (0.5, 0.32),
                   (0.42, 0.5), (-0.42, 0.5), (-0.5, 0.32), (-0.5, -0.32)]
        sections = []
        for z, scale in ((0.0, 0.94), (0.065, 1.0), (height - 0.15, 0.92), (height, 0.72)):
            sections.append([(x + px * width * scale, py * depth * scale, z) for px, py in outline])
        draft = MeshDraft(f"PaintedSample{index}")
        add_profile_loft(draft, sections)
        objects.append(create_mesh_object(draft))
        descriptions.append({"centre_x": x, "height": height, "half_width": width * 0.5,
                             "half_depth": depth * 0.5})
    return objects, descriptions


def layered_painters(descriptions):
    palette = ((0.028, 0.24, 0.23), (0.025, 0.095, 0.22), (0.40, 0.105, 0.035))
    def albedo(position, normal, piece):
        spec = descriptions[piece]
        x = (position[0] - spec["centre_x"]) / spec["half_width"]
        y = position[1] / spec["half_depth"]
        z = position[2] / spec["height"]
        # Broad pigment gradient, a restrained base contact band, exposed edges,
        # per-piece brush variation and intentionally placed cream chevrons.
        gradient = 0.79 + 0.34 * z
        contact = 0.70 + 0.30 * smoothstep(0.025, 0.17, z)
        edge_coordinate = abs(y) if abs(normal[0]) > 0.8 else abs(x)
        edge = smoothstep(0.71, 0.97, edge_coordinate) * 0.10
        brush = 1 + 0.028 * math.sin(x * 17 + z * 9 + piece * 13)
        color = [component * gradient * contact * brush + edge * warm
                 for component, warm in zip(palette[piece], (0.5, 0.32, 0.14))]
        if abs(normal[1]) > 0.8:
            border = (1 - smoothstep(0.008, 0.018, abs(z - 0.24))) * (1 - smoothstep(0.67, 0.79, abs(x)))
            chevron = (1 - smoothstep(0.012, 0.026, abs(z - (0.68 - 0.15 * abs(x)))))
            chevron *= 1 - smoothstep(0.52, 0.64, abs(x))
            stripe = max(border, chevron) * 0.87
            color = [c * (1 - stripe) + accent * stripe for c, accent in zip(color, (0.75, 0.53, 0.24))]
        return (*color, 1.0)
    def roughness(position, normal, piece):
        spec = descriptions[piece]
        z = position[2] / spec["height"]
        value = 0.61 + 0.12 * (1 - smoothstep(0.02, 0.18, z))
        value += 0.035 * math.sin(position[0] * 11 + piece * 7)
        return (value, value, value, 1.0)
    return albedo, roughness


def render_imported(out_dir, objects):
    """Render actual imported texture nodes with a pinned CPU Cycles setup."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 32
    scene.cycles.seed = 17
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 840, 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.world = bpy.data.worlds.new("SurfaceReviewWorld")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.065, 0.075, 0.10, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.55
    for name, location, energy, size in (("Key", (-3, -4, 5), 650, 4), ("Fill", (4, -1, 3), 280, 3)):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy, light_data.shape, light_data.size = energy, "DISK", size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((0, 0, 0.65)) - light.location).to_track_quat("-Z", "Y").to_euler()
    camera = bpy.data.objects.new("SurfaceReviewCamera", bpy.data.cameras.new("SurfaceReviewCamera"))
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.type, camera.data.ortho_scale = "ORTHO", 3.3
    camera.location = (2.8, -6, 2.9)
    camera.rotation_euler = (Vector((0, 0, 0.73)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(out_dir / "imported-surface.png")
    bpy.ops.render.render(write_still=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "build" / "textured-surface")
    parser.add_argument("--texture-size", type=int, default=1024)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    start_empty_scene()
    bpy.context.scene.unit_settings.system = "METRIC"
    objects, descriptions = build_samples()
    topology = {obj.name: inspect_topology(obj) for obj in objects}
    for values in topology.values():
        if any(values[key] for key in ("boundary_edges", "nonmanifold_edges", "degenerate_faces")):
            raise RuntimeError("source topology gate failed")
    plan = triangle_atlas(objects, args.texture_size, gutter_px=8)
    source_uv = [uv_report(obj, args.texture_size) for obj in objects]
    for values in source_uv:
        require_uv_metrics(values, density_min=20, stretch_max=1.002)
    albedo_painter, roughness_painter = layered_painters(descriptions)
    albedo = paint_atlas(plan, out_dir / "albedo.png", albedo_painter)
    roughness = paint_atlas(plan, out_dir / "roughness.png", roughness_painter, "Non-Color")
    material = principled_textured("LayeredPaint", albedo, roughness_image=roughness)
    for obj in objects:
        obj.data.materials.append(material)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "textured-surface.blend"))
    output = write_glb(objects, out_dir / "textured-surface.glb")
    shipping = glb_surface_report(output, require_data_texture=True)
    start_empty_scene()
    bpy.ops.import_scene.gltf(filepath=str(output))
    imported = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    reimported = imported_surface_report(imported, args.texture_size, require_data_texture=True)
    by_name = {value["object"]: value for value in source_uv}
    for observed in reimported["uv"]:
        require_uv_metrics(observed, density_min=20, stretch_max=1.002)
        expected = by_name[observed["object"]]
        for key in ("world_area", "uv_area"):
            if abs(expected[key] - observed[key]) > 1e-5:
                raise AssertionError(f"re-import changed {observed['object']} {key}")
        if expected["triangles"] != observed["triangles"]:
            raise AssertionError("re-import changed triangle count")
    if not args.skip_render:
        render_imported(out_dir, imported)
    report = {
        "asset": "textured-surface-technique-example", "blender": bpy.app.version_string,
        "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "helper_sha256": hashlib.sha256((ROOT / "scripts/blender/surfacekit.py").read_bytes()).hexdigest(),
        "topology": topology, "source_uv": source_uv,
        "atlas": {key: value for key, value in plan.items() if key != "charts"},
        "paint_layers": ["large-form pigment gradient", "base contact response", "exposed-edge pigment",
                         "deterministic per-piece brush variation", "localized cream insignia"],
        "textures": {name: {"size": args.texture_size, "sha256": hashlib.sha256((out_dir / name).read_bytes()).hexdigest()}
                     for name in ("albedo.png", "roughness.png")},
        "glb": shipping, "reimport": reimported, "passed": True,
        "limitations": ["technique example, not independently approved production art",
                        "no bake, no engine integration, no target-device mip validation",
                        "triangle atlas trades packing efficiency for deterministic isolated gutters"],
    }
    (out_dir / "surface-report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": True, "out_dir": str(out_dir), "triangles": sum(r["triangles"] for r in source_uv),
                      "glb": shipping, "density": source_uv[0]["density_px_per_world_unit"]}, sort_keys=True))


if __name__ == "__main__":
    main()
