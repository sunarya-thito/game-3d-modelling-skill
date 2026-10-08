"""Headless Blender regression checks for the animation-channel example."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))

from animationkit import (  # noqa: E402
    assert_exported_evidence,
    exported_bone_channel,
    exported_morph_channel,
    exported_transform_channel,
    load_manifest,
    runtime_effect_channel,
    runtime_material_channel,
    runtime_texture_channel,
    runtime_visibility_channel,
    validate_manifest,
)


def _load_example():
    path = ROOT / "examples" / "animation-channels.py"
    spec = importlib.util.spec_from_file_location("animation_channels_example", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    manifest = load_manifest(ROOT / "templates" / "animation-manifest.json")
    check(validate_manifest(manifest) == [], "template manifest must validate")

    broken = json.loads(json.dumps(manifest))
    runtime = next(channel for channel in broken["channels"] if channel["authority"] == "runtime_engine")
    runtime["format_support"]["GLB"] = "native"
    check(any("cannot claim native export" in item for item in validate_manifest(broken)), "runtime/native contradiction must fail")

    constructors = [
        exported_transform_channel("o", "Object", "location", 1, 2, 24),
        exported_bone_channel("b", "Rig", "Bone", "rotation_euler", 1, 2, 24),
        exported_morph_channel("m", "Mesh", "Shape", 1, 2, 24),
        runtime_material_channel("p", "Material", "emission_strength", "demo.glow", 0.0, 1.0),
        runtime_texture_channel("t", "Material", "atlas_frame", "demo.frame", 0.0, 1.0),
        runtime_visibility_channel("v", "Object", "demo.visible", 0.0, 1.0),
        runtime_effect_channel("e", "Effect", "demo.effect", 0.0, 1.0),
    ]
    constructor_manifest = {
        "schema_version": 1,
        "asset_id": "constructor-check",
        "export": {"format": "GLB", "fps": 24},
        "channels": constructors,
    }
    check(validate_manifest(constructor_manifest) == [], "channel constructors must create valid declarations")

    with tempfile.TemporaryDirectory(prefix="animation-channels-") as folder:
        report = _load_example().build(folder)
        source = report["source"]
        reimported = report["reimported"]
        assert_exported_evidence(manifest, source)
        assert_exported_evidence(manifest, reimported)

        check(source["marker-turn"]["fcurves"] >= 1, "source object transform lacks curves")
        check(source["soft-pulse"]["shape_key_present"], "source morph target is absent")
        check(reimported["marker-turn"]["fcurves"] >= 1, "GLB object transform did not re-import")
        check(reimported["soft-pulse"]["shape_key_present"], "GLB morph target did not re-import")
        check(reimported["soft-pulse"]["fcurves"] >= 1, "GLB morph animation did not re-import")

        sidecar = json.loads(Path(report["sidecar"]).read_text(encoding="utf-8"))
        runtime_channels = [channel for channel in sidecar["channels"] if channel["authority"] == "runtime_engine"]
        check({channel["kind"] for channel in runtime_channels} >= {"material_parameter", "texture_state"}, "runtime sidecar channels are incomplete")
        check(all(channel["runtime_parameter"] for channel in runtime_channels), "runtime channel lacks parameter name")
        check(Path(report["glb"]).is_file(), "GLB was not written")
        check((Path(folder) / "animation-evidence.json").is_file(), "evidence report was not written")

    print("Blender animation checks PASSED")


if __name__ == "__main__":
    main()
