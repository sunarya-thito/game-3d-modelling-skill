"""Blender-runtime regression checks for meshkit.

Run from the repository root:
  blender --background --factory-startup --python-exit-code 1 \
    --python tests/blender_meshkit_checks.py
"""

from pathlib import Path
import sys
import tempfile

import bpy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))

from meshkit import (  # noqa: E402
    MeshDraft,
    add_extruded_outline,
    add_path_extrusion,
    add_profile_loft,
    add_revolved_profile,
    create_mesh_object,
    inspect_topology,
    start_empty_scene,
    write_glb,
)


def assert_clean(report: dict[str, int]) -> None:
    for field in ("boundary_edges", "nonmanifold_edges", "degenerate_faces"):
        if report[field] != 0:
            raise AssertionError(f"expected clean topology, got {report}")


start_empty_scene()

loft = MeshDraft("loft")
add_profile_loft(
    loft,
    (
        ((-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)),
        ((-0.7, 1, -0.8), (0.7, 1, -0.8), (0.7, 1, 0.8), (-0.7, 1, 0.8)),
    ),
)
assert_clean(inspect_topology(create_mesh_object(loft)))

sweep = MeshDraft("sweep")
add_path_extrusion(
    sweep,
    path=((0, 0, 0), (0, 0, 1), (0.4, 0, 2)),
    section=((-0.2, -0.1), (0.2, -0.1), (0.2, 0.1), (-0.2, 0.1)),
    guide_up=(0, 0, 1),
)
assert_clean(inspect_topology(create_mesh_object(sweep)))

pointed = MeshDraft("pointed-revolved-profile")
sections = add_revolved_profile(
    pointed,
    radius_and_height=((0.0, 0.0), (1.0, 1.0), (0.0, 2.0)),
    segment_count=14,
)
if [len(section) for section in sections] != [1, 14, 1]:
    raise AssertionError("zero-radius profile stations must collapse to one vertex")
pointed_obj = create_mesh_object(pointed)
assert_clean(inspect_topology(pointed_obj))

slab = MeshDraft("concave-slab")
add_extruded_outline(
    slab,
    outline=((0, 0), (2, 0), (2, 1), (1, 0.4), (0, 1)),
    origin=(0, 0, 0),
    horizontal=(1, 0, 0),
    vertical=(0, 0, 1),
    thickness=0.2,
)
assert_clean(inspect_topology(create_mesh_object(slab)))

bad_material = MeshDraft("bad-material")
add_profile_loft(
    bad_material,
    (
        ((0, 0, 0), (1, 0, 0), (0, 0, 1)),
        ((0, 1, 0), (1, 1, 0), (0, 1, 1)),
    ),
    material_index=1,
)
try:
    create_mesh_object(bad_material)
except ValueError as exc:
    if "material slot" not in str(exc):
        raise
else:
    raise AssertionError("invalid material index was accepted")

with tempfile.TemporaryDirectory() as directory:
    exported = write_glb([pointed_obj], Path(directory) / "roundtrip.glb")
    start_empty_scene()
    bpy.ops.import_scene.gltf(filepath=str(exported))
    imported = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if len(imported) != 1:
        raise AssertionError(f"expected one re-imported mesh, got {len(imported)}")
    imported[0].data.calc_loop_triangles()
    if len(imported[0].data.loop_triangles) != 28:
        raise AssertionError("GLB round-trip changed the triangle count")

print("meshkit Blender regression checks passed")
