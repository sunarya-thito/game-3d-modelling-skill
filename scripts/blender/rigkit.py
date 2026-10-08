"""Small clean-room rigging helpers for Blender example builders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import bpy
from mathutils import Matrix, Vector


@dataclass(frozen=True)
class JointSpec:
    name: str
    head: tuple[float, float, float]
    tail: tuple[float, float, float] | None = None
    parent: str | None = None


def parent_first(specs: Sequence[JointSpec]) -> list[JointSpec]:
    """Return parents before children and reject duplicate, missing, or cyclic data."""

    by_name = {spec.name: spec for spec in specs}
    if len(by_name) != len(specs):
        raise ValueError("joint names must be unique")
    result: list[JointSpec] = []
    pending = set(by_name)
    while pending:
        ready = sorted(
            (name for name in pending if by_name[name].parent is None or by_name[name].parent not in pending)
        )
        if not ready:
            raise ValueError("joint hierarchy contains a cycle")
        for name in ready:
            parent = by_name[name].parent
            if parent is not None and parent not in by_name:
                raise ValueError(f"{name}: missing parent {parent}")
            result.append(by_name[name])
            pending.remove(name)
    return result


def keep_world_parent(child: bpy.types.Object, parent: bpy.types.Object) -> None:
    world = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = world


def create_rigid_hierarchy(specs: Sequence[JointSpec]) -> dict[str, bpy.types.Object]:
    """Create named joint empties at authored Blender-space pivots."""

    made: dict[str, bpy.types.Object] = {}
    for spec in parent_first(specs):
        joint = bpy.data.objects.new(spec.name, None)
        joint.empty_display_type = "ARROWS"
        joint.empty_display_size = 0.15
        joint.matrix_world = Matrix.Translation(Vector(spec.head))
        bpy.context.scene.collection.objects.link(joint)
        if spec.parent:
            keep_world_parent(joint, made[spec.parent])
        made[spec.name] = joint
    return made


def create_armature(name: str, specs: Sequence[JointSpec]) -> bpy.types.Object:
    """Create an armature with explicitly authored heads, tails, and parents."""

    ordered = parent_first(specs)
    data = bpy.data.armatures.new(name)
    armature = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(armature)
    bpy.context.view_layer.objects.active = armature
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for spec in ordered:
        bone = data.edit_bones.new(spec.name)
        bone.head = Vector(spec.head)
        tail = Vector(spec.tail) if spec.tail else bone.head + Vector((0.0, 0.0, 0.25))
        if (tail - bone.head).length <= 1e-6:
            raise ValueError(f"{spec.name}: bone tail must differ from its head")
        bone.tail = tail
        if spec.parent:
            bone.parent = data.edit_bones[spec.parent]
            bone.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return armature


def bind_weights(
    mesh_object: bpy.types.Object,
    armature: bpy.types.Object,
    weights: Sequence[Mapping[str, float]],
    epsilon: float = 1e-6,
) -> None:
    """Bind normalized per-vertex weights and fail on incomplete declarations."""

    if mesh_object.type != "MESH" or armature.type != "ARMATURE":
        raise TypeError("bind_weights expects a mesh and an armature")
    if len(weights) != len(mesh_object.data.vertices):
        raise ValueError("one weight mapping is required per mesh vertex")
    bone_names = {bone.name for bone in armature.data.bones}
    groups = {name: mesh_object.vertex_groups.new(name=name) for name in sorted(bone_names)}
    for vertex_index, mapping in enumerate(weights):
        unknown = set(mapping) - bone_names
        if unknown:
            raise ValueError(f"vertex {vertex_index}: unknown bones {sorted(unknown)}")
        total = sum(value for value in mapping.values() if value > epsilon)
        if total <= epsilon:
            raise ValueError(f"vertex {vertex_index}: no positive bone influence")
        for name, value in mapping.items():
            if value > epsilon:
                groups[name].add([vertex_index], value / total, "REPLACE")
    modifier = mesh_object.modifiers.new("Armature", "ARMATURE")
    modifier.object = armature
    keep_world_parent(mesh_object, armature)


def weight_report(mesh_object: bpy.types.Object) -> dict[str, int]:
    """Report unweighted vertices and vertices whose stored weights do not sum to one."""

    unweighted = 0
    unnormalized = 0
    for vertex in mesh_object.data.vertices:
        total = sum(entry.weight for entry in vertex.groups)
        if not vertex.groups:
            unweighted += 1
        elif abs(total - 1.0) > 1e-4:
            unnormalized += 1
    return {"unweighted_vertices": unweighted, "unnormalized_vertices": unnormalized}
