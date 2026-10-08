"""Executable positive and negative fixtures for ``auditkit``.

Run from the repository root:

  blender --background --factory-startup --python-exit-code 1 \
    --python examples/geometry-gate.py -- --out build/geometry-gate

The positive fixture must pass.  The deliberately broken fixture must fail and
must expose topology, placement, contact, support, and self-intersection issues.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

import bpy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))

from auditkit import assert_audit_passed, audit_scene  # noqa: E402


BOX_FACES = (
    (0, 3, 2, 1),
    (4, 5, 6, 7),
    (0, 1, 5, 4),
    (1, 2, 6, 5),
    (2, 3, 7, 6),
    (3, 0, 4, 7),
)


def _box_data(minimum: Sequence[float], maximum: Sequence[float]):
    x0, y0, z0 = minimum
    x1, y1, z1 = maximum
    vertices = (
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    )
    return vertices, BOX_FACES


def _material(name: str, color: Sequence[float]) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    return material


def create_box(
    name: str,
    minimum: Sequence[float],
    maximum: Sequence[float],
    color: Sequence[float],
    *,
    omit_face: int | None = None,
) -> bpy.types.Object:
    vertices, faces = _box_data(minimum, maximum)
    selected_faces = [face for index, face in enumerate(faces) if index != omit_face]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], selected_faces)
    mesh.materials.append(_material(f"{name}Material", color))
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_overlapping_shells(name: str) -> bpy.types.Object:
    """Create two individually closed boxes whose surfaces cross each other."""

    first_vertices, first_faces = _box_data((3.0, 0.0, 0.0), (4.0, 1.0, 1.0))
    second_vertices, second_faces = _box_data((3.4, 0.3, 0.2), (4.4, 1.3, 1.2))
    vertices = list(first_vertices) + list(second_vertices)
    faces = list(first_faces) + [tuple(index + 8 for index in face) for face in second_faces]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(_material(f"{name}Material", (0.8, 0.25, 0.2)))
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _topology(maximum_self_intersections: int = 0) -> dict:
    return {
        "max_boundary_edges": 0,
        "max_nonmanifold_edges": 0,
        "max_degenerate_faces": 0,
        "max_degenerate_triangles": 0,
        "require_closed_shell": True,
        "require_positive_volume": True,
        "max_self_intersections": maximum_self_intersections,
    }


def positive_contract() -> dict:
    return {
        "schema_version": 1,
        "coordinate_system": {"up_axis": "Z", "ground_height": 0.0},
        "geometry_epsilon": 1e-6,
        "allow_unlisted_meshes": False,
        "objects": {
            "Base": {
                "origin": {"expected_world": [0, 0, 0], "tolerance": 1e-6},
                "bounds": {
                    "expected_min": [0, 0, 0],
                    "expected_max": [2, 2, 0.5],
                    "tolerance": 1e-6,
                },
                "triangles": {"min": 12, "max": 12},
                "materials": {"min": 1, "max": 1},
                "topology": _topology(),
                "ground": {"touch_tolerance": 1e-6, "max_penetration": 0.0},
            },
            "Payload": {
                "origin": {"expected_world": [0, 0, 0], "tolerance": 1e-6},
                "bounds": {
                    "expected_min": [0.5, 0.5, 0.5],
                    "expected_max": [1.5, 1.5, 1.5],
                    "tolerance": 1e-6,
                },
                "triangles": {"min": 12, "max": 12},
                "materials": {"min": 1, "max": 1},
                "topology": _topology(),
            },
        },
        "budgets": {
            "triangles": {"min": 24, "max": 24},
            "materials": {"min": 2, "max": 2},
            "parts": {"min": 2, "max": 2},
        },
        "contacts": [
            {
                "name": "payload-on-base",
                "a": "Payload",
                "b": "Base",
                "max_gap": 1e-6,
                "min_penetration": 0.0,
                "max_penetration": 1e-6,
            }
        ],
        "support": {
            "ground_nodes": ["Base"],
            "required_nodes": ["Base", "Payload"],
            "edges": [
                {"child": "Payload", "support": "Base", "probe": "payload-on-base"}
            ],
        },
    }


def negative_contract() -> dict:
    contract = positive_contract()
    contract["objects"]["CrossedShells"] = {
        "origin": {"expected_world": [0, 0, 0], "tolerance": 1e-6},
        "triangles": {"min": 24, "max": 24},
        "materials": {"min": 1, "max": 1},
        "topology": _topology(),
    }
    contract["budgets"] = {
        "triangles": {"min": 48, "max": 48},
        "materials": {"min": 3, "max": 3},
        "parts": {"min": 3, "max": 3},
    }
    return contract


def build_positive_fixture() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    create_box("Base", (0, 0, 0), (2, 2, 0.5), (0.15, 0.35, 0.75))
    create_box("Payload", (0.5, 0.5, 0.5), (1.5, 1.5, 1.5), (0.9, 0.55, 0.15))


def build_negative_fixture() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Base is above ground, Payload is open and floating, and two shells cross.
    create_box("Base", (0, 0, 0.1), (2, 2, 0.6), (0.15, 0.35, 0.75))
    create_box(
        "Payload",
        (0.5, 0.5, 0.9),
        (1.5, 1.5, 1.9),
        (0.9, 0.55, 0.15),
        omit_face=1,
    )
    create_overlapping_shells("CrossedShells")


def _arguments() -> argparse.Namespace:
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="Run deterministic geometry-gate fixtures")
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "geometry-gate")
    return parser.parse_args(values)


def main() -> None:
    arguments = _arguments()
    arguments.out.mkdir(parents=True, exist_ok=True)

    build_positive_fixture()
    positive = audit_scene(positive_contract())
    assert_audit_passed(positive)
    (arguments.out / "positive.json").write_text(
        json.dumps(positive, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    build_negative_fixture()
    negative = audit_scene(negative_contract())
    if negative["passed"]:
        raise AssertionError("deliberately broken geometry fixture unexpectedly passed")
    required_codes = {"bounds", "contact", "ground", "open_shell", "self_intersection", "unsupported"}
    observed_codes = {issue["code"] for issue in negative["issues"]}
    missing = required_codes - observed_codes
    if missing:
        raise AssertionError(f"negative fixture did not exercise expected failures: {sorted(missing)}")
    (arguments.out / "negative.json").write_text(
        json.dumps(negative, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        "geometry-gate fixtures passed: positive accepted; negative rejected with "
        f"{len(negative['issues'])} issue(s)"
    )


if __name__ == "__main__":
    main()
