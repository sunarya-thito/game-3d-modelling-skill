"""Compact Blender helpers for deterministic game-asset examples.

The module demonstrates a useful boundary between authored geometry data and
Blender while leaving project paths, registries, art rules, and export policy
to the consuming game project.

Run it inside Blender's Python runtime; it imports ``bpy``, ``bmesh``, and
``mathutils`` supplied by Blender.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, tau, sin
from pathlib import Path
from typing import Iterable, Sequence

import bmesh
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


Vec2 = Sequence[float]
Vec3 = Sequence[float]


@dataclass(frozen=True)
class CoordinateBasis:
    """Describe where project-space X, Y, and Z point in Blender space."""

    project_x: Vec3 = (1.0, 0.0, 0.0)
    project_y: Vec3 = (0.0, 1.0, 0.0)
    project_z: Vec3 = (0.0, 0.0, 1.0)

    def convert(self, value: Vec3) -> Vector:
        x, y, z = value
        return (
            Vector(self.project_x) * x
            + Vector(self.project_y) * y
            + Vector(self.project_z) * z
        )


BLENDER_FRAME = CoordinateBasis()
Y_UP_FRAME = CoordinateBasis(
    project_x=(1.0, 0.0, 0.0),
    project_y=(0.0, 0.0, 1.0),
    project_z=(0.0, -1.0, 0.0),
)


@dataclass
class MeshDraft:
    """Blender-independent polygon data for one named object."""

    name: str
    points: list[Vector] = field(default_factory=list)
    polygons: list[list[int]] = field(default_factory=list)
    polygon_materials: list[int] = field(default_factory=list)

    def add_point(self, value: Vec3) -> int:
        self.points.append(Vector(value))
        return len(self.points) - 1

    def add_polygon(self, indices: Iterable[int], material_index: int = 0) -> None:
        values = list(indices)
        compact = [value for index, value in enumerate(values) if value != values[index - 1]]
        if len(compact) < 3 or len(set(compact)) < 3:
            raise ValueError(f"{self.name}: polygon needs three distinct points")
        self.polygons.append(compact)
        self.polygon_materials.append(material_index)


def _add_ring(draft: MeshDraft, values: Iterable[Vec3]) -> list[int]:
    return [draft.add_point(value) for value in values]


def _join_rings(
    draft: MeshDraft,
    first: Sequence[int],
    second: Sequence[int],
    material_index: int,
) -> None:
    if len(first) != len(second) or len(first) < 3:
        raise ValueError("rings must have equal lengths of at least three")
    for index in range(len(first)):
        following = (index + 1) % len(first)
        draft.add_polygon(
            (first[index], first[following], second[following], second[index]),
            material_index,
        )


def add_profile_loft(
    draft: MeshDraft,
    cross_sections: Sequence[Sequence[Vec3]],
    material_index: int = 0,
    close_ends: bool = True,
) -> list[list[int]]:
    """Add a closed form through equal-sized, explicitly authored sections."""

    if len(cross_sections) < 2:
        raise ValueError("a profile loft needs at least two cross-sections")
    count = len(cross_sections[0])
    if count < 3 or any(len(section) != count for section in cross_sections):
        raise ValueError("all loft cross-sections must have the same point count")
    rings = [_add_ring(draft, section) for section in cross_sections]
    for first, second in zip(rings, rings[1:]):
        _join_rings(draft, first, second, material_index)
    if close_ends:
        draft.add_polygon(reversed(rings[0]), material_index)
        draft.add_polygon(rings[-1], material_index)
    return rings


def add_path_extrusion(
    draft: MeshDraft,
    path: Sequence[Vec3],
    section: Sequence[Vec2],
    guide_up: Vec3 = (0.0, 1.0, 0.0),
    station_scales: Sequence[tuple[float, float]] | None = None,
    material_index: int = 0,
) -> list[list[int]]:
    """Carry a 2D section along authored stations and close both ends."""

    stations = [Vector(value) for value in path]
    if len(stations) < 2 or len(section) < 3:
        raise ValueError("path extrusion needs two stations and a three-point section")
    if station_scales is not None and len(station_scales) != len(stations):
        raise ValueError("station_scales must match the path length")

    reference_up = Vector(guide_up)
    rings = []
    for index, station in enumerate(stations):
        direction = stations[min(index + 1, len(stations) - 1)] - stations[max(index - 1, 0)]
        if direction.length < 1e-8:
            raise ValueError("path contains coincident neighboring stations")
        direction.normalize()
        local_up = reference_up - direction * reference_up.dot(direction)
        if local_up.length < 1e-8:
            alternate = min(
                (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0))),
                key=lambda candidate: abs(candidate.dot(direction)),
            )
            local_up = alternate - direction * alternate.dot(direction)
        local_up.normalize()
        local_side = direction.cross(local_up).normalized()
        scale_side, scale_up = station_scales[index] if station_scales else (1.0, 1.0)
        ring = (
            station + local_side * (side * scale_side) + local_up * (up * scale_up)
            for side, up in section
        )
        rings.append(_add_ring(draft, ring))

    for first, second in zip(rings, rings[1:]):
        _join_rings(draft, first, second, material_index)
    draft.add_polygon(reversed(rings[0]), material_index)
    draft.add_polygon(rings[-1], material_index)
    return rings


def add_revolved_profile(
    draft: MeshDraft,
    radius_and_height: Sequence[Vec2],
    segment_count: int,
    centre: Vec3 = (0.0, 0.0, 0.0),
    axis: Vec3 = (0.0, 1.0, 0.0),
    radial_direction: Vec3 = (1.0, 0.0, 0.0),
    material_index: int = 0,
) -> list[list[int]]:
    """Add a surface of revolution, collapsing zero-radius stations to poles."""

    if segment_count < 3 or len(radius_and_height) < 2:
        raise ValueError("a revolved profile needs three segments and two profile points")
    origin = Vector(centre)
    direction = Vector(axis).normalized()
    radial = Vector(radial_direction)
    radial = (radial - direction * radial.dot(direction)).normalized()
    tangent = direction.cross(radial).normalized()
    if any(radius < 0.0 for radius, _height in radius_and_height):
        raise ValueError("revolved profile radii cannot be negative")
    rings = []
    for radius, height in radius_and_height:
        if abs(radius) <= 1e-8:
            rings.append([draft.add_point(origin + direction * height)])
            continue
        values = []
        for index in range(segment_count):
            angle = tau * index / segment_count
            values.append(
                origin
                + direction * height
                + (radial * cos(angle) + tangent * sin(angle)) * radius
            )
        rings.append(_add_ring(draft, values))
    for first, second in zip(rings, rings[1:]):
        if len(first) == 1 and len(second) == 1:
            raise ValueError("adjacent zero-radius profile points cannot form a surface")
        if len(first) == 1:
            for index in range(len(second)):
                following = (index + 1) % len(second)
                draft.add_polygon((first[0], second[following], second[index]), material_index)
        elif len(second) == 1:
            for index in range(len(first)):
                following = (index + 1) % len(first)
                draft.add_polygon((first[index], first[following], second[0]), material_index)
        else:
            _join_rings(draft, first, second, material_index)
    if len(rings[0]) > 1:
        draft.add_polygon(reversed(rings[0]), material_index)
    if len(rings[-1]) > 1:
        draft.add_polygon(rings[-1], material_index)
    return rings


def add_extruded_outline(
    draft: MeshDraft,
    outline: Sequence[Vec2],
    origin: Vec3,
    horizontal: Vec3,
    vertical: Vec3,
    thickness: float,
    material_index: int = 0,
) -> tuple[list[int], list[int]]:
    """Turn a concave or convex 2D outline into a closed plate."""

    if len(outline) < 3 or thickness <= 0.0:
        raise ValueError("an extruded outline needs three points and positive thickness")
    base = Vector(origin)
    u_axis = Vector(horizontal).normalized()
    v_axis = Vector(vertical).normalized()
    normal = u_axis.cross(v_axis).normalized()
    flat = [Vector((x, y, 0.0)) for x, y in outline]
    triangles = tessellate_polygon([flat])
    lookup = {tuple(value): index for index, value in enumerate(flat)}
    front = _add_ring(
        draft,
        (base + u_axis * x + v_axis * y + normal * thickness * 0.5 for x, y in outline),
    )
    back = _add_ring(
        draft,
        (base + u_axis * x + v_axis * y - normal * thickness * 0.5 for x, y in outline),
    )
    for triangle in triangles:
        a, b, c = (
            int(value) if isinstance(value, int) else lookup[tuple(value)]
            for value in triangle
        )
        draft.add_polygon((front[a], front[b], front[c]), material_index)
        draft.add_polygon((back[c], back[b], back[a]), material_index)
    _join_rings(draft, back, front, material_index)
    return front, back


def start_empty_scene() -> None:
    """Reset to an empty factory scene."""

    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_preview_material(
    name: str,
    rgba: Sequence[float],
    roughness: float = 0.7,
) -> bpy.types.Material:
    """Create a plain Principled material for previews and examples."""

    if len(rgba) != 4:
        raise ValueError("rgba must contain exactly four values")
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    result.diffuse_color = tuple(rgba)
    shader = result.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = tuple(rgba)
    shader.inputs["Roughness"].default_value = roughness
    return result


def create_mesh_object(
    draft: MeshDraft,
    materials: Sequence[bpy.types.Material] = (),
    basis: CoordinateBasis = BLENDER_FRAME,
) -> bpy.types.Object:
    """Validate a draft, create a Blender mesh, orient normals, and triangulate."""

    if not draft.points or not draft.polygons:
        raise ValueError(f"{draft.name}: draft contains no renderable geometry")
    if len(draft.polygons) != len(draft.polygon_materials):
        raise ValueError(f"{draft.name}: polygon material data is incomplete")
    slot_count = max(1, len(materials))
    if any(index < 0 or index >= slot_count for index in draft.polygon_materials):
        raise ValueError(f"{draft.name}: polygon references an unknown material slot")
    largest = len(draft.points) - 1
    if any(index < 0 or index > largest for polygon in draft.polygons for index in polygon):
        raise ValueError(f"{draft.name}: polygon references an unknown point")

    mesh = bpy.data.meshes.new(draft.name)
    mesh.from_pydata([basis.convert(point) for point in draft.points], [], draft.polygons)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(draft.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    for entry in materials:
        mesh.materials.append(entry)
    for polygon, material_index in zip(mesh.polygons, draft.polygon_materials):
        polygon.material_index = material_index

    editable = bmesh.new()
    editable.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(editable, faces=editable.faces)
    bmesh.ops.triangulate(
        editable,
        faces=editable.faces,
        quad_method="BEAUTY",
        ngon_method="EAR_CLIP",
    )
    editable.to_mesh(mesh)
    editable.free()
    mesh.update(calc_edges=True)
    return obj


def inspect_topology(obj: bpy.types.Object, area_epsilon: float = 1e-10) -> dict[str, int]:
    """Measure topology without modifying the source object."""

    if obj.type != "MESH":
        raise TypeError("inspect_topology expects a mesh object")
    editable = bmesh.new()
    editable.from_mesh(obj.data)
    editable.normal_update()
    result = {
        "vertices": len(editable.verts),
        "edges": len(editable.edges),
        "faces": len(editable.faces),
        "triangles": sum(max(0, len(face.verts) - 2) for face in editable.faces),
        "boundary_edges": sum(1 for edge in editable.edges if len(edge.link_faces) == 1),
        "nonmanifold_edges": sum(1 for edge in editable.edges if not edge.is_manifold),
        "degenerate_faces": sum(1 for face in editable.faces if face.calc_area() <= area_epsilon),
    }
    editable.free()
    return result


def write_glb(roots: Sequence[bpy.types.Object], destination: str | Path) -> Path:
    """Export supplied roots and descendants, including supported animation data."""

    if not roots:
        raise ValueError("write_glb requires at least one root object")
    output = Path(destination).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    pending = list(roots)
    selected = set()
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
        export_apply=True,
    )
    return output
