"""Measured, non-mutating geometry gates for Blender game assets.

The public entry point is :func:`audit_scene`.  It evaluates named mesh objects
through Blender's dependency graph, compares the measurements with a JSON-like
contract, and returns a serialisable report.  The module never moves, repairs,
recalculates, or otherwise changes authored geometry.

This module must run in Blender's Python runtime because it imports ``bpy``,
``bmesh``, and ``mathutils``.
"""

from __future__ import annotations

from contextlib import contextmanager
from math import atan2, isfinite, pi
from typing import Any, Iterator, Mapping, Sequence

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}


class AuditContractError(ValueError):
    """Raised when a binding audit contract is missing or ambiguous."""


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _require_number(value: Any, path: str, *, minimum: float | None = None) -> float:
    if not _finite_number(value):
        raise AuditContractError(f"{path} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise AuditContractError(f"{path} must be at least {minimum}")
    return result


def _require_vector(value: Any, path: str) -> tuple[float, float, float]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
        raise AuditContractError(f"{path} must contain exactly three numbers")
    return tuple(_require_number(component, f"{path}[{index}]") for index, component in enumerate(value))


def _limits(value: Any, path: str) -> tuple[float | None, float | None]:
    if not isinstance(value, Mapping):
        raise AuditContractError(f"{path} must be an object containing min and/or max")
    if "min" not in value and "max" not in value:
        raise AuditContractError(f"{path} must declare min and/or max")
    lower = _require_number(value["min"], f"{path}.min", minimum=0.0) if "min" in value else None
    upper = _require_number(value["max"], f"{path}.max", minimum=0.0) if "max" in value else None
    if lower is not None and upper is not None and lower > upper:
        raise AuditContractError(f"{path}.min cannot exceed {path}.max")
    return lower, upper


def _issue(code: str, path: str, message: str, **evidence: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"code": code, "path": path, "message": message}
    result.update(evidence)
    return result


@contextmanager
def _evaluated_mesh(
    obj: bpy.types.Object,
    depsgraph: bpy.types.Depsgraph,
) -> Iterator[tuple[bpy.types.Object, bpy.types.Mesh]]:
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    if mesh is None:
        raise RuntimeError(f"Blender could not evaluate mesh object {obj.name!r}")
    try:
        yield evaluated, mesh
    finally:
        evaluated.to_mesh_clear()


def _triangle_area(a: Vector, b: Vector, c: Vector) -> float:
    return (b - a).cross(c - a).length * 0.5


def _snapshot_object(
    obj: bpy.types.Object,
    depsgraph: bpy.types.Depsgraph,
    area_epsilon: float,
) -> dict[str, Any]:
    """Copy dependency-graph results into plain data for later checks."""

    with _evaluated_mesh(obj, depsgraph) as (evaluated, mesh):
        matrix = evaluated.matrix_world.copy()
        nonfinite_transform_values = sum(
            1 for row in matrix for component in row if not isfinite(component)
        )
        local_vertices = [vertex.co.copy() for vertex in mesh.vertices]
        world_vertices = [matrix @ value for value in local_vertices]
        local_nonfinite = sum(
            1 for value in local_vertices if not all(isfinite(component) for component in value)
        )
        world_nonfinite = sum(
            1 for value in world_vertices if not all(isfinite(component) for component in value)
        )

        mesh.calc_loop_triangles()
        triangles = [tuple(int(index) for index in triangle.vertices) for triangle in mesh.loop_triangles]
        triangle_degenerates = 0
        if world_nonfinite == 0:
            triangle_degenerates = sum(
                1
                for a, b, c in triangles
                if _triangle_area(world_vertices[a], world_vertices[b], world_vertices[c]) <= area_epsilon
            )

        editable = bmesh.new()
        try:
            editable.from_mesh(mesh)
            for vertex in editable.verts:
                vertex.co = matrix @ vertex.co
            editable.normal_update()
            boundary_edges = sum(1 for edge in editable.edges if len(edge.link_faces) == 1)
            wire_edges = sum(1 for edge in editable.edges if len(edge.link_faces) == 0)
            nonmanifold_edges = sum(1 for edge in editable.edges if len(edge.link_faces) != 2)
            degenerate_faces = sum(
                1 for face in editable.faces if face.calc_area() <= area_epsilon
            )
            closed = bool(editable.faces) and nonmanifold_edges == 0 and world_nonfinite == 0
            signed_volume = float(editable.calc_volume(signed=True)) if closed else None
        finally:
            editable.free()

        used_indices = sorted({int(polygon.material_index) for polygon in mesh.polygons})
        material_names = []
        invalid_material_faces = 0
        for index in used_indices:
            if index >= len(mesh.materials) or mesh.materials[index] is None:
                invalid_material_faces += sum(
                    1 for polygon in mesh.polygons if int(polygon.material_index) == index
                )
            else:
                material_names.append(mesh.materials[index].name_full)

        bounds_min: list[float] | None = None
        bounds_max: list[float] | None = None
        if world_vertices and world_nonfinite == 0:
            bounds_min = [min(vertex[axis] for vertex in world_vertices) for axis in range(3)]
            bounds_max = [max(vertex[axis] for vertex in world_vertices) for axis in range(3)]

        return {
            "name": obj.name,
            "origin_world": [
                float(value) if isfinite(value) else None for value in matrix.translation
            ],
            "bounds_world": {"min": bounds_min, "max": bounds_max},
            "vertices": [[float(component) for component in value] for value in world_vertices],
            "triangles_data": [list(value) for value in triangles],
            "vertex_count": len(world_vertices),
            "edge_count": len(mesh.edges),
            "face_count": len(mesh.polygons),
            "triangle_count": len(triangles),
            "material_slot_count": len(mesh.materials),
            "used_material_count": len(used_indices),
            "used_material_names": material_names,
            "invalid_material_faces": invalid_material_faces,
            "local_nonfinite_vertices": local_nonfinite,
            "world_nonfinite_vertices": world_nonfinite,
            "nonfinite_transform_values": nonfinite_transform_values,
            "boundary_edges": boundary_edges,
            "wire_edges": wire_edges,
            "nonmanifold_edges": nonmanifold_edges,
            "degenerate_faces": degenerate_faces,
            "degenerate_triangles": triangle_degenerates,
            "closed_shell": closed,
            "signed_volume": signed_volume,
            "winding_signal": (
                "open_or_invalid"
                if signed_volume is None
                else "positive"
                if signed_volume > area_epsilon
                else "negative"
                if signed_volume < -area_epsilon
                else "zero"
            ),
        }


def _vectors(snapshot: Mapping[str, Any]) -> list[Vector]:
    return [Vector(value) for value in snapshot["vertices"]]


def _triangles(snapshot: Mapping[str, Any]) -> list[tuple[int, int, int]]:
    return [tuple(value) for value in snapshot["triangles_data"]]


def _bvh(snapshot: Mapping[str, Any], epsilon: float) -> BVHTree | None:
    if snapshot["world_nonfinite_vertices"] or not snapshot["triangles_data"]:
        return None
    return BVHTree.FromPolygons(
        _vectors(snapshot),
        _triangles(snapshot),
        all_triangles=True,
        epsilon=epsilon,
    )


def _self_intersections(snapshot: Mapping[str, Any], epsilon: float) -> list[list[int]] | None:
    """Return conservative triangle pairs, excluding topological neighbours."""

    tree = _bvh(snapshot, epsilon)
    if tree is None:
        return None
    triangles = _triangles(snapshot)
    pairs = set()
    for first, second in tree.overlap(tree):
        if first == second:
            continue
        ordered = tuple(sorted((int(first), int(second))))
        if set(triangles[ordered[0]]) & set(triangles[ordered[1]]):
            continue
        pairs.add(ordered)
    return [list(pair) for pair in sorted(pairs)]


def _samples(snapshot: Mapping[str, Any]) -> list[Vector]:
    vertices = _vectors(snapshot)
    result = list(vertices)
    for a, b, c in _triangles(snapshot):
        result.append((vertices[a] + vertices[b] + vertices[c]) / 3.0)
    return result


def _nearest_samples(
    source: Mapping[str, Any],
    target_tree: BVHTree,
) -> tuple[float | None, list[float] | None, list[float] | None]:
    best_distance: float | None = None
    best_source: Vector | None = None
    best_target: Vector | None = None
    for sample in _samples(source):
        nearest = target_tree.find_nearest(sample)
        if nearest is None or nearest[0] is None:
            continue
        location, _normal, _index, distance = nearest
        if best_distance is None or distance < best_distance:
            best_distance = float(distance)
            best_source = sample.copy()
            best_target = location.copy()
    return (
        best_distance,
        [float(value) for value in best_source] if best_source is not None else None,
        [float(value) for value in best_target] if best_target is not None else None,
    )


def _outside_bounds(
    point: Vector,
    target: Mapping[str, Any],
    epsilon: float,
) -> bool:
    minimum = target["bounds_world"]["min"]
    maximum = target["bounds_world"]["max"]
    if minimum is None or maximum is None:
        return False
    return any(
        point[axis] < minimum[axis] - epsilon
        or point[axis] > maximum[axis] + epsilon
        for axis in range(3)
    )


def _winding_number(
    point: Vector,
    vertices: Sequence[Vector],
    triangles: Sequence[tuple[int, int, int]],
) -> float:
    """Return the signed generalized winding number around ``point``."""

    solid_angle = 0.0
    for first, second, third in triangles:
        a = vertices[first] - point
        b = vertices[second] - point
        c = vertices[third] - point
        a_length = a.length
        b_length = b.length
        c_length = c.length
        numerator = a.dot(b.cross(c))
        denominator = (
            a_length * b_length * c_length
            + a.dot(b) * c_length
            + b.dot(c) * a_length
            + c.dot(a) * b_length
        )
        solid_angle += 2.0 * atan2(numerator, denominator)
    return solid_angle / (4.0 * pi)


def _containment_depths(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    target_tree: BVHTree,
    epsilon: float,
) -> dict[str, Any]:
    """Classify source samples with a closed-shell winding-number test.

    A world-AABB rejection is an exact necessary condition and avoids doing
    expensive winding work for provably external points.  Samples on the
    boundary are not penetration.  Non-integral winding results are ambiguous
    and make the directional estimate fail closed.
    """

    signed_volume = target["signed_volume"]
    if (
        not target["closed_shell"]
        or signed_volume is None
        or abs(signed_volume) <= epsilon
        or target.get("self_intersection_pairs") is None
        or bool(target["self_intersection_pairs"])
    ):
        return {
            "evaluable": False,
            "reason": "target must be a finite, non-self-intersecting closed shell",
            "depths": [],
            "samples": 0,
            "outside_aabb_samples": 0,
            "boundary_samples": 0,
            "inside_samples": 0,
            "ambiguous_samples": 0,
        }

    vertices = _vectors(target)
    triangles = _triangles(target)
    depths: list[float] = []
    outside_aabb = 0
    boundary = 0
    inside = 0
    ambiguous = 0
    sample_count = 0
    for sample in _samples(source):
        sample_count += 1
        if _outside_bounds(sample, target, epsilon):
            outside_aabb += 1
            continue
        nearest = target_tree.find_nearest(sample)
        if nearest is None or nearest[0] is None:
            ambiguous += 1
            continue
        _location, _normal, _index, distance = nearest
        if distance <= epsilon:
            boundary += 1
            continue

        winding = _winding_number(sample, vertices, triangles)
        nearest_integer = round(winding)
        # A closed, consistently oriented, non-self-intersecting shell has an
        # integer generalized winding number away from its boundary.  Refuse a
        # penetration estimate if numeric or winding defects violate that fact.
        if abs(winding - nearest_integer) > 1e-3:
            ambiguous += 1
            continue
        if nearest_integer != 0:
            inside += 1
            depths.append(float(distance))
    return {
        "evaluable": ambiguous == 0,
        "method": "generalized_winding_number",
        "depths": depths,
        "samples": sample_count,
        "outside_aabb_samples": outside_aabb,
        "boundary_samples": boundary,
        "inside_samples": inside,
        "ambiguous_samples": ambiguous,
    }


def _axis_overlap(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
) -> list[float] | None:
    first_min = first["bounds_world"]["min"]
    first_max = first["bounds_world"]["max"]
    second_min = second["bounds_world"]["min"]
    second_max = second["bounds_world"]["max"]
    if first_min is None or second_min is None:
        return None
    return [
        float(min(first_max[axis], second_max[axis]) - max(first_min[axis], second_min[axis]))
        for axis in range(3)
    ]


def measure_contact(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    epsilon: float = 1e-6,
) -> dict[str, Any]:
    """Measure a named pair without altering either object.

    Closest distance samples vertices and triangle centroids in both directions.
    Penetration is a lower-bound estimate from those same samples. Containment
    uses generalized winding numbers for valid closed shells; nearest-surface
    distance is used only after containment is established. The report exposes
    that limit and must not be interpreted as exact CSG depth.
    """

    first_tree = _bvh(first, epsilon)
    second_tree = _bvh(second, epsilon)
    if first_tree is None or second_tree is None:
        return {
            "evaluable": False,
            "reason": "both objects need finite, triangulated evaluated meshes",
            "gap": None,
            "penetration_depth_estimate": None,
        }

    forward = _nearest_samples(first, second_tree)
    backward = _nearest_samples(second, first_tree)
    choices = [entry for entry in (forward, backward) if entry[0] is not None]
    selected = min(choices, key=lambda entry: entry[0])
    distance, point_a, point_b = selected
    if selected is backward:
        point_a, point_b = point_b, point_a

    overlaps = sorted({tuple(sorted(pair)) for pair in first_tree.overlap(second_tree)})
    first_containment = _containment_depths(first, second, second_tree, epsilon)
    second_containment = _containment_depths(second, first, first_tree, epsilon)
    penetration_evaluable = bool(
        first_containment["evaluable"] and second_containment["evaluable"]
    )
    all_depths = first_containment["depths"] + second_containment["depths"]
    penetration = max(all_depths, default=0.0) if penetration_evaluable else None
    intersects_or_contains = bool(overlaps or all_depths)

    return {
        "evaluable": True,
        "gap": 0.0 if intersects_or_contains else float(distance),
        "closest_points": {"a": point_a, "b": point_b},
        "surface_intersection_pairs": len(overlaps),
        "penetrating_samples": len(all_depths),
        "penetration_evaluable": penetration_evaluable,
        "penetration_depth_estimate": penetration,
        "penetration_is_sampled_lower_bound": True,
        "containment_method": "generalized_winding_number",
        "containment": {
            "a_in_b": {key: value for key, value in first_containment.items() if key != "depths"},
            "b_in_a": {key: value for key, value in second_containment.items() if key != "depths"},
        },
        "axis_aligned_bounds_overlap": _axis_overlap(first, second),
    }


def _compare_budget(
    issues: list[dict[str, Any]],
    value: float,
    declaration: Any,
    path: str,
    code: str,
) -> None:
    lower, upper = _limits(declaration, path)
    if lower is not None and value < lower:
        issues.append(_issue(code, path, f"{value} is below the declared minimum {lower}", measured=value, minimum=lower))
    if upper is not None and value > upper:
        issues.append(_issue(code, path, f"{value} exceeds the declared maximum {upper}", measured=value, maximum=upper))


def _check_object(
    name: str,
    spec: Mapping[str, Any],
    snapshot: dict[str, Any],
    area_epsilon: float,
    issues: list[dict[str, Any]],
) -> None:
    path = f"objects.{name}"
    if snapshot["vertex_count"] == 0 or snapshot["triangle_count"] == 0:
        issues.append(_issue("empty_mesh", path, "evaluated mesh has no renderable triangles"))
    if (
        snapshot["local_nonfinite_vertices"]
        or snapshot["world_nonfinite_vertices"]
        or snapshot["nonfinite_transform_values"]
    ):
        issues.append(
            _issue(
                "nonfinite_coordinates",
                path,
                "evaluated mesh contains NaN or infinite coordinates",
                local=snapshot["local_nonfinite_vertices"],
                world=snapshot["world_nonfinite_vertices"],
                transform=snapshot["nonfinite_transform_values"],
            )
        )
    if snapshot["invalid_material_faces"]:
        issues.append(
            _issue(
                "invalid_material_assignment",
                path,
                "one or more faces use an empty or missing material slot",
                faces=snapshot["invalid_material_faces"],
            )
        )

    if "triangles" not in spec or "materials" not in spec or "topology" not in spec:
        raise AuditContractError(f"{path} must declare triangles, materials, and topology")
    _compare_budget(issues, snapshot["triangle_count"], spec["triangles"], f"{path}.triangles", "triangle_budget")
    _compare_budget(issues, snapshot["used_material_count"], spec["materials"], f"{path}.materials", "material_budget")

    topology = spec["topology"]
    if not isinstance(topology, Mapping):
        raise AuditContractError(f"{path}.topology must be an object")
    required_topology = (
        "max_boundary_edges",
        "max_nonmanifold_edges",
        "max_degenerate_faces",
        "max_degenerate_triangles",
        "require_closed_shell",
        "require_positive_volume",
        "max_self_intersections",
    )
    missing = [key for key in required_topology if key not in topology]
    if missing:
        raise AuditContractError(f"{path}.topology is missing: {', '.join(missing)}")
    for field, key in (
        ("boundary_edges", "max_boundary_edges"),
        ("nonmanifold_edges", "max_nonmanifold_edges"),
        ("degenerate_faces", "max_degenerate_faces"),
        ("degenerate_triangles", "max_degenerate_triangles"),
    ):
        maximum = _require_number(topology[key], f"{path}.topology.{key}", minimum=0.0)
        if snapshot[field] > maximum:
            issues.append(_issue("topology", f"{path}.topology.{key}", f"measured {snapshot[field]}, maximum {maximum}", measured=snapshot[field], maximum=maximum))
    if not isinstance(topology["require_closed_shell"], bool) or not isinstance(topology["require_positive_volume"], bool):
        raise AuditContractError(f"{path}.topology closed-shell and volume flags must be booleans")
    if topology["require_closed_shell"] and not snapshot["closed_shell"]:
        issues.append(_issue("open_shell", f"{path}.topology.require_closed_shell", "evaluated mesh is not a closed two-manifold shell"))
    if topology["require_positive_volume"]:
        volume = snapshot["signed_volume"]
        if volume is None or volume <= area_epsilon:
            issues.append(_issue("winding_or_volume", f"{path}.topology.require_positive_volume", "closed shell does not have a positive signed-volume signal", measured=volume))

    self_pairs = _self_intersections(snapshot, area_epsilon)
    snapshot["self_intersection_pairs"] = self_pairs
    maximum_self = _require_number(topology["max_self_intersections"], f"{path}.topology.max_self_intersections", minimum=0.0)
    if self_pairs is None:
        issues.append(_issue("self_intersection_unevaluable", f"{path}.topology.max_self_intersections", "self-intersection could not be evaluated"))
    elif len(self_pairs) > maximum_self:
        issues.append(_issue("self_intersection", f"{path}.topology.max_self_intersections", f"measured {len(self_pairs)} conservative triangle pairs, maximum {maximum_self}", measured=len(self_pairs), maximum=maximum_self))

    if "origin" in spec:
        origin = spec["origin"]
        if not isinstance(origin, Mapping) or "expected_world" not in origin or "tolerance" not in origin:
            raise AuditContractError(f"{path}.origin needs expected_world and tolerance")
        expected = _require_vector(origin["expected_world"], f"{path}.origin.expected_world")
        tolerance = _require_number(origin["tolerance"], f"{path}.origin.tolerance", minimum=0.0)
        actual_origin = snapshot["origin_world"]
        deviations = [
            abs(actual_origin[axis] - expected[axis])
            if actual_origin[axis] is not None
            else None
            for axis in range(3)
        ]
        if any(value is None or value > tolerance for value in deviations):
            issues.append(_issue("origin", f"{path}.origin", "world origin is outside tolerance", measured=snapshot["origin_world"], expected=list(expected), tolerance=tolerance))

    if "bounds" in spec:
        bounds = spec["bounds"]
        if not isinstance(bounds, Mapping) or not all(key in bounds for key in ("expected_min", "expected_max", "tolerance")):
            raise AuditContractError(f"{path}.bounds needs expected_min, expected_max, and tolerance")
        expected_min = _require_vector(bounds["expected_min"], f"{path}.bounds.expected_min")
        expected_max = _require_vector(bounds["expected_max"], f"{path}.bounds.expected_max")
        tolerance = _require_number(bounds["tolerance"], f"{path}.bounds.tolerance", minimum=0.0)
        actual_min = snapshot["bounds_world"]["min"]
        actual_max = snapshot["bounds_world"]["max"]
        if actual_min is None or any(abs(actual_min[i] - expected_min[i]) > tolerance or abs(actual_max[i] - expected_max[i]) > tolerance for i in range(3)):
            issues.append(_issue("bounds", f"{path}.bounds", "evaluated world bounds are outside tolerance", measured=snapshot["bounds_world"], expected={"min": list(expected_min), "max": list(expected_max)}, tolerance=tolerance))


def _ground_check(
    name: str,
    snapshot: Mapping[str, Any],
    ground: Mapping[str, Any],
    axis: int,
    height: float,
    issues: list[dict[str, Any]],
) -> bool:
    path = f"objects.{name}.ground"
    if "touch_tolerance" not in ground or "max_penetration" not in ground:
        raise AuditContractError(f"{path} needs touch_tolerance and max_penetration")
    tolerance = _require_number(ground["touch_tolerance"], f"{path}.touch_tolerance", minimum=0.0)
    max_penetration = _require_number(ground["max_penetration"], f"{path}.max_penetration", minimum=0.0)
    minimum = snapshot["bounds_world"]["min"]
    if minimum is None:
        issues.append(_issue("ground_unevaluable", path, "ground reach could not be evaluated"))
        return False
    offset = float(minimum[axis] - height)
    passed = offset <= tolerance and offset >= -max_penetration
    if not passed:
        issues.append(_issue("ground", path, "lowest evaluated point does not meet the ground contract", offset=offset, touch_tolerance=tolerance, max_penetration=max_penetration))
    return passed


def audit_scene(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the current Blender scene against an explicit binding contract."""

    if not isinstance(contract, Mapping):
        raise AuditContractError("contract must be a mapping")
    if contract.get("schema_version") != 1:
        raise AuditContractError("schema_version must be 1")
    coordinate = contract.get("coordinate_system")
    objects_spec = contract.get("objects")
    if not isinstance(coordinate, Mapping) or not isinstance(objects_spec, Mapping) or not objects_spec:
        raise AuditContractError("coordinate_system and a non-empty objects mapping are required")
    if not isinstance(contract.get("allow_unlisted_meshes", False), bool):
        raise AuditContractError("allow_unlisted_meshes must be a boolean")
    axis_name = coordinate.get("up_axis")
    if axis_name not in AXIS_INDEX:
        raise AuditContractError("coordinate_system.up_axis must be X, Y, or Z")
    ground_height = _require_number(coordinate.get("ground_height"), "coordinate_system.ground_height")
    epsilon = _require_number(contract.get("geometry_epsilon", 1e-6), "geometry_epsilon", minimum=0.0)
    if epsilon == 0.0:
        raise AuditContractError("geometry_epsilon must be greater than zero")

    issues: list[dict[str, Any]] = []
    scene_meshes = {obj.name: obj for obj in bpy.context.scene.objects if obj.type == "MESH"}
    unlisted = sorted(set(scene_meshes) - set(objects_spec))
    if unlisted and not contract.get("allow_unlisted_meshes", False):
        issues.append(_issue("unlisted_meshes", "objects", "scene contains mesh objects absent from the contract", objects=unlisted))

    depsgraph = bpy.context.evaluated_depsgraph_get()
    snapshots: dict[str, dict[str, Any]] = {}
    ground_pass: dict[str, bool] = {}
    for name, spec in objects_spec.items():
        if not isinstance(name, str) or not name or not isinstance(spec, Mapping):
            raise AuditContractError("objects must map non-empty names to object declarations")
        obj = scene_meshes.get(name)
        if obj is None:
            issues.append(_issue("missing_object", f"objects.{name}", "required mesh object is absent"))
            ground_pass[name] = False
            continue
        snapshot = _snapshot_object(obj, depsgraph, epsilon)
        snapshots[name] = snapshot
        _check_object(name, spec, snapshot, epsilon, issues)
        if "ground" in spec:
            if not isinstance(spec["ground"], Mapping):
                raise AuditContractError(f"objects.{name}.ground must be an object")
            ground_pass[name] = _ground_check(name, snapshot, spec["ground"], AXIS_INDEX[axis_name], ground_height, issues)
        else:
            ground_pass[name] = False

    budgets = contract.get("budgets", {})
    if not isinstance(budgets, Mapping):
        raise AuditContractError("budgets must be an object")
    total_triangles = sum(value["triangle_count"] for value in snapshots.values())
    all_materials = sorted({name for value in snapshots.values() for name in value["used_material_names"]})
    if "triangles" in budgets:
        _compare_budget(issues, total_triangles, budgets["triangles"], "budgets.triangles", "triangle_budget")
    if "materials" in budgets:
        _compare_budget(issues, len(all_materials), budgets["materials"], "budgets.materials", "material_budget")
    if "parts" in budgets:
        _compare_budget(issues, len(snapshots), budgets["parts"], "budgets.parts", "part_budget")

    contact_results: dict[str, dict[str, Any]] = {}
    contacts = contract.get("contacts", [])
    if not isinstance(contacts, Sequence) or isinstance(contacts, (str, bytes)):
        raise AuditContractError("contacts must be an array")
    for index, declaration in enumerate(contacts):
        path = f"contacts[{index}]"
        if not isinstance(declaration, Mapping):
            raise AuditContractError(f"{path} must be an object")
        required = ("name", "a", "b", "max_gap", "min_penetration", "max_penetration")
        if any(key not in declaration for key in required):
            raise AuditContractError(f"{path} must declare {', '.join(required)}")
        probe_name = declaration["name"]
        first_name = declaration["a"]
        second_name = declaration["b"]
        if not isinstance(probe_name, str) or not probe_name or probe_name in contact_results:
            raise AuditContractError(f"{path}.name must be unique and non-empty")
        if not isinstance(first_name, str) or not isinstance(second_name, str):
            raise AuditContractError(f"{path}.a and {path}.b must be object names")
        max_gap = _require_number(declaration["max_gap"], f"{path}.max_gap", minimum=0.0)
        min_penetration = _require_number(declaration["min_penetration"], f"{path}.min_penetration", minimum=0.0)
        max_penetration = _require_number(declaration["max_penetration"], f"{path}.max_penetration", minimum=0.0)
        if min_penetration > max_penetration:
            raise AuditContractError(f"{path}.min_penetration cannot exceed max_penetration")
        if first_name not in snapshots or second_name not in snapshots:
            result = {"evaluable": False, "passed": False, "reason": "one or both named mesh objects are absent"}
        else:
            result = measure_contact(snapshots[first_name], snapshots[second_name], epsilon)
            gap = result.get("gap")
            penetration = result.get("penetration_depth_estimate")
            result["passed"] = bool(
                result["evaluable"]
                and gap is not None
                and gap <= max_gap
                and result.get("penetration_evaluable")
                and penetration is not None
                and min_penetration <= penetration <= max_penetration
            )
        result.update({"a": first_name, "b": second_name, "limits": {"max_gap": max_gap, "min_penetration": min_penetration, "max_penetration": max_penetration}})
        contact_results[probe_name] = result
        if not result["passed"]:
            issues.append(_issue("contact", path, f"contact probe {probe_name!r} failed", probe=probe_name, measurement=result))

    support = contract.get("support")
    support_report: dict[str, Any] | None = None
    if support is not None:
        if not isinstance(support, Mapping) or not all(key in support for key in ("ground_nodes", "required_nodes", "edges")):
            raise AuditContractError("support needs ground_nodes, required_nodes, and edges")
        ground_nodes = support["ground_nodes"]
        required_nodes = support["required_nodes"]
        edges = support["edges"]
        if any(not isinstance(value, Sequence) or isinstance(value, (str, bytes)) for value in (ground_nodes, required_nodes, edges)):
            raise AuditContractError("support ground_nodes, required_nodes, and edges must be arrays")
        if any(not isinstance(name, str) or name not in objects_spec for name in [*ground_nodes, *required_nodes]):
            raise AuditContractError("support ground_nodes and required_nodes must name contract objects")
        missing_ground = [name for name in ground_nodes if "ground" not in objects_spec[name]]
        if missing_ground:
            raise AuditContractError(
                "support ground_nodes need object ground declarations: "
                + ", ".join(missing_ground)
            )
        active_ground = {name for name in ground_nodes if name in snapshots and ground_pass.get(name, False)}
        adjacency: dict[str, set[str]] = {name: set() for name in objects_spec}
        active_edges = []
        for index, edge in enumerate(edges):
            if not isinstance(edge, Mapping) or not all(key in edge for key in ("child", "support", "probe")):
                raise AuditContractError(f"support.edges[{index}] needs child, support, and probe")
            child, parent, probe = edge["child"], edge["support"], edge["probe"]
            if child not in objects_spec or parent not in objects_spec or probe not in contact_results:
                raise AuditContractError(f"support.edges[{index}] references an unknown object or probe")
            if contact_results[probe]["passed"]:
                adjacency[child].add(parent)
                active_edges.append({"child": child, "support": parent, "probe": probe})

        reachable = set(active_ground)
        changed = True
        while changed:
            changed = False
            for child, parents in adjacency.items():
                if child not in reachable and parents & reachable:
                    reachable.add(child)
                    changed = True
        unreachable = sorted(name for name in required_nodes if name not in reachable)
        for name in unreachable:
            issues.append(_issue("unsupported", "support.required_nodes", f"{name!r} has no passing declared contact path to ground", object=name))
        support_report = {
            "declared_ground_nodes": list(ground_nodes),
            "active_ground_nodes": sorted(active_ground),
            "active_edges": active_edges,
            "reachable_nodes": sorted(reachable),
            "unreachable_required_nodes": unreachable,
        }

    for snapshot in snapshots.values():
        snapshot.pop("vertices", None)
        snapshot.pop("triangles_data", None)
    report = {
        "schema_version": 1,
        "passed": not issues,
        "issues": issues,
        "summary": {
            "audited_objects": len(snapshots),
            "triangles": total_triangles,
            "materials": len(all_materials),
            "material_names": all_materials,
        },
        "objects": snapshots,
        "contacts": contact_results,
        "support": support_report,
    }
    return report


def assert_audit_passed(report: Mapping[str, Any]) -> None:
    """Raise one compact assertion containing all binding audit failures."""

    if report.get("passed"):
        return
    issues = report.get("issues", [])
    details = "\n".join(
        f"- {entry.get('code', 'unknown')} at {entry.get('path', '?')}: {entry.get('message', '')}"
        for entry in issues
    )
    raise AssertionError(f"geometry audit failed with {len(issues)} issue(s):\n{details}")
