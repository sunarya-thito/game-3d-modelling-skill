"""Executable positive and negative surface regression checks for Blender 4.2."""

from array import array
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))
from meshkit import start_empty_scene, write_glb
from surfacekit import (triangle_atlas, smart_unwrap, uv_report, require_uv_metrics, paint_atlas,
                       save_rgba_png, principled_textured, glb_surface_report, imported_surface_report)


def rejected(call, message):
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def pixel_bytes(path):
    """Decode our deterministic unfiltered PNG for color-encoding assertions."""
    data = Path(path).read_bytes()
    offset, compressed = 8, bytearray()
    while offset < len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        if kind == b"IDAT":
            compressed.extend(data[offset + 8:offset + 8 + length])
        offset += length + 12
    raw = zlib.decompress(compressed)
    if raw[0] != 0:
        raise AssertionError("test expects the writer's unfiltered scanline")
    return raw[1:5]


def main():
    spec = importlib.util.spec_from_file_location("surface_example", ROOT / "examples/textured-surface-workflow.py")
    example = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(example)
    start_empty_scene()
    objects, descriptions = example.build_samples()
    rejected(lambda: require_uv_metrics(uv_report(objects[0], 512)), "missing UV gate did not fail")
    # Atlas is measured in world units, including nonuniform object scale.
    objects[0].scale = (1.1, 0.9, 1.2)
    bpy.context.view_layer.update()
    plan = triangle_atlas(objects, 512, gutter_px=5)
    initial_uv = [[tuple(loop.uv) for loop in obj.data.uv_layers.active.data] for obj in objects]
    triangle_atlas(objects, 512, gutter_px=5)
    if initial_uv != [[tuple(loop.uv) for loop in obj.data.uv_layers.active.data] for obj in objects]:
        raise AssertionError("atlas is not deterministic")
    source = [uv_report(obj, 512) for obj in objects]
    for measured in source:
        require_uv_metrics(measured, density_min=5, stretch_max=1.002)
        if abs(measured["density_px_per_world_unit"]["area_weighted_mean"] - plan["density_px_per_world_unit"]) > 1e-3:
            raise AssertionError("measured world density does not match atlas construction")
    for chart in plan["charts"]:
        x0, y0, x1, y1 = chart["cell"]
        if any(min(x - x0, y - y0, x1 - x, y1 - y) < 5.99 for x, y in chart["pixels"]):
            raise AssertionError("triangle lacks the declared cell clearance")
    corrupt = objects[0].data.uv_layers.active.data
    backup = [tuple(loop.uv) for loop in corrupt]
    for loop in corrupt:
        loop.uv = (0.0, 0.0)
    rejected(lambda: require_uv_metrics(uv_report(objects[0], 512)), "zero-area UV gate did not fail")
    for loop, value in zip(corrupt, backup):
        loop.uv = value
    rejected(lambda: require_uv_metrics(source[0], density_min=1e5), "density contract did not fail")
    bad_stretch = dict(source[0], stretch_anisotropy={"min": 1, "max": 4})
    rejected(lambda: require_uv_metrics(bad_stretch, stretch_max=2), "stretch contract did not fail")
    rejected(lambda: triangle_atlas(objects, 32, gutter_px=8), "impossible padding was accepted")
    with tempfile.TemporaryDirectory(prefix="public-surface-checks-") as directory:
        out = Path(directory)
        # Linear 18% gray encodes as 118 in sRGB and 46 in a data texture.
        color = save_rgba_png(out / "gray-color.png", 1, 1, array("f", (0.18, 0.18, 0.18, 0.5)), "sRGB")
        data = save_rgba_png(out / "gray-data.png", 1, 1, array("f", (0.18, 0.18, 0.18, 0.5)), "Non-Color")
        if tuple(pixel_bytes(out / "gray-color.png")) != (118, 118, 118, 128):
            raise AssertionError("sRGB encoding or alpha handling is wrong")
        if tuple(pixel_bytes(out / "gray-data.png")) != (46, 46, 46, 128):
            raise AssertionError("Non-Color data was gamma encoded")
        if color.colorspace_settings.name != "sRGB" or data.colorspace_settings.name != "Non-Color":
            raise AssertionError("image color spaces are wrong")
        albedo_painter, roughness_painter = example.layered_painters(descriptions)
        albedo = paint_atlas(plan, out / "albedo.png", albedo_painter)
        paint_atlas(plan, out / "albedo-repeat.png", albedo_painter)
        if (out / "albedo.png").read_bytes() != (out / "albedo-repeat.png").read_bytes():
            raise AssertionError("procedural image is not deterministic")
        roughness = paint_atlas(plan, out / "roughness.png", roughness_painter, "Non-Color")
        rejected(lambda: principled_textured("BadRoles", albedo, roughness_image=albedo), "conflicting image roles accepted")
        material = principled_textured("SurfaceCheck", albedo, roughness_image=roughness)
        for obj in objects:
            obj.data.materials.append(material)
        exported = write_glb(objects, out / "surface.glb")
        shipping = glb_surface_report(exported, require_data_texture=True)
        # Missing graph connections must fail both the shipping and scene gates.
        shader = material.node_tree.nodes.get("Principled BSDF")
        connection = shader.inputs["Base Color"].links[0]
        from_socket = connection.from_socket
        material.node_tree.links.remove(connection)
        rejected(lambda: imported_surface_report(objects, 512, True), "unlinked albedo passed scene gate")
        untextured = write_glb(objects, out / "missing-albedo.glb")
        rejected(lambda: glb_surface_report(untextured, True), "missing GLB albedo texture passed")
        material.node_tree.links.new(from_socket, shader.inputs["Base Color"])
        start_empty_scene()
        bpy.ops.import_scene.gltf(filepath=str(exported))
        imported = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        result = imported_surface_report(imported, 512, require_data_texture=True)
        for measured in result["uv"]:
            require_uv_metrics(measured, density_min=5, stretch_max=1.002)
            old = next(entry for entry in source if entry["object"] == measured["object"])
            if old["triangles"] != measured["triangles"] or abs(old["world_area"] - measured["world_area"]) > 1e-5:
                raise AssertionError("geometry changed in surface round-trip")
            if abs(old["uv_area"] - measured["uv_area"]) > 1e-6:
                raise AssertionError("UV area changed in surface round-trip")
        # The alternate unwrap path is executed and restores selection/active state.
        target = imported[0]
        bpy.ops.object.select_all(action="DESELECT")
        imported[-1].select_set(True)
        bpy.context.view_layer.objects.active = imported[-1]
        previous = bpy.context.view_layer.objects.active
        unwrapped = smart_unwrap(target, 512, 5)
        require_uv_metrics(unwrapped, density_min=1, stretch_max=10)
        if bpy.context.view_layer.objects.active != previous or bpy.context.selected_objects != [previous]:
            raise AssertionError("unwrap did not restore Object-mode selection")
        print(json.dumps({"passed": True, "blender": bpy.app.version_string, "meshes": len(imported),
                          "glb": shipping, "checks": ["missing UV rejection", "degenerate UV rejection", "density and stretch gates",
                          "world-scale density", "deterministic atlas and PNG", "isolated gutters", "sRGB/data encoding",
                          "conflicting roles rejection", "missing texture rejection", "GLB and imported links",
                          "round-trip geometry and UVs", "explicit-context unwrap"]}, sort_keys=True))


if __name__ == "__main__":
    main()
