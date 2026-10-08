"""Build a GLB animation example plus runtime-channel sidecar.

Run from the repository root:
  blender --background --factory-startup --python-exit-code 1 \
    --python examples/animation-channels.py -- --out-dir build/animation-channels
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))

from animationkit import (  # noqa: E402
    assert_exported_evidence,
    configure_scene_timing,
    export_glb,
    keyframe_morph,
    keyframe_object_transform,
    load_manifest,
    reimport_channel_evidence,
    set_interpolation,
    source_channel_evidence,
    write_manifest,
)


def arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=ROOT / "build" / "animation-channels")
    return parser.parse_args(values)


def _material() -> bpy.types.Material:
    material = bpy.data.materials.new("RuntimeSurface")
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.10, 0.32, 0.72, 1.0)
    shader.inputs["Roughness"].default_value = 0.55
    emission = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
    if emission is not None:
        emission.default_value = (0.04, 0.20, 0.90, 1.0)
    strength = shader.inputs.get("Emission Strength")
    if strength is not None:
        strength.default_value = 0.0
    material["runtime_emission_parameter"] = "demo.emission_strength"
    material["runtime_texture_parameter"] = "demo.atlas_frame"
    return material


def _animated_marker(material: bpy.types.Material) -> bpy.types.Object:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.55, location=(-1.0, 0.0, 0.0))
    obj = bpy.context.object
    obj.name = "AnimatedMarker"
    obj.data.name = "AnimatedMarkerMesh"
    obj.data.materials.append(material)
    keyframe_object_transform(obj, 1, rotation_euler=(0.0, 0.0, 0.0))
    keyframe_object_transform(obj, 25, rotation_euler=(0.0, math.pi, math.pi * 0.25))
    keyframe_object_transform(obj, 49, rotation_euler=(0.0, math.tau, 0.0))
    set_interpolation(obj, "LINEAR")
    obj.animation_data.action.name = "MarkerTurn"
    return obj


def _morph_badge(material: bpy.types.Material) -> bpy.types.Object:
    vertices = [
        (-0.65, -0.22, -0.65),
        (0.65, -0.22, -0.65),
        (0.65, -0.22, 0.65),
        (-0.65, -0.22, 0.65),
        (-0.65, 0.22, -0.65),
        (0.65, 0.22, -0.65),
        (0.65, 0.22, 0.65),
        (-0.65, 0.22, 0.65),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    ]
    mesh = bpy.data.meshes.new("MorphBadgeMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new("MorphBadge", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (1.0, 0.0, 0.0)
    obj.data.materials.append(material)
    obj.shape_key_add(name="Basis")
    pulse = obj.shape_key_add(name="Pulse")
    for vertex in pulse.data:
        if vertex.co.z > 0.0:
            vertex.co.z *= 1.35
            vertex.co.y *= 1.8
    keyframe_morph(obj, "Pulse", 1, 0.0)
    keyframe_morph(obj, "Pulse", 25, 1.0)
    keyframe_morph(obj, "Pulse", 49, 0.0)
    set_interpolation(obj.data.shape_keys, "BEZIER")
    obj.data.shape_keys.animation_data.action.name = "BadgePulse"
    return obj


def build(out_dir: str | Path) -> dict[str, object]:
    output = Path(out_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(ROOT / "templates" / "animation-manifest.json")
    write_manifest(manifest, output / "animation-manifest.json")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    configure_scene_timing(1, 49, manifest["export"]["fps"])
    material = _material()
    marker = _animated_marker(material)
    badge = _morph_badge(material)

    source = source_channel_evidence(manifest)
    assert_exported_evidence(manifest, source)
    glb = export_glb((marker, badge), output / "animation-channels.glb")
    reimported = reimport_channel_evidence(glb, manifest)
    assert_exported_evidence(manifest, reimported)

    report = {
        "glb": str(glb),
        "sidecar": str(output / "animation-manifest.json"),
        "source": source,
        "reimported": reimported,
    }
    (output / "animation-evidence.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    report = build(arguments().out_dir)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
