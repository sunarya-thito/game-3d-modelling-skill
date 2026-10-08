"""Blender-runtime regression checks for the measured geometry gate.

Run from the repository root:
  blender --background --factory-startup --python-exit-code 1 \
    --python tests/blender_audit_checks.py
"""

from copy import deepcopy
import json
from pathlib import Path
import runpy
import sys

import bpy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))

from auditkit import AuditContractError, assert_audit_passed, audit_scene  # noqa: E402


fixture = runpy.run_path(str(ROOT / "examples" / "geometry-gate.py"))
build_positive_fixture = fixture["build_positive_fixture"]
build_negative_fixture = fixture["build_negative_fixture"]
positive_contract = fixture["positive_contract"]
negative_contract = fixture["negative_contract"]
create_box = fixture["create_box"]
topology_contract = fixture["_topology"]


def codes(report: dict) -> set[str]:
    return {issue["code"] for issue in report["issues"]}


# A clean two-part assembly passes evaluated bounds, topology, budgets, contact,
# ground, and directed support reachability.
build_positive_fixture()
positive = audit_scene(positive_contract())
assert_audit_passed(positive)
assert positive["passed"]
assert positive["summary"]["triangles"] == 24
assert positive["objects"]["Base"]["signed_volume"] > 0.0
assert positive["objects"]["Base"]["self_intersection_pairs"] == []
assert positive["contacts"]["payload-on-base"]["gap"] == 0.0
assert positive["contacts"]["payload-on-base"]["penetration_depth_estimate"] == 0.0
assert positive["support"]["unreachable_required_nodes"] == []
json.dumps(positive, allow_nan=False)


# The deterministic bad assembly must exercise every major structural class.
build_negative_fixture()
negative = audit_scene(negative_contract())
assert not negative["passed"]
expected = {
    "bounds",
    "contact",
    "ground",
    "open_shell",
    "self_intersection",
    "topology",
    "triangle_budget",
    "unsupported",
    "winding_or_volume",
}
assert expected <= codes(negative), (expected - codes(negative), negative["issues"])
assert negative["objects"]["CrossedShells"]["self_intersection_pairs"]
assert negative["contacts"]["payload-on-base"]["penetration_evaluable"] is False
try:
    assert_audit_passed(negative)
except AssertionError as exc:
    assert "geometry audit failed" in str(exc)
else:
    raise AssertionError("assert_audit_passed accepted a failed report")


# Penetration is accepted only through an explicit bounded declaration and is
# reported as a sampled lower-bound estimate rather than exact CSG depth.
build_positive_fixture()
payload = bpy.data.objects["Payload"]
for vertex in payload.data.vertices:
    vertex.co.z -= 0.1
overlap_contract = positive_contract()
overlap_contract["objects"]["Payload"]["bounds"]["expected_min"][2] = 0.4
overlap_contract["objects"]["Payload"]["bounds"]["expected_max"][2] = 1.4
overlap_contract["contacts"][0]["max_penetration"] = 0.11
overlap = audit_scene(overlap_contract)
assert_audit_passed(overlap)
probe = overlap["contacts"]["payload-on-base"]
assert probe["penetration_evaluable"] is True
assert 0.09 < probe["penetration_depth_estimate"] < 0.11, probe
assert probe["penetration_is_sampled_lower_bound"] is True


# A curved, concave closed shell must never classify points outside its world
# AABB as inside. The torus-hole case also exercises points inside the AABB but
# outside the actual solid, where a local nearest-face half-space is inadequate.
def build_torus_probe(source_min, source_max) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_torus_add(
        align="WORLD",
        location=(0.0, 0.0, 0.0),
        major_segments=24,
        minor_segments=8,
        major_radius=1.0,
        minor_radius=0.2,
    )
    guard = bpy.context.object
    guard.name = "CurvedGuard"
    guard.data.name = "CurvedGuard"
    guard_material = bpy.data.materials.new("CurvedGuardMaterial")
    guard.data.materials.append(guard_material)
    create_box("OutsideProbe", source_min, source_max, (0.9, 0.2, 0.1))


def torus_probe_contract() -> dict:
    return {
        "schema_version": 1,
        "coordinate_system": {"up_axis": "Z", "ground_height": 0.0},
        "geometry_epsilon": 1e-6,
        "allow_unlisted_meshes": False,
        "objects": {
            "CurvedGuard": {
                "triangles": {"min": 300, "max": 500},
                "materials": {"min": 1, "max": 1},
                "topology": topology_contract(),
            },
            "OutsideProbe": {
                "triangles": {"min": 12, "max": 12},
                "materials": {"min": 1, "max": 1},
                "topology": topology_contract(),
            },
        },
        "contacts": [
            {
                "name": "probe-to-curved-guard",
                "a": "OutsideProbe",
                "b": "CurvedGuard",
                "max_gap": 1.0,
                "min_penetration": 0.0,
                "max_penetration": 0.0,
            }
        ],
    }


build_torus_probe((1.4, -0.05, -0.05), (1.5, 0.05, 0.05))
outside_aabb = audit_scene(torus_probe_contract())
assert_audit_passed(outside_aabb)
outside_probe = outside_aabb["contacts"]["probe-to-curved-guard"]
assert outside_probe["containment_method"] == "generalized_winding_number"
assert (
    outside_probe["containment"]["a_in_b"]["outside_aabb_samples"]
    == outside_probe["containment"]["a_in_b"]["samples"]
)
assert outside_probe["containment"]["a_in_b"]["inside_samples"] == 0
assert outside_probe["penetrating_samples"] == 0
assert outside_probe["penetration_depth_estimate"] == 0.0

build_torus_probe((-0.05, -0.05, -0.05), (0.05, 0.05, 0.05))
concave_hole = audit_scene(torus_probe_contract())
assert_audit_passed(concave_hole)
hole_probe = concave_hole["contacts"]["probe-to-curved-guard"]
assert hole_probe["containment"]["a_in_b"]["outside_aabb_samples"] == 0
assert hole_probe["containment"]["a_in_b"]["inside_samples"] == 0
assert hole_probe["containment"]["a_in_b"]["ambiguous_samples"] == 0
assert hole_probe["penetration_depth_estimate"] == 0.0


# Non-finite authored coordinates must never become an uneventful pass or leak
# non-standard NaN tokens into the machine-readable report.
build_positive_fixture()
bpy.data.objects["Base"].data.vertices[0].co.x = float("nan")
bpy.context.view_layer.update()
nonfinite = audit_scene(positive_contract())
assert not nonfinite["passed"]
assert "nonfinite_coordinates" in codes(nonfinite)
assert "self_intersection_unevaluable" in codes(nonfinite)
json.dumps(nonfinite, allow_nan=False)


# A polygon may have non-zero total area while its evaluated triangulation
# contains a collapsed triangle; both defect classes are binding measurements.
build_positive_fixture()
payload = bpy.data.objects["Payload"]
payload.data.vertices[1].co = payload.data.vertices[0].co
payload.data.update(calc_edges=True)
degenerate = audit_scene(positive_contract())
assert not degenerate["passed"]
assert degenerate["objects"]["Payload"]["degenerate_triangles"] > 0
assert "topology" in codes(degenerate)


# Mirroring a valid closed mesh changes the signed-volume winding signal and
# must fail when the contract requires positive winding.
build_positive_fixture()
base = bpy.data.objects["Base"]
base.scale.x = -1.0
bpy.context.view_layer.update()
mirrored_contract = positive_contract()
mirrored_contract["objects"]["Base"]["bounds"]["expected_min"][0] = -2.0
mirrored_contract["objects"]["Base"]["bounds"]["expected_max"][0] = 0.0
mirrored = audit_scene(mirrored_contract)
assert not mirrored["passed"]
assert mirrored["objects"]["Base"]["winding_signal"] == "negative"
assert "winding_or_volume" in codes(mirrored)


# Binding fields cannot disappear silently. Invalid contracts raise before a
# caller can mistake incomplete checks for a passing asset.
build_positive_fixture()
malformed = deepcopy(positive_contract())
del malformed["objects"]["Base"]["topology"]
try:
    audit_scene(malformed)
except AuditContractError as exc:
    assert "topology" in str(exc)
else:
    raise AssertionError("incomplete object contract was accepted")

missing = positive_contract()
missing["objects"]["Absent"] = deepcopy(missing["objects"]["Payload"])
missing["allow_unlisted_meshes"] = True
missing_report = audit_scene(missing)
assert not missing_report["passed"]
assert "missing_object" in codes(missing_report)

print("auditkit Blender regression checks passed")
