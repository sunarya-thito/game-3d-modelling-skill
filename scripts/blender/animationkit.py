"""Provider-neutral animation-channel helpers for Blender and GLB pipelines.

Run this module inside Blender.  It deliberately separates channels that the
standard Blender glTF exporter can carry from channels that need an engine-side
runtime adapter and a JSON sidecar.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import bpy


CHANNEL_KINDS = {
    "object_transform",
    "bone_transform",
    "morph_target",
    "material_parameter",
    "texture_state",
    "visibility",
    "effect",
}
AUTHORITIES = {"blender_clip", "runtime_engine"}
OWNER_TYPES = {"object", "bone", "shape_key", "material", "effect"}
TIME_UNITS = {"frames", "seconds"}
LOOP_POLICIES = {"once", "cycle", "ping_pong"}
ROOT_POLICIES = {"none", "object", "bone", "runtime"}
SUPPORT_LEVELS = {"native", "sidecar", "unsupported"}
EXPORTABLE_KINDS = {"object_transform", "bone_transform", "morph_target"}
RUNTIME_KINDS = {"material_parameter", "texture_state", "visibility", "effect"}

KIND_OWNER_TYPES = {
    "object_transform": {"object"},
    "bone_transform": {"bone"},
    "morph_target": {"shape_key"},
    "material_parameter": {"material"},
    "texture_state": {"material"},
    "visibility": {"object"},
    "effect": {"effect"},
}


class ManifestError(ValueError):
    """Raised when an animation manifest is incomplete or contradictory."""


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Return all manifest errors without mutating the supplied mapping."""

    errors: list[str] = []
    _require(manifest.get("schema_version") == 1, "schema_version must be 1", errors)
    _require(bool(manifest.get("asset_id")), "asset_id is required", errors)

    export = manifest.get("export")
    _require(isinstance(export, Mapping), "export must be an object", errors)
    export_format = None
    if isinstance(export, Mapping):
        export_format = export.get("format")
        _require(export_format in {"GLB", "GLTF"}, "export.format must be GLB or GLTF", errors)
        _require(_number(export.get("fps")) and export.get("fps", 0) > 0, "export.fps must be positive", errors)

    channels = manifest.get("channels")
    _require(isinstance(channels, list) and bool(channels), "channels must be a non-empty array", errors)
    if not isinstance(channels, list):
        return errors

    seen: set[str] = set()
    for index, channel in enumerate(channels):
        label = f"channels[{index}]"
        if not isinstance(channel, Mapping):
            errors.append(f"{label} must be an object")
            continue
        channel_id = channel.get("id")
        _require(isinstance(channel_id, str) and bool(channel_id), f"{label}.id is required", errors)
        if isinstance(channel_id, str):
            _require(channel_id not in seen, f"{label}.id is duplicated: {channel_id}", errors)
            seen.add(channel_id)

        kind = channel.get("kind")
        authority = channel.get("authority")
        _require(kind in CHANNEL_KINDS, f"{label}.kind is invalid", errors)
        _require(authority in AUTHORITIES, f"{label}.authority is invalid", errors)

        owner = channel.get("owner")
        _require(isinstance(owner, Mapping), f"{label}.owner must be an object", errors)
        if isinstance(owner, Mapping):
            owner_type = owner.get("type")
            _require(owner_type in OWNER_TYPES, f"{label}.owner.type is invalid", errors)
            _require(bool(owner.get("name")), f"{label}.owner.name is required", errors)
            if kind in KIND_OWNER_TYPES:
                _require(owner_type in KIND_OWNER_TYPES[kind], f"{label}.owner.type does not match {kind}", errors)
            if owner_type == "bone":
                _require(bool(owner.get("armature")), f"{label}.owner.armature is required", errors)
            if owner_type == "shape_key":
                _require(bool(owner.get("shape_key")), f"{label}.owner.shape_key is required", errors)

        _require(bool(channel.get("property")), f"{label}.property is required", errors)

        timing = channel.get("time")
        _require(isinstance(timing, Mapping), f"{label}.time must be an object", errors)
        if isinstance(timing, Mapping):
            unit = timing.get("unit")
            start = timing.get("start")
            end = timing.get("end")
            _require(unit in TIME_UNITS, f"{label}.time.unit is invalid", errors)
            _require(_number(start) and _number(end) and start < end, f"{label}.time needs start < end", errors)
            if unit == "frames":
                fps = timing.get("fps", export.get("fps") if isinstance(export, Mapping) else None)
                _require(_number(fps) and fps > 0, f"{label}.time.fps must be positive", errors)

        _require(channel.get("loop") in LOOP_POLICIES, f"{label}.loop is invalid", errors)
        _require(channel.get("root_motion") in ROOT_POLICIES, f"{label}.root_motion is invalid", errors)

        support = channel.get("format_support")
        _require(isinstance(support, Mapping), f"{label}.format_support must be an object", errors)
        selected_support = None
        if isinstance(support, Mapping) and export_format:
            selected_support = support.get(export_format)
            _require(selected_support in SUPPORT_LEVELS, f"{label}.format_support lacks {export_format}", errors)

        runtime_parameter = channel.get("runtime_parameter")
        fallback = channel.get("fallback")
        _require(isinstance(fallback, Mapping) and bool(fallback.get("mode")), f"{label}.fallback.mode is required", errors)

        if kind in EXPORTABLE_KINDS:
            _require(authority == "blender_clip", f"{label}: {kind} must use blender_clip authority", errors)
            _require(selected_support == "native", f"{label}: {kind} must declare native export support", errors)
            _require(runtime_parameter in (None, ""), f"{label}: exported channels must not claim a runtime parameter", errors)
        elif kind in RUNTIME_KINDS:
            _require(authority == "runtime_engine", f"{label}: {kind} must use runtime_engine authority", errors)
            _require(selected_support in {"sidecar", "unsupported"}, f"{label}: runtime channels cannot claim native export", errors)
            _require(isinstance(runtime_parameter, str) and bool(runtime_parameter), f"{label}: runtime_parameter is required", errors)

        if authority == "blender_clip":
            _require(isinstance(timing, Mapping) and timing.get("unit") == "frames", f"{label}: Blender clips use frame ranges", errors)
        elif authority == "runtime_engine":
            _require(channel.get("root_motion") in {"none", "runtime"}, f"{label}: runtime channels use none or runtime root policy", errors)

    return errors


def require_valid_manifest(manifest: Mapping[str, Any]) -> None:
    errors = validate_manifest(manifest)
    if errors:
        raise ManifestError("invalid animation manifest:\n- " + "\n- ".join(errors))


def load_manifest(path: str | Path) -> dict[str, Any]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    require_valid_manifest(manifest)
    return manifest


def write_manifest(manifest: Mapping[str, Any], path: str | Path) -> Path:
    require_valid_manifest(manifest)
    destination = Path(path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def exported_transform_channel(
    channel_id: str,
    owner_name: str,
    property_name: str,
    start: float,
    end: float,
    fps: float,
    *,
    loop: str = "once",
    root_motion: str = "none",
) -> dict[str, Any]:
    """Declare a standard object-transform animation channel."""

    return _channel(
        channel_id, "object_transform", "blender_clip",
        {"type": "object", "name": owner_name}, property_name,
        {"unit": "frames", "start": start, "end": end, "fps": fps},
        loop, root_motion, "native", None, {"mode": "rest_transform"},
    )


def exported_bone_channel(
    channel_id: str,
    armature_name: str,
    bone_name: str,
    property_name: str,
    start: float,
    end: float,
    fps: float,
    *,
    loop: str = "once",
    root_motion: str = "none",
) -> dict[str, Any]:
    """Declare a standard skeletal-transform animation channel."""

    return _channel(
        channel_id, "bone_transform", "blender_clip",
        {"type": "bone", "name": bone_name, "armature": armature_name}, property_name,
        {"unit": "frames", "start": start, "end": end, "fps": fps},
        loop, root_motion, "native", None, {"mode": "rest_pose"},
    )


def exported_morph_channel(
    channel_id: str,
    object_name: str,
    shape_key: str,
    start: float,
    end: float,
    fps: float,
    *,
    loop: str = "once",
) -> dict[str, Any]:
    """Declare a standard glTF morph-weight animation channel."""

    return _channel(
        channel_id, "morph_target", "blender_clip",
        {"type": "shape_key", "name": object_name, "shape_key": shape_key}, "value",
        {"unit": "frames", "start": start, "end": end, "fps": fps},
        loop, "none", "native", None, {"mode": "basis_shape"},
    )


def runtime_material_channel(
    channel_id: str,
    material_name: str,
    property_name: str,
    runtime_parameter: str,
    start: float,
    end: float,
    *,
    loop: str = "once",
    fallback: Any = 0.0,
) -> dict[str, Any]:
    """Declare an engine-owned material parameter, including emission."""

    return _runtime_channel(
        channel_id, "material_parameter", {"type": "material", "name": material_name},
        property_name, runtime_parameter, start, end, loop, fallback,
    )


def runtime_texture_channel(
    channel_id: str,
    material_name: str,
    property_name: str,
    runtime_parameter: str,
    start: float,
    end: float,
    *,
    loop: str = "once",
    fallback: Any = 0,
) -> dict[str, Any]:
    """Declare an engine-owned UV, atlas-frame, or image-sequence state."""

    return _runtime_channel(
        channel_id, "texture_state", {"type": "material", "name": material_name},
        property_name, runtime_parameter, start, end, loop, fallback,
    )


def runtime_visibility_channel(
    channel_id: str,
    object_name: str,
    runtime_parameter: str,
    start: float,
    end: float,
    *,
    loop: str = "once",
    fallback: bool = True,
) -> dict[str, Any]:
    """Declare engine-owned visibility without encoding it as scale animation."""

    return _runtime_channel(
        channel_id, "visibility", {"type": "object", "name": object_name},
        "visible", runtime_parameter, start, end, loop, fallback,
    )


def runtime_effect_channel(
    channel_id: str,
    effect_name: str,
    runtime_parameter: str,
    start: float,
    end: float,
    *,
    loop: str = "once",
    fallback: Any = False,
) -> dict[str, Any]:
    """Declare an engine-owned particle or effect state."""

    return _runtime_channel(
        channel_id, "effect", {"type": "effect", "name": effect_name},
        "enabled", runtime_parameter, start, end, loop, fallback,
    )


def tag_runtime_binding(id_block: Any, runtime_parameter: str, fallback: Any) -> None:
    """Add non-authoritative discovery metadata to a static Blender owner.

    The JSON manifest remains authoritative.  Custom properties are convenient
    for inspection, but consumers must not assume a glTF importer preserves
    them unless exporter extras are explicitly enabled and tested.
    """

    if not runtime_parameter:
        raise ValueError("runtime_parameter is required")
    id_block["runtime_parameter"] = runtime_parameter
    id_block["runtime_fallback"] = fallback


def _runtime_channel(
    channel_id: str,
    kind: str,
    owner: Mapping[str, Any],
    property_name: str,
    runtime_parameter: str,
    start: float,
    end: float,
    loop: str,
    fallback: Any,
) -> dict[str, Any]:
    return _channel(
        channel_id, kind, "runtime_engine", owner, property_name,
        {"unit": "seconds", "start": start, "end": end},
        loop, "none", "sidecar", runtime_parameter,
        {"mode": "constant", "value": fallback},
    )


def _channel(
    channel_id: str,
    kind: str,
    authority: str,
    owner: Mapping[str, Any],
    property_name: str,
    timing: Mapping[str, Any],
    loop: str,
    root_motion: str,
    support: str,
    runtime_parameter: str | None,
    fallback: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "id": channel_id,
        "kind": kind,
        "authority": authority,
        "owner": dict(owner),
        "property": property_name,
        "time": dict(timing),
        "loop": loop,
        "root_motion": root_motion,
        "format_support": {"GLB": support},
        "runtime_parameter": runtime_parameter,
        "fallback": dict(fallback),
    }


def configure_scene_timing(start: int, end: int, fps: float) -> None:
    if start >= end or fps <= 0:
        raise ValueError("scene timing needs start < end and positive fps")
    scene = bpy.context.scene
    scene.frame_start = int(start)
    scene.frame_end = int(end)
    scene.render.fps = int(round(fps))
    scene.render.fps_base = scene.render.fps / float(fps)


def _keyframe(id_block: Any, data_path: str, frame: float, index: int = -1) -> None:
    id_block.keyframe_insert(data_path=data_path, frame=frame, index=index)


def keyframe_object_transform(
    obj: bpy.types.Object,
    frame: float,
    *,
    location: Sequence[float] | None = None,
    rotation_euler: Sequence[float] | None = None,
    scale: Sequence[float] | None = None,
) -> None:
    """Key selected object transform components at one frame."""

    if location is not None:
        obj.location = location
        _keyframe(obj, "location", frame)
    if rotation_euler is not None:
        obj.rotation_mode = "XYZ"
        obj.rotation_euler = rotation_euler
        _keyframe(obj, "rotation_euler", frame)
    if scale is not None:
        obj.scale = scale
        _keyframe(obj, "scale", frame)


def keyframe_bone_transform(
    armature: bpy.types.Object,
    bone_name: str,
    frame: float,
    *,
    location: Sequence[float] | None = None,
    rotation_euler: Sequence[float] | None = None,
    scale: Sequence[float] | None = None,
) -> None:
    """Key a pose bone relative to its rest transform."""

    if armature.type != "ARMATURE" or bone_name not in armature.pose.bones:
        raise ValueError(f"unknown pose bone {bone_name!r}")
    bone = armature.pose.bones[bone_name]
    if location is not None:
        bone.location = location
        _keyframe(bone, "location", frame)
    if rotation_euler is not None:
        bone.rotation_mode = "XYZ"
        bone.rotation_euler = rotation_euler
        _keyframe(bone, "rotation_euler", frame)
    if scale is not None:
        bone.scale = scale
        _keyframe(bone, "scale", frame)


def keyframe_morph(obj: bpy.types.Object, shape_key: str, frame: float, value: float) -> None:
    """Key one relative shape-key value for glTF morph-weight export."""

    keys = obj.data.shape_keys
    if keys is None or shape_key not in keys.key_blocks:
        raise ValueError(f"{obj.name!r} has no shape key {shape_key!r}")
    block = keys.key_blocks[shape_key]
    block.value = float(value)
    _keyframe(block, "value", frame)


def set_interpolation(id_block: Any, interpolation: str = "LINEAR") -> None:
    """Set interpolation on every key in the active action of an ID block."""

    animation = getattr(id_block, "animation_data", None)
    action = animation.action if animation else None
    if action is None:
        raise ValueError("ID block has no active action")
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = interpolation


def _actions(id_block: Any) -> Iterable[bpy.types.Action]:
    animation = getattr(id_block, "animation_data", None)
    if animation is None:
        return ()
    actions: list[bpy.types.Action] = []
    if animation.action is not None:
        actions.append(animation.action)
    for track in animation.nla_tracks:
        actions.extend(strip.action for strip in track.strips if strip.action is not None)
    return actions


def _curve_summary(id_block: Any, data_path_contains: str | Sequence[str]) -> dict[str, Any]:
    required = (data_path_contains,) if isinstance(data_path_contains, str) else tuple(data_path_contains)
    curves = [
        curve
        for action in _actions(id_block)
        for curve in action.fcurves
        if all(token in curve.data_path for token in required)
    ]
    frames = sorted({round(float(point.co.x), 6) for curve in curves for point in curve.keyframe_points})
    return {"fcurves": len(curves), "frames": frames}


def source_channel_evidence(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Inspect current Blender data for manifest-owned exported channels."""

    require_valid_manifest(manifest)
    evidence: dict[str, Any] = {}
    for channel in manifest["channels"]:
        channel_id = channel["id"]
        if channel["authority"] == "runtime_engine":
            evidence[channel_id] = {
                "authority": "runtime_engine",
                "runtime_parameter": channel["runtime_parameter"],
                "sidecar_only": channel["format_support"][manifest["export"]["format"]] != "native",
            }
            continue
        owner = channel["owner"]
        if channel["kind"] == "object_transform":
            obj = bpy.data.objects.get(owner["name"])
            summary = _curve_summary(obj, channel["property"]) if obj else {"fcurves": 0, "frames": []}
        elif channel["kind"] == "bone_transform":
            armature = bpy.data.objects.get(owner["armature"])
            token = f'pose.bones["{owner["name"]}"]'
            summary = _curve_summary(armature, (token, channel["property"])) if armature else {"fcurves": 0, "frames": []}
        elif channel["kind"] == "morph_target":
            obj = bpy.data.objects.get(owner["name"])
            keys = obj.data.shape_keys if obj and hasattr(obj.data, "shape_keys") else None
            token = f'key_blocks["{owner["shape_key"]}"]'
            summary = _curve_summary(keys, token) if keys else {"fcurves": 0, "frames": []}
            summary["shape_key_present"] = bool(keys and owner["shape_key"] in keys.key_blocks)
        else:
            summary = {"fcurves": 0, "frames": []}
        summary["authority"] = "blender_clip"
        evidence[channel_id] = summary
    return evidence


def export_glb(roots: Sequence[bpy.types.Object], destination: str | Path) -> Path:
    """Export selected roots and descendants with standard glTF animations."""

    if not roots:
        raise ValueError("export_glb requires at least one root")
    output = Path(destination).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    pending = list(roots)
    selected: set[str] = set()
    while pending:
        obj = pending.pop()
        if obj.name in selected:
            continue
        selected.add(obj.name)
        obj.select_set(True)
        pending.extend(obj.children)
    bpy.context.view_layer.objects.active = roots[0]
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_morph=True,
        export_morph_animation=True,
        export_apply=False,
    )
    return output


def reimport_channel_evidence(glb_path: str | Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Import a GLB into an empty scene and inspect portable channel evidence."""

    require_valid_manifest(manifest)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(glb_path).resolve()))
    evidence = source_channel_evidence(manifest)
    # glTF stores rotations as quaternions.  Blender may therefore re-import an
    # authored Euler curve as rotation_quaternion; that is a representation
    # change, not lost semantic animation.
    for channel in manifest["channels"]:
        if channel["kind"] not in {"object_transform", "bone_transform"}:
            continue
        current = evidence[channel["id"]]
        if current.get("fcurves") or not channel["property"].startswith("rotation"):
            continue
        owner = channel["owner"]
        obj = bpy.data.objects.get(owner["name"] if channel["kind"] == "object_transform" else owner["armature"])
        if obj is not None:
            tokens: str | Sequence[str] = "rotation_"
            if channel["kind"] == "bone_transform":
                tokens = (f'pose.bones["{owner["name"]}"]', "rotation_")
            replacement = _curve_summary(obj, tokens)
            replacement["authority"] = "blender_clip"
            evidence[channel["id"]] = replacement
    return evidence


def assert_exported_evidence(manifest: Mapping[str, Any], evidence: Mapping[str, Any]) -> None:
    """Fail when an exported channel lacks keys or its declared range endpoints."""

    failures: list[str] = []
    for channel in manifest["channels"]:
        if channel["authority"] != "blender_clip":
            continue
        found = evidence.get(channel["id"], {})
        frames = found.get("frames", [])
        if not found.get("fcurves"):
            failures.append(f"{channel['id']}: no animation curves")
            continue
        for endpoint in (channel["time"]["start"], channel["time"]["end"]):
            if not any(abs(float(frame) - float(endpoint)) < 1e-4 for frame in frames):
                failures.append(f"{channel['id']}: missing range endpoint {endpoint}")
        if channel["kind"] == "morph_target" and not found.get("shape_key_present"):
            failures.append(f"{channel['id']}: shape key is missing")
    if failures:
        raise AssertionError("animation evidence failed:\n- " + "\n- ".join(failures))
